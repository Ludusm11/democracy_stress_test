"""Prepare a small set of chart data for the local website MVP."""

from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZipFile

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw"
PROCESSED = ROOT / "data/processed"
OUT = ROOT / "website/data"
OUT.mkdir(parents=True, exist_ok=True)

COUNTRIES = pd.read_csv(PROCESSED / "idea_turnout_clean.csv", usecols=["Country", "ISO2", "ISO3"])
CODE_NAMES = {}
for row in COUNTRIES.drop_duplicates("Country").itertuples(index=False):
    for code in (row.ISO2, row.ISO3):
        if pd.notna(code):
            CODE_NAMES[str(code)] = str(row.Country)
CODE_NAMES.update({"EL": "Greece", "EU": "European Union", "D-W": "West Germany", "D-E": "East Germany", "DEW": "West Germany", "DEE": "East Germany"})

# Eurostat aggregates: give the current EU-27 the plain name so it can be compared.
EUROSTAT_AGGREGATES = {
    "EU27_2020": "European Union", "EU": "European Union (changing membership)",
    "EU28": "EU-28 (to 2019)", "EA20": "Euro area (20)", "EA": "Euro area (changing membership)",
}

SOURCE_URLS = {
    "vdem": "https://v-dem.net/data/the-v-dem-dataset/",
    "freedom": "https://ourworldindata.org/democracy",
    "turnout": "https://www.idea.int/data-tools/data/voter-turnout-database",
    "economy": "https://ec.europa.eu/eurostat/",
    "eurobarometer": "https://europa.eu/eurobarometer/surveys/detail/3613",
    "evs": "https://www.worldvaluessurvey.org/WVSEVSjoint2017.jsp",
    "ches": "https://www.chesdata.eu/",
    "ppeg": "https://ppeg.wzb.eu/",
}

CHES_NAMES = {
    1: "Belgium", 2: "Denmark", 3: "Germany", 4: "Greece", 5: "Spain", 6: "France",
    7: "Ireland", 8: "Italy", 10: "Netherlands", 11: "United Kingdom", 12: "Portugal",
    13: "Austria", 14: "Finland", 16: "Sweden", 20: "Bulgaria", 21: "Czech Republic",
    22: "Estonia", 23: "Hungary", 24: "Latvia", 25: "Lithuania", 26: "Poland",
    27: "Romania", 28: "Slovakia", 29: "Slovenia", 31: "Croatia", 37: "Malta",
    38: "Luxembourg", 40: "Cyprus",
}


def measure(key: str, label: str, unit: str = "", multiplier: float = 1,
            meaning: str = "", axis_min: float | None = None,
            axis_max: float | None = None) -> dict:
    return dict(key=key, label=label, unit=unit, multiplier=multiplier,
                meaning=meaning, axisMin=axis_min, axisMax=axis_max)


