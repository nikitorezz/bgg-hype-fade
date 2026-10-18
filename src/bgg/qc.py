"""Step 5: run sql/04_quality_checks.sql and write the QC report, CSV and spot-check figure."""

from __future__ import annotations

import csv
import logging
import subprocess
from collections import Counter
from datetime import datetime

import duckdb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from bgg.build import connect, run_sql_file, set_variables  # noqa: E402
from bgg.config import PROJECT_ROOT, Config  # noqa: E402

log = logging.getLogger(__name__)


def _prepare_inputs(con: duckdb.DuckDBPyConnection, cfg: Config) -> None:
    """Load the manifest and the expected values from config.yaml into tables/variables."""
    qc = cfg.section("qc")
    con.execute("SET VARIABLE manifest_path = ?", [cfg.path("manifest").as_posix()])
    con.execute("CREATE OR REPLACE TABLE manifest AS SELECT * FROM "
                "read_csv(getvariable('manifest_path'), header = true, "
                "types = {'month': 'DATE', 'chosen_date': 'DATE'})")
    con.execute("SET VARIABLE milestones = ?", [list(cfg.section("summary")["milestones"])])
    con.execute("SET VARIABLE tolerance_mean_change = ?", [qc["tolerance_mean_change"]])
    con.execute("SET VARIABLE pilot_games_with_missing_month = ?",
                [qc["pilot_games_with_missing_month"]])

    con.execute("CREATE OR REPLACE TABLE qc_expect_subst (month DATE)")
    con.executemany("INSERT INTO qc_expect_subst VALUES (?)",
                    [[m] for m in qc["expected_substituted_months"]])
    con.execute("CREATE OR REPLACE TABLE qc_expect_entry (entry_year INT, expected INT)")
    con.executemany("INSERT INTO qc_expect_entry VALUES (?, ?)",
                    list(qc["expected_new_releases"].items()))
    con.execute("CREATE OR REPLACE TABLE qc_expect_m36 (entry_year INT, pilot INT)")
    con.executemany("INSERT INTO qc_expect_m36 VALUES (?, ?)",
                    list(qc["pilot_observed_m36"].items()))
    con.execute("CREATE OR REPLACE TABLE qc_expect_mean (k INT, expected DOUBLE)")
    con.executemany("INSERT INTO qc_expect_mean VALUES (?, ?)",
                    list(qc["expected_mean_change"].items()))
    con.execute("""CREATE OR REPLACE TABLE qc_expect_spot (
        id BIGINT, name VARCHAR, entry DATE, pub_year INT, in_cohort BOOL, avg_k0 DOUBLE,
        raters_k0 INT, raters_k6 INT, avg_k12 DOUBLE, avg_k36 DOUBLE, raters_k36 INT)""")
    con.executemany("INSERT INTO qc_expect_spot VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    [[s["id"], s["name"], s["entry"], s["pub_year"], s["in_cohort"], s["avg_k0"],
                      s["raters_k0"], s["raters_k6"], s["avg_k12"], s["avg_k36"],
                      s["raters_k36"]] for s in qc["spot_checks"]])


def _git_commit() -> str:
    try:
        run = lambda *a: subprocess.run(["git", "-C", str(PROJECT_ROOT), *a],  # noqa: E731
                                        capture_output=True, text=True, check=True).stdout.strip()
        dirty = "+uncommitted changes" if run("status", "--porcelain") else ""
        return run("rev-parse", "--short", "HEAD") + dirty
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "n/a (not a git checkout)"


def _md_table(header: list[str], rows: list[tuple]) -> str:
    def cell(v: object) -> str:
        return ("-" if v is None else str(v)).replace("|", "\\|")

    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines += ["| " + " | ".join(cell(v) for v in r) + " |" for r in rows]
    return "\n".join(lines)


def _table(con: duckdb.DuckDBPyConnection, name: str) -> tuple[list[str], list[tuple]]:
    cur = con.execute(f"SELECT * FROM {name}")
    return [d[0] for d in cur.description], cur.fetchall()


def _write_csv(cfg: Config, header: list[str], rows: list[tuple]) -> None:
    path = cfg.path("qc_dir") / "qc_results.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


