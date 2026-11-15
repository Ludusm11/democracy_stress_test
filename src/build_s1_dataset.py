"""S1 pilot dataset: one row per reviewed government-collapse episode, inputs and trust outcomes.

Reads data/reference/s1_verified_events.csv (dated, reviewed events) and keeps the episodes marked
`yes`, `held_out` (France) or `review` for scenario S1. Writes data/processed/s1_episode_dataset.csv.

Baseline inputs are the ending cabinet's recorded type and seat share, the crisis
mechanism, trust before the event, the economy in the year before. The time until a non-caretaker
cabinet is installed is a post-event descriptor, not a baseline predictor. Outputs include the change
in trust in parliament and government from the two Eurobarometer waves before the event to the first
wave starting 90-270 days after it, minus the same change in EU countries without a coded event in
that window. ESS parliament trust (0-10, biennial) is added as a second source when the ESS table exists.
This is a table for describing and, later, testing; it fits no model and shows no causal effect.
"""

from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

import pandas as pd

import radical_links
from trust_windows import EU27, ISO3_TO_EB, comparison_change, comparison_countries, load_waves

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC = ROOT / "data/raw", ROOT / "data/processed"
POST_MIN_DAYS, POST_MAX_DAYS = 90, 270
HELD_OUT = {"FRA_2024_25_instability"}  # France is the application case, kept out of fitting
OUTPUTS = {"National parliament": "parl", "National government": "gov", "Political parties": "parties"}


def load_inputs():
    events = pd.read_csv(ROOT / "data/reference/s1_verified_events.csv", parse_dates=["ending_cabinet_inauguration_date", "verified_event_date"])
    all_events = events.copy()
    events = events[events.primary_scenario.eq("S1") & events.include_in_s1_training.isin(["yes", "held_out", "review"])].copy()
    with ZipFile(RAW / "ppeg_2025v1/ppeg_gov_2025v1.zip") as archive:
        gov = pd.read_csv(archive.open("ppeg_gov_2025v1.csv"), low_memory=False)
    gov["idate"] = pd.to_datetime(gov.idate)
    gov["edate"] = pd.to_datetime(gov.edate)
    cabinets = gov.drop_duplicates(["iso3c", "idate"])
    elections = election_table()
    macro = pd.read_csv(PROC / "eurostat_macro_country_year.csv")
    reference = pd.read_csv(RAW / "shocks/episodes.csv")
    reference["start_date"] = pd.to_datetime(reference.start)
    reference["end_date"] = pd.to_datetime(reference.end) + pd.offsets.MonthEnd(0)
    ess_path = PROC / "ess_country_round_summary.csv"
    ess = pd.read_csv(ess_path, parse_dates=["interview_median"]) if ess_path.exists() else None
    return events, all_events, cabinets, elections, macro, reference, ess


def election_table() -> pd.DataFrame:
    """One row per PPEG parliamentary election: turnout and effective number of parties.

    Turnout = votes cast / electorate. Effective number of parties = 1 / sum of squared vote shares,
    counting an alliance's member parties as one list (as in build_shock_numbers.py). Compulsory voting
    comes from the International IDEA export. Radical vote share is not included: the PopuList
    classification in data/reference/radical_parties.csv covers only eight countries, none of the
    other S1 countries.
    """
    cols = ["iso3c", "edate", "party_id", "v_share", "alliance", "alliance_id", "total_vote", "electorate"]
    with ZipFile(RAW / "ppeg_2025v1/ppeg_parl_2025v1.zip") as archive:
        parl = pd.read_csv(archive.open("ppeg_parl_2025v1.csv"), usecols=cols, low_memory=False)
    parl["edate"] = pd.to_datetime(parl.edate)
    member = parl.alliance.eq("Electoral alliance member") & parl.alliance_id.notna()
    parl["list_id"] = parl.alliance_id.where(member, parl.party_id)
    rows = []
    for (iso3, edate), g in parl.groupby(["iso3c", "edate"]):
        shares = g.groupby("list_id").v_share.sum()
        electorate, votes = g.electorate.iloc[0], g.total_vote.iloc[0]
        rows.append(dict(iso3c=iso3, edate=edate, turnout_pct=100 * votes / electorate if electorate > 0 else float("nan"),
                         effective_parties=1 / (shares ** 2).sum() if (shares ** 2).sum() > 0 else float("nan")))
    table = pd.DataFrame(rows)
    idea = pd.read_excel(RAW / "idea_export_voter_turnout_database_region.xlsx", sheet_name="Parliamentary")
    idea["year"] = pd.to_datetime(idea.Year, errors="coerce").dt.year
    flag = idea.assign(compulsory=idea["Compulsory voting"].eq("Yes")).groupby(["ISO3", "year"]).compulsory.max()
    table["compulsory_voting"] = [bool(flag.get((r.iso3c, r.edate.year), False)) for r in table.itertuples()]
    return table


