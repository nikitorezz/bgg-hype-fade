"""Action titles for figures: templates live in config.yaml, numbers come from key_numbers."""

from __future__ import annotations

import re

from bgg.config import Config

_PLACEHOLDER = re.compile(r"\{(\w+)((?:\|\w+)*)(?::([^}]*))?\}")
_TRANSFORMS = {"abs": abs, "pct": lambda v: 100 * v}


def fill(template: str, numbers: dict[str, dict]) -> str:
    """Replace ``{key|transform:fmt}`` placeholders with values from ``numbers``.

    Transforms: ``abs`` (absolute value) and ``pct`` (x100). Unknown keys raise, so a title can
    never silently show a stale or invented number.
    """
    def sub(m: re.Match[str]) -> str:
        key, transforms, fmt = m.group(1), m.group(2), m.group(3) or ""
        if key not in numbers:
            raise KeyError(f"title placeholder {key!r} has no key number")
        value = numbers[key]["value"]
        for t in filter(None, transforms.split("|")):
            value = _TRANSFORMS[t](value)
        return format(value, fmt)

    return _PLACEHOLDER.sub(sub, template)


def figure_titles(cfg: Config, fig_id: str, numbers: dict[str, dict]) -> tuple[str, str]:
    """(title, subtitle) for ``fig_id`` rendered from the config templates."""
    t = cfg.section("analysis")["titles"][fig_id]
    return fill(t["title"], numbers), fill(t.get("subtitle", ""), numbers)
