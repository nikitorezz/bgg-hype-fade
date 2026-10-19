import json

import numpy as np
import pandas as pd
import pytest

from bgg.config import load_config
from bgg.dashboard import MAX_SIZE_MB, adjusted_ratings, app_data_dir

CFG = load_config()
DATA = CFG.root / "app" / "data"
pytestmark = pytest.mark.skipif(not (DATA / "games.parquet").exists(),
                                reason="run `bgg dashboard-data` first")


@pytest.mark.skipif(not (CFG.path("processed_dir") / "game_summary.parquet").exists(),
                    reason="needs the local pipeline output (data/processed is not published)")
def test_row_counts_and_main_sample_complete():
    g = pd.read_parquet(DATA / "games.parquet")
    summary = pd.read_parquet(CFG.path("processed_dir") / "game_summary.parquet")
    assert len(g) == len(summary) and g["game_id"].is_unique
    main = summary[summary["in_main_sample"] & summary["observed_m36"]]["game_id"]
    assert set(main) == set(g.loc[g["main_sample"], "game_id"])
    traj = pd.read_parquet(DATA / "trajectories.parquet")
    assert len(traj) == len(pd.read_parquet(CFG.path("processed_dir") / "panel.parquet"))
    assert traj[["game_id", "k"]].duplicated().sum() == 0


def test_every_spot_check_game_present_or_explained():
    g = pd.read_parquet(DATA / "games.parquet")
    other = pd.read_parquet(DATA / "other_games.parquet")
    for s in CFG.section("qc")["spot_checks"]:
        in_g, in_o = s["id"] in set(g["game_id"]), s["id"] in set(other["game_id"])
        assert in_g != in_o, s["name"]          # exactly one of the two lists
        assert in_g == s["in_cohort"], s["name"]


def test_extract_size_limit():
    size = sum(f.stat().st_size for f in DATA.rglob("*") if f.is_file()) / 1e6
    assert size < MAX_SIZE_MB


def test_adjusted_rating_equals_formula_with_stored_coefficients():
    g = pd.read_parquet(DATA / "games.parquet")
    nums = json.loads((DATA / "key_numbers.json").read_text(encoding="utf-8"))["numbers"]
    row = g[g["game_id"] == 342942].iloc[0]  # Ark Nova
    for k in CFG.section("analysis")["q4"]["adjusted_ks"]:
        c = {n: nums[f"q4_adj_coef_{n}_k{k}"]["value"] for n in ("const", "avg_k", "ln_raters_k")}
        expected = c["const"] + c["avg_k"] * row[f"avg_m{k}"] + c["ln_raters_k"] * np.log(
            row[f"raters_m{k}"])
        if k > 0:
            expected += nums[f"q4_adj_coef_ln_growth_k{k}"]["value"] * np.log(
                row[f"raters_m{k}"] / row["raters_m0"] + 1)
        assert row[f"adj_rating_k{k}"] == pytest.approx(expected, abs=1e-4)
    again = adjusted_ratings(g.head(50), nums, [0, 12])
    assert np.allclose(again["adj_rating_k12"], g.head(50)["adj_rating_k12"], equal_nan=True,
                       atol=1e-4)


def test_app_data_dir_is_inside_app_folder():
    assert app_data_dir(CFG) == DATA