EARLY_ENDINGS = {"LoPS", "Diss", "ResPM", "IoHS"}  # PPEG reasons for an early end: no support, dissension, PM resigned, head of state


def government_inputs(cabinets, iso3, date):
    """Instability before the event and the time until a PPEG non-caretaker cabinet followed it."""
    c = cabinets[cabinets.iso3c == iso3].sort_values("idate").copy()
    c["ended"] = c.idate.shift(-1)  # the next inauguration stands in for the end date
    start = date - pd.DateOffset(months=24)
    after = c[c.idate > date]
    full = after[after.tog.ne("EC")]
    first30 = after[after.idate <= date + pd.Timedelta(days=30)].head(1)
    return dict(d30_successor_inaugurated=bool(len(first30)),
                d30_days_to_successor=(first30.idate.iloc[0] - date).days if len(first30) else float("nan"),
                d30_successor_is_caretaker=(bool(first30.tog.iloc[0] == "EC") if len(first30) else pd.NA),
                cabinets_24m_before=int(((c.idate > start) & (c.idate <= date)).sum()),
                early_endings_24m_before=int(((c.ended > start) & (c.ended <= date) & c.rft.isin(EARLY_ENDINGS)).sum()),
                days_until_non_caretaker_cabinet=(full.idate.iloc[0] - date).days if len(full) else float("nan"),
                successor_is_caretaker=bool(len(after) and after.tog.iloc[0] == "EC"))


def radical_shares() -> pd.DataFrame:
    """Radical vote share per election: PopuList far right and far left parties linked to PPEG.

    France uses the team's table data/reference/radical_parties.csv (its DISPUTED and PARTIAL rows are kept
    apart); the other countries use outputs/data_audit/popu_ppeg_links.csv from radical_links.py. Parties
    that PPEG folds into an "Others" row cannot be counted, so the shares are lower bounds.
    """
    links_path = ROOT / "outputs/data_audit/popu_ppeg_links.csv"
    if not links_path.exists():
        return pd.DataFrame(columns=["iso3", "edate"])
    links = pd.read_csv(links_path, keep_default_na=False)
    team = pd.read_csv(ROOT / "data/reference/radical_parties.csv")
    team = team[team.iso3.eq("FRA")].rename(columns={"party_id": "ppeg_party_id"}).assign(status="linked")
    links = pd.concat([links[~links.iso3.eq("FRA")], team[["iso3", "ppeg_party_id", "family", "first_year", "last_year", "status", "note"]]], ignore_index=True)
    with ZipFile(RAW / "ppeg_2025v1/ppeg_parl_2025v1.zip") as archive:
        ppeg = pd.read_csv(archive.open("ppeg_parl_2025v1.csv"), usecols=["iso3c", "edate", "party_id", "v_share"], low_memory=False)
    return radical_links.election_shares(ppeg, links)


def election_outcomes(elections, iso3, date, shares=None):
    """Previous and next parliamentary election around the event, with turnout and fragmentation change."""
    e = elections[elections.iso3c == iso3].sort_values("edate")
    prev, nxt = e[e.edate <= date].tail(1), e[e.edate > date].head(1)
    out = dict(prev_election=prev.edate.iloc[0].date() if len(prev) else None, next_election=nxt.edate.iloc[0].date() if len(nxt) else None,
               next_election_gap_days=(nxt.edate.iloc[0] - date).days if len(nxt) else float("nan"))
    if len(prev) and len(nxt):
        out.update(turnout_prev_pct=prev.turnout_pct.iloc[0], turnout_next_pct=nxt.turnout_pct.iloc[0],
                   turnout_change_pp=nxt.turnout_pct.iloc[0] - prev.turnout_pct.iloc[0],
                   effective_parties_prev=prev.effective_parties.iloc[0], effective_parties_next=nxt.effective_parties.iloc[0],
                   effective_parties_change=nxt.effective_parties.iloc[0] - prev.effective_parties.iloc[0],
                   compulsory_voting=bool(nxt.compulsory_voting.iloc[0] or prev.compulsory_voting.iloc[0]))
    if shares is not None and len(shares):
        def share(row):
            hit = shares[(shares.iso3 == iso3) & (shares.edate == row.edate.iloc[0])]
            return (hit.radical_pct.iloc[0], hit.disputed_pct.iloc[0]) if len(hit) else (float("nan"), float("nan"))
        if len(prev):
            out["radical_prev_pct"], out["radical_disputed_prev_pct"] = share(prev)
        if len(nxt):
            out["radical_next_pct"], out["radical_disputed_next_pct"] = share(nxt)
        if len(prev) and len(nxt):
            out["radical_change_pp"] = out["radical_next_pct"] - out["radical_prev_pct"]
    return out


