import numpy as np
import pandas as pd
import pytest

from bgg.analysis.stats import group_mean_ci, mean_ci, weighted_mean


def test_mean_ci_matches_hand_calculation():
    r = mean_ci([1.0, 2.0, 3.0, 4.0], z=2.0)
    se = np.std([1, 2, 3, 4], ddof=1) / 2
    assert r["mean"] == 2.5 and r["n"] == 4
    assert r["ci_low"] == pytest.approx(2.5 - 2 * se)
    assert r["ci_high"] == pytest.approx(2.5 + 2 * se)


def test_mean_ci_ignores_nan_and_handles_empty():
    assert mean_ci([1.0, np.nan, 3.0])["n"] == 2
    assert np.isnan(mean_ci([np.nan])["mean"])


def test_group_mean_ci_one_row_per_group():
    df = pd.DataFrame({"k": [0, 0, 1, 1], "y": [1.0, 3.0, 2.0, 4.0]})
    out = group_mean_ci(df, "k", "y")
    assert out["mean"].tolist() == [2.0, 3.0] and out["n"].tolist() == [2, 2]


def test_gap_is_rowwise_not_difference_of_weighted_means():
    # A big, highly rated game (weight 1000) and a small, low-rated one (weight 10).
    df = pd.DataFrame({"avg_rating": [9.0, 5.0], "new_avg_3": [8.9, 4.5], "w": [1000, 10]})
    gap = df["new_avg_3"] - df["avg_rating"]
    assert gap.mean() == pytest.approx(-0.3)                 # equal weight per row (primary)
    assert weighted_mean(gap, df["w"]) == pytest.approx((-0.1 * 1000 - 0.5 * 10) / 1010)
    # the trap: weighted mean of new_avg vs unweighted mean of avg_rating looks like a rise
    trap = weighted_mean(df["new_avg_3"], df["w"]) - df["avg_rating"].mean()
    assert trap > 0 > gap.mean()