def save(dataset_id: str, title: str, note: str, source: str, frame: pd.DataFrame,
         country: str, year: str, measures: list[dict], group: str | None = None,
         group_label: str = "", date: str | None = None, chart: str = "line",
         x_label: str = "Year") -> dict:
    records = []
    for item in measures:
        values = pd.to_numeric(frame[item["key"]], errors="coerce") * item["multiplier"]
        valid = values.notna() & frame[country].notna() & pd.to_numeric(frame[year], errors="coerce").notna()
        subset = frame.loc[valid]
        for index, row in subset.iterrows():
            record = {
                "country": str(row[country]).strip('"'),
                "year": int(row[year]),
                "date": str(row[date])[:10] if date and pd.notna(row[date]) else "",
                "group": str(row[group]).strip('"') if group and pd.notna(row[group]) else "",
                "metric": item["key"],
                "value": round(float(values.loc[index]), 5),
            }
            if dataset_id == "vdem":
                low, high = f"{item['key']}_codelow", f"{item['key']}_codehigh"
                if pd.notna(row[low]) and pd.notna(row[high]):
                    record["low"] = round(float(row[low]), 5)
                    record["high"] = round(float(row[high]), 5)
            records.append(record)
    (OUT / f"{dataset_id}.json").write_text(json.dumps(records, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return {
        "id": dataset_id, "title": title, "note": note, "source": source,
        "groupLabel": group_label, "chart": chart, "xLabel": x_label,
        "metrics": [{key: item[key] for key in ("key", "label", "unit", "meaning", "axisMin", "axisMax")} for item in measures],
        "countries": sorted({row["country"] for row in records}),
        "firstYear": min(row["year"] for row in records),
        "lastYear": max(row["year"] for row in records),
        "rows": len(records),
    }


def main() -> None:
    catalog = []

    vdem = pd.read_csv(PROCESSED / "vdem_country_year_core_v16.csv")
    catalog.append(save("vdem", "Democracy scores", "V-Dem expert estimates. The two indices use a 0–1 scale; uncertainty ranges are in the source table.",
        "V-Dem v16", vdem, "country_name", "year",
        [measure("v2x_polyarchy", "Electoral democracy", "score (0–1)", meaning="Higher scores indicate more electoral democracy.", axis_min=0, axis_max=1),
         measure("v2x_libdem", "Liberal democracy", "score (0–1)", meaning="Higher scores indicate more liberal democracy.", axis_min=0, axis_max=1)]))

    freedom = pd.read_csv(PROCESSED / "freedom_house_country_year_owid.csv")
    catalog.append(save("freedom", "Freedom House scores", "A second view of democracy. Its 0–100 combined score is not on V-Dem's scale.",
        "Freedom House via OWID", freedom, "country_name", "year",
        [measure("freedom_score", "Combined freedom score", "points (0–100)", meaning="Higher scores indicate more political rights and civil liberties.", axis_min=0, axis_max=100),
         measure("political_rights", "Political rights", "points (0–40)", meaning="Higher scores indicate more political rights. Deductions can put some values below zero.", axis_min=0, axis_max=40),
         measure("civil_liberties", "Civil liberties", "points (0–60)", meaning="Higher scores indicate more civil liberties.", axis_min=0, axis_max=60)]))

    idea = pd.read_csv(PROCESSED / "idea_turnout_clean.csv")
    idea["year"] = idea.election_year
    idea["chart_date"] = idea.election_date_reported.where(idea.election_date_precision == "day_reported", "")
    catalog.append(save("turnout", "Election turnout", "Election dates and turnout denominators need care. The working table flags suspect dates and impossible rates.",
        "International IDEA", idea, "Country", "year",
        [measure("registered_turnout_pct", "Registered voter turnout", "%", meaning="Votes cast as a share of registered voters.", axis_min=0, axis_max=100),
         measure("vap_turnout_pct", "Voting age population turnout", "%", meaning="Votes cast as a share of the estimated voting-age population; estimates can exceed 100%.", axis_min=0, axis_max=100)],
        "Election Type", "Election type", "chart_date", "dots", "Election year"))

    macro = pd.read_csv(PROCESSED / "eurostat_macro_country_year.csv")
    macro["country"] = macro.geo.map(EUROSTAT_AGGREGATES).fillna(macro.geo.map(CODE_NAMES)).fillna(macro.geo)
    catalog.append(save("economy", "Economic context", "Annual country figures for growth, unemployment, inflation and public debt.",
        "Eurostat", macro, "country", "year",
        [measure("nama_10_gdp_real_growth", "Real GDP growth", "%", meaning="Annual change in real GDP. Negative values mean contraction."),
         measure("une_rt_a_unemployment", "Unemployment", "%", meaning="Unemployed people as a share of the labour force.", axis_min=0),
         measure("prc_hicp_aind_inflation", "Inflation", "%", meaning="Annual change in consumer prices. Negative values mean falling prices."),
         measure("gov_10dd_edpt1_debt_gdp", "Public debt / GDP", "%", meaning="Government debt as a share of annual GDP.", axis_min=0)]))

    eb = pd.read_csv(PROCESSED / "eurobarometer_trust_trend.csv")
    eb["country"] = eb.country_code.map(CODE_NAMES).fillna(eb.country_code)
    catalog.append(save("eurobarometer", "Trust across survey waves", "Each point is a published Eurobarometer survey wave, not an annual average.",
        "Eurobarometer", eb, "country", "fieldwork_year", [measure("trust_pct", "Tend to trust", "%", meaning="Share of respondents who tend to trust the selected institution.", axis_min=0, axis_max=100)],
        "institution", "Institution", "fieldwork_start", "line", "Survey year"))

    evs = pd.read_csv(PROCESSED / "evs_wvs_country_trust_summary.csv")
    evs["country"] = evs.country_code.map(CODE_NAMES).fillna(evs.country_code)
    catalog.append(save("evs", "Confidence in institutions", "Weighted share of valid EVS/WVS survey answers. Survey years differ by country.",
        "EVS/WVS", evs, "country", "year", [measure("weighted_confident_pct", "Expressing confidence", "%", meaning="Weighted share of valid answers expressing confidence in the selected institution.", axis_min=0, axis_max=100)],
        "institution", "Institution", chart="dots", x_label="Survey year"))

    ches = pd.read_csv(RAW / "ches/1999-2024_CHES_dataset_meansV2.csv")
    ches["country_name"] = ches.country.map(CHES_NAMES)
    catalog.append(save("ches", "Party positions", "CHES expert ratings are measured in waves, not every year. Select a party before reading the trend.",
        "CHES", ches, "country_name", "year",
        [measure("lrgen", "General left–right", "score (0–10)", meaning="0 is left; 10 is right.", axis_min=0, axis_max=10),
         measure("lrecon", "Economic left–right", "score (0–10)", meaning="0 is economically left; 10 is economically right.", axis_min=0, axis_max=10),
         measure("galtan", "Social values (GAL–TAN)", "score (0–10)", meaning="0 is green, alternative and libertarian; 10 is traditional, authoritarian and nationalist.", axis_min=0, axis_max=10)],
        "party", "Party", chart="dots", x_label="CHES survey year"))

    with ZipFile(RAW / "ppeg_2025v1/ppeg_parl_2025v1.zip") as archive:
        ppeg = pd.read_csv(archive.open("ppeg_parl_2025v1.csv"), low_memory=False)
    ppeg["year"] = pd.to_datetime(ppeg.edate, errors="coerce").dt.year
    catalog.append(save("ppeg", "Parliamentary election results", "PPEG includes parties and alliances. An alliance vote share is not the vote share of one member party.",
        "PPEG", ppeg, "cname_en", "year",
        [measure("v_share", "Vote share", "%", 100, meaning="The selected party or alliance's share of recorded votes.", axis_min=0, axis_max=100),
         measure("s_share", "Seat share", "%", 100, meaning="The selected party or alliance's share of parliamentary seats.", axis_min=0, axis_max=100)],
        "pname_en", "Party or alliance", "edate", "dots", "Election year"))

    for item in catalog:
        item["url"] = SOURCE_URLS[item["id"]]
    (OUT / "catalog.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Prepared {len(catalog)} datasets for the website MVP.")


if __name__ == "__main__":
    main()
