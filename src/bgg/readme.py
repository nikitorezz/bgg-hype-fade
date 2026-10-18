"""Render README.md from README.template.md so every number comes from key_numbers.json.

Template syntax
  ``{{key|abs|pct:.0f}}``     a key number (transforms ``abs``/``pct``, half-up formatting)
  ``{{@name}}``               a link/value from the ``publish:`` section of config.yaml
  ``{{#if name}} ... {{/if}}`` kept only when ``publish.name`` is non-empty
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from bgg.analysis.titles import fill
from bgg.config import Config

_IF = re.compile(r"\{\{#if (\w+)\}\}\n?(.*?)\{\{/if\}\}\n?", re.S)
_LINK = re.compile(r"\{\{@(\w+)\}\}")
_NUM = re.compile(r"\{\{([^{}@#/][^{}]*)\}\}")


def render(template: str, numbers: dict[str, dict], publish: dict[str, str]) -> str:
    """Fill conditionals, publish values and key-number placeholders."""
    out = _IF.sub(lambda m: m.group(2) if publish.get(m.group(1)) else "", template)
    out = _LINK.sub(lambda m: str(publish.get(m.group(1)) or ""), out)
    return _NUM.sub(lambda m: fill("{" + m.group(1) + "}", numbers), out)


def render_readme(cfg: Config) -> str:
    """The README text implied by the template, key_numbers.json and config.yaml."""
    template = (cfg.root / "README.template.md").read_text(encoding="utf-8")
    nums = json.loads((cfg.root / cfg.section("analysis")["results_dir"] / "key_numbers.json")
                      .read_text(encoding="utf-8"))["numbers"]
    return render(template, nums, cfg.section("publish"))


def readme_path(cfg: Config) -> Path:
    return cfg.root / "README.md"
