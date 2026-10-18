"""Plotly chart builders for the dashboard (no Streamlit import; reused by the static export)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from lib.fmt import fmt
from plotly.subplots import make_subplots

BLUE, ORANGE, GREEN, RED = "#0072B2", "#E69F00", "#009E73", "#D55E00"
PURPLE, SKY, GREY = "#CC79A7", "#56B4E9", "#666666"
CYCLE = [BLUE, ORANGE, GREEN, RED, PURPLE, SKY, GREY]
SEQ4 = ["#9ECAE1", "#4292C6", "#2171B5", "#08306B"]
MILESTONES = (12, 24, 36)
FONT = dict(family="Arial, sans-serif", size=13, color="#222222")


def _rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def base_layout(fig: go.Figure, height: int = 420, legend_below: bool = True) -> go.Figure:
    """Shared look: white background, light grid, compact margins, legend below (phone-friendly)."""
    fig.update_layout(
        font=FONT, height=height, margin=dict(l=55, r=15, t=15, b=50), plot_bgcolor="white",
        hovermode="closest",
        legend=(dict(orientation="h", y=-0.22, x=0) if legend_below else None))
    fig.update_xaxes(gridcolor="#E5E5E5", zeroline=False, linecolor="#999999")
    fig.update_yaxes(gridcolor="#E5E5E5", zeroline=False, linecolor="#999999")
    return fig


def _band_trace(fig, df, color, name, row=None, col=None, dash=None):
    """Mean line plus CI band with a hover showing mean, CI and n."""
    hover = ("<b>" + name + "</b><br>Month %{x}<br>Mean change %{y:+.3f}"
             "<br>95% CI [%{customdata[0]:+.3f}, %{customdata[1]:+.3f}]<br>n = %{customdata[2]:,}"
             "<extra></extra>")
    kw = dict(row=row, col=col) if row else {}
    fig.add_trace(go.Scatter(x=df["k"], y=df["ci_high"], mode="lines", line=dict(width=0),
                             hoverinfo="skip", showlegend=False), **kw)
    fig.add_trace(go.Scatter(x=df["k"], y=df["ci_low"], mode="lines", line=dict(width=0),
                             fill="tonexty", fillcolor=_rgba(color, 0.18), hoverinfo="skip",
                             showlegend=False), **kw)
    fig.add_trace(go.Scatter(x=df["k"], y=df["mean"], mode="lines", name=name,
                             line=dict(color=color, width=2.4, dash=dash),
                             customdata=np.stack([df["ci_low"], df["ci_high"], df["n"]], axis=1),
                             hovertemplate=hover), **kw)


def fig_overview(curves: pd.DataFrame, group_type: str) -> go.Figure:
    """Fig 1: mean change by months since entry, one line per group in the chosen comparison."""
    fig = go.Figure()
    groups = sorted(curves["group_value"].unique())
    for i, g in enumerate(groups):
        color = (SEQ4[int(g[1]) - 1] if group_type == "hype_quartile"
                 else BLUE if group_type == "none" else CYCLE[i % len(CYCLE)])
        label = g
        if group_type == "hype_quartile":
            label = {"Q1": "Q1 (least hyped)", "Q4": "Q4 (most hyped)"}.get(g, g)
        _band_trace(fig, curves[curves["group_value"] == g].sort_values("k"), color, label)
    if group_type == "none":  # label the headline points, as in the static Fig 1
        d = curves[curves["k"].isin(MILESTONES)].sort_values("k")
        fig.add_trace(go.Scatter(
            x=d["k"], y=d["mean"], mode="markers+text", showlegend=False, hoverinfo="skip",
            marker=dict(color=BLUE, size=9), text=[fmt(v, "+.2f", minus=True) for v in d["mean"]],
            textposition="bottom center", textfont=dict(color=BLUE, size=12)))
    fig.add_hline(y=0, line_color="black", line_width=1)
    fig.update_xaxes(title="Months since entering the ranking")
    fig.update_yaxes(title="Change in displayed rating")
    fig.update_layout(showlegend=group_type != "none")
    return base_layout(fig)


def fig_explore(seg: pd.DataFrame, overall: pd.DataFrame, group_type: str) -> go.Figure:
    """Segment curves (colour) against the overall curve (dashed grey), with CI bands."""
    fig = go.Figure()
    groups = sorted(seg["group_value"].unique())
    n_groups = len(groups)
    for i, g in enumerate(groups):
        if group_type in ("hype_quartile", "start_decile"):
            shade = i / max(n_groups - 1, 1)
            color = _blend("#9ECAE1", "#08306B", shade)
        else:
            color = CYCLE[i % len(CYCLE)]
        _band_trace(fig, seg[seg["group_value"] == g].sort_values("k"), color, str(g))
    o = overall.sort_values("k")
    fig.add_trace(go.Scatter(x=o["k"], y=o["mean"], mode="lines", name="All new games",
                             line=dict(color="#444444", dash="dash", width=2.2), hoverinfo="skip"))
    fig.add_hline(y=0, line_color="black", line_width=1)
    fig.update_xaxes(title="Months since entering the ranking")
    fig.update_yaxes(title="Change in displayed rating")
    return base_layout(fig, height=440)


def _blend(c0: str, c1: str, t: float) -> str:
    """Linear blend between two hex colours (t = 0 -> c0, t = 1 -> c1)."""
    a = [int(c0[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b, strict=True))


def fig_gap(gap: pd.DataFrame) -> go.Figure:
    """Fig 2: new raters' average minus displayed average (top) and usable share (bottom)."""
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.72, 0.28],
                        vertical_spacing=0.06)
    g = gap.rename(columns={"mean": "mean", "ci_low": "ci_low", "ci_high": "ci_high"})
    _band_trace(fig, g, RED, "New raters minus displayed", row=1, col=1)
    fig.add_hline(y=0, line_color="black", line_width=1, row=1, col=1)
    fig.add_trace(go.Scatter(x=gap["k"], y=100 * gap["share_usable"], mode="lines",
                             line=dict(color=GREY, width=2), name="Usable share",
                             hovertemplate="Month %{x}: %{y:.0f}% of game-months usable"
                                           "<extra></extra>"), row=2, col=1)
    fig.update_yaxes(title_text="New-rater avg minus displayed", row=1, col=1)
    fig.update_yaxes(title_text="% usable", row=2, col=1)
    fig.update_xaxes(title_text="Months since entering the ranking", row=2, col=1)
    fig.update_layout(showlegend=False)
    return base_layout(fig, height=480, legend_below=False)


