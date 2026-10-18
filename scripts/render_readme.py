"""Render README.md from README.template.md (numbers from reports/results/key_numbers.json).

Usage: uv run python scripts/render_readme.py          # write README.md
       uv run python scripts/render_readme.py --check  # exit 1 if README.md is stale
"""

from __future__ import annotations

import argparse
import sys

from bgg.config import load_config
from bgg.readme import readme_path, render_readme


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="fail if README.md differs")
    args = ap.parse_args()
    cfg = load_config()
    text = render_readme(cfg)
    path = readme_path(cfg)
    if args.check:
        current = path.read_text(encoding="utf-8") if path.exists() else ""
        if current != text:
            print("README.md is stale: run `uv run python scripts/render_readme.py`")
            return 1
        return 0
    path.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {path} ({len(text.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
