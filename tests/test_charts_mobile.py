"""Charts must not hijack touch scrolling, and the phone variants must still build."""

import numpy as np
import pandas as pd
import pytest
from lib import charts

from bgg.config import load_config

CFG = load_config()
DATA = CFG.root / "app" / "data"
pytestmark = pytest.mark.skipif(not (DATA / "key_numbers.json").exists(),
                                reason="run `bgg dashboard-data` first")


def _t(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA / "tables" / f"{name}.csv")


def _all_figures(compact: bool):
    import json

    n = json.loads((DATA / "key_numbers.json").read_text(encoding="utf-8"))["numbers"]
    seg = _t("curve_by_segment")
    cfg = json.loads((DATA / "app_config.json").read_text(encoding="utf-8"))
    acc = _t("q4_accuracy_by_k")
    a = acc[acc["tolerance"] == cfg["rule_tolerance"]].sort_values("k")
    curve = pd.DataFrame({"k": a["k"], "share": a["share_within"], "n": a["n"]})
    bars = pd.DataFrame({"k": [0, 3], "predictor": ["Displayed rating"] * 2,
                         "share_within": [0.3, 0.4], "mae": [0.4, 0.3], "n": [10, 10]})
    bars = pd.concat([bars, bars.assign(predictor="Adjusted launch rating")])
    for gt in ("none", "hype_quartile", "launch_year", "start_decile", "popularity", "kickstarted"):
        d = seg[(seg["group_type"] == gt) & (seg["adjusted"] == 0)]
        yield f"overview/{gt}", charts.fig_overview(d, gt, compact=compact)
        yield f"explore/{gt}", charts.fig_explore(
            d, seg[(seg["group_type"] == "none") & (seg["adjusted"] == 0)], gt, compact=compact)
    yield "gap", charts.fig_gap(_t("gap_new_vs_displayed"), compact=compact)
    yield "speed", charts.fig_speed(_t("speed_not_size"), tuple(cfg["speed_months"]), compact=compact)
    yield "specs", charts.fig_specs(n, compact=compact)
    yield "kickstarter", charts.fig_kickstarter(_t("kickstarter_by_band"), compact=compact)
    yield "trust", charts.fig_trust(curve, cfg["rule_tolerance"], cfg["rule_share"], 13.0,
                                    compact=compact)
    yield "adjusted", charts.fig_adjusted(bars, 0.25, compact=compact)


@pytest.mark.parametrize("compact", [False, True])
def test_no_chart_captures_touch_drag_or_zoom(compact):
    for name, fig in _all_figures(compact):
        assert fig.layout.dragmode is False, name
        assert fig.layout.xaxis.fixedrange is True, name
        assert fig.layout.yaxis.fixedrange is True, name
    assert charts.PLOT_CONFIG["scrollZoom"] is False
    assert charts.PLOT_CONFIG["displayModeBar"] is False


def test_phone_charts_are_not_taller_or_wider_than_a_phone_needs():
    for name, fig in _all_figures(True):
        assert fig.layout.height <= 400, (name, fig.layout.height)
        assert fig.layout.margin.r <= 30, (name, fig.layout.margin.r)  # no wide label gutters


def test_phone_overview_uses_a_legend_not_end_labels():
    seg = _t("curve_by_segment")
    d = seg[(seg["group_type"] == "hype_quartile") & (seg["adjusted"] == 0)]
    wide, narrow = charts.fig_overview(d, "hype_quartile"), charts.fig_overview(
        d, "hype_quartile", compact=True)
    assert not wide.layout.showlegend and len(wide.layout.annotations) >= 4
    assert narrow.layout.showlegend and len(narrow.layout.annotations) == 0
    assert np.isclose(len([t for t in narrow.data if t.showlegend is not False and t.name]), 4)
