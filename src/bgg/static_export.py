"""``bgg export-static``: the GitHub Pages site.

Writes two pages to ``reports/site/``:
- ``index.html``: a small landing page (no Plotly, < 100 KB) with an inline SVG of the fade,
  the four headline numbers, three findings and links. Kept small so link previews work.
- ``dashboard.html``: the full static dashboard, one self-contained file (Plotly inlined).

Reads only ``app/data`` (aggregate tables + key numbers); charts and sentences come from the same
``app/lib`` modules as the Streamlit app, so the two never disagree.
"""

from __future__ import annotations

import html
import json
import logging
import re
import sys
from pathlib import Path

import pandas as pd

from bgg.config import Config

log = logging.getLogger(__name__)

FONT_LINK = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
             '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
             '<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:ital,wght@'
             '0,400;0,500;0,600;0,700;1,400&display=swap" rel="stylesheet">')

CSS = """
:root{--ink:#1B2430;--ink-2:#667085;--ink-3:#667085;--rule:#E3E8EE;--panel:#F4F6F9;
--blue:#1F5AA6;--red:#C62F2F;--paper:#FFFFFF}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.6 "IBM Plex Sans","Segoe UI",
"Helvetica Neue",Arial,sans-serif;font-feature-settings:"tnum" 0}
a{color:var(--blue);text-decoration:none}a:hover{text-decoration:underline}
a:focus-visible,button:focus-visible{outline:2px solid var(--blue);outline-offset:2px}
.wrap{max-width:1060px;margin:0 auto;padding:0 24px}
header.top{border-bottom:1px solid var(--rule)}
header.top .wrap{display:flex;justify-content:space-between;align-items:center;height:56px}
header.top .brand{font-weight:600;color:var(--ink)}
header.top nav a{color:var(--ink-2);margin-left:22px;font-size:.95rem}
h1{font-size:3rem;line-height:1.08;letter-spacing:-.02em;margin:3rem 0 .8rem;font-weight:700}
.deck{font-size:1.15rem;color:var(--ink-2);max-width:44rem;margin:0}
b{font-weight:600;color:var(--blue,#1F5AA6)}b.bad{color:#C62F2F}b.good{color:#1E8A4C}
.lede{font-size:1.2rem;line-height:1.55;max-width:46rem;margin:1.6rem 0 0}
.stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));margin:2.2rem 0 0;
border-top:1px solid var(--rule);border-bottom:1px solid var(--rule)}
.stat{--c:#667085;padding:.9rem 0 .5rem;border-top:3px solid var(--c)}.stats{gap:0 1.2rem}
.stat.fall{--c:#C62F2F}.stat.time{--c:#1F5AA6}.stat.trust{--c:#C27803}
.stat .v{font-size:2.1rem;font-weight:600;line-height:1.1;font-variant-numeric:tabular-nums;color:var(--c)}
.stat .l{font-size:.9rem;color:var(--ink-3);margin-top:.2rem}
.hero-chart{margin:2.2rem 0 0}
.hero-chart svg{width:100%;height:auto;display:block}
.cap{font-size:.86rem;color:var(--ink-3);max-width:50rem;margin:.4rem 0 0}
.actions{display:flex;flex-wrap:wrap;gap:12px;margin:2.2rem 0 0}
.btn{display:inline-block;padding:.7rem 1.15rem;border-radius:6px;border:1px solid var(--rule);
color:var(--ink);font-weight:500}.btn:hover{text-decoration:none;border-color:var(--ink-3)}
.btn.primary{background:var(--blue);border-color:var(--blue);color:#fff}
.btn.primary:hover{background:#174A8C}
.findings{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:36px;margin:3.6rem 0 0;
padding:2.2rem 0 0;border-top:1px solid var(--rule)}
.findings h3{font-size:1.05rem;margin:0 0 .4rem;line-height:1.35}
.findings p{margin:0;color:var(--ink-2);font-size:.97rem}
section{padding:3rem 0 0}
section h2{font-size:1.6rem;line-height:1.25;letter-spacing:-.01em;margin:0 0 .5rem}
section .sub{color:var(--ink-2);max-width:48rem;margin:0 0 1rem}
h3.chart{font-size:1.05rem;margin:2rem 0 .2rem}
.note{border-left:3px solid var(--blue);background:var(--panel);padding:.9rem 1.15rem;
border-radius:0 6px 6px 0;max-width:52rem;margin:.6rem 0 0}
.two{display:grid;grid-template-columns:1fr 3fr;gap:28px;align-items:start}
.big{font-size:3rem;font-weight:600;line-height:1;margin:.6rem 0 .6rem}
table.wf{border-collapse:collapse;width:100%;max-width:34rem;margin:.6rem 0 0;
font-variant-numeric:tabular-nums}
table.wf td{border-bottom:1px solid var(--rule);padding:.45rem .2rem}
table.wf td:last-child{text-align:right;font-weight:500}
table.wf tr:last-child td{font-weight:600;border-bottom:2px solid var(--ink)}
ul.lim{padding-left:1.1rem;max-width:52rem;color:var(--ink-2)}ul.lim li{margin:.25rem 0}
footer{margin:4rem 0 0;border-top:1px solid var(--rule);padding:1.2rem 0 2.4rem;font-size:.84rem;
color:var(--ink-3)}footer a{color:var(--ink-2)}
@media (max-width:760px){
h1{font-size:2.2rem;margin-top:2rem}.stats{grid-template-columns:repeat(2,minmax(0,1fr))}
.stat{margin-bottom:.6rem}
.findings{grid-template-columns:1fr;gap:24px}.two{grid-template-columns:1fr}
header.top nav a{margin-left:14px;font-size:.9rem}header.top .brand{display:none}
.hero-chart svg text.t{font-size:28px}.hero-chart svg text.m{font-size:34px}}
@media (prefers-reduced-motion:no-preference){.hero-chart path.fade{stroke-dasharray:1400;
stroke-dashoffset:1400;animation:draw 1.6s ease-out .2s forwards}}
@keyframes draw{to{stroke-dashoffset:0}}
"""


