"""Decode the S2 (financial crisis) source files into two tidy tables.

Reads the Eurostat and World Bank files in data/raw/eurostat_s2/, the existing macro table, and the ESM/EFSF loan
file in data/raw/esm_efsf_loans/. Writes:
  data/processed/s2_country_year_inputs.csv   one row per EU27 country and year, severity and control series
  data/processed/s2_bailout_programmes.csv    one row per country and facility: dates and size of ESM/EFSF loans
  data/processed/s2_bailout_country.csv       one row per EU27 country: all lenders combined (ESM/EFSF file + data/reference/s2_bailout_programmes_ec_imf.csv)
This builds no analysis dataset: it only puts the sources side by side, with the gaps visible.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from trust_windows import EU27, ISO3_TO_EB

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC = ROOT / "data/raw", ROOT / "data/processed"
EB_TO_ISO3 = {v: k for k, v in ISO3_TO_EB.items()}


def decode_jsonstat(path: Path) -> pd.DataFrame:
    """Flatten a Eurostat JSON-stat response into one row per observation (value positions follow the dimension order)."""
    j = json.loads(path.read_text(encoding="utf-8"))
    ids, size = j["id"], j["size"]
    categories = []
    for dim in ids:
        index = j["dimension"][dim]["category"]["index"]
        categories.append(list(index.keys()) if isinstance(index, dict) else list(index))
    rows = []
    for position, value in j["value"].items():
        pos, picks = int(position), []
        for s in reversed(size):
            picks.append(pos % s)
            pos //= s
        picks.reverse()
        rows.append({ids[k]: categories[k][picks[k]] for k in range(len(ids))} | {"value": value})
    return pd.DataFrame(rows)


def series(file: str, name: str) -> pd.Series:
    df = decode_jsonstat(RAW / "eurostat_s2" / file)
    df = df[df.geo.isin(EU27)].assign(year=lambda d: d.time.astype(int))
    return df.set_index(["geo", "year"]).value.rename(name)


def country_year_inputs() -> pd.DataFrame:
    parts = [
        series("nama_10_gdp_real_levels.json", "gdp_real_meur"),
        series("nama_10_gdp_current_prices.json", "gdp_current_meur"),
        series("nama_10_pc_gdp_per_head.json", "gdp_per_head_real_eur"),
        series("gov_10dd_edpt1_net_lending_gdp.json", "net_lending_pct_gdp"),
        series("irt_lt_mcby_a_bond_yield.json", "bond_yield_pct"),
        series("prc_hpi_a_house_prices.json", "house_price_index"),
    ]
    # Youth unemployment: the historical series for years before 2009, the current series from 2009.
    hist = series("une_rt_a_h_youth_unemployment_historical.json", "youth_unemployment_pct")
    current = series("une_rt_a_youth_unemployment.json", "youth_unemployment_pct")
    youth = current.combine_first(hist[hist.index.get_level_values("year") < 2009])
    parts.append(youth)
    wb = json.loads((RAW / "eurostat_s2/worldbank_bank_npl_ratio.json").read_text(encoding="utf-8"))[1]
    npl = pd.DataFrame([{"geo": ISO3_TO_EB.get(r["countryiso3code"]), "year": int(r["date"]), "bank_npl_pct": r["value"]} for r in wb])
    parts.append(npl.dropna(subset=["geo", "bank_npl_pct"]).set_index(["geo", "year"]).bank_npl_pct)
    table = pd.concat(parts, axis=1).reset_index()
    macro = pd.read_csv(PROC / "eurostat_macro_country_year.csv", usecols=["geo", "year", "nama_10_gdp_real_growth", "une_rt_a_unemployment",
                                                                           "prc_hicp_aind_inflation", "gov_10dd_edpt1_debt_gdp"])
    table = table.merge(macro, on=["geo", "year"], how="outer")
    table = table[table.geo.isin(EU27) & table.year.between(2000, 2024)].sort_values(["geo", "year"]).reset_index(drop=True)
    table.insert(1, "iso3", table.geo.map(EB_TO_ISO3))
    return table.round(3)


def bailout_programmes(gdp: pd.DataFrame) -> pd.DataFrame:
    loans = pd.read_csv(RAW / "esm_efsf_loans/OverviewData.csv")
    loans["date"] = pd.to_datetime(loans["Payment Date"], format="%d/%m/%Y")
    out = []
    for (company, country), g in loans.groupby(["Company", "Country"]):
        paid = g[g.Payment < 0]
        out.append(dict(country=country, facility=company, first_disbursement=paid.date.min().date(), last_disbursement=paid.date.max().date(),
                        disbursed_bn=round(-paid.Payment.sum() / 1e9, 2),
                        repaid_early_bn=round(g[(g.Payment > 0) & g.Type.eq("Repayment")].Payment.sum() / 1e9, 2),
                        scheduled_repayments_bn=round(g[g.Type.eq("ScheduledRepayment")].Payment.sum() / 1e9, 2),
                        last_scheduled_repayment=g.date.max().date()))
    table = pd.DataFrame(out)
    code = {"Cyprus": "CY", "Greece": "EL", "Ireland": "IE", "Portugal": "PT", "Spain": "ES"}
    g2012 = gdp[gdp.year == 2012].set_index("geo").gdp_current_meur
    table["gdp_2012_bn"] = table.country.map(lambda c: round(g2012[code[c]] / 1000, 1))
    table["disbursed_pct_gdp_2012"] = (100 * table.disbursed_bn / table.gdp_2012_bn).round(1)
    table["note"] = "ESM/EFSF loans only: excludes EFSM, the Greek Loan Facility, IMF and EU balance-of-payments loans, so a lower bound"
    return table


def bailout_country(esm: pd.DataFrame, gdp: pd.DataFrame) -> pd.DataFrame:
    """All lenders per country: ESM/EFSF loans from the team's file plus EC and IMF programmes from the reference table.

    Only money actually drawn counts. Start is the earliest first disbursement and end the latest last disbursement of any lender
    (months or arrangement dates where exact draws are not published). Amounts agreed but not found as paid are left out.
    """
    other = pd.read_csv(ROOT / "data/reference/s2_bailout_programmes_ec_imf.csv")
    drawn = other[other.drawn.eq("yes")].copy()
    for col in ["first_disbursement", "last_disbursement"]:
        drawn[col] = pd.to_datetime(drawn[col], format="mixed")
    esm = esm.assign(geo=esm.country.map({"Cyprus": "CY", "Greece": "EL", "Ireland": "IE", "Portugal": "PT", "Spain": "ES"}),
                     first=pd.to_datetime(esm.first_disbursement), last=pd.to_datetime(esm.last_disbursement))
    g2012 = gdp[gdp.year == 2012].set_index("geo").gdp_current_meur / 1000
    rows = []
    for geo in EU27:
        d, e = drawn[drawn.geo == geo], esm[esm.geo == geo]
        starts = list(d.first_disbursement) + list(e["first"])
        ends = list(d.last_disbursement) + list(e["last"])
        ec_imf, esm_efsf = d.disbursed_eur_bn.sum(), e.disbursed_bn.sum()
        total = ec_imf + esm_efsf
        rows.append(dict(geo=geo, had_programme=int(total > 0), first_disbursement=min(starts).date() if starts else "", last_disbursement=max(ends).date() if ends else "",
                         esm_efsf_bn=round(esm_efsf, 1), ec_imf_bn=round(ec_imf, 1), total_disbursed_bn=round(total, 1),
                         total_pct_gdp_2012=round(100 * total / g2012[geo], 1) if total else 0.0,
                         lenders=", ".join(sorted(set(d.lender) | ({"ESM/EFSF"} if len(e) else set())))))
    out = pd.DataFrame(rows)
    out["note"] = "Lower bound: bilateral loans to Ireland (4.8 bn agreed) and the Nordic and other lenders to Latvia (2.7 bn agreed) are not counted; IMF euro amounts are approximate"
    return out


def main() -> None:
    inputs = country_year_inputs()
    inputs.to_csv(PROC / "s2_country_year_inputs.csv", index=False)
    programmes = bailout_programmes(inputs)
    programmes.to_csv(PROC / "s2_bailout_programmes.csv", index=False)
    country = bailout_country(programmes, inputs)
    country.to_csv(PROC / "s2_bailout_country.csv", index=False)
    print(f"Countries with a drawn programme: {int(country.had_programme.sum())} ({', '.join(country[country.had_programme == 1].geo)}).")
    crisis = inputs[inputs.year.between(2007, 2014)]
    have = {c: int(crisis.groupby("geo")[c].count().eq(8).sum()) for c in
            ["gdp_real_meur", "net_lending_pct_gdp", "bond_yield_pct", "youth_unemployment_pct", "house_price_index", "bank_npl_pct"]}
    print(f"S2 inputs: {len(inputs)} country-years. EU27 countries complete for 2007-2014: " + ", ".join(f"{k} {v}" for k, v in have.items()))
    print(f"Bailout programmes: {len(programmes)} country-facility rows.")


if __name__ == "__main__":
    main()
