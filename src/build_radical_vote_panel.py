"""Radical and populist vote share for every EU country and parliamentary election: data/processed/radical_vote_panel.csv.

PopuList 4.0 classes parties as far right, far left, populist and Eurosceptic and carries each party's ParlGov id. ParlGov holds the
vote share of every party at every election. Joining the two on the ParlGov party id gives, per election:

    farright_pct, farleft_pct, radical_pct (= far right + far left), populist_pct   (strict: parties PopuList flags as borderline are excluded)
    *_incl_bl                                                                       (the same including the borderline parties)

A party counts at an election if the election year lies inside the class's start and end years in PopuList (`farright_startnobl` and
`farright_endnobl` for the strict version, `farright_start` and `farright_end` including borderline parties).

Limits. ParlGov lists an electoral alliance as one party and PopuList classes its member parties, so an alliance's votes are missing from
the radical total: the shares are lower bounds where far-right or far-left parties ran inside alliances. The strict version leaves out
parties the PopuList authors flag as borderline. data/processed/radical_vote_panel_check.csv compares the result with the team's own
France, Belgium, Spain, Greece, Portugal, Ireland, Austria and Italy table (data/reference/radical_parties.csv, PPEG) where the two overlap.

Run from the project folder:  .venv/bin/python src/build_radical_vote_panel.py
"""
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC = ROOT / "data/raw", ROOT / "data/processed"

pl = pd.read_csv(RAW / "The PopuList 4.0.csv", sep=None, engine="python", encoding="utf-8-sig")
pl = pl.dropna(subset=["parlgov_id"]).assign(parlgov_id=lambda d: d.parlgov_id.astype(int))
for c in ["farright", "farleft", "populist"]:
    for s in ["start", "end", "startnobl", "endnobl", "bl"]:
        pl[f"{c}_{s}"] = pd.to_numeric(pl[f"{c}_{s}"], errors="coerce")

el = pd.read_csv(RAW / "parlgov_2024/view_election.tab", sep="\t", quotechar='"')
el = el[el.election_type == "parliament"].copy()
el["election_date"] = pd.to_datetime(el.election_date)
el["year"] = el.election_date.dt.year
el = el[el.year >= 1995]

EU = {"AUT", "BEL", "BGR", "HRV", "CYP", "CZE", "DNK", "EST", "FIN", "FRA", "DEU", "GRC", "HUN", "IRL", "ITA", "LVA", "LTU", "LUX", "MLT", "NLD", "POL", "PRT", "ROU", "SVK", "SVN", "ESP", "SWE", "GBR"}
el = el[el.country_name_short.isin(EU)]
m = el.merge(pl[["parlgov_id"] + [f"{c}_{s}" for c in ["farright", "farleft", "populist"] for s in ["start", "end", "startnobl", "endnobl", "bl", ]] + ["farright", "farleft", "populist"]],
             left_on="party_id", right_on="parlgov_id", how="left", suffixes=("", "_pl"))


def inside(row, cls, strict):
    if not (row[cls] == 1):
        return False
    a, b = (row[f"{cls}_startnobl"], row[f"{cls}_endnobl"]) if strict else (row[f"{cls}_start"], row[f"{cls}_end"])
    if strict and row[f"{cls}_bl"] == 1:
        return False
    return bool(pd.notna(a) and pd.notna(b) and a <= row["year"] <= b)


for cls in ["farright", "farleft", "populist"]:
    m[f"{cls}_strict"] = m.apply(lambda r: inside(r, cls, True), axis=1)
    m[f"{cls}_all"] = m.apply(lambda r: inside(r, cls, False), axis=1)

rows = []
for (iso3, date), g in m.groupby(["country_name_short", "election_date"]):
    s = g.vote_share.fillna(0)
    rows.append({"iso3": iso3, "election_date": date.date(), "listed_vote_pct": s.sum(),
                 "farright_pct": s[g.farright_strict].sum(), "farleft_pct": s[g.farleft_strict].sum(), "populist_pct": s[g.populist_strict].sum(),
                 "farright_incl_bl_pct": s[g.farright_all].sum(), "farleft_incl_bl_pct": s[g.farleft_all].sum(), "populist_incl_bl_pct": s[g.populist_all].sum(),
                 "parties_flagged": ", ".join(sorted(set(g.loc[g.farright_strict | g.farleft_strict, "party_name_short"]))) })
out = pd.DataFrame(rows)
out["radical_pct"] = out.farright_pct + out.farleft_pct
out["radical_incl_bl_pct"] = out.farright_incl_bl_pct + out.farleft_incl_bl_pct
out.round(2).to_csv(PROC / "radical_vote_panel.csv", index=False)

# ---- check against the team's table (PPEG shares; far right + far left, disputed and partial parties left out) -----------------
ref = pd.read_csv(ROOT / "data/reference/radical_parties.csv")
ref = ref[~ref.note.fillna("").str.startswith(("DISPUTED", "PARTIAL"))]
with ZipFile(RAW / "ppeg_2025v1/ppeg_parl_2025v1.zip") as z:
    ppeg = pd.read_csv(z.open("ppeg_parl_2025v1.csv"), usecols=["iso3c", "edate", "party_id", "v_share"], low_memory=False)
ppeg["edate"] = pd.to_datetime(ppeg.edate)
chk = []
for (iso3, edate), g in ppeg[ppeg.iso3c.isin(ref.iso3.unique())].groupby(["iso3c", "edate"]):
    r = ref[ref.iso3 == iso3]
    share = 0.0
    for p in r.itertuples():
        if p.first_year <= edate.year <= p.last_year:
            share += 100 * g.loc[g.party_id == p.party_id, "v_share"].sum()
    near = out[(out.iso3 == iso3) & ((pd.to_datetime(out.election_date) - edate).abs() <= pd.Timedelta(days=5))]
    if len(near) and edate.year >= 2000:
        chk.append({"iso3": iso3, "election_date": edate.date(), "team_table_pct": round(share, 1), "this_panel_pct": round(near.radical_pct.iloc[0], 1)})
chk = pd.DataFrame(chk)
chk["difference"] = (chk.this_panel_pct - chk.team_table_pct).round(1)
chk.to_csv(PROC / "radical_vote_panel_check.csv", index=False)
print(f"radical_vote_panel.csv: {len(out)} elections in {out.iso3.nunique()} countries, {out.election_date.min()} to {out.election_date.max()}")
print(f"Check against the team's table: {len(chk)} elections in {chk.iso3.nunique()} countries; |difference| <= 2 points in {int((chk.difference.abs() <= 2).sum())}, median |difference| {chk.difference.abs().median():.1f}")