def trust_outcome(eb, code, institution, event_date, countries_hit):
    """Pre/post trust for one country around an event, and the change in countries not hit."""
    d = eb[(eb.institution == institution) & (eb.country_code == code)].sort_values("start")
    pre = d[d.end < event_date].tail(2)
    post = d[d.start.between(event_date + pd.Timedelta(days=POST_MIN_DAYS), event_date + pd.Timedelta(days=POST_MAX_DAYS))].head(1)
    row = {"pre_waves": "; ".join(f"{s:%Y-%m-%d}" for s in pre.start), "pre_trust_pct": pre.trust.mean() if len(pre) == 2 else float("nan"),
           "pre_gap_days": (event_date - pre.end.iloc[-1]).days if len(pre) else float("nan")}
    row.update(post_wave_start=post.start.iloc[0] if len(post) else pd.NaT,
               post_wave_end=post.end.iloc[0] if len(post) else pd.NaT,
               post_trust_pct=post.trust.iloc[0] if len(post) else float("nan"))
    if len(pre) == 2 and len(post):
        row["change_pp"] = row["post_trust_pct"] - row["pre_trust_pct"]
        window_end = post.end.iloc[0]
        window_start = pre.start.iloc[0]
        excluded = {code} | {c for c, (a, b) in countries_hit.items() if a <= window_end and b >= window_start}
        change, n = comparison_change(eb, institution, pre.wave, post.wave.iloc[0], excluded)
        row.update(comparison_change_pp=change, comparison_countries=n, change_beyond_comparison_pp=row["change_pp"] - change,
                   comparison_group=";".join(comparison_countries(eb, institution, pre.wave, post.wave.iloc[0], excluded)))
    return row


def ess_outcome(ess, iso3, event_date):
    """ESS trust in parliament (0-10) at the last round before and first round after the event."""
    if ess is None:
        return {}
    d = ess[ess.iso3.eq(iso3) & ess.interview_median.notna()].sort_values("interview_median")
    before = d[d.interview_median < event_date].tail(1)
    after = d[d.interview_median >= event_date].head(1)
    out = {}
    if len(before):
        out.update(ess_round_before=int(before.essround.iloc[0]), ess_trstprl_before=before.trstprl_mean.iloc[0],
                   ess_before_gap_days=(event_date - before.interview_median.iloc[0]).days)
    if len(after):
        out.update(ess_round_after=int(after.essround.iloc[0]), ess_trstprl_after=after.trstprl_mean.iloc[0],
                   ess_after_gap_days=(after.interview_median.iloc[0] - event_date).days)
    # A change is reported only when both rounds are within two years of the event; further away the
    # two rounds say little about this event (the gaps stay in the table).
    if len(before) and len(after) and out["ess_before_gap_days"] <= 730 and out["ess_after_gap_days"] <= 730:
        out["ess_trstprl_change"] = after.trstprl_mean.iloc[0] - before.trstprl_mean.iloc[0]
    return out


