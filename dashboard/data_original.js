// Democracy Stress Test MVP - data file.
// PLACEHOLDER VALUES. Replace baseline values in `outcomes` and the rows in `effects` with real estimates.
// effects: one row per scenario x parameter x outcome x horizon. horizon 1-4 = Eurobarometer waves after the shock; 0 = next election.
// effect_per_unit = change in the outcome (points) for one unit of the parameter; ci_low / ci_high = 90% interval.
// RULE: effects used for France are estimated on the panel WITHOUT France. backtest: each episode predicted by a model estimated without it. france_check: France episodes, predicted without France vs what happened.
window.MVP_DATA = {
 "meta": {
  "version": "prototype-0.1",
  "placeholder": true,
  "country": "France",
  "note": "PLACEHOLDER VALUES: format only, not results. Mark replaces baseline and effects with the real estimates.",
  "survey_noise_pp": 4.4,
  "ci_level": "90%",
  "estimated_without": "France",
  "rule": "A case that is read or tested is never used to estimate: effects for France come from the panel without France."
 },
 "outcomes": [
  {
   "id": "trust_gov",
   "label": "Trust in national government",
   "unit": "%",
   "kind": "survey",
   "source": "Standard Eurobarometer",
   "date": "EB 105, spring 2026",
   "baseline": 25
  },
  {
   "id": "trust_parl",
   "label": "Trust in national parliament",
   "unit": "%",
   "kind": "survey",
   "source": "Standard Eurobarometer",
   "date": "EB 105, spring 2026",
   "baseline": 30
  },
  {
   "id": "trust_parties",
   "label": "Trust in political parties",
   "unit": "%",
   "kind": "survey",
   "source": "Standard Eurobarometer",
   "date": "EB 105, spring 2026",
   "baseline": 12
  },
  {
   "id": "satisf_dem",
   "label": "Satisfied with democracy",
   "unit": "%",
   "kind": "survey",
   "source": "Standard Eurobarometer",
   "date": "EB 105, spring 2026",
   "baseline": 45
  },
  {
   "id": "radical_vote",
   "label": "Radical vote share",
   "unit": "% of votes",
   "kind": "election",
   "source": "Official results (data.gouv.fr), PopuList 4.0",
   "date": "Legislative election 2024",
   "baseline": 40
  },
  {
   "id": "turnout",
   "label": "Turnout",
   "unit": "% of registered",
   "kind": "election",
   "source": "Official results (data.gouv.fr)",
   "date": "Legislative election 2024",
   "baseline": 60
  }
 ],
 "scenarios": [
  {
   "id": "S1",
   "name": "Government collapse",
   "short": "Cabinet falls early and the country is left without a full-powered government.",
   "status": "Under test",
   "evidence": "medium",
   "params": [
    {
     "id": "days_no_gov",
     "label": "Days without a full-powered government",
     "unit": "days",
     "min": 0,
     "max": 540,
     "step": 10,
     "default": 60,
     "type": "range",
     "note": "Panel maximum: Belgium 2010–11, 541 days"
    },
    {
     "id": "cabinet_falls_24m",
     "label": "Cabinet falls in the last 24 months",
     "unit": "",
     "min": 0,
     "max": 4,
     "step": 1,
     "default": 1,
     "type": "range"
    },
    {
     "id": "early_election",
     "label": "Ends with an early election",
     "unit": "",
     "min": 0,
     "max": 1,
     "step": 1,
     "default": 0,
     "type": "toggle"
    }
   ],
   "episodes": [
    "Belgium 2010–11",
    "Spain 2015–16"
   ],
   "threshold": "Conflict-driven cabinet ends as coded by CPDS (published coding)",
   "sources": [
    "CPDS Government Composition",
    "ParlGov",
    "data.gouv.fr, Assemblée nationale open data",
    "Economic Policy Uncertainty index (FRED)"
   ]
  },
  {
   "id": "E",
   "name": "Energy-price shock",
   "short": "Consumer energy prices rise sharply for several months.",
   "status": "Candidate to replace S1",
   "evidence": "strong",
   "params": [
    {
     "id": "energy_yoy",
     "label": "Energy price increase, year on year",
     "unit": "%",
     "min": 0,
     "max": 45,
     "step": 1,
     "default": 20,
     "type": "range",
     "note": "Placeholder maximum: Mark sets the panel maximum"
    },
    {
     "id": "duration_m",
     "label": "Duration of the shock",
     "unit": "months",
     "min": 1,
     "max": 24,
     "step": 1,
     "default": 6,
     "type": "range"
    }
   ],
   "episodes": [
    "EU energy crisis 2021–23",
    "Strait of Hormuz 2026"
   ],
   "threshold": "Energy inflation in the top 10% of 1997–2026 (team choice; also tested at 5% and 20%)",
   "sources": [
    "Eurostat HICP, energy (prc_hicp_manr)",
    "Eurostat HICP item weights",
    "Konc, Steckel et al., CESifo 2026 (literature)"
   ]
  },
  {
   "id": "S2",
   "name": "Financial crisis",
   "short": "A systemic banking crisis hits jobs and output.",
   "status": "In MVP",
   "evidence": "strong",
   "params": [
    {
     "id": "unemp_pp",
     "label": "Rise in unemployment",
     "unit": "pp",
     "min": 0,
     "max": 15,
     "step": 0.5,
     "default": 3,
     "type": "range"
    },
    {
     "id": "gdp_fall",
     "label": "Fall in GDP",
     "unit": "%",
     "min": 0,
     "max": 10,
     "step": 0.5,
     "default": 3,
     "type": "range"
    },
    {
     "id": "spread_bp",
     "label": "Rise in sovereign spread",
     "unit": "bp",
     "min": 0,
     "max": 1000,
     "step": 25,
     "default": 150,
     "type": "range"
    }
   ],
   "episodes": [
    "Euro area 2008–13 (IE, ES, GR, PT, IT)"
   ],
   "threshold": "Crisis dates from the ECB/ESRB and IMF databases (published)",
   "sources": [
    "ECB/ESRB European financial crises database",
    "IMF Systemic Banking Crises Database",
    "Eurostat unemployment and GDP",
    "Funke, Schularick & Trebesch; Algan et al. (literature)"
   ]
  }
 ],
 "effects": [
  {
   "scenario": "S1",
   "param": "days_no_gov",
   "outcome": "trust_gov",
   "horizon": 1,
   "effect_per_unit": -0.004,
   "ci_low": -0.0104,
   "ci_high": 0.0024,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "days_no_gov",
   "outcome": "trust_gov",
   "horizon": 2,
   "effect_per_unit": -0.0034,
   "ci_low": -0.00884,
   "ci_high": 0.00204,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "days_no_gov",
   "outcome": "trust_gov",
   "horizon": 3,
   "effect_per_unit": -0.0024,
   "ci_low": -0.00624,
   "ci_high": 0.00144,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "days_no_gov",
   "outcome": "trust_gov",
   "horizon": 4,
   "effect_per_unit": -0.0014,
   "ci_low": -0.00364,
   "ci_high": 0.00084,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "days_no_gov",
   "outcome": "trust_parl",
   "horizon": 1,
   "effect_per_unit": -0.0032,
   "ci_low": -0.00832,
   "ci_high": 0.00192,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "days_no_gov",
   "outcome": "trust_parl",
   "horizon": 2,
   "effect_per_unit": -0.00272,
   "ci_low": -0.00707,
   "ci_high": 0.00163,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "days_no_gov",
   "outcome": "trust_parl",
   "horizon": 3,
   "effect_per_unit": -0.00192,
   "ci_low": -0.00499,
   "ci_high": 0.00115,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "days_no_gov",
   "outcome": "trust_parl",
   "horizon": 4,
   "effect_per_unit": -0.00112,
   "ci_low": -0.00291,
   "ci_high": 0.00067,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "days_no_gov",
   "outcome": "trust_parties",
   "horizon": 1,
   "effect_per_unit": -0.002,
   "ci_low": -0.0052,
   "ci_high": 0.0012,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "days_no_gov",
   "outcome": "trust_parties",
   "horizon": 2,
   "effect_per_unit": -0.0017,
   "ci_low": -0.00442,
   "ci_high": 0.00102,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "days_no_gov",
   "outcome": "trust_parties",
   "horizon": 3,
   "effect_per_unit": -0.0012,
   "ci_low": -0.00312,
   "ci_high": 0.00072,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "days_no_gov",
   "outcome": "trust_parties",
   "horizon": 4,
   "effect_per_unit": -0.0007,
   "ci_low": -0.00182,
   "ci_high": 0.00042,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "days_no_gov",
   "outcome": "satisf_dem",
   "horizon": 1,
   "effect_per_unit": -0.0036,
   "ci_low": -0.00936,
   "ci_high": 0.00216,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "days_no_gov",
   "outcome": "satisf_dem",
   "horizon": 2,
   "effect_per_unit": -0.00306,
   "ci_low": -0.00796,
   "ci_high": 0.00184,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "days_no_gov",
   "outcome": "satisf_dem",
   "horizon": 3,
   "effect_per_unit": -0.00216,
   "ci_low": -0.00562,
   "ci_high": 0.0013,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "days_no_gov",
   "outcome": "satisf_dem",
   "horizon": 4,
   "effect_per_unit": -0.00126,
   "ci_low": -0.00328,
   "ci_high": 0.00076,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "days_no_gov",
   "outcome": "radical_vote",
   "horizon": 0,
   "effect_per_unit": 0.002,
   "ci_low": -0.0012,
   "ci_high": 0.0052,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "days_no_gov",
   "outcome": "turnout",
   "horizon": 0,
   "effect_per_unit": -0.0012,
   "ci_low": -0.00312,
   "ci_high": 0.00072,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "cabinet_falls_24m",
   "outcome": "trust_gov",
   "horizon": 1,
   "effect_per_unit": -0.8,
   "ci_low": -1.92,
   "ci_high": 0.32,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "cabinet_falls_24m",
   "outcome": "trust_gov",
   "horizon": 2,
   "effect_per_unit": -0.68,
   "ci_low": -1.632,
   "ci_high": 0.272,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "cabinet_falls_24m",
   "outcome": "trust_gov",
   "horizon": 3,
   "effect_per_unit": -0.48,
   "ci_low": -1.152,
   "ci_high": 0.192,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "cabinet_falls_24m",
   "outcome": "trust_gov",
   "horizon": 4,
   "effect_per_unit": -0.28,
   "ci_low": -0.672,
   "ci_high": 0.112,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "cabinet_falls_24m",
   "outcome": "trust_parl",
   "horizon": 1,
   "effect_per_unit": -0.64,
   "ci_low": -1.536,
   "ci_high": 0.256,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "cabinet_falls_24m",
   "outcome": "trust_parl",
   "horizon": 2,
   "effect_per_unit": -0.544,
   "ci_low": -1.3056,
   "ci_high": 0.2176,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "cabinet_falls_24m",
   "outcome": "trust_parl",
   "horizon": 3,
   "effect_per_unit": -0.384,
   "ci_low": -0.9216,
   "ci_high": 0.1536,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "cabinet_falls_24m",
   "outcome": "trust_parl",
   "horizon": 4,
   "effect_per_unit": -0.224,
   "ci_low": -0.5376,
   "ci_high": 0.0896,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "cabinet_falls_24m",
   "outcome": "trust_parties",
   "horizon": 1,
   "effect_per_unit": -0.4,
   "ci_low": -0.96,
   "ci_high": 0.16,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "cabinet_falls_24m",
   "outcome": "trust_parties",
   "horizon": 2,
   "effect_per_unit": -0.34,
   "ci_low": -0.816,
   "ci_high": 0.136,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "cabinet_falls_24m",
   "outcome": "trust_parties",
   "horizon": 3,
   "effect_per_unit": -0.24,
   "ci_low": -0.576,
   "ci_high": 0.096,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "cabinet_falls_24m",
   "outcome": "trust_parties",
   "horizon": 4,
   "effect_per_unit": -0.14,
   "ci_low": -0.336,
   "ci_high": 0.056,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "cabinet_falls_24m",
   "outcome": "satisf_dem",
   "horizon": 1,
   "effect_per_unit": -0.72,
   "ci_low": -1.728,
   "ci_high": 0.288,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "cabinet_falls_24m",
   "outcome": "satisf_dem",
   "horizon": 2,
   "effect_per_unit": -0.612,
   "ci_low": -1.4688,
   "ci_high": 0.2448,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "cabinet_falls_24m",
   "outcome": "satisf_dem",
   "horizon": 3,
   "effect_per_unit": -0.432,
   "ci_low": -1.0368,
   "ci_high": 0.1728,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "cabinet_falls_24m",
   "outcome": "satisf_dem",
   "horizon": 4,
   "effect_per_unit": -0.252,
   "ci_low": -0.6048,
   "ci_high": 0.1008,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "cabinet_falls_24m",
   "outcome": "radical_vote",
   "horizon": 0,
   "effect_per_unit": 0.4,
   "ci_low": -0.16,
   "ci_high": 0.96,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "cabinet_falls_24m",
   "outcome": "turnout",
   "horizon": 0,
   "effect_per_unit": -0.24,
   "ci_low": -0.576,
   "ci_high": 0.096,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "early_election",
   "outcome": "trust_gov",
   "horizon": 1,
   "effect_per_unit": 1.2,
   "ci_low": -0.6,
   "ci_high": 3.0,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "early_election",
   "outcome": "trust_gov",
   "horizon": 2,
   "effect_per_unit": 1.02,
   "ci_low": -0.51,
   "ci_high": 2.55,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "early_election",
   "outcome": "trust_gov",
   "horizon": 3,
   "effect_per_unit": 0.72,
   "ci_low": -0.36,
   "ci_high": 1.8,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "early_election",
   "outcome": "trust_gov",
   "horizon": 4,
   "effect_per_unit": 0.42,
   "ci_low": -0.21,
   "ci_high": 1.05,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "early_election",
   "outcome": "trust_parl",
   "horizon": 1,
   "effect_per_unit": 0.96,
   "ci_low": -0.48,
   "ci_high": 2.4,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "early_election",
   "outcome": "trust_parl",
   "horizon": 2,
   "effect_per_unit": 0.816,
   "ci_low": -0.408,
   "ci_high": 2.04,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "early_election",
   "outcome": "trust_parl",
   "horizon": 3,
   "effect_per_unit": 0.576,
   "ci_low": -0.288,
   "ci_high": 1.44,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "early_election",
   "outcome": "trust_parl",
   "horizon": 4,
   "effect_per_unit": 0.336,
   "ci_low": -0.168,
   "ci_high": 0.84,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "early_election",
   "outcome": "trust_parties",
   "horizon": 1,
   "effect_per_unit": 0.6,
   "ci_low": -0.3,
   "ci_high": 1.5,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "early_election",
   "outcome": "trust_parties",
   "horizon": 2,
   "effect_per_unit": 0.51,
   "ci_low": -0.255,
   "ci_high": 1.275,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "early_election",
   "outcome": "trust_parties",
   "horizon": 3,
   "effect_per_unit": 0.36,
   "ci_low": -0.18,
   "ci_high": 0.9,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "early_election",
   "outcome": "trust_parties",
   "horizon": 4,
   "effect_per_unit": 0.21,
   "ci_low": -0.105,
   "ci_high": 0.525,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "early_election",
   "outcome": "satisf_dem",
   "horizon": 1,
   "effect_per_unit": 1.08,
   "ci_low": -0.54,
   "ci_high": 2.7,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "early_election",
   "outcome": "satisf_dem",
   "horizon": 2,
   "effect_per_unit": 0.918,
   "ci_low": -0.459,
   "ci_high": 2.295,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "early_election",
   "outcome": "satisf_dem",
   "horizon": 3,
   "effect_per_unit": 0.648,
   "ci_low": -0.324,
   "ci_high": 1.62,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "early_election",
   "outcome": "satisf_dem",
   "horizon": 4,
   "effect_per_unit": 0.378,
   "ci_low": -0.189,
   "ci_high": 0.945,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "early_election",
   "outcome": "radical_vote",
   "horizon": 0,
   "effect_per_unit": -0.6,
   "ci_low": -1.5,
   "ci_high": 0.3,
   "n_events": 140
  },
  {
   "scenario": "S1",
   "param": "early_election",
   "outcome": "turnout",
   "horizon": 0,
   "effect_per_unit": 0.36,
   "ci_low": -0.18,
   "ci_high": 0.9,
   "n_events": 140
  },
  {
   "scenario": "E",
   "param": "energy_yoy",
   "outcome": "trust_gov",
   "horizon": 1,
   "effect_per_unit": -0.12,
   "ci_low": -0.174,
   "ci_high": -0.066,
   "n_events": 310
  },
  {
   "scenario": "E",
   "param": "energy_yoy",
   "outcome": "trust_gov",
   "horizon": 2,
   "effect_per_unit": -0.102,
   "ci_low": -0.1479,
   "ci_high": -0.0561,
   "n_events": 310
  },
  {
   "scenario": "E",
   "param": "energy_yoy",
   "outcome": "trust_gov",
   "horizon": 3,
   "effect_per_unit": -0.072,
   "ci_low": -0.1044,
   "ci_high": -0.0396,
   "n_events": 310
  },
  {
   "scenario": "E",
   "param": "energy_yoy",
   "outcome": "trust_gov",
   "horizon": 4,
   "effect_per_unit": -0.042,
   "ci_low": -0.0609,
   "ci_high": -0.0231,
   "n_events": 310
  },
  {
   "scenario": "E",
   "param": "energy_yoy",
   "outcome": "trust_parl",
   "horizon": 1,
   "effect_per_unit": -0.096,
   "ci_low": -0.1392,
   "ci_high": -0.0528,
   "n_events": 310
  },
  {
   "scenario": "E",
   "param": "energy_yoy",
   "outcome": "trust_parl",
   "horizon": 2,
   "effect_per_unit": -0.0816,
   "ci_low": -0.11832,
   "ci_high": -0.04488,
   "n_events": 310
  },
  {
   "scenario": "E",
   "param": "energy_yoy",
   "outcome": "trust_parl",
   "horizon": 3,
   "effect_per_unit": -0.0576,
   "ci_low": -0.08352,
   "ci_high": -0.03168,
   "n_events": 310
  },
  {
   "scenario": "E",
   "param": "energy_yoy",
   "outcome": "trust_parl",
   "horizon": 4,
   "effect_per_unit": -0.0336,
   "ci_low": -0.04872,
   "ci_high": -0.01848,
   "n_events": 310
  },
  {
   "scenario": "E",
   "param": "energy_yoy",
   "outcome": "trust_parties",
   "horizon": 1,
   "effect_per_unit": -0.06,
   "ci_low": -0.087,
   "ci_high": -0.033,
   "n_events": 310
  },
  {
   "scenario": "E",
   "param": "energy_yoy",
   "outcome": "trust_parties",
   "horizon": 2,
   "effect_per_unit": -0.051,
   "ci_low": -0.07395,
   "ci_high": -0.02805,
   "n_events": 310
  },
  {
   "scenario": "E",
   "param": "energy_yoy",
   "outcome": "trust_parties",
   "horizon": 3,
   "effect_per_unit": -0.036,
   "ci_low": -0.0522,
   "ci_high": -0.0198,
   "n_events": 310
  },
  {
   "scenario": "E",
   "param": "energy_yoy",
   "outcome": "trust_parties",
   "horizon": 4,
   "effect_per_unit": -0.021,
   "ci_low": -0.03045,
   "ci_high": -0.01155,
   "n_events": 310
  },
  {
   "scenario": "E",
   "param": "energy_yoy",
   "outcome": "satisf_dem",
   "horizon": 1,
   "effect_per_unit": -0.108,
   "ci_low": -0.1566,
   "ci_high": -0.0594,
   "n_events": 310
  },
  {
   "scenario": "E",
   "param": "energy_yoy",
   "outcome": "satisf_dem",
   "horizon": 2,
   "effect_per_unit": -0.0918,
   "ci_low": -0.13311,
   "ci_high": -0.05049,
   "n_events": 310
  },
  {
   "scenario": "E",
   "param": "energy_yoy",
   "outcome": "satisf_dem",
   "horizon": 3,
   "effect_per_unit": -0.0648,
   "ci_low": -0.09396,
   "ci_high": -0.03564,
   "n_events": 310
  },
  {
   "scenario": "E",
   "param": "energy_yoy",
   "outcome": "satisf_dem",
   "horizon": 4,
   "effect_per_unit": -0.0378,
   "ci_low": -0.05481,
   "ci_high": -0.02079,
   "n_events": 310
  },
  {
   "scenario": "E",
   "param": "energy_yoy",
   "outcome": "radical_vote",
   "horizon": 0,
   "effect_per_unit": 0.06,
   "ci_low": 0.033,
   "ci_high": 0.087,
   "n_events": 310
  },
  {
   "scenario": "E",
   "param": "energy_yoy",
   "outcome": "turnout",
   "horizon": 0,
   "effect_per_unit": -0.036,
   "ci_low": -0.0522,
   "ci_high": -0.0198,
   "n_events": 310
  },
  {
   "scenario": "E",
   "param": "duration_m",
   "outcome": "trust_gov",
   "horizon": 1,
   "effect_per_unit": -0.15,
   "ci_low": -0.24,
   "ci_high": -0.06,
   "n_events": 310
  },
  {
   "scenario": "E",
   "param": "duration_m",
   "outcome": "trust_gov",
   "horizon": 2,
   "effect_per_unit": -0.1275,
   "ci_low": -0.204,
   "ci_high": -0.051,
   "n_events": 310
  },
  {
   "scenario": "E",
   "param": "duration_m",
   "outcome": "trust_gov",
   "horizon": 3,
   "effect_per_unit": -0.09,
   "ci_low": -0.144,
   "ci_high": -0.036,
   "n_events": 310
  },
  {
   "scenario": "E",
   "param": "duration_m",
   "outcome": "trust_gov",
   "horizon": 4,
   "effect_per_unit": -0.0525,
   "ci_low": -0.084,
   "ci_high": -0.021,
   "n_events": 310
  },
  {
   "scenario": "E",
   "param": "duration_m",
   "outcome": "trust_parl",
   "horizon": 1,
   "effect_per_unit": -0.12,
   "ci_low": -0.192,
   "ci_high": -0.048,
   "n_events": 310
  },
  {
   "scenario": "E",
   "param": "duration_m",
   "outcome": "trust_parl",
   "horizon": 2,
   "effect_per_unit": -0.102,
   "ci_low": -0.1632,
   "ci_high": -0.0408,
   "n_events": 310
  },
  {
   "scenario": "E",
   "param": "duration_m",
   "outcome": "trust_parl",
   "horizon": 3,
   "effect_per_unit": -0.072,
   "ci_low": -0.1152,
   "ci_high": -0.0288,
   "n_events": 310
  },
  {
   "scenario": "E",
   "param": "duration_m",
   "outcome": "trust_parl",
   "horizon": 4,
   "effect_per_unit": -0.042,
   "ci_low": -0.0672,
   "ci_high": -0.0168,
   "n_events": 310
  },
  {
   "scenario": "E",
   "param": "duration_m",
   "outcome": "trust_parties",
   "horizon": 1,
   "effect_per_unit": -0.075,
   "ci_low": -0.12,
   "ci_high": -0.03,
   "n_events": 310
  },
  {
   "scenario": "E",
   "param": "duration_m",
   "outcome": "trust_parties",
   "horizon": 2,
   "effect_per_unit": -0.06375,
   "ci_low": -0.102,
   "ci_high": -0.0255,
   "n_events": 310
  },
  {
   "scenario": "E",
   "param": "duration_m",
   "outcome": "trust_parties",
   "horizon": 3,
   "effect_per_unit": -0.045,
   "ci_low": -0.072,
   "ci_high": -0.018,
   "n_events": 310
  },
  {
   "scenario": "E",
   "param": "duration_m",
   "outcome": "trust_parties",
   "horizon": 4,
   "effect_per_unit": -0.02625,
   "ci_low": -0.042,
   "ci_high": -0.0105,
   "n_events": 310
  },
  {
   "scenario": "E",
   "param": "duration_m",
   "outcome": "satisf_dem",
   "horizon": 1,
   "effect_per_unit": -0.135,
   "ci_low": -0.216,
   "ci_high": -0.054,
   "n_events": 310
  },
  {
   "scenario": "E",
   "param": "duration_m",
   "outcome": "satisf_dem",
   "horizon": 2,
   "effect_per_unit": -0.11475,
   "ci_low": -0.1836,
   "ci_high": -0.0459,
   "n_events": 310
  },
  {
   "scenario": "E",
   "param": "duration_m",
   "outcome": "satisf_dem",
   "horizon": 3,
   "effect_per_unit": -0.081,
   "ci_low": -0.1296,
   "ci_high": -0.0324,
   "n_events": 310
  },
  {
   "scenario": "E",
   "param": "duration_m",
   "outcome": "satisf_dem",
   "horizon": 4,
   "effect_per_unit": -0.04725,
   "ci_low": -0.0756,
   "ci_high": -0.0189,
   "n_events": 310
  },
  {
   "scenario": "E",
   "param": "duration_m",
   "outcome": "radical_vote",
   "horizon": 0,
   "effect_per_unit": 0.075,
   "ci_low": 0.03,
   "ci_high": 0.12,
   "n_events": 310
  },
  {
   "scenario": "E",
   "param": "duration_m",
   "outcome": "turnout",
   "horizon": 0,
   "effect_per_unit": -0.045,
   "ci_low": -0.072,
   "ci_high": -0.018,
   "n_events": 310
  },
  {
   "scenario": "S2",
   "param": "unemp_pp",
   "outcome": "trust_gov",
   "horizon": 1,
   "effect_per_unit": -0.9,
   "ci_low": -1.26,
   "ci_high": -0.54,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "unemp_pp",
   "outcome": "trust_gov",
   "horizon": 2,
   "effect_per_unit": -0.765,
   "ci_low": -1.071,
   "ci_high": -0.459,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "unemp_pp",
   "outcome": "trust_gov",
   "horizon": 3,
   "effect_per_unit": -0.54,
   "ci_low": -0.756,
   "ci_high": -0.324,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "unemp_pp",
   "outcome": "trust_gov",
   "horizon": 4,
   "effect_per_unit": -0.315,
   "ci_low": -0.441,
   "ci_high": -0.189,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "unemp_pp",
   "outcome": "trust_parl",
   "horizon": 1,
   "effect_per_unit": -0.72,
   "ci_low": -1.008,
   "ci_high": -0.432,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "unemp_pp",
   "outcome": "trust_parl",
   "horizon": 2,
   "effect_per_unit": -0.612,
   "ci_low": -0.8568,
   "ci_high": -0.3672,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "unemp_pp",
   "outcome": "trust_parl",
   "horizon": 3,
   "effect_per_unit": -0.432,
   "ci_low": -0.6048,
   "ci_high": -0.2592,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "unemp_pp",
   "outcome": "trust_parl",
   "horizon": 4,
   "effect_per_unit": -0.252,
   "ci_low": -0.3528,
   "ci_high": -0.1512,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "unemp_pp",
   "outcome": "trust_parties",
   "horizon": 1,
   "effect_per_unit": -0.45,
   "ci_low": -0.63,
   "ci_high": -0.27,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "unemp_pp",
   "outcome": "trust_parties",
   "horizon": 2,
   "effect_per_unit": -0.3825,
   "ci_low": -0.5355,
   "ci_high": -0.2295,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "unemp_pp",
   "outcome": "trust_parties",
   "horizon": 3,
   "effect_per_unit": -0.27,
   "ci_low": -0.378,
   "ci_high": -0.162,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "unemp_pp",
   "outcome": "trust_parties",
   "horizon": 4,
   "effect_per_unit": -0.1575,
   "ci_low": -0.2205,
   "ci_high": -0.0945,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "unemp_pp",
   "outcome": "satisf_dem",
   "horizon": 1,
   "effect_per_unit": -0.81,
   "ci_low": -1.134,
   "ci_high": -0.486,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "unemp_pp",
   "outcome": "satisf_dem",
   "horizon": 2,
   "effect_per_unit": -0.6885,
   "ci_low": -0.9639,
   "ci_high": -0.4131,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "unemp_pp",
   "outcome": "satisf_dem",
   "horizon": 3,
   "effect_per_unit": -0.486,
   "ci_low": -0.6804,
   "ci_high": -0.2916,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "unemp_pp",
   "outcome": "satisf_dem",
   "horizon": 4,
   "effect_per_unit": -0.2835,
   "ci_low": -0.3969,
   "ci_high": -0.1701,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "unemp_pp",
   "outcome": "radical_vote",
   "horizon": 0,
   "effect_per_unit": 0.45,
   "ci_low": 0.27,
   "ci_high": 0.63,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "unemp_pp",
   "outcome": "turnout",
   "horizon": 0,
   "effect_per_unit": -0.27,
   "ci_low": -0.378,
   "ci_high": -0.162,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "gdp_fall",
   "outcome": "trust_gov",
   "horizon": 1,
   "effect_per_unit": -0.6,
   "ci_low": -0.9,
   "ci_high": -0.3,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "gdp_fall",
   "outcome": "trust_gov",
   "horizon": 2,
   "effect_per_unit": -0.51,
   "ci_low": -0.765,
   "ci_high": -0.255,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "gdp_fall",
   "outcome": "trust_gov",
   "horizon": 3,
   "effect_per_unit": -0.36,
   "ci_low": -0.54,
   "ci_high": -0.18,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "gdp_fall",
   "outcome": "trust_gov",
   "horizon": 4,
   "effect_per_unit": -0.21,
   "ci_low": -0.315,
   "ci_high": -0.105,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "gdp_fall",
   "outcome": "trust_parl",
   "horizon": 1,
   "effect_per_unit": -0.48,
   "ci_low": -0.72,
   "ci_high": -0.24,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "gdp_fall",
   "outcome": "trust_parl",
   "horizon": 2,
   "effect_per_unit": -0.408,
   "ci_low": -0.612,
   "ci_high": -0.204,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "gdp_fall",
   "outcome": "trust_parl",
   "horizon": 3,
   "effect_per_unit": -0.288,
   "ci_low": -0.432,
   "ci_high": -0.144,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "gdp_fall",
   "outcome": "trust_parl",
   "horizon": 4,
   "effect_per_unit": -0.168,
   "ci_low": -0.252,
   "ci_high": -0.084,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "gdp_fall",
   "outcome": "trust_parties",
   "horizon": 1,
   "effect_per_unit": -0.3,
   "ci_low": -0.45,
   "ci_high": -0.15,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "gdp_fall",
   "outcome": "trust_parties",
   "horizon": 2,
   "effect_per_unit": -0.255,
   "ci_low": -0.3825,
   "ci_high": -0.1275,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "gdp_fall",
   "outcome": "trust_parties",
   "horizon": 3,
   "effect_per_unit": -0.18,
   "ci_low": -0.27,
   "ci_high": -0.09,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "gdp_fall",
   "outcome": "trust_parties",
   "horizon": 4,
   "effect_per_unit": -0.105,
   "ci_low": -0.1575,
   "ci_high": -0.0525,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "gdp_fall",
   "outcome": "satisf_dem",
   "horizon": 1,
   "effect_per_unit": -0.54,
   "ci_low": -0.81,
   "ci_high": -0.27,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "gdp_fall",
   "outcome": "satisf_dem",
   "horizon": 2,
   "effect_per_unit": -0.459,
   "ci_low": -0.6885,
   "ci_high": -0.2295,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "gdp_fall",
   "outcome": "satisf_dem",
   "horizon": 3,
   "effect_per_unit": -0.324,
   "ci_low": -0.486,
   "ci_high": -0.162,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "gdp_fall",
   "outcome": "satisf_dem",
   "horizon": 4,
   "effect_per_unit": -0.189,
   "ci_low": -0.2835,
   "ci_high": -0.0945,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "gdp_fall",
   "outcome": "radical_vote",
   "horizon": 0,
   "effect_per_unit": 0.3,
   "ci_low": 0.15,
   "ci_high": 0.45,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "gdp_fall",
   "outcome": "turnout",
   "horizon": 0,
   "effect_per_unit": -0.18,
   "ci_low": -0.27,
   "ci_high": -0.09,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "spread_bp",
   "outcome": "trust_gov",
   "horizon": 1,
   "effect_per_unit": -0.004,
   "ci_low": -0.0068,
   "ci_high": -0.0012,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "spread_bp",
   "outcome": "trust_gov",
   "horizon": 2,
   "effect_per_unit": -0.0034,
   "ci_low": -0.00578,
   "ci_high": -0.00102,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "spread_bp",
   "outcome": "trust_gov",
   "horizon": 3,
   "effect_per_unit": -0.0024,
   "ci_low": -0.00408,
   "ci_high": -0.00072,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "spread_bp",
   "outcome": "trust_gov",
   "horizon": 4,
   "effect_per_unit": -0.0014,
   "ci_low": -0.00238,
   "ci_high": -0.00042,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "spread_bp",
   "outcome": "trust_parl",
   "horizon": 1,
   "effect_per_unit": -0.0032,
   "ci_low": -0.00544,
   "ci_high": -0.00096,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "spread_bp",
   "outcome": "trust_parl",
   "horizon": 2,
   "effect_per_unit": -0.00272,
   "ci_low": -0.00462,
   "ci_high": -0.00082,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "spread_bp",
   "outcome": "trust_parl",
   "horizon": 3,
   "effect_per_unit": -0.00192,
   "ci_low": -0.00326,
   "ci_high": -0.00058,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "spread_bp",
   "outcome": "trust_parl",
   "horizon": 4,
   "effect_per_unit": -0.00112,
   "ci_low": -0.0019,
   "ci_high": -0.00034,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "spread_bp",
   "outcome": "trust_parties",
   "horizon": 1,
   "effect_per_unit": -0.002,
   "ci_low": -0.0034,
   "ci_high": -0.0006,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "spread_bp",
   "outcome": "trust_parties",
   "horizon": 2,
   "effect_per_unit": -0.0017,
   "ci_low": -0.00289,
   "ci_high": -0.00051,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "spread_bp",
   "outcome": "trust_parties",
   "horizon": 3,
   "effect_per_unit": -0.0012,
   "ci_low": -0.00204,
   "ci_high": -0.00036,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "spread_bp",
   "outcome": "trust_parties",
   "horizon": 4,
   "effect_per_unit": -0.0007,
   "ci_low": -0.00119,
   "ci_high": -0.00021,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "spread_bp",
   "outcome": "satisf_dem",
   "horizon": 1,
   "effect_per_unit": -0.0036,
   "ci_low": -0.00612,
   "ci_high": -0.00108,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "spread_bp",
   "outcome": "satisf_dem",
   "horizon": 2,
   "effect_per_unit": -0.00306,
   "ci_low": -0.0052,
   "ci_high": -0.00092,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "spread_bp",
   "outcome": "satisf_dem",
   "horizon": 3,
   "effect_per_unit": -0.00216,
   "ci_low": -0.00367,
   "ci_high": -0.00065,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "spread_bp",
   "outcome": "satisf_dem",
   "horizon": 4,
   "effect_per_unit": -0.00126,
   "ci_low": -0.00214,
   "ci_high": -0.00038,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "spread_bp",
   "outcome": "radical_vote",
   "horizon": 0,
   "effect_per_unit": 0.002,
   "ci_low": 0.0006,
   "ci_high": 0.0034,
   "n_events": 60
  },
  {
   "scenario": "S2",
   "param": "spread_bp",
   "outcome": "turnout",
   "horizon": 0,
   "effect_per_unit": -0.0012,
   "ci_low": -0.00204,
   "ci_high": -0.00036,
   "n_events": 60
  }
 ],
 "backtest": [
  {
   "scenario": "S1",
   "episode": "Belgium 2010–11",
   "outcome": "trust_gov",
   "horizon": 2,
   "pred_low": -4.1,
   "pred_high": 0.6,
   "actual": -2.0
  },
  {
   "scenario": "S1",
   "episode": "Spain 2015–16",
   "outcome": "trust_gov",
   "horizon": 2,
   "pred_low": -3.8,
   "pred_high": 0.9,
   "actual": 0.5
  },
  {
   "scenario": "S1",
   "episode": "Italy 2022",
   "outcome": "trust_gov",
   "horizon": 2,
   "pred_low": -3.5,
   "pred_high": 1.0,
   "actual": -4.6
  },
  {
   "scenario": "E",
   "episode": "Germany 2022",
   "outcome": "trust_gov",
   "horizon": 2,
   "pred_low": -6.0,
   "pred_high": -1.2,
   "actual": -3.1
  },
  {
   "scenario": "E",
   "episode": "Italy 2022",
   "outcome": "trust_gov",
   "horizon": 2,
   "pred_low": -5.5,
   "pred_high": -0.8,
   "actual": -2.4
  },
  {
   "scenario": "E",
   "episode": "Czechia 2022",
   "outcome": "trust_gov",
   "horizon": 2,
   "pred_low": -6.2,
   "pred_high": -1.0,
   "actual": -0.4
  },
  {
   "scenario": "S2",
   "episode": "Spain 2008–13",
   "outcome": "trust_gov",
   "horizon": 2,
   "pred_low": -9.0,
   "pred_high": -2.5,
   "actual": -6.8
  },
  {
   "scenario": "S2",
   "episode": "Ireland 2008–13",
   "outcome": "trust_gov",
   "horizon": 2,
   "pred_low": -8.5,
   "pred_high": -2.0,
   "actual": -5.1
  },
  {
   "scenario": "S2",
   "episode": "Greece 2010–15",
   "outcome": "trust_gov",
   "horizon": 2,
   "pred_low": -9.5,
   "pred_high": -3.0,
   "actual": -11.0
  }
 ],
 "france_check": [
  {
   "scenario": "S1",
   "episode": "France 2024–25 (government falls)",
   "outcome": "trust_gov",
   "horizon": 2,
   "pred_low": -4.0,
   "pred_high": 0.8,
   "actual": -2.5
  },
  {
   "scenario": "E",
   "episode": "France 2022 (energy crisis, bouclier tarifaire)",
   "outcome": "trust_gov",
   "horizon": 2,
   "pred_low": -3.0,
   "pred_high": 0.5,
   "actual": -1.0
  }
 ]
};
