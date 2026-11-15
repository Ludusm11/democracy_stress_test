"""Link PPEG election parties to CHES parties using the evidence both sources hold.

CHES lists, for each party and survey wave, the party's vote share (`vote`) at its most recent national
election (`electionyear`). PPEG has the vote share of every party at every election. That makes a link
checkable: a PPEG party and a CHES party are the same party when they share a Manifesto ID (`cmp`), or
when they carry the same name and nearly the same vote share at the same election, or when one vote
share is unique and equal to the hundredth. A link is made once per PPEG `party_id` and then applies to
all of that party's elections.

Methods, strongest first:
  cmp_id           same Manifesto ID in both sources
  name_and_vote    similar name and vote shares within 0.5 points at the same election
  vote_share       no name evidence, but vote shares within 0.15 points and no other candidate near
  alliance_sum     one PPEG alliance row whose vote equals the sum of 2-4 CHES parties (within 0.25 points)
  alliance_members hand-written list in data/reference/alliance_members.csv (France 2024)

Every link is a candidate until a person has checked it (see `checked_by_person`).
"""

from __future__ import annotations

import re
from itertools import combinations

import pandas as pd

CHES_ISO3 = {1: "BEL", 2: "DNK", 3: "DEU", 4: "GRC", 5: "ESP", 6: "FRA", 7: "IRL", 8: "ITA", 10: "NLD", 11: "GBR",
             12: "PRT", 13: "AUT", 14: "FIN", 16: "SWE", 20: "BGR", 21: "CZE", 22: "EST", 23: "HUN", 24: "LVA",
             25: "LTU", 26: "POL", 27: "ROU", 28: "SVK", 29: "SVN", 31: "HRV", 37: "MLT", 38: "LUX", 40: "CYP"}
CATCH_ALL = r"^(?:Others?|Miscellaneous|Independents?|Against all|Minorities)\b|^Other\b"
RANK = {"cmp_id": 0, "name_and_vote": 1, "vote_share": 2, "alliance_sum": 3, "alliance_members": 4}


def norm(text) -> str:
    return re.sub(r"[^a-z0-9]", "", str(text).lower().replace("ø", "o").replace("æ", "ae")) if pd.notna(text) else ""


def name_evidence(ches_name, initials, english) -> bool:
    c, i, e = norm(ches_name), norm(initials), norm(english)
    i = re.sub(r"\d{4}$", "", i)  # "V (2017)" -> "v"
    if len(c) >= 2 and len(i) >= 2 and (c == i or c in i or i in c):
        return True
    return len(c) >= 4 and (c in e or e == c)


def prepare(ches: pd.DataFrame, ppeg: pd.DataFrame):
    ches = ches[ches.country.isin(CHES_ISO3)].copy()
    ches["iso3"] = ches.country.map(CHES_ISO3)
    ppeg = ppeg[ppeg.iso3c.isin(CHES_ISO3.values())].copy()
    ppeg["edate"] = pd.to_datetime(ppeg.edate)
    ppeg["vote_pct"] = 100 * ppeg.v_share
    ppeg["is_catch_all"] = ppeg.pname_en.fillna("Others").str.contains(CATCH_ALL, regex=True) | ppeg.party_id.astype(str).str.endswith(("999", "995", "996"))
    return ches, ppeg


def build_links(ches: pd.DataFrame, ppeg: pd.DataFrame) -> pd.DataFrame:
    """One row per (PPEG party, CHES party) link with the method and the evidence that produced it."""
    ches, ppeg = prepare(ches, ppeg)
    links = []
    for iso3, c_country in ches.groupby("iso3"):
        p_country = ppeg[ppeg.iso3c == iso3]
        for (year, wave_year), wave in c_country.dropna(subset=["electionyear"]).groupby(["electionyear", "year"]):
            options = []  # one entry per election in that year: the links it would give
            for edate in sorted(p_country[p_country.edate.dt.year == int(year)].edate.unique()):
                e = p_country[(p_country.edate == edate) & ~p_country.is_catch_all]
                if e.empty:
                    continue
                matched_c, matched_p = set(), set()
                found = []

                def add(c, r, method, diff, found=found, edate=edate):
                    found.append(dict(iso3=iso3, ppeg_party_id=r.party_id, ppeg_party=r.pinitials if pd.notna(r.pinitials) else r.pname_en,
                                      ppeg_name=r.pname_en, ches_party_id=int(c.party_id), ches_party=c.party, method=method,
                                      evidence_election=str(pd.Timestamp(edate).date()), ches_wave=int(wave_year),
                                      ches_vote_pct=c.vote, ppeg_vote_pct=round(r.vote_pct, 2), vote_difference=round(diff, 2)))
                    matched_c.add(c.party_id); matched_p.add(r.party_id)

                rows = list(e.itertuples())
                for c in wave.itertuples():
                    if pd.notna(c.cmp_id):
                        for r in rows:
                            if pd.notna(r.cmp) and r.cmp == c.cmp_id:
                                add(c, r, "cmp_id", abs(c.vote - r.vote_pct) if pd.notna(c.vote) else float("nan"))
                for c in wave.itertuples():
                    if c.party_id in matched_c or pd.isna(c.vote) or c.vote <= 0:
                        continue
                    near = [(abs(c.vote - r.vote_pct), r) for r in rows if r.party_id not in matched_p and abs(c.vote - r.vote_pct) <= 0.5]
                    named = [(d, r) for d, r in near if name_evidence(c.party, r.pinitials, r.pname_en)]
                    if len(named) == 1:
                        add(c, named[0][1], "name_and_vote", named[0][0])
                    elif not named:
                        close = [(d, r) for d, r in near if d <= 0.15]
                        rivals = [x for x in wave.itertuples() if x.party_id != c.party_id and x.party_id not in matched_c and pd.notna(x.vote)
                                  and abs(x.vote - c.vote) <= 0.3]
                        if len(close) == 1 and not rivals:
                            add(c, close[0][1], "vote_share", close[0][0])
                # Alliances: an unmatched PPEG row whose vote equals the sum of several unmatched CHES parties.
                free_c = [c for c in wave.itertuples() if c.party_id not in matched_c and pd.notna(c.vote) and c.vote > 0]
                for r in [x for x in rows if x.party_id not in matched_p and x.vote_pct >= 1]:
                    is_alliance = r.alliance == "Electoral alliance" or bool(re.search(r"[-–/]|\band\b", str(r.pname_en)))
                    hits = [combo for k in (2, 3, 4) for combo in combinations(free_c, k)
                            if abs(sum(c.vote for c in combo) - r.vote_pct) <= 0.2
                            and (is_alliance or all(name_evidence(c.party, r.pinitials, r.pname_en) for c in combo))]
                    if len(hits) == 1:
                        for c in hits[0]:
                            add(c, r, "alliance_sum", abs(sum(x.vote for x in hits[0]) - r.vote_pct))
                options.append(found)
            # CHES `vote` refers to one election. When a country voted twice in that year (Bulgaria 2024),
            # keep the election where the most parties are confirmed by ID or by name.
            if options:
                links.extend(max(options, key=lambda f: sum(x["method"] in ("cmp_id", "name_and_vote") for x in f)))
    table = pd.DataFrame(links)
    if table.empty:
        return table
    table["rank"] = table.method.map(RANK)
    table = (table.sort_values(["rank", "vote_difference"]).drop_duplicates(["ppeg_party_id", "ches_party_id", "iso3"])
             .drop(columns="rank").sort_values(["iso3", "ppeg_party_id"]))
    table["checked_by_person"] = "no"
    return table