def _import_app_lib(cfg: Config):
    sys.path.insert(0, str(cfg.root / "app"))
    from lib import charts, logic, text  # noqa: PLC0415

    return charts, logic, text


def _md(s: str) -> str:
    """Tiny markdown subset: **bold**, *italic* and `code`."""
    s = html.escape(s)
    s = re.sub(r"!!(.+?)!!", r'<b class="bad">\1</b>', s)
    s = re.sub(r"\+\+(.+?)\+\+", r'<b class="good">\1</b>', s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"\*(.+?)\*", r"<i>\1</i>", s)
    return re.sub(r"`(.+?)`", r"<code>\1</code>", s)


def fade_svg(curve: pd.DataFrame, fmt) -> str:
    """Hand-built SVG of the mean fade with its CI band and three labelled milestones."""
    w, h, left, right, top, bottom = 960, 340, 56, 70, 18, 46
    y_min, y_max = -0.45, 0.0
    k_max = 36

    def x(k: float) -> float:
        return left + (w - left - right) * k / k_max

    def y(v: float) -> float:
        return top + (h - top - bottom) * (y_max - v) / (y_max - y_min)

    c = curve.sort_values("k")
    line = " ".join(f"{'M' if i == 0 else 'L'}{x(k):.1f},{y(m):.1f}"
                    for i, (k, m) in enumerate(zip(c["k"], c["mean"], strict=True)))
    upper = [f"{x(k):.1f},{y(v):.1f}" for k, v in zip(c["k"], c["ci_high"], strict=True)]
    lower = [f"{x(k):.1f},{y(v):.1f}" for k, v in zip(c["k"], c["ci_low"], strict=True)]
    band = "M" + " L".join(upper + lower[::-1]) + " Z"
    grid = ""
    for v in (0.0, -0.1, -0.2, -0.3, -0.4):
        stroke = "#1B2430" if v == 0 else "#E9EDF2"
        grid += (f'<line x1="{left}" x2="{w - right}" y1="{y(v):.1f}" y2="{y(v):.1f}" '
                 f'stroke="{stroke}" stroke-width="1" opacity="{0.6 if v == 0 else 1}"/>'
                 f'<text class="t" x="{left - 10}" y="{y(v) + 4:.1f}" text-anchor="end" font-size="13" '
                 f'fill="#667085">{fmt(v, ".1f", minus=True) if v else "0"}</text>')
    ticks = "".join(f'<text class="t" x="{x(k):.1f}" y="{h - bottom + 22}" text-anchor="middle" '
                    f'font-size="13" fill="#667085">{k}</text>' for k in (0, 6, 12, 18, 24, 30, 36))
    marks = ""
    for k in (12, 24, 36):
        v = float(c.loc[c["k"] == k, "mean"].iloc[0])
        marks += (f'<circle cx="{x(k):.1f}" cy="{y(v):.1f}" r="5" fill="#1F5AA6" stroke="#fff" '
                  f'stroke-width="2"/><text class="m" x="{x(k):.1f}" y="{y(v) + 30:.1f}" text-anchor="middle"'
                  f' font-size="15" font-weight="600" fill="#1B2430">'
                  f'{fmt(v, "+.2f", minus=True)}</text>')
    axis = (f'<text class="t" x="{(left + w - right) / 2:.0f}" y="{h - 4}" text-anchor="middle" '
            f'font-size="13" fill="#667085">Months since a game entered the ranking</text>')
    return (f'<svg viewBox="0 0 {w} {h}" role="img" aria-labelledby="fade-t fade-d" '
            f'font-family="IBM Plex Sans, Segoe UI, Arial, sans-serif">'
            f'<title id="fade-t">Mean change in a new game\'s displayed rating</title>'
            f'<desc id="fade-d">The average rating falls steadily over 36 months after launch: '
            f'{fmt(float(c.loc[c["k"] == 12, "mean"].iloc[0]), "+.2f")} by month 12, '
            f'{fmt(float(c.loc[c["k"] == 36, "mean"].iloc[0]), "+.2f")} by month 36.</desc>'
            f'{grid}{ticks}{axis}<path d="{band}" fill="rgba(33,103,176,0.13)"/>'
            f'<path class="fade" d="{line}" fill="none" stroke="#1F5AA6" stroke-width="3" '
            f'stroke-linejoin="round" stroke-linecap="round"/>{marks}</svg>')


