"""Does the Hype Fade? Interactive dashboard (Streamlit).

Run:  uv run streamlit run app/streamlit_app.py
Mode: APP_MODE=full (default) or APP_MODE=aggregates (no game-level data, no lookup).
Every number on this page comes from app/data/key_numbers.json or app/data/tables/*.csv.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import charts, loaders, logic  # noqa: E402

DEFAULT_GAME_ID = 342942  # Ark Nova (a spot-check game from the pipeline QC)
REPO_URL = os.environ.get("BGG_REPO_URL", "")
WRITEUP_URL = os.environ.get("BGG_WRITEUP_URL", "")
PLOT_CONFIG = {"displayModeBar": False, "responsive": True}
COMPARE = {"None (all new games)": "none", "Launch year": "launch_year",
           "Hype quartile": "hype_quartile", "Popularity (top 10% vs rest)": "popularity",
           "Kickstarted": "kickstarted"}
REASONS = {
    "left_censored": "was already in the ranking when the data starts (Oct 2016), so its launch "
                     "was not observed",
    "unknown_pub_year": "has no usable publication year, so it cannot be classed as a new release",
    "old_game": "was published well before it entered the ranking, so it is not a new release",
}

st.set_page_config(page_title="Does the Hype Fade?", page_icon=":game_die:", layout="wide")


def show(fig) -> None:
    st.plotly_chart(fig, width="stretch", config=PLOT_CONFIG)


def signed(x: float, digits: int = 2) -> str:
    return f"{x:+.{digits}f}".replace("-", "−")


# ----------------------------------------------------------------------------------------------
def section_overview(n: dict, mode: str) -> None:
    kn = logic.kn
    cfg = loaders.app_config()
    st.subheader("Does the hype fade?")
    st.markdown(
        f"**Launch ratings oversell.** On BoardGameGeek the typical new game loses "
        f"**{abs(kn(n, 'change_36')):.2f} points** over three years, most of it in year one, and "
        "new raters still rate it lower at the end. Hype doesn't decide how far a game falls; it "
        "decides how fast the number catches up.")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("3-year change", signed(kn(n, "change_36")),
              help=f"95% CI {logic.ci_text(n, 'change_36', 2)}; n = {n['change_36']['n']:,}")
    c1.caption("Average fall in a new game's displayed rating")
    c2.metric("Fall happening in year one", f"{100 * kn(n, 'share_of_decline_by_12'):.0f}%",
              help=f"95% CI {100 * n['share_of_decline_by_12']['ci_low']:.0f}-"
                   f"{100 * n['share_of_decline_by_12']['ci_high']:.0f}%")
    c2.caption("Share of the 3-year fall reached by month 12")
    c3.metric("Games that decline", f"{100 * kn(n, 'share_declining'):.0f}%")
    c3.caption("End lower than they started (month 36)")
    c4.metric("Trust point", f"Month {kn(n, 'q4_rule_month'):.0f}",
              help=f"95% CI {n['q4_rule_month']['ci_low']:.0f}-{n['q4_rule_month']['ci_high']:.0f}")
    c4.caption(f"{100 * cfg['rule_share']:.0f}% of games are within ±{cfg['rule_tolerance']} "
               "of their 3-year rating")

    st.markdown("#### How ratings move after a game enters the ranking")
    col_a, col_b = st.columns([2, 1])
    label = col_a.selectbox("Compare by", list(COMPARE))
    adjust = col_b.toggle(
        "Adjust for site-wide drift", value=False,
        help=f"Subtract the change of {int(kn(n, 'n_control_games')):,} established games over "
             "the same calendar months.")
    gt = COMPARE[label]
    curves = loaders.table("curve_by_segment")
    df = curves[(curves["group_type"] == gt) & (curves["adjusted"] == int(adjust))]
    show(charts.fig_overview(df, gt))
    if gt == "kickstarted":
        yrs = cfg["kickstarter_years"]
        st.caption(f"Only games entering {yrs[0]}-{yrs[-1]} can be matched to the Kaggle metadata; "
                   "the flag comes from a 2022 snapshot. Descriptive only.")
    st.caption(
        f"Main sample: new releases entering the ranking {cfg['main_entry_start'][:7]} to "
        f"{cfg['main_entry_end'][:7]}, followed for {cfg['final_k']} months "
        f"({int(kn(n, 'n_main_sample')):,} games). Shaded bands are 95% confidence intervals; "
        "hover for the exact values.")


def section_gap(n: dict) -> None:
    kn = logic.kn
    st.subheader("What new raters say vs what is displayed")
    st.markdown(
        f"The displayed rating is a running average, so it still carries the enthusiasm of the "
        f"launch crowd. Looking only at the ratings added recently, new raters score games "
        f"**{abs(kn(n, 'gap_k3')):.2f} below the displayed average at month 3 and "
        f"{abs(kn(n, 'gap_k36')):.2f} below at month 36**. The decline isn't finished.")
    show(charts.fig_gap(loaders.table("gap_new_vs_displayed")))
    st.caption("Lower panel: share of game-months where the new-rater average can be backed out "
               "reliably. It is available for roughly half to two-thirds of game-months, more "
               "often for fast-growing games.")
    with st.expander("How is the new-rater average computed?"):
        st.latex(r"\text{new avg} = \frac{avg_t n_t - avg_{t-3} n_{t-3}}{n_t - n_{t-3}}")
        st.markdown(
            "From two running averages three months apart, the average of just the ratings added "
            "in between. BGG publishes averages with two decimals, so the result carries a "
            "rounding error of up to `0.005 * (n_t + n_(t-3)) / (n_t - n_(t-3))`. A value is kept "
            "only if at least 10 ratings were added **and** that error bound is at most 0.5 "
            "points, **and** the result lies between 1 and 10. The gap is computed game by game "
            "and then averaged with equal weight.")


def section_hype(n: dict) -> None:
    kn = logic.kn
    cfg = loaders.app_config()
    first, last = cfg["speed_months"]
    st.subheader("Hype: speed, not size")
    speed = loaders.table("speed_not_size")
    show(charts.fig_speed(speed, (first, last)))
    q1, q4 = speed.iloc[0], speed.iloc[-1]
    st.info(
        f"**Takeaway.** Hype changes how fast ratings fall, not how far. By month {first}, the "
        f"most-hyped quarter of games has lost {abs(q4[f'change_{first}']):.2f} points and the "
        f"least-hyped quarter {abs(q1[f'change_{first}']):.2f}. By month {last} they are close "
        f"({abs(q4[f'change_{last}']):.2f} vs {abs(q1[f'change_{last}']):.2f}). A hyped game "
        f"gains a median {q4['growth_median']:.0f}x its launch raters in {first} months, which "
        f"dilutes the early enthusiasts quickly; for a quiet release the launch crowd is still "
        f"{100 * q1['entry_share_median']:.0f}% of raters at month {last}, and new raters rate it "
        f"{abs(q1[f'gap_k{last}']):.2f} below the displayed number. Quiet games haven't faded "
        "less; they haven't finished fading.")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Change curves by hype quartile**")
        curves = loaders.table("curve_by_segment")
        df = curves[(curves["group_type"] == "hype_quartile") & (curves["adjusted"] == 0)]
        show(charts.fig_overview(df, "hype_quartile"))
    with col2:
        st.markdown("**Does hype predict the size of the fall? (H2: negative sign)**")
        show(charts.fig_specs(n))
        st.caption(
            f"Spec A (controls for starting rating and size): {signed(kn(n, 'spec_a_hype'), 3)}; "
            f"Spec B (change after month 6): {signed(kn(n, 'spec_b_hype'), 3)}. No spec supports "
            "a bigger fall for more-hyped games. Observational data: patterns, not causal effects.")
    st.markdown("**Kickstarted games fall further, even from the same starting rating**")
    bands = loaders.table("kickstarter_by_band")
    show(charts.fig_kickstarter(bands))
    st.caption(
        f"Kickstarted games start higher ({kn(n, 'ks_avg_m0'):.2f} vs {kn(n, 'nonks_avg_m0'):.2f}) "
        f"and, within the same starting band, fall {abs(kn(n, 'ks_gap_within_bands')):.2f} more on "
        "average. Descriptive only: the flag comes from a January 2022 snapshot and covers about "
        f"{100 * kn(n, 'q3_share_kickstarted'):.0f}% of games, so it is probably broader than "
        "\"launched via Kickstarter\".")


def section_trust(n: dict, mode: str) -> None:
    kn = logic.kn
    cfg = loaders.app_config()
    st.subheader("When can you trust a new game's rating?")
    if mode == "full":
        c1, c2 = st.columns(2)
        tol = round(c1.slider("Tolerance (± rating points)", 0.10, 0.50, cfg["rule_tolerance"],
                              0.05), 2)
        target = c2.slider("Target share of games (%)", 60, 95, int(100 * cfg["rule_share"]),
                           5) / 100
        err, obs = loaders.trust_matrix()
        curve = logic.trust_curve(err, obs, tol)
    else:
        acc = loaders.table("q4_accuracy_by_k")
        tol = st.select_slider("Tolerance (± rating points)", cfg["tolerances"],
                               value=cfg["rule_tolerance"])
        target = st.slider("Target share of games (%)", 60, 95, int(100 * cfg["rule_share"]),
                           5) / 100
        a = acc[acc["tolerance"] == tol].sort_values("k")
        curve = pd.DataFrame({"k": a["k"].to_numpy(), "share": a["share_within"].to_numpy(),
                              "n": a["n"].to_numpy()})
        st.caption("Aggregates mode: only the precomputed tolerances are available.")
    k_rule = logic.trust_month(curve, target)
    default = tol == cfg["rule_tolerance"] and target == cfg["rule_share"]
    left, right = st.columns([1, 3])
    left.metric("Trust month", "never" if np.isnan(k_rule) else f"Month {k_rule:.0f}")
    left.caption(
        f"First month when at least {100 * target:.0f}% of new games are within ±{tol:.2f} of "
        f"their month-{cfg['final_k']} rating."
        + (f" Bootstrap 95% CI for the default: {n['q4_rule_month']['ci_low']:.0f}-"
           f"{n['q4_rule_month']['ci_high']:.0f}." if default else ""))
    with right:
        show(charts.fig_trust(curve, tol, target, k_rule))
    st.caption("Agreement at later months is partly mechanical: the running average at month 24 "
               "already contains most of the raters of month 36.")
    st.markdown("#### A platform could show an adjusted launch rating")
    bars = logic.adjusted_vs_raw(loaders.table("q4_adjusted_predictor"), cfg["rule_tolerance"])
    show(charts.fig_adjusted(bars, cfg["rule_tolerance"]))
    tr, te = cfg["train_entry_years"], cfg["test_entry_years"]
    st.caption(
        f"Trained on games entering {tr[0]}-{tr[1]}, tested on {te[0]}-{te[1]}. At entry the "
        f"adjusted rating is within ±{cfg['rule_tolerance']} of the eventual rating for "
        f"{100 * kn(n, 'q4_test_adj_within_k0'):.0f}% of test games (displayed rating: "
        f"{100 * kn(n, 'q4_test_raw_within_k0'):.0f}%) and cuts the mean error from "
        f"{kn(n, 'q4_test_raw_mae_k0'):.2f} to {kn(n, 'q4_test_adj_mae_k0'):.2f}. It works mostly "
        "by shrinking high launch ratings toward the typical level.")


def _lookup_other(query: str) -> None:
    other = loaders.other_games()
    hits = other[other["latest_name"].str.contains(query, case=False, regex=False)].head(5)
    if hits.empty:
        st.caption("No excluded game matches that name (it may be a new release: use the box "
                   "above).")
        return
    for _, r in hits.iterrows():
        st.warning(f"**{r['latest_name']}** is not in the sample: it {REASONS[r['reason']]}.")


def section_lookup(n: dict) -> None:
    cfg = loaders.app_config()
    g, traj = loaders.games(), loaders.trajectories()
    st.subheader("Look up a game")
    g = g.assign(label=g["latest_name"] + " (" + g["entry_year"].astype(str) + ")")
    labels = g["label"].tolist()
    default = g.index[g["game_id"] == DEFAULT_GAME_ID]
    pick = st.selectbox(f"Search the {len(g):,} new releases", labels,
                        index=int(default[0]) if len(default) else 0)
    row = g[g["label"] == pick].iloc[0]
    tj = traj[traj["game_id"] == row["game_id"]].sort_values("k")
    last = logic.last_observed(tj)
    if row["followup_months"] < cfg["final_k"]:
        st.info(f"Still in follow-up: {int(row['followup_months'])} of {cfg['final_k']} months "
                "observed so far.")
    cohort = loaders.table("curve_by_entry_year")
    cohort = cohort[cohort["entry_year"] == row["entry_year"]].sort_values("k")
    if cohort.empty:  # entry years after the main sample have no published cohort curve
        cohort = loaders.table("curve_overall")
    show(charts.fig_lookup(row.to_dict(), tj, cohort, "new_avg_3"))

    start, now = row["avg_m0"], float(last["avg_rating"])
    dist = logic.cohort_change_distribution(loaders.wide(), g, int(row["entry_year"]),
                                            int(last["k"]))
    frac = logic.share_fallen_further(now - start, dist)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Entered the ranking", pd.Timestamp(row["entry_month"]).strftime("%b %Y"))
    c2.metric(f"Rating: start to month {int(last['k'])}", f"{start:.2f} → {now:.2f}",
              signed(now - start))
    c3.metric(f"Fell further than (of {int(row['entry_year'])} launches)",
              f"{100 * frac:.0f}%" if frac == frac else "n/a",
              help=f"Share of games launched in {int(row['entry_year'])} whose rating fell by "
                   "less over the same number of months.")
    q = row["hype_quartile"]
    c4.metric("Hype quartile", f"Q{int(q)} of 4" if q == q else "n/a",
              help="1 = least hyped (growth in raters during months 0-6).")
    c5, c6, c7 = st.columns(3)
    adj = row.get("adj_rating_k0")
    if adj == adj and adj is not None:
        train = cfg["train_entry_years"]
        in_sample = train[0] <= row["entry_year"] <= train[1]
        c5.metric("Adjusted launch rating", f"{adj:.2f}",
                  help="What the Q4 model would show at entry instead of the raw average."
                       + (" This game is in the model's training years, so the fit is "
                          "in-sample." if in_sample else " Out-of-sample for this game."))
        c5.caption(f"Displayed at entry: {start:.2f}. Actual by month {int(last['k'])}: "
                   f"{now:.2f}" + (" (in-sample)" if in_sample else ""))
    r0, r1 = row["rank_m0"], last["rank"]
    c6.metric("Rank", f"{int(r0):,} → {int(r1):,}" if r0 == r0 and r1 == r1 else "n/a",
              help="Rank is based on a Bayes average, so it often improves while the raw average "
                   "falls.")
    c7.metric("Raters", f"{int(row['raters_m0']):,} → {int(last['n_raters']):,}")
    st.markdown("---")
    q = st.text_input("Looking for an established game (e.g. a classic)?",
                      placeholder="Type a name, e.g. Gloomhaven")
    if q.strip():
        _lookup_other(q.strip())


def section_method(n: dict) -> None:
    cfg = loaders.app_config()
    st.subheader("Method & data")
    st.markdown(
        "**Data.** [`beefsack/bgg-ranking-historicals`](https://github.com/beefsack/"
        "bgg-ranking-historicals) archives BoardGameGeek's full ranked list every day since "
        f"October 2016. I use one snapshot per month (to {cfg['end_month'][:7]}) and follow "
        f"newly released games that entered the ranking between {cfg['main_entry_start'][:7]} "
        f"and {cfg['main_entry_end'][:7]}, each for {cfg['final_k']} months "
        f"({int(logic.kn(n, 'n_main_sample')):,} games).\n\n"
        "**Cleaning.** Truncated snapshots are replaced by the first complete file of the month; "
        "duplicate rows are removed; junk publication years are excluded; and the new-rater "
        "average is kept only when its rounding error is small.\n\n"
        "**Models.** A game fixed-effects event study, cross-sectional OLS with robust standard "
        "errors, game-level bootstrap intervals, a robustness grid, and an out-of-sample "
        "predictive check.")
    wf = loaders.table("sample_waterfall")
    st.markdown("**Sample waterfall**")
    st.dataframe(wf.rename(columns={"step_no": "#", "step": "Step", "n_games": "Games",
                                    "removed": "Removed"}), hide_index=True,
                 width="stretch")
    qc = loaders.table("qc_results")
    counts = qc["status"].value_counts()
    st.markdown(f"**Data-quality checks.** {int(counts.get('PASS', 0))} of "
                f"{int(counts.get('PASS', 0) + counts.get('WARN', 0) + counts.get('FAIL', 0))} "
                f"automated checks pass ({int(counts.get('WARN', 0))} warnings, "
                f"{int(counts.get('FAIL', 0))} failures; {int(counts.get('INFO', 0))} report-only "
                "rows).")
    st.markdown("**Limitations**")
    st.markdown(
        "- A game only enters the ranking at 30 ratings, so its very first ratings are folded "
        "into month 0. I measure change *after* entry.\n"
        "- Observational data: patterns, not causal effects. \"Hype\" (rater growth) also "
        "reflects print runs, distribution and price.\n"
        "- Regression to the mean and self-selection of the launch audience can't be cleanly "
        "separated.\n"
        "- The new-rater estimate is approximate (rounding, edited ratings) and over-represents "
        "fast-growing games.\n"
        "- One enthusiast platform. The Kickstarter flag comes from a 2022 snapshot.\n"
        "- Monthly snapshots only; a daily-data robustness check is future work.")
    links = []
    if REPO_URL:
        links.append(f"[Code]({REPO_URL})")
    if WRITEUP_URL:
        links.append(f"[Write-up]({WRITEUP_URL})")
    if links:
        st.markdown(" · ".join(links))
    st.caption("Metadata: \"Board Game Database from BoardGameGeek\" (threnjen, Kaggle, "
               "CC BY-SA 3.0).")


# ----------------------------------------------------------------------------------------------
def main() -> None:
    mode = loaders.app_mode()
    n = loaders.numbers()
    st.title("Does the Hype Fade?")
    st.caption("Post-release rating trajectories of board games on BoardGameGeek, 2016-2026")
    names = ["Overview", "New raters vs displayed", "Hype: speed, not size",
             "When can you trust a rating?"]
    names += ["Look up a game"] if mode == "full" else []
    names += ["Method & data"]
    tabs = st.tabs(names)
    sections = [lambda: section_overview(n, mode), lambda: section_gap(n),
                lambda: section_hype(n), lambda: section_trust(n, mode)]
    sections += [lambda: section_lookup(n)] if mode == "full" else []
    sections += [lambda: section_method(n)]
    for tab, fn in zip(tabs, sections, strict=True):
        with tab:
            fn()
    st.markdown("---")
    st.caption("Data: daily BoardGameGeek ranking snapshots from beefsack/bgg-ranking-historicals. "
               "Data © BoardGameGeek. This project is not affiliated with BoardGameGeek. "
               f"Snapshots through {loaders.app_config()['end_month'][:7]}.")


main()
