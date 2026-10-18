"""Part B: build the self-contained data extract for the dashboard (``bgg dashboard-data``).

The app never reads ``reports/`` or ``data/`` directly: everything it needs is copied or derived
into ``app/data/`` so the app folder can be deployed on its own.
"""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from bgg.analysis.crowdfunding import load_kaggle
from bgg.analysis.data import Inputs, control_series, load_inputs
from bgg.analysis.io import results_dir, write_table
from bgg.analysis.stats import group_mean_ci, mean_ci
from bgg.config import Config

log = logging.getLogger(__name__)

APP_DIR_NAME = "app"
COPY_TABLES = [
    "curve_overall", "curve_by_entry_year", "curve_by_hype_quartile", "curve_by_segment",
    "segment_change",
    "control_series", "control_curve_by_age", "gap_new_vs_displayed", "segments",
    "speed_not_size", "kickstarter_by_band", "q4_accuracy_by_k", "q4_adjusted_predictor",
    "sample_waterfall", "cohort_sizes", "table1_sample",
]
MAX_SIZE_MB = 20.0


def app_data_dir(cfg: Config) -> Path:
    d = cfg.root / APP_DIR_NAME / "data"
    d.mkdir(parents=True, exist_ok=True)
    return d


def adjusted_ratings(games: pd.DataFrame, numbers: dict[str, dict],
                     ks: list[int]) -> pd.DataFrame:
    """Adjusted launch rating at each k: the Q4 OLS model applied with the stored coefficients.

    ``avg_k`` is the displayed average at k, ``ln_raters_k`` the log of raters at k and
    ``ln_growth`` the log of (raters_k / raters_0 + 1); the growth term is absent at k = 0.
    """
    out = {}
    for k in ks:
        def c(name: str, k: int = k) -> float | None:
            e = numbers.get(f"q4_adj_coef_{name}_k{k}")
            return None if e is None else e["value"]

        val = c("const") + c("avg_k") * games[f"avg_m{k}"] + c("ln_raters_k") * np.log(
            games[f"raters_m{k}"].astype(float))
        if c("ln_growth") is not None:
            val = val + c("ln_growth") * np.log(
                games[f"raters_m{k}"].astype(float) / games["raters_m0"].astype(float) + 1)
        out[f"adj_rating_k{k}"] = val.astype("float32")
    return pd.DataFrame(out, index=games.index)


def build_games(cfg: Config, inp: Inputs, numbers: dict[str, dict]) -> pd.DataFrame:
    """One row per new release, with sample flags, milestones, hype and adjusted ratings."""
    g = inp.summary.copy()
    main = g["game_id"].isin(inp.main_ids)
    g["main_sample"] = main
    cut = g.loc[main, "raters_m36"].quantile(1 - inp.acfg["segments"]["popular_top_share"])
    g["popular_top"] = (g["raters_m36"] >= cut) & main
    end = pd.Timestamp(cfg.end_month)
    g["followup_months"] = ((end.year - g["entry_month"].dt.year) * 12
                            + (end.month - g["entry_month"].dt.month)).clip(upper=36)
    kag = load_kaggle(cfg)
    g["kickstarted"] = (g["game_id"].map(kag.set_index("game_id")["kickstarted"])
                        if kag is not None else np.nan)
    g["kickstarted"] = g["kickstarted"].astype("Int8")
    adj = adjusted_ratings(g, numbers, inp.acfg["q4"]["adjusted_ks"])
    g = pd.concat([g, adj], axis=1)
    keep = ["game_id", "latest_name", "entry_month", "entry_year", "pub_year_entry",
            "in_main_sample", "main_sample", "popular_top", "followup_months", "observed_m12",
            "observed_m24", "observed_m36"]
    keep += [f"avg_m{k}" for k in inp.cfg.section("summary")["milestones"]]
    keep += [f"raters_m{k}" for k in inp.cfg.section("summary")["milestones"]]
    keep += ["rank_m0", "rank_m36", "change_12", "change_24", "change_36", "hype_log",
             "hype_quartile", "kickstarted"] + list(adj.columns)
    out = g[keep].copy()
    return out


