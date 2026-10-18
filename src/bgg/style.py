"""One shared matplotlib style, matching the dashboard (same palette, quiet axes, light grid).

Palette checked with a colour-blind validator: blue, plum and amber are separable under all
common colour-vision deficiencies; ordered groups use one blue ramp, light to dark.
"""

from __future__ import annotations

import matplotlib
from matplotlib import font_manager

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

INK, INK_2, INK_3 = "#1D2533", "#4A5466", "#6B7585"
GRID = "#E9EDF2"
PALETTE = {
    "blue": "#2167B0", "plum": "#B23F68", "amber": "#B3770A", "grey": "#7A8494",
    # legacy names used by older figure code
    "red": "#B23F68", "orange": "#B3770A", "green": "#2E8B57", "sky": "#93B8E0",
    "purple": "#6B5FB5", "yellow": "#B3770A",
}
CYCLE = [PALETTE[c] for c in ("blue", "amber", "plum", "grey")]
# Ordered quartiles (1 = least hyped .. 4 = most hyped): one hue, light to dark.
SEQ4 = ["#93B8E0", "#5A8FCB", "#2E66A8", "#0D3462"]


def ramp(n: int) -> list[str]:
    """n steps of the blue ramp, light to dark."""
    lo, hi = (0x93, 0xB8, 0xE0), (0x0D, 0x34, 0x62)
    out = []
    for i in range(n):
        t = i / max(n - 1, 1)
        out.append("#" + "".join(f"{round(a + (b - a) * t):02x}" for a, b in zip(lo, hi,
                                                                               strict=True)))
    return out


def _font() -> str:
    """IBM Plex Sans if installed (as on the dashboard), otherwise DejaVu Sans."""
    names = {f.name for f in font_manager.fontManager.ttflist}
    return "IBM Plex Sans" if "IBM Plex Sans" in names else "DejaVu Sans"


def apply_style() -> None:
    """Set rcParams once per process."""
    plt.rcParams.update({
        "font.family": _font(), "font.size": 10, "text.color": INK,
        "axes.titlesize": 10, "axes.titleweight": "bold", "axes.titlelocation": "left",
        "axes.titlecolor": INK, "axes.labelsize": 9.5, "axes.labelcolor": INK_3,
        "axes.edgecolor": GRID, "axes.spines.top": False, "axes.spines.right": False,
        "axes.spines.left": False, "axes.grid": True, "axes.grid.axis": "y",
        "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
        "xtick.color": INK_3, "ytick.color": INK_3, "xtick.labelsize": 9, "ytick.labelsize": 9,
        "xtick.major.size": 0, "ytick.major.size": 0, "xtick.major.pad": 6,
        "legend.fontsize": 9, "legend.frameon": False,
        "axes.prop_cycle": matplotlib.cycler(color=CYCLE), "figure.dpi": 100,
        "figure.facecolor": "white", "savefig.bbox": "tight", "savefig.facecolor": "white",
        "lines.solid_capstyle": "round", "errorbar.capsize": 0,
    })


apply_style()
