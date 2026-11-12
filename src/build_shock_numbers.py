"""Numbers around each reference episode for the website's Shocks view.

Same method as notebooks/02_shock_numbers.ipynb (trust windows, elections, party moves,
economy, V-Dem). Observations only: no effects or forecasts. Writes website/data/shocks.json.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from zipfile import ZipFile

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC, OUT = ROOT / "data/raw", ROOT / "data/processed", ROOT / "website/data"

ISO2 = {"BEL": "BE", "ESP": "ES", "FRA": "FR", "GRC": "EL", "PRT": "PT", "IRL": "IE", "AUT": "AT", "ITA": "IT"}
INSTITUTIONS = ["National parliament", "National government", "Political parties"]
SUCCESSOR = {"FR603": "FR604", "FR29": "FR606", "FR607": "FR33", "BE600": "BE30"}  # renamed lists, see notebook 02
COUNT_BY_PARTY = {"BEL"}


def clean(value):
    """JSON-safe number: None for missing, rounded otherwise."""
    if value is None or (isinstance(value, float) and math.isnan(value)) or pd.isna(value):
        return None
    return round(float(value), 3)


def load():
    episodes = pd.read_csv(RAW / "shocks/episodes.csv")
    episodes["start_date"] = pd.to_datetime(episodes.start)
    episodes["end_date"] = pd.to_datetime(episodes.end) + pd.offsets.MonthEnd(0)
    episodes["iso2"] = episodes.iso3.map(ISO2)

    eb = pd.read_csv(PROC / "eurobarometer_trust_trend.csv", parse_dates=["fieldwork_start"])
    eb["fieldwork_end"] = pd.to_datetime(eb.fieldwork.str.split(" ").str[1], format="%d/%b/%Y", errors="coerce")
    eb = eb.groupby(["country_code", "institution", "wave"], as_index=False).agg(
        trust=("trust_pct", "mean"), start=("fieldwork_start", "first"), end=("fieldwork_end", "first"))

    with ZipFile(RAW / "ppeg_2025v1/ppeg_parl_2025v1.zip") as archive:
        ppeg = pd.read_csv(archive.open("ppeg_parl_2025v1.csv"), low_memory=False)
    ppeg["edate"] = pd.to_datetime(ppeg.edate)
    ppeg["party"] = ppeg.pinitials.fillna(ppeg.pname_en)
    member = ppeg.alliance.eq("Electoral alliance member") & ppeg.alliance_id.notna()
    ppeg["list_id"] = ppeg.alliance_id.where(member, ppeg.party_id)
    ppeg["list_name"] = ppeg.alliance_initials.where(member, ppeg.party)

    family = pd.read_csv(ROOT / "data/reference/party_lists.csv").set_index("party_id").list_family.to_dict()
    macro = pd.read_csv(PROC / "eurostat_macro_country_year.csv")
    vdem = pd.read_csv(PROC / "vdem_country_year_core_v16.csv")
    return episodes, eb, ppeg, family, macro, vdem


def trust_window(ep, eb, institution):
    d = eb[eb.institution == institution]
    country = d[d.country_code == ep.iso2].sort_values("start")
    eu = d[d.country_code == "EU"].set_index("wave").trust
    before = country[country.end < ep.start_date].tail(2)
    after = country[country.start > ep.end_date].head(1)
    window = pd.concat([country[country.start.between(ep.start_date, ep.end_date)], after])
    if len(before) < 2 or window.empty:
        return None
    low = window.loc[window.trust.idxmin()]
    change = low.trust - before.trust.mean()
    eu_change = eu.get(low.wave) - eu.reindex(before.wave).mean()
    return {"institution": institution, "before": clean(before.trust.mean()),
            "beforeWaves": f"{before.start.iloc[0]:%b %Y} and {before.start.iloc[1]:%b %Y}",
            "lowest": clean(low.trust), "lowestWave": f"{low.start:%b %Y}",
            "after": clean(after.trust.iloc[0]) if len(after) else None,
            "afterWave": f"{after.start.iloc[0]:%b %Y}" if len(after) else None,
            "change": clean(change), "euChange": clean(eu_change), "beyondEu": clean(change - eu_change)}


def elections(ep, ppeg, family):
    d = ppeg[ppeg.iso3c == ep.iso3]
    dates = sorted(d.edate.unique())
    before = [x for x in dates if x < ep.start_date][-1:]
    during = [x for x in dates if ep.start_date <= x <= ep.end_date + pd.DateOffset(months=12)]
    if not before or not during:
        return None
    a, b = before[0], during[-1]
    by_list = ep.iso3 not in COUNT_BY_PARTY and bool(
        (d[d.edate.isin([a, b])].alliance.eq("Electoral alliance") & d[d.edate.isin([a, b])].v_share.ge(0.05)).any())
    key, label = ("list_id", "list_name") if by_list else ("party_id", "party")

    def summary(date):
        e = d[d.edate == date]
        turnout = e.total_vote.iloc[0] / e.electorate.iloc[0] * 100 if ep.use_turnout else None
        return {"date": f"{pd.Timestamp(date):%b %Y}", "turnout": clean(turnout),
                "parties": clean(1 / (e.groupby(key).v_share.sum() ** 2).sum())}

    # Biggest movers between the two elections (renamed lists and list families linked).
    names = d.sort_values("edate").groupby(key)[label].last()
    group = d[key].replace(SUCCESSOR)
    if ep.iso3 != "FRA":
        group = group.map(lambda i: family.get(i, i))
    share = lambda date: d[d.edate == date].groupby(group).v_share.sum() * 100
    diff = share(b).sub(share(a), fill_value=0)
    diff = diff.drop(index=[i for i in diff.index if str(i).endswith("999")], errors="ignore")
    moves = lambda s: [{"name": str(names.get(i, i)), "change": clean(v)} for i, v in s.items()]
    return {"before": summary(a), "after": summary(b), "countedBy": "list" if by_list else "party",
            "gains": moves(diff.nlargest(3)), "losses": moves(diff.nsmallest(3))}


def economy(ep, macro):
    g = macro[macro.geo == ep.iso2].set_index("year")
    y0, y1 = ep.start_date.year - 1, ep.end_date.year
    if g.empty or y0 not in g.index:
        return None
    w = g.loc[ep.start_date.year:y1]
    growth, unemp, debt = w.nama_10_gdp_real_growth, w.une_rt_a_unemployment, g.gov_10dd_edpt1_debt_gdp
    return {"yearBefore": y0, "endYear": y1,
            "worstGrowth": clean(growth.min()), "worstGrowthYear": int(growth.idxmin()) if growth.notna().any() else None,
            "unemploymentBefore": clean(g.une_rt_a_unemployment.get(y0)),
            "unemploymentPeak": clean(unemp.max()), "unemploymentPeakYear": int(unemp.idxmax()) if unemp.notna().any() else None,
            "debtBefore": clean(debt.get(y0)), "debtEnd": clean(debt.get(y1))}


def vdem_change(ep, vdem):
    v = vdem.set_index(["country_text_id", "year"])
    y0, y1 = ep.start_date.year - 1, min(ep.end_date.year + 1, int(vdem.year.max()))
    if (ep.iso3, y0) not in v.index or (ep.iso3, y1) not in v.index:
        return None
    a, b = v.loc[(ep.iso3, y0)], v.loc[(ep.iso3, y1)]
    width = b.v2x_polyarchy_codehigh - b.v2x_polyarchy_codelow
    change = b.v2x_polyarchy - a.v2x_polyarchy
    return {"yearBefore": y0, "before": clean(a.v2x_polyarchy), "yearAfter": y1, "after": clean(b.v2x_polyarchy),
            "change": clean(change), "clear": bool(abs(change) >= width)}


def main() -> None:
    episodes, eb, ppeg, family, macro, vdem = load()
    out = []
    for ep in episodes.itertuples():
        y0, y1 = ep.start[:4], ep.end[:4]
        out.append({
            "id": ep.episode_id, "shock": ep.shock, "country": ep.country,
            "label": f"{ep.country} {y0}" + ("" if y0 == y1 else f"–{y1[2:]}"),
            "start": ep.start, "end": ep.end, "startYear": int(y0), "endYear": int(y1), "note": ep.note,
            "trust": [t for inst in INSTITUTIONS if ep.use_trust and (t := trust_window(ep, eb, inst))],
            "elections": elections(ep, ppeg, family),
            "economy": economy(ep, macro),
            "vdem": vdem_change(ep, vdem),
        })
    (OUT / "shocks.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Prepared numbers for {len(out)} reference episodes.")


if __name__ == "__main__":
    main()
