"""Steps 1-2: headline descriptives (Figs 1-6, Table 1) and segment cuts."""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from bgg import plots
from bgg.analysis.data import (
    Inputs,
    balanced_summary,
    control_change,
    control_lookup,
    control_series,
    main_panel,
    main_summary,
)
from bgg.analysis.io import entry, md_table, save_fragment, write_table
from bgg.analysis.stats import (
    bootstrap_indices,
    group_mean_ci,
    mean_ci,
    percentile_ci,
    weighted_mean,
)

log = logging.getLogger(__name__)


def curve_overall(inp: Inputs) -> pd.DataFrame:
    """Mean change in displayed average (d_rating) by k on the main sample."""
    return group_mean_ci(main_panel(inp), "k", "d_rating", inp.z)


def share_of_decline(inp: Inputs, first: int, last: int) -> dict[str, float]:
    """Mean change at ``first`` / mean change at ``last`` on the balanced sample, bootstrap CI."""
    b = balanced_summary(inp)
    a, c = b[f"change_{first}"].to_numpy(), b[f"change_{last}"].to_numpy()
    point = a.mean() / c.mean()
    draws = [a[i].mean() / c[i].mean()
             for i in bootstrap_indices(len(b), inp.acfg["bootstrap_reps"], inp.acfg["seed"])]
    lo, hi = percentile_ci(np.array(draws))
    return {"value": point, "ci_low": lo, "ci_high": hi, "n": len(b)}


def gap_table(inp: Inputs) -> pd.DataFrame:
    """New-rater average minus displayed average, computed row-wise, by k (equal weight per row).

    Never compare a weighted mean of new_avg with an unweighted mean of avg_rating (data_notes 11).
    """
    w = inp.acfg["gap"]["window"]
    p = main_panel(inp)
    p = p[p[f"prev_n_{w}"].notna()]
    ok = p[p[f"new_avg_ok_{w}"]].copy()
    ok["gap"] = ok[f"new_avg_{w}"] - ok["avg_rating"]
    t = group_mean_ci(ok, "k", "gap", inp.z)
    wmean = ok.groupby("k").apply(lambda g: weighted_mean(g["gap"], g[f"delta_raters_{w}"]),
                                  include_groups=False)
    t["mean_delta_weighted"] = t["k"].map(wmean)
    t["rows_with_lag"] = t["k"].map(p.groupby("k").size())
    t["share_usable"] = t["n"] / t["rows_with_lag"]
    return t


def curve_by_entry_year(inp: Inputs) -> pd.DataFrame:
    return group_mean_ci(main_panel(inp), ["entry_year", "k"], "d_rating", inp.z)


