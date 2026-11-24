"""Build a country x wave panel of political trust from Eurobarometer respondent files (GESIS).

Reads every ZA*.dta or ZA*.dta.zip under data/new/ (any subfolder). For each wave and country it
computes the weighted share who "tend to trust" the national government, the national parliament
and political parties, and the share satisfied with how democracy works in their country, with
standard errors and the interview dates.

Rules, the same in every wave:
- Items are found by their label, because variable names change between waves (v52, qa6_2, ...).
- Answers are classified by their value-label text: "tend to trust", "tend not to trust", "don't know".
  Don't know stays in the denominator, as in the published Eurobarometer tables. Inapplicable and
  no-answer codes are left out.
- Weights: the national "weight result from target". Germany (East + West samples) and the United
  Kingdom (Great Britain + Northern Ireland) are combined with their own whole-country weights.
  The Turkish Cypriot community sample (CY-TCC) is left out.
- Standard errors use the Kish effective sample size, so they allow for weighting but not for
  clustering: treat them as a lower bound.

The respondent files are not in the repository (GESIS terms bar redistribution). Download the ZA
numbers listed in WAVES below from https://search.gesis.org/research_data/ZA<number> into data/new/.

Output: data/processed/eb_panel.csv (one row per wave x country) and
outputs/data_audit/eb_panel_items.csv (which variable was used for each item in each wave).
"""

from pathlib import Path
from zipfile import ZipFile
from io import BytesIO
import argparse
import re
import sys
import warnings
from datetime import datetime

import numpy as np
import pandas as pd
from pandas.io.stata import StataMissingValue

warnings.filterwarnings("ignore", category=UserWarning)

ROOT = Path(__file__).resolve().parents[1]

# ZA number -> (Eurobarometer, fieldwork months, fieldwork year), from GESIS's trust-in-institutions
# trend list, plus the three Standard waves released after it (102.2, 103.3, 104.1).
# Left out on purpose: ZA3086 (EB 50.1, different question); ZA4973, ZA4975 and ZA5237 (EB 71.3, 72.1, 74.1:
# 10-point scale, not "tend to trust").
# Known quirks, flagged in the output column `note`:
SYSMISS_IS_DK = {5913}  # EB 81.2 labels code 3 as DK but stores don't know as system-missing
NOTES = {
    5913: "don't know left uncoded in the file; system-missing answers counted as don't know (matches published figures)",
    7649: "don't know and inapplicable share one code (left out); summer 2020 mixed-mode fieldwork",
}
WAVES = {
    2959: ("48.0", "10-11", 1997), 3171: ("51.0", "3-4", 1999), 3387: ("54.1", "11-12", 2000),
    3507: ("55.1", "4-5", 2001), 3627: ("56.2", "10-11", 2001), 3639: ("57.1", "3-5", 2002),
    3904: ("59.1", "3-4", 2003), 3938: ("60.1", "10-11", 2003), 4056: ("61", "2-3", 2004),
    4229: ("62.0", "10-11", 2004), 4411: ("63.4", "5-6", 2005), 4414: ("64.2", "10-11", 2005),
    4506: ("65.2", "3-5", 2006), 4526: ("66.1", "9-10", 2006), 4528: ("66.3", "11-12", 2006),
    4530: ("67.2", "4-5", 2007), 4565: ("68.1", "9-11", 2007), 4744: ("69.2", "3-5", 2008),
    4819: ("70.1", "10-11", 2008), 4971: ("71.1", "1-2", 2009), 4994: ("72.4", "10-11", 2009),
    5234: ("73.4", "5", 2010), 5449: ("74.2", "11-12", 2010),
    5481: ("75.3", "5", 2011), 5567: ("76.3", "11", 2011), 5612: ("77.3", "5", 2012),
    5685: ("78.1", "11", 2012), 5689: ("79.3", "5", 2013), 5876: ("80.1", "11", 2013),
    5913: ("81.2", "3", 2014), 5928: ("81.4", "5-6", 2014), 5932: ("82.3", "11", 2014),
    5998: ("83.3", "5", 2015), 6643: ("84.3", "11", 2015), 6694: ("85.2", "5", 2016),
    6788: ("86.2", "11", 2016), 6862: ("87.2", "4", 2017), 6863: ("87.3", "5", 2017),
    6928: ("88.3", "11", 2017), 6963: ("89.1", "3", 2018), 7489: ("90.3", "11", 2018),
    7562: ("91.2", "3", 2019), 7576: ("91.5", "6-7", 2019), 7601: ("92.3", "11-12", 2019),
    7649: ("93.1", "7-8", 2020), 7780: ("94.3", "2-3", 2021), 7783: ("95.3", "6-7", 2021),
    7848: ("96.3", "1-2", 2022), 7902: ("97.5", "6-7", 2022), 7953: ("98.2", "1-2", 2023),
    7997: ("99.4", "5-6", 2023), 8779: ("100.2", "10-11", 2023), 8843: ("101.3", "4-5", 2024),
    8905: ("102.2", "10-11", 2024), 9128: ("103.3", "3-4", 2025), 9130: ("104.1", "10-11", 2025),
}
# GESIS's trend list calls ZA4744 EB 69.1; its study page says 69.2, which is used here.
# GESIS lists EB 98.2 under 2022; its fieldwork was January-February 2023 (dates in the file confirm it).

