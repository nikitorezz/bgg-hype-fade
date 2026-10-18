import math

from bgg.fmt import fmt, pct, round_half_up


def test_half_up_rounds_ties_the_way_a_human_expects():
    assert format(0.365, ".2f") == "0.36"       # the float trap this helper avoids
    assert fmt(0.365, ".2f") == "0.37"
    assert fmt(-0.365, ".2f") == "-0.37"
    assert fmt(2.675, ".2f") == "2.68"
    assert str(round_half_up(0.125, 2)) == "0.13"


def test_formats_used_across_the_project():
    assert fmt(-0.3646, ".2f") == "-0.36"
    assert fmt(0.0492, "+.3f") == "+0.049"
    assert fmt(-0.004, "+.3f", minus=True) == "−0.004"
    assert fmt(12759, ",.0f") == "12,759"
    assert fmt(13.0, ".0f") == "13"
    assert pct(0.609) == "61%" and pct(0.8693, 1) == "86.9%"


def test_missing_values_render_as_dash():
    assert fmt(None) == "–" and fmt(math.nan) == "–" and pct(None) == "–"


def test_titles_use_the_helper():
    from bgg.analysis.titles import fill
    assert fill("{a|abs:.2f}", {"a": {"value": -0.365}}) == "0.37"