def fig_speed(speed: pd.DataFrame, months: tuple[int, int]) -> go.Figure:
    """Fig 9: dumbbell per hype quartile, mean change at the two months with CIs."""
    first, last = months
    fig = go.Figure()
    labels = []
    for _, r in speed.iterrows():
        q = int(r["hype_quartile"])
        labels.append(f"Q{q}" + (" (least hyped)" if q == 1 else " (most hyped)" if q == 4 else ""))
    y = labels
    fig.add_trace(go.Scatter(
        x=speed[f"change_{last}"], y=y, mode="markers", name=f"Month {last}",
        marker=dict(color=SEQ4[3], size=13),
        error_x=dict(type="data", symmetric=False, color=SEQ4[3], thickness=2,
                     array=speed[f"change_{last}_ci_high"] - speed[f"change_{last}"],
                     arrayminus=speed[f"change_{last}"] - speed[f"change_{last}_ci_low"]),
        hovertemplate=f"%{{y}}<br>Month {last}: %{{x:+.3f}}<extra></extra>"))
    fig.add_trace(go.Scatter(
        x=speed[f"change_{first}"], y=y, mode="markers", name=f"Month {first}",
        marker=dict(color=SEQ4[0], size=13, line=dict(color=SEQ4[1], width=1)),
        error_x=dict(type="data", symmetric=False, color=SEQ4[1], thickness=2,
                     array=speed[f"change_{first}_ci_high"] - speed[f"change_{first}"],
                     arrayminus=speed[f"change_{first}"] - speed[f"change_{first}_ci_low"]),
        hovertemplate=f"%{{y}}<br>Month {first}: %{{x:+.3f}}<extra></extra>"))
    for lab, a, b in zip(labels, speed[f"change_{first}"], speed[f"change_{last}"], strict=True):
        fig.add_shape(type="line", x0=a, x1=b, y0=lab, y1=lab, layer="below",
                      line=dict(color="#BBBBBB", width=4))
    fig.add_vline(x=0, line_color="black", line_width=1)
    fig.update_xaxes(title="Mean change in displayed rating since entry")
    fig.update_yaxes(autorange="reversed")
    return base_layout(fig, height=330)


