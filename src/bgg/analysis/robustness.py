"""Step 6: robustness grid (samples, weights, adjustments) and gap-threshold sensitivity."""

from __future__ import annotations

import logging
import re

import numpy as np
import pandas as pd

from bgg.analysis.data import (
    Inputs,
    control_change,
    control_lookup,
    control_series,
    main_summary,
)
from bgg.analysis.io import entry, md_table, results_dir, save_fragment, write_table
from bgg.analysis.models import (
    SPECS,
    event_arrays,
    event_study_bootstrap,
    fit_spec,
    prepare_q2_frame,
    within_betas,
)
from bgg.analysis.stats import mean_ci, percentile_ci

log = logging.getLogger(__name__)

COLUMNS = ["variant", "n_games", "beta_12", "beta_12_se", "beta_36", "beta_36_se", "share_by_12",
           "share_ci_low", "share_ci_high", "hype_a", "hype_a_se", "hype_b", "hype_b_se",
           "n_hype_models"]


def evaluate_variant(inp: Inputs, label: str, ids: np.ndarray, weight_col: str | None = None,
                     control_lookup_: dict | None = None, hype: bool = True) -> dict:
    """Event-study beta12/36 and Spec A/B hype coefficients for one sample/weighting variant."""
    a = inp.acfg
    kmax, (h1, _, h3) = a["curve_k_max"], a["horizons"]
    s = prepare_q2_frame(inp.summary[inp.summary["game_id"].isin(ids)])
    p = inp.panel[inp.panel["game_id"].isin(ids)].copy()
    p["y"] = p["avg_rating"]
    if control_lookup_ is not None:
        p["y"] -= p["snap_month"].dt.date.map(control_lookup_)
        s["change_36"] -= control_change(control_lookup_, s["entry_month"], 0, 36)
        s["change_after6"] -= control_change(control_lookup_, s["entry_month"], 6, 36)
    ea = event_arrays(p, "y", kmax)
    w = None
    if weight_col is not None:
        w = s.set_index("game_id").loc[ea.game_ids, weight_col].to_numpy()
    beta, se = within_betas(ea, w, cluster_se=True)
    draws = event_study_bootstrap(ea, a["bootstrap_reps"], a["seed"], w)
    sh = draws[:, h1 - 1] / draws[:, h3 - 1]
    lo, hi = percentile_ci(sh)
    row = {"variant": label, "n_games": len(ea.n_obs), "beta_12": beta[h1 - 1],
           "beta_12_se": se[h1 - 1], "beta_36": beta[h3 - 1], "beta_36_se": se[h3 - 1],
           "share_by_12": beta[h1 - 1] / beta[h3 - 1], "share_ci_low": lo, "share_ci_high": hi}
    if hype:
        for name in ("A", "B"):
            res, d = fit_spec(s, SPECS[name], weight_col)
            h = SPECS[name]["hype"]
            row[f"hype_{name.lower()}"], row[f"hype_{name.lower()}_se"] = res.params[h], res.bse[h]
            row["n_hype_models"] = int(res.nobs)
    return row


def robustness_grid(inp: Inputs) -> pd.DataFrame:
    """All variants of the robustness table (baseline first)."""
    cfg_r = inp.acfg["robustness"]
    m = main_summary(inp)
    series, _ = control_series(inp.cfg)
    look = control_lookup(series)
    rows = [evaluate_variant(inp, "1 Baseline (main sample)", inp.main_ids)]
    rows.append(evaluate_variant(inp, "2 Rater-weighted (weights = raters_m36)", inp.main_ids,
                                 weight_col="raters_m36"))
    covid = cfg_r["covid_entry_years"]
    rows.append(evaluate_variant(
        inp, f"3 Excluding {covid[0]}-{covid[-1]} entry cohorts",
        m.loc[~m["entry_year"].between(covid[0], covid[-1]), "game_id"].to_numpy()))
    cut = m["raters_m36"].quantile(1 - cfg_r["popular_top_share"])
    top = int(100 * cfg_r["popular_top_share"])
    rows.append(evaluate_variant(inp, f"4a Popular only (top {top}% raters_m36)",
                                 m.loc[m["raters_m36"] >= cut, "game_id"].to_numpy()))
    rows.append(evaluate_variant(inp, f"4b Rest (below top {top}%)",
                                 m.loc[m["raters_m36"] < cut, "game_id"].to_numpy()))
    rows.append(evaluate_variant(
        inp, f"5 Entered with >= {cfg_r['min_entry_raters']} raters",
        m.loc[m["raters_m0"] >= cfg_r["min_entry_raters"], "game_id"].to_numpy()))
    rows.append(evaluate_variant(inp, "6 Control-adjusted outcome", inp.main_ids,
                                 control_lookup_=look))
    unbalanced = inp.summary["game_id"].to_numpy()
    rows.append(evaluate_variant(inp, "7 Unbalanced: all new releases (event study only)",
                                 unbalanced, hype=False))
    return pd.DataFrame(rows)[COLUMNS]


