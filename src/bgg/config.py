"""Load and validate ``config.yaml``; derive values used across stages."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = PROJECT_ROOT / "config.yaml"


def add_months(d: date, n: int) -> date:
    """Return the first day of the month ``n`` months after ``d``'s month."""
    idx = d.year * 12 + (d.month - 1) + n
    return date(idx // 12, idx % 12 + 1, 1)


def month_range(start: date, end: date) -> list[date]:
    """Inclusive list of month-start dates from ``start`` to ``end``."""
    out, cur = [], date(start.year, start.month, 1)
    while cur <= end:
        out.append(cur)
        cur = add_months(cur, 1)
    return out


@dataclass(frozen=True)
class Config:
    """Validated pipeline configuration (paths are absolute)."""

    raw: dict
    root: Path

    # --- convenience accessors -------------------------------------------------
    def section(self, name: str) -> dict:
        return self.raw[name]

    def path(self, key: str) -> Path:
        p = Path(self.raw["paths"][key])
        return p if p.is_absolute() else self.root / p

    @property
    def start_month(self) -> date:
        return self.raw["download"]["start_month"]

    @property
    def end_month(self) -> date:
        return self.raw["download"]["end_month"]

    @property
    def main_entry_end(self) -> date:
        """Last entry month with a full follow-up window (end_month - followup_months)."""
        return add_months(self.end_month, -self.raw["cohort"]["followup_months"])

    @property
    def months(self) -> list[date]:
        return month_range(self.start_month, self.end_month)


def _require(cfg: dict, section: str, keys: list[str]) -> None:
    if section not in cfg:
        raise ValueError(f"config.yaml: missing section '{section}'")
    missing = [k for k in keys if k not in cfg[section]]
    if missing:
        raise ValueError(f"config.yaml: section '{section}' missing keys {missing}")


def load_config(path: Path | str | None = None) -> Config:
    """Read the YAML file, validate required keys and return a :class:`Config`."""
    path = Path(path) if path else DEFAULT_CONFIG
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    _require(raw, "source", ["repo", "branch", "raw_url_template", "tree_api_url", "git_url",
                             "filename_pattern"])
    _require(raw, "download", ["backend", "start_month", "end_month", "max_candidate_day",
                               "min_row_ratio", "timeout_seconds", "max_retries",
                               "backoff_factor"])
    _require(raw, "paths", ["raw_dir", "rejected_dir", "manifest", "duckdb", "interim_dir",
                            "processed_dir", "qc_dir", "tables_dir", "figures_dir"])
    _require(raw, "load", ["dedup_order"])
    _require(raw, "cohort", ["first_snapshot_month", "new_release_max_age_years",
                             "min_valid_pub_year", "max_pub_year_slack", "main_entry_start",
                             "followup_months", "max_k"])
    _require(raw, "new_rating_average", ["rounding_half_unit", "min_delta_raters",
                                         "max_error_bound", "windows", "valid_range"])
    _require(raw, "summary", ["milestones", "hype_month", "hype_quartile_partition"])
    if raw["download"]["backend"] not in ("http", "git"):
        raise ValueError("download.backend must be 'http' or 'git'")
    if raw["download"]["start_month"] > raw["download"]["end_month"]:
        raise ValueError("download.start_month is after end_month")
    return Config(raw=raw, root=path.resolve().parent)
