import json
import re

import pandas as pd
import pytest
from lib import logic
from streamlit.testing.v1 import AppTest

from bgg.config import load_config

CFG = load_config()
APP = CFG.root / "app"
DATA = APP / "data"
SCRIPT = str(APP / "streamlit_app.py")
needs_games = pytest.mark.skipif(not (DATA / "games.parquet").exists(),
                                 reason="game-level extract not built (aggregates-only checkout)")
needs_data = pytest.mark.skipif(not (DATA / "key_numbers.json").exists(),
                                reason="run `bgg dashboard-data` first")

ORDER_FULL = ["The fade", "Look up a game", "New vs displayed", "Hype", "When to trust", "Explore",
              "Method"]
ORDER_AGGREGATES = [s for s in ORDER_FULL if s != "Look up a game"]


def _run(mode: str, monkeypatch) -> AppTest:
    monkeypatch.setenv("BGG_APP_MODE", mode)
    at = AppTest.from_file(SCRIPT, default_timeout=180)
    at.run()
    return at


def _group(at: AppTest, label: str):
    """A pill group by its label (the section menu is labelled 'Section')."""
    return next(g for g in at.get("button_group") if g.label == label)


def _goto(at: AppTest, section: str) -> AppTest:
    _group(at, "Section").set_value(section).run()
    return at


def _page_text(at: AppTest) -> str:
    return " ".join(m.value for m in at.markdown)


def _trust_month(at: AppTest) -> str:
    m = re.search(r'class="trust-num">([^<]+)<', _page_text(at))
    return m.group(1) if m else ""


@needs_data
@pytest.mark.parametrize("mode", ["full", "aggregates"])
def test_every_section_renders_in_both_modes(mode, monkeypatch):
    if mode == "full" and not (DATA / "games.parquet").exists():
        pytest.skip("game-level extract not built")
    at = _run(mode, monkeypatch)
    assert not at.exception, [e.value for e in at.exception]
    options = list(_group(at, "Section").options)
    assert options == (ORDER_FULL if mode == "full" else ORDER_AGGREGATES)
    for section in options:                      # only the chosen section is rendered
        _goto(at, section)
        assert not at.exception, (section, [e.value for e in at.exception])


@needs_data
def test_deep_link_opens_the_requested_section(monkeypatch):
    monkeypatch.setenv("BGG_APP_MODE", "aggregates")
    at = AppTest.from_file(SCRIPT, default_timeout=180)
    at.query_params["s"] = "hype"
    at.run()
    assert _group(at, "Section").value == "Hype"
    assert at.query_params["s"] == ["hype"] or at.query_params["s"] == "hype"


@needs_data
def test_headline_numbers_match_key_numbers(monkeypatch):
    at = _run("aggregates", monkeypatch)
    nums = json.loads((DATA / "key_numbers.json").read_text(encoding="utf-8"))["numbers"]
    page = _page_text(at)
    for v in (f"{100 * nums['share_of_decline_by_12']['value']:.0f}%",
              f"{100 * nums['share_declining']['value']:.0f}%",
              f"Month {nums['q4_rule_month']['value']:.0f}",
              f"{nums['change_36']['value']:+.2f}".replace("-", "−")):
        assert f'<div class="v">{v}</div>' in page, v


@needs_games
def test_trust_month_default_equals_key_number():
    games = pd.read_parquet(DATA / "games.parquet")
    traj = pd.read_parquet(DATA / "trajectories.parquet")
    cfg = json.loads((DATA / "app_config.json").read_text(encoding="utf-8"))
    nums = json.loads((DATA / "key_numbers.json").read_text(encoding="utf-8"))["numbers"]
    main_ids = games.loc[games["main_sample"], "game_id"].to_numpy()
    err, obs = logic.trust_errors(logic.avg_wide(traj), main_ids, cfg["k_max"], cfg["final_k"])
    curve = logic.trust_curve(err, obs, cfg["rule_tolerance"])
    assert logic.trust_month(curve, cfg["rule_share"]) == nums["q4_rule_month"]["value"]
    k0 = nums["q4_within_025_k0"]["value"]
    assert curve.loc[curve["k"] == 0, "share"].iloc[0] == pytest.approx(k0)


