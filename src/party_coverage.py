"""Link PPEG election rows to CHES parties and report how much of the vote is covered.

Used by audit_data.py (France 2024 crosswalk). Run directly to write
outputs/data_audit/ches_coverage.csv: one line per country for its latest
parliamentary election, matched against the CHES 2024 parties.

A PPEG row is linked in one of three ways:
  direct       its Manifesto ID (cmp) equals a CHES cmp_id
  via_members  it is an alliance in data/reference/alliance_members.csv
               with at least one member that CHES rates
  none         anything else
Catch-all rows ("Others", "Miscellaneous…", "Other extreme…") are not parties and
are left out of both counts. Positions of an alliance are not averaged here: the
members' own vote shares inside the alliance are unknown.
"""

from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw"
OUT = ROOT / "outputs/data_audit"

CATCH_ALL = r"^(?:Others?|Miscellaneous|Independents?)\b|^Other\b"
CHES_COUNTRY = {1: "BEL", 4: "GRC", 5: "ESP", 6: "FRA", 7: "IRL", 8: "ITA", 12: "PRT", 13: "AUT"}
MIN_VOTE_PCT = 1.0


def link_rows(rows: pd.DataFrame, ches: pd.DataFrame, members: pd.DataFrame) -> pd.DataFrame:
    """Add link_status, linked_ches_ids and is_catch_all to PPEG rows of one election.

    rows needs iso3c, edate, party_id, pname_en, cmp; ches is one country's CHES wave;
    members is alliance_members.csv.
    """
    out = rows.copy()
    out["edate"] = out.edate.astype(str).str[:10]
    cmp_to_ches = ches.dropna(subset=["cmp_id"]).drop_duplicates("cmp_id").set_index("cmp_id").party_id
    rated = members.dropna(subset=["ches_party_id"]).copy()
    rated["key"] = list(zip(rated.iso3, rated.edate.astype(str), rated.alliance_party_id))
    by_alliance = rated.groupby("key").ches_party_id.apply(lambda s: ";".join(str(int(i)) for i in s))
    listed = {(r.iso3, str(r.edate), r.alliance_party_id) for r in members.itertuples()}

    status, ids = [], []
    for row in out.itertuples():
        key = (row.iso3c, row.edate, row.party_id)
        if pd.notna(row.cmp) and row.cmp in cmp_to_ches.index:
            status.append("direct"); ids.append(str(int(cmp_to_ches[row.cmp])))
        elif key in by_alliance.index:
            status.append("via_members"); ids.append(by_alliance[key])
        elif key in listed:
            status.append("alliance_no_rated_member"); ids.append("")
        else:
            status.append("none"); ids.append("")
    out["link_status"], out["linked_ches_ids"] = status, ids
    out["is_catch_all"] = out.pname_en.fillna("Others").str.contains(CATCH_ALL, regex=True) | out.party_id.str.endswith("999")
    return out


def coverage(linked: pd.DataFrame) -> dict:
    """Party-count and vote-weighted coverage over rows with at least 1% of the vote."""
    parties = linked[~linked.is_catch_all & linked.vote_pct.ge(MIN_VOTE_PCT)]
    matched = parties.link_status.isin(["direct", "via_members"])
    direct = parties.link_status.eq("direct")
    vote = parties.vote_pct
    return dict(
        parties_over_1pct=len(parties), parties_matched=int(matched.sum()), parties_direct=int(direct.sum()),
        pct_parties_matched=round(100 * matched.mean(), 1) if len(parties) else None,
        pct_parties_direct=round(100 * direct.mean(), 1) if len(parties) else None,
        pct_vote_matched=round(100 * vote[matched].sum() / vote.sum(), 1) if len(parties) else None,
        pct_vote_direct=round(100 * vote[direct].sum() / vote.sum(), 1) if len(parties) else None,
        vote_pct_catch_all=round(linked.loc[linked.is_catch_all, "vote_pct"].sum(), 1),
        unmatched=", ".join(parties.loc[~matched, "pname_en"]),
    )


def main() -> None:
    members = pd.read_csv(ROOT / "data/reference/alliance_members.csv")
    ches = pd.read_csv(RAW / "ches/1999-2024_CHES_dataset_meansV2.csv", low_memory=False)
    ches = ches[ches.year.eq(2024)]
    with ZipFile(RAW / "ppeg_2025v1/ppeg_parl_2025v1.zip") as archive:
        ppeg = pd.read_csv(archive.open("ppeg_parl_2025v1.csv"), low_memory=False)

    lines = []
    for code, iso3 in CHES_COUNTRY.items():
        country = ppeg[ppeg.iso3c.eq(iso3)]
        latest = country[country.edate.eq(country.edate.max())].copy()
        latest["vote_pct"] = 100 * latest.v_share
        wave = ches[ches.country.eq(code)]
        linked = link_rows(latest, wave, members)
        no_id = int(wave.cmp_id.isna().sum())
        lines.append(dict(iso3=iso3, election=str(latest.edate.iloc[0])[:10], **coverage(linked),
                          ches_parties=len(wave), ches_parties_without_cmp_id=no_id,
                          note=("Lower bound: CHES parties without a Manifesto ID cannot be matched by ID. "
                                if no_id else "") + ("Alliances read from alliance_members.csv." if iso3 == "FRA" else "")))
    table = pd.DataFrame(lines)
    table.to_csv(OUT / "ches_coverage.csv", index=False)
    print(table.drop(columns="unmatched").to_string(index=False))


if __name__ == "__main__":
    main()
