# Our World in Data: Freedom House tables

Captured on 12 November 2026 from the [Democracy Data Explorer](https://ourworldindata.org/explorers/democracy).

## Contents

- `explorer/073_freedom-house__freedom__political-rights-score.csv`: Freedom House political rights score.
- `explorer/075_freedom-house__freedom__civil-liberties-score.csv`: Freedom House civil liberties score.
- `index.csv`: inventory of the original download (one row per requested file, with URL, status, size, SHA-256 hash and CSV header).

`src/audit_data.py` adds the two scores into `freedom_score` (`data/processed/freedom_house_country_year_owid.csv`).

The original download had 270 chart and explorer tables (V-Dem, Regimes of the World, Lexical Index, Freedom House, Bertelsmann, Polity). Only these two feed any result, so the others were removed. `index.csv` still lists all of them with their URLs if one is needed later.

## Re-downloading

- [Political rights score](https://ourworldindata.org/explorers/democracy.csv?Dataset=Freedom+House&Metric=%C2%AD%C2%AD%C2%AD%C2%ADFreedom&Sub-metric=Political+rights+score)
- [Civil liberties score](https://ourworldindata.org/explorers/democracy.csv?Dataset=Freedom+House&Metric=%C2%AD%C2%AD%C2%AD%C2%ADFreedom&Sub-metric=Civil+liberties+score)

Third-party data keep their original licence terms (see OWID's [reuse notice](https://ourworldindata.org/democracy#reuse-this-work)).
