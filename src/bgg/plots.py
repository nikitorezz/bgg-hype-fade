"""Figure functions: each takes tidy DataFrames and returns a matplotlib Figure."""

from __future__ import annotations

import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.figure import Figure

from bgg.style import CYCLE, PALETTE, SEQ4

log = logging.getLogger(__name__)


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
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
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
    ax.set_title("The fade: mean change in displayed rating since entry")
    return fig


def fig02_gap(gap: pd.DataFrame) -> Figure:
    """New raters' average minus the displayed average, plus the share of usable rows."""
    fig, (ax, ax2) = plt.subplots(2, 1, figsize=(7.5, 5.6), sharex=True,
                                  gridspec_kw={"height_ratios": [3, 1.2]})
    _band(ax, gap, "k", PALETTE["red"])
    ax.axhline(0, color="black", lw=0.8)
    ax.set_ylabel("New-rater average minus displayed average")
    ax.set_title("What new raters say vs what is displayed")
    ax2.plot(gap["k"], 100 * gap["share_usable"], color=PALETTE["grey"], lw=1.6)
    ax2.set_ylabel("% rows usable")
    ax2.set_xlabel("Months since entering the ranking")
    return fig


def fig03_cohorts_control(by_year: pd.DataFrame, control: pd.DataFrame,
                          adjusted: dict[str, float]) -> Figure:
    """Left: curves by entry year. Right: mature-control drift by calendar month."""
    fig, (a, b) = plt.subplots(1, 2, figsize=(12, 4.6))
    for i, y in enumerate(sorted(by_year["entry_year"].unique())):
        d = by_year[by_year["entry_year"] == y]
        a.plot(d["k"], d["mean"], color=CYCLE[i % len(CYCLE)], lw=1.5, label=str(y))
    a.axhline(0, color="black", lw=0.8)
    a.set_xlabel("Months since entering the ranking")
    a.set_ylabel("Change in displayed average rating")
    a.set_title("By launch year")
    a.legend(ncol=2)
    b.plot(control["snap_month"], control["rebased"], color=PALETTE["grey"], lw=1.6)
    b.axhline(0, color="black", lw=0.8)
    b.set_ylabel("Mean average, rebased to 2016-10")
    b.set_title(f"Background drift ({int(control['n_games'].iloc[0]):,} mature games)")
    b.text(0.03, 0.05, f"Raw 36-month change {adjusted['raw']:+.3f}; control drift "
           f"{adjusted['drift']:+.3f};\nadjusted {adjusted['adjusted']:+.3f}",
           transform=b.transAxes, fontsize=9)
    return fig


def fig04_distribution(change36: pd.Series, deciles: pd.DataFrame, share_declining: float,
                       median: float) -> Figure:
    """Histogram of 36-month changes and mean change by starting-rating decile."""
    fig, (a, b) = plt.subplots(1, 2, figsize=(12, 4.6))
    a.hist(change36.dropna(), bins=60, color=PALETTE["blue"], alpha=0.85)
    a.axvline(0, color="black", lw=0.8)
    a.axvline(median, color=PALETTE["red"], lw=1.4, ls="--")
    a.text(0.97, 0.95, f"{100 * share_declining:.1f}% decline\nmedian {median:+.2f}",
           transform=a.transAxes, ha="right", va="top")
    a.set_xlabel("Change in average rating, entry to month 36")
    a.set_ylabel("Games")
    a.set_title("Most games decline")
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
    fig, axes = plt.subplots(2, 3, figsize=(12, 6.2), sharex=True)
    for ax, g in zip(axes.ravel(), games, strict=False):
        d = traj[traj["game_id"] == g.game_id].sort_values("k")
        ax.plot(d["k"], d["avg_rating"], color=PALETTE["blue"], lw=1.6, label="Displayed average")
        ok = d.dropna(subset=["new_avg_3_ok"])
        ax.scatter(ok["k"], ok["new_avg_3_ok"], s=12, color=PALETTE["red"],
                   label="New raters (3-month)")
        ax.set_title(f"{g.name}\n({g.role})", fontsize=9)
    axes[0, 0].legend(fontsize=7)
    for ax in axes[1]:
        ax.set_xlabel("Months since entry")
    fig.suptitle("Example trajectories (chosen by rule, see examples.csv)", fontweight="bold")
    fig.tight_layout()
    return fig


def fig06_hype_quartiles(curve: pd.DataFrame) -> Figure:
    """Mean change curves by hype quartile (1 = least hyped)."""
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    for q, color in zip(sorted(curve["hype_quartile"].unique()), SEQ4, strict=False):
        d = curve[curve["hype_quartile"] == q]
        tag = " (least hyped)" if q == 1 else " (most hyped)" if q == 4 else ""
        ax.plot(d["k"], d["mean"], color=color, lw=1.8, label=f"Q{int(q)}{tag}")
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xlabel("Months since entering the ranking")
    ax.set_ylabel("Change in displayed average rating")
    ax.set_title("Change by hype quartile (growth in raters, months 0-6)")
    ax.legend()
    return fig


def fig07_event_study(es: pd.DataFrame) -> Figure:
    """Event-study coefficients with CIs (month 0 is the reference)."""
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    _band(ax, es, "k", PALETTE["blue"], y="beta")
    ax.plot(es["k"], es["beta"], "o", ms=3, color=PALETTE["blue"])
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xlabel("Months since entering the ranking")
    ax.set_ylabel("Coefficient vs month 0 (game fixed effects)")
    ax.set_title("Event study: average rating by age within game")
    return fig


def fig08_when_to_trust(acc: pd.DataFrame, rule: dict[str, float], tol: float,
                        share: float) -> Figure:
    """Share of games within +/- tol of their month-36 rating, by age, with the rule marked."""
    d = acc[acc["tolerance"] == tol]
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    ax.plot(d["k"], 100 * d["share_within"], color=PALETTE["blue"], lw=1.8)
    ax.axhline(100 * share, color=PALETTE["grey"], ls="--", lw=1)
    if not np.isnan(rule["k"]):
        ax.axvline(rule["k"], color=PALETTE["red"], lw=1.2)
        ax.text(rule["k"] + 0.4, 5, f"month {int(rule['k'])}\n(95% CI {rule['ci_low']:.0f}-"
                f"{rule['ci_high']:.0f})", color=PALETTE["red"], fontsize=9)
    ax.set_xlabel("Months since entering the ranking")
    ax.set_ylabel(f"% of games within ±{tol} of their month-36 rating")
    ax.set_title("When can you trust a new game's rating?")
    ax.set_ylim(0, 100)
    return fig
