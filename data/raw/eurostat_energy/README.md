# Eurostat energy-price series for the E (energy shock) plan

Downloaded 24 November 2026 from the [Eurostat statistics API](https://ec.europa.eu/eurostat/en/web/user-guides/data-browser/api-data-access/api-introduction). Each file is the original JSON-stat 2.0 API response (same format as `../eurostat_macro_annual/` and `../eurostat_s2/`). No country filter was applied, so each file holds all 45 geographies the API returns (EU members, euro-area and EU aggregates, candidates, EFTA, UK). Open data, no login.

Inputs named in the MVP data specification, scenario E: energy inflation (the `energy_yoy` slider), household exposure (energy weight in the HICP basket) and duration (derived, below).

| Local file | Indicator | Exact request (base `https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/`) |
|---|---|---|
| `prc_hicp_manr_energy.json` | HICP energy aggregate (`NRG`), monthly, annual rate of change, %. **The main E shock series.** | `prc_hicp_manr?coicop=NRG&unit=RCH_A&sinceTimePeriod=1997-01&format=JSON&lang=EN` |
| `prc_hicp_manr_electricity_gas_fuels.json` | Electricity, gas and other fuels (`CP045`), same measure | `prc_hicp_manr?coicop=CP045&unit=RCH_A&sinceTimePeriod=1997-01&format=JSON&lang=EN` |
| `prc_hicp_manr_electricity.json` | Electricity (`CP0451`), same measure | `prc_hicp_manr?coicop=CP0451&unit=RCH_A&sinceTimePeriod=1997-01&format=JSON&lang=EN` |
| `prc_hicp_manr_gas.json` | Gas (`CP0452`), same measure | `prc_hicp_manr?coicop=CP0452&unit=RCH_A&sinceTimePeriod=1997-01&format=JSON&lang=EN` |
| `prc_hicp_inw_energy_weights.json` | HICP item weight of energy (`NRG`), per mille of the all-items basket, annual | `prc_hicp_inw?coicop=NRG&sinceTimePeriod=1996&format=JSON&lang=EN` |
| `prc_hicp_minr_energy_ecoicop2.json` | Same measure (HICP energy aggregate `NRG`, monthly annual rate of change) under Eurostat's 2026 classification (ECOICOP version 2), dataset `prc_hicp_minr`, January 1997 to **October 2026**, updated by Eurostat on 18 November 2026. Downloaded 24 November 2026. Used from January 2026 on; before that the old series is used (the two agree: mean absolute difference 0.016 points for EU countries over 9,366 overlapping country-months). | `prc_hicp_minr?coicop18=NRG&unit=RCH_A&sinceTimePeriod=1996-01&format=JSON&lang=EN` (note the dimension is `coicop18`) |
| `nrg_bal_c_gas_in_gross_energy_2015_2020.json` | Gross available energy (`GAE`), total (`TOTAL`) and natural gas (`G3000`), terajoules, annual 2015–2020. Gas share of supply = `G3000 / TOTAL`; the notebook averages 2018–2020. Pre-shock exposure for the E notebook. Downloaded 24 November 2026. | `nrg_bal_c?nrg_bal=GAE&siec=TOTAL&siec=G3000&unit=TJ&sinceTimePeriod=2015&untilTimePeriod=2020&format=JSON&lang=EN` |
| `nrg_ti_gas_imports_russia_2015_2020.json` | Natural gas imports (`G3000`), terajoules gross calorific value, from the Russian Federation (`RU`) and in total (`TOTAL`), annual 2015–2020. Russian share = `RU / TOTAL`; 2018–2020 averaged. Eurostat records the **direct** country of origin, so countries that buy Russian gas through a neighbour (Austria, Ireland) read 0%. | `nrg_ti_gas?siec=G3000&unit=TJ_GCV&partner=TOTAL&partner=RU&sinceTimePeriod=2015&untilTimePeriod=2020&format=JSON&lang=EN` |
| `prc_hicp_inw_all_items.json` | HICP all-items weight (`CP00`, = 1000), to scale the above | `prc_hicp_inw?coicop=CP00&sinceTimePeriod=1996&format=JSON&lang=EN` |

Decoding: the value index is `geo_position × number_of_months + time_position` (positions from `dimension.geo.category.index` and `dimension.time.category.index`). Eurostat uses `EL` for Greece and `UK` for the United Kingdom; Eurobarometer and the other tables here use `GR` and `GB`, so recode as `eurostat_macro_country_year.csv` already does.

## Checked on download

- The old dataset `prc_hicp_manr` stops at December 2025 (Eurostat changed the HICP classification in 2026). The 2026 months come from `prc_hicp_minr`, which also carries the history back to 1997, so the two can be checked against each other. In October 2026, 19 of 27 EU countries are above 15.6% (Belgium 39%, Lithuania 33%, Italy 32%, France 24%).
- 25 of the 37 national series start in 1997; others start when the country joined the HICP.
- Spot check, France, October 2022: energy 20.0%, electricity 8.8%, gas 31.7%, electricity-gas-fuels 25.3%. France's maximum is June 2022 (33.8%).
- Weights: France's energy weight is 103.22 per mille in 2022.

## Cautions for the shock definition

- **The raw maximum is not 2022.** Over the whole file the largest value is Bulgaria, December 1997, **+544%** (the 1997 hyperinflation), then the Netherlands, September 2022, +113.8%. Since 2001 the maximum is the Netherlands, September 2022. The specification says the slider maximum is "reached in 2022"; that holds only if the panel starts after the Bulgarian episode, or is limited to countries in the EU and to months covered by a Eurobarometer wave. Decide the rule before fixing the threshold.
- **Threshold.** The pooled 90th percentile across EU members is about 16% year on year (about 16 for any start year from 1997 to 2005). The specification leaves open whether the top-10% rule is pooled or per country.
- **Duration** is not a download: count the months above the threshold in the energy series.
- **France.** Regulated prices were capped in 2022–23 (bouclier tarifaire), so French energy inflation is lower than in most countries; the series already reflects this.
