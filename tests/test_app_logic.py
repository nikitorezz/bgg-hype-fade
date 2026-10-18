import numpy as np
import pandas as pd
from lib import logic


def _traj():
    # two games, k = 0..3; game 2 misses k = 2
    rows = []
    for gid, vals in {1: {0: 8.0, 1: 7.9, 2: 7.8, 3: 7.7}, 2: {0: 7.0, 1: 7.4, 3: 7.1}}.items():
        for k, v in vals.items():
            rows.append({"game_id": gid, "k": k, "avg_rating": v})
    return pd.DataFrame(rows)


def test_trust_curve_and_month_on_toy_data():
    wide = logic.avg_wide(_traj())
    err, obs = logic.trust_errors(wide, np.array([1, 2]), k_max=3, final_k=3)
    loose = logic.trust_curve(err, obs, 0.35)
    assert loose["share"].tolist() == [1.0, 1.0, 1.0, 1.0]
    tight = logic.trust_curve(err, obs, 0.15)
    assert tight["share"].tolist() == [0.5, 0.0, 1.0, 1.0]
    assert logic.trust_month(tight, 0.8) == 2.0
    assert np.isnan(logic.trust_month(tight, 1.01))


def test_trust_uses_only_main_sample_games():
    wide = logic.avg_wide(_traj())
    err, obs = logic.trust_errors(wide, np.array([1]), k_max=3, final_k=3)
    assert err.shape[0] == 1


def test_percentile_and_cohort_distribution():
    wide = logic.avg_wide(_traj())
    games = pd.DataFrame({"game_id": [1, 2], "entry_year": [2020, 2020]})
    dist = logic.cohort_change_distribution(wide, games, 2020, 1)
    assert sorted(dist.round(2)) == [-0.1, 0.4]
    assert logic.share_fallen_further(0.0, dist) == 0.5
    assert logic.share_fallen_further(-0.5, dist) == 1.0


def test_ci_text_handles_missing_ci():
    n = {"a": {"value": 1, "ci_low": 0.5, "ci_high": 1.5},
         "b": {"value": 2, "ci_low": None, "ci_high": None}}
    assert logic.ci_text(n, "a") == "[0.50, 1.50]"
    assert logic.ci_text(n, "b") == ""