def fig_specs(numbers: dict[str, dict]) -> go.Figure:
    """Hype coefficient for Specs A-D with 95% CI; the region H2 predicts is shaded."""
    labels = {"a": "A: change_36, controls", "b": "B: change after month 6",
              "c": "C: reach (log raters m6)", "d": "D: no controls"}
    xs, lo, hi, ys = [], [], [], []
    for s, lab in labels.items():
        e = numbers[f"spec_{s}_hype"]
        xs.append(e["value"])
        lo.append(e["value"] - e["ci_low"])
        hi.append(e["ci_high"] - e["value"])
        ys.append(lab)
    fig = go.Figure()
    fig.add_vrect(x0=-1, x1=0, fillcolor="#D55E00", opacity=0.07, line_width=0, layer="below")
    fig.add_annotation(x=0, y=1.08, yref="paper", xanchor="right", showarrow=False,
                       text="H2 predicts a negative coefficient", font=dict(color=RED, size=11))
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="markers", marker=dict(color=BLUE, size=12),
                             error_x=dict(type="data", symmetric=False, array=hi, arrayminus=lo,
                                          color=BLUE, thickness=2),
                             hovertemplate="%{y}<br>coefficient %{x:+.3f}<extra></extra>"))
    fig.add_vline(x=0, line_color="black", line_width=1)
    span = max(abs(v) for v in xs + [x + h for x, h in zip(xs, hi, strict=True)]
               + [x - low for x, low in zip(xs, lo, strict=True)]) * 1.15
    fig.update_xaxes(title="Hype coefficient (per log-unit), 95% CI", range=[-span, span])
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(showlegend=False)
    return base_layout(fig, height=300, legend_below=False)


def fig_kickstarter(bands: pd.DataFrame) -> go.Figure:
    """Fig 10: change to month 36 by starting band, Kickstarted vs not, with CIs."""
    fig = go.Figure()
    for flag, color, name, off in ((0, BLUE, "Not Kickstarted", -0.03),
                                   (1, RED, "Kickstarted", 0.03)):
        d = bands[bands["kickstarted"] == flag]
        fig.add_trace(go.Scatter(
            x=d["band_mid"] + off, y=d["mean"], mode="lines+markers", name=name,
            line=dict(color=color), marker=dict(size=9),
            error_y=dict(type="data", symmetric=False, array=d["ci_high"] - d["mean"],
                         arrayminus=d["mean"] - d["ci_low"], color=color),
            customdata=np.stack([d["band_low"], d["band_high"], d["n"]], axis=1),
            hovertemplate=name + "<br>Start %{customdata[0]:.1f}-%{customdata[1]:.1f}"
                                 "<br>Mean change %{y:+.3f}<br>n = %{customdata[2]:,}"
                                 "<extra></extra>"))
    fig.add_hline(y=0, line_color="black", line_width=1)
    fig.update_xaxes(title="Average rating at entry (0.5-wide bands)")
    fig.update_yaxes(title="Mean change to month 36")
    return base_layout(fig, height=380)