# --- Variable dictionary: every column, when it is known, and where it comes from -----------------
# timing: label | day0 (known on the event date) | day30 (known 30 days after it) | post_event_descriptor (known only afterwards, not a
# predictor) | outcome | design
TRUST_COLUMNS = {
    "pre_waves": ("day0", "Start dates of the two Eurobarometer waves ending before the event"),
    "pre_trust_pct": ("day0", "Mean 'tend to trust' of those two waves, %"),
    "pre_gap_days": ("day0", "Days from the end of the last pre-event wave to the event"),
    "post_wave_start": ("outcome", "Start of the first wave beginning 90-270 days after the event"),
    "post_wave_end": ("outcome", "End of that wave"),
    "post_trust_pct": ("outcome", "'Tend to trust' in that wave, %"),
    "change_pp": ("outcome", "Post-event trust minus pre-event trust, percentage points"),
    "comparison_change_pp": ("outcome", "Same change, averaged over EU27 countries with no reviewed event or reference episode in the window"),
    "comparison_countries": ("outcome", "Number of countries in that comparison group"),
    "comparison_group": ("outcome", "Eurobarometer codes of the countries in that comparison group, separated by semicolons"),
    "change_beyond_comparison_pp": ("outcome", "change_pp minus comparison_change_pp"),
}
INSTITUTIONS = {"parl": "national parliament", "gov": "national government", "parties": "political parties"}
VARIABLES = {
    "episode_id": ("label", "s1_verified_events.csv", "Episode name from data/reference/s1_verified_events.csv"),
    "iso3": ("label", "", "Country"),
    "event_date": ("label", "s1_verified_events.csv", "Date of the verified loss of parliamentary support or equivalent event"),
    "role": ("label", "", "candidate, or held_out (France is the application case and is not fitted)"),
    "provisional_decision": ("label", "s1_verified_events.csv", "yes (S1 episode) or held_out (France); decisions recorded in docs/s1_review_cases.md"),
    "flags": ("label", "s1_verified_events.csv", "Case flags: economic_crisis_context, same_pm_returned, covid_shock_in_window, election_in_window, wider_crisis_continues"),
    "sample_group": ("label", "derived", "held_out; clean (complete window, no election or other reviewed event before the post wave); broad_only (complete window but an election or other event intervenes); no_post_wave (no trust wave 90-270 days after)"),
    "event_type": ("day0", "s1_verified_events.csv", "How the government lost support, coded by hand"),
    "government_type": ("day0", "PPEG gov (tog)", "Type of the ending cabinet at formation, e.g. MWC minimal winning coalition, MPMi multi-party minority"),
    "government_seat_share": ("day0", "PPEG gov (gov_seat)", "Government parties' share of parliamentary seats at formation, 0-1"),
    "government_parties": ("day0", "PPEG gov (ngovparties)", "Number of government parties at formation"),
    "ending_cabinet_age_days": ("day0", "PPEG gov (idate)", "Days from the ending cabinet's inauguration to the event"),
    "review_note": ("label", "s1_verified_events.csv", "Reviewer's note"),
    "econ_year": ("day0", "rule in build_s1_dataset.py", "Year of the economic controls: t-1 if the event is on or after 1 May, else t-2 (assumed publication lag)"),
    "unemployment_pct": ("day0", "Eurostat", "Unemployment rate in econ_year, %"),
    "gdp_growth_pct": ("day0", "Eurostat", "Real GDP growth in econ_year, %"),
    "inflation_pct": ("day0", "Eurostat", "HICP annual inflation in econ_year, %"),
    "cabinets_24m_before": ("day0", "PPEG gov (idate)", "Cabinets inaugurated in the 24 months up to the event"),
    "early_endings_24m_before": ("day0", "PPEG gov (rft)", "Cabinets that ended early (LoPS, Diss, ResPM, IoHS) in the 24 months before the event; the next inauguration stands in for the end date"),
    "d30_successor_inaugurated": ("day30", "PPEG gov (idate)", "A new cabinet was inaugurated within 30 days of the event. PPEG records inaugurations only, so a continuing cabinet acting as caretaker counts as no successor"),
    "d30_days_to_successor": ("day30", "PPEG gov (idate)", "Days to that cabinet, if within 30 days"),
    "d30_successor_is_caretaker": ("day30", "PPEG gov (tog)", "That cabinet is coded expert or caretaker (blank if none)"),
    "d30_election_held": ("day30", "PPEG parl", "A parliamentary election was held within 30 days of the event. Whether one had been called is not recorded"),
    "days_until_non_caretaker_cabinet": ("post_event_descriptor", "PPEG gov (tog, idate)", "Days from the event to the next cabinet not coded expert or caretaker; the final value is known only afterwards"),
    "successor_is_caretaker": ("post_event_descriptor", "PPEG gov (tog)", "The cabinet that followed is coded expert or caretaker"),
    "cabinets_inaugurated_after_event": ("post_event_descriptor", "PPEG gov (idate)", "Cabinets inaugurated between the event and the end of the post-event wave"),
    "election_before_post_wave": ("post_event_descriptor", "PPEG parl", "A parliamentary election fell between the event and the end of the post-event wave"),
    "another_reviewed_event_before_post_wave": ("post_event_descriptor", "s1_verified_events.csv", "Another reviewed event in the same country fell in that period"),
    "prev_election": ("day0", "PPEG parl", "Last parliamentary election on or before the event"),
    "next_election": ("outcome", "PPEG parl", "First parliamentary election after the event"),
    "next_election_gap_days": ("outcome", "PPEG parl", "Days from the event to that election"),
    "turnout_prev_pct": ("day0", "PPEG parl", "Turnout at the previous election: votes cast / electorate, %"),
    "turnout_next_pct": ("outcome", "PPEG parl", "Turnout at the next election, %"),
    "turnout_change_pp": ("outcome", "PPEG parl", "Next minus previous turnout, percentage points"),
    "effective_parties_prev": ("day0", "PPEG parl", "Effective number of parties at the previous election (1 / sum of squared vote shares; alliance members counted as one list)"),
    "effective_parties_next": ("outcome", "PPEG parl", "Same at the next election"),
    "effective_parties_change": ("outcome", "PPEG parl", "Next minus previous"),
    "radical_prev_pct": ("day0", "PopuList + PPEG", "Far-right plus far-left vote share at the previous election, % (PopuList 4.0 parties linked to PPEG; parties PopuList marks borderline, and DISPUTED or PARTIAL ones, excluded; parties inside PPEG 'Others' rows are missed)"),
    "radical_disputed_prev_pct": ("day0", "PopuList + PPEG", "Vote share of borderline, DISPUTED or PARTIAL radical parties at the previous election (e.g. Bulgaria BSP and BBT; France LR and the New Popular Front)"),
    "radical_next_pct": ("outcome", "PopuList + PPEG", "Same at the next election"),
    "radical_disputed_next_pct": ("outcome", "PopuList + PPEG", "Same for borderline, DISPUTED or PARTIAL parties at the next election"),
    "radical_change_pp": ("outcome", "PopuList + PPEG", "Next minus previous radical vote share, percentage points"),
    "compulsory_voting": ("design", "International IDEA", "IDEA flags a legal compulsory-voting rule at the previous or next election; it does not say whether the rule was enforced"),
    "ess_round_before": ("day0", "ESS", "Last ESS round whose median interview date is before the event"),
    "ess_trstprl_before": ("day0", "ESS", "Weighted mean trust in parliament in that round, 0-10"),
    "ess_before_gap_days": ("day0", "ESS", "Days from that round's median interview date to the event"),
    "ess_round_after": ("outcome", "ESS", "First ESS round whose median interview date is on or after the event"),
    "ess_trstprl_after": ("outcome", "ESS", "Weighted mean trust in parliament in that round, 0-10"),
    "ess_after_gap_days": ("outcome", "ESS", "Days from the event to that round's median interview date"),
    "ess_trstprl_change": ("outcome", "ESS", "After minus before; filled only when both rounds are within two years of the event"),
    "complete_parl_window": ("post_event_descriptor", "derived", "Parliament trust is available before and 90-270 days after the event"),
    "clean_window": ("post_event_descriptor", "derived", "Complete window with no PPEG election and no other reviewed event before the post wave ends; does not rule out unreviewed shocks"),
}