def _write_report(cfg: Config, con: duckdb.DuckDBPyConnection, header: list[str],
                  rows: list[tuple]) -> Counter:
    counts = Counter(r[header.index("status")] for r in rows)
    parts = [
        "# QC report",
        "",
        f"- Run: {datetime.now().astimezone().isoformat(timespec='seconds')}",
        f"- Config end_month: {cfg.end_month}",
        f"- Git commit: {_git_commit()}",
        f"- Summary: **{counts['PASS']} PASS, {counts['WARN']} WARN, {counts['FAIL']} FAIL**"
        f" ({counts['INFO']} report-only INFO rows)",
        "",
        "## Results",
        "",
        _md_table(header, rows),
        "",
        "## Substituted months (check 02)",
        "",
        _md_table(*_table(con, "qc_tbl_substitutions")),
        "",
        "## New releases with a missing month, by entry year (check 10)",
        "",
        "`with_internal_gap`: a month is absent but later months exist (the game fell out of the "
        "ranking and came back, or a snapshot lacked it). `dropped_out_early`: ranking history "
        "ends before the end of follow-up.",
        "",
        _md_table(*_table(con, "qc_tbl_missing_months")),
        "",
        "## Share of usable new_avg by months since entry (check 12)",
        "",
        "Among panel rows whose lagged month is observed. Usable = delta raters >= threshold AND "
        "rounding-error bound <= threshold AND value in the valid range.",
        "",
        _md_table(*_table(con, "qc_tbl_new_avg_ok")),
        "",
        "## Spot-check games (check 16)",
        "",
        _md_table(*_table(con, "qc_tbl_spot_checks")),
        "",
    ]
    path = cfg.path("qc_dir") / "qc_report.md"
    path.write_text("\n".join(parts), encoding="utf-8")
    log.info("wrote %s", path)
    return counts


def _spot_check_figure(cfg: Config, con: duckdb.DuckDBPyConnection) -> None:
    """One small panel per spot-check game: avg_rating by k, plus usable 3-month new_avg points."""
    games = con.execute("SELECT id, name FROM qc_expect_spot ORDER BY id").fetchall()
    fig, axes = plt.subplots(2, 5, figsize=(16, 6), sharex=True)
    for ax, (gid, name) in zip(axes.ravel(), games, strict=False):
        traj = con.execute(
            "SELECT date_diff('month', g.first_month, s.snap_month) AS k, s.avg_rating "
            "FROM snapshots s JOIN games g USING (game_id) WHERE game_id = ? "
            "AND date_diff('month', g.first_month, s.snap_month) <= ? ORDER BY k",
            [gid, cfg.section("cohort")["max_k"]]).fetchall()
        ok = con.execute("SELECT k, new_avg_3 FROM panel WHERE game_id = ? AND new_avg_ok_3 "
                         "ORDER BY k", [gid]).fetchall()
        ax.plot([r[0] for r in traj], [r[1] for r in traj], color="#1f77b4", lw=1.5,
                label="Average")
        if ok:
            ax.scatter([r[0] for r in ok], [r[1] for r in ok], s=12, color="#d62728",
                       label="new_avg (3-month, usable)")
        ax.set_title(name, fontsize=9)
        ax.set_xlabel("months since entry")
        ax.grid(alpha=0.3)
    axes[0, 0].legend(fontsize=7)
    fig.suptitle("QC spot-check trajectories (not a headline chart)")
    fig.tight_layout()
    path = cfg.path("figures_dir") / "qc_spotcheck_trajectories.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=120)
    plt.close(fig)
    log.info("wrote %s", path)


def run_qc(cfg: Config) -> int:
    """Run all checks, write the reports; returns 1 if any check FAILs, else 0."""
    cfg.path("qc_dir").mkdir(parents=True, exist_ok=True)
    con = connect(cfg)
    try:
        set_variables(con, cfg)
        _prepare_inputs(con, cfg)
        run_sql_file(con, cfg, "04_quality_checks.sql")
        header, rows = _table(con, "qc_results")
        log.info("qc: table qc_results has %d rows", len(rows))
        _write_csv(cfg, header, rows)
        counts = _write_report(cfg, con, header, rows)
        _spot_check_figure(cfg, con)
    finally:
        con.close()
    log.info("QC summary: %d PASS, %d WARN, %d FAIL, %d INFO", counts["PASS"], counts["WARN"],
             counts["FAIL"], counts["INFO"])
    for r in rows:
        if r[header.index("status")] in ("WARN", "FAIL"):
            log.warning("%s %s: %s (expected %s) -> %s", r[0], r[1], r[2], r[3], r[4])
    return 1 if counts["FAIL"] else 0
