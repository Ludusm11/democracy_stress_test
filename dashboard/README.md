# Dashboard (local build)

`index.html` + `data.js` is the team's prototype page, patched so that all three scenarios show real estimates: **S1 (government collapse)**, **E (energy-price shock)** and **S2 (systemic financial crisis)**. The page keeps a per-scenario badge (green for estimated, orange for any placeholder).

| File | What it is |
| --- | --- |
| `index.html` | The page. Differences from `index_original.html`: scenarios S1, E and S2 read a precomputed `grid` and interpolate; per-scenario horizons (S2 is read in years after Lehman, not waves); a "shape of the dose-response" selector for E; a per-scenario placeholder badge; vote outcomes with no estimate show "Not estimated yet"; back-test and France check filtered by outcome and horizon for E. |
| `data.js` | Built by `src/build_dashboard_data.py`. Do not edit by hand. |
| `src/build_s1_grid.py` | Reads the S1 readings off the team's own panel model (`notebooks/Shock_1_gov_collapse.ipynb`) without touching its output files, and writes `outputs/model/s1_grid.csv` and `s1_conformal.csv`. Run it before the data builder. |
| `data_original.js`, `index_original.html` | The prototype as received (copied from the shared artifact, version 1795262560-abff). |

## Why S1 and E read a grid, not additive effect rows
The original page computes `baseline + Σ effect_per_unit × slider` and adds each parameter's range bounds. That cannot represent E (and gives wrong ranges for S1): there is a base effect and two slopes whose estimates are correlated (adding their separate ranges overstates the uncertainty), the effect only exists above the 15.6% threshold, and the dose-response has two plausible shapes. For S1 the same holds: a base effect plus three slopes with correlated estimates. `outputs/model/e_grid.csv` and `s1_grid.csv` hold the reading and its **joint wild-bootstrap range** at each combination of energy rise × duration, for every outcome and horizon, for a straight line and for a curve that flattens above 25%.

## Rebuild
```bash
.venv/bin/python src/build_s1_grid.py
.venv/bin/python src/build_dashboard_data.py
.venv/bin/python -m http.server 8766 --directory dashboard
```
Open http://127.0.0.1:8766. The grid comes from `notebooks/Shock_E_energy_price.ipynb`.

## Still to do
The vote outcomes need estimates and a baseline (the far-right and far-left classification needs a team decision). The Strait of Hormuz 2026 episode is not in the data (Eurostat energy series ends December 2025).

**S2 specifics.** One slider (the rise in unemployment), six horizons (1, 2, 3, 4, 5 and 8 years after Lehman, each tied to the survey wave nearest that date), because the crisis effect builds for about five years and recovers only partly. GDP and the sovereign spread are not offered as sliders: GDP adds nothing once unemployment is in, and the spread's coefficient changes sign between horizons (see `notebooks/Shock_2_financial_crisis_analysis.ipynb`, section 9b). The vote outcomes use the all-election panel and are not distinguishable from zero. Everything the dashboard reads for S2 is in `outputs/model/s2_grid.csv`, `s2_dashboard_*.csv`.