ITEMS = {
    "trust_gov": r"TRUST IN INSTIT.*(NAT\w* GOVERN)",
    "trust_parl": r"TRUST IN INSTIT.*(NAT\w* PARLIAM)",
    "trust_parties": r"TRUST IN INSTIT.*(POLIT\w* PARTIES)",
    "swd": r"(DEMOCRACY SATISF\w*|SATISF\w* .*DEMOCRACY).*(COUNTRY|NATION|\(OUR COUNTRY\))",
}
EXCLUDE_ITEM = r"TCC|EUROPEAN|\bEU\b|REGION|LOCAL"

GROUPS = {"DE-W": "DE", "DE-E": "DE", "GB-GBN": "GB", "GB-NIR": "GB"}
DROP = {"CY-TCC", "CY-TCC ", "TCC"}


def missing_code(x):
    """Stata extended missing values (.a-.z) as the int32 codes used in value labels."""
    if isinstance(x, StataMissingValue):
        tag = x.string
        return 2147483621 + (0 if tag == "." else ord(tag[1]) - 96)
    return x


def classify(label, item):
    """Map a value label to 1 (positive), 0 (negative), 'dk' or None (excluded)."""
    t = label.lower()
    if re.search(r"inap", t):  # e.g. EB 93.1 codes "DK/NA or inapplicable" together: leave it out
        return None
    if re.search(r"\bdk\b|don.?t know|dont know", t):
        return "dk"
    if item == "swd":
        if re.search(r"not very|not at all", t):
            return 0
        if re.search(r"very satisf|fairly satisf", t):
            return 1
        return None
    if re.search(r"tend not to trust", t):
        return 0
    if re.search(r"tend to trust", t):
        return 1
    return None


def open_reader(path):
    if path.suffix == ".zip":
        with ZipFile(path) as z:
            name = next(n for n in z.namelist() if n.lower().endswith(".dta"))
            return pd.io.stata.StataReader(BytesIO(z.read(name)))
    return pd.io.stata.StataReader(path)


def find_vars(reader):
    lab = reader.variable_labels()
    found = {}
    for item, pattern in ITEMS.items():
        cands = [k for k, v in lab.items() if re.search(pattern, v, re.I) and not re.search(EXCLUDE_ITEM, v, re.I)]
        if cands:
            found[item] = cands[0]
    country = next((k for k, v in lab.items() if k.lower() == "isocntry"), None) or next(
        (k for k, v in lab.items() if re.search(r"NATION - ALL SAMPLES ISO 3166", v, re.I)), None)
    weights = {k: v for k, v in lab.items() if re.search(r"WEIGHT", v, re.I)}
    w_nat = next((k for k, v in weights.items() if re.search(r"RESULT FROM TARGET", v, re.I)
                  and not re.search(r"GERMANY|KINGDOM|NATION|EURO|EU\d|\bEU\b", v, re.I)), None)
    w_de = next((k for k, v in weights.items() if re.search(r"GERMANY", v, re.I) and not re.search(r"UK|KINGDOM", v, re.I)
                 and re.search(r"RESULT FROM TARGET", v, re.I)), None) or next(
        (k for k, v in weights.items() if re.search(r"GERMANY", v, re.I) and not re.search(r"UK|KINGDOM", v, re.I)), None)
    w_uk = next((k for k, v in weights.items() if re.search(r"KINGDOM", v, re.I) and not re.search(r"GERMANY", v, re.I)
                 and re.search(r"RESULT FROM TARGET", v, re.I)), None) or next(
        (k for k, v in weights.items() if re.search(r"KINGDOM", v, re.I) and not re.search(r"GERMANY", v, re.I)), None)
    date = next((k for k, v in lab.items() if re.search(r"DATE OF INTERVIEW", v, re.I)), None)
    return found, country, w_nat, w_de, w_uk, date, lab


