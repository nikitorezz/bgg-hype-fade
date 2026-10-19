"""Take screenshots of every dashboard section (uses the installed Chrome via Playwright).

Usage: uv run python scripts/app_screenshots.py [--mode full|aggregates] [--mobile]
Starts its own Streamlit server on a free port, writes reports/figures/app_*.png.
``--mobile`` emulates an iPhone (390 px, touch, phone user agent), so the compact layout is used.
"""

from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SECTIONS = {"The fade": "overview", "Look up a game": "lookup", "New vs displayed": "gap",
            "Hype": "hype", "When to trust": "trust", "Explore": "explore", "Method": "method"}


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="full")
    ap.add_argument("--mobile", action="store_true")
    args = ap.parse_args()
    port = free_port()
    env = {**os.environ, "BGG_APP_MODE": args.mode}
    server = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", str(ROOT / "app" / "streamlit_app.py"),
         "--server.port", str(port), "--server.headless", "true"], cwd=ROOT, env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(80):
            try:
                urllib.request.urlopen(f"http://localhost:{port}/_stcore/health", timeout=1)
                break
            except OSError:
                time.sleep(0.5)
        suffix = "_mobile" if args.mobile else ""
        out = ROOT / "reports" / "figures"
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome")
            ctx = (browser.new_context(**p.devices["iPhone 13"]) if args.mobile
                   else browser.new_context(viewport={"width": 1280, "height": 900}))
            page = ctx.new_page()
            page.goto(f"http://localhost:{port}", wait_until="networkidle")
            page.wait_for_timeout(2500)
            nav = page.locator('[data-testid="stButtonGroup"]').first
            size = page.viewport_size
            for name, slug in SECTIONS.items():
                pill = nav.locator("button", has_text=name)
                if pill.count() == 0:
                    continue
                pill.first.click()
                page.wait_for_timeout(2500)
                # Streamlit scrolls an inner container, so size the viewport to the content
                height = page.evaluate(
                    "document.querySelector('[data-testid=\"stMain\"]').scrollHeight")
                page.set_viewport_size({"width": size["width"], "height": int(height) + 20})
                page.wait_for_timeout(1500)
                page.screenshot(path=str(out / f"app_{slug}{suffix}.png"))
                page.set_viewport_size(size)
                print("saved", f"app_{slug}{suffix}.png")
            browser.close()
    finally:
        server.terminate()


if __name__ == "__main__":
    main()
