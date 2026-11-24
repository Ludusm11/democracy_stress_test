# Energy-price shock (E): decisions and open points

Notebook: `notebooks/Shock_E_energy_price.ipynb`. Outputs: `outputs/model/e_*.csv`. Dashboard build: `src/build_dashboard_data.py`.

## Decisions, and why

| Choice | Decision | Reason |
| --- | --- | --- |
| Shock rule | Energy HICP year-on-year rate above **15.6%**: the 90th percentile of EU-member country-months from 2001 to December 2025, France left out | The specification says "top 10%, fixed in advance". 2001 start because 1997–98 holds Bulgaria's +544% hyperinflation. Fixed on data to December 2025 so the 2026 surge cannot move it |
| Spell | A run of months above the threshold, gaps of up to 2 months allowed | One surge is not cut in two by a single dip. Spells still running at the end of the data are not used for estimation |
| Sliders | Mean rise over the spell, and length in months | The specification's two sliders. Length is only known when a surge ends, so it is a what-if |
| Timing | Baseline = mean of the two waves before; after wave must start 30+ days after the spell | Removes waves that cannot yet show an effect and halves baseline noise |
| Exposure control | **Gas share of energy supply only** (2018–2020) | Measured directly and reliably. The Russian share (Eurostat records direct origin: Austria and Ireland read 0%) and the front-line indicator are checks. The main reading is the same with all three, with each alone, and with none |
| Ranges for effects | Wild cluster bootstrap-t, 999 draws | About 25 country clusters; t-ranges were too narrow |
| Ranges for one future episode | Conformal: reading ± the error 90% of past episodes stayed within | The model's own ranges covered 82% against a target of 90% |
| Dose-response | Straight line **and** a curve with a bend at 25% (22% and 30% checked); the dashboard default is the range covering both | The two eras disagree on the slope; one curve that flattens explains most of it, but the data cannot choose between the shapes. The 35% reading differs by about 1.7× |
| Two eras | Estimated separately as a check, not as the main model | A partially pooled slope was tried and dropped: it averaged in the earlier eras' steep slope, which was observed only at 16–28% rises and does not apply at 35% |
| Held-out cases | France is never used to estimate. Back-tests leave out one country at a time; a forward test trains on spells before mid-2020 | Same rule as the S1 notebooks. Every test is scored against "no change" |
| 2026 data | Old series to December 2025, new series (`prc_hicp_minr`, ECOICOP v2) from January 2026 | They agree where they overlap |

## What the results support
- A fall in trust of a few points about **a year** after a large surge (second wave); the first wave is flat; later waves are mostly noise except for the effect of duration.
- The size is uncertain by a factor of about two because of the shape of the dose-response, and wider still for a single episode.
- A pattern across countries, not a proven cause: overall inflation and the war are not controlled for after the shock (the specification measures E's total effect).

## What it does not support
- Any statement about the 2026 surge's effect: no Eurobarometer wave after it is published (readings in the notebook are what-ifs).
- The size of the effect of a surge above about 45% (few spells there).
- That the earlier, smaller episodes predict how much a large surge hurts: the forward test gets the pattern across countries roughly right (median correlation 0.43) but the size wrong (actual about 0.2 times predicted).

## Open points
1. **Respondent-level analysis** (households with larger energy burdens against others, inside the same country and wave). The only fix that could sharpen the result. It needs the GESIS respondent files (not in the repository) and pre-determined household variables.
2. **Ex-ante input for the dashboard.** The rise over the first three months, with no duration, is preferred by BIC in 12 of 16 cells (all 8 at the first two waves). A dashboard on that input is feasible but needs its own slider and limits.
3. **Autumn 2026 Eurobarometer** is the first real test of the model on the 2026 surge.
4. Radical vote at the next election, months to the next scheduled election, and a joint E and S2 estimate are not built.
5. The dashboard's S1 and S2 are still placeholders.