@needs_games
def test_lookup_works_for_every_spot_check_game(monkeypatch):
    games = pd.read_parquet(DATA / "games.parquet")
    labels = games["latest_name"] + " (" + games["entry_year"].astype(str) + ")"
    by_id = dict(zip(games["game_id"], labels, strict=True))
    at = _goto(_run("full", monkeypatch), "Look up a game")
    for s in CFG.section("qc")["spot_checks"]:
        if not s["in_cohort"]:
            continue
        box = next(b for b in at.selectbox if b.label.startswith("Search"))
        box.set_value(by_id[s["id"]]).run()
        assert not at.exception, (s["name"], [e.value for e in at.exception])
    # an established game is handled gracefully
    ti = next(t for t in at.text_input if t.label.startswith("Looking for an established"))
    ti.set_value("Gloomhaven").run()
    assert not at.exception
    assert any("not in the sample" in m.value for m in at.markdown)


@needs_data
def test_aggregates_mode_works_without_game_level_files(monkeypatch, tmp_path):
    """Simulate the public deployment: only tables, key numbers and app_config exist."""
    import shutil

    public = tmp_path / "data"
    public.mkdir()
    shutil.copytree(DATA / "tables", public / "tables")
    for f in ("key_numbers.json", "app_config.json"):
        shutil.copyfile(DATA / f, public / f)
    monkeypatch.setenv("BGG_APP_DATA", str(public))
    monkeypatch.setenv("BGG_APP_MODE", "full")  # must fall back to aggregates by itself
    import importlib

    from lib import loaders
    importlib.reload(loaders)
    at = AppTest.from_file(SCRIPT, default_timeout=180)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert "Look up a game" not in list(_group(at, "Section").options)
    importlib.reload(loaders)


@needs_data
def test_trust_sliders_work_in_aggregates_mode(monkeypatch):
    at = _goto(_run("aggregates", monkeypatch), "When to trust")
    nums = json.loads((DATA / "key_numbers.json").read_text(encoding="utf-8"))["numbers"]
    assert _trust_month(at) == f"Month {nums['q4_rule_month']['value']:.0f}"  # +-0.25 / 80%
    tol = next(s for s in at.select_slider if s.label.startswith("Close means"))
    tol.set_value(0.5).run()
    assert _trust_month(at) == "Month 3"                                   # looser, earlier
    tol = next(s for s in at.select_slider if s.label.startswith("Close means"))
    tol.set_value(0.1).run()
    assert _trust_month(at) == "Month 26"
    assert not at.exception


@needs_data
def test_explore_segments_renders_for_every_split(monkeypatch):
    at = _goto(_run("aggregates", monkeypatch), "Explore")
    for label in list(_group(at, "Split by").options):
        _group(at, "Split by").set_value(label).run()
        assert not at.exception, (label, [e.value for e in at.exception])
    # no per-game content anywhere on the page
    page = _page_text(at)
    assert "Ark Nova" not in page and "Wingspan" not in page


@needs_data
def test_compare_pills_switch_the_chart_without_errors(monkeypatch):
    at = _run("aggregates", monkeypatch)
    for label in list(_group(at, "Compare").options):
        _group(at, "Compare").set_value(label).run()
        assert not at.exception, (label, [e.value for e in at.exception])


@needs_data
def test_phone_layout_renders_everywhere(monkeypatch):
    """?compact=1 (also chosen automatically for phone user agents) must work in every section."""
    monkeypatch.setenv("BGG_APP_MODE", "aggregates")
    at = AppTest.from_file(SCRIPT, default_timeout=180)
    at.query_params["compact"] = "1"
    at.run()
    for section in list(_group(at, "Section").options):
        _goto(at, section)
        assert not at.exception, (section, [e.value for e in at.exception])
