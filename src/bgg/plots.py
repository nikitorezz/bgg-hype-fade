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

from bgg.style import CYCLE, PALETTE, SEQ4

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
             fontweight="bold")
    if subtitle:
        fig.text(0.01, 1 - 0.50 / h, subtitle, ha="left", va="top", fontsize=SUBTITLE_FONT,
                 color="#555555")
    return fig


def save_figure(fig: Figure, name: str, out_dir: Path) -> None:
    """Write ``name`` as 200-dpi PNG and SVG into ``out_dir``."""
    out_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_dir / f"{name}.png", dpi=200)
    fig.savefig(out_dir / f"{name}.svg")
    plt.close(fig)
    log.info("wrote figure %s", name)


def _band(ax, df: pd.DataFrame, x: str, color: str, y: str = "mean") -> None:
    ax.plot(df[x], df[y], color=color, lw=1.8)
    ax.fill_between(df[x], df["ci_low"], df["ci_high"], color=color, alpha=0.2, lw=0)


def fig01_rating_change(curve: pd.DataFrame, share: dict[str, float]) -> Figure:
    """Mean change in displayed average by age, with the share of decline reached in year 1."""
    fig, ax = plt.subplots(figsize=(9, 5.2))
    _band(ax, curve, "k", PALETTE["blue"])
    ax.axhline(0, color="black", lw=0.8)
    for k in (12, 24, 36):
        r = curve[curve["k"] == k].iloc[0]
        ax.plot([k], [r["mean"]], "o", color=PALETTE["blue"])
        ax.annotate(f"{r['mean']:+.3f}", (k, r["mean"]), textcoords="offset points",
                    xytext=(0, -14), ha="center", fontsize=9)
    ax.text(0.98, 0.95,
            f"{100 * share['value']:.0f}% of the 3-year decline happens in year 1\n"
            f"(95% CI {100 * share['ci_low']:.0f}-{100 * share['ci_high']:.0f}%)",
            transform=ax.transAxes, ha="right", va="top", fontsize=9)
    ax.set_xlabel("Months since entering the ranking")
    ax.set_ylabel("Change in displayed average rating")
    return fig


def fig02_gap(gap: pd.DataFrame) -> Figure:
    """New raters' average minus the displayed average, plus the share of usable rows."""
    fig, (ax, ax2) = plt.subplots(2, 1, figsize=(9, 6.4), sharex=True,
                                  gridspec_kw={"height_ratios": [3, 1.2]})
    _band(ax, gap, "k", PALETTE["red"])
    ax.axhline(0, color="black", lw=0.8)
    ax.set_ylabel("New-rater average minus\ndisplayed average")
    ax2.plot(gap["k"], 100 * gap["share_usable"], color=PALETTE["grey"], lw=1.6)
    ax2.set_ylabel("% of game-months\nwith a usable estimate")
    ax2.set_xlabel("Months since entering the ranking")
    return fig


def fig03_cohorts_control(by_year: pd.DataFrame, control_curve: pd.DataFrame,
                          control: pd.DataFrame, adjusted: dict[str, float]) -> Figure:
    """Left: curves by entry year plus control drift on the same scale. Right: zoomed control."""
    fig, (a, b) = plt.subplots(1, 2, figsize=(12, 5.2))
    for i, y in enumerate(sorted(by_year["entry_year"].unique())):
        d = by_year[by_year["entry_year"] == y]
        a.plot(d["k"], d["mean"], color=CYCLE[i % len(CYCLE)], lw=1.5, label=str(y))
    a.plot(control_curve["k"], control_curve["mean"], color="#555555", ls="--", lw=2,
           label="Mature control group")
    a.axhline(0, color="black", lw=0.8)
    a.set_xlabel("Months since entering the ranking")
    a.set_ylabel("Change in displayed average rating")
    a.set_title("New games by launch year, vs the control group")
    a.legend(ncol=2, loc="lower left")
    b.plot(control["snap_month"], control["rebased"], color=PALETTE["grey"], lw=1.6)
    b.axhline(0, color="black", lw=0.8)
    b.set_ylabel("Mean average, rebased to 2016-10")
    b.set_title(f"Zoomed scale: drift of {int(control['n_games'].iloc[0]):,} mature games")
    b.text(0.97, 0.95, f"Raw 36-month change {adjusted['raw']:+.3f}\ncontrol drift "
           f"{adjusted['drift']:+.3f}\nadjusted {adjusted['adjusted']:+.3f}",
           transform=b.transAxes, fontsize=9, ha="right", va="top")
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
    a.text(0.97, 0.95, f"{100 * share_declining:.1f}% decline\nmedian {median:+.2f}",
           transform=a.transAxes, ha="right", va="top")
    a.text(0.97, 0.80, f"{n_out} games outside the range", transform=a.transAxes, ha="right",
           va="top", fontsize=8, color="#555555")
    a.set_xlabel("Change in average rating, entry to month 36")
    a.set_ylabel("Games")
    a.set_title("Change to month 36")
    x = np.arange(len(deciles))
    b.errorbar(x, deciles["mean"], yerr=[deciles["mean"] - deciles["ci_low"],
                                         deciles["ci_high"] - deciles["mean"]],
               fmt="o-", color=PALETTE["blue"], capsize=3)
    b.set_xticks(x, [f"{v:.1f}" for v in deciles["avg_m0_mean"]])
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
    fig, ax = plt.subplots(figsize=(9, 5.2))
    for q, color in zip(sorted(curve["hype_quartile"].unique()), SEQ4, strict=False):
        d = curve[curve["hype_quartile"] == q]
        tag = " (least hyped)" if q == 1 else " (most hyped)" if q == 4 else ""
        ax.plot(d["k"], d["mean"], color=color, lw=2.0, label=f"Q{int(q)}{tag}")
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xlabel("Months since entering the ranking")
    ax.set_ylabel("Change in displayed average rating")
    ax.legend()
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
    d = acc[acc["tolerance"] == tol]
    fig, ax = plt.subplots(figsize=(9, 5.2))
    ax.plot(d["k"], 100 * d["share_within"], color=PALETTE["blue"], lw=1.8)
    ax.axhline(100 * share, color=PALETTE["grey"], ls="--", lw=1)
    if not np.isnan(rule["k"]):
        ax.axvline(rule["k"], color=PALETTE["red"], lw=1.2)
        ax.text(rule["k"] + 0.4, 5, f"month {int(rule['k'])}\n(95% CI {rule['ci_low']:.0f}-"
                f"{rule['ci_high']:.0f})", color=PALETTE["red"], fontsize=9)
    ax.set_xlabel("Months since entering the ranking")
    ax.set_ylabel(f"% of games within ±{tol} of their month-36 rating")
    ax.set_ylim(0, 100)
    return fig


