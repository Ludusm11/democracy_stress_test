# S1 pilot: input and output variables

**Question to test:** Can information available when a government loses parliamentary support help predict the subsequent change in trust in the national parliament? This is a proposed prediction task. Nothing is fitted yet, and nothing here is a causal estimate.

## Status

| | |
| --- | --- |
| Built | A reviewed event table, an episode dataset with inputs, controls and outputs ([`s1_episode_dataset.csv`](../data/processed/s1_episode_dataset.csv)), and a [variable dictionary](../data/processed/s1_variable_dictionary.csv) that gives every column's timing and source. Both are rebuilt by `src/build_s1_dataset.py`, which `run_analysis.py` runs. |
| Sample | 14 reviewed S1 episodes in 9 countries (Romania has 6): 13 S1 episodes and France 2024–25 held out. 12 have a complete parliament-trust window (11 plus France). `sample_group` splits the 13: **8 clean** (no coded election or other reviewed event before the post wave ends), **3 broad only** (Bulgaria 2022, Malta 2012, Netherlands 2012: an election intervenes), and **2 without a wave in the fixed 90–270-day window** (Romania 2018, 2019). |
| Not built | A day-0 measure of how large the shock is (for example the margin of the vote that toppled the government, which needs official vote records), a frozen prediction time, a fitted model, and the day-30 facts that need manual research (formation attempts, whether an election had been called). Malta has no radical vote share because no radical party could be linked. |
| Decided (one reviewer, 15 Nov 2026; team to confirm) | The 8 `review` cases: 7 are S1 episodes and France is held out. Overlaps are flags, not exclusions. Reasoning in [s1_review_cases.md](s1_review_cases.md). |
| Not decided | The prediction time, and the checks listed under "Decisions for the team". |

With 8 clean episodes, the right next step is a descriptive comparison. Among them the parliament-trust change beyond the comparison group runs from **−8 to +5 points, median +0.4**. That is too few and too varied to fit or validate a model.

## Source and coverage audit

Run `.venv/bin/python src/audit_s1_variables.py`. It reads the locally stored [PPEG 2025v1 government data](../data/raw/ppeg_2025v1/) and [Eurobarometer trust trend](../data/processed/eurobarometer_trust_trend.csv), then writes [candidate events](../outputs/s1_feasibility/candidate_events.csv) and a [coverage summary](../outputs/s1_feasibility/coverage_summary.csv).

The audit finds **28** European PPEG cabinets coded `LoPS` (lack of parliamentary support) whose successor was inaugurated from 2005 onward in a country covered by the trust series. All 28 have a parliamentary-trust wave within 365 days on either side of the **successor's inauguration date**. The broader review queue adds 49 `Diss` (cabinet dissension) and 65 `ResPM` (prime-minister resignation) records. These are **candidate cabinet records, not 142 independent shocks or training examples**.

PPEG's `rft` is the reason the *ending* cabinet terminated; `idate` is the date a cabinet was *inaugurated*. The next cabinet's `idate` is therefore **not necessarily the date the government fell**. The pre/post values in `candidate_events.csv` only check survey availability around this proxy.

## Review of all 28 `LoPS` records

The [case-by-case review](../data/reference/s1_verified_events.csv) records a dated event, mechanism, episode ID, evidence link, and inclusion decision for every `LoPS` cabinet. The [review summary](../outputs/s1_feasibility/review_summary.csv) counts **14 S1 cases**: 13 marked `yes` and France marked `held_out`. The other 14 comprise 5 primarily scandal/integrity cases (S3), 3 financial-crisis cases (S2), 4 failed post-election government formations, 1 presidential-election failure, and 1 duplicate caretaker confidence failure. These are decisions by one reviewer that the team should confirm; PPEG does not supply the scenario labels.

