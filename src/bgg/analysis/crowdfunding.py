"""Step 8 (optional) Q3: does a crowdfunded launch change the fade? Needs the Kaggle games.csv."""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from bgg import plots
from bgg.analysis.data import Inputs, main_summary
from bgg.analysis.io import entry, md_table, results_dir, save_fragment, write_table
from bgg.analysis.stats import mean_ci
from bgg.analysis.titles import figure_titles

log = logging.getLogger(__name__)

STATUS_KEY = "q3_status"


def _skip(cfg, reason: str) -> None:
    log.warning("Q3 skipped: %s", reason)
    save_fragment(cfg, "crowdfunding", {STATUS_KEY: entry(
        f"skipped: {reason}", "crowdfunding", "whether the optional Q3 analysis ran")})


def load_kaggle(cfg) -> pd.DataFrame | None:
    """Read games.csv (id + flag), verifying the expected columns; None if unavailable."""
    q3 = cfg.section("analysis")["q3"]
    path = cfg.root / cfg.section("analysis")["external_dir"] / "games.csv"
    if not path.exists():
        return None
    header = pd.read_csv(path, nrows=0).columns.tolist()
    missing = [c for c in (q3["id_column"], q3["flag_column"]) if c not in header]
    if missing:
        raise ValueError(f"{path}: expected columns {missing} not found; header = {header[:12]}")
    df = pd.read_csv(path, usecols=[q3["id_column"], q3["flag_column"]])
    df.columns = ["game_id", "kickstarted"]
    if df["game_id"].duplicated().any():
        raise ValueError("games.csv has duplicate ids")
    return df


def _kickstarter_bands(cfg, inp: Inputs, d: pd.DataFrame) -> dict[str, dict]:
    """Starting-rating comparison and within-band change gap (Kickstarted minus not); Fig 10."""
    kc = inp.acfg["kickstarter"]
    z = inp.z
    keys: dict[str, dict] = {}
    for flag, name in ((1, "ks_avg_m0"), (0, "nonks_avg_m0")):
        r = mean_ci(d.loc[d["kickstarted"] == flag, "avg_m0"], z)
        keys[name] = entry(r["mean"], "model_q3",
                           f"mean starting average, Kickstarted = {flag} (Q3 sample)",
                           r["ci_low"], r["ci_high"], r["n"])
    raw = {"ks": d.loc[d["kickstarted"] == 1, "change_36"].mean(),
           "other": d.loc[d["kickstarted"] == 0, "change_36"].mean()}  # full Q3 sample
    edges = np.arange(kc["band_start"], kc["band_end"] + 1e-9, kc["band_width"])
    d = d.assign(band=pd.cut(d["avg_m0"], edges, right=False)).dropna(subset=["band"])
    rows = []
    for (band, flag), g in d.groupby(["band", "kickstarted"], observed=True):
        r = mean_ci(g["change_36"], z)
        rows.append({"kickstarted": int(flag), "band_low": band.left, "band_high": band.right,
                     "band_mid": (band.left + band.right) / 2, "mean": r["mean"], "se": r["se"],
                     "ci_low": r["ci_low"], "ci_high": r["ci_high"], "n": r["n"]})
    bands = pd.DataFrame(rows)
    write_table(cfg, bands, "kickstarter_by_band")
    wide = bands.pivot(index="band_low", columns="kickstarted", values=["mean", "se", "n"])
    ok = wide.dropna()
    gaps = ok[("mean", 1)] - ok[("mean", 0)]
    size = ok[("n", 1)] + ok[("n", 0)]
    w = size / size.sum()
    var = ok[("se", 1)] ** 2 + ok[("se", 0)] ** 2
    gap = float((w * gaps).sum())
    se = float(np.sqrt((w ** 2 * var).sum()))
    keys["ks_gap_within_bands"] = entry(
        gap, "kickstarter_by_band", "mean of (Kickstarted - other) change_36 across 0.5-wide "
        "starting-average bands, weighted by band size", gap - z * se, gap + z * se,
        int(size.sum()))
    big = ok[(ok[("n", 1)] >= kc["min_band_n"]) & (ok[("n", 0)] >= kc["min_band_n"])]
    bg = big[("mean", 1)] - big[("mean", 0)]
    keys["ks_gap_band_min"] = entry(bg.min(), "kickstarter_by_band",
                                    f"smallest per-band gap among bands with >= {kc['min_band_n']} "
                                    "games in each group")
    keys["ks_gap_band_max"] = entry(bg.max(), "kickstarter_by_band",
                                    "largest per-band gap (same bands)")
    fig = plots.add_titles(plots.fig10_kickstarter(bands, raw), *figure_titles(cfg, "fig10", keys))
    plots.save_figure(fig, "fig10_kickstarter", cfg.path("figures_dir"))
    return keys