def variable_dictionary(columns) -> pd.DataFrame:
    rows = []
    for col in columns:
        if col in VARIABLES:
            timing, source, text = VARIABLES[col]
        else:
            tag, _, rest = col.partition("_")
            if tag in INSTITUTIONS and rest in TRUST_COLUMNS:
                timing, text = TRUST_COLUMNS[rest]
                source, text = "Eurobarometer", f"{text} ({INSTITUTIONS[tag]})"
            else:
                raise KeyError(f"column {col} has no entry in the variable dictionary")
        rows.append(dict(variable=col, timing=timing, source=source, definition=text))
    return pd.DataFrame(rows)


def main() -> None:
    events, all_events, cabinets, elections, macro, reference, ess = load_inputs()
    eb = load_waves()
    shares = radical_shares()

    # Window during which each country had any reviewed event or reference episode: such countries
    # are left out of the comparison group.
    hit = {}
    def mark(code, start, end):
        a, b = hit.get(code, (start, end))
        hit[code] = (min(a, start), max(b, end))
    for ev in all_events.itertuples():
        mark(ISO3_TO_EB.get(ev.iso3c, ev.iso3c), ev.verified_event_date - pd.Timedelta(days=365), ev.verified_event_date + pd.Timedelta(days=365))
    for ep in reference.itertuples():
        mark(ISO3_TO_EB.get(ep.iso3, ep.iso3), ep.start_date, ep.end_date)
    # A single span per country is coarse (it merges separate episodes): it only makes the comparison group stricter.

    rows = []
    for ev in events.drop_duplicates("episode_id").itertuples():
        code = ISO3_TO_EB.get(ev.iso3c, ev.iso3c)
        date = ev.verified_event_date
        cab = cabinets[(cabinets.iso3c == ev.iso3c) & (cabinets.idate == ev.ending_cabinet_inauguration_date)]
        cab = cab.iloc[0] if len(cab) else None
        row = dict(episode_id=ev.episode_id, iso3=ev.iso3c, event_date=date.date(), role="held_out" if ev.episode_id in HELD_OUT else "candidate",
                   provisional_decision=ev.include_in_s1_training, event_type=ev.event_type, flags=ev.flags,
                   government_type=cab.tog if cab is not None else None, government_seat_share=cab.gov_seat if cab is not None else float("nan"),
                   government_parties=cab.ngovparties if cab is not None else float("nan"),
                   ending_cabinet_age_days=(date - ev.ending_cabinet_inauguration_date).days, review_note=ev.review_note)
        # Annual Eurostat figures for year t-1 are assumed published by 1 May of year t (a rule of thumb, not
        # checked against release calendars); an earlier event uses year t-2.
        year = date.year - 1 if date >= pd.Timestamp(date.year, 5, 1) else date.year - 2
        m = macro[(macro.geo == code) & (macro.year == year)]
        row.update(econ_year=year, unemployment_pct=m.une_rt_a_unemployment.iloc[0] if len(m) else float("nan"),
                   gdp_growth_pct=m.nama_10_gdp_real_growth.iloc[0] if len(m) else float("nan"),
                   inflation_pct=m.prc_hicp_aind_inflation.iloc[0] if len(m) else float("nan"))
        row.update(government_inputs(cabinets, ev.iso3c, pd.Timestamp(date)))
        for institution, tag in OUTPUTS.items():
            res = trust_outcome(eb, code, institution, pd.Timestamp(date), hit)
            for key, value in res.items():
                row[f"{tag}_{key}"] = value
        post_end = row.get("parl_post_wave_end")
        end = pd.Timestamp(post_end) if pd.notna(post_end) else pd.Timestamp(date) + pd.Timedelta(days=POST_MAX_DAYS)
        e = elections[(elections.iso3c == ev.iso3c) & (elections.edate > date) & (elections.edate <= end)]
        later = cabinets[(cabinets.iso3c == ev.iso3c) & (cabinets.idate > date) & (cabinets.idate <= end)]
        other = all_events[(all_events.iso3c == ev.iso3c) & (all_events.verified_event_date > date) & (all_events.verified_event_date <= end)
                           & (all_events.episode_id != ev.episode_id)]
        row.update(election_before_post_wave=len(e) > 0, cabinets_inaugurated_after_event=len(later), another_reviewed_event_before_post_wave=len(other) > 0)
        row["d30_election_held"] = bool(((elections.iso3c == ev.iso3c) & (elections.edate > date) & (elections.edate <= pd.Timestamp(date) + pd.Timedelta(days=30))).any())
        row.update(election_outcomes(elections, ev.iso3c, pd.Timestamp(date), shares))
        row.update(ess_outcome(ess, ev.iso3c, pd.Timestamp(date)))
        row["complete_parl_window"] = pd.notna(row.get("parl_change_pp"))
        row["clean_window"] = row["complete_parl_window"] and not (row["election_before_post_wave"] or row["another_reviewed_event_before_post_wave"])
        row["sample_group"] = ("held_out" if row["role"] == "held_out" else "clean" if row["clean_window"]
                               else "broad_only" if row["complete_parl_window"] else "no_post_wave")
        rows.append(row)

    out = pd.DataFrame(rows)
    for col in out.columns:
        if col.endswith("_pp") or col.endswith("_pct") or col.endswith("_share") or col.endswith("_parties"):
            out[col] = out[col].round(3)
    out.to_csv(PROC / "s1_episode_dataset.csv", index=False)
    variable_dictionary(out.columns).to_csv(PROC / "s1_variable_dictionary.csv", index=False)
    usable = out[(out.role == "candidate") & out.complete_parl_window]
    print(f"S1 dataset: {len(out)} episodes ({(out.role == 'held_out').sum()} held out); "
          f"{len(usable)} candidates with a complete parliament-trust window, {int(usable.clean_window.sum())} of them without an election or other event before the post wave.")


if __name__ == "__main__":
    main()
