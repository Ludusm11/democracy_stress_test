# Democracy Stress Test: France first

We are building a way to explain how democracies might hold up under pressure. France is our first case. The project is at the **data prototype** stage: we have collected and checked sources, but we have not built a stress-test model or made a forecast.

## Start here

1. **Explore the website.** Run the command below, then open the address. The **Shocks** view shows the three documented France scenarios and their reference episodes. **Explore data** lets you chart the prepared datasets by country and measure.
2. Read [Where the project stands](outputs/data_audit/report.md) for a short account of what we know and what remains uncertain.
3. Use [the data guide](data_sets_legend.txt) to understand a source. The [short notebook](notebooks/01_data_audit_and_analysis.ipynb) is another gentle introduction.
4. Open [the shock numbers notebook](notebooks/02_shock_numbers.ipynb) for quotable figures around each reference episode: trust, turnout, party system, economy and V-Dem, next to the EU and France today. Observations, not effects.
5. Open [the radical voting notebook](notebooks/03_radical_voting.ipynb) for far-right and far-left vote shares: France since 1978, around each episode, and the eight countries today. The party classification is in [data/reference/radical_parties.csv](data/reference/radical_parties.csv).

```powershell
.\.venv\Scripts\python.exe -m http.server 8765 --directory website
```

Open **http://127.0.0.1:8765** in your browser. Press `Ctrl+C` in PowerShell to stop the website. It runs only on your computer; no data are uploaded.

The website's scenario catalogue follows the Scope Review: government collapse, systemic financial crisis, integrity scandal, electoral-integrity shock, and concentration of executive power. The Board 1 MVP update makes the first three the immediate focus; the last two are labelled as later scenarios. The Shocks view shows a compact France baseline, several relevant charts around each reference episode, and a selector for any other prepared dataset on the same timeline. A red band runs from the labelled start-year gridline to the labelled end-year gridline. A single-year or open-ended episode has a red line at its year; exact event days are not encoded. France's full historical trends are in Explore data. **These are observations, not stressed outcomes:** the effect ranges and severity levels still need a documented method.

The data view covers the eight prepared sources: V-Dem, Freedom House, International IDEA, Eurostat, Eurobarometer, EVS/WVS, CHES and PPEG. Charts have year gridlines; hover over a point for its exact date and value, or click to keep it selected. V-Dem charts show its uncertainty intervals. Source notes explain limits such as survey waves and party alliances. Other downloads remain in `data/raw/` for later work; they are not all charted on the site.

## Where things are

| Folder | What you will find |
| --- | --- |
| `data/raw/` | Original downloads. Leave these files as they are. |
| `data/reference/` | Tables written by the team, such as the radical-party classification. |
| `data/processed/` | Smaller tables prepared for analysis. |
| `outputs/data_audit/figures/` | Charts made from the working tables. |
| `outputs/data_audit/` | The short report and detailed check files. |
| `website/` | The small website and its prepared chart data. |
| `src/` | Code that rebuilds the tables, checks and charts. |

The project brief is `Scope_Review_Capstone_Democracy_v2(1).pptx` in this folder. The Board 1 update supplied by the team narrows the MVP to France and S1–S3.

## Rebuild the analysis

You need [Python 3.12](https://www.python.org/downloads/) and Git. All raw data is in the repository, so nothing else needs downloading.

**First time only.** Clone the repository, create the environment, install the packages and register the notebook kernel. In PowerShell (Windows):

```powershell
git clone https://github.com/Ludusm11/democracy_stress_test.git
cd democracy_stress_test
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m ipykernel install --sys-prefix --name capstone-democracy --display-name "Capstone (.venv Python 3.12)"
```

On macOS or Linux, use `python3.12 -m venv .venv` and replace `.\.venv\Scripts\python.exe` with `.venv/bin/python` in every command.

**Rebuild the processed tables, outputs and website data:**

```powershell
.\.venv\Scripts\python.exe src\run_analysis.py
```

**Open the notebooks:**

```powershell
.\.venv\Scripts\python.exe -m jupyter lab
```

In VS Code, open the folder and select the **Capstone (.venv Python 3.12)** kernel at the top right of a notebook.

**Get teammates' changes / share yours:** `git pull` before you start; `git add -A`, `git commit -m "what changed"` and `git push` when you are done.

## What remains open

- Radical vote shares are calculated descriptively in [notebook 03](notebooks/03_radical_voting.ipynb), using PopuList classes linked to PPEG results in [data/reference/](data/reference/). Two judgment calls are still the team's to make: whether to count Les Républicains (and the RPR before it) as far right, as PopuList 4.0 does, and how to split the 2024 New Popular Front, which PPEG reports as one alliance.
- Linking election votes to CHES party positions still needs a checked list of the parties inside each 2024 alliance.
- No shock transmission estimates or severity ranges are calculated yet. The site does not present a forecast.
- The ESS folder contains guidance, but no respondent data yet.
- The trust surveys ask different questions. Their results stay separate.

The detailed findings are in [the issue log](outputs/data_audit/quality_issues.csv). The original EVS/WVS and Manifesto files have sharing restrictions; check their terms before distributing them.
