"""Narrative sentences shared by the Streamlit app and the static export.

Every number is filled from key_numbers.json or an app/data table, never typed.
"""

from __future__ import annotations

import pandas as pd
from lib.fmt import fmt
from lib.logic import kn


def signed(x: float, digits: int = 2) -> str:
    """Signed number with a real minus sign."""
    return fmt(x, f"+.{digits}f", minus=True)


def headline(n: dict) -> str:
    return (f"**Launch ratings oversell.** On BoardGameGeek the typical new game loses "
            f"**{fmt(abs(kn(n, 'change_36')), '.2f')} points** over three years, most of it in year one, "
            "and new raters still rate it lower at the end. Hype doesn't decide how far a game "
            "falls; it decides how fast the number catches up.")


def gap_text(n: dict) -> str:
    return (f"The displayed rating is a running average, so it still carries the enthusiasm of "
            f"the launch crowd. Looking only at the ratings added recently, new raters score "
            f"games **{fmt(abs(kn(n, 'gap_k3')), '.2f')} below the displayed average at month 3 and "
            f"{fmt(abs(kn(n, 'gap_k36')), '.2f')} below at month 36**. The decline isn't finished.")


def hype_takeaway(speed: pd.DataFrame, months: tuple[int, int]) -> str:
    first, last = months
    q1, q4 = speed.iloc[0], speed.iloc[-1]
    return (
        f"**Takeaway.** Hype changes how fast ratings fall, not how far. By month {first}, the "
        f"most-hyped quarter of games has lost {abs(q4[f'change_{first}']):.2f} points and the "
        f"least-hyped quarter {abs(q1[f'change_{first}']):.2f}. By month {last} they are close "
        f"({abs(q4[f'change_{last}']):.2f} vs {abs(q1[f'change_{last}']):.2f}). A hyped game "
        f"gains a median {fmt(q4['growth_median'], '.0f')}x its launch raters in {first} months, which "
        f"dilutes the early enthusiasts quickly; for a quiet release the launch crowd is still "
        f"{fmt(100 * q1['entry_share_median'], '.0f')}% of raters at month {last}, and new raters rate "
        f"it {abs(q1[f'gap_k{last}']):.2f} below the displayed number. Quiet games haven't "
        "faded less; they haven't finished fading.")


def specs_caption(n: dict) -> str:
    return (f"Spec A (controls for starting rating and size): {signed(kn(n, 'spec_a_hype'), 3)}; "
            f"Spec B (change after month 6): {signed(kn(n, 'spec_b_hype'), 3)}. No spec supports "
            "a bigger fall for more-hyped games. Observational data: patterns, not causal "
            "effects.")


def kickstarter_caption(n: dict) -> str:
    return (f"Kickstarted games start higher ({fmt(kn(n, 'ks_avg_m0'), '.2f')} vs "
            f"{fmt(kn(n, 'nonks_avg_m0'), '.2f')}) and, within the same starting band, fall "
            f"{fmt(abs(kn(n, 'ks_gap_within_bands')), '.2f')} more on average. Descriptive only: the flag "
            "comes from a January 2022 snapshot and covers about "
            f"{fmt(100 * kn(n, 'q3_share_kickstarted'), '.0f')}% of games, so it is probably broader "
            "than \"launched via Kickstarter\".")


def adjusted_caption(n: dict, cfg: dict) -> str:
    tr, te = cfg["train_entry_years"], cfg["test_entry_years"]
    return (f"Trained on games entering {tr[0]}-{tr[1]}, tested on {te[0]}-{te[1]}. At entry the "
            f"adjusted rating is within ±{cfg['rule_tolerance']} of the eventual rating for "
            f"{fmt(100 * kn(n, 'q4_test_adj_within_k0'), '.0f')}% of test games (displayed rating: "
            f"{fmt(100 * kn(n, 'q4_test_raw_within_k0'), '.0f')}%) and cuts the mean error from "
            f"{fmt(kn(n, 'q4_test_raw_mae_k0'), '.2f')} to {fmt(kn(n, 'q4_test_adj_mae_k0'), '.2f')}. It works "
            "mostly by shrinking high launch ratings toward the typical level.")


def trust_footnote() -> str:
    return ("Agreement at later months is partly mechanical: the running average at month 24 "
            "already contains most of the raters of month 36.")


def kpis(n: dict, cfg: dict) -> list[tuple[str, str, str]]:
    """(label, value, caption) for the four headline tiles."""
    return [
        ("3-year change", signed(kn(n, "change_36")),
         "Average fall in a new game's displayed rating"),
        ("Fall happening in year one", f"{fmt(100 * kn(n, 'share_of_decline_by_12'), '.0f')}%",
         "Share of the 3-year fall reached by month 12"),
        ("Games that decline", f"{fmt(100 * kn(n, 'share_declining'), '.0f')}%",
         "End lower than they started (month 36)"),
        ("Trust point", f"Month {fmt(kn(n, 'q4_rule_month'), '.0f')}",
         f"{fmt(100 * cfg['rule_share'], '.0f')}% of games are within ±{cfg['rule_tolerance']} of their "
         "3-year rating"),
    ]
