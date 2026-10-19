"""Figure functions: each takes tidy DataFrames and returns a matplotlib Figure.

Titles are added by the caller with :func:`add_titles` (action title + descriptive subtitle).
"""

from __future__ import annotations

import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.figure import Figure

from bgg.fmt import fmt
from bgg.style import INK, INK_3, PALETTE, SEQ4, ramp

log = logging.getLogger(__name__)

TITLE_FONT, SUBTITLE_FONT = 13, 9.5


def add_titles(fig: Figure, title: str, subtitle: str = "") -> Figure:
    """Left-aligned action title with a grey descriptive subtitle above the panels.

    Spacing is set in inches so every figure gets the same header height, with extra room when
    the panels carry their own small titles.
    """
    h = fig.get_figheight()
    panel_titles = any(ax.get_title() for ax in fig.axes)
    fig.subplots_adjust(top=1 - (0.95 + (0.25 if panel_titles else 0.0)) / h)
    fig.text(0.01, 1 - 0.10 / h, title, ha="left", va="top", fontsize=TITLE_FONT,
             fontweight="bold", color=INK)
    if subtitle:
        fig.text(0.01, 1 - 0.50 / h, subtitle, ha="left", va="top", fontsize=SUBTITLE_FONT,
                 color=INK_3)
    return fig


def save_figure(fig: Figure, name: str, out_dir: Path) -> None:
    """Write ``name`` as 200-dpi PNG and SVG into ``out_dir``."""
    out_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_dir / f"{name}.png", dpi=200)
    fig.savefig(out_dir / f"{name}.svg")
    plt.close(fig)
    log.info("wrote figure %s", name)


def _band(ax, df: pd.DataFrame, x: str, color: str, y: str = "mean") -> None:
    ax.fill_between(df[x], df["ci_low"], df["ci_high"], color=color, alpha=0.14, lw=0)
    ax.plot(df[x], df[y], color=color, lw=2.2)


def _baseline(ax, vertical: bool = False) -> None:
    (ax.axvline if vertical else ax.axhline)(0, color=INK, lw=0.9, alpha=0.6, zorder=1)


def _months_axis(ax, k_max: int = 36) -> None:
    ax.set_xticks(range(0, k_max + 1, 6))
    ax.set_xlim(-0.5, k_max + 0.5)
    ax.set_xlabel("Months since entering the ranking")


def _end_labels(ax, items: list[tuple[str, float, float, str]], min_gap: float) -> None:
    """Label lines at their right end, nudged apart so they never overlap; text stays in ink."""
    items = sorted(items, key=lambda t: t[2], reverse=True)
    ys = [it[2] for it in items]
    for i in range(1, len(ys)):
        ys[i] = min(ys[i], ys[i - 1] - min_gap)
    for (label, x, _, color), y in zip(items, ys, strict=True):
        ax.plot([x], [y], "o", ms=5, color=color, clip_on=False, zorder=4)
        ax.annotate(label, (x, y), xytext=(7, 0), textcoords="offset points", va="center",
                    fontsize=9, color="#667085", annotation_clip=False)


def _milestones(ax, curve: pd.DataFrame, color: str, ks=(12, 24, 36), size: float = 9.5) -> None:
    for k in ks:
        r = curve[curve["k"] == k].iloc[0]
        ax.plot([k], [r["mean"]], "o", ms=7, color=color, mec="white", mew=1.8, zorder=4)
        ax.annotate(fmt(r["mean"], "+.2f", minus=True), (k, r["mean"]), textcoords="offset points",
                    xytext=(0, -16), ha="center", fontsize=size, fontweight="bold", color=INK)


def fig01_rating_change(curve: pd.DataFrame, share: dict[str, float]) -> Figure:
    """Mean change in displayed average by age, with the share of decline reached in year 1."""
    fig, ax = plt.subplots(figsize=(9, 5.0))
    _band(ax, curve, "k", PALETTE["blue"])
    _baseline(ax)
    _milestones(ax, curve, PALETTE["blue"])
    ax.text(0.99, 0.93,
            f"{fmt(100 * share['value'], '.0f')}% of the 3-year decline happens in year one\n"
            f"95% CI {fmt(100 * share['ci_low'], '.0f')}–{fmt(100 * share['ci_high'], '.0f')}%",
            transform=ax.transAxes, ha="right", va="top", fontsize=9, color=INK_3)
    _months_axis(ax)
    ax.set_ylabel("Change in displayed rating")
    return fig


