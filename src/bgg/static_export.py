"""``bgg export-static``: one self-contained HTML page (Plotly inlined, no lookup, no servers).

Reads only ``app/data`` (aggregate tables + key numbers), so it can be hosted on GitHub Pages
and opened offline. Charts and sentences come from the same ``app/lib`` modules as the app.
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

CSS = """
body{font-family:Arial,Helvetica,sans-serif;color:#222;max-width:1050px;margin:0 auto;padding:16px;
line-height:1.5}h1{margin-bottom:0}h2{margin-top:40px;border-bottom:2px solid #0072B2;
padding-bottom:4px}.sub{color:#777;margin-top:0}.kpis{display:flex;flex-wrap:wrap;gap:16px}
.kpi{flex:1 1 200px;background:#F3F6F9;border-radius:8px;padding:12px 16px}.kpi .v{font-size:2.2em}
.kpi .l{color:#555;font-size:.9em}.kpi .c{color:#777;font-size:.8em}.box{background:#E8F1FB;
padding:12px 16px;border-radius:8px}.cap{color:#666;font-size:.85em}table{border-collapse:collapse;
margin:8px 0}td,th{border-bottom:1px solid #ddd;padding:4px 10px;text-align:right}
th:first-child,td:first-child{text-align:left}footer{margin-top:50px;color:#777;font-size:.8em;
border-top:1px solid #ddd;padding-top:10px}.grid{display:flex;flex-wrap:wrap;gap:16px}
.grid>div{flex:1 1 440px;min-width:300px}
"""


def _import_app_lib(cfg: Config):
    sys.path.insert(0, str(cfg.root / "app"))
    from lib import charts, logic, text  # noqa: PLC0415

    return charts, logic, text


def _md(s: str) -> str:
    """Tiny markdown subset: **bold** and `code`."""
    s = html.escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    return re.sub(r"`(.+?)`", r"<code>\1</code>", s)


def _table_html(df: pd.DataFrame, formats: dict | None = None) -> str:
    """HTML table; ``formats`` maps a column to a callable formatting its values."""
    formats = formats or {}
    head = "".join(f"<th>{html.escape(str(c))}</th>" for c in df.columns)
    rows = []
    for _, r in df.iterrows():
        cells = "".join(f"<td>{formats.get(c, str)(r[c])}</td>" for c in df.columns)
        rows.append(f"<tr>{cells}</tr>")
    return f"<table><tr>{head}</tr>{''.join(rows)}</table>"


def run_export_static(cfg: Config) -> Path:
    """Write reports/site/index.html and return its path."""
    charts, logic, text = _import_app_lib(cfg)
    from lib.fmt import fmt, pct  # noqa: PLC0415
    data = cfg.root / "app" / "data"
    if not (data / "key_numbers.json").exists():
        raise FileNotFoundError("app/data is missing; run `bgg dashboard-data` first")
    n = json.loads((data / "key_numbers.json").read_text(encoding="utf-8"))["numbers"]
    acfg = json.loads((data / "app_config.json").read_text(encoding="utf-8"))

    def table(name: str) -> pd.DataFrame:
        return pd.read_csv(data / "tables" / f"{name}.csv")

    first_chart = [True]

    def plot(fig) -> str:
        inline = first_chart[0]
        first_chart[0] = False
        return fig.to_html(full_html=False, include_plotlyjs=True if inline else False,
                           config={"displayModeBar": False, "responsive": True})

    curves = table("curve_by_segment")

    def curve(gt: str):
        return curves[(curves["group_type"] == gt) & (curves["adjusted"] == 0)]

    first, last = acfg["speed_months"]
    speed = table("speed_not_size")
    acc = table("q4_accuracy_by_k")
    a = acc[acc["tolerance"] == acfg["rule_tolerance"]].sort_values("k")
    trust_curve = pd.DataFrame({"k": a["k"], "share": a["share_within"], "n": a["n"]})
    rule_k = logic.trust_month(trust_curve, acfg["rule_share"])
    bars = logic.adjusted_vs_raw(table("q4_adjusted_predictor"), acfg["rule_tolerance"])
    waterfall = table("sample_waterfall")
    qc = table("qc_results")["status"].value_counts()
    ks_years = acfg["kickstarter_years"]

    kpi_html = "".join(
        f'<div class="kpi"><div class="l">{html.escape(lab)}</div><div class="v">'
        f'{html.escape(val)}</div><div class="c">{html.escape(cap)}</div></div>'
        for lab, val, cap in text.kpis(n, acfg))
    shares = acc[acc["tolerance"].isin(acfg["tolerances"]) & acc["k"].isin([0, 3, 6, 12, 18, 24])]
    share_tbl = shares.pivot(index="k", columns="tolerance", values="share_within").reset_index()
    share_tbl.columns = ["Month"] + [f"within ±{t}" for t in share_tbl.columns[1:]]
    share_tbl["Month"] = share_tbl["Month"].astype(int)
    waterfall = waterfall.assign(
        Games=waterfall["n_games"].map("{:,}".format),
        Removed=waterfall["removed"].map(lambda v: "" if pd.isna(v) else f"{int(v):,}"))

    body = f"""
<h1>Does the Hype Fade?</h1>
<p class="sub">Post-release rating trajectories of board games on BoardGameGeek, 2016-2026</p>
<p>{_md(text.headline(n))}</p>
<div class="kpis">{kpi_html}</div>

<h2>How ratings move after a game enters the ranking</h2>
{plot(charts.fig_overview(curve("none"), "none"))}
<h3>By launch year</h3>
{plot(charts.fig_overview(curve("launch_year"), "launch_year"))}
<h3>By hype quartile</h3>
{plot(charts.fig_overview(curve("hype_quartile"), "hype_quartile"))}
<p class="cap">Main sample: {int(n["n_main_sample"]["value"]):,} new releases entering the ranking
{acfg["main_entry_start"][:7]} to {acfg["main_entry_end"][:7]}, followed for {acfg["final_k"]} months.
Shaded bands are 95% confidence intervals. The interactive version has more comparisons and a
drift-adjustment toggle.</p>

<h2>What new raters say vs what is displayed</h2>
<p>{_md(text.gap_text(n))}</p>
{plot(charts.fig_gap(table("gap_new_vs_displayed")))}
<p class="cap">New avg = (avg_t x n_t - avg_(t-3) x n_(t-3)) / (n_t - n_(t-3)); kept only when at
least 10 ratings were added, the rounding-error bound is at most 0.5 and the value lies in
[1, 10]. Lower panel: share of game-months with a usable estimate.</p>

<h2>Hype: speed, not size</h2>
{plot(charts.fig_speed(speed, (first, last)))}
<p class="box">{_md(text.hype_takeaway(speed, (first, last)))}</p>
<h3>Does hype predict the size of the fall? (H2: negative sign)</h3>
{plot(charts.fig_specs(n))}<p class="cap">{_md(text.specs_caption(n))}</p>
<h3>Kickstarted games fall further, even from the same starting rating
({ks_years[0]}-{ks_years[-1]} entries)</h3>
{plot(charts.fig_kickstarter(table("kickstarter_by_band")))}
<p class="cap">{_md(text.kickstarter_caption(n))}</p>

<h2>When can you trust a new game's rating?</h2>
<p>At the default setting (at least {fmt(100 * acfg["rule_share"], '.0f')}% of games within
±{acfg["rule_tolerance"]} of their {acfg["final_k"]}-month rating) the answer is
<b>month {fmt(rule_k, '.0f')}</b> (bootstrap 95% CI {fmt(n["q4_rule_month"]["ci_low"], '.0f')}-
{fmt(n["q4_rule_month"]["ci_high"], '.0f')}).</p>
{plot(charts.fig_trust(trust_curve, acfg["rule_tolerance"], acfg["rule_share"], rule_k))}
{_table_html(share_tbl, {"Month": lambda v: fmt(v, ".0f"),
                         **{c: (lambda v: pct(v, 1)) for c in share_tbl.columns[1:]}})}
<p class="cap">{_md(text.trust_footnote())}</p>
<h3>A platform could show an adjusted launch rating</h3>
{plot(charts.fig_adjusted(bars, acfg["rule_tolerance"]))}
<p class="cap">{_md(text.adjusted_caption(n, acfg))}</p>

<h2>Method &amp; data</h2>
<p>Data: daily BoardGameGeek ranking snapshots from beefsack/bgg-ranking-historicals (one per
month, to {acfg["end_month"][:7]}). A game fixed-effects event study, robust cross-sectional OLS,
game-level bootstrap intervals, a robustness grid and an out-of-sample predictive check.
Data-quality checks: {int(qc.get("PASS", 0))} pass, {int(qc.get("WARN", 0))} warnings,
{int(qc.get("FAIL", 0))} failures.</p>
{_table_html(waterfall.rename(columns={"step_no": "#", "step": "Step"})
             [["#", "Step", "Games", "Removed"]])}
<p class="cap">Limitations: ratings enter the ranking only at 30 raters, so the first ratings are
folded into month 0; observational data (patterns, not causal effects); regression to the mean and
audience self-selection cannot be fully separated; the new-rater estimate is approximate; one
enthusiast platform; the Kickstarter flag comes from a 2022 snapshot; monthly snapshots only.</p>
<footer>Data: BoardGameGeek ranking snapshots (beefsack/bgg-ranking-historicals). Data ©
BoardGameGeek; this project is not affiliated with BoardGameGeek. Metadata: "Board Game Database
from BoardGameGeek" (threnjen, Kaggle, CC BY-SA 3.0).</footer>
"""
    pages = (cfg.section("publish").get("pages_url") or "").rstrip("/")
    image = f"{pages}/social_card.png" if pages else "social_card.png"
    desc = (f"On BoardGameGeek the typical new board game loses {fmt(abs(n['change_36']['value']), '.2f')} "
            f"rating points in three years, {pct(n['share_of_decline_by_12']['value'])} of it in year "
            "one. An interactive look at how launch ratings fade.")
    meta = "".join([
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f'<meta name="description" content="{html.escape(desc, quote=True)}">',
        '<meta property="og:type" content="website">',
        '<meta property="og:title" content="Does the Hype Fade? Board-game ratings after launch">',
        f'<meta property="og:description" content="{html.escape(desc, quote=True)}">',
        f'<meta property="og:image" content="{html.escape(image, quote=True)}">',
        f'<meta property="og:url" content="{html.escape(pages, quote=True)}">' if pages else "",
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:image" content="{html.escape(image, quote=True)}">'])
    page = (f'<!DOCTYPE html><html lang="en"><head>{meta}<title>Does the Hype Fade?</title>'
            f"<style>{CSS}</style></head><body>{body}</body></html>")
    site = cfg.root / "reports" / "site"
    site.mkdir(parents=True, exist_ok=True)
    out = site / "dashboard.html"           # the full, self-contained page (about 5 MB)
    out.write_text(page, encoding="utf-8")
    pub = cfg.section("publish")
    kpi_cards = "".join(
        f'<div class="kpi"><div class="l">{html.escape(lab)}</div><div class="v">{html.escape(val)}</div>'
        f'<div class="c">{html.escape(cap)}</div></div>' for lab, val, cap in text.kpis(n, acfg))
    links = ['<a class="btn" href="dashboard.html">Open the dashboard</a>']
    if pub.get("dashboard_url"):
        links.append(f'<a href="{html.escape(pub["dashboard_url"])}">Live interactive app</a>')
    if pub.get("github_repo"):
        repo = f"https://github.com/{pub['github_repo']}"
        links += [f'<a href="{repo}/blob/main/reports/writeup.md">Write-up</a>',
                  f'<a href="{repo}">Code</a>']
    landing_body = f"""
<h1>Does the Hype Fade?</h1>
<p class="sub">Post-release rating trajectories of board games on BoardGameGeek, 2016-2026</p>
<p>{_md(text.headline(n))}</p>
<div class="kpis">{kpi_cards}</div>
<p><img src="social_card.png" alt="Mean change in rating by months since entry" style="max-width:100%"></p>
<p class="links">{" · ".join(links)}</p>
<p class="cap">The dashboard page is a single offline-capable file (about 5 MB, Plotly inlined).</p>
<footer>Data: BoardGameGeek ranking snapshots (beefsack/bgg-ranking-historicals). Data © BoardGameGeek;
this project is not affiliated with BoardGameGeek.</footer>"""
    landing_css = CSS + ".btn{background:#0072B2;color:#fff;padding:8px 16px;border-radius:6px;text-decoration:none}.links a{margin-right:6px}"
    landing = (f'<!DOCTYPE html><html lang="en"><head>{meta}<title>Does the Hype Fade?</title>'
               f"<style>{landing_css}</style></head><body>{landing_body}</body></html>")
    index = site / "index.html"             # small page for link previews (LinkedIn caps pages at 3 MB)
    index.write_text(landing, encoding="utf-8")
    card = cfg.root / "reports" / "figures" / "social_card.png"
    if card.exists():  # next to index.html, so the og:image link works once hosted
        (site / "social_card.png").write_bytes(card.read_bytes())
    (site / ".nojekyll").write_text("", encoding="utf-8")
    log.info("wrote %s (%.1f MB) and %s (%.0f KB)", out.name, out.stat().st_size / 1e6, index.name,
             index.stat().st_size / 1e3)
    if re.search(r"<script[^>]+src=", page):
        raise RuntimeError("static page references an external script; it must work offline")
    if index.stat().st_size > 1_000_000:
        raise RuntimeError("landing page too large for link-preview scrapers")
    return out
