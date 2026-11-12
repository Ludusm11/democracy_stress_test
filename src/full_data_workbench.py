"""Build source-specific working tables and figures from the whole raw collection.

Run after audit_data.py. Nothing in data/raw is edited. Each output keeps its
source and unit of observation; the report explains where comparison stops.
"""

from __future__ import annotations

import hashlib
import io
import os
import re
from pathlib import Path
from zipfile import ZipFile

os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parents[1] / "outputs" / ".matplotlib"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw"
PROCESSED = ROOT / "data/processed"
OUT = ROOT / "outputs/data_audit"
FIG = OUT / "figures"
for folder in (PROCESSED, OUT, FIG):
    folder.mkdir(parents=True, exist_ok=True)


def save_plot(name: str) -> None:
    plt.tight_layout()
    plt.savefig(FIG / name, dpi=170, bbox_inches="tight")
    plt.close()


def family(path: Path) -> str:
    part = path.relative_to(RAW).parts[0]
    if part in {"V-Dem-CY-FullOthers-v16_csv.zip", "idea_export_voter_turnout_database_region.xlsx", "The PopuList 4.0.csv"}:
        return {"V-Dem-CY-FullOthers-v16_csv.zip": "V-Dem", "idea_export_voter_turnout_database_region.xlsx": "IDEA", "The PopuList 4.0.csv": "PopuList"}[part]
    return part


# Local-only files (not in the repository, see .gitignore): left out so every computer gets the same inventory.
LOCAL_ONLY = {"evs_wvs_joint_2017_2022_v5/EVS_WVS_Joint_Csv_v5_0.csv"}


def inventory() -> pd.DataFrame:
    rows = []
    for path in sorted(RAW.rglob("*"), key=lambda p: p.relative_to(RAW).as_posix()):
        if not path.is_file() or path.relative_to(RAW).as_posix() in LOCAL_ONLY:
            continue
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        ext = path.suffix.lower()
        role = ("table" if ext in {".csv", ".tsv", ".tab", ".xlsx", ".db", ".json"}
                else "archive" if ext == ".zip" else "documentation/metadata")
        rows.append(dict(source_family=family(path), relative_path=path.relative_to(RAW).as_posix(),
                         extension=ext, role=role, bytes=path.stat().st_size, sha256=digest.hexdigest()))
    result = pd.DataFrame(rows)
    result.to_csv(OUT / "raw_file_inventory.csv", index=False)
    return result


def eurobarometer_trend() -> pd.DataFrame:
    source = RAW / "eurobarometer_std105_2026/STD105_volume_D.zip"
    indicators = {"QA6_2": "Political parties", "QA6_10": "National government",
                  "QA6_11": "National parliament"}
    rows = []
    with ZipFile(source) as archive:
        for question, indicator in indicators.items():
            name = next(n for n in archive.namelist() if n.endswith(f"_{question}.xlsx"))
            book = load_workbook(io.BytesIO(archive.read(name)), read_only=True, data_only=True)
            for sheet_name in book.sheetnames:
                sheet = book[sheet_name]
                country = sheet_name.removeprefix(question + "_")
                for column in range(3, sheet.max_column + 1):
                    wave = sheet.cell(10, column).value
                    pct = sheet.cell(13, column).value
                    count = sheet.cell(12, column).value
                    fieldwork = sheet.cell(11, column).value
                    if wave is None or pct is None:
                        continue
                    years = re.findall(r"20\d{2}", str(fieldwork))
                    rows.append(dict(country_code=country, question=question,
                                     institution=indicator, wave=str(wave),
                                     fieldwork=str(fieldwork).replace("\n", " "),
                                     fieldwork_year=int(years[-1]) if years else np.nan,
                                     trust_pct=100 * float(pct),
                                     weighted_count=float(count) if count is not None else np.nan,
                                     source_file=name, source_sheet=sheet_name,
                                     source_cell=f"{sheet.cell(13, column).coordinate}"))
            book.close()
    trend = pd.DataFrame(rows)
    starts = trend.fieldwork.str.extract(r"(\d{1,2}/[A-Za-z]{3}/20\d{2})", expand=False)
    trend["fieldwork_start"] = pd.to_datetime(starts, format="%d/%b/%Y", errors="coerce")
    # Volume D repeats the current wave as the last "previous" column and as
    # the current column. Verify the two percentages agree before keeping one.
    keys = ["country_code", "question", "wave"]
    dup = trend.duplicated(keys, keep=False)
    if dup.any():
        assert trend.loc[dup].groupby(keys).trust_pct.nunique().eq(1).all()
        trend = trend.drop_duplicates(keys, keep="last").reset_index(drop=True)
    assert trend.trust_pct.between(0, 100).all()
    # The independent Volume AP comparison workbook reports these same cells.
    expected = {"QA6_2": 12, "QA6_10": 21, "QA6_11": 23}
    for question, value in expected.items():
        actual = trend.loc[trend.country_code.eq("FR") & trend.question.eq(question)
                           & trend.wave.eq("105.2"), "trust_pct"]
        assert len(actual) == 1 and np.isclose(actual.iloc[0], value), (question, actual)
    trend.to_csv(PROCESSED / "eurobarometer_trust_trend.csv", index=False)
    fr = trend.loc[trend.country_code.eq("FR") & trend.fieldwork_start.notna()].copy()
    fig, ax = plt.subplots(figsize=(10, 5))
    for name, group in fr.groupby("institution"):
        group = group.sort_values("fieldwork_start")
        ax.plot(group.fieldwork_start, group.trust_pct, marker=".", markersize=4, label=name)
    ax.set(xlabel="Fieldwork start", ylabel="Tend to trust (%)",
           title="Trust in French institutions across Eurobarometer waves")
    ax.legend(frameon=False)
    ax.grid(alpha=0.2)
    save_plot("france_eurobarometer_trend.png")
    return trend