def _page(title: str, meta: str, body: str, pub: dict) -> str:
    repo = f"https://github.com/{pub['github_repo']}" if pub.get("github_repo") else ""
    nav = []
    if pub.get("dashboard_url"):
        nav.append(f'<a href="{html.escape(pub["dashboard_url"])}">Interactive app</a>')
    if repo:
        nav += [f'<a href="{repo}/blob/main/reports/writeup.md">Write-up</a>',
                f'<a href="{repo}">Code</a>']
    header = (f'<header class="top"><div class="wrap"><a class="brand" href="index.html">Does the '
              f'hype fade?</a><nav>{"".join(nav)}</nav></div></header>')
    author = html.escape(pub.get("author") or "")
    foot = ('<footer><div class="wrap">Data: daily BoardGameGeek ranking snapshots from '
            '<a href="https://github.com/beefsack/bgg-ranking-historicals">bgg-ranking-historicals'
            '</a>. Data © BoardGameGeek; this project is not affiliated with BoardGameGeek. '
            'Metadata: “Board Game Database from BoardGameGeek” (threnjen, Kaggle, CC BY-SA 3.0).'
            + (f' Analysis and code by {author}' + (f' (<a href="{repo}">GitHub</a>)' if repo
                                                   else "") + "." if author else "")
            + '</div></footer>')
    return (f'<!DOCTYPE html><html lang="en"><head>{meta}<title>{html.escape(title)}</title>'
            f'{FONT_LINK}<style>{CSS}</style></head><body>{header}<main class="wrap">{body}'
            f'</main>{foot}</body></html>')


