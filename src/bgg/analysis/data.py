"""Loaders and sample definitions for the analysis (DuckDB/parquet -> pandas)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

import duckdb
import numpy as np
import pandas as pd

from bgg.config import Config, add_months

log = logging.getLogger(__name__)


@dataclass
class Inputs:
    """Processed tables plus the sample ids derived from them."""

    cfg: Config
    panel: pd.DataFrame      # every new-release game x observed month (k = 0..36)
    summary: pd.DataFrame    # one row per new-release game
    main_ids: np.ndarray     # in_main_sample AND observed at the last horizon
    balanced_ids: np.ndarray  # main sample also observed at every horizon

    @property
    def acfg(self) -> dict:
        return self.cfg.section("analysis")

    @property
    def z(self) -> float:
        return self.acfg["ci_z"]


def load_inputs(cfg: Config) -> Inputs:
    """Read panel and game_summary parquet files and define the main/balanced samples."""
    processed = cfg.path("processed_dir")
    panel = duckdb.sql(f"SELECT * FROM '{(processed / 'panel.parquet').as_posix()}'").df()
    summary = duckdb.sql(f"SELECT * FROM '{(processed / 'game_summary.parquet').as_posix()}'").df()
    horizons = cfg.section("analysis")["horizons"]
    main = summary["in_main_sample"] & summary[f"observed_m{horizons[-1]}"]
    balanced = main.copy()
    for h in horizons:
        balanced &= summary[f"observed_m{h}"]
    inp = Inputs(cfg, panel, summary, summary.loc[main, "game_id"].to_numpy(),
                 summary.loc[balanced, "game_id"].to_numpy())
    log.info("loaded %d panel rows, %d games; main sample %d, balanced %d", len(panel),
             len(summary), len(inp.main_ids), len(inp.balanced_ids))
    return inp


def main_summary(inp: Inputs) -> pd.DataFrame:
    """Game summary restricted to the main sample, with change_k columns."""
    return inp.summary[inp.summary["game_id"].isin(inp.main_ids)].copy()


def balanced_summary(inp: Inputs) -> pd.DataFrame:
    return inp.summary[inp.summary["game_id"].isin(inp.balanced_ids)].copy()


def main_panel(inp: Inputs) -> pd.DataFrame:
    return inp.panel[inp.panel["game_id"].isin(inp.main_ids)].copy()


def control_series(cfg: Config) -> tuple[pd.DataFrame, np.ndarray]:
    """Mature control group: games with >= min_raters in the base month, present in every snapshot.

    Returns (monthly mean-average series with rebased column, control game ids).
    """
    a = cfg.section("analysis")["control"]
    snap = (cfg.path("interim_dir") / "snapshots_monthly.parquet").as_posix()
    n_months = len(cfg.months)
    con = duckdb.connect()
    con.execute("SET VARIABLE base_month = ?", [a["base_month"]])
    con.execute("SET VARIABLE min_raters = ?", [a["min_raters"]])
    con.execute("SET VARIABLE n_months = ?", [n_months])
    con.execute(f"""CREATE VIEW snap AS SELECT * FROM '{snap}'""")
    ids = con.execute("""
        SELECT game_id FROM snap
        WHERE snap_month = getvariable('base_month') AND n_raters >= getvariable('min_raters')
          AND game_id IN (SELECT game_id FROM snap GROUP BY game_id
                          HAVING count(DISTINCT snap_month) = getvariable('n_months'))
        ORDER BY game_id""").df()["game_id"].to_numpy()
    series = con.execute("""
        SELECT snap_month, avg(avg_rating) AS mean_avg, count(*) AS n_games
        FROM snap WHERE game_id IN (SELECT unnest(?)) GROUP BY snap_month ORDER BY snap_month
        """, [ids.tolist()]).df()
    series["snap_month"] = pd.to_datetime(series["snap_month"])
    base = series.loc[series["snap_month"] == pd.Timestamp(a["base_month"]), "mean_avg"].iloc[0]
    series["rebased"] = series["mean_avg"] - base
    con.close()
    log.info("control group: %d games, mean %.3f -> %.3f", len(ids), series["mean_avg"].iloc[0],
             series["mean_avg"].iloc[-1])
    return series, ids


def control_lookup(series: pd.DataFrame) -> dict[date, float]:
    """Month-start date -> control mean average."""
    return {d.date(): v for d, v in zip(series["snap_month"], series["mean_avg"], strict=True)}


def control_change(lookup: dict[date, float], entry_month: pd.Series, k_from: int,
                   k_to: int) -> pd.Series:
    """Control-group change over [entry+k_from, entry+k_to] calendar months, per game.

    ``entry_month`` holds each game's entry month; NaN where the control series lacks a month.
    """
    def one(m) -> float:
        d = pd.Timestamp(m).date()
        return lookup.get(add_months(d, k_to), np.nan) - lookup.get(add_months(d, k_from), np.nan)

    return entry_month.map(one)
