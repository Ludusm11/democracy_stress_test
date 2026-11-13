"""Rebuild the working tables, checks, charts and short report in one step."""

from pathlib import Path
import subprocess
import sys


root = Path(__file__).resolve().parents[1]

# Raw downloads the pipeline needs. Registration-only sources are marked.
REQUIRED = {
    "data/raw/V-Dem-CY-FullOthers-v16_csv.zip": "https://v-dem.net/data/the-v-dem-dataset/",
    "data/raw/idea_export_voter_turnout_database_region.xlsx": "https://www.idea.int/data-tools/data/voter-turnout-database",
    "data/raw/The PopuList 4.0.csv": "https://popu-list.org/",
    "data/raw/ches/1999-2024_CHES_dataset_meansV2.csv": "https://www.chesdata.eu/",
    "data/raw/ppeg_2025v1/ppeg_parl_2025v1.zip": "https://ppeg.wzb.eu/",
    "data/raw/ppeg_2025v1/ppeg_gov_2025v1.zip": "https://ppeg.wzb.eu/",
    "data/raw/parlgov_2024/view_party.tab": "https://www.parlgov.org/",
    "data/raw/ches/CHES_2024_final_v2.csv": "https://www.chesdata.eu/",
    "data/raw/eurobarometer_std105_2026/STD105_volume_D.zip": "https://europa.eu/eurobarometer/surveys/detail/3613",
    "data/raw/eurostat_macro_annual": "https://ec.europa.eu/eurostat/",
    "data/raw/eurostat_macro_annual/une_rt_a_h_unemployment_historical.json": "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/une_rt_a_h?age=Y15-74&sex=T&unit=PC_ACT&sinceTimePeriod=2000",
    "data/raw/owid_democracy/explorer/073_freedom-house__freedom__political-rights-score.csv": "https://ourworldindata.org/explorers/democracy.csv?Dataset=Freedom+House&Metric=%C2%AD%C2%AD%C2%AD%C2%ADFreedom&Sub-metric=Political+rights+score",
    "data/raw/owid_democracy/explorer/075_freedom-house__freedom__civil-liberties-score.csv": "https://ourworldindata.org/explorers/democracy.csv?Dataset=Freedom+House&Metric=%C2%AD%C2%AD%C2%AD%C2%ADFreedom&Sub-metric=Civil+liberties+score",
    "data/raw/evs_wvs_joint_2017_2022_v5/F00012158-EVS_WVS_Joint_Csv_v5_0.zip": "https://www.worldvaluessurvey.org/WVSEVSjoint2017.jsp (free registration)",
    "data/raw/manifesto_2026a/MPDataset_MPDS2026a.csv": "https://manifesto-project.wzb.eu/ (free registration)",
    "data/raw/cevipof_bcp_2026/Barometre_confiance_CEVIPOFVague17_fev2026_vd1.pdf": "https://www.sciencespo.fr/cevipof/",
}
missing = {path: url for path, url in REQUIRED.items() if not (root / path).exists()}
if missing:
    print("These raw files are missing. Download them, then run this again:")
    for path, url in missing.items():
        print(f"  {path}\n    from {url}")
    sys.exit(1)

for script in ("audit_data.py", "party_coverage.py", "full_data_workbench.py", "build_site_data.py", "build_shock_numbers.py"):
    subprocess.run([sys.executable, str(root / "src" / script)], cwd=root, check=True)

print("Done. Read outputs/data_audit/report.md to see the results.")
