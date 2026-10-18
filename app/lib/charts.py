"""Plotly chart builders for the dashboard (no Streamlit import; reused by the static export).

Design rules (kept deliberately few):
- horizontal grid only, very light; no axis lines except the zero baseline
- confidence bands only on single-series charts; multi-series charts show CIs on hover
- lines are labelled at their right end instead of a legend wherever possible
- ordered groups (launch year, hype quartile, decile) use one blue ramp, light to dark;
  two-group splits use blue vs amber; "new raters" is plum; context lines are dashed grey
Palette validated with the dataviz skill's validator (colour-blind separation and contrast).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from lib.fmt import fmt

# --- tokens ------------------------------------------------------------------------------------
INK, INK_2, INK_3 = "#1D2533", "#4A5466", "#6B7585"
GRID, BASELINE = "#E9EDF2", "#1D2533"
BLUE, PLUM, AMBER, GREY = "#2167B0", "#B23F68", "#B3770A", "#7A8494"
RAMP_LIGHT, RAMP_DARK = "#93B8E0", "#0D3462"
FONT_FAMILY = "IBM Plex Sans, Segoe UI, Helvetica Neue, Arial, sans-serif"
MILESTONES = (12, 24, 36)
X_TITLE = "Months since entering the ranking"

# kept for backwards compatibility with older imports
RED, GREEN, SKY = PLUM, "#2E8B57", RAMP_LIGHT
SEQ4 = ["#93B8E0", "#5A8FCB", "#2E66A8", "#0D3462"]
CYCLE = [BLUE, AMBER, PLUM, GREY]


def _rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def _blend(c0: str, c1: str, t: float) -> str:
    """Linear blend between two hex colours (t = 0 -> c0, t = 1 -> c1)."""
    a = [int(c0[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b, strict=True))


def ramp(n: int) -> list[str]:
    """n steps of the blue ramp, light to dark."""
    return [_blend(RAMP_LIGHT, RAMP_DARK, i / max(n - 1, 1)) for i in range(n)]


def base_layout(fig: go.Figure, height: int = 400, legend: bool = False,
                unified: bool = True, right_margin: int = 24,
                top: int | None = None) -> go.Figure:
    """Shared look: quiet axes, light horizontal grid, compact margins, transparent background."""
    fig.update_layout(
        font=dict(family=FONT_FAMILY, size=13, color=INK),
        height=height, margin=dict(l=8, r=right_margin, t=top if top is not None else (36 if legend else 12), b=8),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        hovermode="x unified" if unified else "closest",
        hoverlabel=dict(bgcolor="white", bordercolor=GRID, font=dict(family=FONT_FAMILY,
                                                                      size=12, color=INK)),
        showlegend=legend,
        legend=dict(orientation="h", x=0, y=1.02, yanchor="bottom", title=None,
                    font=dict(size=12, color=INK_2), itemclick=False, itemdoubleclick=False),
    )
    fig.update_xaxes(showgrid=False, zeroline=False, showline=False, ticks="",
                     tickfont=dict(color=INK_3, size=12), title_font=dict(color=INK_3, size=12),
                     automargin=True)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, showline=False, ticks="",
                     tickfont=dict(color=INK_3, size=12), title_font=dict(color=INK_3, size=12),
                     automargin=True)
    return fig


def _baseline(fig: go.Figure, horizontal: bool = True) -> None:
    if horizontal:
        fig.add_hline(y=0, line_color=BASELINE, line_width=1, opacity=0.6)
    else:
        fig.add_vline(x=0, line_color=BASELINE, line_width=1, opacity=0.6)


def _end_labels(fig: go.Figure, items: list[tuple[str, float, float, str]],
                min_gap: float) -> None:
    """Label lines at their right end: (text, x, y, colour). Labels are nudged apart vertically.

    Text stays in ink; a coloured dot beside it carries the series identity.
    """
    if not items:
        return
    items = sorted(items, key=lambda t: t[2], reverse=True)
    ys = [it[2] for it in items]
    for i in range(1, len(ys)):  # push down so labels never overlap
        ys[i] = min(ys[i], ys[i - 1] - min_gap)
    shift = (np.mean([it[2] for it in items]) - np.mean(ys))  # re-centre the stack
    for (label, x, _, color), y in zip(items, ys, strict=True):
        fig.add_annotation(
            x=x, y=y + shift, xanchor="left", yanchor="middle", showarrow=False, xshift=8,
            text=f"<span style='color:{color}'>●</span> {label}",
            font=dict(size=12, color=INK_2))


def _line(fig: go.Figure, df: pd.DataFrame, color: str, name: str, band: bool,
          width: float = 2.4, dash: str | None = None) -> None:
    """Mean line, optional CI band; hover shows mean and CI."""
    if band:
        fig.add_trace(go.Scatter(x=df["k"], y=df["ci_high"], mode="lines", line=dict(width=0),
                                 hoverinfo="skip", showlegend=False))
        fig.add_trace(go.Scatter(x=df["k"], y=df["ci_low"], mode="lines", line=dict(width=0),
                                 fill="tonexty", fillcolor=_rgba(color, 0.14), hoverinfo="skip",
                                 showlegend=False))
    fig.add_trace(go.Scatter(
        x=df["k"], y=df["mean"], mode="lines", name=name,
        line=dict(color=color, width=width, dash=dash),
        customdata=np.stack([df["ci_low"], df["ci_high"]], axis=1),
        hovertemplate=f"{name}: %{{y:+.2f}} <span style='color:{INK_3}'>"
                      "[%{customdata[0]:+.2f}, %{customdata[1]:+.2f}]</span><extra></extra>"))


def _group_colors(groups: list[str], group_type: str) -> dict[str, str]:
    if group_type in ("hype_quartile", "start_decile", "launch_year"):
        return dict(zip(groups, ramp(len(groups)), strict=True))
    if group_type == "popularity":
        return {g: (BLUE if "Top" in g else AMBER) for g in groups}
    if group_type == "kickstarted":
        return {g: (AMBER if g == "Kickstarted" else BLUE) for g in groups}
    return {g: BLUE for g in groups}


def _label_for(g: str, group_type: str) -> str:
    if group_type == "hype_quartile":
        return {"Q1": "Q1 least hyped", "Q4": "Q4 most hyped"}.get(g, g)
    if group_type == "start_decile":
        return {"D01": "Lowest start", "D10": "Highest start"}.get(g, g)
    if group_type == "popularity":
        return {"Top 10% by raters": "Top 10% popular", "Other games": "Others"}.get(g, g)
    return str(g)


def _x_axis(fig: go.Figure, k_max: int = 36) -> None:
    fig.update_xaxes(title=X_TITLE, tickvals=[0, 6, 12, 18, 24, 30, 36],
                     range=[-0.5, k_max + 0.5])


def fig_overview(curves: pd.DataFrame, group_type: str, height: int = 400,
                 highlight: str | None = None) -> go.Figure:
    """The fade: mean change by months since entry.

    Up to four groups are drawn in colour with end labels. With more groups (launch years,
    deciles) every group is a thin grey context line and only ``highlight`` is drawn in colour.
    """
    fig = go.Figure()
    groups = sorted(curves["group_value"].unique())
    single = len(groups) == 1
    many = len(groups) > 4
    colors = _group_colors(groups, group_type)
    labels = []
    if many:
        highlight = highlight if highlight in groups else groups[-1]
        for g in groups:
            if g == highlight:
                continue
            d = curves[curves["group_value"] == g].sort_values("k")
            fig.add_trace(go.Scatter(x=d["k"], y=d["mean"], mode="lines", name=str(g),
                                     line=dict(color="#CDD4DE", width=1.3),
                                     hovertemplate=f"{_label_for(g, group_type)}: %{{y:+.2f}}"
                                                   "<extra></extra>"))
        d = curves[curves["group_value"] == highlight].sort_values("k")
        name = _label_for(highlight, group_type)
        _line(fig, d, BLUE, name, band=True, width=2.8)
        last = d.iloc[-1]
        labels.append((name, float(last["k"]), float(last["mean"]), BLUE))
    else:
        for g in groups:
            d = curves[curves["group_value"] == g].sort_values("k")
            name = _label_for(g, group_type)
            _line(fig, d, colors[g], "All new games" if single else name, band=single)
            if not single:
                last = d.iloc[-1]
                labels.append((name, float(last["k"]), float(last["mean"]), colors[g]))
    if single:
        d = curves[curves["k"].isin(MILESTONES)].sort_values("k")
        fig.add_trace(go.Scatter(
            x=d["k"], y=d["mean"], mode="markers+text", showlegend=False, hoverinfo="skip",
            marker=dict(color=BLUE, size=8, line=dict(color="white", width=2)),
            text=[fmt(v, "+.2f", minus=True) for v in d["mean"]],
            textposition="bottom center", textfont=dict(color=INK, size=13), cliponaxis=False))
    _baseline(fig)
    _x_axis(fig)
    fig.update_yaxes(title="Change in displayed rating", tickformat=".1f", dtick=0.1)
    _end_labels(fig, labels, min_gap=0.024)
    return base_layout(fig, height=height, right_margin=44 if single else 130)


def fig_explore(seg: pd.DataFrame, overall: pd.DataFrame, group_type: str,
                highlight: str | None = None) -> go.Figure:
    """Segment curves against the overall curve (dashed grey)."""
    fig = fig_overview(seg, group_type, height=440, highlight=highlight)
    o = overall.sort_values("k")
    fig.add_trace(go.Scatter(x=o["k"], y=o["mean"], mode="lines", name="All new games",
                             line=dict(color=GREY, dash="dash", width=1.8),
                             hovertemplate="All new games: %{y:+.2f}<extra></extra>"))
    last = o.iloc[-1]
    fig.add_annotation(x=float(last["k"]), y=float(last["mean"]), xanchor="left", xshift=8,
                       yshift=-14, showarrow=False, text="All games (dashed)",
                       font=dict(size=11, color=INK_3))
    return fig


def fig_gap(gap: pd.DataFrame) -> go.Figure:
    """New raters' average minus the displayed average, by month (usable share in the hover)."""
    fig = go.Figure()
    g = gap.sort_values("k")
    fig.add_trace(go.Scatter(x=g["k"], y=g["ci_high"], mode="lines", line=dict(width=0),
                             hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(x=g["k"], y=g["ci_low"], mode="lines", line=dict(width=0),
                             fill="tonexty", fillcolor=_rgba(PLUM, 0.14), hoverinfo="skip",
                             showlegend=False))
    fig.add_trace(go.Scatter(
        x=g["k"], y=g["mean"], mode="lines", line=dict(color=PLUM, width=2.4),
        customdata=np.stack([g["ci_low"], g["ci_high"], 100 * g["share_usable"]], axis=1),
        hovertemplate="New raters vs displayed: %{y:+.2f}"
                      f"<span style='color:{INK_3}'> [%{{customdata[0]:+.2f}}, "
                      "%{customdata[1]:+.2f}]<br>estimate available for %{customdata[2]:.0f}% "
                      "of games</span><extra></extra>", name=""))
    for k in (3, 36):
        row = g[g["k"] == k]
        if not row.empty:
            v = float(row["mean"].iloc[0])
            fig.add_trace(go.Scatter(x=[k], y=[v], mode="markers+text", hoverinfo="skip",
                                     marker=dict(color=PLUM, size=8,
                                                 line=dict(color="white", width=2)),
                                     text=[fmt(v, "+.2f", minus=True)],
                                     textposition="bottom center",
                                     textfont=dict(color=INK, size=13), showlegend=False,
                                     cliponaxis=False))
    _baseline(fig)
    _x_axis(fig)
    fig.update_xaxes(range=[1.5, 36.8], tickvals=[3, 6, 12, 18, 24, 30, 36])
    lo = min(-0.3, float(g["ci_low"].min()) - 0.03)
    fig.update_yaxes(title="New-rater average minus displayed", range=[lo, 0.03],
                     tickformat=".1f", dtick=0.1)
    fig.add_annotation(x=36, y=0, yshift=10, xanchor="right", showarrow=False,
                       text="Displayed average", font=dict(size=12, color=INK_3))
    return base_layout(fig, height=380, right_margin=44)


def fig_speed(speed: pd.DataFrame, months: tuple[int, int]) -> go.Figure:
    """Dumbbell per hype quartile: mean change at month `first` and at month `last`."""
    first, last = months
    fig = go.Figure()
    labels = [f"Q{int(q)}" + (" least hyped" if q == 1 else " most hyped" if q == 4 else "")
              for q in speed["hype_quartile"]]
    for lab, a, b in zip(labels, speed[f"change_{first}"], speed[f"change_{last}"], strict=True):
        fig.add_shape(type="line", x0=a, x1=b, y0=lab, y1=lab, layer="below",
                      line=dict(color="#D3DAE3", width=6))
    for m, color, size in ((first, RAMP_LIGHT, 14), (last, RAMP_DARK, 14)):
        fig.add_trace(go.Scatter(
            x=speed[f"change_{m}"], y=labels, mode="markers", name=f"Month {m}",
            marker=dict(color=color, size=size, line=dict(color="white", width=2)),
            customdata=np.stack([speed[f"change_{m}_ci_low"], speed[f"change_{m}_ci_high"]],
                                axis=1),
            hovertemplate=f"%{{y}}, month {m}: %{{x:+.2f}} <span style='color:{INK_3}'>"
                          "[%{customdata[0]:+.2f}, %{customdata[1]:+.2f}]</span><extra></extra>"))
    _baseline(fig, horizontal=False)
    fig.update_xaxes(title="Mean change in displayed rating since entry", tickformat=".1f",
                     dtick=0.1, showgrid=True, gridcolor=GRID)
    fig.update_yaxes(autorange="reversed", showgrid=False)
    return base_layout(fig, height=300, legend=True, unified=False)


def fig_specs(numbers: dict[str, dict]) -> go.Figure:
    """Hype coefficient for the four model specifications with 95% CI."""
    labels = {"a": "With controls", "b": "Change after month 6",
              "c": "Reach instead of growth", "d": "No controls"}
    xs, lo, hi, ys = [], [], [], []
    for s, lab in labels.items():
        e = numbers[f"spec_{s}_hype"]
        xs.append(e["value"])
        lo.append(e["value"] - e["ci_low"])
        hi.append(e["ci_high"] - e["value"])
        ys.append(lab)
    fig = go.Figure()
    span = max(abs(v) for v in [x + h for x, h in zip(xs, hi, strict=True)]
               + [x - low for x, low in zip(xs, lo, strict=True)]) * 1.25
    fig.add_vrect(x0=-span, x1=0, fillcolor=PLUM, opacity=0.05, line_width=0, layer="below")
    fig.add_annotation(x=-span, y=1.0, yref="paper", xanchor="left", yanchor="bottom",
                       showarrow=False, text="Hyped games fade more",
                       font=dict(color=PLUM, size=11))
    fig.add_annotation(x=span, y=1.0, yref="paper", xanchor="right", yanchor="bottom",
                       showarrow=False, text="Hyped games fade less",
                       font=dict(color=INK_3, size=11))
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="markers",
                             marker=dict(color=BLUE, size=11, line=dict(color="white", width=2)),
                             error_x=dict(type="data", symmetric=False, array=hi, arrayminus=lo,
                                          color=BLUE, thickness=1.6, width=0),
                             hovertemplate="%{y}: %{x:+.3f}<extra></extra>"))
    _baseline(fig, horizontal=False)
    fig.update_xaxes(title="Effect of hype on the 3-year change (95% CI)", range=[-span, span],
                     showgrid=True, gridcolor=GRID, tickformat="+.2f")
    fig.update_yaxes(autorange="reversed", showgrid=False)
    return base_layout(fig, height=290, unified=False, top=30)


