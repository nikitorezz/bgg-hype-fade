"""Orchestrates the analysis steps (``bgg analysis [--only ...]``)."""

from __future__ import annotations

import importlib
import logging

from bgg.analysis.data import load_inputs
from bgg.config import Config

log = logging.getLogger(__name__)

# step name -> (module, function); order matters (key numbers last)
STEPS: dict[str, tuple[str, str]] = {
    "descriptives": ("bgg.analysis.descriptives", "run_descriptives"),
    "models": ("bgg.analysis.models", "run_models"),
    "predictive": ("bgg.analysis.predictive", "run_predictive"),
    "robustness": ("bgg.analysis.robustness", "run_robustness"),
    "crowdfunding": ("bgg.analysis.crowdfunding", "run_crowdfunding"),
    "keynumbers": ("bgg.analysis.keynumbers", "run_keynumbers"),
}


def run_analysis(cfg: Config, only: str | None = None) -> int:
    """Run every analysis step (or just ``only``); returns a process exit code."""
    names = [only] if only else list(STEPS)
    inp = None if names == ["keynumbers"] else load_inputs(cfg)
    for name in names:
        module, func = STEPS[name]
        log.info("=== analysis: %s ===", name)
        fn = getattr(importlib.import_module(module), func)
        if name == "keynumbers":
            fn(cfg)
        else:
            fn(cfg, inp)
    return 0
