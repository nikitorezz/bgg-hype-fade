"""The dedup rule in sql/01_load.sql keeps the row with more raters (then better rank)."""

import duckdb

from bgg.build import SQL_DIR, expand_template

DEDUP_ORDER = "n_raters DESC, rank ASC"


def _dedup_sql() -> str:
    """Extract the `snapshots` statement from 01_load.sql so the test exercises the real SQL."""
    text = expand_template((SQL_DIR / "01_load.sql").read_text(encoding="utf-8"),
                           {"dedup_order": DEDUP_ORDER}, {})
    start = text.index("CREATE OR REPLACE TABLE snapshots AS")
    return text[start:text.index(";", start) + 1]


def test_duplicate_pair_keeps_row_with_more_raters():
    con = duckdb.connect()
    con.execute("""
        CREATE TABLE snapshots_raw AS SELECT * FROM (VALUES
            (DATE '2025-06-01', 1, 'A', 100, 7.5, 7.0, 6130),
            (DATE '2025-06-01', 1, 'A', 101, 7.5, 7.0, 6131),
            (DATE '2025-06-01', 2, 'B', 200, 6.0, 5.9, 50)
        ) t(snap_date, game_id, name, rank, avg_rating, bayes_avg, n_raters)
    """)
    con.execute(_dedup_sql())
    rows = con.execute("SELECT game_id, n_raters FROM snapshots ORDER BY game_id").fetchall()
    assert rows == [(1, 6131), (2, 50)]


def test_identical_duplicates_collapse_to_one_row():
    con = duckdb.connect()
    con.execute("""
        CREATE TABLE snapshots_raw AS SELECT * FROM (VALUES
            (DATE '2025-06-01', 1, 'A', 100, 7.5, 7.0, 60),
            (DATE '2025-06-01', 1, 'A', 100, 7.5, 7.0, 60)
        ) t(snap_date, game_id, name, rank, avg_rating, bayes_avg, n_raters)
    """)
    con.execute(_dedup_sql())
    assert con.execute("SELECT count(*) FROM snapshots").fetchone()[0] == 1
