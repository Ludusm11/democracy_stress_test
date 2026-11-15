# Eurostat and World Bank series for the S2 (financial crisis) plan

Downloaded 15 November 2026. Each Eurostat file is the original JSON-stat 2.0 API response (same format as `../eurostat_macro_annual/`); `sinceTimePeriod=2000` asks for observations from 2000 on, and availability varies by country. No country filter was applied. Open data, no login.

| Local file | Indicator | Exact request (base `https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/`) |
|---|---|---|
| `irt_lt_mcby_a_bond_yield.json` | Long-term government bond yield (Maastricht criterion), annual, % | `irt_lt_mcby_a?int_rt=MCBY&sinceTimePeriod=2000` |
| `gov_10dd_edpt1_net_lending_gdp.json` | General-government net lending (+) or borrowing (-), % of GDP (`B9`, sector `S13`) | `gov_10dd_edpt1?unit=PC_GDP&sector=S13&na_item=B9&sinceTimePeriod=2000` |
| `nama_10_gdp_real_levels.json` | GDP at market prices, chain-linked volumes (2010), million euro | `nama_10_gdp?unit=CLV10_MEUR&na_item=B1GQ&sinceTimePeriod=2000` |
| `nama_10_gdp_current_prices.json` | GDP at market prices, current prices, million euro | `nama_10_gdp?unit=CP_MEUR&na_item=B1GQ&sinceTimePeriod=2000` |
| `nama_10_pc_gdp_per_head.json` | GDP per head, chain-linked volumes (2010), euro | `nama_10_pc?unit=CLV10_EUR_HAB&na_item=B1GQ&sinceTimePeriod=2000` |
| `une_rt_a_youth_unemployment.json` | Youth unemployment (15-24), % of active population, from 2009 for most countries | `une_rt_a?age=Y15-24&sex=T&unit=PC_ACT&sinceTimePeriod=2000` |
| `une_rt_a_h_youth_unemployment_historical.json` | Same, historical series to 2020, for the years before 2009 | `une_rt_a_h?age=Y15-24&sex=T&unit=PC_ACT&sinceTimePeriod=2000` |
| `prc_hpi_a_house_prices.json` | House price index, all dwellings, 2015 = 100, annual average | `prc_hpi_a?purchase=TOTAL&unit=I15_A_AVG&sinceTimePeriod=2000` |
| `worldbank_bank_npl_ratio.json` | Bank non-performing loans to total gross loans, % (World Bank `FB.AST.NPER.ZS`), 2000-2024, all countries | `https://api.worldbank.org/v2/country/all/indicator/FB.AST.NPER.ZS?format=json&per_page=20000&date=2000:2024` |

Gaps seen on download: no long-term bond yield for Estonia; house prices missing some years for 8 of 27 EU countries; World Bank bank-loan data are patchy for some countries. `src/prepare_s2_sources.py` decodes everything into `data/processed/s2_country_year_inputs.csv`.
