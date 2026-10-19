"""Does the Hype Fade? Interactive dashboard (Streamlit).

Run:  uv run streamlit run app/streamlit_app.py
Mode: BGG_APP_MODE=full (default) or BGG_APP_MODE=aggregates (hides the game lookup).
Every number on this page comes from app/data/key_numbers.json or app/data/tables/*.csv.
"""

from __future__ import annotations

import html
import os
import random
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import charts, loaders, logic, text  # noqa: E402
from lib.fmt import fmt  # noqa: E402

DEFAULT_GAME_ID = 342942  # Ark Nova
REPO_URL = os.environ.get("BGG_REPO_URL", "https://github.com/nikitorezz/bgg-hype-fade")
WRITEUP_URL = os.environ.get(
    "BGG_WRITEUP_URL", "https://github.com/nikitorezz/bgg-hype-fade/blob/main/reports/writeup.md")
PAGES_URL = os.environ.get("BGG_PAGES_URL", "https://nikitorezz.github.io/bgg-hype-fade/")
AUTHOR = os.environ.get("BGG_AUTHOR", "Nikita Reznichenko")
GOOD_C, BAD_C = "#1E8A4C", "#C62F2F"
PLOT_CONFIG = charts.PLOT_CONFIG   # no zoom/pan: a finger on a chart scrolls the page
COMPARE = {"All new games": "none", "By hype": "hype_quartile", "By popularity": "popularity",
           "By Kickstarter": "kickstarted"}
SEGMENT_TYPES = {"Launch year": "launch_year", "Hype": "hype_quartile",
                 "Starting rating": "start_decile", "Popularity": "popularity",
                 "Kickstarter": "kickstarted"}
HYPE_NOTE = "Hype = how much a game's number of raters grew during months 0–6."
MOBILE_UA = re.compile(r"Mobi|Android|iPhone|iPod", re.I)
TONES = ["fall", "time", "fall", "time"]   # accent of each headline number
REASONS = {
    "left_censored": "was already ranked when the data starts (Oct 2016), so its launch "
                     "was not observed",
    "unknown_pub_year": "has no usable publication year",
    "old_game": "was published well before it entered the ranking, so it is not a new release",
}

