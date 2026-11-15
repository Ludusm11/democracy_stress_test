"""Link PopuList 4.0 far-right and far-left parties to PPEG election parties.

PopuList names each party and its ParlGov ID but has no election results, so a link rests on
evidence from elsewhere. For every PopuList party classed far right or far left it tries, in order:

  cmp_id         the party's Manifesto ID (ParlGov party list) equals a PPEG row's `cmp` in the same country
  parlgov_vote   ParlGov's vote share for the party at an election equals a PPEG row's share at the same
                 election (within 0.25 points, one candidate only)
  name           PopuList's abbreviation or English name equals a PPEG abbreviation or name (one candidate only)

A link is accepted when one method gives exactly one PPEG party. Parties that PopuList lists but PPEG never
shows, or where methods disagree, stay unlinked in the table so they can be reviewed. Nothing is checked
by a person. Writes outputs/data_audit/popu_ppeg_links.csv.
"""

from __future__ import annotations

import re
from pathlib import Path
from zipfile import ZipFile

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, OUT = ROOT / "data/raw", ROOT / "outputs/data_audit"

POPU_COUNTRY = {"AUT": "Austria", "BEL": "Belgium", "BGR": "Bulgaria", "HRV": "Croatia", "CYP": "Cyprus", "CZE": "Czech Republic",
                "DNK": "Denmark", "EST": "Estonia", "FIN": "Finland", "FRA": "France", "DEU": "Germany", "GRC": "Greece",
                "HUN": "Hungary", "IRL": "Ireland", "ITA": "Italy", "LVA": "Latvia", "LTU": "Lithuania", "LUX": "Luxembourg",
                "MLT": "Malta", "NLD": "Netherlands", "POL": "Poland", "PRT": "Portugal", "ROU": "Romania", "SVK": "Slovakia",
                "SVN": "Slovenia", "ESP": "Spain", "SWE": "Sweden"}  # the EU27, as PopuList names them
RANK = {"cmp_id": 0, "parlgov_vote": 1, "name": 2}


def norm(text) -> str:
    text = str(text).lower() if pd.notna(text) else ""
    return re.sub(r"[^a-z0-9]", "", re.sub(r"\(\d{4}\)", "", text))


def load():
    pop = pd.read_csv(RAW / "The PopuList 4.0.csv", sep=";", low_memory=False)
    pg_party = pd.read_csv(RAW / "parlgov_2024/view_party.tab", sep="\t", low_memory=False)
    pg_elec = pd.read_csv(RAW / "parlgov_2024/view_election.tab", sep="\t", low_memory=False)
    with ZipFile(RAW / "ppeg_2025v1/ppeg_parl_2025v1.zip") as archive:
        ppeg = pd.read_csv(archive.open("ppeg_parl_2025v1.csv"), low_memory=False)
    ppeg["edate"] = pd.to_datetime(ppeg.edate)
    ppeg["vote_pct"] = 100 * ppeg.v_share
    return pop, pg_party, pg_elec[pg_elec.election_type == "parliament"].assign(election_date=lambda d: pd.to_datetime(d.election_date)), ppeg


def classes(row):
    """Far-right and far-left periods that apply (PopuList uses 1900/2100 for 'always')."""
    out = []
    if row.farright == 1:
        out.append(("far_right", int(row.farright_start), int(row.farright_end), int(row.farright_bl) == 1))
    if row.farleft == 1:
        out.append(("far_left", int(row.farleft_start), int(row.farleft_end), int(row.farleft_bl) == 1))
    return out


