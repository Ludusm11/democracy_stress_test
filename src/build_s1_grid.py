"""Export S1 (government collapse) readings for the dashboard: outputs/model/s1_grid.csv and s1_conformal.csv.

The model is the team's own, estimated in notebooks/Shock_1_gov_collapse.ipynb (EU panel, fixed effects, France left out). This script runs the
notebook's setup and estimation cells (not its plots, tables or file writers, so s1_effects.csv, s1_backtest.csv etc. are NOT touched) and
reads the readings off the fitted models:

    reading = fall + days/100 * b_days + early_election * b_early + falls_24m * b_falls

for every combination of the three sliders (days without a full government, cabinet falls in the last 24 months, early election yes/no), for each
outcome and horizon, with a wild cluster bootstrap-t 90% range that keeps the joint uncertainty of the four coefficients. The single-episode
(conformal) half-widths come from the notebook's leave-one-country-out back-test, s1_backtest.csv, as for scenario E.

Run from the project folder:  .venv/bin/python src/build_s1_grid.py
"""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/model"
NB = ROOT / "notebooks/Shock_1_gov_collapse.ipynb"

# ---- run the notebook's setup and estimation cells only ------------------------------------------------------------------------------
nb = json.loads(NB.read_text(encoding="utf8"))
ns = {"__name__": "s1_nb"}
import os

os.chdir(ROOT)
for cell in nb["cells"]:
    if cell["cell_type"] != "code":
        continue
    src = "".join(cell["source"])
    exec(compile(src, "<s1 notebook cell>", "exec"), ns)
    if "models[(outcome, h)] = (s, X, b, V, u, G)" in src:      # the estimation cell: stop here
        break
models, OUTCOMES, HORIZONS, falls, HELD_OUT = ns["models"], ns["OUTCOMES"], ns["HORIZONS"], ns["falls"], ns["HELD_OUT"]
est_falls = falls[falls.iso3 != HELD_OUT]


def wild_ci(model, combos, B=999, seed=20261124, alpha=0.10):
    """Percentile-t wild cluster bootstrap (Rademacher weights, unrestricted residuals) for linear combinations of the coefficients."""
    s, X, b, V, u, G = model
    Xv, y, bv = X.to_numpy(), s.dy.to_numpy(), b.to_numpy()
    _, inv = np.unique(s.iso3.to_numpy(), return_inverse=True)
    g = inv.max() + 1
    D = np.zeros((len(y), g)); D[np.arange(len(y)), inv] = 1.0
    XtXi = np.linalg.pinv(Xv.T @ Xv)
    n, k = Xv.shape
    adj = g / (g - 1) * (n - 1) / (n - k)
    C = np.atleast_2d(np.asarray(combos, float))
    P = C @ XtXi
    theta = C @ bv
    se_of = lambda uvec: np.sqrt(adj * ((D.T @ (Xv * uvec[:, None]) @ P.T) ** 2).sum(axis=0))
    se0 = se_of(u)
    rng = np.random.default_rng(seed)
    fitted = Xv @ bv
    T = np.empty((B, len(C)))
    for i in range(B):
        ys = fitted + rng.choice([-1.0, 1.0], size=g)[inv] * u
        bs = XtXi @ (Xv.T @ ys)
        T[i] = (C @ bs - theta) / se_of(ys - Xv @ bs)
    qlo, qhi = np.nanquantile(T, [alpha / 2, 1 - alpha / 2], axis=0)
    return theta, theta - qhi * se0, theta - qlo * se0


# ---- grid ------------------------------------------------------------------------------------------------------------------------------
DAYS_MAX = float(est_falls.days_no_gov.max())
FALLS_MAX = int(est_falls.falls_24m.max())
DAYS = sorted({0, 10, 30, 60, 100, 150, 200, 300, 400, 500, 650, int(DAYS_MAX)})
FALLS = list(range(0, FALLS_MAX + 1))
EARLY = [0, 1]
combos = [(d, f, e) for d in DAYS for f in FALLS for e in EARLY]          # row-major: days, then falls, then early
rows = []
for o in OUTCOMES:
    for h in HORIZONS:
        model = models[(o, h)]
        cols = list(model[2].index)
        C = np.zeros((len(combos), len(cols)))
        for i, (d, f, e) in enumerate(combos):
            C[i, cols.index("fall")] = 1.0
            C[i, cols.index("days")] = d / 100
            C[i, cols.index("early_election")] = e
            C[i, cols.index("falls_24m")] = f
        th, lo, hi = wild_ci(model, C)
        for i, (d, f, e) in enumerate(combos):
            rows.append({"outcome": o, "horizon": h, "days": d, "falls24": f, "early": e, "reading": th[i], "ci_low": lo[i], "ci_high": hi[i],
                         "n_events": int(model[0].fall.sum())})
grid = pd.DataFrame(rows).round(2)
grid.to_csv(OUT / "s1_grid.csv", index=False)

# ---- single-episode half-widths from the notebook's own back-test ---------------------------------------------------------------------
bt = pd.read_csv(OUT / "s1_backtest.csv")
bt["iso3"] = bt.episode.str[:3]
bt["err_model"] = (bt.actual - bt.predicted).abs()
bt["err_zero"] = bt.actual.abs()


def conformal_q(scores, level=0.90):
    n = len(scores)
    return np.sort(scores)[min(n, int(np.ceil((n + 1) * level))) - 1]


crow = []
for (o, h), g in bt.groupby(["outcome", "horizon"]):
    inside = []
    for c in g.iso3.unique():
        q_c = conformal_q(g[g.iso3 != c].err_model.to_numpy())
        inside += list(g[g.iso3 == c].err_model <= q_c)
    crow.append({"outcome": o, "horizon": h, "spells": len(g), "model_coverage": float(((g.actual >= g.pred_low) & (g.actual <= g.pred_high)).mean()),
                 "conformal_coverage": float(np.mean(inside)), "conformal_half_width": float(conformal_q(g.err_model.to_numpy())),
                 "mae_model": float(g.err_model.mean()), "mae_no_change": float(g.err_zero.mean()), "corr_pred_actual": float(g.predicted.corr(g.actual))})
conf = pd.DataFrame(crow).round(3)
conf.to_csv(OUT / "s1_conformal.csv", index=False)

print(f"s1_grid.csv: {len(grid)} rows ({len(DAYS)} day values x {len(FALLS)} earlier-fall values x 2 x {len(OUTCOMES)} outcomes x {len(HORIZONS)} horizons)")
print(f"Observed range: days without full government 0 to {DAYS_MAX:.0f}, earlier falls 0 to {FALLS_MAX}; {len(est_falls)} falls in {est_falls.iso3.nunique()} countries")
print(f"Back-test vs 'no change': model has lower error in {int((conf.mae_model < conf.mae_no_change).sum())} of {len(conf)} cells; conformal coverage {conf.conformal_coverage.mean():.2f}")