def run_crowdfunding(cfg, inp: Inputs | None = None) -> None:
    from bgg.analysis.data import load_inputs
    kag = load_kaggle(cfg)
    if kag is None:
        _skip(cfg, "data not provided")
        return
    inp = inp or load_inputs(cfg)
    q3 = inp.acfg["q3"]
    m = main_summary(inp).merge(kag, on="game_id", how="left")
    m["covered"] = m["kickstarted"].notna()

    cov = m.groupby("entry_year").agg(n_main_sample=("game_id", "size"),
                                      n_matched=("covered", "sum"),
                                      n_kickstarted=("kickstarted", lambda s: int((s == 1).sum())))
    cov["coverage"] = cov["n_matched"] / cov["n_main_sample"]
    cov["share_kickstarted_of_matched"] = cov["n_kickstarted"] / cov["n_matched"].replace(0, np.nan)
    cov["modelled"] = cov["coverage"] >= q3["min_coverage"]
    cov = cov.reset_index()
    write_table(cfg, cov, "q3_coverage")
    years = cov.loc[cov["modelled"], "entry_year"].tolist()
    log.info("Q3 coverage by entry year: %s; modelled years %s",
             dict(zip(cov["entry_year"], cov["coverage"].round(3), strict=True)), years)

    keys: dict[str, dict] = {}
    if not years:
        keys[STATUS_KEY] = entry("coverage only: no entry year reaches the coverage threshold",
                                 "q3_coverage", "whether the optional Q3 analysis ran")
        save_fragment(cfg, "crowdfunding", keys)
        return

    d = m[m["entry_year"].isin(years) & m["covered"]].dropna(
        subset=["hype_log", "avg_m0", "raters_m0", "change_36"]).copy()
    d["kickstarted"] = d["kickstarted"].astype(int)
    d["ln_raters_m0"] = np.log(d["raters_m0"].astype(float))
    rows, fits = [], {}
    for name, rhs in {"A (baseline)": "hype_log + avg_m0 + ln_raters_m0",
                      "A + kickstarted": "hype_log + kickstarted + avg_m0 + ln_raters_m0",
                      "A + kickstarted x hype": "hype_log * kickstarted + avg_m0 + ln_raters_m0"
                      }.items():
        res = smf.ols(f"change_36 ~ {rhs} + C(entry_year)", data=d).fit(cov_type="HC1")
        fits[name] = res
        for term in res.params.index:
            if term.startswith("C(entry_year)"):
                continue
            rows.append({"model": name, "term": term, "coef": res.params[term],
                         "se": res.bse[term], "p": res.pvalues[term], "n": int(res.nobs),
                         "r2": res.rsquared})
    out = pd.DataFrame(rows)
    write_table(cfg, out, "model_q3", "results")
    grp = pd.DataFrame([{"kickstarted": k, **mean_ci(g["change_36"], inp.z)}
                        for k, g in d.groupby("kickstarted")])
    write_table(cfg, grp, "q3_change_by_kickstarted")
    (results_dir(cfg) / "model_q3.md").write_text(
        "# Q3: crowdfunded launches (optional)\n\n"
        "Source: Kaggle *Board Game Database from BoardGameGeek* (threnjen, CC BY-SA 3.0), a "
        f"January 2022 snapshot, so only entry years with at least {100 * q3['min_coverage']:.0f}% "
        f"coverage are modelled: {years}. The `Kickstarted` flag is the dataset's own binary "
        "variable, taken as given (as of 2022, not at launch).\n\n"
        "## Coverage of the main sample\n\n" + md_table(cov) + "\n\n"
        "## Mean change_36 by flag (covered games, modelled years)\n\n" + md_table(grp) + "\n\n"
        "## Regressions (change_36, HC1 SEs, entry-year FE)\n\n" + md_table(out) + "\n",
        encoding="utf-8")

    keys[STATUS_KEY] = entry(f"ran on entry years {years}", "q3_coverage",
                             "whether the optional Q3 analysis ran", n=len(d))
    keys["q3_share_kickstarted"] = entry(
        float(d["kickstarted"].mean()), "q3_coverage", "share of covered main-sample games flagged "
        "Kickstarted (modelled entry years)", n=len(d))
    k_res = fits["A + kickstarted"]
    i_res = fits["A + kickstarted x hype"]
    for key, res, term, desc in [
        ("q3_kickstarted_coef", k_res, "kickstarted", "Spec A + kickstarted: coefficient on flag"),
        ("q3_hype_coef_with_kickstarted", k_res, "hype_log",
         "Spec A + kickstarted: hype coefficient"),
        ("q3_interaction_coef", i_res, "hype_log:kickstarted",
         "interaction hype_log x kickstarted")]:
        ci = res.conf_int().loc[term]
        keys[key] = entry(res.params[term], "model_q3", desc, ci[0], ci[1], int(res.nobs))
        keys[key + "_p"] = entry(res.pvalues[term], "model_q3", f"p-value: {desc}",
                                 n=int(res.nobs))
    for _, r in grp.iterrows():
        keys[f"q3_change_36_kickstarted_{int(r['kickstarted'])}"] = entry(
            r["mean"], "q3_change_by_kickstarted",
            f"mean change_36 where Kickstarted = {int(r['kickstarted'])}", r["ci_low"],
            r["ci_high"], r["n"])
    keys.update(_kickstarter_bands(cfg, inp, d))
    save_fragment(cfg, "crowdfunding", keys)
