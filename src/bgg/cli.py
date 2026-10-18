"""Command-line entry point: ``bgg download|load|cohorts|panel|qc|all``."""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Callable

from bgg.config import Config, load_config

log = logging.getLogger("bgg")

STAGES = ["download", "load", "cohorts", "panel", "qc"]
ANALYSIS_STEPS = ["descriptives", "models", "predictive", "robustness", "crowdfunding",
                  "keynumbers"]


def _run_stage(name: str, cfg: Config, args: argparse.Namespace) -> int:
    """Run one stage; returns a process exit code."""
    log.info("=== stage: %s ===", name)
    if name == "download":
        from bgg.download import run_download

        run_download(cfg, backend=args.backend)
    elif name in ("load", "cohorts", "panel"):
        from bgg.build import run_sql_stage

        run_sql_stage(cfg, name)
    elif name == "qc":
        from bgg.qc import run_qc

        return run_qc(cfg)
    elif name == "analysis":
        from bgg.analysis.run import run_analysis

        return run_analysis(cfg, only=args.only)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="bgg", description="BGG Hype Fade data pipeline")
    p.add_argument("--config", default=None, help="path to config.yaml (default: project root)")
    p.add_argument("--log-level", default="INFO", help="DEBUG, INFO, WARNING ...")
    sub = p.add_subparsers(dest="stage", required=True)
    help_text: dict[str, str] = {
        "download": "select and download monthly snapshots, write manifest",
        "load": "load manifest files into DuckDB, dedup, export parquet",
        "cohorts": "entry months, cohort flags, waterfall",
        "panel": "monthly panel, new-rating average, game summary",
        "qc": "quality checks and report",
        "all": "run every pipeline stage in order",
        "analysis": "run the analysis (figures, models, key numbers)",
        "everything": "pipeline stages followed by the analysis",
    }
    for name, h in help_text.items():
        sp = sub.add_parser(name, help=h)
        if name in ("download", "all"):
            sp.add_argument("--backend", choices=["http", "git"], default=None,
                            help="override download.backend from config")
        if name == "everything":
            sp.add_argument("--backend", choices=["http", "git"], default=None,
                            help="override download.backend from config")
        if name == "analysis":
            sp.add_argument("--only", default=None, choices=ANALYSIS_STEPS,
                            help="run a single analysis step")
    return p


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=args.log_level.upper(),
                        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
                        datefmt="%H:%M:%S")
    cfg = load_config(args.config)
    stages = {"all": STAGES, "everything": [*STAGES, "analysis"]}.get(args.stage, [args.stage])
    args.only = getattr(args, "only", None)
    run: Callable[[str], int] = lambda s: _run_stage(s, cfg, args)  # noqa: E731
    code = 0
    for s in stages:
        code = run(s)
        if code:
            log.error("stage '%s' failed with exit code %d", s, code)
            break
    sys.exit(code)


if __name__ == "__main__":
    main()
