"""Step 7: merge every module's key numbers into key_numbers.json, a facts-only summary and the
sanity-value comparison."""

from __future__ import annotations

import json
import logging
import math
import subprocess
from datetime import datetime
from pathlib import Path

import pandas as pd

from bgg.analysis.io import entry, md_table, results_dir, write_table
from bgg.config import PROJECT_ROOT, Config

log = logging.getLogger(__name__)

REQUIRED = (
    ["n_main_sample", "n_balanced_sample", "n_control_games", "change_12", "change_24",
     "change_36", "median_change_36", "share_declining", "share_of_decline_by_12",
     "control_drift_36", "change_36_control_adjusted", "change_36_rater_weighted",
     "gap_k3", "gap_k6", "gap_k12", "gap_k24", "gap_k36", "beta_12", "beta_24", "beta_36",
     "beta_share_by_12", "q4_rule_month", "q3_status"]
    + [f"spec_{s}_hype{suffix}" for s in "abcd" for suffix in ("", "_per_sd", "_p")]
    + [f"change_36_hype_q{q}" for q in range(1, 5)]
    + [f"{base}_by_hype_q{q}" for base in ("change_6", "rater_growth_m6",
                                            "rater_growth_median_m6", "entry_rater_share_m36",
                                            "gap_k36") for q in range(1, 5)]
    + ["share_rank_improved_36", "avg_rank100", "avg_rank1000", "avg_rank100_vs_rank1000",
       "fade_share_of_rank_gap", "ks_avg_m0", "nonks_avg_m0", "ks_gap_within_bands"]
    + [f"q4_adj_coef_{c}_k{k}" for k in (0, 3, 6, 12) for c in ("const", "avg_k", "ln_raters_k")]
    + [f"q4_mae_k{k}" for k in (0, 3, 6, 12)]
    + [f"q4_within_025_k{k}" for k in (0, 3, 6, 12)]
    + [f"q4_test_{kind}_{m}_k{k}" for kind in ("raw", "adj") for m in ("mae", "within")
       for k in (0, 3, 6, 12)]
)

HEADLINE = [
    ("n_main_sample", "Main sample (games)"), ("n_balanced_sample", "Balanced sample (games)"),
    ("change_12", "Mean change in rating, entry to month 12"),
    ("change_24", "... to month 24"), ("change_36", "... to month 36"),
    ("share_of_decline_by_12", "Share of 36-month decline reached by month 12"),
    ("median_change_36", "Median change to month 36"),
    ("share_declining", "Share of games declining"),
    ("change_36_rater_weighted", "Rater-weighted change to month 36"),
    ("control_drift_36", "Mature-control drift over 36 months"),
    ("change_36_control_adjusted", "Control-adjusted change to month 36"),
    ("gap_k3", "New raters minus displayed, month 3"), ("gap_k12", "... month 12"),
    ("gap_k36", "... month 36"),
    ("beta_12", "Event study beta, month 12"), ("beta_36", "Event study beta, month 36"),
    ("spec_a_hype", "Q2 Spec A hype coefficient (H2: negative)"),
    ("spec_b_hype", "Q2 Spec B hype coefficient (H2: negative)"),
    ("spec_c_hype", "Q2 Spec C reach coefficient"), ("spec_d_hype", "Q2 Spec D, no controls"),
    ("q4_rule_month", "First month with >=80% of games within ±0.25 of month-36 rating"),
    ("q4_within_025_k0", "Share within ±0.25 of final, at entry"),
    ("q4_within_025_k6", "... month 6"), ("q4_within_025_k12", "... month 12"),
    ("q4_test_raw_within_k0", "Test set, raw entry rating within ±0.25"),
    ("q4_test_adj_within_k0", "Test set, adjusted entry rating within ±0.25"),
]