def build(countries=POPU_COUNTRY) -> pd.DataFrame:
    pop, pg_party, pg_elec, ppeg = load()
    rows = []
    for iso3, popu_name in countries.items():
        p_country = ppeg[ppeg.iso3c == iso3]
        parties = p_country.drop_duplicates(["party_id", "pinitials", "pname_en"])[["party_id", "pinitials", "pname_en", "cmp"]]  # a party can be renamed
        cand = pop[(pop.country_name == popu_name) & ((pop.farright == 1) | (pop.farleft == 1))]
        for r in cand.itertuples():
            found = {}
            pg = pg_party[pg_party.party_id == r.parlgov_id] if pd.notna(r.parlgov_id) else pg_party.iloc[0:0]
            # 1. Manifesto ID through ParlGov
            if len(pg) and pd.notna(pg.cmp.iloc[0]):
                hit = parties[parties.cmp == pg.cmp.iloc[0]].party_id.unique()
                if len(hit) == 1:
                    found["cmp_id"] = (hit[0], "")
            # 2. ParlGov vote share against PPEG at the same election
            if len(pg):
                votes = pg_elec[pg_elec.party_id == r.parlgov_id]
                hits, notes = set(), []
                for v in votes.itertuples():
                    if pd.isna(v.vote_share):
                        continue
                    e = p_country[(p_country.edate - v.election_date).abs() <= pd.Timedelta(days=3)]
                    near = e[(e.vote_pct - v.vote_share).abs() <= 0.25]
                    if len(near) == 1:
                        hits.add(near.party_id.iloc[0]); notes.append(f"{v.election_date:%Y-%m-%d}: {v.vote_share:.2f} vs {near.vote_pct.iloc[0]:.2f}")
                if len(hits) == 1:
                    found["parlgov_vote"] = (next(iter(hits)), "; ".join(notes[:3]))
            # 3. Name
            keys = {norm(r.party_name_short), norm(r.party_name_english)} - {""}
            named = parties[parties.pinitials.map(norm).isin(keys) | parties.pname_en.map(norm).isin(keys)].party_id.unique()
            if len(named) != 1:  # a longer PPEG name that contains the PopuList abbreviation ("Volya" in "Volya Movement")
                short = norm(r.party_name_short)
                named = parties[parties.pname_en.map(norm).map(lambda n: len(short) >= 5 and short in n)].party_id.unique()
            if len(named) == 1:
                found["name"] = (named[0], "")
            ids = {v[0] for v in found.values()}
            status = "linked" if len(ids) == 1 else ("conflict" if len(ids) > 1 else "not_linked")
            method = min(found, key=RANK.get) if len(ids) == 1 else ""
            for family, first, last, borderline in classes(r):
                rows.append(dict(iso3=iso3, popu_party=r.party_name_short, popu_name=r.party_name_english, family=family,
                                 first_year=first, last_year=last, ppeg_party_id=next(iter(ids)) if len(ids) == 1 else "",
                                 ppeg_party=(parties[parties.party_id == next(iter(ids))].pinitials.iloc[0] if len(ids) == 1 else ""),
                                 methods="+".join(sorted(found, key=RANK.get)), status=status,
                                 evidence=found[method][1] if method else "; ".join(f"{k}={v[0]}" for k, v in found.items()),
                                 source="PopuList 4.0", borderline=int(borderline), checked_by_person="no"))
    table = pd.DataFrame(rows)
    # Two PopuList parties cannot both be one PPEG party unless both are backed by the strongest evidence
    # (PopuList lists the Czech Communists twice): keep the better-evidenced one, flag the rest.
    best = table.methods.map(lambda m: min(RANK[x] for x in m.split("+")) if m else 9)
    linked = table.status.eq("linked")
    for (iso3, pid), group in table[linked].groupby(["iso3", "ppeg_party_id"]):
        if group.popu_party.nunique() > 1:
            top = best[group.index].min()
            for idx in group.index[best[group.index] > top]:
                table.loc[idx, ["status", "evidence"]] = ["conflict", f"also claimed by a better-evidenced PopuList party; was {pid}"]
                table.loc[idx, "ppeg_party_id"] = ""
    table["note"] = table.borderline.map({1: "BORDERLINE: PopuList 4.0 marks this class as borderline", 0: ""})
    for (iso3, party), (extra_ids, note) in MANUAL.items():
        base = table[(table.iso3 == iso3) & (table.popu_party == party)].iloc[0].copy()
        table = table[~((table.iso3 == iso3) & (table.popu_party == party))]
        for pid in extra_ids:
            base["ppeg_party_id"], base["status"], base["methods"] = pid, "linked", "manual"
            base["ppeg_party"], base["evidence"], base["note"] = pid, "same party under a later list name", note
            table = pd.concat([table, base.to_frame().T], ignore_index=True)
    return table