CSS = """
<style>
.block-container {max-width: 1060px; padding-top: 2.6rem; padding-bottom: 3rem;}
[data-testid="stHeader"] {background: transparent;}
[data-testid="stDecoration"], #MainMenu, footer {display: none !important;}
h1, h2, h3, h4 {letter-spacing: -0.01em;}
.hero h1 {font-size: 2.7rem; line-height: 1.1; margin: 0 0 .5rem 0; padding: 0; font-weight: 700;}
.hero .deck {font-size: 1.08rem; color: #667085; max-width: 46rem; margin: 0;}
.stats {display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 0 1.2rem;
        margin: 1.8rem 0 .6rem;}
.stat {--c: #667085; padding: .85rem 0 .4rem; border-top: 3px solid var(--c);}
.stat .v {font-size: 2rem; font-weight: 600; line-height: 1.15; font-variant-numeric: tabular-nums;
          color: var(--c);}
.stat .l {font-size: .88rem; color: #667085; margin-top: .2rem;}
.stat.fall {--c: #C62F2F;} .stat.time {--c: #1F5AA6;}
.stats.sm .v {font-size: 1.5rem; color: #1B2430;}
.stats.sm .stat.fall .v {color: #C62F2F;} .stats.sm .stat.rise .v {color: #1E8A4C;}
.stat.rise {--c: #1E8A4C;} .stat.amber {--c: #C27803;} .stat.amber .v {color: #8A5A00;}
@media (max-width: 700px) {
  .block-container {padding: 1.4rem .95rem 2.4rem;}
  .hero h1 {font-size: 1.95rem;}
  .hero .deck {font-size: .98rem;}
  .stats {grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0 .9rem; margin: 1.1rem 0 .3rem;}
  .stat {margin-bottom: .35rem; padding: .6rem 0 .25rem;}
  .stat .v {font-size: 1.6rem;}
  .stat .l {font-size: .8rem;}
  .stats.sm .v {font-size: 1.25rem;}
  .lede {font-size: 1.02rem; line-height: 1.5;}
  .section-title {font-size: 1.25rem;}
  .chart-title {font-size: 1rem; margin-top: 1.3rem;}
  .game-name {font-size: 1.4rem;}
  .trust-num {font-size: 2.3rem;}
  .note {padding: .7rem .85rem; font-size: .95rem;}
  .site-foot {margin-top: 2rem;}
}
/* heading anchor icons are tiny tap targets and useless here */
[data-testid="stHeaderActionElements"] {display: none !important;}
/* the page, not the chart, owns vertical touch scrolling */
.js-plotly-plot, .js-plotly-plot * {touch-action: pan-y;}
/* navigation: wrapped pills instead of a sideways-scrolling tab strip */
[data-testid="stButtonGroup"] {margin: .2rem 0 .8rem;}
[data-testid="stButtonGroup"] button {min-height: 2.5rem;}
/* the section menu is filled blue so it reads as navigation, not as a chart filter */
.st-key-nav button {font-weight: 500;}
.st-key-nav button[aria-checked="true"] {background: #1F5AA6 !important;
                                       border-color: #1F5AA6 !important;}
.st-key-nav button[aria-checked="true"] * {color: #FFFFFF !important;}
.site-foot a {display: inline-block; padding: .35rem 0;}
[aria-label^="Help for"] {min-width: 2rem; min-height: 2rem; display: inline-flex;
                          align-items: center; justify-content: center;}
.seg-wrap {overflow-x: auto; margin: .3rem 0 .8rem;}
table.seg {border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums;
           border: none; font-size: .93rem;}
table.seg th {text-align: left; font-weight: 500; color: #667085; font-size: .8rem; border: none;
              border-bottom: 1px solid #E3E8EE; padding: .4rem .35rem; white-space: nowrap;}
table.seg td {border: none; border-bottom: 1px solid #E3E8EE; padding: .5rem .35rem;
              vertical-align: top;}
table.seg td.n {color: #667085; text-align: right;} table.seg th.n {text-align: right;}
table.seg .ci {display: block; color: #667085; font-size: .75rem;}
table.seg .down {color: #C62F2F; font-weight: 500;} table.seg .up {color: #1E8A4C; font-weight: 500;}
.delta {font-weight: 600; white-space: nowrap;}
.delta.up {color: #1E8A4C;} .delta.down {color: #C62F2F;}
.game-name {font-size: 1.7rem; font-weight: 600; line-height: 1.2; margin: 1rem 0 .35rem;}
.chips {display: flex; flex-wrap: wrap; gap: .4rem; margin: 0 0 .9rem;}
.chip {display: inline-block; padding: .12rem .65rem; border-radius: 999px; font-size: .8rem;
       font-weight: 500; background: #EEF1F5; color: #667085;}
.chip.blue {background: #E6EEF9; color: #14407A;} .chip.amber {background: #FBF0D8; color: #7A4F00;}
.chip.red {background: #FBE9E9; color: #9B2424;} .chip.green {background: #E3F4EA; color: #14693A;}
.lede {font-size: 1.15rem; line-height: 1.55; max-width: 48rem; margin: .4rem 0 1.2rem;}
.section-title {font-size: 1.45rem; font-weight: 600; margin: .6rem 0 .3rem; line-height: 1.25;}
.section-title::before {content: ""; display: inline-block; width: 5px; height: 1em;
                         background: #1F5AA6; border-radius: 2px; margin-right: .6rem;
                         vertical-align: -.1em;}
.section-sub {color: #667085; max-width: 48rem; margin: 0 0 .8rem;}
.chart-title {font-size: 1.05rem; font-weight: 600; margin: 1.6rem 0 .1rem;}
.note {border-left: 3px solid #1F5AA6; background: #EEF4FB; padding: .85rem 1.1rem;
       border-radius: 0 6px 6px 0; color: #1B2430; max-width: 52rem; margin: .4rem 0 1rem;}
.note.fall {border-color: #C62F2F; background: #FDEEEE;}
.note.rise {border-color: #1E8A4C; background: #EAF6EF;}
.note.amber {border-color: #C27803; background: #FBF5E6;}
b, strong {font-weight: 600;}
.lede b, .section-sub b, .note b, .small b {color: #1F5AA6;}
.note.fall b, b.bad {color: #C62F2F;} .note.rise b, b.good {color: #1E8A4C;}
.small {font-size: .85rem; color: #667085; max-width: 52rem;}
.trust-num {font-size: 3rem; font-weight: 600; line-height: 1; margin: .4rem 0 .5rem;
            font-variant-numeric: tabular-nums; color: #1F5AA6;}
.site-foot {margin-top: 3rem; padding-top: 1rem; border-top: 1px solid #E3E8EE; font-size: .82rem;
            color: #667085;}
.site-foot a {color: #667085;}
[data-baseweb="tab-list"] {gap: 1.4rem;}
table.wf {border-collapse: collapse; width: 100%; max-width: 34rem; margin: .3rem 0 1.4rem;
          font-variant-numeric: tabular-nums; border: none;}
table.wf td {border: none; border-bottom: 1px solid #E3E8EE; padding: .45rem .2rem;}
table.wf td:last-child {text-align: right; font-weight: 500;}
table.wf tr:last-child td {font-weight: 600; border-bottom: 2px solid #1B2430;}
[data-baseweb="tab"] p {font-size: .98rem; font-weight: 500;}
</style>
"""