def cevipof_published() -> pd.DataFrame:
    # Transcribed from visually checked report pages 28, 40 and 43. Page 43 is
    # a cross-country presentation of Q25; France is not duplicated in analysis.
    rows = [
        ("France", "Q13", "National Assembly", 20, 28, 3166),
        ("France", "Q13", "Government", 17, 28, 3166),
        ("France", "Q25", "Political parties", 15, 40, 3166),
        ("Germany", "Q25", "Political parties", 35, 43, np.nan),
        ("Italy", "Q25", "Political parties", 26, 43, np.nan),
        ("United Kingdom", "Q25", "Political parties", 31, 43, np.nan),
        ("Romania", "Q25", "Political parties", 18, 43, np.nan),
    ]
    table = pd.DataFrame(rows, columns=["country", "question", "institution",
                                        "trust_pct", "pdf_page", "france_sample_n"])
    table["wave"] = "Wave 17, January–February 2026"
    table["measure"] = "Published percent expressing confidence"
    table["source_file"] = "Barometre_confiance_CEVIPOFVague17_fev2026_vd1.pdf"
    table.to_csv(PROCESSED / "cevipof_trust_2026_published.csv", index=False)
    plot = table.loc[table.institution.eq("Political parties")].sort_values("trust_pct")
    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.barh(plot.country, plot.trust_pct, color="#527c91")
    ax.set(xlim=(0, 40), xlabel="Confidence (%)",
           title="Confidence in political parties, CEVIPOF wave 17")
    for i, value in enumerate(plot.trust_pct):
        ax.text(value + 0.6, i, f"{value:.0f}%", va="center")
    save_plot("cevipof_party_trust_countries.png")
    return table


def evs_country_trust() -> pd.DataFrame:
    source = RAW / "evs_wvs_joint_2017_2022_v5/F00012158-EVS_WVS_Joint_Csv_v5_0.zip"  # pandas reads the CSV inside
    columns = ["cntry_AN", "year", "gwght", "E069_07", "E069_11", "E069_12"]
    responses = pd.read_csv(source, usecols=columns, low_memory=False)
    rows = []
    for code, institution in [("E069_07", "Parliament"), ("E069_11", "Government"),
                              ("E069_12", "Political parties")]:
        valid = responses.loc[responses[code].isin([1, 2, 3, 4]) & responses.gwght.gt(0)].copy()
        valid["weighted_confident"] = np.where(valid[code].isin([1, 2]), valid.gwght, 0)
        totals = valid.groupby(["cntry_AN", "year"], dropna=False).agg(
            valid_n=(code, "size"), weight_sum=("gwght", "sum"),
            confident_weight=("weighted_confident", "sum")).reset_index()
        totals["institution"] = institution
        totals["weighted_confident_pct"] = 100 * totals.confident_weight / totals.weight_sum
        rows.append(totals)
    result = pd.concat(rows, ignore_index=True).rename(columns={"cntry_AN": "country_code"})
    assert result.weighted_confident_pct.between(0, 100).all()
    result.to_csv(PROCESSED / "evs_wvs_country_trust_summary.csv", index=False)
    # This is a country-and-fieldwork-year comparison within one survey release.
    subset = result.loc[result.country_code.isin(["FR", "DE", "IT", "ES"])
                        & result.institution.eq("Political parties")].sort_values("country_code")
    fig, ax = plt.subplots(figsize=(7, 3.8))
    labels = subset.country_code + " " + subset.year.astype(str)
    ax.barh(labels, subset.weighted_confident_pct, color="#658459")
    ax.set(xlabel="Weighted confident share among valid answers (%)",
           title="Confidence in political parties, EVS/WVS joint survey")
    save_plot("evs_wvs_party_confidence_selected_countries.png")
    return result


