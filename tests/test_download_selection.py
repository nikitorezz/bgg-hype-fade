from datetime import date

from bgg.download import build_candidates, select_monthly


def _counter(counts):
    return lambda d: counts[d]


def test_first_month_accepts_first_candidate():
    m = date(2016, 10, 1)
    out = select_monthly({m: [date(2016, 10, 12)]}, _counter({date(2016, 10, 12): 12800}), 0.99)
    assert out[0].chosen == date(2016, 10, 12) and out[0].status == "ok"


def test_truncation_case_2024_01_picks_day_5():
    prev, jan = date(2023, 12, 1), date(2024, 1, 1)
    counts = {date(2023, 12, 1): 25488, date(2024, 1, 1): 22100, date(2024, 1, 2): 22800,
              date(2024, 1, 3): 23800, date(2024, 1, 4): 24800, date(2024, 1, 5): 25646}
    cands = {prev: [date(2023, 12, 1)], jan: [date(2024, 1, d) for d in range(1, 6)]}
    out = select_monthly(cands, _counter(counts), 0.99)
    assert out[1].chosen == date(2024, 1, 5)
    assert out[1].status == "substituted"
    assert out[1].rejected == [(date(2024, 1, 1), 22100), (date(2024, 1, 2), 22800),
                               (date(2024, 1, 3), 23800), (date(2024, 1, 4), 24800)]


def test_prev_rows_seed_one_month_at_a_time():
    jan = date(2024, 1, 1)
    counts = {date(2024, 1, 1): 22100, date(2024, 1, 5): 25646}
    out = select_monthly({jan: [date(2024, 1, 1), date(2024, 1, 5)]}, _counter(counts), 0.99,
                         prev_rows=25488)
    assert out[0].chosen == date(2024, 1, 5)


def test_fallback_when_nothing_passes():
    prev, nxt = date(2024, 8, 1), date(2024, 9, 1)
    counts = {date(2024, 8, 1): 26000, date(2024, 9, 1): 20000, date(2024, 9, 2): 21000}
    out = select_monthly({prev: [date(2024, 8, 1)], nxt: [date(2024, 9, 1), date(2024, 9, 2)]},
                         _counter(counts), 0.99)
    assert out[1].chosen == date(2024, 9, 2) and out[1].status == "fallback"


def test_missing_month_is_reported():
    out = select_monthly({date(2020, 1, 1): [date(2020, 1, 1)], date(2020, 2, 1): []},
                         _counter({date(2020, 1, 1): 100}), 0.99)
    assert out[1].status == "missing"


def test_build_candidates_window_and_first_month_fallback():
    files = ["2016-10-12.csv", "2016-10-13.csv", "2016-11-01.csv", "2016-11-11.csv"]
    months = [date(2016, 10, 1), date(2016, 11, 1)]
    c = build_candidates(files, months, 10)
    assert c[months[0]] == [date(2016, 10, 12)]
    assert c[months[1]] == [date(2016, 11, 1)]