def fig_kickstarter(bands: pd.DataFrame) -> go.Figure:
    """Change to month 36 by starting-rating band, Kickstarted vs not, with CIs."""
    fig = go.Figure()
    labels = []
    for flag, color, name, off in ((0, BLUE, "Not Kickstarted", -0.025),
                                   (1, AMBER, "Kickstarted", 0.025)):
        d = bands[bands["kickstarted"] == flag].sort_values("band_mid")
        fig.add_trace(go.Scatter(
            x=d["band_mid"] + off, y=d["mean"], mode="lines+markers", name=name,
            line=dict(color=color, width=2), marker=dict(size=8, line=dict(color="white",
                                                                            width=1.5)),
            error_y=dict(type="data", symmetric=False, array=d["ci_high"] - d["mean"],
                         arrayminus=d["mean"] - d["ci_low"], color=_rgba(color, 0.6),
                         thickness=1.4, width=0),
            customdata=np.stack([d["band_low"], d["band_high"], d["n"]], axis=1),
            hovertemplate=name + ", start %{customdata[0]:.1f}–%{customdata[1]:.1f}: "
                                 "%{y:+.2f} (n = %{customdata[2]:,})<extra></extra>"))
        last = d.iloc[-1]
        labels.append((name, float(last["band_mid"] + off), float(last["mean"]), color))
    _baseline(fig)
    fig.update_xaxes(title="Average rating at entry", dtick=0.5)
    fig.update_yaxes(title="Change to month 36", tickformat=".1f", dtick=0.2)
    _end_labels(fig, labels, min_gap=0.06)
    return base_layout(fig, height=360, unified=False, right_margin=130)


