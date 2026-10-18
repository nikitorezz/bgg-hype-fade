"""Run the real sql/03_panel.sql on a tiny in-memory dataset to test the new-rating average."""

import duckdb
import pytest

from bgg.build import run_sql_file, set_variables
from bgg.config import load_config


def _panel(rows: list[tuple[int, int, float, int]]):
    """rows = (game_id, k, avg_rating, n_raters); every game enters 2020-01 and is a new release."""
    cfg = load_config()
    con = duckdb.connect()
    set_variables(con, cfg)
    games = sorted({r[0] for r in rows})
    con.execute("""CREATE TABLE game_cohorts (
        game_id BIGINT, latest_name VARCHAR, entry_month DATE, entry_year INT, pub_year_entry INT,
        is_new_release BOOL, in_main_sample BOOL,
        observed_m12 BOOL, observed_m24 BOOL, observed_m36 BOOL)""")
    for g in games:
        con.execute("INSERT INTO game_cohorts VALUES (?, 'g', DATE '2020-01-01', 2020, 2020, "
                    "TRUE, TRUE, FALSE, FALSE, FALSE)", [g])
    con.execute("""CREATE TABLE snapshots (snap_month DATE, game_id BIGINT, avg_rating DOUBLE,
                   bayes_avg DOUBLE, n_raters INT, rank INT)""")
    for g, k, avg, n in rows:
        m = 2020 * 12 + k
        con.execute("INSERT INTO snapshots VALUES (make_date(?, ?, 1), ?, ?, 5.5, ?, 1)",
                    [m // 12, m % 12 + 1, g, avg, n])
    run_sql_file(con, cfg, "03_panel.sql")
    return con


def _row(con, game, k):
    cur = con.execute("SELECT * FROM panel WHERE game_id = ? AND k = ?", [game, k])
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, cur.fetchone(), strict=True))


def test_hand_built_case():
    con = _panel([(1, 0, 8.00, 100), (1, 1, 7.90, 150)])
    r = _row(con, 1, 1)
    assert r["delta_raters_1"] == 50
    assert r["new_avg_1"] == pytest.approx(7.70)
    assert r["new_avg_err_1"] == pytest.approx(0.025)
    assert r["new_avg_ok_1"] is True
    assert r["d_rating"] == pytest.approx(-0.10)


def test_no_new_raters_gives_null():
    con = _panel([(1, 0, 8.0, 100), (1, 1, 8.0, 100), (1, 2, 8.0, 90)])
    for k in (1, 2):
        r = _row(con, 1, k)
        assert r["new_avg_1"] is None and r["new_avg_err_1"] is None
        assert r["new_avg_ok_1"] is False
    assert _row(con, 1, 2)["raters_decreased_1"] is True
    assert _row(con, 1, 1)["raters_decreased_1"] is False


def test_threshold_logic():
    con = _panel([
        (1, 0, 8.0, 100), (1, 1, 8.0, 105),          # delta 5 < min_delta_raters
        (2, 0, 8.0, 60000), (2, 1, 8.0, 60100),      # delta 100, error bound ~6 > max
        (3, 0, 8.0, 100), (3, 1, 1.0, 120),          # new_avg outside [1, 10]
    ])
    assert _row(con, 1, 1)["new_avg_ok_1"] is False
    r2 = _row(con, 2, 1)
    assert r2["new_avg_ok_1"] is False and r2["new_avg_err_1"] > 5
    r3 = _row(con, 3, 1)
    assert r3["new_avg_out_of_range_1"] is True and r3["new_avg_ok_1"] is False


def test_lags_only_use_exactly_k_minus_w():
    # month 1 is missing: k=2 must not borrow k=0 as its "previous" for the 1-month window
    con = _panel([(1, 0, 8.0, 100), (1, 2, 7.8, 300), (1, 3, 7.7, 400)])
    r2 = _row(con, 1, 2)
    assert r2["prev_n_1"] is None and r2["new_avg_1"] is None
    assert r2["prev_n_3"] is None  # k - 3 < 0
    r3 = _row(con, 1, 3)
    assert r3["prev_n_3"] == 100 and r3["prev_n_1"] == 300
    assert r3["new_avg_3"] == pytest.approx((7.7 * 400 - 8.0 * 100) / 300)