def run_export_static(cfg: Config) -> Path:
    """Write reports/site/{index,dashboard}.html and return the dashboard path."""
    charts, logic, text = _import_app_lib(cfg)
    from lib.fmt import fmt, pct  # noqa: PLC0415

    data = cfg.root / "app" / "data"
    if not (data / "key_numbers.json").exists():
        raise FileNotFoundError("app/data is missing; run `bgg dashboard-data` first")
    n = json.loads((data / "key_numbers.json").read_text(encoding="utf-8"))["numbers"]
    acfg = json.loads((data / "app_config.json").read_text(encoding="utf-8"))
    pub = cfg.section("publish")

    def table(name: str) -> pd.DataFrame:
        return pd.read_csv(data / "tables" / f"{name}.csv")

    first_chart = [True]

    def plot(fig) -> str:
        inline = first_chart[0]
        first_chart[0] = False
        return fig.to_html(full_html=False, include_plotlyjs=True if inline else False,
                           config={"displayModeBar": False, "responsive": True})

    curves = table("curve_by_segment")

    def curve(gt: str) -> pd.DataFrame:
        return curves[(curves["group_type"] == gt) & (curves["adjusted"] == 0)]

    tones = ["fall", "time", "fall", "trust"]
    stats = "".join(f'<div class="stat {t}"><div class="v">{html.escape(v)}</div>'
                    f'<div class="l">{html.escape(lab)}</div></div>'
                    for (v, lab), t in zip(text.kpis(n, acfg), tones, strict=True))
    first, last = acfg["speed_months"]
    speed = table("speed_not_size")
    q1, q4 = speed.iloc[0], speed.iloc[-1]
    acc = table("q4_accuracy_by_k")
    a = acc[acc["tolerance"] == acfg["rule_tolerance"]].sort_values("k")
    trust_curve = pd.DataFrame({"k": a["k"], "share": a["share_within"], "n": a["n"]})
    rule_k = logic.trust_month(trust_curve, acfg["rule_share"])
    bars = logic.adjusted_vs_raw(table("q4_adjusted_predictor"), acfg["rule_tolerance"])
    wf = table("sample_waterfall").sort_values("step_no")
    qc = table("qc_results")["status"].value_counts()
    qc_total = int(qc.get("PASS", 0) + qc.get("WARN", 0) + qc.get("FAIL", 0))
    start, end = acfg["main_entry_start"][:4], acfg["main_entry_end"][:4]

    pages_url = (pub.get("pages_url") or "").rstrip("/")
    image = f"{pages_url}/social_card.png" if pages_url else "social_card.png"
    desc = (f"The typical new board game on BoardGameGeek loses "
            f"{fmt(abs(n['change_36']['value']), '.2f')} rating points in three years, "
            f"{pct(n['share_of_decline_by_12']['value'])} of it in year one. A data analysis of "
            "how launch ratings fade.")

    def meta(url: str) -> str:
        return "".join([
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            f'<meta name="description" content="{html.escape(desc, quote=True)}">',
            f'<meta name="author" content="{html.escape(pub.get("author") or "", quote=True)}">',
            '<meta property="og:type" content="website">',
            '<meta property="og:title" content="Does the hype fade? Board-game ratings after '
            'launch">',
            f'<meta property="og:description" content="{html.escape(desc, quote=True)}">',
            f'<meta property="og:image" content="{html.escape(image, quote=True)}">',
            f'<meta property="og:url" content="{html.escape(url, quote=True)}">' if url else "",
            '<meta name="twitter:card" content="summary_large_image">',
            f'<meta name="twitter:image" content="{html.escape(image, quote=True)}">',
            '<meta name="theme-color" content="#FFFFFF">'])

    # ---------------- landing page ----------------
    actions = []
    if pub.get("dashboard_url"):
        actions.append(f'<a class="btn primary" href="{html.escape(pub["dashboard_url"])}">'
                       "Explore the interactive dashboard</a>")
    actions.append('<a class="btn" href="dashboard.html">Static dashboard</a>')
    if pub.get("github_repo"):
        repo = f"https://github.com/{pub['github_repo']}"
        actions += [f'<a class="btn" href="{repo}/blob/main/reports/writeup.md">Read the write-up</a>',
                    f'<a class="btn" href="{repo}">Code on GitHub</a>']
    findings = [
        ("The decline isn't finished at three years",
         f"Ratings added recently still come in {fmt(abs(n['gap_k36']['value']), '.2f')} below "
         "the displayed number at month 36. The running average carries the launch crowd's "
         "enthusiasm for years."),
        ("Hype changes the speed, not the size",
         f"The most-hyped games lose {fmt(abs(q4[f'change_{first}']), '.2f')} points by month "
         f"{first}, quiet ones {fmt(abs(q1[f'change_{first}']), '.2f')}. By month {last} they "
         "end up in nearly the same place."),
        (f"Trust a rating after about {fmt(rule_k, '.0f')} months",
         f"Only {pct(n['q4_within_025_k0']['value'])} of games launch within ±"
         f"{acfg['rule_tolerance']} of their 3-year rating. A simple adjusted launch rating gets "
         f"{pct(n['q4_test_adj_within_k0']['value'])} there on day one."),
    ]
    finding_html = "".join(f"<div><h3>{html.escape(t)}</h3><p>{html.escape(p)}</p></div>"
                           for t, p in findings)
    landing_body = f"""
<h1>Does the hype fade?</h1>
<p class="deck">{html.escape(text.deck(n))}</p>
<p class="lede">{_md(text.headline(n))}</p>
<figure class="hero-chart" style="margin-left:0;margin-right:0">
{fade_svg(curve("none"), fmt)}
<figcaption class="cap">Mean change in the displayed rating of {int(n["n_main_sample"]["value"]):,}
games launched {start}–{end}, measured from the month each entered the ranking. The band is the
95% confidence interval.</figcaption></figure>
<div class="stats">{stats}</div>
<div class="actions">{"".join(actions)}</div>
<div class="findings">{finding_html}</div>
"""
    site = cfg.root / "reports" / "site"
    site.mkdir(parents=True, exist_ok=True)
    index = site / "index.html"
    index.write_text(_page("Does the hype fade? Board-game ratings after launch",
                           meta(pages_url), landing_body, pub), encoding="utf-8")

    # ---------------- full static dashboard ----------------
    rows = "".join(f"<tr><td>{html.escape(lab)}</td><td>{int(v):,}</td></tr>" for lab, v in zip(
        ["All games ever ranked", "Not already ranked when the data starts",
         "With a usable publication year", "New releases", f"Launched {start}–{end}",
         f"Still ranked at month {acfg['final_k']} (analysis sample)"], wf["n_games"],
        strict=True))
    body = f"""
<h1>Does the hype fade?</h1>
<p class="deck">{html.escape(text.deck(n))}</p>
<div class="stats">{stats}</div>

<section id="fade">
<h2>Launch ratings oversell</h2>
<p class="sub">{_md(text.headline(n))}</p>
{plot(charts.fig_overview(curve("none"), "none"))}
<h3 class="chart">Big games fade less than niche ones</h3>
{plot(charts.fig_overview(curve("popularity"), "popularity"))}
<p class="cap">Mean change in the displayed rating since entry; {int(n["n_main_sample"]["value"]):,}
games launched {start}–{end}. The interactive app adds more splits and a site-drift adjustment.</p>
</section>

<section id="gap">
<h2>New raters still rate below the number on the page</h2>
<p class="sub">{_md(text.gap_text(n))}</p>
{plot(charts.fig_gap(table("gap_new_vs_displayed")))}
<p class="cap">The new-rater average is backed out from two running averages three months apart
and kept only when at least 10 ratings were added and its rounding error is at most 0.5 points.</p>
</section>

<section id="hype">
<h2>Hype changes how fast ratings fall, not how far</h2>
{plot(charts.fig_speed(speed, (first, last)))}
<div class="note">{_md(text.hype_takeaway(speed, (first, last)))}</div>
<h3 class="chart">No model finds that hyped games fall further</h3>
{plot(charts.fig_specs(n))}
<p class="cap">{_md(text.specs_caption(n))}</p>
<h3 class="chart">Kickstarter games fall further, even from the same start</h3>
{plot(charts.fig_kickstarter(table("kickstarter_by_band")))}
<p class="cap">{_md(text.kickstarter_caption(n))}</p>
</section>

<section id="trust">
<h2>A new game's rating settles after about a year</h2>
<div class="two"><div><div class="big">Month {fmt(rule_k, '.0f')}</div>
<p class="cap">First month when {fmt(100 * acfg["rule_share"], '.0f')}% of games are within
±{acfg["rule_tolerance"]} of their 3-year rating (95% CI: months
{fmt(n["q4_rule_month"]["ci_low"], '.0f')}–{fmt(n["q4_rule_month"]["ci_high"], '.0f')}).</p></div>
<div>{plot(charts.fig_trust(trust_curve, acfg["rule_tolerance"], acfg["rule_share"], rule_k))}</div>
</div>
<h3 class="chart">An adjusted launch rating gets there much sooner</h3>
{plot(charts.fig_adjusted(bars, acfg["rule_tolerance"]))}
<p class="cap">{_md(text.adjusted_caption(n, acfg))}</p>
</section>

<section id="method">
<h2>Method and data</h2>
<p class="sub">One monthly snapshot of BoardGameGeek's ranked list from October 2016 to
{acfg["end_month"][:7]}. Truncated snapshots are replaced, duplicates removed and junk metadata
excluded; {int(qc.get("PASS", 0))} of {qc_total} automated quality checks pass. Models: a game
fixed-effects event study, robust cross-sectional regressions, game-level bootstrap intervals, an
eight-variant robustness grid and an out-of-sample predictive check.</p>
<table class="wf">{rows}</table>
<h3 class="chart">Limitations</h3>
<ul class="lim"><li>A game enters the ranking only at 30 ratings, so its first ratings are folded
into month 0: the analysis measures change after entry.</li><li>Observational data: patterns, not
causal effects. Rater growth also reflects print runs, distribution and price.</li><li>Regression
to the mean and self-selection of the launch audience can't be fully separated.</li><li>The
new-rater average is approximate and over-represents fast-growing games.</li><li>One enthusiast
platform; monthly snapshots.</li></ul>
</section>
"""
    out = site / "dashboard.html"
    out.write_text(_page("Does the hype fade? Static dashboard",
                         meta(f"{pages_url}/dashboard.html" if pages_url else ""), body, pub),
                   encoding="utf-8")
    card = cfg.root / "reports" / "figures" / "social_card.png"
    if card.exists():  # next to index.html, so the og:image link works once hosted
        (site / "social_card.png").write_bytes(card.read_bytes())
    (site / ".nojekyll").write_text("", encoding="utf-8")
    log.info("wrote %s (%.1f MB) and %s (%.0f KB)", out.name, out.stat().st_size / 1e6,
             index.name, index.stat().st_size / 1e3)
    if re.search(r"<script[^>]+src=", out.read_text(encoding="utf-8")):
        raise RuntimeError("static dashboard references an external script; it must work offline")
    if index.stat().st_size > 1_000_000:
        raise RuntimeError("landing page too large for link-preview scrapers")
    return out
