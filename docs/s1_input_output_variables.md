# S1 pilot: input and output variables

**Question to test:** Can information available when a government loses parliamentary support help predict the subsequent change in trust in the national parliament? This is a proposed prediction task, not yet a fitted model or a causal estimate.

## Source and coverage audit

Run `.venv/bin/python src/audit_s1_variables.py`. It reads the locally stored [PPEG 2025v1 government data](../data/raw/ppeg_2025v1/) and [Eurobarometer trust trend](../data/processed/eurobarometer_trust_trend.csv), then writes [candidate events](../outputs/s1_feasibility/candidate_events.csv) and a [coverage summary](../outputs/s1_feasibility/coverage_summary.csv).

The current audit finds **28** European PPEG cabinets coded `LoPS` (lack of parliamentary support) whose successor was inaugurated from 2005 onward in a country covered by the trust series. All 28 have a parliamentary-trust wave within 365 days on either side of the **successor's inauguration date**. The broader review queue adds 49 `Diss` (cabinet dissension) and 65 `ResPM` (prime-minister resignation) records. These are **candidate cabinet records, not 142 independent shocks or training examples**.

PPEG's `rft` is the reason the *ending* cabinet terminated; `idate` is the date a cabinet was *inaugurated*. The next cabinet's `idate` is therefore **not necessarily the date the government fell**. The pre/post values in `candidate_events.csv` only check survey availability around this proxy.

## Review of all 28 `LoPS` records

The [case-by-case review](../data/reference/s1_verified_events.csv) records a dated event, mechanism, episode ID, evidence link, and provisional inclusion decision for every `LoPS` cabinet. The [review summary](../outputs/s1_feasibility/review_summary.csv) counts **14 potential S1 cases**: 6 marked `yes` and 8 marked `review`. The other 14 comprise 5 primarily scandal/integrity cases (S3), 3 financial-crisis cases (S2), 4 failed post-election government formations, 1 presidential-election failure, and 1 duplicate caretaker confidence failure. The classification is a research decision that can be revised as episode definitions improve; it is not supplied by PPEG.

| Provisional decision | Reviewed cabinets |
| --- | --- |
| S1 `yes` (6) | Bulgaria Petkov 2022; Estonia Rõivas 2016; Romania Grindeanu 2017, Tudose 2018, Dăncilă 2019; Slovakia Heger 2022 |
| S1 `review` (8) | Czechia Topolánek 2009; France Barnier 2024; Malta Gonzi 2012; Netherlands Rutte 2012; Romania Ungureanu 2012, Orban 2020, Cîțu 2021; Sweden Löfven 2021 |
| S3 overlap (5) | Austria Kurz 2019; Spain Rajoy 2018; Luxembourg Juncker 2013; Portugal Montenegro 2025; Slovenia Janša 2013 |
| S2 overlap (3) | Hungary Gyurcsány 2009; Italy Monti 2012; Slovakia Radičová 2011 |
| Post-election formation (4) | Czechia Topolánek 2006 and Babiš 2018; Poland Morawiecki 2023; Portugal Passos Coelho 2015 |
| Other / duplicate (2) | Greece Samaras 2014: failed presidential election; Slovakia Ódor 2023: continuation of the Heger crisis |

The `review` cases need an explicit decision before fitting: France is the held-out application case; Czechia 2009, the Netherlands 2012, and Romania 2012 overlap economic crises; Malta 2012 needs an official vote record; Romania 2021 needs the parliamentary roll call; and Romania 2020 and Sweden 2021 returned the same prime minister after a short disruption. The reviewed evidence includes official parliamentary or government records for most dates, a contemporaneous newspaper for Malta, and a public news agency for several Romanian events. Greece's 2014 case is documented by the final presidential-ballot record but remains outside S1 because the government did not lose a confidence vote.

Applying the fixed trust window to all 28 reviewed dates produces [measurement checks](../outputs/s1_feasibility/reviewed_window_checks.csv). All 14 potential S1 records have two pre-event waves; **12 have a wave 90–270 days later**. Of the 6 `yes` cases, only **4** have a complete window. These counts are cabinet records, not yet a model sample. A later election or another government crisis can fall inside the 90–270 day window. Malta's trust change of **+33 percentage points**, for example, is measured after the March 2013 election; it must not be read as the effect of losing the December 2012 budget vote.