def coverage_by_election(ppeg: pd.DataFrame, links: pd.DataFrame, members: pd.DataFrame, since: int = 1999) -> pd.DataFrame:
    """For each election: how much of the vote (parties with 1%+) is linked to CHES, in total and by ID alone."""
    ppeg = ppeg[ppeg.iso3c.isin(CHES_ISO3.values())].copy()
    ppeg["edate"] = pd.to_datetime(ppeg.edate)
    ppeg["vote_pct"] = 100 * ppeg.v_share
    ppeg["is_catch_all"] = ppeg.pname_en.fillna("Others").str.contains(CATCH_ALL, regex=True) | ppeg.party_id.astype(str).str.endswith(("999", "995", "996"))
    best = links.assign(rank=links.method.map(RANK)).sort_values("rank").drop_duplicates(["iso3", "ppeg_party_id"]).set_index(["iso3", "ppeg_party_id"]).method
    cmp_ids = set(links[links.method == "cmp_id"].ppeg_party_id)
    member_keys = {(r.iso3, str(r.edate)[:10], r.alliance_party_id) for r in members.dropna(subset=["ches_party_id"]).itertuples()}
    rows = []
    for (iso3, edate), g in ppeg[ppeg.edate.dt.year >= since].groupby(["iso3c", "edate"]):
        parties = g[~g.is_catch_all & g.vote_pct.ge(1.0)]
        if parties.empty:
            continue
        method = [best.get((iso3, p)) if (iso3, p) in best.index else ("alliance_members" if (iso3, str(edate.date()), p) in member_keys else None)
                  for p in parties.party_id]
        parties = parties.assign(method=method)
        linked = parties.method.notna()
        by_id = parties.method.eq("cmp_id")
        confirmed = parties.method.isin(["cmp_id", "name_and_vote", "alliance_members"])
        vote = parties.vote_pct
        rows.append(dict(iso3=iso3, election=str(edate.date()), parties_over_1pct=len(parties), parties_linked=int(linked.sum()),
                         pct_parties_linked=round(100 * linked.mean(), 1), pct_vote_linked=round(100 * vote[linked].sum() / vote.sum(), 1),
                         pct_vote_confirmed=round(100 * vote[confirmed].sum() / vote.sum(), 1),
                         pct_vote_linked_by_id_only=round(100 * vote[by_id].sum() / vote.sum(), 1),
                         vote_pct_catch_all=round(g.loc[g.is_catch_all, "vote_pct"].sum(), 1),
                         not_linked=", ".join(f"{p} ({v:.1f}%)" for p, v in zip(parties.loc[~linked, "pinitials"].fillna(parties.pname_en), vote[~linked]))))
    return pd.DataFrame(rows)


def precision_check(ches: pd.DataFrame, ppeg: pd.DataFrame) -> pd.DataFrame:
    """How often name and vote evidence alone finds the link the Manifesto ID gives.

    Hides every CHES Manifesto ID, rebuilds the links, and compares them with the ID links on the parties
    that have one. A link by name or vote that disagrees is counted wrong even if the ID link is the odd one out.
    """
    truth = build_links(ches, ppeg).query("method == 'cmp_id'")[["iso3", "ppeg_party_id", "ches_party_id"]].assign(correct=True)
    blind = build_links(ches.assign(cmp_id=float("nan")), ppeg)
    known = blind.merge(truth[["iso3", "ppeg_party_id"]].drop_duplicates(), on=["iso3", "ppeg_party_id"])
    known = known.merge(truth, on=["iso3", "ppeg_party_id", "ches_party_id"], how="left")
    known["correct"] = known.correct.fillna(False).astype(bool)
    out = known.groupby("method").agg(links_tested=("correct", "size"), agree_with_id=("correct", "sum")).reset_index()
    out["share_agreeing"] = (out.agree_with_id / out.links_tested).round(3)
    return out
