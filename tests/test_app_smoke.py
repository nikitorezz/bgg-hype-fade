import json

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


def _run(mode: str, monkeypatch) -> AppTest:
    monkeypatch.setenv("APP_MODE", mode)
    at = AppTest.from_file(SCRIPT, default_timeout=180)
    at.run()
    return at


@needs_data
@pytest.mark.parametrize("mode", ["full", "aggregates"])
def test_every_section_renders_in_both_modes(mode, monkeypatch):
    if mode == "full" and not (DATA / "games.parquet").exists():
        pytest.skip("game-level extract not built")
    at = _run(mode, monkeypatch)
    assert not at.exception, [e.value for e in at.exception]
    labels = [t.label for t in at.tabs]
    assert ("Look up a game" in labels) == (mode == "full")
    assert "Overview" in labels and "Method & data" in labels


@needs_data
def test_kpi_tiles_match_key_numbers(monkeypatch):
    at = _run("aggregates", monkeypatch)
    nums = json.loads((DATA / "key_numbers.json").read_text(encoding="utf-8"))["numbers"]
    vals = [m.value for m in at.metric]
    assert f"{100 * nums['share_of_decline_by_12']['value']:.0f}%" in vals
    assert f"{100 * nums['share_declining']['value']:.0f}%" in vals
    assert f"Month {nums['q4_rule_month']['value']:.0f}" in vals
    assert f"{nums['change_36']['value']:+.2f}".replace("-", "−") in vals


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
    at = _run("full", monkeypatch)
    for s in CFG.section("qc")["spot_checks"]:
        if not s["in_cohort"]:
            continue
        box = next(b for b in at.selectbox if b.label.startswith("Search the"))
        box.set_value(by_id[s["id"]]).run()
        assert not at.exception, (s["name"], [e.value for e in at.exception])
    # an established game is handled gracefully
    ti = next(t for t in at.text_input if t.label.startswith("Looking for an established"))
    ti.set_value("Gloomhaven").run()
    assert not at.exception
    assert any("not in the sample" in w.value for w in at.warning)


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
    monkeypatch.setenv("APP_MODE", "full")  # must fall back to aggregates by itself
    import importlib

    from lib import loaders
    importlib.reload(loaders)
    at = AppTest.from_file(SCRIPT, default_timeout=180)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert "Look up a game" not in [t.label for t in at.tabs]
    importlib.reload(loaders)