st.set_page_config(page_title="Does the Hype Fade? Board-game ratings after launch",
                   page_icon=":game_die:", layout="centered")


def show(fig) -> None:
    st.plotly_chart(fig, width="stretch", config=PLOT_CONFIG)


def compact() -> bool:
    """True on phones (user agent) or with ?compact=1: charts use the narrow layout."""
    flag = st.query_params.get("compact")
    if flag is not None:
        return flag not in ("0", "false")
    try:
        return bool(MOBILE_UA.search(st.context.headers.get("User-Agent", "")))
    except Exception:  # headers are unavailable outside a browser session (e.g. in tests)
        return False


def choose(key: str, label: str, options: list[str], default: str | None = None) -> str:
    """Wrapping pill selector that always has a value (tapping the chosen pill again keeps it).

    Pills replace dropdowns for short lists: one tap, no on-screen keyboard, nothing scrolls
    sideways.
    """
    default = default or options[0]
    last = f"_{key}_last"
    st.session_state.setdefault(last, default)
    st.session_state.setdefault(key, default)

    def keep() -> None:
        if st.session_state.get(key) is None:
            st.session_state[key] = st.session_state[last]
        else:
            st.session_state[last] = st.session_state[key]

    st.pills(label, options, key=key, on_change=keep, label_visibility="collapsed")
    return st.session_state.get(key) or st.session_state[last]