def control_adjusted(inp: Inputs, series: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Per-game control-adjusted 36-month change; returns (game-level frame, summary by year)."""
    last = inp.acfg["horizons"][-1]
    m = main_summary(inp)
    m["control_drift"] = control_change(control_lookup(series), m["entry_month"], 0, last)
    m["change_adjusted"] = m[f"change_{last}"] - m["control_drift"]
    rows = []
    for label, d in [("all", m)] + [(str(y), g) for y, g in m.groupby("entry_year")]:
        rows.append({"group": label, "n": len(d), "change_36": d[f"change_{last}"].mean(),
                     "control_drift": d["control_drift"].mean(), **{
                         f"adj_{k}": v for k, v in mean_ci(d["change_adjusted"], inp.z).items()
                         if k != "n"}})
    return m, pd.DataFrame(rows)


def decile_table(inp: Inputs) -> pd.DataFrame:
    """Mean change_36 by decile of the average rating at entry."""
    m = main_summary(inp)
    n_bins = inp.acfg["segments"]["avg0_deciles"]
    m["decile"] = pd.qcut(m["avg_m0"], n_bins, labels=False, duplicates="drop") + 1
    rows = []
    for d, g in m.groupby("decile"):
        rows.append({"decile": int(d), "avg_m0_mean": g["avg_m0"].mean(), **mean_ci(
            g["change_36"], inp.z)})
    return pd.DataFrame(rows)


def examples(inp: Inputs) -> pd.DataFrame:
    """Six games chosen by rule among main-sample games with many raters (see config)."""
    a = inp.acfg["examples"]
    m = main_summary(inp)
    big = m[m["raters_m36"] >= a["min_raters_m36"]].copy()
    mean_change = m["change_36"].mean()
    picks: list[tuple[int, str]] = []
    for gid in big.nsmallest(a["n_decliners"], "change_36")["game_id"]:
        picks.append((gid, "largest decline"))
    for gid in big.nlargest(a["n_risers"], "change_36")["game_id"]:
        picks.append((gid, "largest rise"))
    chosen = {g for g, _ in picks}
    typical = big[~big["game_id"].isin(chosen)].assign(
        dist=lambda d: (d["change_36"] - mean_change).abs()).nsmallest(a["n_typical"], "dist")
    picks += [(gid, "typical") for gid in typical["game_id"]]
    names = big.set_index("game_id")["latest_name"]
    p = inp.panel
    w = inp.acfg["gap"]["window"]
    out = []
    for gid, role in picks:
        d = p[p["game_id"] == gid].sort_values("k")
        out.append(pd.DataFrame({
            "game_id": gid, "name": names[gid], "role": role, "k": d["k"],
            "avg_rating": d["avg_rating"],
            "new_avg_3_ok": d[f"new_avg_{w}"].where(d[f"new_avg_ok_{w}"])}))
    return pd.concat(out, ignore_index=True)


def segments_table(inp: Inputs) -> pd.DataFrame:
    """Mean change_12 / change_36 by hype quartile, start level, entry raters and popularity."""
    s = inp.acfg["segments"]
    m = main_summary(inp)
    edges = s["entry_raters_edges"]
    labels = [f"<{edges[0]}"] + [f"{a}-{b - 1}" for a, b in zip(edges[:-1], edges[1:], strict=True)
                                  ] + [f"{edges[-1]}+"]
    m["entry_raters_bucket"] = pd.cut(m["raters_m0"], [-np.inf, *edges, np.inf], right=False,
                                      labels=labels).astype(str)
    q = s["avg0_quintiles"]
    m["avg0_quintile"] = "Q" + (pd.qcut(m["avg_m0"], q, labels=False, duplicates="drop") + 1
                                ).astype(str)
    cut = m["raters_m36"].quantile(1 - s["popular_top_share"])
    m["popularity"] = np.where(m["raters_m36"] >= cut,
                               f"top {int(100 * s['popular_top_share'])}% by raters_m36", "rest")
    m["hype_quartile_lbl"] = m["hype_quartile"].map(lambda v: f"Q{int(v)}" if v == v else None)
    rows = []
    for seg_type, col in [("hype_quartile", "hype_quartile_lbl"),
                          ("avg_m0_quintile", "avg0_quintile"),
                          ("entry_raters_bucket", "entry_raters_bucket"),
                          ("popularity", "popularity")]:
        for val, g in m.dropna(subset=[col]).groupby(col):
            for metric in ("change_12", "change_36"):
                r = mean_ci(g[metric], inp.z)
                rows.append({"segment_type": seg_type, "segment_value": val, "metric": metric,
                             "mean": r["mean"], "ci_low": r["ci_low"], "ci_high": r["ci_high"],
                             "n": r["n"]})
    return pd.DataFrame(rows)


def curve_by_hype_quartile(inp: Inputs) -> pd.DataFrame:
    p = main_panel(inp).merge(inp.summary[["game_id", "hype_quartile"]], on="game_id")
    return group_mean_ci(p.dropna(subset=["hype_quartile"]), ["hype_quartile", "k"], "d_rating",
                         inp.z)


def table1(cfg, inp: Inputs) -> pd.DataFrame:
    """Sample waterfall + cohort sizes in one long table (plus a markdown rendering)."""
    wf = pd.read_csv(cfg.path("tables_dir") / "sample_waterfall.csv")
    cs = pd.read_csv(cfg.path("tables_dir") / "cohort_sizes.csv")
    long = pd.concat([
        pd.DataFrame({"section": "waterfall", "label": wf["step"], "metric": "n_games",
                      "value": wf["n_games"]}),
        cs.melt(id_vars="entry_year", var_name="metric", value_name="value").assign(
            section="cohort_sizes", label=lambda d: d["entry_year"].astype(str)
        )[["section", "label", "metric", "value"]],
    ], ignore_index=True)
    from bgg.analysis.io import results_dir
    (results_dir(cfg) / "table1_sample.md").write_text(
        "## Sample waterfall\n\n" + md_table(wf, "{:.0f}") + "\n\n## New releases by entry year\n\n"
        + md_table(cs, "{:.0f}") + "\n", encoding="utf-8")
    return long


def run_descriptives(cfg, inp: Inputs | None = None) -> None:
    """Build Figs 1-6, Table 1, all descriptive tables and the descriptive key numbers."""
    from bgg.analysis.data import load_inputs
    inp = inp or load_inputs(cfg)
    fig_dir, z = cfg.path("figures_dir"), inp.z
    keys: dict[str, dict] = {}
    m, b = main_summary(inp), balanced_summary(inp)
    series, ctrl_ids = control_series(cfg)

    # --- Fig 1 -----------------------------------------------------------------------------
    curve = curve_overall(inp)
    write_table(cfg, curve, "curve_overall")
    share = share_of_decline(inp, 12, 36)
    plots.save_figure(plots.fig01_rating_change(curve, share), "fig01_rating_change_by_age",
                      fig_dir)
    keys["n_main_sample"] = entry(len(m), "game_summary", "in_main_sample AND observed_m36",
                                  n=len(m))
    keys["n_balanced_sample"] = entry(len(b), "game_summary",
                                      "main sample also observed at k=12 and k=24", n=len(b))
    keys["n_control_games"] = entry(len(ctrl_ids), "control_series",
                                    "ranked 2016-10 with >=500 raters, present in every snapshot",
                                    n=len(ctrl_ids))
    for h in inp.acfg["horizons"]:
        r = mean_ci(b[f"change_{h}"], z)
        keys[f"change_{h}"] = entry(r["mean"], "game_summary (balanced)",
                                    f"mean change in displayed average from entry to month {h}",
                                    r["ci_low"], r["ci_high"], r["n"])
    keys["share_of_decline_by_12"] = entry(
        share["value"], "game_summary (balanced)",
        "mean change_12 / mean change_36 (game-level bootstrap CI)", share["ci_low"],
        share["ci_high"], share["n"])
    c36 = m["change_36"]
    keys["median_change_36"] = entry(c36.median(), "game_summary (main)",
                                     "median change from entry to month 36", n=len(m))
    p_decl = (c36 < 0).mean()
    se = np.sqrt(p_decl * (1 - p_decl) / len(m))
    keys["share_declining"] = entry(p_decl, "game_summary (main)",
                                    "share of games with change_36 < 0",
                                    p_decl - z * se, p_decl + z * se, len(m))
    keys["change_36_rater_weighted"] = entry(
        weighted_mean(c36, m["raters_m36"]), "game_summary (main)",
        "mean change_36 weighted by raters at month 36", n=len(m))

    # --- Fig 2 -----------------------------------------------------------------------------
    gap = gap_table(inp)
    write_table(cfg, gap, "gap_new_vs_displayed")
    plots.save_figure(plots.fig02_gap(gap), "fig02_new_vs_displayed_gap", fig_dir)
    for k in inp.acfg["gap"]["ks"]:
        r = gap[gap["k"] == k].iloc[0]
        keys[f"gap_k{k}"] = entry(r["mean"], "gap_new_vs_displayed",
                                  f"mean of (new_avg_3 - avg_rating) at k={k}, usable rows, equal "
                                  "weight per row", r["ci_low"], r["ci_high"], r["n"])

    # --- Fig 3 -----------------------------------------------------------------------------
    by_year = curve_by_entry_year(inp)
    write_table(cfg, by_year, "curve_by_entry_year")
    write_table(cfg, series, "control_series")
    gm, adj = control_adjusted(inp, series)
    write_table(cfg, adj, "control_adjusted_change36")
    a_all = adj[adj["group"] == "all"].iloc[0]
    plots.save_figure(plots.fig03_cohorts_control(
        by_year, series, {"raw": a_all["change_36"], "drift": a_all["control_drift"],
                          "adjusted": a_all["adj_mean"]}), "fig03_cohorts_and_control", fig_dir)
    keys["control_drift_36"] = entry(a_all["control_drift"], "control_adjusted_change36",
                                     "mean control-group change over each main-sample game's own "
                                     "36-month window", n=a_all["n"])
    keys["change_36_control_adjusted"] = entry(
        a_all["adj_mean"], "control_adjusted_change36",
        "mean of change_36 minus control change over the same calendar months",
        a_all["adj_ci_low"], a_all["adj_ci_high"], a_all["n"])
    keys["control_change_full_period"] = entry(
        series["mean_avg"].iloc[-1] - series["mean_avg"].iloc[0], "control_series",
        "control-group mean average, last month minus 2016-10", n=len(ctrl_ids))

    # --- Fig 4 -----------------------------------------------------------------------------
    dec = decile_table(inp)
    write_table(cfg, dec, "change36_by_avg0_decile")
    plots.save_figure(plots.fig04_distribution(c36, dec, p_decl, c36.median()),
                      "fig04_change_distribution", fig_dir)

    # --- Fig 5 -----------------------------------------------------------------------------
    ex = examples(inp)
    write_table(cfg, ex, "examples")
    plots.save_figure(plots.fig05_examples(ex), "fig05_examples", fig_dir)

    # --- Step 2: segments + Fig 6 ----------------------------------------------------------
    seg = segments_table(inp)
    write_table(cfg, seg, "segments")
    hq = curve_by_hype_quartile(inp)
    write_table(cfg, hq, "curve_by_hype_quartile")
    plots.save_figure(plots.fig06_hype_quartiles(hq), "fig06_by_hype_quartile", fig_dir)
    for q in range(1, 5):
        r = seg[(seg["segment_type"] == "hype_quartile") & (seg["segment_value"] == f"Q{q}")
                & (seg["metric"] == "change_36")].iloc[0]
        keys[f"change_36_hype_q{q}"] = entry(r["mean"], "segments",
                                             f"mean change_36, hype quartile {q} (1 = least hyped)",
                                             r["ci_low"], r["ci_high"], r["n"])

    write_table(cfg, table1(cfg, inp), "table1_sample")
    save_fragment(cfg, "descriptives", keys)
