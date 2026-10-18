"""One shared matplotlib style: colour-blind-safe palette (Okabe-Ito), fonts, grid."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

PALETTE = {
    "blue": "#0072B2", "orange": "#E69F00", "green": "#009E73", "red": "#D55E00",
    "purple": "#CC79A7", "sky": "#56B4E9", "yellow": "#F0E442", "grey": "#666666",
}
CYCLE = [PALETTE[c] for c in ("blue", "orange", "green", "red", "purple", "sky", "grey")]
SEQ4 = ["#56B4E9", "#0072B2", "#E69F00", "#D55E00"]  # hype quartiles 1 (least) .. 4 (most)


def apply_style() -> None:
    """Set rcParams once per process."""
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 10, "axes.titlesize": 11,
        "axes.titleweight": "bold", "axes.labelsize": 10, "legend.fontsize": 9,
        "legend.frameon": False, "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": "#DDDDDD", "grid.linewidth": 0.6,
        "axes.prop_cycle": matplotlib.cycler(color=CYCLE), "figure.dpi": 100,
        "savefig.bbox": "tight",
    })


apply_style()
