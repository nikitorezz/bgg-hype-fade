"""Pure data logic for the dashboard (pandas/numpy only, no Streamlit): easy to test and reuse."""

from __future__ import annotations

import numpy as np
import pandas as pd


def kn(numbers: dict[str, dict], key: str) -> float:
    """Value of a key number (raises KeyError if missing, so text can never show a stale number)."""
    return numbers[key]["value"]


def ci_text(numbers: dict[str, dict], key: str, digits: int = 2) -> str:
    """'[low, high]' for a key number, or '' if it has no CI."""
    e = numbers[key]
    if e.get("ci_low") is None or e.get("ci_high") is None:
        return ""
    return f"[{e['ci_low']:.{digits}f}, {e['ci_high']:.{digits}f}]"


def avg_wide(traj: pd.DataFrame) -> pd.DataFrame:
    """Games x k matrix of the displayed average (NaN where the month is unobserved)."""
    return traj.pivot(index="game_id", columns="k", values="avg_rating").sort_index()


def trust_errors(wide: pd.DataFrame, main_ids: np.ndarray, k_max: int,
                 final_k: int) -> tuple[np.ndarray, np.ndarray]:
    """|avg at k - avg at final_k| for main-sample games (G x K) and the observed mask."""
    w = wide.loc[wide.index.isin(main_ids)]
    ks = list(range(k_max + 1))
    target = w[final_k].to_numpy()
    x = w[ks].to_numpy()
    err = np.abs(x - target[:, None])
    return err, ~np.isnan(err)


def trust_curve(err: np.ndarray, obs: np.ndarray, tolerance: float) -> pd.DataFrame:
    """Share of games within ``tolerance`` of their final rating at each k (same rule as the
    analysis: err <= tolerance on float64 values)."""
    within = (err <= tolerance) & obs
    n = obs.sum(axis=0)
    return pd.DataFrame({"k": np.arange(err.shape[1]), "share": within.sum(axis=0) / n, "n": n})


def trust_month(curve: pd.DataFrame, target_share: float) -> float:
    """First k with share >= target (NaN if never reached)."""
    hit = curve.loc[curve["share"] >= target_share, "k"]
    return float(hit.iloc[0]) if len(hit) else float("nan")


def cohort_change_distribution(wide: pd.DataFrame, games: pd.DataFrame, entry_year: int,
                               k: int) -> np.ndarray:
    """Change in displayed average from entry to month k for every game launched that year."""
    ids = games.loc[games["entry_year"] == entry_year, "game_id"]
    w = wide.loc[wide.index.isin(ids)]
    d = (w[k] - w[0]).dropna()
    return d.to_numpy()


def share_fallen_further(value: float, dist: np.ndarray) -> float:
    """Share of the cohort whose change is *less* negative than ``value`` (game fell further)."""
    return float((dist > value).mean()) if len(dist) else float("nan")


def last_observed(traj_g: pd.DataFrame) -> pd.Series:
    """Row of the game's latest observed month."""
    return traj_g.sort_values("k").iloc[-1]


def adjusted_vs_raw(adj: pd.DataFrame, tol: float) -> pd.DataFrame:
    """Long table (k, predictor, share_within, mae) from q4_adjusted_predictor.csv."""
    col = f"within_{tol}"
    rows = []
    for _, r in adj.iterrows():
        rows.append({"k": int(r["k"]), "predictor": "Displayed rating",
                     "share_within": r[f"raw_{col}"], "mae": r["raw_mae"], "n": r["n_test"]})
        rows.append({"k": int(r["k"]), "predictor": "Adjusted launch rating",
                     "share_within": r[f"adj_{col}"], "mae": r["adj_mae"], "n": r["n_test"]})
    return pd.DataFrame(rows)


def launch_year_options(games: pd.DataFrame) -> list[str]:
    return sorted(games["entry_year"].astype(str).unique())
