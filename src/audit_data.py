"""Internal data checks used by run_analysis.py; original downloads stay untouched."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from zipfile import ZipFile

os.environ.setdefault(
    "MPLCONFIGDIR", str(Path(__file__).resolve().parents[1] / "outputs" / ".matplotlib")
)
Path(os.environ["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from openpyxl import load_workbook
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
OUT = ROOT / "outputs" / "data_audit"
FIG = OUT / "figures"
for folder in (PROCESSED, OUT, FIG):
    folder.mkdir(parents=True, exist_ok=True)
logging.getLogger("pypdf").setLevel(logging.ERROR)

profiles: list[dict] = []
issues: list[dict] = []


def issue(source: str, severity: str, finding: str, evidence: str, action: str) -> None:
    issues.append(
        dict(source=source, severity=severity, finding=finding, evidence=evidence, action=action)
    )


def profile(
    source: str,
    df: pd.DataFrame,
    grain: str,
    keys: list[str] | None = None,
    france_mask: pd.Series | None = None,
    year: pd.Series | None = None,
    note: str = "",
) -> None:
    duplicates = int(df.duplicated(keys).sum()) if keys else np.nan
    missing_key = int(df[keys].isna().any(axis=1).sum()) if keys else np.nan
    yrs = pd.to_numeric(year, errors="coerce") if year is not None else pd.Series(dtype=float)
    profiles.append(
        dict(
            source=source,
            grain=grain,
            rows=len(df),
            columns=len(df.columns),
            france_rows=int(france_mask.sum()) if france_mask is not None else np.nan,
            first_year=int(yrs.min()) if yrs.notna().any() else np.nan,
            last_year=int(yrs.max()) if yrs.notna().any() else np.nan,
            duplicate_key_rows=duplicates,
            missing_key_rows=missing_key,
            note=note,
        )
    )
    if keys and duplicates:
        issue(source, "review", "Some rows share the proposed identifier",
              f"{duplicates:,} rows repeat {keys}",
              "Open these rows and check which field distinguishes them before removing anything.")
    if keys and missing_key:
        issue(source, "review", "Some rows lack an identifier",
              f"{missing_key:,} rows have a blank field in {keys}",
              "Keep these rows and find out why the identifier is missing.")


def eurostat_long(path: Path) -> pd.DataFrame:
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["id"][-2:] == ["geo", "time"]
    assert all(n == 1 for n in data["size"][:-2])
    geo_index = data["dimension"]["geo"]["category"]["index"]
    year_index = data["dimension"]["time"]["category"]["index"]
    inverse_geo = {i: geo for geo, i in geo_index.items()}
    inverse_year = {i: int(year) for year, i in year_index.items()}
    n_years = data["size"][-1]
    rows = []
    for flat_key, value in data["value"].items():
        position = int(flat_key)
        geo = inverse_geo[position // n_years]
        year = inverse_year[position % n_years]
        rows.append((geo, year, value, data.get("status", {}).get(flat_key, "")))
    return pd.DataFrame(rows, columns=["geo", "year", path.stem, path.stem + "_flag"])


def plot_save(name: str) -> None:
    plt.tight_layout()
    plt.savefig(FIG / name, dpi=160, bbox_inches="tight")
    plt.close()


def main() -> None:
    # V-Dem: selected measures from the original country-year archive.
    vdem_cols = [
        "country_name", "country_text_id", "year", "v2x_polyarchy",
        "v2x_polyarchy_codelow", "v2x_polyarchy_codehigh", "v2x_libdem",
        "v2x_libdem_codelow", "v2x_libdem_codehigh",
    ]
    with ZipFile(RAW / "V-Dem-CY-FullOthers-v16_csv.zip") as archive:
        with archive.open("V-Dem-CY-Full+Others-v16.csv") as stream:
            chunks = pd.read_csv(stream, usecols=vdem_cols, chunksize=2000)
            vdem = pd.concat(
                [c.loc[c.year.between(2000, 2025)] for c in chunks], ignore_index=True
            )
    profile("V-Dem v16", vdem, "country-year", ["country_text_id", "year"],
            vdem.country_text_id.eq("FRA"), vdem.year)
    for metric in ("v2x_polyarchy", "v2x_libdem"):
        bad = vdem[metric].notna() & (
            vdem[metric].lt(vdem[metric + "_codelow"])
            | vdem[metric].gt(vdem[metric + "_codehigh"])
        )
        if bad.any():
            issue("V-Dem v16", "review", "Estimate outside coding interval",
                  f"{int(bad.sum())} rows for {metric}", "Check codebook and release notes.")
    vdem.to_csv(PROCESSED / "vdem_country_year_core_v16.csv", index=False)

    # OWID: only the two Freedom House tables are kept; index.csv lists the original 2026 download.
    owid = RAW / "owid_democracy"
    owid_rows = []
    for folder in ("charts", "explorer"):
        for path in sorted((owid / folder).glob("*.csv")):
            try:
                df = pd.read_csv(path, low_memory=False)
                cols = set(df.columns)
                key = ["Code", "Year"] if {"Code", "Year"} <= cols else None
                dup = int(df.loc[df.Code.notna()].duplicated(key).sum()) if key else np.nan
                owid_rows.append(dict(file=str(path.relative_to(owid)), rows=len(df),
                                      columns=len(df.columns), duplicate_code_year=dup,
                                      france_rows=int(df.Code.eq("FRA").sum()) if "Code" in df else np.nan,
                                      error=""))
            except Exception as exc:
                owid_rows.append(dict(file=str(path.relative_to(owid)), rows=np.nan,
                                      columns=np.nan, duplicate_code_year=np.nan,
                                      france_rows=np.nan, error=str(exc)))
    owid_files = pd.DataFrame(owid_rows)
    owid_files.to_csv(OUT / "owid_file_audit.csv", index=False)
    failed = int(owid_files.error.ne("").sum())
    profiles.append(dict(source="OWID democracy", grain="chart/explorer export",
                         rows=int(owid_files.rows.sum()), columns=np.nan,
                         france_rows=int(owid_files.france_rows.sum()), first_year=np.nan,
                         last_year=np.nan, duplicate_key_rows=int(owid_files.duplicate_code_year.sum()),
                         missing_key_rows=np.nan,
                         note=f"{len(owid_files)} CSV files; {failed} read errors"))
    if failed:
        issue("OWID democracy", "error", "Unreadable CSV files",
              f"{failed} CSVs failed to parse", "Inspect owid_file_audit.csv.")
    fh_rights = pd.read_csv(owid / "explorer/073_freedom-house__freedom__political-rights-score.csv")
    fh_liberties = pd.read_csv(owid / "explorer/075_freedom-house__freedom__civil-liberties-score.csv")
    aggregate_rows = int(fh_rights.Code.isna().sum() + fh_liberties.Code.isna().sum())
    if aggregate_rows:
        issue("OWID Freedom House", "cleaning", "Summary rows have no country code",
              f"{aggregate_rows} rows across the political-rights and civil-liberties exports",
              "Leave them in the raw files, and use only coded countries in the country-year table.")
    fh = (
        fh_rights.loc[fh_rights.Code.notna(), ["Entity", "Code", "Year", "Political rights score"]]
        .merge(fh_liberties.loc[fh_liberties.Code.notna(),
                               ["Code", "Year", "Civil liberties score"]],
               on=["Code", "Year"], how="inner", validate="one_to_one")
        .rename(columns={"Entity": "country_name", "Code": "iso3", "Year": "year",
                         "Political rights score": "political_rights",
                         "Civil liberties score": "civil_liberties"})
    )
    fh["freedom_score"] = fh.political_rights + fh.civil_liberties
    fh.to_csv(PROCESSED / "freedom_house_country_year_owid.csv", index=False)

    # ParlGov and PPEG: keep source-specific identifiers and grains.
    for name, keys, year_col in [
        ("view_party", ["country_id", "party_id"], None),
        ("view_election", ["election_id", "party_id"], "election_date"),
        ("view_cabinet", ["cabinet_id", "party_id"], "start_date"),
    ]:
        df = pd.read_csv(RAW / "parlgov_2024" / f"{name}.tab", sep="\t", low_memory=False)
        actual_keys = [k for k in keys if k in df]
        date = pd.to_datetime(df[year_col], errors="coerce").dt.year if year_col else None
        profile("ParlGov " + name, df, name.replace("view_", ""), actual_keys,
                df.country_name_short.astype(str).str.strip('"').eq("FRA"),
                date, "2024 release")
    ppeg_tables = {}
    for kind, key in [
        ("parl", ["iso3c", "edate", "party_id"]),
        ("pres", ["iso3c", "edate", "candidate"]),
        ("gov", ["iso3c", "idate", "party_id"]),
        ("comb", ["iso3c", "edate", "idate", "party_id"]),
    ]:
        with ZipFile(RAW / "ppeg_2025v1" / f"ppeg_{kind}_2025v1.zip") as archive:
            with archive.open(f"ppeg_{kind}_2025v1.csv") as stream:
                df = pd.read_csv(stream, low_memory=False)
        ppeg_tables[kind] = df
        year = pd.to_datetime(df.edate, errors="coerce").dt.year
        profile("PPEG " + kind, df, kind, key, df.iso3c.eq("FRA"), year,
                "Combined archive overlaps the component archives" if kind == "comb" else "")
    parl = ppeg_tables["parl"]
    fr_parl = parl.loc[parl.iso3c.eq("FRA")].copy()
    latest = fr_parl.edate.max()
    latest_parl = fr_parl.loc[fr_parl.edate.eq(latest)].copy()
    latest_parl["vote_pct"] = 100 * latest_parl.v_share
    latest_parl["seat_pct"] = 100 * latest_parl.s_share
    latest_parl.to_csv(PROCESSED / "ppeg_france_latest_parliamentary.csv", index=False)
    alliance_rows = int(latest_parl.alliance.notna().sum())
    issue("PPEG + CHES", "join", "Election alliances and CHES parties are different units",
          f"France {latest}: {alliance_rows}/{len(latest_parl)} PPEG rows have an alliance label",
          "Check alliance membership before linking vote shares to CHES party positions.")
    if not np.isclose(latest_parl.v_share.sum(), 1.0, atol=0.01):
        issue("PPEG parl", "review", "Vote shares do not sum to 100%",
              f"France {latest}: {latest_parl.v_share.sum():.3f}",
              "Check exclusions, tiers, and alliance conventions.")

    # Turnout: parse source strings without changing the source workbook.
    idea = pd.read_excel(RAW / "idea_export_voter_turnout_database_region.xlsx", sheet_name="All")
    turnout = idea.copy()
    turnout["election_date_reported"] = pd.to_datetime(turnout["Year"], errors="coerce")
    turnout["election_year"] = turnout.election_date_reported.dt.year
    suspected_year_only = turnout.election_date_reported.dt.month.eq(1) & turnout.election_date_reported.dt.day.eq(1)
    turnout["election_date_precision"] = np.where(
        suspected_year_only, "year_only_or_unverified", "day_reported"
    )
    turnout["election_date"] = turnout.election_date_reported.mask(suspected_year_only)
    issue("IDEA turnout", "date", "Many election dates look like year placeholders",
          f"{int(suspected_year_only.sum()):,}/{len(turnout):,} reported dates are January 1; "
          f"{int((suspected_year_only & turnout.ISO3.eq('FRA')).sum())} France rows",
          "Use the year for now. Check another election source before assigning an exact day.")
    for source_col, target in [
        ("Voter Turnout", "registered_turnout_pct"),
        ("VAP Turnout", "vap_turnout_pct"),
        ("Invalid votes", "invalid_vote_pct"),
    ]:
        turnout[target] = pd.to_numeric(
            turnout[source_col].astype("string").str.replace("%", "", regex=False)
            .str.replace(",", "", regex=False), errors="coerce"
        )
    for source_col, target in [
        ("Total vote", "total_vote"), ("Registration", "registered_voters"),
        ("Voting age population", "voting_age_population"),
    ]:
        turnout[target] = pd.to_numeric(
            turnout[source_col].astype("string").str.replace(",", "", regex=False),
            errors="coerce",
        )
    invalid_pct = turnout.registered_turnout_pct.notna() & ~turnout.registered_turnout_pct.between(0, 100)
    if invalid_pct.any():
        issue("IDEA turnout", "error", "Three reported turnout rates exceed 100%",
              f"{int(invalid_pct.sum())} rows: Bahamas 1972 and Bolivia 1978 in this snapshot",
              "Keep the reported rates for reference; leave the validated rates blank.")
    turnout["registered_turnout_pct_reported"] = turnout["registered_turnout_pct"]
    turnout["turnout_quality_flag"] = np.where(
        invalid_pct, "reported_registered_turnout_over_100", ""
    )
    turnout.loc[invalid_pct, "registered_turnout_pct"] = np.nan
    profile("IDEA turnout", turnout, "country-election",
            ["ISO3", "Election Type", "election_date_reported"], turnout.ISO3.eq("FRA"),
            turnout.election_year)
    turnout[["Country", "ISO2", "ISO3", "Election Type", "election_year",
             "election_date_reported", "election_date", "election_date_precision",
             "registered_turnout_pct", "registered_turnout_pct_reported",
             "turnout_quality_flag", "vap_turnout_pct", "invalid_vote_pct",
             "total_vote", "registered_voters", "voting_age_population"]].to_csv(
        PROCESSED / "idea_turnout_clean.csv", index=False
    )

    # Party classifications and positions: clean values but defer crosswalk decisions.
    pop = pd.read_csv(RAW / "The PopuList 4.0.csv", sep=";", low_memory=False)
    profile("PopuList 4.0", pop, "party", ["country_name", "party_name"],
            pop.country_name.eq("France"), None)
    ches = pd.read_csv(RAW / "ches/1999-2024_CHES_dataset_meansV2.csv", low_memory=False)
    ches24 = pd.read_csv(RAW / "ches/CHES_2024_final_v2.csv", low_memory=False)
    profile("CHES trend", ches, "party-wave", ["year", "country", "party_id"],
            ches.country.eq(6), ches.year, "France country code 6 verified in 2024 codebook")
    profile("CHES 2024", ches24, "party-wave", ["country", "party_id"],
            ches24.country.eq(6), pd.Series(2024, index=ches24.index))
    manifesto = pd.read_csv(RAW / "manifesto_2026a/MPDataset_MPDS2026a.csv", low_memory=False)
    parties_long = pd.read_csv(RAW / "manifesto_2026a/parties_long_MPDataset_MPDS2026a.csv", low_memory=False)
    profile("Manifesto MPDS 2026a", manifesto, "party-manifesto",
            ["country", "party", "date"], manifesto.countryname.eq("France"),
            pd.to_numeric(manifesto.date, errors="coerce") // 100)
    profile("Manifesto party list", parties_long, "party-name period",
            ["country", "party", "year_min", "year_max"],
            parties_long.countryname.eq("France"), parties_long.year_max)
    fr_manifesto = manifesto.loc[manifesto.countryname.eq("France")]
    fr_manifesto_last = int((pd.to_numeric(fr_manifesto.date, errors="coerce") // 100).max())
    if fr_manifesto_last < int(str(latest)[:4]):
        issue("Manifesto + PPEG", "coverage", "France's newest manifesto predates the 2024 election",
              f"Latest France manifesto year {fr_manifesto_last}; PPEG election {latest}",
              "If using a 2022 manifesto for 2024, label it as earlier information.")
    crosswalk = (
        latest_parl[["iso3c", "edate", "party_id", "pname_en", "cmp", "vote_pct", "alliance"]]
        .merge(
            ches.loc[(ches.country.eq(6)) & (ches.year.eq(2024)) & ches.cmp_id.notna(),
                     ["party_id", "party", "cmp_id", "lrgen", "lrecon", "galtan"]]
            .rename(columns={"party_id": "ches_party_id"}),
            left_on="cmp", right_on="cmp_id", how="left", validate="many_to_one"
        )
    )
    crosswalk["match_status"] = np.where(
        crosswalk.ches_party_id.notna(), "CMP ID match; review", "unmatched"
    )
    crosswalk.to_csv(OUT / "france_party_crosswalk_candidates.csv", index=False)
    matched_vote = crosswalk.loc[crosswalk.ches_party_id.notna(), "vote_pct"].sum()
    issue("PPEG + CHES", "join", "Most 2024 votes have no direct CHES match",
          f"CMP IDs directly match {matched_vote:.1f}% of France {latest} vote",
          "Review the alliance rows and missing IDs before using a merged party table.")

    # EVS/WVS: distinguish valid 1–4 confidence codes from negative missing codes.
    evs_path = RAW / "evs_wvs_joint_2017_2022_v5/F00012158-EVS_WVS_Joint_Csv_v5_0.zip"  # pandas reads the CSV inside
    evs_cols = ["uniqid", "cntry_AN", "year", "gwght", "E069_07", "E069_11", "E069_12"]
    evs = pd.read_csv(evs_path, usecols=evs_cols, low_memory=False)
    profile("EVS/WVS joint v5", evs, "respondent", ["uniqid"],
            evs.cntry_AN.eq("FR"), evs.year, "Selected audit columns; source CSV has 231")
    france_evs = evs.loc[evs.cntry_AN.eq("FR")]
    trust = []
    for column, institution in [
        ("E069_07", "Parliament"), ("E069_11", "Government"),
        ("E069_12", "Political parties"),
    ]:
        valid = france_evs.loc[france_evs[column].isin([1, 2, 3, 4]) & france_evs.gwght.gt(0)]
        trust.append(dict(source="EVS/WVS", year=2018, institution=institution,
                          weighted_confident_pct=100 * valid.loc[valid[column].isin([1, 2]), "gwght"].sum()
                          / valid.gwght.sum(), valid_n=len(valid),
                          missing_n=len(france_evs) - len(valid)))
    evs_trust = pd.DataFrame(trust)
    evs_trust.to_csv(PROCESSED / "evs_france_2018_trust_summary.csv", index=False)

    # Eurobarometer: record aggregate cells and survey-wave grain.
    eb_dir = RAW / "eurobarometer_std105_2026"
    eb_workbook = load_workbook(eb_dir / "STD105_volume_AP.xlsx", read_only=True, data_only=True)
    eb_rows = []
    for sheet, row, indicator in [
        ("QA6_2", 13, "Trust in political parties"),
        ("QA6_10", 13, "Trust in national government"),
        ("QA6_11", 13, "Trust in national parliament"),
        ("SD18a", 23, "Satisfied with democracy in France"),
    ]:
        ws = eb_workbook[sheet]
        for column, wave in [("AA", "Autumn 2025"), ("AB", "Spring 2026")]:
            eb_rows.append(dict(source="Eurobarometer 105.2", country="France",
                                wave=wave, indicator=indicator, share_pct=100 * ws[f"{column}{row}"].value,
                                source_cell=f"{sheet}!{column}{row}"))
    n_sheets = len(eb_workbook.sheetnames)
    eb_workbook.close()
    eb = pd.DataFrame(eb_rows)
    eb.to_csv(PROCESSED / "eurobarometer_france_trust_summary.csv", index=False)
    profiles.append(dict(source="Eurobarometer 105.2", grain="country-question-wave aggregate",
                         rows=len(eb), columns=len(eb.columns), france_rows=len(eb),
                         first_year=2025, last_year=2026, duplicate_key_rows=0,
                         missing_key_rows=0, note=f"{n_sheets} sheets in comparison workbook; 8 selected cells audited"))
    issue("EVS/WVS + Eurobarometer", "comparability", "The trust surveys ask different questions",
          "EVS 2018 respondent confidence; EB 2025/26 published trust percentages",
          "Keep the results separate while checking wording, response bases and weights.")

    # Eurostat: decode every nonmissing observation in each requested series.
    macro_files = [
        "nama_10_gdp_real_growth.json", "une_rt_a_unemployment.json",
        "prc_hicp_aind_inflation.json", "gov_10dd_edpt1_debt_gdp.json",
    ]
    macro = None
    for filename in macro_files:
        part = eurostat_long(RAW / "eurostat_macro_annual" / filename)
        profile("Eurostat " + filename.removesuffix(".json"), part, "geo-year",
                ["geo", "year"], part.geo.eq("FR"), part.year)
        macro = part if macro is None else macro.merge(part, on=["geo", "year"], how="outer",
                                                       validate="one_to_one")
    # une_rt_a starts in 2009 for most countries. Fill earlier years only from Eurostat's
    # historical series (une_rt_a_h, 1992-2020, same age, sex and unit), and record the source.
    hist = eurostat_long(RAW / "eurostat_macro_annual" / "une_rt_a_h_unemployment_historical.json")
    macro = macro.merge(hist, on=["geo", "year"], how="outer", validate="one_to_one")
    col, hist_col = "une_rt_a_unemployment", "une_rt_a_h_unemployment_historical"
    current = macro[col].notna()
    macro[col + "_source"] = np.where(current, "une_rt_a", np.where(macro[hist_col].notna(), "une_rt_a_h", ""))
    macro[col] = macro[col].fillna(macro[hist_col])
    filled = int((~current & macro[hist_col].notna()).sum())
    both = macro[current & macro[hist_col].notna()]
    gap = (both[col] - both[hist_col]).abs().max()
    macro = macro.drop(columns=[hist_col, hist_col + "_flag"])
    issue("Eurostat unemployment", "coverage", "Current series starts in 2009 for most countries",
          f"{filled} country-years filled from the historical series une_rt_a_h; where both exist they differ by at most {gap:.1f} points",
          "Read the source column; treat 2008-09 changes as approximate because of the series break.")
    macro.to_csv(PROCESSED / "eurostat_macro_country_year.csv", index=False)

    # Documentation-only sources are explicitly not treated as data tables.
    cevi = RAW / "cevipof_bcp_2026/Barometre_confiance_CEVIPOFVague17_fev2026_vd1.pdf"
    pages = len(PdfReader(cevi).pages)
    profiles.append(dict(source="CEVIPOF wave 17", grain="published PDF aggregates",
                         rows=np.nan, columns=np.nan, france_rows=np.nan, first_year=2026,
                         last_year=2026, duplicate_key_rows=np.nan, missing_key_rows=np.nan,
                         note=f"{pages} pages; no respondent file"))
    profiles.append(dict(source="ESS", grain="documentation only", rows=np.nan,
                         columns=np.nan, france_rows=np.nan, first_year=np.nan,
                         last_year=np.nan, duplicate_key_rows=np.nan, missing_key_rows=np.nan,
                         note="Questionnaire and weighting guide only; no respondent file"))
    issue("ESS", "access", "We have ESS guidance but no survey responses",
          "The ESS folder contains documentation only",
          "Sign in to the ESS portal and download a France extract when ready.")
    issue("CEVIPOF", "format", "CEVIPOF provides published results here",
          f"Wave 17 report has {pages} pages but no microdata",
          "Cite the report page and question for each figure taken from it.")

    # Figures: source-specific scales and observation units.
    fr_vdem = vdem.loc[vdem.country_text_id.eq("FRA")].sort_values("year")
    fr_fh = fh.loc[fh.iso3.eq("FRA")].sort_values("year")
    fig, ax = plt.subplots(2, 1, figsize=(9, 6), sharex=True)
    for metric, label, color in [
        ("v2x_polyarchy", "Electoral democracy", "#175a82"),
        ("v2x_libdem", "Liberal democracy", "#a65c25"),
    ]:
        ax[0].plot(fr_vdem.year, fr_vdem[metric], label=label, color=color)
        ax[0].fill_between(fr_vdem.year, fr_vdem[metric + "_codelow"],
                           fr_vdem[metric + "_codehigh"], color=color, alpha=0.15)
    ax[0].set(ylabel="V-Dem index (0–1)", title="How democracy scores have changed in France")
    ax[0].legend(frameon=False)
    ax[1].plot(fr_fh.year, fr_fh.freedom_score, color="#4b6b46")
    ax[1].set(xlabel="Year", ylabel="Freedom House score (0–100)")
    ax[1].grid(alpha=0.2)
    plot_save("france_democracy_indices.png")

    fig, ax = plt.subplots(2, 1, figsize=(9, 6), sharex=True)
    for geo, label in [("FR", "France"), ("ES", "Spain"), ("EL", "Greece"), ("PT", "Portugal")]:
        sub = macro.loc[macro.geo.eq(geo) & macro.year.between(2005, 2016)].sort_values("year")
        ax[0].plot(sub.year, sub.nama_10_gdp_real_growth, marker=".", label=label)
        ax[1].plot(sub.year, sub.une_rt_a_unemployment, marker=".", label=label)
    ax[0].axhline(0, color="black", linewidth=0.6)
    ax[0].set(ylabel="Real GDP growth (%)", title="The downturn and its aftermath, 2005–2016")
    ax[1].set(xlabel="Year", ylabel="Unemployment (% of labour force)")
    ax[0].legend(ncol=4, frameon=False)
    plot_save("financial_crisis_macro.png")

    top = latest_parl.sort_values("vote_pct", ascending=False).head(10).iloc[::-1]
    fig, ax = plt.subplots(figsize=(9, 5))
    y = np.arange(len(top))
    ax.barh(y - 0.18, top.vote_pct, height=0.36, label="Vote", color="#2775a1")
    ax.barh(y + 0.18, top.seat_pct, height=0.36, label="Seats", color="#d28b43")
    ax.set_yticks(y, top.pname_en)
    ax.set(xlabel="Share (%)", title=f"France 2024: votes and seats by party or alliance (PPEG)")
    ax.legend(frameon=False)
    plot_save("france_ppeg_votes_seats.png")

    fr_ches = ches.loc[ches.country.eq(6) & ches.year.eq(2024)].copy()
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(fr_ches.lrecon, fr_ches.galtan,
               s=np.maximum(fr_ches.vote.fillna(0), 1) * 22,
               alpha=0.65, color="#775899")
    for row in fr_ches.itertuples():
        ax.annotate(str(row.party), (row.lrecon, row.galtan), xytext=(4, 4),
                    textcoords="offset points", fontsize=8)
    ax.set(xlim=(0, 10), ylim=(0, 10), xlabel="Economic left–right (CHES)",
           ylabel="GAL–TAN (CHES)",
           title="Where French parties sit in CHES 2024 (size: CHES vote %)")
    ax.grid(alpha=0.2)
    plot_save("france_ches_party_positions.png")

    eb_plot = eb.pivot(index="indicator", columns="wave", values="share_pct")
    fig, ax = plt.subplots(figsize=(9, 4.5))
    y = np.arange(len(eb_plot))
    ax.barh(y - 0.18, eb_plot["Autumn 2025"], height=0.36, label="Autumn 2025")
    ax.barh(y + 0.18, eb_plot["Spring 2026"], height=0.36, label="Spring 2026")
    ax.set_yticks(y, eb_plot.index)
    ax.set(xlabel="Published weighted share (%)",
           title="French views in two Eurobarometer waves")
    ax.legend(frameon=False)
    plot_save("france_eurobarometer_trust.png")

    # Presence by observation year is useful for planning joins, but a mark is
    # not evidence that the source was measured continuously through that year.
    coverage_years = np.arange(2000, 2027)
    observed = {
        "V-Dem country-year": set(fr_vdem.year),
        "Freedom House country-year": set(fr_fh.year),
        "Eurostat GDP": set(macro.loc[macro.geo.eq("FR"), "year"]),
        "PPEG parliamentary election": set(pd.to_datetime(fr_parl.edate).dt.year),
        "IDEA election": set(turnout.loc[turnout.ISO3.eq("FRA"), "election_year"].dropna().astype(int)),
        "CHES party wave": set(ches.loc[ches.country.eq(6), "year"]),
        "Manifesto program": set((pd.to_numeric(fr_manifesto.date) // 100).astype(int)),
        "EVS respondent survey": {2018},
        "Eurobarometer aggregate": {2025, 2026},
    }
    coverage = np.array(
        [[int(year in years) for year in coverage_years] for years in observed.values()]
    )
    fig, ax = plt.subplots(figsize=(11, 4.5))
    from matplotlib.colors import ListedColormap
    ax.imshow(coverage, aspect="auto", interpolation="nearest",
              cmap=ListedColormap(["#f1f1f1", "#245c80"]), vmin=0, vmax=1)
    ax.set_yticks(np.arange(len(observed)), list(observed))
    ax.set_xticks(np.arange(0, len(coverage_years), 2), coverage_years[::2])
    ax.set(xlabel="Observation year", title="When we have data for France, 2000–2026")
    ax.text(0, -0.18, "Mark = at least one observation; elections and surveys are not annual series.",
            transform=ax.transAxes, fontsize=8, va="top")
    plot_save("france_source_coverage.png")

    # Save detailed checks. The workbench writes the short reader-facing report.
    prof = pd.DataFrame(profiles)
    iss = pd.DataFrame(issues)
    prof.to_csv(OUT / "source_profiles.csv", index=False)
    iss.to_csv(OUT / "quality_issues.csv", index=False)
    print(f"Checked {len(prof)} source tables or families and {len(owid_files)} OWID CSVs.")
    print(f"Saved {len(iss)} review notes and the first set of charts.")


if __name__ == "__main__":
    main()