def elections_and_parties() -> dict:
    turnout = pd.read_csv(PROCESSED / "idea_turnout_clean.csv")
    fr_turnout = turnout.loc[turnout.ISO3.eq("FRA")].copy()
    fr_turnout.to_csv(PROCESSED / "idea_france_elections.csv", index=False)
    fig, ax = plt.subplots(figsize=(9, 4))
    for kind, group in fr_turnout.groupby("Election Type"):
        ax.scatter(group.election_year, group.registered_turnout_pct, s=40, alpha=0.8, label=kind)
    ax.set(xlabel="Election year", ylabel="Registered-voter turnout (%)",
           title="French turnout in the IDEA download")
    ax.legend(frameon=False)
    ax.grid(alpha=0.2)
    save_plot("france_idea_turnout.png")

    manifest = pd.read_csv(RAW / "manifesto_2026a/MPDataset_MPDS2026a.csv", low_memory=False)
    fr_manifest = manifest.loc[manifest.countryname.eq("France"),
                               ["countryname", "date", "edate", "party", "partyname",
                                "rile", "pervote", "total", "welfare", "markeco", "planeco"]].copy()
    fr_manifest["year"] = pd.to_numeric(fr_manifest.date, errors="coerce") // 100
    fr_manifest.to_csv(PROCESSED / "manifesto_france_programs.csv", index=False)
    recent = fr_manifest.loc[fr_manifest.year.ge(2000) & fr_manifest.rile.notna()]
    fig, ax = plt.subplots(figsize=(10, 4.5))
    for party, group in recent.groupby("partyname"):
        if len(group) < 2 or group.pervote.max() < 5:
            continue
        ax.plot(group.year, group.rile, marker=".", label=party)
    ax.axhline(0, color="black", linewidth=0.7)
    ax.set(xlabel="Manifesto year", ylabel="RILE index",
           title="Selected French party manifestos, 2000–2022")
    ax.legend(fontsize=7, ncol=2, frameon=False)
    save_plot("france_manifesto_rile.png")

    ches = pd.read_csv(RAW / "ches/1999-2024_CHES_dataset_meansV2.csv", low_memory=False)
    fr_ches = ches.loc[ches.country.eq(6), ["year", "party_id", "party", "cmp_id", "vote",
                                         "lrgen", "lrecon", "galtan", "eu_position"]].copy()
    fr_ches.to_csv(PROCESSED / "ches_france_party_waves.csv", index=False)
    pop = pd.read_csv(RAW / "The PopuList 4.0.csv", sep=";", low_memory=False)
    fr_pop = pop.loc[pop.country_name.eq("France"), ["party_name", "party_name_short",
                 "party_name_english", "populist", "farright", "farleft", "eurosceptic",
                 "partyfacts_id", "parlgov_id"]].copy()
    fr_pop.to_csv(PROCESSED / "populist_france_party_labels.csv", index=False)
    pg_party = pd.read_csv(RAW / "parlgov_2024/view_party.tab", sep="\t")
    pg_fr = pg_party.loc[pg_party.country_name_short.eq("FRA")]
    pg_ids = set(pg_fr.party_id.dropna().astype(int))
    fr_pop["parlgov_id_found"] = fr_pop.parlgov_id.isin(pg_ids)
    fr_pop.to_csv(OUT / "france_populist_parlgov_id_check.csv", index=False)
    return dict(turnout=fr_turnout, manifesto=fr_manifest, ches=fr_ches, populist=fr_pop)


