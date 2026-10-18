"""One number-formatting helper for the whole project (stdlib only, so the deployed app can use it).

Python's ``format(0.365, ".2f")`` rounds the *binary* float and gives ``0.36``; a reader doing the
sum by hand expects ``0.37``. Every displayed number goes through :func:`fmt`, which rounds the
shortest decimal representation half-up instead.
"""

from __future__ import annotations

import math
import re
from decimal import ROUND_HALF_UP, Decimal

_SPEC = re.compile(r"^(?P<sign>\+?)(?P<comma>,?)\.(?P<digits>\d+)f$")


def round_half_up(x: float, digits: int = 2) -> Decimal:
    """Round ``x`` to ``digits`` decimals, ties away from zero, on its shortest decimal form."""
    q = Decimal(1).scaleb(-digits)
    return Decimal(repr(float(x))).quantize(q, rounding=ROUND_HALF_UP)


def fmt(x: float | None, spec: str = ".2f", minus: bool = False) -> str:
    """Format like ``format(x, spec)`` for specs ``[+][,].Nf`` but with half-up rounding.

    Other specs fall back to the standard formatter. ``minus=True`` uses the typographic minus.
    NaN/None give an en dash.
    """
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "–"
    m = _SPEC.match(spec)
    if not m:
        out = format(x, spec)
    else:
        d = round_half_up(x, int(m["digits"]))
        body = format(abs(d), f"{m['comma']}.{m['digits']}f")
        neg = d < 0
        sign = "-" if neg else ("+" if m["sign"] else "")
        out = f"{sign}{body}"
    return out.replace("-", "−") if minus else out


def pct(x: float | None, digits: int = 0) -> str:
    """A share as a percentage string with half-up rounding (0.609 -> '61%')."""
    if x is None:
        return "–"
    return f"{fmt(100 * x, f'.{digits}f')}%"