def fig02_gap(gap: pd.DataFrame) -> Figure:
    """New raters' average minus the displayed average, by month (usable rows only)."""
    fig, ax = plt.subplots(figsize=(9, 5.0))
    g = gap.sort_values("k")
    _band(ax, g, "k", PALETTE["red"])
    _baseline(ax)
    ax.text(36, 0.008, "Displayed average", ha="right", va="bottom", fontsize=9, color=INK_3)
    for k in (3, 36):
        _milestones(ax, g, PALETTE["red"], ks=(k,))
    _months_axis(ax)
    ax.set_xlim(1.5, 36.8)
    ax.set_ylim(min(-0.3, float(g["ci_low"].min()) - 0.03), 0.04)
    ax.set_ylabel("New-rater average minus displayed")
    return fig


def fig03_cohorts_control(by_year: pd.DataFrame, control_curve: pd.DataFrame,
                          control: pd.DataFrame, adjusted: dict[str, float]) -> Figure:
    """Left: curves by entry year plus control drift on the same scale. Right: zoomed control."""
    fig, (a, b) = plt.subplots(1, 2, figsize=(12, 5.0), gridspec_kw={"width_ratios": [3, 2]})
    years = sorted(by_year["entry_year"].unique())
    labels = []
    for y, color in zip(years, ramp(len(years)), strict=True):
        d = by_year[by_year["entry_year"] == y].sort_values("k")
        a.plot(d["k"], d["mean"], color=color, lw=1.6)
        labels.append((str(y), float(d["k"].iloc[-1]), float(d["mean"].iloc[-1]), color))
    cc = control_curve.sort_values("k")
    a.plot(cc["k"], cc["mean"], color=PALETTE["grey"], ls="--", lw=1.8)
    a.annotate("Established games, same months", (cc["k"].iloc[-1], cc["mean"].iloc[-1]),
               xytext=(-4, 8), textcoords="offset points", ha="right", fontsize=9, color=INK_3)
    _baseline(a)
    _end_labels(a, labels, min_gap=0.016)
    _months_axis(a)
    a.set_ylabel("Change in displayed rating")
    a.set_title("New games by launch year")
    b.plot(control["snap_month"], control["rebased"], color=PALETTE["grey"], lw=1.8)
    _baseline(b)
    b.set_ylabel("Mean rating, rebased to Oct 2016")
    b.set_title(f"Zoomed: {int(control['n_games'].iloc[0]):,} established games")
    b.text(0.97, 0.93, f"36-month change {fmt(adjusted['raw'], '+.3f', minus=True)}\n"
           f"site drift {fmt(adjusted['drift'], '+.3f', minus=True)}\n"
           f"adjusted {fmt(adjusted['adjusted'], '+.3f', minus=True)}",
           transform=b.transAxes, fontsize=9, ha="right", va="top", color=INK_3)
    fig.tight_layout(w_pad=3)
    return fig


def fig04_distribution(change36: pd.Series, deciles: pd.DataFrame, share_declining: float,
                       median: float, x_range: tuple[float, float]) -> Figure:
    """Histogram of 36-month changes and mean change by starting-rating decile."""
    fig, (a, b) = plt.subplots(1, 2, figsize=(12, 5.2))
    c = change36.dropna()
    n_out = int(((c < x_range[0]) | (c > x_range[1])).sum())
    a.hist(c, bins=60, range=x_range, color=PALETTE["blue"], alpha=0.85)
    a.axvline(0, color="black", lw=0.8)
    a.axvline(median, color=PALETTE["red"], lw=1.4, ls="--")
    a.text(0.97, 0.95, f"{fmt(100 * share_declining, '.1f')}% decline\nmedian {fmt(median, '+.2f')}",
           transform=a.transAxes, ha="right", va="top")
    a.text(0.97, 0.80, f"{n_out} games outside the range", transform=a.transAxes, ha="right",
           va="top", fontsize=8, color="#555555")
    a.set_xlabel("Change in average rating, entry to month 36")
    a.set_ylabel("Games")
    a.set_title("Change to month 36")
    x = np.arange(len(deciles))
    b.errorbar(x, deciles["mean"], yerr=[deciles["mean"] - deciles["ci_low"],
                                         deciles["ci_high"] - deciles["mean"]],
               fmt="o-", color=PALETTE["blue"], capsize=0)
    b.set_xticks(x, [f"{fmt(v, '.1f')}" for v in deciles["avg_m0_mean"]])
    b.set_xlabel("Average rating at entry (decile mean)")
    b.set_ylabel("Mean change to month 36")
    b.set_title("High starters fall most (partly regression to the mean)")
    return fig


