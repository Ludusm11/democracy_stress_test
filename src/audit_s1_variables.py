"""Audit candidate S1 events and parliamentary-trust survey coverage.

This is a source-coverage audit, not a prediction dataset. PPEG records why a
government ended, but its next inauguration date is only a proxy for the date
the instability began. The nearest survey readings are shown for inspection;
they are not labelled as shock effects or model outcomes.
"""

from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PPEG_ZIP = ROOT / "data/raw/ppeg_2025v1/ppeg_gov_2025v1.zip"
TRUST_CSV = ROOT / "data/processed/eurobarometer_trust_trend.csv"
OUT = ROOT / "outputs/s1_feasibility"
VERIFIED_CSV = ROOT / "data/reference/s1_verified_events.csv"
REASONS = {
    "LoPS": "lack_of_parliamentary_support",
    "Diss": "cabinet_dissension",
    "ResPM": "prime_minister_resignation_review_required",
}
ISO2_TO_EB = {"GR": "EL"}


def load_governments() -> pd.DataFrame:
    with ZipFile(PPEG_ZIP) as archive:
        rows = pd.read_csv(
            archive.open("ppeg_gov_2025v1.csv"),
            usecols=[
                "iso3c", "iso2c", "cname_en", "continent", "idate", "pm",
                "rft", "tog", "gov_seat", "ngovparties",
            ],
            low_memory=False,
        )
    # PPEG has one row per cabinet party. One country/date represents a cabinet.
    cabinets = rows.groupby(["iso3c", "idate"], as_index=False).agg(
        iso2c=("iso2c", "first"), country=("cname_en", "first"),
        continent=("continent", "first"), prime_minister=("pm", "first"),
        termination_reason=("rft", "first"), reason_codes=("rft", "nunique"),
        government_type=("tog", "first"), government_seat_share=("gov_seat", "first"),
        government_party_count=("ngovparties", "first"),
    )
    if (cabinets.reason_codes != 1).any():
        raise ValueError("PPEG termination reasons disagree within a cabinet")
    cabinets["cabinet_inauguration_date"] = pd.to_datetime(cabinets.idate)
    cabinets = cabinets.sort_values(["iso3c", "cabinet_inauguration_date"])
    cabinets["next_cabinet_inauguration_date"] = cabinets.groupby("iso3c")[
        "cabinet_inauguration_date"
    ].shift(-1)
    cabinets["eb_country_code"] = cabinets.iso2c.replace(ISO2_TO_EB)
    return cabinets


def load_trust() -> pd.DataFrame:
    trust = pd.read_csv(TRUST_CSV)
    trust = trust[trust.institution.eq("National parliament")].copy()
    trust = trust[~trust.country_code.isin(["EU", "D-E", "D-W", "DEE", "DEW"])]
    trust["wave_start"] = pd.to_datetime(trust.fieldwork_start)
    trust["wave_end"] = pd.to_datetime(
        trust.fieldwork.str.rsplit(" ", n=1).str[-1],
        format="%d/%b/%Y", errors="raise",
    )
    return trust.sort_values(["country_code", "wave_start"])


def nearest_waves(event: pd.Series, trust: pd.DataFrame) -> dict:
    date = event.next_cabinet_inauguration_date
    country = trust[trust.country_code.eq(event.eb_country_code)]
    before = country[country.wave_end.lt(date)].tail(1)
    after = country[country.wave_start.gt(date)].head(1)
    result = {}
    for label, wave, date_col in (
        ("pre", before, "wave_end"), ("post", after, "wave_start")
    ):
        if wave.empty:
            result.update({f"{label}_wave": None, f"{label}_wave_date": None,
                           f"{label}_trust_pct": None, f"{label}_gap_days": None})
            continue
        row = wave.iloc[0]
        gap = (date - row[date_col]).days if label == "pre" else (row[date_col] - date).days
        result.update({f"{label}_wave": row.wave,
                       f"{label}_wave_date": row[date_col].date().isoformat(),
                       f"{label}_trust_pct": row.trust_pct,
                       f"{label}_gap_days": gap})
    result["waves_within_365_days_of_proxy"] = (
        result["pre_gap_days"] is not None
        and result["post_gap_days"] is not None
        and result["pre_gap_days"] <= 365
        and result["post_gap_days"] <= 365
    )
    return result


