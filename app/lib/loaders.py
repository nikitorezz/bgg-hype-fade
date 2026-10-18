"""Cached data loaders for the Streamlit app. Reads only from app/data (self-contained)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import streamlit as st
from lib.logic import avg_wide, trust_errors

DATA = Path(os.environ.get("BGG_APP_DATA", Path(__file__).resolve().parents[1] / "data"))


def app_mode() -> str:
    """'full' (game lookup + live trust sliders) or 'aggregates' (curve/segment tables only).

    Chosen by the APP_MODE environment variable; falls back to aggregates when the game-level
    files are not shipped.
    """
    mode = os.environ.get("APP_MODE", "full").strip().lower()
    if mode == "full" and not (DATA / "games.parquet").exists():
        return "aggregates"
    return "aggregates" if mode == "aggregates" else "full"


@st.cache_data(show_spinner=False)
def numbers() -> dict[str, dict]:
    return json.loads((DATA / "key_numbers.json").read_text(encoding="utf-8"))["numbers"]


@st.cache_data(show_spinner=False)
def meta() -> dict:
    return json.loads((DATA / "key_numbers.json").read_text(encoding="utf-8"))["meta"]


@st.cache_data(show_spinner=False)
def app_config() -> dict:
    return json.loads((DATA / "app_config.json").read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def table(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA / "tables" / f"{name}.csv")


@st.cache_data(show_spinner=False)
def games() -> pd.DataFrame:
    return pd.read_parquet(DATA / "games.parquet")


@st.cache_data(show_spinner=False)
def trajectories() -> pd.DataFrame:
    return pd.read_parquet(DATA / "trajectories.parquet")


@st.cache_data(show_spinner=False)
def other_games() -> pd.DataFrame:
    return pd.read_parquet(DATA / "other_games.parquet")


@st.cache_data(show_spinner=False)
def wide() -> pd.DataFrame:
    return avg_wide(trajectories())


@st.cache_data(show_spinner=False)
def trust_matrix():
    """(error matrix, observed mask) for main-sample games, k = 0..k_max vs the final month."""
    cfg = app_config()
    g = games()
    main_ids = g.loc[g["main_sample"], "game_id"].to_numpy()
    return trust_errors(wide(), main_ids, cfg["k_max"], cfg["final_k"])
