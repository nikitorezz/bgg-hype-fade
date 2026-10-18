"""Small statistics helpers shared by the analysis modules (means, CIs, bootstrap)."""

from __future__ import annotations

import numpy as np
import pandas as pd


def mean_ci(x: pd.Series | np.ndarray, z: float = 1.96) -> dict[str, float]:
    """Mean with normal-approximation CI (mean +/- z * SE across observations)."""
    a = np.asarray(x, dtype=float)
    a = a[~np.isnan(a)]
    n = len(a)
    if n == 0:
        return {"mean": np.nan, "se": np.nan, "ci_low": np.nan, "ci_high": np.nan, "n": 0}
    m = a.mean()
    se = a.std(ddof=1) / np.sqrt(n) if n > 1 else np.nan
    return {"mean": m, "se": se, "ci_low": m - z * se, "ci_high": m + z * se, "n": n}


def group_mean_ci(df: pd.DataFrame, by: str | list[str], col: str, z: float = 1.96) -> pd.DataFrame:
    """One row per group with mean, se, ci_low, ci_high, n of ``col`` (equal weight per row)."""
    rows = []
    for key, g in df.groupby(by, sort=True):
        keys = key if isinstance(key, tuple) else (key,)
        rows.append({**dict(zip([by] if isinstance(by, str) else by, keys, strict=True)),
                     **mean_ci(g[col], z)})
    return pd.DataFrame(rows)


def weighted_mean(x: np.ndarray | pd.Series, w: np.ndarray | pd.Series) -> float:
    """Weighted mean ignoring NaN values in either argument."""
    x, w = np.asarray(x, dtype=float), np.asarray(w, dtype=float)
    ok = ~(np.isnan(x) | np.isnan(w))
    return float((x[ok] * w[ok]).sum() / w[ok].sum()) if ok.any() else float("nan")


def percentile_ci(draws: np.ndarray, level: float = 0.95) -> tuple[float, float]:
    """Percentile interval of bootstrap draws (NaNs dropped)."""
    d = np.asarray(draws, dtype=float)
    d = d[~np.isnan(d)]
    a = (1 - level) / 2
    return float(np.quantile(d, a)), float(np.quantile(d, 1 - a))


def bootstrap_indices(n: int, reps: int, seed: int):
    """Yield ``reps`` arrays of row indices resampled with replacement (game-level bootstrap)."""
    rng = np.random.default_rng(seed)
    for _ in range(reps):
        yield rng.integers(0, n, n)
