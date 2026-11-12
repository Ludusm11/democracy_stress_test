# Eurostat annual macro snapshot

Downloaded 12 November 2026 from the [Eurostat statistics API](https://ec.europa.eu/eurostat/en/web/user-guides/data-browser/api-data-access/api-introduction). Each file is the original JSON-stat 2.0 API response. `sinceTimePeriod=2000` requests observations from 2000 onward; actual availability varies by country and indicator. No country filter was applied.

| Local file | Indicator | Exact request |
|---|---|---|
| `nama_10_gdp_real_growth.json` | Annual real GDP growth, chain-linked volume percentage change on previous period; GDP at market prices (`B1GQ`). Re-downloaded 12 November 2026: the first download used `B1G`, which is gross value added, not GDP | https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/nama_10_gdp?unit=CLV_PCH_PRE&na_item=B1GQ&sinceTimePeriod=2000 |
| `une_rt_a_unemployment.json` | Annual unemployment, age 15–74, both sexes, percentage of active population | https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/une_rt_a?age=Y15-74&sex=T&unit=PC_ACT&sinceTimePeriod=2000 |
| `une_rt_a_h_unemployment_historical.json` | Historical annual unemployment (1992–2020), same age, sex and unit; downloaded 12 November 2026 to fill years before 2009, when `une_rt_a` starts for most countries | https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/une_rt_a_h?age=Y15-74&sex=T&unit=PC_ACT&sinceTimePeriod=2000 |
| `prc_hicp_aind_inflation.json` | All-items HICP annual-average rate of change | https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/prc_hicp_aind?coicop=CP00&unit=RCH_A_AVG&sinceTimePeriod=2000 |
| `gov_10dd_edpt1_debt_gdp.json` | General-government consolidated gross debt, percentage of GDP | https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/gov_10dd_edpt1?unit=PC_GDP&sector=S13&na_item=GD&sinceTimePeriod=2000 |

The JSON `value` field uses flat numeric positions indexed by the ordered dimensions in `id` and `size`. Decode those dimensions before joining to country-year tables; missing positions are absent from `value`. Preserve Eurostat observation flags in `status` where supplied.
