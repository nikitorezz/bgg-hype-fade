"""Re-export of the project's single number-formatting helper (canonical copy: app/lib/fmt.py).

The deployed dashboard only ships ``app/``, so the helper lives there; the pipeline loads that
same file instead of keeping a second copy.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_PATH = Path(__file__).resolve().parents[2] / "app" / "lib" / "fmt.py"
_spec = importlib.util.spec_from_file_location("bgg_app_fmt", _PATH)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

fmt = _mod.fmt
pct = _mod.pct
round_half_up = _mod.round_half_up
