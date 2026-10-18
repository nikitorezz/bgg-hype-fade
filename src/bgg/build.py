"""DuckDB runner: open the database, set config variables, run numbered SQL files, export files."""

from __future__ import annotations

import csv
import logging
import re
from pathlib import Path

import duckdb

from bgg.config import PROJECT_ROOT, Config

log = logging.getLogger(__name__)

SQL_DIR = PROJECT_ROOT / "sql"

# stage -> (sql file, tables whose row counts are logged afterwards)
STAGES: dict[str, tuple[str, list[str]]] = {
    "load": ("01_load.sql", ["snapshots_raw", "snapshots", "load_log", "games"]),
    "cohorts": ("02_entry_and_cohorts.sql", ["game_cohorts", "sample_waterfall", "cohort_sizes"]),
    "panel": ("03_panel.sql", ["panel", "game_summary"]),
    "qc": ("04_quality_checks.sql", ["qc_results"]),
}

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_REPEAT = re.compile(r"-- @repeat (\w+)\n(.*?)-- @end\n", re.S)


def connect(cfg: Config) -> duckdb.DuckDBPyConnection:
    """Open (creating if needed) the persistent database."""
    db = cfg.path("duckdb")
    db.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(db))


def template_values(cfg: Config) -> tuple[dict[str, str], dict[str, list[int]]]:
    """Scalars for ``{{name}}`` and lists for ``-- @repeat name`` blocks in the SQL files."""
    nra, cohort, summ = cfg.section("new_rating_average"), cfg.section("cohort"), cfg.section(
        "summary")
    partition = summ["hype_quartile_partition"]
    if not _IDENT.match(partition):
        raise ValueError(f"summary.hype_quartile_partition is not an identifier: {partition!r}")
    scalars = {
        "dedup_order": cfg.section("load")["dedup_order"],
        "hype_month": str(summ["hype_month"]),
        "hype_quartile_partition": partition,
        "main_window": str(nra["windows"][0]),
        "max_k": str(cohort["max_k"]),
    }
    lists = {
        "windows": list(nra["windows"]),
        "milestones": list(summ["milestones"]),
        # follow-up horizons at which "observed" flags and total changes are reported
        "horizons": [m for m in summ["milestones"] if m >= 12],
    }
    return scalars, lists


def expand_template(sql: str, scalars: dict[str, str], lists: dict[str, list[int]]) -> str:
    """Expand ``-- @repeat <list> ... -- @end`` blocks, then ``{{scalar}}`` placeholders."""

    def repeat(m: re.Match[str]) -> str:
        return "".join(m.group(2).replace("{{item}}", str(v)) for v in lists[m.group(1)])

    sql = _REPEAT.sub(repeat, sql)
    for key, value in scalars.items():
        sql = sql.replace("{{" + key + "}}", value)
    if "{{" in sql:
        raise ValueError("unresolved template placeholder in SQL")
    return sql


def set_variables(con: duckdb.DuckDBPyConnection, cfg: Config) -> None:
    """Pass every scalar threshold/date from config.yaml to SQL as a DuckDB variable."""
    cohort, nra, summ = cfg.section("cohort"), cfg.section("new_rating_average"), cfg.section(
        "summary")
    lo, hi = nra["valid_range"]
    values: dict[str, object] = {
        "start_month": cfg.start_month,
        "end_month": cfg.end_month,
        "min_row_ratio": cfg.section("download")["min_row_ratio"],
        "first_snapshot_month": cohort["first_snapshot_month"],
        "new_release_max_age_years": cohort["new_release_max_age_years"],
        "min_valid_pub_year": cohort["min_valid_pub_year"],
        "max_pub_year_slack": cohort["max_pub_year_slack"],
        "main_entry_start": cohort["main_entry_start"],
        "main_entry_end": cfg.main_entry_end,
        "followup_months": cohort["followup_months"],
        "max_k": cohort["max_k"],
        "rounding_half_unit": nra["rounding_half_unit"],
        "min_delta_raters": nra["min_delta_raters"],
        "max_error_bound": nra["max_error_bound"],
        "valid_min": lo,
        "valid_max": hi,
        "hype_month": summ["hype_month"],
    }
    for name, v in values.items():
        con.execute(f"SET VARIABLE {name} = ?", [v])


def read_manifest_files(cfg: Config) -> list[str]:
    """Snapshot paths (forward slashes) listed in the manifest, in month order."""
    path = cfg.path("manifest")
    if not path.exists():
        raise FileNotFoundError(f"{path} not found; run 'bgg download' first")
    raw_dir = cfg.path("raw_dir")
    with path.open(newline="", encoding="utf-8") as fh:
        files = [(raw_dir / r["chosen_file"]).as_posix() for r in csv.DictReader(fh)]
    missing = [f for f in files if not Path(f).exists()]
    if missing:
        raise FileNotFoundError(f"manifest files missing on disk: {missing[:3]} ...")
    return files


def run_sql_file(con: duckdb.DuckDBPyConnection, cfg: Config, filename: str) -> None:
    """Expand templates in ``sql/<filename>`` and execute it."""
    scalars, lists = template_values(cfg)
    text = (SQL_DIR / filename).read_text(encoding="utf-8")
    con.execute(expand_template(text, scalars, lists))


def _count(con: duckdb.DuckDBPyConnection, table: str) -> int:
    return con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]


def _copy(con: duckdb.DuckDBPyConnection, table: str, dest: Path, fmt: str) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    opts = "FORMAT PARQUET, COMPRESSION ZSTD" if fmt == "parquet" else "FORMAT CSV, HEADER"
    con.execute(f"COPY (SELECT * FROM {table}) TO '{dest.as_posix()}' ({opts})")
    log.info("exported %s -> %s", table, dest)


def run_sql_stage(cfg: Config, stage: str) -> None:
    """Run the SQL for ``load``, ``cohorts`` or ``panel`` and write that stage's exports."""
    filename, tables = STAGES[stage]
    con = connect(cfg)
    try:
        set_variables(con, cfg)
        if stage == "load":
            con.execute("SET VARIABLE snapshot_files = ?", [read_manifest_files(cfg)])
        run_sql_file(con, cfg, filename)
        for t in tables:
            log.info("%s: table %s has %d rows", stage, t, _count(con, t))
        _export(con, cfg, stage)
    finally:
        con.close()


def _export(con: duckdb.DuckDBPyConnection, cfg: Config, stage: str) -> None:
    interim, processed, tables = cfg.path("interim_dir"), cfg.path("processed_dir"), cfg.path(
        "tables_dir")
    if stage == "load":
        _copy(con, "snapshots", interim / "snapshots_monthly.parquet", "parquet")
        _copy(con, "games", interim / "games.parquet", "parquet")
    elif stage == "cohorts":
        _copy(con, "sample_waterfall", tables / "sample_waterfall.csv", "csv")
        _copy(con, "cohort_sizes", tables / "cohort_sizes.csv", "csv")
    elif stage == "panel":
        _copy(con, "panel", processed / "panel.parquet", "parquet")
        _copy(con, "game_summary", processed / "game_summary.parquet", "parquet")
