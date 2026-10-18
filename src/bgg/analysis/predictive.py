"""Step 5 (Q4): when can you trust a new game's rating, and can an adjusted launch rating help?"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
import statsmodels.api as sm

from bgg import plots
from bgg.analysis.data import Inputs, main_panel, main_summary
from bgg.analysis.io import entry, md_table, results_dir, save_fragment, write_table
from bgg.analysis.stats import percentile_ci
from bgg.analysis.titles import figure_titles

log = logging.getLogger(__name__)


def _wide(inp: Inputs, value: str) -> pd.DataFrame:
    """Main-sample games x k matrix of ``value`` (NaN where the month is unobserved)."""
    p = main_panel(inp)
    return p.pivot(index="game_id", columns="k", values=value).sort_index()


def accuracy_table(inp: Inputs) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    """MAE and share within each tolerance of the month-36 average, by k (long format).

    Games count at k when both the k-month and the 36-month averages are observed.
    Returns (table, within[tol] arrays stacked as G x K x T bool, observed G x K bool).
    """
    q = inp.acfg["q4"]
    last = inp.acfg["horizons"][-1]
    A = _wide(inp, "avg_rating")
    ks = list(range(q["k_max"] + 1))
    target = A[last].to_numpy()
    X = A[ks].to_numpy()
    obs = ~np.isnan(X) & ~np.isnan(target)[:, None]
    err = np.abs(X - target[:, None])
    within = np.stack([(err <= t) & obs for t in q["tolerances"]], axis=2)
    rows = []
    for j, k in enumerate(ks):
        n = int(obs[:, j].sum())
        for ti, t in enumerate(q["tolerances"]):
            share = within[:, j, ti].sum() / n
            se = np.sqrt(share * (1 - share) / n)
            rows.append({"k": k, "tolerance": t, "share_within": share,
                         "ci_low": share - inp.z * se, "ci_high": share + inp.z * se,
                         "mae": float(np.nanmean(err[obs[:, j], j])), "n": n})
    return pd.DataFrame(rows), within, obs


def rule_k(share: np.ndarray, threshold: float) -> float:
    """First k whose share reaches ``threshold`` (NaN if never)."""
    hit = np.where(share >= threshold)[0]
    return float(hit[0]) if len(hit) else float("nan")


def bootstrap_rule(within_t: np.ndarray, obs: np.ndarray, threshold: float, reps: int,
                   seed: int) -> np.ndarray:
    """Game-level bootstrap draws of the rule month. ``within_t`` is G x K bool."""
    rng = np.random.default_rng(seed)
    g = within_t.shape[0]
    w, o = within_t.astype(float), obs.astype(float)
    out = np.empty(reps)
    for r in range(reps):
        c = np.bincount(rng.integers(0, g, g), minlength=g).astype(float)
        out[r] = rule_k((c @ w) / (c @ o), threshold)
    return out


def adjusted_predictor(inp: Inputs) -> pd.DataFrame:
    """Raw vs adjusted launch rating: train on early entry years, evaluate on later ones."""
    q = inp.acfg["q4"]
    last = inp.acfg["horizons"][-1]
    m = main_summary(inp)
    (tr_lo, tr_hi), (te_lo, te_hi) = q["train_entry_years"], q["test_entry_years"]
    train = m[m["entry_year"].between(tr_lo, tr_hi)]
    test = m[m["entry_year"].between(te_lo, te_hi)]
    target = f"avg_m{last}"
    rows = []
    for k in q["adjusted_ks"]:
        def feats(d: pd.DataFrame, k=k) -> pd.DataFrame:
            f = pd.DataFrame({"avg_k": d[f"avg_m{k}"], "ln_raters_k": np.log(
                d[f"raters_m{k}"].astype(float))})
            if k > 0:  # at k=0 the growth term is the constant ln 2
                f["ln_growth"] = np.log(d[f"raters_m{k}"].astype(float)
                                        / d["raters_m0"].astype(float) + 1)
            return f
        ftr, fte = feats(train), feats(test)
        ok_tr = ftr.notna().all(axis=1) & train[target].notna()
        ok_te = fte.notna().all(axis=1) & test[target].notna()
        fit = sm.OLS(train.loc[ok_tr, target], sm.add_constant(ftr[ok_tr])).fit()
        pred = fit.predict(sm.add_constant(fte[ok_te], has_constant="add"))
        y = test.loc[ok_te, target]
        raw_err = (fte.loc[ok_te, "avg_k"] - y).abs()
        adj_err = (pred - y).abs()
        row = {"k": k, "n_train": int(ok_tr.sum()), "n_test": int(ok_te.sum()),
               "raw_mae": raw_err.mean(), "adj_mae": adj_err.mean()}
        for t in q["tolerances"]:
            row[f"raw_within_{t}"] = (raw_err <= t).mean()
            row[f"adj_within_{t}"] = (adj_err <= t).mean()
        for name, v in fit.params.items():
            row[f"coef_{name}"] = v
        rows.append(row)
    return pd.DataFrame(rows)


def run_predictive(cfg, inp: Inputs | None = None) -> None:
    from bgg.analysis.data import load_inputs
    inp = inp or load_inputs(cfg)
    q, a = inp.acfg["q4"], inp.acfg
    acc, within, obs = accuracy_table(inp)
    write_table(cfg, acc, "q4_accuracy_by_k")
    tol, thr = q["rule_tolerance"], q["rule_share"]
    ti = q["tolerances"].index(tol)
    share = acc[acc["tolerance"] == tol].sort_values("k")["share_within"].to_numpy()
    k_rule = rule_k(share, thr)
    draws = bootstrap_rule(within[:, :, ti], obs, thr, a["bootstrap_reps"], a["seed"])
    lo, hi = percentile_ci(draws)
    n_never = int(np.isnan(draws).sum())
    log.info("Q4 rule: month %s (bootstrap CI %.0f-%.0f; %d draws never reach it)", k_rule, lo, hi,
             n_never)

    adj = adjusted_predictor(inp)
    write_table(cfg, adj, "q4_adjusted_predictor")
    (results_dir(cfg) / "q4_notes.md").write_text(
        "# Q4: when can you trust a new game's rating?\n\n"
        f"Rule: first month k where at least {100 * thr:.0f}% of main-sample games have a "
        "displayed "
        f"average within ±{tol} of their month-36 average: **month {k_rule:.0f}** "
        f"(bootstrap 95% CI {lo:.0f}-{hi:.0f}).\n\n"
        "Caveat: agreement at large k is partly mechanical. The running average at k=24 already "
        "contains most of the raters that make up the month-36 average.\n\n"
        "## Adjusted launch rating (train on entry years "
        f"{q['train_entry_years'][0]}-{q['train_entry_years'][1]}, test on "
        f"{q['test_entry_years'][0]}-{q['test_entry_years'][1]})\n\n"
        "Model: avg_m36 ~ avg_k + ln(raters_k) + ln(raters_k / raters_0 + 1) (growth term dropped "
        "at k=0, where it is constant).\n\n"
        + md_table(adj[["k", "n_train", "n_test", "raw_mae", "adj_mae"]
                       + [c for c in adj.columns if "within" in c]]) + "\n", encoding="utf-8")

    keys: dict[str, dict] = {}
    keys["q4_rule_month"] = entry(
        k_rule, "q4_accuracy_by_k",
        f"first k with >= {100 * thr:.0f}% of games within ±{tol} of their month-36 average "
        "(game-level bootstrap CI)", lo, hi, len(within))
    at_rule = acc[(acc["tolerance"] == tol) & (acc["k"] == k_rule)]
    if len(at_rule):
        r = at_rule.iloc[0]
        keys["q4_share_at_rule_month"] = entry(r["share_within"], "q4_accuracy_by_k",
                                               "share within tolerance at the rule month",
                                               r["ci_low"], r["ci_high"], r["n"])
    for k in sorted({0, 3, 6, 12, 18, 24, *a["q4"]["adjusted_ks"]}):
        for t in q["tolerances"]:
            r = acc[(acc["tolerance"] == t) & (acc["k"] == k)].iloc[0]
            tag = f"{t:.2f}".replace(".", "")
            keys[f"q4_within_{tag}_k{k}"] = entry(
                r["share_within"], "q4_accuracy_by_k",
                f"share of games with |avg at k={k} - avg at month 36| <= {t}", r["ci_low"],
                r["ci_high"], r["n"])
        keys[f"q4_mae_k{k}"] = entry(r["mae"], "q4_accuracy_by_k",
                                     f"mean absolute error of avg at k={k} vs month-36 avg",
                                     n=r["n"])
    for _, r in adj.iterrows():
        k = int(r["k"])
        for kind in ("raw", "adj"):
            keys[f"q4_test_{kind}_mae_k{k}"] = entry(
                r[f"{kind}_mae"], "q4_adjusted_predictor",
                f"test-set MAE vs month-36 average, {kind} predictor at k={k}", n=r["n_test"])
            t = q["rule_tolerance"]
            keys[f"q4_test_{kind}_within_k{k}"] = entry(
                r[f"{kind}_within_{t}"], "q4_adjusted_predictor",
                f"test-set share within ±{t}, {kind} predictor at k={k}", n=r["n_test"])
    for _, r in adj.iterrows():  # model coefficients, applied by the dashboard extract
        for col in [c for c in adj.columns if c.startswith("coef_")]:
            if not np.isnan(r[col]):
                keys[f"q4_adj_{col}_k{int(r['k'])}"] = entry(
                    r[col], "q4_adjusted_predictor",
                    f"adjusted-predictor OLS coefficient ({col[5:]}) at k={int(r['k'])}, "
                    "trained on "
                    f"entry years {q['train_entry_years'][0]}-{q['train_entry_years'][1]}")
    fig8 = plots.add_titles(plots.fig08_when_to_trust(
        acc, {"k": k_rule, "ci_low": lo, "ci_high": hi}, tol, thr), *figure_titles(
        cfg, "fig08", keys))
    plots.save_figure(fig8, "fig08_when_to_trust", cfg.path("figures_dir"))
    save_fragment(cfg, "predictive", keys)
