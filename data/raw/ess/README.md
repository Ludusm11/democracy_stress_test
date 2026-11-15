# European Social Survey (ESS) source notes

## Intended dataset

- Source: https://ess.sikt.no/en/data-builder/
- First prototype: select **France** and all available standard ESS rounds (1–11), then download the **CSV** with the variables below. The portal requires an ESS login.
- Latest round currently listed in the portal: ESS11 (2023/24). The ESS11 integrated file is edition 4.2, DOI: https://doi.org/10.21338/ess11e04_2 .
- Alternative for a Europe comparison: select France and the comparison countries together in the Datafile Builder, using the same rounds and variables.

## Select these variables

- Identifiers: `cntry`, `essround`, `idno`.
- Democracy and political trust: `stfdem` (satisfaction with democracy), `stfgov` (satisfaction with government), `trstprl` (trust in parliament), `trstplt` (trust in politicians), `trstprt` (trust in political parties).
- Context: `polintr` (interest in politics), `vote` (voted in last national election), `lrscale` (self-placement on left-right scale), `ppltrst` (social trust).
- Weights: `anweight`, `pspwght`, `pweight`, `dweight` when available. The ESS weighting guide recommends `anweight` by default; `pspwght` also works for single-country estimates. Weights and variable availability can differ by round.
- Preserve interview date/year variables supplied by the builder when available. Rounds are fielded across calendar years, so do not equate a round number with one calendar year.

## First analysis

Calculate weighted round-level estimates for France for `stfdem`, `trstprl`, and `trstprt`. Report unweighted valid sample size and the share of missing responses for each estimate. Treat these as measured public attitudes at survey time, not as a measured response to a future stress scenario.

## Files here

- `ESS11_source_questionnaire.pdf`: https://www.europeansocialsurvey.org/sites/default/files/2024-01/ESS%20Round%2011%20Source%20Questionnaire_FINAL_Alert%2004.pdf
- `ESS_weighting_guide.pdf`: https://www.europeansocialsurvey.org/sites/default/files/2023-06/ESS_weighting_data_1_1.pdf

## Access

The ESS Data Portal requires login for data downloads. Its API requires a user ID for usage statistics; the ID is shown after login at https://ess.sikt.no/en/api . The data file has not yet been downloaded into this folder.

## Where the respondent file goes, and what the pipeline builds from it

Save the Data Builder CSV as `data/raw/ess/Datafile-subset.csv` (the pipeline also finds it in `data/new/Datafile-subset/`). It is ignored by git. `src/build_ess_tables.py` (run by `run_analysis.py`, skipped if the file is missing) builds:

- `data/processed/ess_respondents_slim.csv`: about 30 useful columns per respondent, with refusal, don't-know and no-answer codes turned into blanks. Ignored by git, because respondent data may not be redistributed.
- `data/processed/ess_country_round_summary.csv`: one row per country and round. Weighted means (`pspwght`) of trust in parliament, politicians, parties, the legal system and the EU parliament, satisfaction with democracy, government and the economy (all 0–10), self-reported turnout among eligible voters, valid counts, and interview dates. Aggregates only, safe to commit.

Limits: interview dates are missing for ESS round 10 in several countries (including Austria and Spain), round 5 Estonia and round 9 Bulgaria (see `interview_date_share`). `trstprt` was not asked in round 1. Self-reported turnout is higher than real turnout. ESS trust uses 0–10, not Eurobarometer's "tend to trust", so the two are not one series.
