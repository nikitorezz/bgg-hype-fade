"""Output helpers: tidy CSV tables, markdown tables, and key-number fragments."""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path

import pandas as pd

from bgg.config import Config

log = logging.getLogger(__name__)


def results_dir(cfg: Config) -> Path:
    d = cfg.root / cfg.section("analysis")["results_dir"]
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_table(cfg: Config, df: pd.DataFrame, name: str, where: str = "tables") -> Path:
    """Write ``df`` as ``<dir>/<name>.csv`` (dir = tables_dir or the results dir)."""
    d = cfg.path("tables_dir") if where == "tables" else results_dir(cfg)
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{name}.csv"
    df.to_csv(path, index=False, float_format="%.6g")
    log.info("wrote %s (%d rows)", path.name, len(df))
    return path


def md_table(df: pd.DataFrame, floatfmt: str = "{:.3f}") -> str:
    """Render a DataFrame as a GitHub markdown table."""
    def cell(v: object) -> str:
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return "-"
        return floatfmt.format(v) if isinstance(v, float) else str(v)

    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    lines += ["| " + " | ".join(cell(v) for v in row) + " |" for row in df.itertuples(index=False)]
    return "\n".join(lines)


def entry(value: float | str | None, source: str, definition: str, ci_low: float | None = None,
          ci_high: float | None = None, n: int | None = None) -> dict:
    """One key-number record (value, optional CI, n, source table/model, plain definition)."""
    def clean(x):
        if x is None:
            return None
        if isinstance(x, str):
            return x
        x = float(x)
        return None if math.isnan(x) else x

    return {"value": clean(value), "ci_low": clean(ci_low), "ci_high": clean(ci_high),
            "n": None if n is None else int(n), "source": source, "definition": definition}


def save_fragment(cfg: Config, module: str, entries: dict[str, dict]) -> None:
    """Persist a module's key numbers; keynumbers.py merges all fragments."""
    d = results_dir(cfg) / "_fragments"
    d.mkdir(exist_ok=True)
    (d / f"{module}.json").write_text(json.dumps(entries, indent=2), encoding="utf-8")
    log.info("saved %d key numbers from %s", len(entries), module)