| Current decision | Reviewed cabinets |
| --- | --- |
| S1 `yes` (13) | Bulgaria Petkov 2022; Czechia Topolánek 2009; Estonia Rõivas 2016; Malta Gonzi 2012; Netherlands Rutte 2012; Romania Ungureanu 2012, Grindeanu 2017, Tudose 2018, Dăncilă 2019, Orban 2020, Cîțu 2021; Slovakia Heger 2022; Sweden Löfven 2021 |
| S1 `held_out` (1) | France Barnier 2024 |
| S3 overlap (5) | Austria Kurz 2019; Spain Rajoy 2018; Luxembourg Juncker 2013; Portugal Montenegro 2025; Slovenia Janša 2013 |
| S2 overlap (3) | Hungary Gyurcsány 2009; Italy Monti 2012; Slovakia Radičová 2011 |
| Post-election formation (4) | Czechia Topolánek 2006 and Babiš 2018; Poland Morawiecki 2023; Portugal Passos Coelho 2015 |
| Other / duplicate (2) | Greece Samaras 2014: failed presidential election; Slovakia Ódor 2023: continuation of the Heger crisis |

The seven previously uncertain non-France cases were included and their economic-crisis, COVID and same-prime-minister overlaps were flagged, as explained in [s1_review_cases.md](s1_review_cases.md). France remains held out. Official vote records are still needed for Malta 2012 and Romania 2012 and 2021. The evidence links have not been re-checked by a second person.

## Variables

[`s1_variable_dictionary.csv`](../data/processed/s1_variable_dictionary.csv) lists all 93 columns with their timing, source and definition. The groups below give the logic.

Every column has one timing:

- **`day0`**: known on the event date.
- **`day30`**: known 30 days after it (a day-30 prediction may use these and every `day0` column).
- **`post_event_descriptor`**: known only afterwards. Useful for describing an episode, not allowed as a predictor.
- **`outcome`**: what the pilot tries to describe or predict.
- **`design`** and **`label`**: not predictors.