def reviewed_window_checks(trust: pd.DataFrame, candidates: pd.DataFrame) -> pd.DataFrame:
    """Check survey windows for every manually reviewed LoPS cabinet record.

    These are measurement checks, not independent shocks or model outcomes.
    """
    reviewed = pd.read_csv(VERIFIED_CSV)
    if reviewed.duplicated(["iso3c", "ending_cabinet_inauguration_date"]).any():
        raise ValueError("Duplicate cabinet keys in reviewed event file")
    reviewed["ending_cabinet_inauguration_date"] = pd.to_datetime(
        reviewed.ending_cabinet_inauguration_date
    )
    lops = candidates[candidates.termination_reason.eq("LoPS")]
    reviewed = reviewed.merge(
        lops[["iso3c", "cabinet_inauguration_date", "next_cabinet_inauguration_date", "eb_country_code"]],
        left_on=["iso3c", "ending_cabinet_inauguration_date"],
        right_on=["iso3c", "cabinet_inauguration_date"],
        how="left", validate="one_to_one",
    )
    if reviewed.eb_country_code.isna().any():
        raise ValueError("A reviewed event does not match a PPEG LoPS candidate")
    if len(reviewed) != len(lops):
        raise ValueError("Not every PPEG LoPS candidate has a review row")
    event_dates = pd.to_datetime(reviewed.verified_event_date)
    if (event_dates.lt(reviewed.cabinet_inauguration_date)
        | event_dates.gt(reviewed.next_cabinet_inauguration_date)).any():
        raise ValueError("Reviewed event date falls outside the ending cabinet period")
    examples = []
    for row in reviewed.itertuples():
        event_date = pd.Timestamp(row.verified_event_date)
        country = trust[trust.country_code.eq(row.eb_country_code)]
        before = country[
            country.wave_end.lt(event_date)
            & country.wave_end.ge(event_date - pd.Timedelta(days=548))
        ].tail(2)
        after = country[
            country.wave_start.gt(event_date + pd.Timedelta(days=90))
            & country.wave_start.le(event_date + pd.Timedelta(days=270))
        ].head(1)
        pre = round(float(before.trust_pct.mean()), 1) if len(before) == 2 else None
        post = round(float(after.trust_pct.iloc[0]), 1) if len(after) else None
        examples.append({
            "iso3c": row.iso3c, "verified_event_date": row.verified_event_date,
            "primary_scenario": row.primary_scenario,
            "include_in_s1_training": row.include_in_s1_training,
            "episode_id": row.episode_id,
            "source_quality": row.source_quality,
            "pre_wave_count": len(before),
            "pre_wave_dates": "; ".join(before.wave_start.dt.date.astype(str)),
            "pre_mean_trust_pct": pre,
            "post_wave_date": after.wave_start.iloc[0].date().isoformat() if len(after) else None,
            "post_trust_pct": post,
            "observed_change_pp": round(post - pre, 1) if pre is not None and post is not None else None,
            "event_source": row.evidence_source,
        })
    return pd.DataFrame(examples)


def main() -> None:
    cabinets, trust = load_governments(), load_trust()
    candidates = cabinets[
        cabinets.continent.eq("Europe")
        & cabinets.termination_reason.isin(REASONS)
        & cabinets.next_cabinet_inauguration_date.between("2005-01-01", "2026-12-31")
        & cabinets.eb_country_code.isin(trust.country_code.unique())
    ].copy()
    candidates["candidate_class"] = candidates.termination_reason.map(REASONS)
    candidates["event_date_status"] = "unknown; next inauguration is a proxy"
    candidates["event_date_reviewed"] = False
    coverage = candidates.apply(lambda row: pd.Series(nearest_waves(row, trust)), axis=1)
    result = pd.concat([candidates.reset_index(drop=True), coverage.reset_index(drop=True)], axis=1)
    columns = [
        "iso3c", "eb_country_code", "country", "prime_minister", "termination_reason",
        "candidate_class", "cabinet_inauguration_date", "next_cabinet_inauguration_date",
        "event_date_status", "event_date_reviewed", "government_type",
        "government_seat_share", "government_party_count", "pre_wave",
        "pre_wave_date", "pre_trust_pct", "pre_gap_days", "post_wave",
        "post_wave_date", "post_trust_pct", "post_gap_days",
        "waves_within_365_days_of_proxy",
    ]
    OUT.mkdir(parents=True, exist_ok=True)
    result[columns].to_csv(OUT / "candidate_events.csv", index=False)
    reviewed_windows = reviewed_window_checks(trust, candidates)
    reviewed_windows.to_csv(OUT / "reviewed_window_checks.csv", index=False)
    reviewed_windows.groupby(
        ["primary_scenario", "include_in_s1_training"], as_index=False
    ).agg(
        reviewed_cabinets=("iso3c", "size"),
        distinct_episodes=("episode_id", "nunique"),
        complete_trust_windows=("observed_change_pp", "count"),
    ).to_csv(OUT / "review_summary.csv", index=False)
    summary = result.groupby(["termination_reason", "candidate_class"], as_index=False).agg(
        candidate_governments=("iso3c", "size"),
        countries=("iso3c", "nunique"),
        proxy_wave_matches=("waves_within_365_days_of_proxy", "sum"),
    )
    summary.to_csv(OUT / "coverage_summary.csv", index=False)
    print(summary.to_string(index=False))
    print(f"Wrote {len(result)} candidates to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
