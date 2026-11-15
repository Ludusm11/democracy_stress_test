"""Clean the ESS respondent file and build the tables this project uses.

Reads the ESS Data Builder CSV (all rounds, all variables). Writes:
  data/processed/ess_respondents_slim.csv       one row per respondent, useful columns only,
                                                missing codes turned into blanks. NOT committed:
                                                ESS respondent data may not be redistributed.
  data/processed/ess_country_round_summary.csv  one row per country and round: weighted means,
                                                valid counts and interview dates. Safe to commit.

The ESS file is optional (it needs a free ESS login). Without it this script only says so.
Looks for the file in data/raw/ess/ first, then in data/new/Datafile-subset/.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data/processed"
CANDIDATES = [ROOT / "data/raw/ess/Datafile-subset.csv", ROOT / "data/new/Datafile-subset/Datafile-subset.csv"]

# 0-10 items: 77 refusal, 88 don't know, 99 no answer. 1-4 / 1-3 items: 7, 8, 9.
SCALE_0_10 = ["trstprl", "trstplt", "trstprt", "trstlgl", "trstep", "stfdem", "stfgov", "stfeco", "lrscale", "hinctnta"]
SMALL_CODES = ["polintr", "clsprty", "vote", "gndr"]
KEEP = (["essround", "edition", "idno", "cntry", "pspwght", "pweight", "dweight", "anweight", "agea", "eduyrs"]
        + SCALE_0_10 + SMALL_CODES
        + ["inwyr", "inwmm", "inwdd", "inwyys", "inwmms", "inwdds", "inwds"])
TRUST_MEASURES = ["trstprl", "trstplt", "trstprt", "trstlgl", "trstep", "stfdem", "stfgov", "stfeco"]
EPISODE_COUNTRIES = ["AT", "BE", "ES", "FR", "GR", "IE", "IT", "PT"]
ISO3 = dict(AL="ALB", AT="AUT", BE="BEL", BG="BGR", CH="CHE", CY="CYP", CZ="CZE", DE="DEU", DK="DNK", EE="EST",
            ES="ESP", FI="FIN", FR="FRA", GB="GBR", GR="GRC", HR="HRV", HU="HUN", IE="IRL", IL="ISR", IS="ISL",
            IT="ITA", LT="LTU", LU="LUX", LV="LVA", ME="MNE", MK="MKD", NL="NLD", NO="NOR", PL="POL", PT="PRT",
            RO="ROU", RS="SRB", RU="RUS", SE="SWE", SI="SVN", SK="SVK", TR="TUR", UA="UKR", XK="XKX")


def find_file() -> Path | None:
    return next((p for p in CANDIDATES if p.exists()), None)


def interview_date(d: pd.DataFrame) -> pd.Series:
    """Round 1-2 and 3-9 store year/month/day columns; rounds 10-11 store one timestamp."""
    def parts(year, month, day):
        return pd.to_datetime(dict(year=d[year], month=d[month], day=d[day]), errors="coerce")
    early = parts("inwyr", "inwmm", "inwdd")
    middle = parts("inwyys", "inwmms", "inwdds")
    late = pd.to_datetime(d.inwds, errors="coerce").dt.normalize()
    return early.where(d.essround.le(2), middle.where(d.essround.le(9), late))


def clean(path: Path) -> pd.DataFrame:
    header = pd.read_csv(path, nrows=0).columns
    use = [c for c in KEEP if c in header]
    d = pd.concat(pd.read_csv(path, usecols=use, chunksize=200_000, low_memory=False))
    for col in SCALE_0_10:
        d[col] = d[col].where(~d[col].isin([77, 88, 99]))
    for col in SMALL_CODES:
        d[col] = d[col].where(~d[col].isin([7, 8, 9]))
    d["eduyrs"] = d.eduyrs.where(~d.eduyrs.isin([77, 88, 99]) & d.eduyrs.le(40))  # above 40 years is a coding error
    d["agea"] = d.agea.where(d.agea.ne(999) & d.agea.le(110))
    d["voted"] = d.vote.map({1: 1.0, 2: 0.0})  # "not eligible" (3) and missing stay blank
    d["interview_date"] = interview_date(d)
    d["iso3"] = d.cntry.map(ISO3)
    d = d.drop(columns=["inwyr", "inwmm", "inwdd", "inwyys", "inwmms", "inwdds", "inwds", "vote"])
    # Weight 0 means "not part of the weighted sample"; keep the row but it adds nothing to estimates.
    return d


def wmean(values: pd.Series, weights: pd.Series) -> float:
    ok = values.notna() & weights.gt(0)
    return float(np.average(values[ok], weights=weights[ok])) if ok.any() else np.nan


def summarise(d: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (round_, country), g in d.groupby(["essround", "cntry"]):
        row = dict(essround=round_, cntry=country, iso3=ISO3.get(country), respondents=len(g),
                   in_episode_countries=country in EPISODE_COUNTRIES,
                   interview_start_p1=g.interview_date.quantile(0.01, interpolation="nearest"),
                   interview_median=g.interview_date.quantile(0.5, interpolation="nearest"),
                   interview_end_p99=g.interview_date.quantile(0.99, interpolation="nearest"),
                   interview_date_share=round(float(g.interview_date.notna().mean()), 3))
        for col in TRUST_MEASURES + ["voted"]:
            scale = 100 if col == "voted" else 1
            row[f"{col}_mean"] = round(scale * wmean(g[col], g.pspwght), 3)
            row[f"{col}_n"] = int(g[col].notna().sum())
        rows.append(row)
    out = pd.DataFrame(rows).rename(columns={"voted_mean": "voted_pct_of_eligible"})
    for col in ("interview_start_p1", "interview_median", "interview_end_p99"):
        out[col] = out[col].dt.strftime("%Y-%m-%d")
    return out


def main() -> None:
    path = find_file()
    if path is None:
        print("ESS file not found (optional). Download it from https://ess.sikt.no/en/data-builder/ "
              "and save it as data/raw/ess/Datafile-subset.csv; see data/raw/ess/README.md.")
        return
    d = clean(path)
    d.to_csv(PROC / "ess_respondents_slim.csv", index=False)
    summary = summarise(d)
    summary.to_csv(PROC / "ess_country_round_summary.csv", index=False)
    print(f"ESS: {len(d):,} respondents, {d.cntry.nunique()} countries, rounds {int(d.essround.min())}-{int(d.essround.max())}; "
          f"wrote {len(summary)} country-round rows.")


if __name__ == "__main__":
    main()
