# Where the project stands

This is a first data prototype for the Democracy Stress Test. It describes what we have and what we can safely say about France. It does not yet calculate how France would respond to a future shock.

## What is ready

- We have 59 original files. Every file is listed in `raw_file_inventory.csv`. Of the Our World in Data download we keep only the two Freedom House tables; they are checked in `owid_file_audit.csv`.
- We can chart France's democracy scores, election turnout, party positions, government changes and public trust. The figures are in `figures/`.
- Eurobarometer gives a trust trend from 2005 to 2026. In its latest French wave, 12% tended to trust political parties, 21% the national government and 23% parliament.
- The 2026 CEVIPOF report also gives French trust figures. We copied seven published values into a small table and recorded the question and PDF page for each.
- The EVS/WVS survey gives answers from people in 92 countries. The French survey has 1,870 respondents in 2018.

## What needs care

- Only 35.8% of the French 2024 vote links directly to a CHES party by ID. Several large election rows are alliances. A person must check their member parties before we combine votes and party positions.
- The EVS, Eurobarometer and CEVIPOF trust questions differ. Read each survey on its own terms; their percentages are not one continuous series.
- Many IDEA election dates are January 1 placeholders. Three reported turnout rates exceed 100%. The working table flags these values and keeps the originals.
- The ESS folder has questionnaires but no survey responses.

## Best next step

Settle the two radical-vote judgment calls shown in `notebooks/03_radical_voting.ipynb` (counting Les Républicains, splitting the 2024 New Popular Front), then decide how effects around the reference episodes will be measured. Keep this report as the starting picture, not as a stress-test result.

For exact rows, source cells and further checks, use `source_profiles.csv`, `quality_issues.csv` and the tables in `data/processed/`.