def fig_trust(curve: pd.DataFrame, tolerance: float, target: float, rule_k: float) -> go.Figure:
    """Fig 8: share within tolerance by month, with the target line and the trust month."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=curve["k"], y=100 * curve["share"], mode="lines",
                             line=dict(color=BLUE, width=2.6), name="Share of games",
                             customdata=curve["n"],
                             hovertemplate="Month %{x}: %{y:.1f}% within the tolerance"
                                           "<br>n = %{customdata:,}<extra></extra>"))
    fig.add_hline(y=100 * target, line_dash="dash", line_color=GREY)
    if not np.isnan(rule_k):
        fig.add_vline(x=rule_k, line_color=RED, line_width=1.5)
        fig.add_annotation(x=rule_k, y=8, text=f"month {int(rule_k)}", showarrow=False,
                           xanchor="left", font=dict(color=RED, size=13))
    fig.update_xaxes(title="Months since entering the ranking")
    fig.update_yaxes(title=f"% of games within ±{tolerance:.2f} of final rating", range=[0, 100])
    fig.update_layout(showlegend=False)
    return base_layout(fig, height=380, legend_below=False)


def fig_adjusted(bars: pd.DataFrame, tol: float) -> go.Figure:
    """Grouped bars: share within tolerance at each launch age, displayed vs adjusted rating."""
    fig = go.Figure()
    for pred, color in (("Displayed rating", GREY), ("Adjusted launch rating", BLUE)):
        d = bars[bars["predictor"] == pred]
        fig.add_trace(go.Bar(
            x=[f"Month {k}" for k in d["k"]], y=100 * d["share_within"], name=pred,
            marker_color=color, text=[f"{100 * v:.0f}%" for v in d["share_within"]],
            textposition="outside", customdata=np.stack([d["mae"], d["n"]], axis=1),
            hovertemplate=pred + "<br>%{y:.1f}% within the tolerance<br>MAE %{customdata[0]:.3f}"
                                 "<br>test n = %{customdata[1]:,}<extra></extra>"))
    fig.update_layout(barmode="group")
    fig.update_yaxes(title=f"% of test games within ±{tol} of final", range=[0, 105])
    return base_layout(fig, height=360)


def fig_lookup(game: dict, traj: pd.DataFrame, cohort_curve: pd.DataFrame,
               new_col: str) -> go.Figure:
    """Game trajectory: displayed average, new-rater dots, cohort reference and raters panel."""
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.72, 0.28],
                        vertical_spacing=0.06)
    t = traj.sort_values("k")
    fig.add_trace(go.Scatter(x=t["k"], y=t["avg_rating"], mode="lines+markers", name="Displayed",
                             line=dict(color=BLUE, width=2.6), marker=dict(size=4),
                             hovertemplate="Month %{x}: %{y:.2f}<extra>Displayed average</extra>"),
                  row=1, col=1)
    ok = t.dropna(subset=[new_col])
    fig.add_trace(go.Scatter(x=ok["k"], y=ok[new_col], mode="markers", name="New raters (3-month)",
                             marker=dict(color=RED, size=7),
                             hovertemplate="Month %{x}: %{y:.2f}<extra>New raters</extra>"),
                  row=1, col=1)
    ref = cohort_curve[cohort_curve["k"] <= t["k"].max()]
    fig.add_trace(go.Scatter(x=ref["k"], y=game["avg_m0"] + ref["mean"], mode="lines",
                             name="Launch-year cohort (avg path)",
                             line=dict(color=GREY, dash="dash", width=2),
                             hovertemplate="Month %{x}: %{y:.2f}<extra>Cohort path</extra>"),
                  row=1, col=1)
    fig.add_trace(go.Scatter(x=t["k"], y=t["n_raters"], mode="lines", name="Raters",
                             line=dict(color=GREEN, width=2), showlegend=False,
                             hovertemplate="Month %{x}: %{y:,} raters<extra></extra>"),
                  row=2, col=1)
    fig.update_yaxes(title_text="Rating", row=1, col=1)
    fig.update_yaxes(title_text="Raters (log)", type="log", row=2, col=1)
    fig.update_xaxes(title_text="Months since entering the ranking", row=2, col=1)
    return base_layout(fig, height=520)
