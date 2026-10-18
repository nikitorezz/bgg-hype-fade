import pytest

from bgg.analysis.titles import figure_titles, fill
from bgg.config import load_config


def _n(v):
    return {"value": v}


def test_fill_applies_transforms_and_formats():
    out = fill("Lose {a|abs:.2f} points, {b|pct:.0f}% early, month {c:+.1f}",
               {"a": _n(-0.4012), "b": _n(0.609), "c": _n(3.0)})
    assert out == "Lose 0.40 points, 61% early, month +3.0"


def test_missing_key_raises_instead_of_inventing_a_number():
    with pytest.raises(KeyError):
        fill("{nope}", {})


def test_all_config_titles_have_a_template():
    cfg = load_config()
    assert {f"fig{i:02d}" for i in range(1, 11)} == set(cfg.section("analysis")["titles"])
    nums = {k: _n(1.0) for k in ("change_36", "share_of_decline_by_12", "gap_k36",
                                 "control_drift_36", "share_declining", "examples_min_raters",
                                 "beta_36", "q4_rule_month")}
    for i in range(1, 11):
        title, _ = figure_titles(cfg, f"fig{i:02d}", nums)
        assert title
