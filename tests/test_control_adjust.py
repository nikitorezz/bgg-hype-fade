from datetime import date

import pandas as pd
import pytest

from bgg.analysis.data import control_change


def _lookup():
    # control mean falls 0.01 per month starting at 7.00 in 2020-01
    out, y, m = {}, 2020, 1
    for i in range(48):
        out[date(y, m, 1)] = 7.0 - 0.01 * i
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def test_control_change_uses_entry_month_plus_k():
    entries = pd.Series(pd.to_datetime(["2020-01-01", "2020-07-01"]))
    got = control_change(_lookup(), entries, 0, 36)
    assert got.tolist() == pytest.approx([-0.36, -0.36])


def test_control_change_partial_window_and_missing_month():
    entries = pd.Series(pd.to_datetime(["2020-03-01", "2023-06-01"]))
    got = control_change(_lookup(), entries, 6, 12)
    assert got.iloc[0] == pytest.approx(-0.06)
    assert pd.isna(got.iloc[1])  # 2024-06 / 2023-12 beyond the toy series -> NaN, not a guess