def cabinets() -> dict:
    pg = pd.read_csv(RAW / "parlgov_2024/view_cabinet.tab", sep="\t", low_memory=False)
    base = pg.loc[pg.country_name_short.eq("FRA")].sort_values("start_date")
    # A cabinet appears once for each party. Keep one row per cabinet ID.
    fr = base.drop_duplicates("cabinet_id")[["cabinet_id", "cabinet_name", "start_date",
             "election_date", "caretaker", "election_seats_total"]].copy()
    fr["start_date"] = pd.to_datetime(fr.start_date)
    fr = fr.sort_values("start_date")
    fr["next_cabinet_start"] = fr.start_date.shift(-1)
    fr["days_until_next_cabinet"] = (fr.next_cabinet_start - fr.start_date).dt.days
    fr.to_csv(PROCESSED / "parlgov_france_cabinets.csv", index=False)

    with ZipFile(RAW / "ppeg_2025v1/ppeg_gov_2025v1.zip") as archive:
        ppeg = pd.read_csv(archive.open("ppeg_gov_2025v1.csv"), low_memory=False)
    pg_fr = ppeg.loc[ppeg.iso3c.eq("FRA")].copy()
    gov = pg_fr.drop_duplicates(["iso3c", "idate"])[["iso3c", "edate", "idate", "pm",
                                "tog", "rft", "gov_seat", "ngovparties"]].copy()
    gov["idate"] = pd.to_datetime(gov.idate)
    gov = gov.sort_values("idate")
    gov["next_cabinet_start"] = gov.idate.shift(-1)
    gov["days_until_next_cabinet"] = (gov.next_cabinet_start - gov.idate).dt.days
    gov.to_csv(PROCESSED / "ppeg_france_governments.csv", index=False)
    fig, ax = plt.subplots(figsize=(9, 4))
    years = gov.loc[gov.idate.dt.year.ge(2000), "idate"].dt.year.value_counts().sort_index()
    ax.bar(years.index, years.values, color="#75638f")
    ax.set(xlabel="Inauguration year", ylabel="PPEG government records",
           title="Government inaugurations in France since 2000")
    save_plot("france_ppeg_government_inaugurations.png")
    return dict(parlgov=fr, ppeg=gov)


def write_report(inventory_df: pd.DataFrame, trend: pd.DataFrame,
                 evs: pd.DataFrame) -> None:
    fr_trend = trend.loc[trend.country_code.eq("FR")]
    latest = fr_trend.loc[fr_trend.wave.eq("105.2")]
    trust = {row.institution: row.trust_pct for row in latest.itertuples()}
    crosswalk = pd.read_csv(OUT / "france_party_crosswalk_candidates.csv")
    matched_vote = crosswalk.loc[crosswalk.ches_party_id.notna(), "vote_pct"].sum()
    lines = [
        "# Where the project stands",
        "",
        "This is a first data prototype for the Democracy Stress Test. It describes what we have and what we can safely say about France. It does not yet calculate how France would respond to a future shock.",
        "",
        "## What is ready",
        "",
        f"- We have {len(inventory_df):,} original files. Every file is listed in `raw_file_inventory.csv`. Of the Our World in Data download we keep only the two Freedom House tables; they are checked in `owid_file_audit.csv`.",
        "- We can chart France's democracy scores, election turnout, party positions, government changes and public trust. The figures are in `figures/`.",
        f"- Eurobarometer gives a trust trend from 2005 to 2026. In its latest French wave, {trust['Political parties']:.0f}% tended to trust political parties, {trust['National government']:.0f}% the national government and {trust['National parliament']:.0f}% parliament.",
        "- The 2026 CEVIPOF report also gives French trust figures. We copied seven published values into a small table and recorded the question and PDF page for each.",
        f"- The EVS/WVS survey gives answers from people in {evs.country_code.nunique()} countries. The French survey has 1,870 respondents in 2018.",
        "",
        "## What needs care",
        "",
        f"- Only {matched_vote:.1f}% of the French 2024 vote links directly to a CHES party by ID. Several large election rows are alliances. A person must check their member parties before we combine votes and party positions.",
        "- The EVS, Eurobarometer and CEVIPOF trust questions differ. Read each survey on its own terms; their percentages are not one continuous series.",
        "- Many IDEA election dates are January 1 placeholders. Three reported turnout rates exceed 100%. The working table flags these values and keeps the originals.",
        "- The ESS folder has questionnaires but no survey responses.",
        "",
        "## Best next step",
        "",
        "Settle the two radical-vote judgment calls shown in `notebooks/03_radical_voting.ipynb` (counting Les Républicains, splitting the 2024 New Popular Front), then decide how effects around the reference episodes will be measured. Keep this report as the starting picture, not as a stress-test result.",
        "",
        "For exact rows, source cells and further checks, use `source_profiles.csv`, `quality_issues.csv` and the tables in `data/processed/`.",
    ]
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    files = inventory()
    trend = eurobarometer_trend()
    cevi = cevipof_published()
    evs = evs_country_trust()
    elections_and_parties()
    cabinets()
    write_report(files, trend, evs)
    print(f"Inventoried {len(files)} raw files; extracted {len(trend)} Eurobarometer observations; "
          f"saved {len(cevi)} CEVIPOF published values.")


if __name__ == "__main__":
    main()