def _git_commit() -> str:
    try:
        return subprocess.run(["git", "-C", str(PROJECT_ROOT), "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "n/a"


def pipeline_facts(cfg: Config) -> dict[str, dict]:
    """Pipeline-level counts (snapshots, rows, QC results) so docs never type them by hand."""
    manifest = pd.read_csv(cfg.path("manifest"))
    qc = pd.read_csv(cfg.path("qc_dir") / "qc_results.csv")
    wf = pd.read_csv(cfg.path("tables_dir") / "sample_waterfall.csv").set_index("step_no")["n_games"]
    counts = qc["status"].value_counts()
    src = "pipeline outputs"
    return {
        "n_snapshots": entry(len(manifest), "manifest", "monthly snapshot files used"),
        "n_snapshot_rows": entry(int(manifest["rows"].sum()), "manifest",
                                 "data rows over all monthly snapshots"),
        "download_mb": entry(float(manifest["bytes"].sum()) / 1e6, "manifest",
                             "size of the monthly snapshot CSVs in MB"),
        "n_games_ever_ranked": entry(int(wf[1]), "sample_waterfall", "distinct games ever ranked"),
        "n_new_releases": entry(int(wf[4]), "sample_waterfall", "games classed as new releases"),
        "n_qc_pass": entry(int(counts.get("PASS", 0)), "qc_results", "QC checks with status PASS"),
        "n_qc_warn": entry(int(counts.get("WARN", 0)), "qc_results", "QC checks with status WARN"),
        "n_qc_fail": entry(int(counts.get("FAIL", 0)), "qc_results", "QC checks with status FAIL"),
        "n_dup_rows_removed": entry(_dup_rows(cfg, qc), src, "duplicate rows removed in load"),
    }


def _dup_rows(cfg: Config, qc: pd.DataFrame) -> int:
    """Parse the load-stage duplicate count from QC check 05 ('721 rows in 16 files')."""
    value = qc.loc[qc["check_id"].astype(str).str.zfill(2) == "05", "value"].iloc[0]
    return int(str(value).split()[0])


def merge_fragments(cfg: Config) -> dict[str, dict]:
    """Union of every ``_fragments/*.json`` (later modules never overwrite earlier keys)."""
    out: dict[str, dict] = {}
    for f in sorted((results_dir(cfg) / "_fragments").glob("*.json")):
        for k, v in json.loads(f.read_text(encoding="utf-8")).items():
            if k in out:
                raise ValueError(f"duplicate key number {k!r} (also in {f.name})")
            out[k] = v
    return out


def validate(numbers: dict[str, dict]) -> list[str]:
    """Problems found: missing required keys, non-finite values, CI not bracketing the value."""
    problems = [f"missing key: {k}" for k in REQUIRED if k not in numbers]
    for k, e in numbers.items():
        v = e["value"]
        if isinstance(v, str) or v is None:
            if v is None:
                problems.append(f"{k}: value is null")
            continue
        if not math.isfinite(v):
            problems.append(f"{k}: non-finite value")
        lo, hi = e.get("ci_low"), e.get("ci_high")
        if lo is not None and hi is not None and not (lo - 1e-9 <= v <= hi + 1e-9):
            problems.append(f"{k}: value {v} outside CI [{lo}, {hi}]")
    return problems


def sanity_checks(cfg: Config, numbers: dict[str, dict]) -> pd.DataFrame:
    """Compare results with the data_notes section 11 values (report only, never enforced)."""
    s = cfg.section("analysis")["sanity"]
    rows = []
    for key, expected in s["values"].items():
        tol = s.get("loose_tolerance", {}).get(key, s["tolerance"])
        actual = numbers.get(key, {}).get("value")
        diff = None if actual is None else actual - expected
        rows.append({"key": key, "expected": expected, "actual": actual, "diff": diff,
                     "tolerance": tol,
                     "status": "MISSING" if actual is None else
                     ("OK" if abs(diff) <= tol + 1e-12 else "DIFF")})
    return pd.DataFrame(rows)


def _fmt(e: dict) -> str:
    v = e["value"]
    if isinstance(v, str):
        return v
    s = f"{v:,.0f}" if abs(v) >= 1000 or float(v).is_integer() else f"{v:.3f}"
    if e.get("ci_low") is not None and e.get("ci_high") is not None:
        s += f" [{e['ci_low']:.3f}, {e['ci_high']:.3f}]" if abs(v) < 1000 else ""
    return s


def write_summary(cfg: Config, numbers: dict[str, dict], sanity: pd.DataFrame) -> None:
    """Facts-only markdown: headline table, sanity comparison, links to every output."""
    head = pd.DataFrame([{"Quantity": label, "Value [95% CI]": _fmt(numbers[k]),
                          "n": numbers[k]["n"] if numbers[k]["n"] is not None else "-"}
                         for k, label in HEADLINE if k in numbers])
    figs = sorted(p.name for p in cfg.path("figures_dir").glob("fig*.png"))
    private = {"examples.csv"}  # game-level, git-ignored: never link it from a published report
    tables = sorted(p.name for p in cfg.path("tables_dir").glob("*.csv")
                    if p.name not in private)
    res = sorted(p.name for p in results_dir(cfg).glob("*") if p.is_file()
                 and not p.name.startswith(".")
                 and p.name not in ("key_numbers.json", "results_summary.md"))
    text = (
        "# Results summary (auto-generated, facts only)\n\n"
        "Source of truth: `reports/results/key_numbers.json`. Every number below comes from it.\n\n"
        "## Headline numbers\n\n" + md_table(head) + "\n\n"
        f"Q3 (crowdfunding): {numbers['q3_status']['value']}\n\n"
        "Not done: daily-vs-monthly snapshot robustness (needs a multi-GB download).\n\n"
        "## Comparison with data_notes section 11 sanity values\n\n"
        + md_table(sanity.assign(diff=sanity["diff"].round(4))) + "\n\n"
        "## Figures\n\n" + "\n".join(f"- [{f}](../figures/{f})" for f in figs)
        + "\n\n## Tables\n\n" + "\n".join(f"- [{t}](../tables/{t})" for t in tables)
        + "\n\n## Model and robustness outputs\n\n"
        + "\n".join(f"- [{r}]({r})" for r in res) + "\n")
    (results_dir(cfg) / "results_summary.md").write_text(text, encoding="utf-8")


def run_keynumbers(cfg: Config) -> None:
    numbers = merge_fragments(cfg)
    numbers.update(pipeline_facts(cfg))
    problems = validate(numbers)
    if problems:
        for p in problems:
            log.error(p)
        raise RuntimeError(f"{len(problems)} key-number problems; run the missing analysis steps")
    payload = {"meta": {"generated": datetime.now().astimezone().isoformat(timespec="seconds"),
                        "end_month": str(cfg.end_month), "git_commit": _git_commit()},
               "numbers": numbers}
    path = results_dir(cfg) / "key_numbers.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    sanity = sanity_checks(cfg, numbers)
    write_table(cfg, sanity, "sanity_checks", "results")
    write_summary(cfg, numbers, sanity)
    n_diff = int((sanity["status"] != "OK").sum())
    log.info("wrote %s: %d key numbers; sanity check differences: %d", Path(path).name,
             len(numbers), n_diff)
    for _, r in sanity[sanity["status"] != "OK"].iterrows():
        log.warning("sanity %s: expected %s, got %s", r["key"], r["expected"], r["actual"])
