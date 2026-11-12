# Joint EVS/WVS 2017–2022, version 5.0.0

Source: https://www.worldvaluessurvey.org/WVSEVSjoint2017.jsp  
WVSA DOI: https://doi.org/10.14281/18241.26  
Release date: 24 June 2024

The full CSV archive (`F00012158-EVS_WVS_Joint_Csv_v5_0.zip`, which the pipeline reads directly), codebook, EVS questionnaire, country list, variable correspondence, and release notes are stored here. The CSV inside it contains 156,658 respondents and 231 columns. France is in this joint release through the **European Values Study (EVS)** portion; WVS Wave 7 alone is not the right France source.

France filter: `cntry_AN == "FR"` (`cntry` is numeric ISO code 250). A local working extract with all columns is at `../../processed/evs_wvs_france_2018_v5.csv`: 1,870 France interviews, all recorded as year 2018. This is one cross-section, not an annual time series or a panel.

Useful first-prototype variables in the joint codebook:

- `E069_07`: confidence in parliament
- `E069_11`: confidence in government
- `E069_12`: confidence in political parties
- `E111_01`: satisfaction with the political system
- `E114`: evaluation of a strong leader political system
- `E116`: evaluation of army rule
- `E117`: evaluation of a democratic political system
- `E226`: free elections as a characteristic of democracy
- `E228`: army takeover as a characteristic of democracy
- `gwght`: within-country survey weight. For pooled cross-country population-weighted analysis, the codebook specifies `gwght * pwght`.

Negative codes indicate missing or non-substantive responses and must be excluded or handled according to the codebook before calculating percentages. Do not merge these respondent records to another survey at the individual level. Aggregate first when combining with country-level indicators.

Citation given by the source: EVS/WVS (2022). *European Values Study and World Values Survey: Joint EVS/WVS 2017–2022 Dataset*. JD Systems Institute & WVSA. Dataset Version 5.0.0. https://doi.org/10.14281/18241.26

WVS download conditions prohibit redistribution of the data files: https://www.worldvaluessurvey.org/AJDownloadLicense.jsp . Keep the raw and France-only microdata out of a public repository or release.
