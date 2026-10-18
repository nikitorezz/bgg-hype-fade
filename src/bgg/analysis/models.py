"""Steps 3-4: Q1 event study (game fixed effects) and Q2 cross-section (hype -> change_36)."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from linearmodels.panel import PanelOLS

from bgg import plots
from bgg.analysis.data import Inputs, main_panel, main_summary
from bgg.analysis.io import entry, md_table, results_dir, save_fragment, write_table
from bgg.analysis.stats import percentile_ci

log = logging.getLogger(__name__)

# --------------------------------------------------------------------------------------------
# Event study: fast within-estimator from per-game sufficient statistics
# --------------------------------------------------------------------------------------------


@dataclass
class EventArrays:
    """Wide per-game arrays for the event study (columns = k = 1..kmax; k = 0 is the reference)."""

    ks: np.ndarray          # 1..kmax
    P: np.ndarray           # G x kmax presence (1 if the game is observed at that k)
    B: np.ndarray           # G x kmax: y_k - ybar_g where present, 0 elsewhere
    n_obs: np.ndarray       # observations per game (including k = 0)
    game_ids: np.ndarray


def event_arrays(df: pd.DataFrame, y: str, kmax: int) -> EventArrays:
    """Pivot a long panel (game_id, k, y) into the arrays used by :func:`within_betas`."""
    wide = df.pivot(index="game_id", columns="k", values=y).reindex(columns=range(kmax + 1))
    vals = wide.to_numpy(dtype=float)
    obs = ~np.isnan(vals)
    n = obs.sum(axis=1)
    ybar = np.nansum(vals, axis=1) / n
    Y = np.where(obs[:, 1:], vals[:, 1:], 0.0)
    P = obs[:, 1:].astype(float)
    B = np.where(obs[:, 1:], Y - ybar[:, None], 0.0)
    return EventArrays(np.arange(1, kmax + 1), P, B, n, wide.index.to_numpy())


def within_betas(ea: EventArrays, weights: np.ndarray | None = None,
                 counts: np.ndarray | None = None, cluster_se: bool = False):
    """Game-FE age-dummy coefficients (absorbing game effects), optionally game-weighted.

    ``counts`` gives bootstrap multiplicities per game. With ``cluster_se`` also returns
    game-clustered standard errors (no small-sample correction).
    """
    w = np.ones(len(ea.n_obs)) if weights is None else np.asarray(weights, dtype=float)
    cw = w if counts is None else w * counts
    A = np.diag(cw @ ea.P) - ea.P.T @ ((cw / ea.n_obs)[:, None] * ea.P)
    b = cw @ ea.B
    beta = np.linalg.solve(A, b)
    if not cluster_se:
        return beta
    # score_g = b_g - A_g beta, with A_g = diag(P_g) - P_g P_g' / n_g
    Pb = ea.P @ beta
    scores = ea.B - ea.P * beta[None, :] + ea.P * (Pb / ea.n_obs)[:, None]
    scores = cw[:, None] * scores
    Ainv = np.linalg.inv(A)
    V = Ainv @ (scores.T @ scores) @ Ainv
    return beta, np.sqrt(np.diag(V))


def event_study_bootstrap(ea: EventArrays, reps: int, seed: int,
                          weights: np.ndarray | None = None) -> np.ndarray:
    """Game-level bootstrap draws of all coefficients (reps x kmax)."""
    rng = np.random.default_rng(seed)
    g = len(ea.n_obs)
    draws = np.empty((reps, len(ea.ks)))
    for r in range(reps):
        counts = np.bincount(rng.integers(0, g, g), minlength=g)
        draws[r] = within_betas(ea, weights, counts)
    return draws


def share_by(beta: np.ndarray, ks: np.ndarray, first: int, last: int) -> float:
    return beta[ks == first][0] / beta[ks == last][0]


def fit_event_study_panelols(panel: pd.DataFrame, kmax: int) -> pd.DataFrame:
    """Headline event study with linearmodels.PanelOLS (game FE, SEs clustered by game)."""
    d = panel[["game_id", "snap_month", "k", "avg_rating"]].copy()
    dummies = pd.get_dummies(d["k"], prefix="k", dtype=float).drop(columns="k_0")
    dummies = dummies[[f"k_{k}" for k in range(1, kmax + 1)]]
    data = pd.concat([d[["game_id", "snap_month", "avg_rating"]], dummies], axis=1)
    data = data.set_index(["game_id", "snap_month"]).sort_index()
    res = PanelOLS(data["avg_rating"], data.drop(columns="avg_rating"),
                   entity_effects=True).fit(cov_type="clustered", cluster_entity=True)
    ci = res.conf_int()
    return pd.DataFrame({"k": range(1, kmax + 1), "beta": res.params.to_numpy(),
                         "se": res.std_errors.to_numpy(), "ci_low": ci["lower"].to_numpy(),
                         "ci_high": ci["upper"].to_numpy(), "n_obs": int(res.nobs)})


def run_event_study(cfg, inp: Inputs) -> tuple[pd.DataFrame, dict[str, dict]]:
    a = inp.acfg
    kmax = a["curve_k_max"]
    p = main_panel(inp)
    es = fit_event_study_panelols(p, kmax)
    ea = event_arrays(p, "avg_rating", kmax)
    fast = within_betas(ea)
    diff = np.abs(fast - es["beta"].to_numpy()).max()
    log.info("event study: PanelOLS vs fast within-estimator max |diff| = %.2e", diff)
    if diff > 1e-6:
        raise RuntimeError(f"fast event-study estimator disagrees with PanelOLS ({diff:.2e})")
    zero = pd.DataFrame({"k": [0], "beta": [0.0], "se": [0.0], "ci_low": [0.0], "ci_high": [0.0],
                         "n_obs": [int(es["n_obs"].iloc[0])]})
    write_table(cfg, pd.concat([zero, es], ignore_index=True), "model_event_study", "results")
    plots.save_figure(plots.fig07_event_study(pd.concat([zero, es], ignore_index=True)),
                      "fig07_event_study", cfg.path("figures_dir"))

    draws = event_study_bootstrap(ea, a["bootstrap_reps"], a["seed"])
    keys: dict[str, dict] = {}
    n_games = len(ea.n_obs)
    for h in a["horizons"]:
        r = es[es["k"] == h].iloc[0]
        keys[f"beta_{h}"] = entry(r["beta"], "model_event_study",
                                  f"event-study coefficient at k={h} vs k=0 (game FE, "
                                  "clustered SE)",
                                  r["ci_low"], r["ci_high"], n_games)
    first, last = a["horizons"][0], a["horizons"][-1]
    sh = draws[:, first - 1] / draws[:, last - 1]
    lo, hi = percentile_ci(sh)
    keys[f"beta_share_by_{first}"] = entry(
        share_by(fast, ea.ks, first, last), "model_event_study",
        f"beta_{first} / beta_{last} (game-level bootstrap CI)", lo, hi, n_games)
    notes = (
        "# Event study notes\n\n"
        "Model: avg_rating_it = alpha_i + sum_k beta_k * 1[k_it = k] + e_it, k = 1..36, month 0 "
        "omitted. `linearmodels.PanelOLS` with game fixed effects, SEs clustered by game, on "
        f"the main sample panel ({n_games:,} games, {int(es['n_obs'].iloc[0]):,} rows).\n\n"
        "No calendar-month fixed effects: with game FE and age dummies, calendar month = entry "
        "month + age is perfectly collinear (age-period-cohort problem). Background drift is "
        "handled by the control-adjusted variant in the robustness grid.\n\n"
        + md_table(es[es["k"].isin(a["horizons"])].drop(columns="n_obs")) + "\n")
    (results_dir(cfg) / "model_event_study.md").write_text(notes, encoding="utf-8")
    return es, keys


# --------------------------------------------------------------------------------------------
# Q2: cross-section
# --------------------------------------------------------------------------------------------

SPECS = {
    "A": {"y": "change_36", "hype": "hype_log", "controls": ["avg_m0", "np.log(raters_m0)"],
          "needs": ["avg_m0", "raters_m0"],
          "why": "as proposed: change_36 on hype, controlling start level and size"},
    "B": {"y": "change_after6", "hype": "hype_log",
          "controls": ["avg_m6", "np.log(raters_m6)"], "needs": ["avg_m6", "raters_m6"],
          "why": "clean timing: change after the hype window (avg_m36 - avg_m6)"},
    "C": {"y": "change_36", "hype": "log_reach", "controls": ["avg_m0", "np.log(raters_m0)"],
          "needs": ["avg_m0", "raters_m0"],
          "why": "absolute reach ln(raters_m6) instead of relative growth"},
    "D": {"y": "change_36", "hype": "hype_log", "controls": [], "needs": [],
          "why": "no controls (entry-year FE only)"},
}


def fit_spec(df: pd.DataFrame, spec: dict, weights: str | None = None):
    """OLS with HC1 robust SEs and entry-year fixed effects for one spec; returns (result, data)."""
    rhs = " + ".join([spec["hype"], *spec["controls"], "C(entry_year)"])
    need = [spec["y"], spec["hype"], "entry_year", *spec["needs"]]
    d = df.dropna(subset=need).copy()
    if weights is None:
        res = smf.ols(f"{spec['y']} ~ {rhs}", data=d).fit(cov_type="HC1")
    else:
        res = smf.wls(f"{spec['y']} ~ {rhs}", data=d, weights=d[weights]).fit(cov_type="HC1")
    return res, d


def prepare_q2_frame(summary: pd.DataFrame) -> pd.DataFrame:
    """Add derived outcome/exposure columns used by the specs."""
    d = summary.copy()
    d["change_after6"] = d["avg_m36"] - d["avg_m6"]
    d["log_reach"] = np.log(d["raters_m6"].astype(float))
    return d


def q2_rows(df: pd.DataFrame, weights: str | None = None) -> pd.DataFrame:
    """Hype coefficient (raw + per-SD) for each spec; one row per spec."""
    rows = []
    for name, spec in SPECS.items():
        res, d = fit_spec(df, spec, weights)
        h = spec["hype"]
        sd = d[h].std()
        ci = res.conf_int().loc[h]
        rows.append({"spec": name, "outcome": spec["y"], "hype_var": h, "coef": res.params[h],
                     "se": res.bse[h], "p": res.pvalues[h], "ci_low": ci[0], "ci_high": ci[1],
                     "sd_hype": sd, "coef_per_sd": res.params[h] * sd, "se_per_sd": res.bse[h] * sd,
                     "n": int(res.nobs), "r2": res.rsquared})
    return pd.DataFrame(rows)


def _sign_line(r: pd.Series) -> str:
    sign = "positive" if r["coef"] > 0 else "negative"
    sig = "significant at 5%" if r["p"] < 0.05 else "not significant at 5%"
    return (f"- Spec {r['spec']} ({SPECS[r['spec']]['why']}): hype coefficient "
            f"{r['coef']:+.3f} (SE {r['se']:.3f}), {sign}, {sig}. H2 predicts a negative sign.")


def run_q2(cfg, inp: Inputs) -> dict[str, dict]:
    m = prepare_q2_frame(main_summary(inp))
    full = []
    for name, spec in SPECS.items():
        res, d = fit_spec(m, spec)
        sd = d[spec["hype"]].std()
        tab = pd.DataFrame({"spec": name, "term": res.params.index, "coef": res.params.to_numpy(),
                            "se": res.bse.to_numpy(), "p": res.pvalues.to_numpy(),
                            "n": int(res.nobs), "r2": res.rsquared})
        tab = tab[~tab["term"].str.startswith("C(entry_year)")]
        tab["coef_per_sd_hype"] = np.where(tab["term"] == spec["hype"], tab["coef"] * sd, np.nan)
        full.append(tab)
    long = pd.concat(full, ignore_index=True)
    write_table(cfg, long, "model_q2", "results")
    summ = q2_rows(m)

    wide = long.copy()
    wide["cell"] = wide.apply(lambda r: f"{r['coef']:+.3f} ({r['se']:.3f})"
                              + ("***" if r["p"] < .001 else "**" if r["p"] < .01
                                 else "*" if r["p"] < .05 else ""), axis=1)
    pivot = wide.pivot(index="term", columns="spec", values="cell").fillna("")
    meta = long.drop_duplicates("spec").set_index("spec")
    pivot.loc["N"] = [f"{meta.loc[s, 'n']:,}" for s in pivot.columns]
    pivot.loc["R2"] = [f"{meta.loc[s, 'r2']:.3f}" for s in pivot.columns]
    pivot = pivot.reset_index().rename(columns={"term": ""})
    qm = pd.read_csv(cfg.path("tables_dir") / "segments.csv")
    qm = qm[(qm["segment_type"] == "hype_quartile") & (qm["metric"] == "change_36")]
    text = (
        "# Q2: does hype predict the fade?\n\n"
        "OLS, HC1 robust SEs, entry-year fixed effects, main sample. Cell = coefficient (SE); "
        "stars: * p<.05, ** p<.01, *** p<.001. H2 predicts a **negative** hype coefficient.\n\n"
        + md_table(pivot) + "\n\n## Hype coefficient per 1 SD of the exposure\n\n"
        + md_table(summ[["spec", "coef", "se", "p", "coef_per_sd", "se_per_sd", "n"]]) + "\n\n"
        "## Sign and significance\n\n" + "\n".join(_sign_line(r) for _, r in summ.iterrows())
        + "\n\n## Quartile means of change_36 (from segments.csv)\n\n"
        + md_table(qm[["segment_value", "mean", "ci_low", "ci_high", "n"]]) + "\n")
    (results_dir(cfg) / "model_q2.md").write_text(text, encoding="utf-8")

    keys: dict[str, dict] = {}
    for _, r in summ.iterrows():
        s = r["spec"].lower()
        keys[f"spec_{s}_hype"] = entry(
            r["coef"], "model_q2", f"Spec {r['spec']}: {SPECS[r['spec']]['why']}; raw coefficient "
            f"on {r['hype_var']}", r["ci_low"], r["ci_high"], r["n"])
        keys[f"spec_{s}_hype_per_sd"] = entry(
            r["coef_per_sd"], "model_q2",
            f"Spec {r['spec']}: coefficient per 1 SD of {r['hype_var']}",
            r["coef_per_sd"] - 1.96 * r["se_per_sd"], r["coef_per_sd"] + 1.96 * r["se_per_sd"],
            r["n"])
        keys[f"spec_{s}_hype_p"] = entry(r["p"], "model_q2",
                                         f"Spec {r['spec']}: p-value of the hype coefficient",
                                         n=r["n"])
    return keys


def run_models(cfg, inp: Inputs | None = None) -> None:
    from bgg.analysis.data import load_inputs
    inp = inp or load_inputs(cfg)
    _, keys = run_event_study(cfg, inp)
    keys.update(run_q2(cfg, inp))
    save_fragment(cfg, "models", keys)
