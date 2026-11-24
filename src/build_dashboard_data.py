"""Build dashboard/data.js: the Democracy Stress Test dashboard's data file.

Starts from dashboard/data_original.js (the team's prototype: S1 and S2 are still placeholder values) and replaces what now has real
estimates:

* the four survey baselines (Standard Eurobarometer 105.2, spring 2026) and the turnout baseline (IDEA, 2024);
* scenario E: its sliders, texts and a grid of readings with joint bootstrap ranges (outputs/model/e_grid.csv);
* E's back-test and France check, using calibrated single-episode ranges (outputs/model/e_conformal.csv).

Run from the project folder:  .venv/bin/python src/build_dashboard_data.py
Needs outputs/model/e_*.csv (run notebooks/Shock_E_energy_price.ipynb first), s1_grid.csv / s1_conformal.csv (run src/build_s1_grid.py first) and s2_grid.csv / s2_dashboard_*.csv (run notebooks/Shock_2_financial_crisis_analysis.ipynb first).
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/model"
DASH = ROOT / "dashboard"
ID = {"trust_gov": "trust_gov", "trust_parl": "trust_parl", "trust_parties": "trust_parties", "swd": "satisf_dem"}   # notebook id -> dashboard id

src = (DASH / "data_original.js").read_text(encoding="utf8")
D = json.loads(src[src.index("window.MVP_DATA = ") + len("window.MVP_DATA = "):].rstrip().rstrip(";"))

# ---- baselines ------------------------------------------------------------------------------------------------------------------
eb = pd.read_csv(ROOT / "data/processed/eurobarometer_france_trust_summary.csv").drop_duplicates()
eb = eb[(eb.wave == "Spring 2026")].set_index("indicator").share_pct.round(0)
base = {"trust_gov": eb["Trust in national government"], "trust_parl": eb["Trust in national parliament"],
        "trust_parties": eb["Trust in political parties"], "satisf_dem": eb["Satisfied with democracy in France"]}
turnout = pd.read_csv(ROOT / "data/processed/idea_france_elections.csv")
turnout = turnout[(turnout["Election Type"] == "Parliamentary") & (turnout.election_date == "2024-06-30")].registered_turnout_pct.iloc[0]
for o in D["outcomes"]:
    if o["id"] in base:
        o["baseline"], o["date"], o["source"] = float(base[o["id"]]), "EB 105.2, spring 2026", "Standard Eurobarometer"
    elif o["id"] == "turnout":
        o["baseline"], o["date"], o["source"] = round(float(turnout), 1), "Legislative election 2024, first round", "International IDEA"
    elif o["id"] == "radical_vote":
        o["baseline"], o["source"] = None, "Not set: the far-right and far-left classification still needs a team decision"

# ---- scenario E -----------------------------------------------------------------------------------------------------------------
grid = pd.read_csv(OUT / "e_grid.csv")
expo = pd.read_csv(OUT / "e_exposure.csv").set_index("iso3")
conf = pd.read_csv(OUT / "e_conformal.csv")
spells = pd.read_csv(OUT / "e_spells.csv")
live = pd.read_csv(OUT / "e_current_surge.csv")
n_est = int(grid[(grid.outcome == "trust_gov") & (grid.horizon == 1)].n_events.iloc[0])
thr = float(__import__("re").search(r"above ([\d.]+)%", (OUT / "e_threshold.txt").read_text()).group(1))
ys, ms = sorted(grid.yoy.unique().tolist()), sorted(grid.months.unique().tolist())
cells = {}
for (o, h), g in grid.groupby(["outcome", "horizon"]):
    g = g.set_index(["yoy", "months"]).reindex([(y, m) for y in ys for m in ms])
    cells[f"{ID[o]}|{int(h)}"] = {k: [round(float(v), 2) for v in g[k]] for k in ["line", "line_low", "line_high", "bend", "bend_low", "bend_high"]}
    cells[f"{ID[o]}|{int(h)}"]["n"] = int(g.n_events.iloc[0])
D["grid"] = {"E": {"params": ["energy_yoy", "duration_m"], "axes": [ys, ms], "shapes": True, "cells": cells}}

E = next(s for s in D["scenarios"] if s["id"] == "E")
fr_gas = float(expo.loc["FRA", "gas_share_pct"])
last_month = str(live.end.max()) if len(live) else "2026-10"
fr_live = live[live.iso3 == "FRA"]
live_note = (f"A new surge is under way: {len(live)} countries are above the threshold in {last_month}"
             + (f"; France since {fr_live.start.iloc[0]}, {fr_live.latest.iloc[0]:.1f}% in {last_month}" if len(fr_live) else "")
             + ". Its effect on trust is not observed yet (no Eurobarometer wave after it is published); readings here are what-ifs.")
single_q = {f"{ID[r.outcome]}|{int(r.horizon)}": round(float(r.conformal_half_width), 1) for r in conf.itertuples()}
E.update({
    "placeholder": False,
    "grid": True,
    "status": "Candidate to replace S1 · estimated",
    "evidence": "medium",
    "evidence_note": f"Shock measured by official statistics; the effect rests on {n_est} past surges, with wide ranges that depend on the shape of the dose-response",
    "params": [
        {"id": "energy_yoy", "label": "Energy price increase, year on year", "unit": "%", "min": ys[0], "max": ys[-1], "step": 1, "default": 35, "type": "range",
         "note": f"Starts at the {thr:.1f}% threshold (a shock is a rise above it). Maximum {ys[-1]}%: the Netherlands, 2021–22. Few spells exceed 45%."},
        {"id": "duration_m", "label": "Duration of the shock", "unit": "months", "min": 1, "max": ms[-1], "step": 1, "default": 6, "type": "range",
         "note": f"Longest observed: {ms[-1]} months (Cyprus, 2010–12). Duration is only known when a surge ends."}],
    "threshold": f"Year-on-year rate of change of the HICP energy component above {thr:.1f}%: the top 10% of EU-member country-months since 2001 to December 2025, France left out "
                 "(fixed before the 2026 surge, so it cannot move the rule; 2001 start because 1997–98 holds Bulgaria's +544% hyperinflation). Also tested at the top 15% and top 5%. "
                 "A shock is a run of months above it; the sliders are its mean rise and its length.",
    "episodes": ["EU energy crisis 2021–23 (most EU countries above the threshold at once)", "Earlier surges: 2005, 2008, 2010–12 (smaller, in fewer countries)",
                 f"{len(spells)} spells in {spells.iso3.nunique()} countries up to {last_month}; {n_est} are used for estimation (France excluded; spells still running are not used)",
                 f"2026 surge: {len(live)} countries above the threshold in {last_month} (not yet used)"],
    "sources": [f"Eurostat HICP, energy aggregate, monthly: prc_hicp_manr to December 2025, prc_hicp_minr (2026 classification) from January 2026, to {last_month}",
                "Eurostat gas share of energy supply (nrg_bal_c) as a pre-shock exposure control",
                "Eurobarometer respondent files (GESIS), 2001–2025: trust and satisfaction with democracy"],
    "country_note": f"gas {fr_gas:.0f}% of energy supply; average EU country {float(expo.gas_share_pct.drop('FRA').mean()):.0f}%",
    "backtest_note": "back-test: held-out spells (trust in government, this horizon) whose real outcome fell inside the calibrated single-episode range",
    "live_note": live_note,
    "single_q": single_q,
    "cautions": ["Most of the evidence is the 2021–23 surge and earlier, smaller episodes. Inside 2021–23 alone, the effect of the size of the rise cannot be told apart from zero.",
                 "The effect shows at about the second survey wave (about a year). At other horizons the changes are mostly within survey noise.",
                 "The size of the reading depends on the shape of the dose-response; the data cannot choose between a straight line and a curve that flattens above a 25% rise, so the default range covers both.",
                 "Duration is only known when a surge ends: treat that slider as a what-if, not a forecast.",
                 "This is an association across countries, not an experiment: overall inflation and the war are not controlled for after the shock, because the specification measures the total effect."],
})
D["effects"] = [r for r in D["effects"] if r["scenario"] != "E"]

# ---- back-test and France check for E: prediction +/- the conformal half-width (calibrated to cover ~90% of past episodes) ----------
q = {(r.outcome, int(r.horizon)): float(r.conformal_half_width) for r in conf.itertuples()}
bt = pd.read_csv(OUT / "e_backtest.csv")
bt_rows = [{"scenario": "E", "outcome": ID[r.outcome], "horizon": int(r.horizon), "episode": f"{r.iso3} {str(r.date)[:7]}",
            "pred_low": round(r.predicted - q[(r.outcome, int(r.horizon))], 1), "pred_high": round(r.predicted + q[(r.outcome, int(r.horizon))], 1),
            "actual": round(r.actual, 1)} for r in bt.itertuples()]
fc = pd.read_csv(OUT / "e_france_check.csv")
fc_rows = [{"scenario": "E", "episode": "France 2021–23 (price cap in force)", "outcome": ID[r.outcome], "horizon": int(r.horizon),
            "pred_low": round(r.predicted - q[(r.outcome, int(r.horizon))], 1), "pred_high": round(r.predicted + q[(r.outcome, int(r.horizon))], 1),
            "actual": round(r.actual, 1)} for r in fc.itertuples()]
D["backtest"] = [r for r in D["backtest"] if r["scenario"] != "E"] + bt_rows
D["france_check"] = [r for r in D["france_check"] if r["scenario"] != "E"] + fc_rows

# ---- scenario S1: the team's own panel model (notebooks/Shock_1_gov_collapse.ipynb), exported by src/build_s1_grid.py ---------------------
g1 = pd.read_csv(OUT / "s1_grid.csv")
c1 = pd.read_csv(OUT / "s1_conformal.csv")
ds, fs = sorted(g1.days.unique().tolist()), sorted(g1.falls24.unique().tolist())
cells1 = {}
for (o, h), g in g1.groupby(["outcome", "horizon"]):
    g = g.set_index(["days", "falls24", "early"]).reindex([(d, f, e) for d in ds for f in fs for e in (0, 1)])
    cells1[f"{ID[o]}|{int(h)}"] = {"line": [round(float(v), 2) for v in g.reading], "line_low": [round(float(v), 2) for v in g.ci_low],
                                    "line_high": [round(float(v), 2) for v in g.ci_high], "n": int(g.n_events.iloc[0])}
D["grid"]["S1"] = {"params": ["days_no_gov", "cabinet_falls_24m", "early_election"], "axes": [ds, fs, [0, 1]], "shapes": False, "cells": cells1}
S1 = next(x for x in D["scenarios"] if x["id"] == "S1")
n1 = int(g1.n_events.iloc[0])
q1 = {(r.outcome, int(r.horizon)): float(r.conformal_half_width) for r in c1.itertuples()}
beats = int((c1.mae_model < c1.mae_no_change).sum())
S1.update({
    "placeholder": False, "grid": True,
    "status": "Estimated · no detectable effect",
    "evidence": "medium",
    "evidence_note": f"{n1} reviewed government falls in 22 EU countries; effects are close to survey noise, and a result of no detectable change is a valid result",
    "params": [
        {"id": "days_no_gov", "label": "Days without a full-powered government", "unit": "days", "min": 0, "max": ds[-1], "step": 10, "default": 60, "type": "range",
         "note": f"Longest observed: {ds[-1]} days (Hungary, 2008–10; the next longest is Italy, 647). Known only when the crisis ends."},
        {"id": "cabinet_falls_24m", "label": "Cabinet falls in the last 24 months", "unit": "", "min": 0, "max": fs[-1], "step": 1, "default": 1, "type": "range",
         "note": f"Observed 0 to {fs[-1]}; one earlier fall is typical."},
        {"id": "early_election", "label": "Ends with an early election", "unit": "", "min": 0, "max": 1, "step": 1, "default": 0, "type": "toggle"}],
    "threshold": ("Early end of a cabinet through a coalition break-up or a lost parliamentary vote (PPEG codes Diss and LoPS, as CPDS codes 4 and 5), "
                  "dated and confirmed by the team's case review (15 November 2026). No numeric threshold; set by PPEG's coding plus the team's review. Estimated without France."),
    "episodes": [f"{n1} falls in 22 EU countries, 2006–2025, estimated without France", "France's own falls, Barnier (December 2024) and Bayrou (September 2025), are the out-of-sample check"],
    "sources": ["PPEG 2025 (cabinet termination codes) and the team's case review (data/reference)", "Eurobarometer respondent files (GESIS), 2005–2025: trust and satisfaction with democracy",
                "Eurostat: unemployment, growth and inflation as controls"],
    "country_note": "",
    "backtest_note": "back-test: held-out falls (trust in government, this horizon) whose real outcome fell inside the calibrated single-episode range",
    "fc_note": "The out-of-sample check on France's falls (Barnier, Bayrou) is only available for the first wave after: later waves already contain the next fall.",
    "single_q": {f"{ID[o]}|{h}": round(q, 1) for (o, h), q in q1.items()},
    "cautions": ["No outcome shows a change larger than survey noise with a range that excludes zero. Read every reading here as 'no detectable change', not as a small effect in a direction.",
                 f"In the back-test the model does better than simply predicting no change in {beats} of {len(c1)} outcome-horizon cells: knowing the length of the crisis, earlier falls and an early election does not help predict the change in trust.",
                 "Trust in government was already falling before these governments fell (the placebo fails for that outcome), so a drop around a fall is not evidence that the fall caused it.",
                 "Days without a full-powered government is only known when the crisis ends, so that slider is a what-if, not a forecast.",
                 "The falls are dated from news and encyclopedia sources and have not been checked against official records."],
})
sc = [r for r in D["scenarios"] if r["id"] == "S1"]
D["effects"] = [r for r in D["effects"] if r["scenario"] != "S1"]
bt1 = pd.read_csv(OUT / "s1_backtest.csv")
bt1_rows = [{"scenario": "S1", "outcome": ID[r.outcome], "horizon": int(r.horizon), "episode": r.episode,
             "pred_low": round(r.predicted - q1[(r.outcome, int(r.horizon))], 1), "pred_high": round(r.predicted + q1[(r.outcome, int(r.horizon))], 1),
             "actual": round(r.actual, 1)} for r in bt1.itertuples()]
fc1 = pd.read_csv(OUT / "s1_france_check.csv")
fc1_rows = [{"scenario": "S1", "episode": r.episode, "outcome": ID[r.outcome], "horizon": int(r.horizon),
             "pred_low": round(r.predicted - q1[(r.outcome, int(r.horizon))], 1), "pred_high": round(r.predicted + q1[(r.outcome, int(r.horizon))], 1),
             "actual": round(r.actual, 1)} for r in fc1.itertuples()]
D["backtest"] = [r for r in D["backtest"] if r["scenario"] != "S1"] + bt1_rows
D["france_check"] = [r for r in D["france_check"] if r["scenario"] != "S1"] + fc1_rows

# ---- scenario S2: notebooks/Shock_2_financial_crisis_analysis.ipynb, section 9b ---------------------------------------------------------------
g2 = pd.read_csv(OUT / "s2_grid.csv")
hz = pd.read_csv(OUT / "s2_dashboard_horizons.csv")
c2 = pd.read_csv(OUT / "s2_dashboard_conformal.csv")
bt2 = pd.read_csv(OUT / "s2_dashboard_backtest.csv")
ID2 = {"trust_gov": "trust_gov", "trust_parl": "trust_parl", "trust_parties": "trust_parties", "swd": "satisf_dem", "radical": "radical_vote", "turnout": "turnout"}
us = sorted(g2.unemp.unique().tolist())
cells2 = {}
for (o, h), g in g2.groupby(["outcome", "horizon"]):
    g = g.set_index("unemp").reindex(us)
    cells2[f"{ID2[o]}|{int(h)}"] = {"line": [round(float(v), 2) for v in g.reading], "line_low": [round(float(v), 2) for v in g.ci_low], "line_high": [round(float(v), 2) for v in g.ci_high], "n": int(g.n.iloc[0])}
D["grid"]["S2"] = {"params": ["unemp_pp"], "axes": [us], "shapes": False, "cells": cells2}
S2 = next(x for x in D["scenarios"] if x["id"] == "S2")
yrs = sorted(int(y) for y in hz["years after Lehman"].unique())
dates = hz[hz.outcome == "Trust in parliament"].set_index("years after Lehman")["median fieldwork date"]
horizons2 = [{"value": y, "label": f"about {y} year{'s' if y > 1 else ''} after Lehman (survey of {pd.Timestamp(dates[y]):%B %Y})", "short": f"+{y}y",
              "after": f"about {y} year{'s' if y > 1 else ''} after Lehman"} for y in yrs]
q2 = {(r.outcome, int(r.horizon)): float(r.half_width) for r in c2.itertuples()}
beats2 = int((bt2.assign(e=(bt2.actual - bt2.predicted).abs(), z=bt2.actual.abs()).groupby(["outcome", "horizon"]).apply(lambda g: g.e.mean() < g.z.mean(), include_groups=False)).sum())
n_cells2 = bt2.groupby(["outcome", "horizon"]).ngroups
S2.update({
    "placeholder": False, "grid": True,
    "name": "Systemic financial crisis", "status": "Estimated · 2008–13 crisis", "evidence": "medium",
    "evidence_note": "27 countries with a wide range of severity and one clear crisis; trust results are robust, the vote results are not detectable, and it is a single crisis",
    "horizons": horizons2, "default_horizon": 4,
    "params": [{"id": "unemp_pp", "label": "Rise in unemployment", "unit": "pp", "min": 0, "max": float(us[-1]), "step": 0.5, "default": 3, "type": "range",
                "note": "From the 2007 level to the peak. Observed 0 to 19.6 (Greece, Spain 18.1); only six countries rose by more than 11. Unemployment is the one severity measure: GDP adds nothing once it is in, and the sovereign spread is not stable across horizons."}],
    "threshold": "No threshold: severity is measured, not defined. The crisis is dated from Lehman (September 2008); country start dates from the ESRB/ECB crises database. Severity is the rise in the 3-month average unemployment rate from its 2007 average to its peak in 2008–2014 (Eurostat). Estimated without France.",
    "episodes": ["Euro-area crisis 2008–13: Greece, Ireland, Portugal, Spain, Italy and Cyprus, the six stress countries", "All 27 EU countries enter the estimate, each with its own severity (France excluded as the held-out case)"],
    "sources": ["Eurostat monthly unemployment (une_rt_m), 2000 to October 2026", "Eurobarometer respondent files (GESIS), 2006–2016: trust and satisfaction with democracy",
                "ParlGov and PopuList 4.0: radical vote at 140 election pairs; PPEG and IDEA: turnout", "ESRB/ECB European financial crises database (crisis dates)"],
    "country_note": "unemployment rose 2.5 points from 2007 to its peak",
    "backtest_note": "back-test: held-out countries (trust in government, this horizon) whose real outcome fell inside the calibrated single-country range",
    "fc_note": "The check on France is available for the survey outcomes only (the vote outcome comes from a different model).",
    "single_q": {f"{ID2[o]}|{h}": round(q, 1) for (o, h), q in q2.items()},
    "cautions": ["This is a comparison across countries in one crisis, not an experiment: the countries hit hardest also had bank rescues, bailouts, austerity and political crises of their own, and the data cannot separate unemployment from those.",
                 f"The straight line is mostly the six stress countries against the rest. Outside them the slope for trust in parliament is about a third as steep, so the reading for a moderate rise understates the contrast between countries and overstates what a moderate rise did on its own. Leave-one-country-out the line still beats 'no change' in {beats2} of {n_cells2} outcome-horizon cells.",
                 "Trust builds for about five years and recovers only partly: about two thirds of the trough is still there after eight years. Pick the horizon with this in mind.",
                 "The radical and populist vote are not detectably related to the rise in unemployment (140 election pairs). That is a statement about this measurement: it does not show the crisis left the party system unchanged.",
                 "Unemployment is the channel and a stand-in for everything that came with it: the reading is the total effect, not the effect of jobs alone."],
})
D["effects"] = [r for r in D["effects"] if r["scenario"] != "S2"]
bt2_rows = [{"scenario": "S2", "outcome": ID2[r.outcome], "horizon": int(r.horizon), "episode": r.iso3,
             "pred_low": round(r.predicted - q2[(r.outcome, int(r.horizon))], 1), "pred_high": round(r.predicted + q2[(r.outcome, int(r.horizon))], 1), "actual": round(r.actual, 1)} for r in bt2.itertuples()]
fc2_rows = [dict(r, episode="France 2008–13 (unemployment +2.5 points)") for r in bt2_rows if r["episode"] == "FRA"]
D["backtest"] = [r for r in D["backtest"] if r["scenario"] != "S2"] + bt2_rows
D["france_check"] = [r for r in D["france_check"] if r["scenario"] != "S2"] + fc2_rows

# ---- meta -----------------------------------------------------------------------------------------------------------------------
D["meta"].update({"version": "prototype-0.2",
                  "note": "All three scenarios and the baselines are estimates from the notebooks."})
for s in D["scenarios"]:
    if s["id"] not in ("E", "S1", "S2"):
        s["placeholder"] = True

header = ("// Democracy Stress Test MVP - data file (built by src/build_dashboard_data.py; do not edit by hand).\n"
          "// S1: notebooks/Shock_1_gov_collapse.ipynb (via src/build_s1_grid.py). E: notebooks/Shock_E_energy_price.ipynb. S2: notebooks/Shock_2_financial_crisis_analysis.ipynb, section 9b.\n"
          "// All three read `grid` (reading and bootstrap range over the slider axes) instead of additive effect rows.\n")
(DASH / "data.js").write_text(header + "window.MVP_DATA = " + json.dumps(D, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf8")
print(f"S2: {len(cells2)} grid cells, horizons {yrs}, {len(bt2_rows)} back-test rows, {len(fc2_rows)} France-check rows")
print(f"Wrote dashboard/data.js: E {len(cells)} grid cells ({len(ys)} x {len(ms)}), S1 {len(cells1)} cells ({len(ds)} x {len(fs)} x 2); back-test rows E {len(bt_rows)}, S1 {len(bt1_rows)}; France check E {len(fc_rows)}, S1 {len(fc1_rows)}")
print("Baselines:", {k: v for k, v in base.items()}, "turnout", round(float(turnout), 1))