def fig_trust(curve: pd.DataFrame, tolerance: float, target: float, rule_k: float) -> go.Figure:
    """Share of games within the tolerance of their 3-year rating, by month."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=curve["k"], y=100 * curve["share"], mode="lines",
        line=dict(color=BLUE, width=2.6),
        hovertemplate="Month %{x}: %{y:.0f}% of games within the tolerance<extra></extra>"))
    fig.add_hline(y=100 * target, line_dash="dot", line_color=GREY, line_width=1.2)
    fig.add_annotation(x=0, y=100 * target, yshift=10, xanchor="left", showarrow=False,
                       text=f"Target {fmt(100 * target, '.0f')}%",
                       font=dict(size=12, color=INK_3))
    if not np.isnan(rule_k):
        y = float(100 * curve.loc[curve["k"] == rule_k, "share"].iloc[0])
        fig.add_trace(go.Scatter(x=[rule_k], y=[y], mode="markers", hoverinfo="skip",
                                 marker=dict(color=BLUE, size=11,
                                             line=dict(color="white", width=2))))
        fig.add_annotation(x=rule_k, y=y, ax=40, ay=40, showarrow=True, arrowhead=0,
                           arrowcolor=INK_3, arrowwidth=1, text=f"<b>Month {int(rule_k)}</b>",
                           font=dict(size=13, color=INK), xanchor="left")
    fig.update_xaxes(title=X_TITLE, tickvals=[0, 6, 12, 18, 24, 30])
    fig.update_yaxes(title=f"Games within ±{tolerance:.2f} of final rating", range=[0, 102],
                     ticksuffix="%", dtick=20)
    return base_layout(fig, height=360, unified=False)


def fig_adjusted(bars: pd.DataFrame, tol: float) -> go.Figure:
    """Share within tolerance at each age: displayed rating vs adjusted launch rating."""
    fig = go.Figure()
    for pred, color in (("Displayed rating", "#B8C2CF"), ("Adjusted launch rating", BLUE)):
        d = bars[bars["predictor"] == pred]
        fig.add_trace(go.Bar(
            x=[f"Month {k}" for k in d["k"]], y=100 * d["share_within"], name=pred,
            marker=dict(color=color, line=dict(width=0), cornerradius=4),
            text=[f"{fmt(100 * v, '.0f')}%" for v in d["share_within"]],
            textposition="outside", textfont=dict(color=INK_2, size=12), cliponaxis=False,
            customdata=np.stack([d["mae"], d["n"]], axis=1),
            hovertemplate=pred + ": %{y:.0f}% within ±" + f"{tol}"
                          " (mean error %{customdata[0]:.2f})<extra></extra>"))
    fig.update_layout(barmode="group", bargap=0.35, bargroupgap=0.08)
    fig.update_yaxes(range=[0, 108], showticklabels=False, showgrid=False)
    fig.update_xaxes(title=None)
    return base_layout(fig, height=320, legend=True, unified=False)


def _short(name: str, n: int = 26) -> str:
    return name if len(name) <= n else name[: n - 1].rstrip() + "…"


RANK_TICKS = [1, 3, 10, 30, 100, 300, 1000, 3000, 10000, 30000]


def fig_lookup(name: str, traj: pd.DataFrame, avg_m0: float, cohort_curve: pd.DataFrame | None,
               new_col: str, metric: str = "rating", other: tuple[str, pd.DataFrame] | None = None,
               expected: float | None = None, cohort_label: str = "Typical launch") -> go.Figure:
    """One game's path (rating, rank or raters), optionally against a second game.

    Rating view: displayed average, new-rater dots, the typical path of its launch year and the
    model's expected three-year rating. Comparing two games drops the context layers.
    """
    fig = go.Figure()
    col = {"rating": "avg_rating", "rank": "rank", "raters": "n_raters"}[metric]
    fmt_hover = {"rating": "%{y:.2f}", "rank": "#%{y:,.0f}", "raters": "%{y:,.0f} raters"}[metric]
    series = [(name, traj.sort_values("k"), BLUE)]
    if other is not None:
        series.append((other[0], other[1].sort_values("k"), AMBER))
    labels, ys = [], []
    if metric == "rating" and other is None:
        t0 = series[0][1]
        if cohort_curve is not None and not cohort_curve.empty:
            ref = cohort_curve[cohort_curve["k"] <= t0["k"].max()].sort_values("k")
            fig.add_trace(go.Scatter(
                x=ref["k"], y=avg_m0 + ref["mean"], mode="lines", name=cohort_label,
                line=dict(color="#B9C1CE", width=2, dash="dash"),
                hovertemplate=cohort_label + ": %{y:.2f}<extra></extra>"))
            labels.append((cohort_label, float(ref["k"].iloc[-1]),
                           float(avg_m0 + ref["mean"].iloc[-1]), GREY))
            ys.append(float(avg_m0 + ref["mean"].iloc[-1]))
        ok = t0.dropna(subset=[new_col])
        if not ok.empty:
            fig.add_trace(go.Scatter(
                x=ok["k"], y=ok[new_col], mode="markers", name="New raters",
                marker=dict(color=PLUM, size=7, line=dict(color="white", width=1)),
                hovertemplate="New raters: %{y:.2f}<extra></extra>"))
            ys += list(ok[new_col])
    for nm, t, color in series:
        d = t.dropna(subset=[col])
        if d.empty:
            continue
        fig.add_trace(go.Scatter(
            x=d["k"], y=d[col], mode="lines", name=_short(nm, 40),
            line=dict(color=color, width=2.8),
            hovertemplate=f"{_short(nm, 30)}: {fmt_hover}<extra></extra>"))
        labels.append((_short(nm), float(d["k"].iloc[-1]), float(d[col].iloc[-1]), color))
        ys += list(d[col])
    if expected is not None and metric == "rating" and other is None and expected == expected:
        fig.add_trace(go.Scatter(
            x=[36], y=[expected], mode="markers", name="Expected from launch data",
            marker=dict(color=AMBER, size=11, symbol="diamond", line=dict(color="white", width=2)),
            hovertemplate="Expected 3-year rating: %{y:.2f}<extra></extra>"))
        labels.append(("Expected at 36", 36.0, float(expected), AMBER))
        ys.append(float(expected))
    kmax = int(max(36, max(t["k"].max() for _, t, _ in series)))
    _x_axis(fig, kmax)
    if metric == "rating":
        span = max(ys) - min(ys) if ys else 1.0
        fig.update_yaxes(title="Average rating", tickformat=".1f")
        _end_labels(fig, labels, min_gap=max(span, 0.3) * 0.075)
    elif metric == "rank":
        fig.update_yaxes(type="log", autorange="reversed", title="Rank (1 = best)",
                         tickvals=RANK_TICKS, ticktext=[f"{v:,}" for v in RANK_TICKS])
        for lab, x, y, color in labels:
            fig.add_annotation(x=x, y=np.log10(y), xanchor="left", yanchor="middle", xshift=8,
                               showarrow=False, text=f"<span style='color:{color}'>●</span> "
                               f"{lab}", font=dict(size=12, color=INK_2))
    else:
        fig.update_yaxes(type="log", title="Raters (log scale)")
        for lab, x, y, color in labels:
            fig.add_annotation(x=x, y=np.log10(y), xanchor="left", yanchor="middle", xshift=8,
                               showarrow=False, text=f"<span style='color:{color}'>●</span> "
                               f"{lab}", font=dict(size=12, color=INK_2))
    return base_layout(fig, height=420, right_margin=150)
