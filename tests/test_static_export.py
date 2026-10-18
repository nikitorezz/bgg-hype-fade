import json
import re

import pytest

from bgg.config import load_config
from bgg.static_export import run_export_static

CFG = load_config()
DATA = CFG.root / "app" / "data"
pytestmark = pytest.mark.skipif(not (DATA / "key_numbers.json").exists(),
                                reason="run `bgg dashboard-data` first")


def test_static_page_is_self_contained_and_matches_key_numbers():
    path = run_export_static(CFG)
    page = path.read_text(encoding="utf-8")
    assert not re.search(r"<script[^>]+src=", page), "must not load external scripts"
    assert "Plotly" in page and page.count("js-plotly-plot") >= 9 or "plotly-graph-div" in page
    n = json.loads((DATA / "key_numbers.json").read_text(encoding="utf-8"))["numbers"]
    assert f"Month {n['q4_rule_month']['value']:.0f}" in page
    assert f"{100 * n['share_declining']['value']:.0f}%" in page
    assert f"{abs(n['change_36']['value']):.2f} points" in page
    assert "Look up" not in page            # no game-level content in the static page
    assert path.stat().st_size < 12e6