| Role | Columns | Timing and note |
| --- | --- | --- |
| Event | `event_type`, `event_date`, `flags`, `sample_group` | Hand-coded in the case review. `flags` records economic_crisis_context, same_pm_returned, covid_shock_in_window, election_in_window and wider_crisis_continues; `sample_group` is derived (held_out, clean, broad_only, no_post_wave). |
| Government weakness | `majority_shortfall`, `majority_shortfall_with_support`, `support_seat_share`, `government_plus_support_seat_share`, `pm_party_share_of_government`, `largest_opposition_party_seat_share`, `coalition_lr_spread`, `coalition_parties_rated`, plus `government_type`, `government_seat_share`, `government_parties`, `ending_cabinet_age_days` | `day0`. How far the cabinet was from a majority (with and without supporting parties), how much it leaned on the prime minister's party, how strong the biggest opposition party was, and how far apart the governing parties are on CHES's 0 to 10 left-right scale (0 for a single party; blank for 4 of 14 episodes where a governing party has no CHES rating, and based on party links nobody has checked). Seat shares are PPEG's when the cabinet formed, not when it fell. Supporting parties are coded without a coalition agreement and PPEG says that coding is probably incomplete in some countries. These describe how weak the government was, **not how large the shock was**. |
| Instability | `cabinets_24m_before`, `early_endings_24m_before` | `day0`. Cabinets inaugurated and early endings (`LoPS`, `Diss`, `ResPM`, `IoHS`) in the 24 months up to the event. The next inauguration stands in for the end date. |
| Baseline trust | `*_pre_trust_pct`, `*_pre_waves` | `day0`. Mean of the last two Eurobarometer waves ending before the event, for parliament, government and parties. |
| Economy | `unemployment_pct`, `gdp_growth_pct`, `inflation_pct`, `econ_year` | `day0`. Eurostat annual values for year t−1 if the event is on or after 1 May, otherwise t−2. This is an **assumed** publication lag, not checked against release calendars. |
| Post-event descriptors | `cabinets_inaugurated_after_event`, `election_before_post_wave`, `another_reviewed_event_before_post_wave`, `complete_parl_window`, `clean_window` | Not predictors. `clean_window` does not rule out unreviewed shocks or continuing instability. |
| Crisis length | `days_until_non_caretaker_cabinet`, `successor_is_caretaker` | **Outcome, not input.** How long the crisis lasted: days from the event to the next cabinet not coded expert or caretaker. It measures cabinet status in PPEG, not legal powers, and is only known when the crisis ends. |
| Trust outcomes | `parl_`, `gov_`, `parties_` + `post_trust_pct`, `change_pp`, `comparison_change_pp`, `change_beyond_comparison_pp` | Outcome. First Eurobarometer wave starting 90–270 days after the event, minus baseline, minus the same change in EU27 countries with no reviewed event or reference episode in that window (14–23 countries). |
| Day 30 | `d30_successor_inaugurated`, `d30_days_to_successor`, `d30_successor_is_caretaker`, `d30_election_held` | `day30`. From PPEG inauguration dates: a new cabinet within 30 days, how many days, and whether it is expert or caretaker. PPEG records inaugurations only, so an outgoing cabinet that stays on as caretaker counts as "no successor". Whether an election had been *called* is not recorded; only whether one was held. |
| Radical vote | `radical_prev_pct` (`day0`), `radical_next_pct`, `radical_change_pp`, and `radical_disputed_*` | Far-right plus far-left vote share, from PopuList 4.0 parties linked to PPEG (see below). Disputed or partial parties are kept in separate columns, not added. |
| Election outcomes | `turnout_change_pp`, `effective_parties_change`, with `prev_`/`next_` values and dates | Outcome, from PPEG. The next election can be years later (`next_election_gap_days`). Alliance member parties count as one list. |
| Second trust source | `ess_*` | ESS parliament trust (0–10) before and after, with the gaps in days. The change is filled only when both rounds are within two years of the event, which holds for 3 episodes. Not comparable with the Eurobarometer percentages. |
| Design | `compulsory_voting` | IDEA's yes/no field flags a legal rule, not whether it was enforced. Use it for a sensitivity check; do not automatically exclude rows. IDEA says Bulgaria's rule became unenforceable in 2017. |

## Choosing the prediction time

Freeze this **before** fitting a model. The dataset supports a prediction made on the event date (**day 0**) with every `day0` column.

A prediction at **day 30** may also use the `d30_` columns. In this sample 7 of 14 episodes had a successor within 30 days (all 7 non-caretaker) and none had an election by then. Formation attempts, and whether an election had been called, are not collected and would need manual research. The crisis length (`days_until_non_caretaker_cabinet`) is an outcome and must not be used at day 0 or day 30.

## Why France shows two different changes

Both are observed before/after differences, not effects of the shock.

| Where | Window | France |
| --- | --- | --- |
| Shocks view and notebook 02 | The whole 2024–25 episode (June 2024 to October 2025). Two waves before it, the first wave after its end, against EU countries with no reference episode. | 27% → 23%, **−4 points** beyond the comparison group |
| S1 dataset | The Barnier censure of 4 December 2024. Two waves before it, the first wave starting 90–270 days after. | 23.5% → 24%, +0.5 points, **−0.7 beyond** the comparison group |

Malta 2012 appears as +33 points raw and +33.6 beyond the comparison group. It has an election in the window (March 2013), so it is not the effect of the December 2012 budget defeat.

## What the data cannot do yet