def fig05_examples(traj: pd.DataFrame) -> Figure:
    """Small multiples: displayed average (+ usable new-rater average) for chosen games."""
    games = list(traj.drop_duplicates("game_id")[["game_id", "name", "role"]].itertuples(
        index=False))
    fig, axes = plt.subplots(2, 3, figsize=(12, 6.6), sharex=True)
    for ax, g in zip(axes.ravel(), games, strict=False):
        d = traj[traj["game_id"] == g.game_id].sort_values("k")
        ax.plot(d["k"], d["avg_rating"], color=PALETTE["blue"], lw=1.6, label="Displayed average")
        ok = d.dropna(subset=["new_avg_3_ok"])
        ax.scatter(ok["k"], ok["new_avg_3_ok"], s=12, color=PALETTE["red"],
                   label="New raters (3-month)")
        note = ("\nentered with unusually low early ratings" if g.role == "largest rise" else "")
        ax.set_title(f"{g.name}\n({g.role}){note}", fontsize=9)
    axes[0, 0].legend(fontsize=7)
    for ax in axes[1]:
        ax.set_xlabel("Months since entry")
    fig.tight_layout()
    return fig


def fig06_hype_quartiles(curve: pd.DataFrame) -> Figure:
    """Mean change curves by hype quartile (1 = least hyped), one sequential hue."""
    fig, ax = plt.subplots(figsize=(9, 5.0))
    labels = []
    for q, color in zip(sorted(curve["hype_quartile"].unique()), SEQ4, strict=False):
        d = curve[curve["hype_quartile"] == q].sort_values("k")
        tag = " least hyped" if q == 1 else " most hyped" if q == 4 else ""
        ax.plot(d["k"], d["mean"], color=color, lw=2.0)
        labels.append((f"Q{int(q)}{tag}", float(d["k"].iloc[-1]), float(d["mean"].iloc[-1]),
                       color))
    _baseline(ax)
    _end_labels(ax, labels, min_gap=0.018)
    _months_axis(ax)
    ax.set_ylabel("Change in displayed rating")
    return fig


def fig07_event_study(es: pd.DataFrame) -> Figure:
    """Event-study coefficients with CIs (month 0 is the reference)."""
    fig, ax = plt.subplots(figsize=(9, 5.2))
    _band(ax, es, "k", PALETTE["blue"], y="beta")
    ax.plot(es["k"], es["beta"], "o", ms=3, color=PALETTE["blue"])
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xlabel("Months since entering the ranking")
    ax.set_ylabel("Coefficient vs month 0 (game fixed effects)")
    return fig


def fig08_when_to_trust(acc: pd.DataFrame, rule: dict[str, float], tol: float,
                        share: float) -> Figure:
    """Share of games within +/- tol of their month-36 rating, by age, with the rule marked."""
    d = acc[acc["tolerance"] == tol].sort_values("k")
    fig, ax = plt.subplots(figsize=(9, 5.0))
    ax.plot(d["k"], 100 * d["share_within"], color=PALETTE["blue"], lw=2.4)
    ax.axhline(100 * share, color=PALETTE["grey"], ls=":", lw=1.2)
    ax.text(0, 100 * share + 1.5, f"Target {fmt(100 * share, '.0f')}%", fontsize=9, color=INK_3)
    if not np.isnan(rule["k"]):
        y = float(100 * d.loc[d["k"] == rule["k"], "share_within"].iloc[0])
        ax.plot([rule["k"]], [y], "o", ms=8, color=PALETTE["blue"], mec="white", mew=1.8,
                zorder=4)
        ax.annotate(f"Month {int(rule['k'])}\n95% CI {fmt(rule['ci_low'], '.0f')}–"
                    f"{fmt(rule['ci_high'], '.0f')}", (rule["k"], y), xytext=(18, -34),
                    textcoords="offset points", fontsize=10, color=INK, fontweight="bold",
                    arrowprops=dict(arrowstyle="-", color=INK_3, lw=0.8))
    _months_axis(ax, int(d["k"].max()))
    ax.set_ylabel(f"Games within ±{tol} of their 3-year rating")
    ax.set_ylim(0, 102)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    return fig