def fig09_speed_not_size(speed: pd.DataFrame, months: tuple[int, int]) -> Figure:
    """Dumbbell per hype quartile: mean change at month 6 and month 36 with CIs."""
    first, last = months
    fig, ax = plt.subplots(figsize=(9, 4.8))
    y = np.arange(len(speed))[::-1]
    labels = []
    for yi, (_, r) in zip(y, speed.iterrows(), strict=True):
        a, b = r[f"change_{first}"], r[f"change_{last}"]
        ax.plot([a, b], [yi, yi], color="#BBBBBB", lw=3, zorder=1)
        for val, lo, hi, color in ((a, r[f"change_{first}_ci_low"], r[f"change_{first}_ci_high"],
                                    SEQ4[0]), (b, r[f"change_{last}_ci_low"],
                                               r[f"change_{last}_ci_high"], SEQ4[3])):
            ax.errorbar([val], [yi], xerr=[[val - lo], [hi - val]], fmt="o", color=color, ms=9,
                        capsize=3, zorder=3)
        labels.append(f"Q{int(r['hype_quartile'])}" + (" (least hyped)" if r["hype_quartile"] == 1
                                                      else " (most hyped)"
                                                      if r["hype_quartile"] == 4 else ""))
    ax.plot([], [], "o", color=SEQ4[0], ms=9, label=f"month {first}")
    ax.plot([], [], "o", color=SEQ4[3], ms=9, label=f"month {last}")
    ax.axvline(0, color="black", lw=0.8)
    ax.set_yticks(y, labels)
    ax.set_xlabel("Mean change in displayed average since entry")
    ax.legend(loc="upper left")
    return fig


def fig10_kickstarter(bands: pd.DataFrame, raw: dict[str, float]) -> Figure:
    """Change to month 36 by starting-rating band, Kickstarted vs not, with CIs."""
    fig, ax = plt.subplots(figsize=(9, 5.2))
    for flag, color, label, off in ((0, PALETTE["blue"], "Not Kickstarted", -0.03),
                                    (1, PALETTE["red"], "Kickstarted", 0.03)):
        d = bands[bands["kickstarted"] == flag]
        ax.errorbar(d["band_mid"] + off, d["mean"], yerr=[d["mean"] - d["ci_low"],
                                                           d["ci_high"] - d["mean"]],
                    fmt="o-", color=color, capsize=3, label=label)
    ax.axhline(0, color="black", lw=0.8)
    ax.text(0.02, 0.05, f"Raw means: Kickstarted {raw['ks']:+.2f}, other {raw['other']:+.2f}\n"
            "(Kickstarted games also start higher)", transform=ax.transAxes, fontsize=9)
    ax.set_xlabel("Average rating at entry (0.5-wide bands)")
    ax.set_ylabel("Mean change to month 36")
    ax.legend()
    return fig


def social_card(curve: pd.DataFrame, title: str, size_px: tuple[int, int]) -> Figure:
    """Fig 1 variant sized for sharing (exact pixel size; save without bbox_inches)."""
    dpi = 100
    fig, ax = plt.subplots(figsize=(size_px[0] / dpi, size_px[1] / dpi), dpi=dpi)
    _band(ax, curve, "k", PALETTE["blue"])
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xlabel("Months since entering the ranking", fontsize=12)
    ax.set_ylabel("Change in displayed rating", fontsize=12)
    fig.subplots_adjust(top=0.82, left=0.09, right=0.97, bottom=0.14)
    fig.text(0.03, 0.95, title, ha="left", va="top", fontsize=19, fontweight="bold", wrap=True)
    return fig