- **A reliable radical vote share.** The shares are lower bounds and rest on links nobody has checked.
  - [`popu_ppeg_links.csv`](../outputs/data_audit/popu_ppeg_links.csv) links 41 of 49 far-right and far-left PopuList party rows in the eight other S1 countries to PPEG parties, by Manifesto ID, ParlGov vote share or name. 24 are backed by two or more methods and 17 by one (11 by name alone).
  - 7 PopuList parties stay unlinked (for example Slovakia's Republic, which polled 4.75% in 2023 and sits inside PPEG's "Others" row) and 1 is a conflict (Slovakia's Vlast).
  - Malta has no linked radical party, so its radical vote is blank, not zero.
  - **Borderline parties are kept out of the radical total.** PopuList 4.0 flags some far-right and far-left classes as borderline, including Bulgaria's BSP, France's LR, Sweden's Left Party and the Dutch Socialist Party. Their vote share is reported separately in the `radical_disputed_*` columns. The provisional choices are in [s1_review_cases.md](s1_review_cases.md); external supporting sources still need to be recorded.
  - France uses the team's own table ([`radical_parties.csv`](../data/reference/radical_parties.csv)), with LR and the New Popular Front kept apart as in notebook 03.
  - [`ches_coverage.csv`](../outputs/data_audit/ches_coverage.csv) shows how well parties link to CHES positions. None of these links has been checked by a person.
- **Model validation.** A fit would need enough independent episodes to beat a no-change or pre-trend baseline. 8 clean episodes in 5 countries do not.
- **Independence.** Romania supplies 6 episodes, and several share the same next election.

## Decisions for the team

1. ~~Which of the 8 `review` cases count as S1.~~ Agreed by one reviewer on 15 November 2026 (see [s1_review_cases.md](s1_review_cases.md)); the team should confirm and retrieve the missing official vote records (Malta, Romania 2012 and 2021).
2. The prediction time: day 0, day 30, or another.
3. Whether to widen the event pool to `Diss` and `ResPM` cases under the same inclusion rules.
4. A person to check the evidence links in the case table, and the party, alliance and PopuList links.
5. Whether borderline PopuList parties (BSP, LR, the Left Party and others) count as radical, and how to treat parties that PPEG hides in "Others". A proposal is in [s1_review_cases.md](s1_review_cases.md).

## Next data work

1. Retrieve the missing official vote records, and keep France out of model fitting.
2. If day 30 is chosen, research formation attempts and whether an election had been called by then; the successor and caretaker columns are already built.
3. Check the PopuList-to-PPEG links, especially the 17 backed by one method, and decide Bulgaria's BSP.
4. Publish a descriptive comparison of the clean episodes and the measurement limits before any model.

## Larger set of S1 cases (built)

Eight clean episodes are too few to see a pattern, so `src/build_s1_dataset.py` also writes a larger **S1-only** table, [`s1_broad_episode_dataset.csv`](../data/processed/s1_broad_episode_dataset.csv). It has the same inputs, controls and trust outputs as the core dataset, plus the day the government fell and when the crisis ended.

**Where the cases come from.** The 14 reviewed S1 episodes (France held out), plus cases from PPEG's 47 cabinets coded as ended by *dissension*. Many of those were not a government falling, so each of 45 was researched ([`s1_researched_dates.csv`](../data/reference/s1_researched_dates.csv): date, how it fell, sources, confidence). Result: **20 include** (the government lost its majority, lost a vote or resigned), **20 exclude** (reshuffles, a party leaving while the majority held, scandal resignations counted under S3, and 5 Cyprus cases because a presidential system has no government that can fall) and **5 need a check** (the date or the majority could not be confirmed). 16 of the 20 included are rated high confidence and 4 medium. The dates come from news and encyclopedia sources and none has been checked against an official record.

**Size.** 34 episodes: 14 reviewed and 20 researched. 31 have a complete trust window; **19 are clean** (no election or other ending before the "after" survey), in 11 countries, and 12 more have an election or another ending in between.

**Fall date and ending.** `event_date` is the day the government fell: the first of losing its majority, losing a vote, or resigning. `successor_start` is when the next cabinet took office (possibly a caretaker) and `full_government_start` when the first cabinet not coded expert or caretaker took office, the end of the crisis in PPEG terms, with the gaps in days. They are listed in section 9 of the notebook.

**Not S1, so not counted:** prime ministers who resigned (45 clean cases), head-of-state interventions, and the reviewed financial-crisis (S2), scandal (S3) and failed-formation cases. They still screen windows (an ending of any kind in the same country makes a window not clean and removes that country from the comparison group). [`s1_all_endings_dataset.csv`](../data/processed/s1_all_endings_dataset.csv) holds all 135 endings for the sensitivity check; its unresearched cases use the successor's inauguration as an approximate date.

**Result (Part 2 of [`Shock_1_gov_collapse.ipynb`](../notebooks/Shock_1_gov_collapse.ipynb)).** Median change in trust against other EU countries: −2.5 points (95% range −7.8 to +2.0, resampling countries); 9 of 19 clean cases fell by more than 3 points and 4 rose by more than 3. Counting prime-minister resignations too gives −1.4. The researched coalition break-ups (12 cases, median −7.1) fell more than the reviewed episodes (7 cases, median −1.4), which with so few cases could be chance. None of the 13 signs of weakness clears the bar that corrects for testing 13 variables; GDP growth in the year before is the strongest (−0.51, chance 0.024 before correction). An earlier version of this analysis, which used approximate dates and counted every dissension ending, found 36 clean cases and a GDP-growth lead (−0.52). With researched dates and only real falls the lead is gone and the sample is smaller.

## Other outcomes (Part 3 of the notebook)

Trust in government and in parties, turnout, the effective number of parties and the radical vote were each measured against the other EU countries over the same period (turnout, parties and radical vote: the change between the elections either side of the fall, against the same change in every other EU country; compulsory-voting elections left out; only cases whose next election came within a year). Results on the 34 S1 episodes:

| Outcome | Cases | Mean change vs. other countries | 95% range |
| --- | --- | --- | --- |
| Trust in parliament | 19 | −2.9 points | −6.2 to +0.4 |
| Trust in government | 19 | −1.7 points | −5.8 to +3.9 |
| Trust in parties | 18 | −1.1 points | −2.9 to +0.5 |
| Turnout | 15 | −0.6 points | −3.7 to +3.3 |
| Effective number of parties | 17 | −0.4 | −0.9 to +0.1 |
| Radical vote | 14 | −1.5 points | −6.8 to +2.6 |

None clears the bar for six outcomes tested (chance below about 0.008) and every range includes zero; the direction is close to even in each. The radical vote is the weakest measure. Two measurement problems were fixed on the way: PopuList classes some parties as radical only for part of the period (Belgium's N-VA from 2019), which made a relabeling look like a 30-point jump, so only parties classed the same way throughout 2000 to 2025 count; and the PPEG-linked radical shares disagreed with ParlGov by more than 3 points in about one election in eight, so an election is kept only if the two sources agree. Renamed party lists can still be missed (the Slovenian series looks suspect).


## Source definitions

- [PPEG government dataset and codebook](https://ppeg.wzb.eu/www/codebook_ppeg_gov_2025v1.pdf): `idate`, `rft`, `tog`, `gov_seat` and coverage.
- [European Commission Eurobarometer 105](https://europa.eu/eurobarometer/surveys/detail/3613): trust question and published survey data. The processed trend holds the source sheet, cell, wave and fieldwork dates.
- Every reviewed event's evidence link and source quality are in [the case table](../data/reference/s1_verified_events.csv). Examples: [French National Assembly](https://www.assemblee-nationale.fr/dyn/actualites-accueil-hub/adoption-d-une-motion-de-censure-le-plfss-2025-est-rejete-en-lecture-cmp-art.-49.3-et-le-premier-ministre-a-presente-la-demission-du-gouvernement-art.-50), [Spanish Congress](https://www.congreso.es/es/cem/mociones-de-censura), [Austrian Parliament](https://www.parlament.gv.at/gegenstand/XXVI/E/75).