def coded(series, labels, item, sysmiss_dk=False):
    """Return a float series: 1, 0, nan for dk (flagged separately) and a dk mask."""
    raw = series.map(missing_code)
    if sysmiss_dk:
        labels = {**labels, 2147483621: "DK"}
    cls = {}
    for code, text in labels.items():
        cls[code] = classify(str(text), item)
    mapped = raw.map(lambda v: cls.get(v, None) if pd.notna(v) else None)
    dk = mapped.eq("dk")
    val = mapped.where(~dk).map(lambda v: v if v in (0, 1) else np.nan).astype(float)
    return val, dk


def parse_dates(series, labels, months, year):
    first_month = int(months.split("-")[0])
    out = {}
    for code, text in labels.items():
        t = str(text)
        m = re.search(r"(\d{1,2})[-./](\d{1,2})[-./](\d{4})", t)
        if m:
            out[code] = datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            continue
        try:
            ts = pd.to_datetime(re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", t.replace(",", " ")), errors="coerce",
                                format="mixed", dayfirst=True)
        except (ValueError, TypeError):
            ts = pd.NaT
        if pd.isna(ts):
            from dateutil import parser
            try:
                ts = parser.parse(re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", t), fuzzy=True, default=datetime(year, 1, 1))
            except (ValueError, OverflowError):
                continue
        ts = pd.Timestamp(ts)
        if not re.search(r"\b(19|20)\d{2}\b", t):
            y = year + (1 if ts.month < first_month - 2 else 0)
            ts = ts.replace(year=y)
        out[code] = ts
    return pd.to_datetime(series.map(missing_code).map(out), errors="coerce")


def weighted(values, w):
    ok = values.notna() & w.notna() & (w > 0)
    v, ww = values[ok], w[ok]
    if len(v) == 0 or ww.sum() == 0:
        return np.nan, np.nan, 0, np.nan
    p = np.average(v, weights=ww)
    n_eff = ww.sum() ** 2 / (ww ** 2).sum()
    se = np.sqrt(p * (1 - p) / n_eff)
    return 100 * p, 100 * se, int(len(v)), n_eff


def process(path, za):
    eb, months, year = WAVES[za]
    reader = open_reader(path)
    found, cvar, w_nat, w_de, w_uk, dvar, lab = find_vars(reader)
    value_labels = reader.value_labels()
    lbl_of = dict(zip(reader._varlist, reader._lbllist))
    cols = [c for c in [cvar, w_nat, w_de, w_uk, dvar, *found.values()] if c]
    reader2 = open_reader(path)
    df = reader2.read(columns=list(dict.fromkeys(cols)), convert_categoricals=False, convert_missing=True)

    country = df[cvar]
    if not isinstance(country.dropna().iloc[0], str):
        names = value_labels.get(lbl_of.get(cvar), {})
        country = country.map(lambda x: names.get(missing_code(x)))
    country = country.astype(str).str.strip().str.upper()
    country = country[~country.isin(DROP)]
    df = df.loc[country.index]
    key = country.replace(GROUPS)

    def num(col):
        return pd.to_numeric(df[col].map(lambda x: np.nan if isinstance(x, StataMissingValue) else x), errors="coerce")

    w = num(w_nat) if w_nat else pd.Series(1.0, index=df.index)
    if w_de:
        w = w.where(~key.eq("DE"), num(w_de))
    if w_uk:
        w = w.where(~key.eq("GB"), num(w_uk))
    elif country.eq("GB-NIR").any():
        # No UK-wide weight: Northern Ireland is oversampled, so GB uses the Great Britain sample only.
        w = w.where(~country.eq("GB-NIR"), 0.0)

    dates = parse_dates(df[dvar], value_labels.get(lbl_of.get(dvar), {}), months, year) if dvar else None

    audit = [{"za": za, "eb": eb, "item": item, "variable": var, "label": lab[var]} for item, var in found.items()]
    audit += [{"za": za, "eb": eb, "item": name, "variable": var, "label": lab.get(var, "")}
              for name, var in [("country", cvar), ("weight", w_nat), ("weight_germany", w_de),
                                ("weight_uk", w_uk), ("interview_date", dvar)]]
    if not w_de and key.eq("DE").any():
        print(f"  ZA{za}: no Germany-wide weight; DE combines East and West with the national weight")

    coded_items = {}
    for item, var in found.items():
        coded_items[item] = coded(df[var], value_labels.get(lbl_of.get(var), {}), item, sysmiss_dk=za in SYSMISS_IS_DK)

    rows = []
    for c, idx in key.groupby(key).groups.items():
        r = {"za": za, "eb": eb, "country": c, "n": len(idx), "note": NOTES.get(za, "")}
        d = dates.loc[idx].dropna() if dates is not None else pd.Series(dtype="datetime64[ns]")
        if len(d):
            r["fieldwork_start"] = d.min().date()
            r["fieldwork_median"] = d.sort_values().iloc[len(d) // 2].date()
            r["fieldwork_end"] = d.max().date()
            r["date_source"] = "interviews"
        else:  # no interview dates in the file: GESIS fieldwork months, mid-month assumed
            parts = months.split("-")
            m0, m1 = int(parts[0]), int(parts[-1])
            start, end = pd.Timestamp(year, m0, 1), pd.Timestamp(year, m1, 1) + pd.offsets.MonthEnd(0)
            r["fieldwork_start"], r["fieldwork_end"] = start.date(), end.date()
            r["fieldwork_median"] = (start + (end - start) / 2).date()
            r["date_source"] = "GESIS fieldwork months"
        for item, (val, dk) in coded_items.items():
            v, k = val.loc[idx], dk.loc[idx]
            share = v.where(~k, 0.0)  # don't know counts in the denominator, as a non-trusting answer
            p, se, n, n_eff = weighted(share.where(v.notna() | k), w.loc[idx])
            r[f"{item}_pct"] = p
            r[f"{item}_se"] = se
            r[f"{item}_n"] = n
            r[f"{item}_dk_pct"] = weighted(k.astype(float).where(v.notna() | k), w.loc[idx])[0]
        rows.append(r)
    return rows, audit


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=str(ROOT / "data/new"))
    ap.add_argument("--out", default=str(ROOT / "data/processed/eb_panel.csv"))
    ap.add_argument("--audit", default=str(ROOT / "outputs/data_audit/eb_panel_items.csv"))
    ap.add_argument("--allow-partial", action="store_true", help="write the panel even if some waves are missing")
    args = ap.parse_args()

    files = {}
    for p in sorted(Path(args.data_dir).rglob("ZA*.dta*")):
        m = re.match(r"ZA(\d{4})_", p.name)
        if m and int(m.group(1)) in WAVES and (p.suffix == ".dta" or p.name.endswith(".dta.zip")):
            files.setdefault(int(m.group(1)), p)
    missing = sorted(set(WAVES) - set(files))
    if missing:
        print("Not found (download from https://search.gesis.org/research_data/ZA<number>):",
              ", ".join(f"ZA{z}" for z in missing))
    if not files:
        print("No Eurobarometer respondent files in data/new/: keeping the existing eb_panel.csv (optional step).")
        sys.exit(0)
    if missing and not args.allow_partial:
        print("Some waves are missing, so the existing eb_panel.csv is kept. Add the files, or rerun with --allow-partial.")
        sys.exit(0)

    rows, audit = [], []
    for za, path in sorted(files.items()):
        print(f"ZA{za} (EB {WAVES[za][0]}) ...", flush=True)
        r, a = process(path, za)
        rows += r
        audit += a
    panel = pd.DataFrame(rows)
    panel["wave_order"] = panel.za.map({z: i for i, z in enumerate(sorted(WAVES))})
    panel = panel.sort_values(["wave_order", "country"]).drop(columns="wave_order")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.audit).parent.mkdir(parents=True, exist_ok=True)
    panel.round(3).to_csv(args.out, index=False)
    pd.DataFrame(audit).to_csv(args.audit, index=False)
    print(f"Wrote {len(panel)} rows ({panel.za.nunique()} waves, {panel.country.nunique()} countries) to {args.out}")


if __name__ == "__main__":
    main()