def build_trajectories(inp: Inputs) -> pd.DataFrame:
    """Game x k rows with only the columns the app draws."""
    w = inp.acfg["gap"]["window"]
    p = inp.panel
    return pd.DataFrame({
        "game_id": p["game_id"].astype("int32"), "k": p["k"].astype("int8"),
        "snap_month": p["snap_month"], "avg_rating": p["avg_rating"].astype("float64"),
        "n_raters": p["n_raters"].astype("int32"),
        "rank": p["rank"].astype("float32"),
        f"new_avg_{w}": p[f"new_avg_{w}"].where(p[f"new_avg_ok_{w}"]).astype("float32"),
    })


def build_other_games(cfg: Config) -> pd.DataFrame:
    """Names of ranked games that are NOT new releases, with the reason (for graceful lookup)."""
    con = duckdb.connect(str(cfg.path("duckdb")), read_only=True)
    try:
        df = con.execute("""
            SELECT game_id, latest_name, entry_month,
                   CASE WHEN left_censored THEN 'left_censored'
                        WHEN pub_year_unknown THEN 'unknown_pub_year'
                        ELSE 'old_game' END AS reason,
                   pub_year_entry
            FROM game_cohorts WHERE NOT is_new_release ORDER BY latest_name""").df()
    finally:
        con.close()
    return df


def _start_deciles(games: pd.DataFrame, n_bins: int = 10) -> pd.Series:
    """Decile label (D01 lowest starting average ... D10 highest) per main-sample game."""
    m = games[games["main_sample"]].set_index("game_id")["avg_m0"]
    return ("D" + (pd.qcut(m, n_bins, labels=False, duplicates="drop") + 1).astype(str).str.zfill(2))


def segment_change_table(inp: Inputs, games: pd.DataFrame) -> pd.DataFrame:
    """change_12 / change_36 by segment (mean, 95% CI, n) for the 'Explore segments' view."""
    m = games[games["main_sample"]].copy()
    m["entry_year_s"] = m["entry_year"].astype(str)
    m["hype_s"] = m["hype_quartile"].map(lambda v: f"Q{int(v)}" if v == v else None)
    m["decile"] = m["game_id"].map(_start_deciles(games, inp.acfg["segments"]["avg0_deciles"]))
    m["popularity"] = np.where(m["popular_top"], "Top 10% by raters", "Other games")
    m["ks"] = m["kickstarted"].map({1: "Kickstarted", 0: "Not Kickstarted"})
    rows = []
    for gtype, col in (("none", None), ("launch_year", "entry_year_s"), ("hype_quartile", "hype_s"),
                       ("start_decile", "decile"), ("popularity", "popularity"),
                       ("kickstarted", "ks")):
        groups = [("All new games", m)] if col is None else list(m.dropna(subset=[col]).groupby(col))
        for val, g in groups:
            for metric in ("change_12", "change_36"):
                st = mean_ci(g[metric], inp.z)
                rows.append({"group_type": gtype, "group_value": val, "metric": metric,
                             "mean": st["mean"], "ci_low": st["ci_low"], "ci_high": st["ci_high"],
                             "n": st["n"]})
    return pd.DataFrame(rows)


def curve_by_segment(cfg: Config, inp: Inputs, games: pd.DataFrame,
                     series: pd.DataFrame) -> pd.DataFrame:
    """Mean change curves for every 'compare by' option, raw and drift-adjusted (long format)."""
    p = inp.panel[inp.panel["game_id"].isin(inp.main_ids)].merge(
        games[["game_id", "popular_top", "kickstarted", "avg_m0"]], on="game_id")
    ctrl = series.set_index("snap_month")["mean_avg"]
    drift = (p["snap_month"].map(ctrl) - p["entry_month"].map(ctrl)).to_numpy()
    p["d_adjusted"] = p["d_rating"] - drift
    p["all"] = "All new games"
    p["entry_year_s"] = p["entry_year"].astype(str)
    p = p.merge(games[["game_id", "hype_quartile"]], on="game_id", how="left", suffixes=("", "_g"))
    p["hype_s"] = p["hype_quartile"].map(lambda v: f"Q{int(v)}" if v == v else None)
    p["popularity"] = np.where(p["popular_top"], "Top 10% by raters", "Other games")
    p["ks"] = p["kickstarted"].map({1: "Kickstarted", 0: "Not Kickstarted"})
    p["decile"] = p["game_id"].map(_start_deciles(games))
    specs = [("none", "all"), ("launch_year", "entry_year_s"), ("hype_quartile", "hype_s"),
             ("start_decile", "decile"), ("popularity", "popularity"), ("kickstarted", "ks")]
    z = inp.z
    frames = []
    for gtype, col in specs:
        d = p.dropna(subset=[col])
        for adj, y in ((0, "d_rating"), (1, "d_adjusted")):
            t = group_mean_ci(d, [col, "k"], y, z).rename(columns={col: "group_value"})
            t.insert(0, "group_type", gtype)
            t.insert(1, "adjusted", adj)
            frames.append(t[["group_type", "group_value", "adjusted", "k", "mean", "ci_low",
                             "ci_high", "n"]])
    return pd.concat(frames, ignore_index=True)


