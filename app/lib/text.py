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
    return (f"**Launch ratings oversell.** The typical new game on BoardGameGeek loses "
            f"**{fmt(abs(kn(n, 'change_36')), '.2f')} rating points** in its first three years, "
            "most of it in year one, and the newest raters still rate it lower than the number "
            "on the page. Hype doesn't decide how far a game falls; it decides how fast.")


def deck(n: dict) -> str:
    return (f"How board-game ratings change after launch: {int(kn(n, 'n_main_sample')):,} new "
            "releases on BoardGameGeek, each followed for three years, from ten years of daily "
            "ranking snapshots.")


def gap_text(n: dict) -> str:
    return (f"The displayed rating is a running average, so it keeps the launch crowd's "
            f"enthusiasm for years. Ratings added in the last three months come in "
            f"**{fmt(abs(kn(n, 'gap_k3')), '.2f')} below** the displayed number at month 3, and "
            f"still **{fmt(abs(kn(n, 'gap_k36')), '.2f')} below** at month 36. The decline isn't "
            "finished.")


def hype_takeaway(speed: pd.DataFrame, months: tuple[int, int]) -> str:
    first, last = months
    q1, q4 = speed.iloc[0], speed.iloc[-1]

    def a(v: float) -> str:
        return fmt(abs(v), ".2f")

    return (
        f"By month {first} the most-hyped quarter of games has already lost "
        f"{a(q4[f'change_{first}'])} points, the least-hyped only {a(q1[f'change_{first}'])}. "
        f"By month {last} they have nearly converged ({a(q4[f'change_{last}'])} vs "
        f"{a(q1[f'change_{last}'])}). A hyped game typically gains "
        f"{fmt(q4['growth_median'], '.0f')}× its launch raters within {first} months, which "
        "dilutes the launch enthusiasts quickly. For a quiet release the launch crowd is still "
        f"{fmt(100 * q1['entry_share_median'], '.0f')}% of raters at month {last}, and new raters "
        f"score it {a(q1[f'gap_k{last}'])} below the displayed number: it hasn't finished fading.")


def specs_caption(n: dict) -> str:
    return (f"With controls for starting rating and size, the hype effect is "
            f"{signed(kn(n, 'spec_a_hype'), 3)} (slightly *less* fade); measured only after the "
            f"hype window it is {signed(kn(n, 'spec_b_hype'), 3)}. No specification supports a "
            "bigger fall for more-hyped games.")


def kickstarter_caption(n: dict) -> str:
    return (f"Kickstarted games start higher ({fmt(kn(n, 'ks_avg_m0'), '.2f')} vs "
            f"{fmt(kn(n, 'nonks_avg_m0'), '.2f')}) and, from the same starting rating, still fall "
            f"{fmt(abs(kn(n, 'ks_gap_within_bands')), '.2f')} more. Descriptive only: the flag "
            "comes from a 2022 metadata snapshot and is probably broader than \"launched on "
            "Kickstarter\".")


def adjusted_caption(n: dict, cfg: dict) -> str:
    tr, te = cfg["train_entry_years"], cfg["test_entry_years"]
    return (f"A three-variable model trained on {tr[0]}–{tr[1]} launches and tested on "
            f"{te[0]}–{te[1]}. At launch it is within ±{cfg['rule_tolerance']} of the eventual "
            f"rating for {fmt(100 * kn(n, 'q4_test_adj_within_k0'), '.0f')}% of games (displayed "
            f"rating: {fmt(100 * kn(n, 'q4_test_raw_within_k0'), '.0f')}%), mostly by pulling high "
            "launch ratings back toward the typical level.")


def trust_footnote() -> str:
    return ("Agreement at later months is partly mechanical: the running average at month 24 "
            "already contains most of the raters of month 36.")


def kpis(n: dict, cfg: dict) -> list[tuple[str, str]]:
    """(value, label) for the four headline numbers."""
    return [
        (fmt(kn(n, "change_36"), "+.2f", minus=True), "rating points lost in three years"),
        (f"{fmt(100 * kn(n, 'share_of_decline_by_12'), '.0f')}%", "of that drop in year one"),
        (f"{fmt(100 * kn(n, 'share_declining'), '.0f')}%", "of games end lower than they start"),
        (f"Month {fmt(kn(n, 'q4_rule_month'), '.0f')}", "before a rating can be trusted"),
    ]
