# S1: the 8 unclear cases, decided

Decided by one reviewer on 15 November 2026. **The team should confirm.**

**Rule:** a case counts if a government really fell. A complication (financial crisis, COVID, same prime minister back) is a note, not a reason to drop it. France is kept aside because it is the country we apply the results to.

**Reading the table:** trust is the share who "tend to trust" parliament. *Before* is the average of the two surveys before the event, *after* is the first survey starting 3 to 9 months later. *vs. others* subtracts the change in EU countries without an event coded in this project. *Clean* means no PPEG parliamentary election or separately reviewed event occurred before the post-survey ended. Other shocks can still overlap.

| Case | What happened | Trust before → after | vs. others | Clean? | Decision |
| --- | --- | --- | --- | --- | --- |
| Czechia 2009 | No-confidence vote, 24 Mar | 18% → 15% | +2.4 | Yes | In. Note: financial crisis |
| Romania 2012 | No-confidence vote, 27 Apr | 11% → 13% | +5.0 | Yes | In. Note: austerity |
| Romania 2020 | No-confidence vote, 5 Feb; same PM back in March | 26.5% → 27% | −0.4 | Yes | In. Notes: same PM, COVID |
| Romania 2021 | No-confidence vote, 5 Oct | 27.5% → 28% | +1.1 | Yes | In. Official roll call still needed |
| Sweden 2021 | No-confidence vote, 21 Jun; same PM back 7 Jul | 70.5% → 64% | −4.7 | Yes | In. Note: same PM returned |
| Malta 2012 | Budget defeat, 10 Dec; election 9 Mar 2013 | 29% → 62% | +33.6 | No | In, but not clean: the jump follows a change of government |
| Netherlands 2012 | Government resigned, 23 Apr, after a support party left; election in Sept | 56.5% → 53% | −0.5 | No | In, but not clean |
| France 2024 | Censure vote, 4 Dec | 23.5% → 24% | −0.7 | Yes | Kept aside |

**Result:** 13 cases plus France. 8 meet the narrow clean-window rule. 3 have an election before the post-survey (Bulgaria 2022, Malta, Netherlands). 2 have no survey starting in the fixed 90–270-day window (Romania 2018, 2019).

## Radical parties

PopuList marks some party classes as *borderline*. One reviewer made these provisional choices; the outside sources behind them still need to be linked and checked:

- **BSP (Bulgaria):** kept outside the main radical total because its classification is disputed.
- **LR (France):** kept outside the main radical total, as in notebook 03.
- **AUTO (Czechia):** treated as borderline; it matters for the 2025 election.

**Rule applied:** every borderline party is left out of the radical total and shown in a separate column, on the left and the right alike. Both columns are in the data if the team prefers to count them. Slovakia's Republic party (4.75% in 2023) can't be counted: the election data hide it in "Others".

## Still to check by a person

- Official vote records for Malta, Romania 2012 and Romania 2021 (today's sources are news).
- The date Orban returned as PM in 2020.
- The evidence links in [`s1_verified_events.csv`](../data/reference/s1_verified_events.csv): I used news and encyclopedia sources, and did not open the official records or the PopuList manual.

Decisions are recorded in `s1_verified_events.csv` (columns `flags`, `decision_note`) and `s1_episode_dataset.csv` (columns `flags`, `sample_group`). Full variable list: [`s1_input_output_variables.md`](s1_input_output_variables.md).