def _ks_years(cfg: Config) -> list[int]:
    """Entry years modelled in Q3 (those with enough Kaggle coverage)."""
    cov = pd.read_csv(cfg.path("tables_dir") / "q3_coverage.csv")
    return [int(y) for y in cov.loc[cov["modelled"], "entry_year"]]


def _dir_size_mb(path: Path) -> float:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file()) / 1e6


def run_dashboard_data(cfg: Config, aggregates_only: bool = False) -> None:
    """Write app/data/ (games, trajectories, other games, tables, key numbers).

    With ``aggregates_only`` the game-level files are skipped and removed (APP_MODE=aggregates).
    """
    inp = load_inputs(cfg)
    kn_path = results_dir(cfg) / "key_numbers.json"
    payload = json.loads(kn_path.read_text(encoding="utf-8"))
    out = app_data_dir(cfg)
    series, _ = control_series(cfg)

    games = build_games(cfg, inp, payload["numbers"])
    if aggregates_only:
        for f in ("games", "trajectories", "other_games"):
            (out / f"{f}.parquet").unlink(missing_ok=True)
    else:
        traj = build_trajectories(inp)
        other = build_other_games(cfg)
        log.info("games %d rows (main sample %d), trajectories %d rows, other games %d rows",
                 len(games), int(games["main_sample"].sum()), len(traj), len(other))
        # the Kickstarter flag derives from CC BY-SA metadata: only its group averages are published
        published = games.drop(columns=["kickstarted"])
        published.to_parquet(out / "games.parquet", index=False, compression="zstd")
        traj.to_parquet(out / "trajectories.parquet", index=False, compression="zstd")
        other.to_parquet(out / "other_games.parquet", index=False, compression="zstd")

    seg = curve_by_segment(cfg, inp, games, series)
    write_table(cfg, seg, "curve_by_segment")
    write_table(cfg, segment_change_table(inp, games), "segment_change")

    tdir = out / "tables"
    tdir.mkdir(exist_ok=True)
    for name in COPY_TABLES:
        shutil.copyfile(cfg.path("tables_dir") / f"{name}.csv", tdir / f"{name}.csv")
    shutil.copyfile(cfg.path("qc_dir") / "qc_results.csv", tdir / "qc_results.csv")
    shutil.copyfile(results_dir(cfg) / "model_q2.csv", tdir / "model_q2.csv")
    shutil.copyfile(kn_path, out / "key_numbers.json")
    q4 = inp.acfg["q4"]
    app_cfg = {"rule_tolerance": q4["rule_tolerance"], "rule_share": q4["rule_share"],
               "tolerances": q4["tolerances"], "k_max": q4["k_max"],
               "final_k": inp.acfg["horizons"][-1], "end_month": str(cfg.end_month),
               "adjusted_ks": q4["adjusted_ks"], "train_entry_years": q4["train_entry_years"],
               "test_entry_years": q4["test_entry_years"],
               "speed_months": inp.acfg["speed"]["months"],
               "main_entry_start": str(cfg.section("cohort")["main_entry_start"]),
               "main_entry_end": str(cfg.main_entry_end),
               "start_month": str(cfg.start_month), "kickstarter_years": _ks_years(cfg),
               "mode_built": "aggregates" if aggregates_only else "full"}
    (out / "app_config.json").write_text(json.dumps(app_cfg, indent=2), encoding="utf-8")

    size = _dir_size_mb(out)
    log.info("app/data size: %.1f MB (limit %.0f MB)", size, MAX_SIZE_MB)
    if size > MAX_SIZE_MB:
        raise RuntimeError(f"app/data is {size:.1f} MB, over the {MAX_SIZE_MB:.0f} MB limit")