# Linked by hand: a party that PPEG records under more than one list ID. DISPUTED rows are left out of the
# main radical total and shown separately.
MANUAL = {("BGR", "BSP"): (["BG1", "BG650"], "BORDERLINE and DISPUTED: PopuList 4.0 marks the Bulgarian Socialist Party borderline far right; other sources call it centre-left or social-democratic")}


STABLE_FROM, STABLE_TO = 2000, 2025  # a party counts as radical only if PopuList classes it so for the whole period


def parlgov_shares() -> pd.DataFrame:
    """Radical vote share per election straight from ParlGov, as an independent check on the PPEG links.

    Uses the same PopuList parties (classed throughout 2000-2025, not borderline) through their ParlGov IDs.
    ParlGov ends in 2023, and it reports some alliances as one list, so it can differ from PPEG.
    """
    pop, _, pg_elec, _ = load()
    names = {v: k for k, v in POPU_COUNTRY.items()}
    rows = []
    for r in pop[pop.country_name.isin(names) & pop.parlgov_id.notna()].itertuples():
        for family, first, last, borderline in classes(r):
            if borderline or first > STABLE_FROM or last < STABLE_TO:
                continue
            for v in pg_elec[pg_elec.party_id == r.parlgov_id].itertuples():
                if pd.notna(v.vote_share):
                    rows.append((names[r.country_name], v.election_date, v.vote_share))
    return pd.DataFrame(rows, columns=["iso3", "edate", "parlgov_radical_pct"]).groupby(["iso3", "edate"], as_index=False).sum()


def election_shares(ppeg: pd.DataFrame, links: pd.DataFrame) -> pd.DataFrame:
    """Radical vote share of each election: far right and far left, with BORDERLINE, DISPUTED and PARTIAL parties kept apart."""
    ppeg = ppeg.assign(edate=pd.to_datetime(ppeg.edate), vote_pct=100 * ppeg.v_share)
    ok = links[links.status.eq("linked")].drop_duplicates(["iso3", "ppeg_party_id", "family"])
    # A class that changes within the period would make a relabeling look like a change in votes (N-VA is far right
    # in PopuList only from 2019), so only parties classed the same way throughout count.
    ok = ok[(ok.first_year.astype(int) <= STABLE_FROM) & (ok.last_year.astype(int) >= STABLE_TO)]
    rows = []
    for (iso3, edate), g in ppeg[ppeg.iso3c.isin(ok.iso3.unique())].groupby(["iso3c", "edate"]):
        mine = ok[ok.iso3 == iso3]
        merged = g.merge(mine, left_on="party_id", right_on="ppeg_party_id")
        merged = merged[(merged.edate.dt.year >= merged.first_year.astype(int)) & (merged.edate.dt.year <= merged.last_year.astype(int))]
        disputed = merged.note.fillna("").str.contains("DISPUTED|PARTIAL|BORDERLINE")
        rows.append(dict(iso3=iso3, edate=edate, far_right_pct=merged[~disputed & merged.family.eq("far_right")].vote_pct.sum(),
                         far_left_pct=merged[~disputed & merged.family.eq("far_left")].vote_pct.sum(), disputed_pct=merged[disputed].vote_pct.sum()))
    out = pd.DataFrame(rows)
    out["radical_pct"] = out.far_right_pct + out.far_left_pct
    return out


def main() -> None:
    table = build()
    table.to_csv(OUT / "popu_ppeg_links.csv", index=False)
    print(f"PopuList links: {len(table)} party-class rows, " + ", ".join(f"{k} {v}" for k, v in table.status.value_counts().items()))


if __name__ == "__main__":
    main()
