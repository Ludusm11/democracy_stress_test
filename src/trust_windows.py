"""Shared Eurobarometer trust helpers: wave table and the comparison group.

An episode's trust effect is the change in a country's trust from its waves before the shock to
a wave after it, minus the same change in a comparison group: EU member states that were not hit.
Used by build_shock_numbers.py (reference episodes) and build_s1_dataset.py (S1 pilot).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

# Eurobarometer country codes of the 27 current EU member states (Greece is EL; Germany's DE row is
# used, not its West/East split).
EU27 = ["AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "EL", "ES", "FI", "FR", "HR", "HU", "IE", "IT",
        "LT", "LU", "LV", "MT", "NL", "PL", "PT", "RO", "SE", "SI", "SK"]
ISO3_TO_EB = {"AUT": "AT", "BEL": "BE", "BGR": "BG", "CYP": "CY", "CZE": "CZ", "DEU": "DE", "DNK": "DK",
              "EST": "EE", "GRC": "EL", "ESP": "ES", "FIN": "FI", "FRA": "FR", "HRV": "HR", "HUN": "HU",
              "IRL": "IE", "ITA": "IT", "LTU": "LT", "LUX": "LU", "LVA": "LV", "MLT": "MT", "NLD": "NL",
              "POL": "PL", "PRT": "PT", "ROU": "RO", "SWE": "SE", "SVN": "SI", "SVK": "SK"}


def load_waves() -> pd.DataFrame:
    """One row per country, institution and Eurobarometer wave, with fieldwork start and end."""
    eb = pd.read_csv(ROOT / "data/processed/eurobarometer_trust_trend.csv", parse_dates=["fieldwork_start"])
    eb["fieldwork_end"] = pd.to_datetime(eb.fieldwork.str.split(" ").str[1], format="%d/%b/%Y", errors="coerce")
    return eb.groupby(["country_code", "institution", "wave"], as_index=False).agg(
        trust=("trust_pct", "mean"), start=("fieldwork_start", "first"), end=("fieldwork_end", "first"))


def comparison_change(eb: pd.DataFrame, institution: str, before_waves, after_wave, exclude) -> tuple[float, int]:
    """Mean change between the before waves (averaged) and the after wave over the comparison group.

    The group is every EU27 member not in `exclude` that has all the waves. Returns (change, countries used).
    """
    d = eb[(eb.institution == institution) & eb.country_code.isin(EU27) & ~eb.country_code.isin(exclude)]
    table = d.pivot_table(index="country_code", columns="wave", values="trust")
    needed = list(before_waves) + [after_wave]
    if any(w not in table.columns for w in needed):
        return float("nan"), 0
    complete = table[needed].dropna()
    if complete.empty:
        return float("nan"), 0
    change = complete[after_wave] - complete[list(before_waves)].mean(axis=1)
    return float(change.mean()), len(complete)
