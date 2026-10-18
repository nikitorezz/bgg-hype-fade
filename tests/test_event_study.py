import numpy as np
import pandas as pd
import pytest

from bgg.analysis.models import event_arrays, fit_event_study_panelols, within_betas

KMAX = 6
TRUE_BETA = np.array([-0.1, -0.2, -0.25, -0.3, -0.32, -0.33])


def _simulate(n_games=400, noise=0.02, seed=1, drop=0.1):
    rng = np.random.default_rng(seed)
    rows = []
    for g in range(n_games):
        alpha = rng.normal(7.5, 1.0)  # big game effects must not bias the beta_k
        for k in range(KMAX + 1):
            if k > 0 and rng.random() < drop:  # unbalanced: some months missing
                continue
            y = alpha + (TRUE_BETA[k - 1] if k else 0.0) + rng.normal(0, noise)
            rows.append((g, pd.Timestamp("2020-01-01") + pd.DateOffset(months=k + g % 5), k, y))
    return pd.DataFrame(rows, columns=["game_id", "snap_month", "k", "avg_rating"])


def test_estimator_recovers_known_betas_despite_game_effects():
    df = _simulate()
    beta = within_betas(event_arrays(df, "avg_rating", KMAX))
    assert beta == pytest.approx(TRUE_BETA, abs=0.01)


def test_fast_estimator_matches_panelols_and_clustered_se_is_close():
    df = _simulate(n_games=300)
    es = fit_event_study_panelols(df, KMAX)
    beta, se = within_betas(event_arrays(df, "avg_rating", KMAX), cluster_se=True)
    assert beta == pytest.approx(es["beta"].to_numpy(), abs=1e-9)
    assert se == pytest.approx(es["se"].to_numpy(), rel=0.05)


def test_weights_and_bootstrap_counts_are_consistent():
    df = _simulate(n_games=200)
    ea = event_arrays(df, "avg_rating", KMAX)
    ones = np.ones(len(ea.n_obs))
    assert within_betas(ea, weights=ones) == pytest.approx(within_betas(ea))
    assert within_betas(ea, counts=ones) == pytest.approx(within_betas(ea))
    # doubling every game's weight does not change the point estimate
    assert within_betas(ea, weights=2 * ones) == pytest.approx(within_betas(ea))
