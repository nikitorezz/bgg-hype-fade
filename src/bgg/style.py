"""One shared matplotlib style, matching the dashboard (same palette, quiet axes, light grid).

Blue for data, red for worse and green for better (always paired with a sign or label),
Kickstarter's own green for Kickstarter games; ordered groups use one blue ramp.
"""

from __future__ import annotations

import matplotlib
from matplotlib import font_manager

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

# two text colours: ink and muted
INK, INK_2, INK_3 = "#1B2430", "#667085", "#667085"
GRID = "#E9EDF2"
PALETTE = {
    "blue": "#1F5AA6", "plum": "#C62F2F", "amber": "#C27803", "grey": "#8B95A5",
    "ks": "#05CE78",  # Kickstarter's own green
    # legacy names used by older figure code
    "red": "#C62F2F", "orange": "#C27803", "green": "#1E8A4C", "sky": "#A9C4E8",
    "purple": "#6B5FB5", "yellow": "#C27803",
}
CYCLE = [PALETTE[c] for c in ("blue", "ks", "red", "grey")]
# Ordered quartiles (1 = least hyped .. 4 = most hyped): one hue, light to dark.
SEQ4 = ["#A9C4E8", "#7796BE", "#446895", "#123A6B"]


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
