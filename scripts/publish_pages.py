"""Build the static dashboard and (optionally) publish it to the ``gh-pages`` branch.

    uv run python scripts/publish_pages.py            # build reports/site/ only, print next steps
    uv run python scripts/publish_pages.py --push     # also force-push one orphan commit to origin/gh-pages

The pushed branch holds index.html (small landing page for link previews), dashboard.html (about 5 MB),
social_card.png and .nojekyll as a single
commit, so the main repository history never grows with the Plotly bundle. Aggregate data only.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from bgg.config import load_config
from bgg.static_export import run_export_static

FILES = ("index.html", "dashboard.html", "social_card.png", ".nojekyll")


def git(*args: str, cwd: Path) -> str:
    res = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return res.stdout.strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--push", action="store_true", help="force-push the page to origin/gh-pages")
    ap.add_argument("--remote", help="push to this URL/path instead of the origin remote")
    args = ap.parse_args()
    cfg = load_config()
    site = run_export_static(cfg).parent
    print(f"built {site}: {', '.join(f for f in FILES if (site / f).exists())}")
    if not args.push:
        print("Not pushed. After the GitHub repository exists, run with --push, then enable "
              "Settings -> Pages -> Deploy from branch -> gh-pages / (root).")
        return 0
    remote = args.remote or git("remote", "get-url", "origin", cwd=cfg.root)
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        for f in FILES:
            shutil.copyfile(site / f, work / f)
        git("init", "-q", "-b", "gh-pages", cwd=work)
        git("add", "-A", cwd=work)
        git("-c", "user.name=bgg-pages", "-c", "user.email=noreply@users.noreply.github.com",
            "commit", "-q", "-m", "Publish static dashboard", cwd=work)
        git("push", "--force", remote, "gh-pages", cwd=work)
    print(f"pushed gh-pages to {remote}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