For the French Barnier censure of **4 December 2024**, the two preceding parliamentary-trust waves average **23.5%** and the first wave starting 90–270 days later reads **24%**: an observed change of **+0.5 percentage points**. This is an observed before/after difference, not evidence that the censure increased trust.

## Proposed variable definitions

Freeze the prediction time and outcome horizon **before** fitting a model. Start with a prediction made on the verified date of a loss of parliamentary support. Each row should be one independently reviewed political episode, not one cabinet-party record or one survey wave.

| Role | Variable | Definition and timing | Available now? |
| --- | --- | --- | --- |
| Event label | Loss of parliamentary support | PPEG `rft=LoPS` is a screening flag. Verify the exact confidence or censure event from an official source; group multiple cabinet changes in one crisis. | All 28 screened and provisionally classified; 8 S1 cases require another decision |
| Baseline input | Pre-event trust | Mean of the last two Eurobarometer national-parliament trust waves **completed before** the verified event; retain both wave dates and sample information. | Yes, once event dates are verified |
| Baseline input | Government seat share | PPEG `gov_seat` of the ending cabinet at formation, on a 0–1 scale. Check missing values and subsequent parliamentary changes. | Mostly; 3 of 28 `LoPS` rows lack it |
| Baseline input | Government type | PPEG `tog` at cabinet formation, e.g. single-party or coalition, majority or minority. | Yes, subject to review |
| Baseline input | Recent economy | Eurostat unemployment and real GDP growth from the latest **published** pre-event period; record release dates if used for genuine real-time prediction. | Annual values exist; availability timing needs review |
| Shock input | Crisis mechanism | Verified event type (successful confidence vote, cabinet-party withdrawal, failed formation). Do not infer it from `rft` alone. | Requires manual coding |
| Shock input for a day-30 update | Days without a stable cabinet, formation attempts, election called | Count only what was known by day 30. Do not use the eventual full crisis duration to predict an earlier outcome. | Not yet collected |
| Output | Change in parliamentary trust | First Eurobarometer wave starting 90–270 days **after the verified event**, minus pre-event trust. Report the exact interval, intervening elections/crises, and missing cases. | Calculated for 12 of 14 potential S1 cabinet records; descriptive only |

The first output is **parliamentary trust only**. Government trust can be a second output. Election turnout and party vote share need separate models because they are observed at irregular election dates. V-Dem's annual institutional indices should not be presented as an immediate post-event response.

## Next data work

1. Resolve the 8 `review` cases, retrieve the missing official vote records, and record intervening elections and repeated crises. Keep France's 2024–25 episode out of model fitting. Decide whether `Diss` and `ResPM` cases meet the same S1 definition.
2. Make a country-episode table with one row per independent episode. Add the fixed pre-event inputs and trust outcome, plus a flag for another major event between the date and survey wave. Document missingness and the final number of usable episodes **before choosing a model**.
3. With at most 12 complete potential S1 records from this screen, first publish a descriptive comparison of cases and measurement limits. Expand the event pool only with the same inclusion rules. Attempt prediction only if the expanded set supplies enough independent episodes to evaluate against a no-change or pre-trend baseline.

## Source definitions

- [PPEG government dataset and codebook](https://ppeg.wzb.eu/www/codebook_ppeg_gov_2025v1.pdf): `idate`, `rft`, `tog`, `gov_seat` and coverage.
- [European Commission Eurobarometer 105](https://europa.eu/eurobarometer/surveys/detail/3613): trust question and published survey data. The processed trend holds the source sheet, cell, wave and fieldwork dates.
- Every reviewed event's evidence link and source quality are in [the case table](../data/reference/s1_verified_events.csv). Examples: [French National Assembly](https://www.assemblee-nationale.fr/dyn/actualites-accueil-hub/adoption-d-une-motion-de-censure-le-plfss-2025-est-rejete-en-lecture-cmp-art.-49.3-et-le-premier-ministre-a-presente-la-demission-du-gouvernement-art.-50), [Spanish Congress](https://www.congreso.es/es/cem/mociones-de-censura), [Austrian Parliament](https://www.parlament.gv.at/gegenstand/XXVI/E/75).