def md(s: str) -> str:
    """**bold** / *italic* to HTML for use inside custom blocks."""
    import re
    s = html.escape(s)
    s = re.sub(r"!!(.+?)!!", r'<b class="bad">\1</b>', s)
    s = re.sub(r"\+\+(.+?)\+\+", r'<b class="good">\1</b>', s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    return re.sub(r"\*(.+?)\*", r"<i>\1</i>", s)


def section_title(title: str, sub: str | None = None) -> None:
    block = f'<div class="section-title">{html.escape(title)}</div>'
    if sub:
        block += f'<p class="section-sub">{md(sub)}</p>'
    st.markdown(block, unsafe_allow_html=True)


def chart_title(title: str) -> None:
    st.markdown(f'<div class="chart-title">{html.escape(title)}</div>', unsafe_allow_html=True)


def small(s: str) -> None:
    st.markdown(f'<p class="small">{md(s)}</p>', unsafe_allow_html=True)


def hero(n: dict) -> None:
    stats = "".join(f'<div class="stat {tone}"><div class="v">{html.escape(v)}</div>'
                    f'<div class="l">{html.escape(lab)}</div></div>'
                    for (v, lab), tone in zip(text.kpis(n, loaders.app_config()), TONES,
                                              strict=True))
    st.markdown(
        f'<div class="hero"><h1>Does the hype fade?</h1><p class="deck">{html.escape(text.deck(n))}'
        f'</p></div><div class="stats">{stats}</div>', unsafe_allow_html=True)


# ----------------------------------------------------------------------------------------------
def section_fade(n: dict) -> None:
    cfg = loaders.app_config()
    st.markdown(f'<p class="lede">{md(text.headline(n))}</p>', unsafe_allow_html=True)
    label = choose("cmp", "Compare", list(COMPARE))
    adjust = st.toggle("Remove site-wide drift", value=False,
                       help=f"Subtracts the change of {int(logic.kn(n, 'n_control_games')):,} "
                            "established games over the same calendar months.")
    gt = COMPARE[label]
    curves = loaders.table("curve_by_segment")
    df = curves[(curves["group_type"] == gt) & (curves["adjusted"] == int(adjust))]
    show(charts.fig_overview(df, gt, compact=compact()))
    note = (f"Mean change in the displayed rating since a game entered the ranking. "
            f"{int(logic.kn(n, 'n_main_sample')):,} games launched {cfg['main_entry_start'][:4]}–"
            f"{cfg['main_entry_end'][:4]}; the band is the 95% confidence interval.")
    if gt == "kickstarted":
        yrs = cfg["kickstarter_years"]
        note += f" Kickstarter flag available for {yrs[0]}–{yrs[-1]} launches only."
    if gt == "hype_quartile":
        note += f" {HYPE_NOTE}"
    small(note)


def section_gap(n: dict) -> None:
    section_title("New raters still rate below the number on the page", text.gap_text(n))
    show(charts.fig_gap(loaders.table("gap_new_vs_displayed"), compact=compact()))
    with st.expander("How the new-rater average is calculated"):
        st.latex(r"\text{new-rater avg} = \frac{avg_t\,n_t - avg_{t-3}\,n_{t-3}}{n_t - n_{t-3}}")
        st.markdown(
            "Two running averages three months apart give the average of just the ratings added "
            "in between. BGG publishes averages to two decimals, so a value is kept only when at "
            "least 10 ratings were added, the worst-case rounding error is at most 0.5 points and "
            "the result lies between 1 and 10. That is possible for roughly half to two-thirds "
            "of game-months, more often for fast-growing games.")


def section_hype(n: dict) -> None:
    cfg = loaders.app_config()
    first, last = cfg["speed_months"]
    speed = loaders.table("speed_not_size")
    section_title("Hype changes how fast ratings fall, not how far")
    show(charts.fig_speed(speed, (first, last), compact=compact()))
    st.markdown(f'<div class="note">{md(text.hype_takeaway(speed, (first, last)))}</div>',
                unsafe_allow_html=True)
    chart_title("No model finds that hyped games fall further")
    show(charts.fig_specs(n, compact=compact()))
    small(text.specs_caption(n))
    chart_title("Kickstarter games fall further, even from the same start")
    show(charts.fig_kickstarter(loaders.table("kickstarter_by_band"), compact=compact()))
    small(text.kickstarter_caption(n))


def section_trust(n: dict, mode: str) -> None:
    cfg = loaders.app_config()
    section_title("A new game's rating settles after about a year",
                  "How long until most games' ratings are close to where they will be at three "
                  "years? Move the sliders to change what “close” means.")
    c1, c2 = st.columns(2)
    tol = c1.select_slider("Close means within ± rating points", cfg["tolerances"],
                           value=cfg["rule_tolerance"], format_func=lambda v: fmt(v, ".2f"))
    target = c2.slider("Share of games that must be close", 60, 95,
                       int(100 * cfg["rule_share"]), 5, format="%d%%") / 100
    if mode == "full":
        err, obs = loaders.trust_matrix()
        curve = logic.trust_curve(err, obs, tol)
    else:
        acc = loaders.table("q4_accuracy_by_k")
        a = acc[acc["tolerance"] == tol].sort_values("k")
        curve = pd.DataFrame({"k": a["k"].to_numpy(), "share": a["share_within"].to_numpy(),
                              "n": a["n"].to_numpy()})
    k_rule = logic.trust_month(curve, target)
    left, right = st.columns([1, 3])
    with left:
        val = "Not within 30 months" if np.isnan(k_rule) else f"Month {fmt(k_rule, '.0f')}"
        st.markdown(f'<div class="trust-num">{val}</div>', unsafe_allow_html=True)
        default = tol == cfg["rule_tolerance"] and target == cfg["rule_share"]
        small(f"First month when {fmt(100 * target, '.0f')}% of games are within "
              f"±{fmt(tol, '.2f')} of their 3-year rating."
              + (f" 95% CI: months {fmt(n['q4_rule_month']['ci_low'], '.0f')}–"
                 f"{fmt(n['q4_rule_month']['ci_high'], '.0f')}." if default else ""))
    with right:
        show(charts.fig_trust(curve, tol, target, k_rule, compact=compact()))
    chart_title("An adjusted launch rating gets there much sooner")
    bars = logic.adjusted_vs_raw(loaders.table("q4_adjusted_predictor"), cfg["rule_tolerance"])
    show(charts.fig_adjusted(bars, cfg["rule_tolerance"], compact=compact()))
    small(text.adjusted_caption(n, cfg) + " Share of test games within "
          f"±{cfg['rule_tolerance']} of their 3-year rating.")


def section_explore(n: dict) -> None:
    section_title("Explore the groups",
                  "Split the new releases and compare each group's path with the overall one.")
    label = choose("split", "Split by", list(SEGMENT_TYPES))
    adjust = st.toggle("Remove site-wide drift", value=False, key="explore_adjust")
    gt = SEGMENT_TYPES[label]
    curves = loaders.table("curve_by_segment")
    adj = int(adjust)
    seg = curves[(curves["group_type"] == gt) & (curves["adjusted"] == adj)]
    overall = curves[(curves["group_type"] == "none") & (curves["adjusted"] == adj)]
    groups = sorted(seg["group_value"].unique())
    highlight = None
    if len(groups) > 4:
        pretty = {g: charts._label_for(g, gt) for g in groups}
        st.markdown('<p class="small" style="margin:.2rem 0 .1rem">Highlight a group:</p>',
                    unsafe_allow_html=True)
        highlight = choose(f"hl_{gt}", "Highlight", [pretty[g] for g in groups],
                           default=pretty[groups[-1]])
        highlight = next(g for g in groups if pretty[g] == highlight)
    show(charts.fig_explore(seg, overall, gt, highlight, compact=compact()))
    table = loaders.table("segment_change")
    t = table[table["group_type"] == gt].pivot_table(
        index="group_value", columns="metric", values=["mean", "ci_low", "ci_high", "n"])

    def cell(group, metric: str) -> str:
        m, lo, hi = (t.loc[group, (k, metric)] for k in ("mean", "ci_low", "ci_high"))
        tone = "down" if m < 0 else "up"
        return (f'<span class="{tone}">{fmt(m, "+.2f", minus=True)}</span>'
                f'<span class="ci">{fmt(lo, "+.2f", minus=True)} to {fmt(hi, "+.2f", minus=True)}'
                f'</span>')

    rows = "".join(
        f'<tr><td>{html.escape(charts._label_for(g, gt))}</td>'
        f'<td class="n">{int(t.loc[g, ("n", "change_36")]):,}</td>'
        f'<td>{cell(g, "change_12")}</td><td>{cell(g, "change_36")}</td></tr>' for g in t.index)
    st.markdown(
        '<div class="seg-wrap"><table class="seg"><thead><tr><th>Group</th><th class="n">Games</th>'
        f'<th>By month 12</th><th>By month 36</th></tr></thead><tbody>{rows}</tbody></table></div>',
        unsafe_allow_html=True)
    small("Mean change in the displayed rating since entry, with 95% confidence intervals."
          + (f" {HYPE_NOTE}" if gt == "hype_quartile" else "")
          + (" Part of the larger fall for high starters is regression to the mean."
             if gt == "start_decile" else ""))


def _lookup_other(query: str) -> None:
    other = loaders.other_games()
    hits = other[other["latest_name"].str.contains(query, case=False, regex=False)].head(5)
    if hits.empty:
        small("No excluded game matches that name.")
        return
    for _, r in hits.iterrows():
        st.markdown(f'<div class="note amber"><b>{html.escape(r["latest_name"])}</b> is not in '
                    f'the sample: it {REASONS[r["reason"]]}.</div>', unsafe_allow_html=True)


def _stat(value: str, label: str, tone: str = "") -> str:
    return (f'<div class="stat {tone}"><div class="v">{value}</div>'
            f'<div class="l">{label}</div></div>')


def _delta(x: float, digits: int = 2) -> str:
    up = x >= 0
    return (f'<span class="delta {"up" if up else "down"}">{"▲" if up else "▼"} '
            f'{text.signed(x, digits)}</span>')


def _chip(label: str, tone: str = "") -> str:
    return f'<span class="chip {tone}">{html.escape(label)}</span>'


def _verdict(n: dict, row: pd.Series, k: int, change: float, rank_better: bool,
             wide: pd.DataFrame, games: pd.DataFrame) -> tuple[str, str] | None:
    """(sentence, tone) comparing the game's change with games launched in the same year."""
    year = int(row["entry_year"])
    dist = logic.cohort_change_distribution(wide, games, year, k)
    if k < 3 or len(dist) < 20:
        return None
    if change < 0:
        p = logic.share_fallen_further(change, dist)
        msg = (f"By month {k} its rating fell **{fmt(abs(change), '.2f')}**, more than "
               f"**{fmt(100 * (1 - p), '.0f')}%** of games launched in {year}.")
        if rank_better:
            msg += (f" Its rank still improved, as it did for "
                    f"{fmt(100 * logic.kn(n, 'share_rank_improved_36'), '.0f')}% of games.")
        return msg, "fall"
    share = float((dist >= 0).mean())
    return (f"By month {k} its rating held or rose ({text.signed(change)}), which only "
            f"**{fmt(100 * share, '.0f')}%** of games launched in {year} managed."), "rise"


def _pick_random(labels: list[str]) -> None:
    st.session_state["lk_pick"] = random.choice(labels)


def section_lookup(n: dict) -> None:
    """Per-game view: one game's rating, rank and audience against games from its launch year."""
    cfg = loaders.app_config()
    g, traj, wide = loaders.games(), loaders.trajectories(), loaders.wide()
    g = g.sort_values(["latest_name", "entry_year"]).reset_index(drop=True)
    label = g["latest_name"] + " (" + g["entry_year"].astype(str) + ")"
    label = label.where(~label.duplicated(keep=False), label + " · BGG " + g["game_id"].astype(str))
    g["label"] = label
    labels = g["label"].tolist()
    sample_labels = g.loc[g["main_sample"], "label"].tolist()
    if "lk_pick" not in st.session_state:
        hit = g.loc[g["game_id"] == DEFAULT_GAME_ID, "label"]
        st.session_state["lk_pick"] = hit.iloc[0] if len(hit) else labels[0]

    section_title("Look up a game",
                  f"{len(g):,} board games entered the BoardGameGeek ranking after October 2016. "
                  "Pick one to see how its rating, rank and audience moved, and how that compares "
                  "with games launched in the same year.")
    c1, c2 = st.columns([5, 1], vertical_alignment="bottom")
    pick = c1.selectbox("Search for a game", labels, key="lk_pick",
                        label_visibility="collapsed", placeholder="Search for a game")
    c2.button("Random", on_click=_pick_random, args=(sample_labels,), width="stretch",
              icon=":material/shuffle:")
    c3, c4 = st.columns([5, 3], vertical_alignment="bottom")
    other_pick = c3.selectbox("Compare with", labels, index=None, key="lk_other",
                              placeholder="Compare with another game (optional)",
                              label_visibility="collapsed")
    metric_label = c4.segmented_control("Show", ["Rating", "Rank", "Raters"], default="Rating",
                                        key="lk_metric", label_visibility="collapsed")
    metric = (metric_label or "Rating").lower()

    row = g[g["label"] == pick].iloc[0]
    tj = traj[traj["game_id"] == row["game_id"]].sort_values("k")
    last = logic.last_observed(tj)
    k_now = int(last["k"])
    start, now = float(row["avg_m0"]), float(last["avg_rating"])
    change = now - start
    expected = row.get("adj_rating_k0")

    chips = [_chip(f"Entered {pd.Timestamp(row['entry_month']).strftime('%b %Y')}")]
    q = row["hype_quartile"]
    if q == q:
        chips.append(_chip(f"Hype Q{int(q)} of 4", "blue"))
    if row["followup_months"] < cfg["final_k"]:
        chips.append(_chip(f"Still in follow-up: {int(row['followup_months'])} of "
                           f"{cfg['final_k']} months", "amber"))
    elif not row["main_sample"]:
        chips.append(_chip("Outside the analysis sample", "amber"))
    st.markdown(f'<div class="game-name">{html.escape(row["latest_name"])}</div>'
                f'<div class="chips">{"".join(chips)}</div>', unsafe_allow_html=True)

    rank_now = float(last["rank"]) if last["rank"] == last["rank"] else float("nan")
    rank_better = bool(rank_now == rank_now and row["rank_m0"] == row["rank_m0"]
                       and rank_now < float(row["rank_m0"]))
    v = _verdict(n, row, k_now, change, rank_better, wide, g)
    if v is not None:
        st.markdown(f'<div class="note {v[1]}">{md(v[0])}</div>', unsafe_allow_html=True)

    rise = change >= 0
    adj_txt = "–" if not expected == expected else fmt(expected, ".2f")
    actual = row["avg_m36"] if row["observed_m36"] and row["avg_m36"] == row["avg_m36"] else None
    adj_label = "expected rating at month 36, from launch data" + (
        f" (actual {fmt(actual, '.2f')})" if actual is not None else "")
    rank_txt = (f"#{int(row['rank_m0']):,} → #{int(rank_now):,}"
                if rank_now == rank_now and row["rank_m0"] == row["rank_m0"] else "–")
    stats = "".join([
        _stat(f"{fmt(start, '.2f')} → {fmt(now, '.2f')}",
              f"{_delta(change)} by month {k_now}", "rise" if rise else "fall"),
        _stat(adj_txt, adj_label, "amber"),
        _stat(rank_txt, "rank at entry → latest"),
        _stat(f"{int(row['raters_m0']):,} → {int(last['n_raters']):,}", "raters at entry → latest"),
    ])
    st.markdown(f'<div class="stats sm">{stats}</div>', unsafe_allow_html=True)

    cohort = loaders.table("curve_by_entry_year")
    cohort = cohort[cohort["entry_year"] == row["entry_year"]].sort_values("k")
    other = None
    if other_pick and other_pick != pick:
        orow = g[g["label"] == other_pick].iloc[0]
        other = (orow["latest_name"], traj[traj["game_id"] == orow["game_id"]])
    show(charts.fig_lookup(row["latest_name"], tj, start, cohort, "new_avg_3", metric, other,
                           expected if expected == expected else None,
                           f"Typical {int(row['entry_year'])} launch", compact=compact()))
    captions = {
        "rating": "Blue: the rating shown on BoardGameGeek. Red dots: the average of ratings "
                  "added in the previous three months. Grey dashes: the average path of games "
                  f"launched in {int(row['entry_year'])}, from this game's starting rating. "
                  "Amber diamond: the rating a model expects at month 36 from launch-month data.",
        "rank": "Position in the BoardGameGeek ranking, 1 being the best. Log scale.",
        "raters": "Number of ratings the game had collected. Log scale."}
    if other is not None and metric == "rating":
        captions["rating"] = (f"Displayed rating of {row['latest_name']} (blue) and {other[0]} (amber), "
                              "by months since each entered the ranking. The numbers above "
                              f"describe {row['latest_name']}.")
    small(captions[metric])
    tr = cfg["train_entry_years"]
    if tr[0] <= int(row["entry_year"]) <= tr[1]:
        small(f"The expected rating for {tr[0]}–{tr[1]} launches comes from a model fitted on "
              "those same games, so it flatters the model slightly.")
    st.markdown("&nbsp;", unsafe_allow_html=True)
    query = st.text_input("Looking for an established game?", placeholder="e.g. Gloomhaven",
                          help="Games already ranked in October 2016 or published long before "
                               "entering the ranking are not new releases, so they are not in the "
                               "sample. Search a name to see why a game is missing.")
    if query.strip():
        _lookup_other(query.strip())


def section_method(n: dict) -> None:
    cfg = loaders.app_config()
    section_title("Method and data")
    st.markdown(
        "**Data.** The [bgg-ranking-historicals](https://github.com/beefsack/bgg-ranking-"
        "historicals) archive holds BoardGameGeek's full ranked list for every day since "
        f"October 2016. One snapshot per month (to {cfg['end_month'][:7]}) gives a panel of "
        f"{int(logic.kn(n, 'n_main_sample')):,} games launched {cfg['main_entry_start'][:4]}–"
        f"{cfg['main_entry_end'][:4]}, each followed for {cfg['final_k']} months.\n\n"
        "**Cleaning.** Truncated snapshots are swapped for the first complete file of the month, "
        "duplicate rows are removed, junk publication years are excluded, and the new-rater "
        "average is kept only when its rounding error is small.\n\n"
        "**Models.** A game fixed-effects event study, robust cross-sectional regressions, "
        "game-level bootstrap intervals, an eight-variant robustness grid and an out-of-sample "
        "predictive check.")
    qc = loaders.table("qc_results")["status"].value_counts()
    total = int(qc.get("PASS", 0) + qc.get("WARN", 0) + qc.get("FAIL", 0))
    st.markdown(f"**Quality checks.** {int(qc.get('PASS', 0))} of {total} automated checks pass.")
    wf = loaders.table("sample_waterfall").sort_values("step_no")
    steps = ["All games ever ranked", "Not already ranked when the data starts",
             "With a usable publication year", "New releases",
             f"Launched {cfg['main_entry_start'][:4]}–{cfg['main_entry_end'][:4]}",
             f"Still ranked at month {cfg['final_k']} (analysis sample)"]
    rows = "".join(f"<tr><td>{html.escape(lab)}</td><td>{int(v):,}</td></tr>"
                   for lab, v in zip(steps, wf["n_games"], strict=True))
    st.markdown(f'<div class="chart-title">How the sample was built</div>'
                f'<table class="wf">{rows}</table>', unsafe_allow_html=True)
    st.markdown("**Limitations**")
    st.markdown(
        "- A game enters the ranking only at 30 ratings, so its first ratings are folded into "
        "month 0: the analysis measures change *after* entry.\n"
        "- Observational data: patterns, not causal effects. Rater growth also reflects print "
        "runs, distribution and price.\n"
        "- Regression to the mean and self-selection of the launch audience can't be fully "
        "separated.\n"
        "- The new-rater average is approximate and over-represents fast-growing games.\n"
        "- One enthusiast platform; monthly snapshots.")
    b1, b2, b3, _ = st.columns([1, 1, 1, 2])
    b1.link_button("Read the write-up", WRITEUP_URL, width="stretch")
    b2.link_button("View the code", REPO_URL, width="stretch")
    b3.link_button("Static version", PAGES_URL, width="stretch")


# ----------------------------------------------------------------------------------------------
def main() -> None:
    st.html(CSS)
    mode = loaders.app_mode()
    n = loaders.numbers()
    hero(n)
    sections = [("fade", "The fade", lambda: section_fade(n))]
    if mode == "full":
        sections.append(("lookup", "Look up a game", lambda: section_lookup(n)))
    sections += [("gap", "New vs displayed", lambda: section_gap(n)),
                 ("hype", "Hype", lambda: section_hype(n)),
                 ("trust", "When to trust", lambda: section_trust(n, mode)),
                 ("explore", "Explore", lambda: section_explore(n)),
                 ("method", "Method", lambda: section_method(n))]
    names = [label for _, label, _ in sections]
    by_key = {key: label for key, label, _ in sections}
    wanted = by_key.get(st.query_params.get("s", ""), names[0])  # deep link: ?s=hype
    if "nav" not in st.session_state:
        st.session_state["nav"] = wanted
    current = choose("nav", "Section", names, default=wanted)
    key, _, render = next(sec for sec in sections if sec[1] == current)
    st.query_params["s"] = key
    render()
    st.markdown(
        f'<div class="site-foot">Data: daily BoardGameGeek ranking snapshots from '
        f'<a href="https://github.com/beefsack/bgg-ranking-historicals">bgg-ranking-historicals'
        f'</a>, through {loaders.app_config()["end_month"][:7]}. Data © BoardGameGeek; this '
        f'project is not affiliated with BoardGameGeek. Analysis and code by '
        f'<a href="{REPO_URL}">{html.escape(AUTHOR)}</a>.</div>', unsafe_allow_html=True)


main()
