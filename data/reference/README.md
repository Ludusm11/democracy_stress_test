# Reference tables written by the team

`radical_parties.csv` links parliamentary election results (PPEG `party_id`) to "radical" party families: parties that **The PopuList 4.0** classes as far right or far left, for France, Belgium, Spain, Greece, Portugal, Ireland, Austria and Italy.

| Column | Meaning |
| --- | --- |
| `iso3`, `party_id`, `initials` | The party or list as PPEG codes it |
| `family` | `far_right` or `far_left` |
| `first_year`, `last_year` | Years the PopuList class applies (1900/2100 = always) |
| `source` | `PopuList 4.0`, or `team` when we classified a PPEG row PopuList does not list (an alliance of listed parties, or PPEG's "other extreme left/right") |
| `note` | Rows starting `DISPUTED` or `PARTIAL` are judgment calls; analyses report results with and without them |

A party missing from this table is not thereby moderate: PopuList only lists parties it has classified. Used by `notebooks/03_radical_voting.ipynb`.

`party_lists.csv` groups lists that are the same political family under different names or alliance codes, so a renaming is not read as votes won or lost. Spain: IU, its 2011 and 2015 lists, Podemos, Unidos/Unidas Podemos and Podemos's regional alliances. France: LFI, PCF and the 2012 Left Front (the 2024 New Popular Front is handled in notebook 03, because only part of it is radical left). Used by notebooks 02 and 03 when they list the parties that gained or lost most.

`alliance_members.csv` lists the parties inside the 2024 French alliances that PPEG reports as one row (New Popular Front, Together, Union of the Far-Right), with their CHES 2024 `party_id` when CHES rates them. Members without a CHES rating stay in the table with a blank ID. `checked_by_person` is `no` until a team member has compared a row with an official list of the 2024 candidates. An alliance counts as linked to CHES when at least one member is rated; its position is not the position of any one party, because the members' own vote shares inside the alliance are unknown. Used by `src/party_coverage.py` and `src/audit_data.py`.

`s3_events.csv` lists the **integrity scandals at the top** used for scenario S3: 22 cases in 18 EU countries, 2005 to 2025, where a head of government, a head of state or a whole cabinet left office over a reported integrity allegation (corruption, conflict of interest, abuse of office, an ethics breach). Columns: `decisive_date` (the day the exit became public), `onset_date` (first major revelation, month precision where the day is not known), `level` (`government_fell`, `pm_resigned`, `head_of_state`), `gov_fell` (1 if the government ended in a way that changed who governs, or an early election followed), `trigger_type`, `s1_episode` (the S1 case it overlaps, if any), `evidence` (news links) and `note`. Built in November 2026 from news reports by one reviewer; **`checked_by_person` is `no` for every row**. Borderline rows (Ahern, Ponta, Fico, Rutte) are flagged in `note`. It is a list of scandals that ended in an exit, not of all scandals: survived scandals are not in it. Used by `notebooks/Shock_3_integrity_scandal.ipynb`.