def gap_sensitivity(inp: Inputs) -> pd.DataFrame:
    """Mean new-vs-displayed gap at chosen k under alternative usability thresholds."""
    r = inp.acfg["robustness"]
    lo, hi = inp.cfg.section("new_rating_average")["valid_range"]
    w = inp.acfg["gap"]["window"]
    p = inp.panel[inp.panel["game_id"].isin(inp.main_ids)]
    p = p[p[f"prev_n_{w}"].notna()]
    rows = []
    for md in r["gap_min_delta_raters"]:
        for me in r["gap_max_error_bound"]:
            ok = p[(p[f"delta_raters_{w}"] >= md) & (p[f"new_avg_err_{w}"] <= me)
                   & p[f"new_avg_{w}"].between(lo, hi)]
            for k in r["gap_ks"]:
                g = (ok.loc[ok["k"] == k, f"new_avg_{w}"] - ok.loc[ok["k"] == k, "avg_rating"])
                st = mean_ci(g, inp.z)
                rows.append({"min_delta_raters": md, "max_error_bound": me, "k": k,
                             "mean_gap": st["mean"], "ci_low": st["ci_low"],
                             "ci_high": st["ci_high"], "n": st["n"],
                             "share_usable": st["n"] / (p["k"] == k).sum()})
    return pd.DataFrame(rows)


def run_robustness(cfg, inp: Inputs | None = None) -> None:
    from bgg.analysis.data import load_inputs
    inp = inp or load_inputs(cfg)
    grid = robustness_grid(inp)
    write_table(cfg, grid, "robustness", "results")
    gap = gap_sensitivity(inp)
    write_table(cfg, gap, "robustness_gap", "results")
    nra = inp.cfg.section("new_rating_average")
    base = gap[(gap["min_delta_raters"] == nra["min_delta_raters"])
               & (gap["max_error_bound"] == nra["max_error_bound"])]
    (results_dir(cfg) / "robustness.md").write_text(
        "# Robustness grid\n\nEvent-study betas use game FE with game-clustered SEs; hype "
        "coefficients are Specs A and B (HC1, entry-year FE). share_by_12 = beta_12 / beta_36 "
        "with a game-level bootstrap CI. Variant 7 is event study only. Daily-vs-monthly "
        "snapshots were not run (needs a multi-GB download).\n\n" + md_table(grid)
        + "\n\n## Gap sensitivity (new_avg_3 - avg_rating, equal weight per row)\n\n"
        "Baseline thresholds are the config values; mean_gap at k = 6 / 12 / 36 under each "
        "combination.\n\n" + md_table(gap.drop(columns=["ci_low", "ci_high"])) + "\n",
        encoding="utf-8")
    keys: dict[str, dict] = {}
    for _, r in grid.iterrows():
        slug = re.sub(r"[^a-z0-9]+", "_", r["variant"].lower()).strip("_")
        n = int(r["n_games"])
        keys[f"robust_{slug}_beta_36"] = entry(r["beta_36"], "robustness",
                                               f"event-study beta_36, variant: {r['variant']}",
                                               r["beta_36"] - 1.96 * r["beta_36_se"],
                                               r["beta_36"] + 1.96 * r["beta_36_se"], n)
        keys[f"robust_{slug}_share_by_12"] = entry(
            r["share_by_12"], "robustness", f"beta_12 / beta_36, variant: {r['variant']}",
            r["share_ci_low"], r["share_ci_high"], n)
        for s in ("a", "b"):
            if not np.isnan(r[f"hype_{s}"]):
                keys[f"robust_{slug}_hype_{s}"] = entry(
                    r[f"hype_{s}"], "robustness", f"Spec {s.upper()} hype coefficient, variant: "
                    f"{r['variant']}", r[f"hype_{s}"] - 1.96 * r[f"hype_{s}_se"],
                    r[f"hype_{s}"] + 1.96 * r[f"hype_{s}_se"], r["n_hype_models"])
    for _, r in base.iterrows():
        keys[f"gap_sensitivity_baseline_k{int(r['k'])}"] = entry(
            r["mean_gap"], "robustness_gap", "mean gap at config thresholds (matches Fig 2)",
            r["ci_low"], r["ci_high"], r["n"])
    save_fragment(cfg, "robustness", keys)