def fig09_speed_not_size(speed: pd.DataFrame, months: tuple[int, int]) -> Figure:
    """Dumbbell per hype quartile: mean change at month 6 and month 36 with CIs."""
    first, last = months
    fig, ax = plt.subplots(figsize=(9, 4.4))
    y = np.arange(len(speed))[::-1]
    labels = []
    for yi, (_, r) in zip(y, speed.iterrows(), strict=True):
        a, b = r[f"change_{first}"], r[f"change_{last}"]
        ax.plot([a, b], [yi, yi], color="#D3DAE3", lw=6, zorder=1, solid_capstyle="round")
        for val, lo, hi, color in ((a, r[f"change_{first}_ci_low"], r[f"change_{first}_ci_high"],
                                    SEQ4[0]), (b, r[f"change_{last}_ci_low"],
                                               r[f"change_{last}_ci_high"], SEQ4[3])):
            ax.errorbar([val], [yi], xerr=[[val - lo], [hi - val]], fmt="o", color=color, ms=10,
                        mec="white", mew=1.8, elinewidth=1.4, zorder=3)
        labels.append(f"Q{int(r['hype_quartile'])}" + (" least hyped" if r["hype_quartile"] == 1
                                                      else " most hyped"
                                                      if r["hype_quartile"] == 4 else ""))
    ax.plot([], [], "o", color=SEQ4[0], ms=9, label=f"Month {first}")
    ax.plot([], [], "o", color=SEQ4[3], ms=9, label=f"Month {last}")
    _baseline(ax, vertical=True)
    ax.grid(axis="x", color="#E9EDF2")
    ax.grid(axis="y", visible=False)
    ax.set_yticks(y, labels)
    ax.set_xlabel("Mean change in displayed rating since entry")
    ax.set_ylim(-0.6, len(speed) - 0.2)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, borderaxespad=0.2)
    return fig


def fig10_kickstarter(bands: pd.DataFrame, raw: dict[str, float]) -> Figure:
    """Change to month 36 by starting-rating band, Kickstarted vs not, with CIs."""
    fig, ax = plt.subplots(figsize=(9, 5.0))
    labels = []
    for flag, color, label, off in ((0, PALETTE["blue"], "Not Kickstarted", -0.025),
                                    (1, PALETTE["ks"], "Kickstarted", 0.025)):
        d = bands[bands["kickstarted"] == flag].sort_values("band_mid")
        ax.errorbar(d["band_mid"] + off, d["mean"], yerr=[d["mean"] - d["ci_low"],
                                                           d["ci_high"] - d["mean"]],
                    fmt="o-", color=color, ms=7, mec="white", mew=1.5, lw=2, elinewidth=1.2)
        labels.append((label, float(d["band_mid"].iloc[-1] + off), float(d["mean"].iloc[-1]),
                       color))
    _baseline(ax)
    _end_labels(ax, labels, min_gap=0.06)
    ax.text(0.01, 0.04, f"Raw means: Kickstarted {fmt(raw['ks'], '+.2f', minus=True)}, other "
            f"{fmt(raw['other'], '+.2f', minus=True)} (Kickstarted games also start higher)",
            transform=ax.transAxes, fontsize=9, color=INK_3)
    ax.set_xlabel("Average rating at entry")
    ax.set_ylabel("Change to month 36")
    return fig


def social_card(curve: pd.DataFrame, title: str, size_px: tuple[int, int]) -> Figure:
    """Fig 1 variant sized for sharing (exact pixel size; save without bbox_inches)."""
    dpi = 100
    fig, ax = plt.subplots(figsize=(size_px[0] / dpi, size_px[1] / dpi), dpi=dpi)
    _band(ax, curve, "k", PALETTE["blue"])
    _baseline(ax)
    _milestones(ax, curve, PALETTE["blue"], size=13)
    _months_axis(ax)
    ax.xaxis.label.set_fontsize(12)
    ax.tick_params(labelsize=11)
    fig.subplots_adjust(top=0.76, left=0.07, right=0.97, bottom=0.13)
    fig.text(0.05, 0.93, title, ha="left", va="top", fontsize=20, fontweight="bold", color=INK)
    n0 = int(curve.loc[curve["k"] == 0, "n"].iloc[0]) if "n" in curve else 0
    fig.text(0.05, 0.84, f"Mean change in the displayed BoardGameGeek rating of {n0:,} new games",
             ha="left", va="top", fontsize=14, color=INK_3)
    return fig
