import json
import re

import pytest

from bgg.config import load_config
from bgg.static_export import run_export_static

CFG = load_config()
DATA = CFG.root / "app" / "data"
pytestmark = pytest.mark.skipif(not (DATA / "key_numbers.json").exists(),
                                reason="run `bgg dashboard-data` first")


def test_dashboard_page_is_self_contained_and_matches_key_numbers():
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


def test_landing_page_is_small_and_has_social_preview_tags():
    run_export_static(CFG)
    index = CFG.root / "reports" / "site" / "index.html"
    assert index.stat().st_size < 1e6, "LinkedIn refuses pages over 3 MB; keep the landing page tiny"
    page = index.read_text(encoding="utf-8")
    assert 'href="dashboard.html"' in page
    for tag in ('property="og:title"', 'property="og:description"', 'property="og:image"',
                'name="twitter:card"', 'name="description"'):
        assert tag in page
    assert (CFG.root / "reports" / "site" / "social_card.png").exists()
