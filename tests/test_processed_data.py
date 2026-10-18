"""Structural checks on data/processed/*.parquet (skipped when the pipeline has not been run)."""

import duckdb
import pytest

from bgg.config import load_config

CFG = load_config()
PANEL = CFG.path("processed_dir") / "panel.parquet"
SUMMARY = CFG.path("processed_dir") / "game_summary.parquet"

pytestmark = pytest.mark.skipif(not (PANEL.exists() and SUMMARY.exists()),
                                reason="data/processed is empty; run `bgg panel` first")


def _q(sql: str):
    return duckdb.sql(sql.format(panel=PANEL.as_posix(), summary=SUMMARY.as_posix())).fetchall()


def test_panel_unique_on_game_and_k():
    assert _q("SELECT count(*) - count(DISTINCT (game_id, k)) FROM '{panel}'")[0][0] == 0


def test_k_range_and_k0_present():
    lo, hi = _q("SELECT min(k), max(k) FROM '{panel}'")[0]
    assert lo == 0 and hi <= CFG.section("cohort")["max_k"]
    assert _q("SELECT count(DISTINCT game_id) FROM '{panel}' WHERE k = 0")[0][0] == \
        _q("SELECT count(DISTINCT game_id) FROM '{panel}'")[0][0]


def test_d_rating_zero_at_entry():
    assert _q("SELECT count(*) FROM '{panel}' WHERE k = 0 AND d_rating <> 0")[0][0] == 0


@pytest.mark.parametrize("k,expected", [(12, -0.24), (24, -0.33), (36, -0.40)])
def test_mean_change_matches_pilot(k, expected):
    got = _q(f"SELECT avg(d_rating) FROM '{{panel}}' WHERE k = {k}")[0][0]
    assert got == pytest.approx(expected, abs=0.03)


def test_summary_one_row_per_game_and_quartiles_balanced():
    assert _q("SELECT count(*) - count(DISTINCT game_id) FROM '{summary}'")[0][0] == 0
    sizes = _q("SELECT entry_year, hype_quartile, count(*) FROM '{summary}' "
               "WHERE hype_quartile IS NOT NULL GROUP BY ALL")
    by_year: dict[int, list[int]] = {}
    for year, _, n in sizes:
        by_year.setdefault(year, []).append(n)
    for counts in by_year.values():
        assert max(counts) - min(counts) <= 1
