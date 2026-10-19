"""Check the dashboard and the static pages on an emulated phone (iPhone 13, touch, 390 px wide).

Usage: uv run python scripts/mobile_check.py [--out DIR] [--mode full|aggregates] [--skip-static]

For the Streamlit app and each static page it saves one full-height screenshot per section and
prints the checks that matter on a phone: horizontal overflow, text that is too small to read,
tap targets that are too small, and Plotly charts that would swallow touch scrolling or zoom.
Uses the installed Chrome through Playwright. Exit code 1 if a check fails.
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

from playwright.sync_api import Page, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
MIN_FONT_PX = 11.0          # smallest readable text on a phone
MIN_TAP_PX = 32.0           # smallest comfortable tap target (WCAG AA minimum is 24)

JS_OVERFLOW = """() => {
  const vw = window.innerWidth, bad = [];
  for (const el of document.querySelectorAll('body *')) {
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    const st = getComputedStyle(el);
    if (st.position === 'fixed' || st.visibility === 'hidden') continue;
    let p = el.parentElement, clipped = false;
    while (p && p !== document.body) {
      const o = getComputedStyle(p);
      if (/(auto|scroll|hidden|clip)/.test(o.overflowX) && p.getBoundingClientRect().right <= vw + 1) {
        clipped = true; break;
      }
      p = p.parentElement;
    }
    if (!clipped && r.right > vw + 1) bad.push(el.tagName + '.' + (el.className || '').toString().slice(0, 40) + ' right=' + Math.round(r.right));
  }
  const root = document.scrollingElement;
  return {vw, scrollW: Math.max(root.scrollWidth, document.querySelector('[data-testid="stMain"]')?.scrollWidth || 0), bad: bad.slice(0, 8)};
}"""

JS_SMALL_TEXT = """(minPx) => {
  const out = new Map();
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    const t = walker.currentNode;
    if (!t.textContent.replace(/[​\s]/g, '')) continue;
    const el = t.parentElement;
    if (!el || ['SCRIPT', 'STYLE'].includes(el.tagName)) continue;
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    const fs = parseFloat(getComputedStyle(el).fontSize);
    if (fs < minPx) out.set(t.textContent.trim().slice(0, 30), fs);
  }
  return [...out.entries()].slice(0, 10);
}"""

JS_TAPS = """(minPx) => {
  // Inline links inside running text are exempt (WCAG 2.5.8); so are visually hidden skip links
  // and the raw checkbox/range inputs whose visible control is the label or slider around them.
  const bad = [];
  const sel = 'a[href], button, [role="tab"], [role="button"], select, input[type="text"]';
  for (const el of document.querySelectorAll(sel)) {
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0 || el.closest('.plotly')) continue;
    if (el.tagName === 'A' && el.closest('p, li, .site-foot')) continue;
    const label = (el.innerText || el.getAttribute('aria-label') || '').trim();
    if (label.startsWith('Skip to main')) continue;
    if (Math.min(r.width, r.height) < minPx) {
      bad.push((label || el.tagName).slice(0, 25) + ' ' + Math.round(r.width) + 'x' + Math.round(r.height));
    }
  }
  return bad.slice(0, 10);
}"""

JS_PLOTS = """() => [...document.querySelectorAll('.js-plotly-plot')].map(g => {
  const fl = g._fullLayout || {};
  const fixed = ['xaxis', 'yaxis'].every(a => !fl[a] || fl[a].fixedrange);
  return {dragmode: fl.dragmode, fixed, w: Math.round(g.getBoundingClientRect().width),
          h: Math.round(g.getBoundingClientRect().height)};
})"""


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def audit(page: Page, label: str, problems: list[str]) -> None:
    """Run the phone checks on the current page and print/collect findings."""
    ov = page.evaluate(JS_OVERFLOW)
    small = page.evaluate(JS_SMALL_TEXT, MIN_FONT_PX)
    taps = page.evaluate(JS_TAPS, MIN_TAP_PX)
    plots = page.evaluate(JS_PLOTS)
    loose = [p for p in plots if not p["fixed"] or p["dragmode"] not in (False, None)]
    print(f"[{label}] viewport {ov['vw']}px, content {ov['scrollW']}px, charts {len(plots)}")
    if ov["scrollW"] > ov["vw"] + 1:
        problems.append(f"{label}: horizontal overflow ({ov['scrollW']} > {ov['vw']}) {ov['bad']}")
    if small:
        problems.append(f"{label}: text under {MIN_FONT_PX}px: {small}")
    if taps:
        problems.append(f"{label}: small tap targets: {taps}")
    if loose:
        problems.append(f"{label}: {len(loose)} chart(s) capture touch drag/zoom: {loose[:2]}")
    narrow = [p for p in plots if p["w"] > ov["vw"] + 1]
    if narrow:
        problems.append(f"{label}: chart wider than the screen: {narrow[:2]}")


def shot(page: Page, path: Path, inner: str | None = None) -> None:
    """Full-height screenshot (Streamlit scrolls an inner container, so resize the viewport)."""
    vp = page.viewport_size
    h = page.evaluate("(sel) => (sel ? document.querySelector(sel) : document.scrollingElement)"
                      ".scrollHeight", inner)
    page.set_viewport_size({"width": vp["width"], "height": int(h) + 10})
    page.wait_for_timeout(700)
    page.screenshot(path=str(path))
    page.set_viewport_size(vp)


def check_app(p, out: Path, mode: str, problems: list[str]) -> None:
    port = free_port()
    env = {**os.environ, "BGG_APP_MODE": mode}
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
        browser = p.chromium.launch(channel="chrome")
        ctx = browser.new_context(**p.devices["iPhone 13"])
        page = ctx.new_page()
        page.goto(f"http://localhost:{port}", wait_until="networkidle")
        page.wait_for_timeout(2500)
        nav = page.locator('[data-testid="stButtonGroup"]').first
        names = [b.inner_text().strip() for b in nav.locator("button").all()]
        print("app sections:", names)
        for i, name in enumerate(names):
            nav.locator("button", has_text=name).first.tap()
            page.wait_for_timeout(2200)
            slug = "".join(c if c.isalnum() else "_" for c in name.lower()).strip("_")
            audit(page, f"app/{name}", problems)
            shot(page, out / f"app_{i}_{slug}.png", '[data-testid="stMain"]')
        browser.close()
    finally:
        server.terminate()


def check_static(p, out: Path, problems: list[str]) -> None:
    site = ROOT / "reports" / "site"
    browser = p.chromium.launch(channel="chrome")
    ctx = browser.new_context(**p.devices["iPhone 13"], offline=True)
    for name in ("index.html", "dashboard.html"):
        page = ctx.new_page()
        page.goto((site / name).as_uri(), wait_until="load")
        page.wait_for_timeout(2500)
        audit(page, f"static/{name}", problems)
        shot(page, out / f"static_{name.replace('.html', '')}.png")
        page.close()
    browser.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "data" / "interim" / "mobile_check"))
    ap.add_argument("--mode", default="full")
    ap.add_argument("--skip-static", action="store_true")
    ap.add_argument("--skip-app", action="store_true")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    problems: list[str] = []
    with sync_playwright() as p:
        if not args.skip_app:
            check_app(p, out, args.mode, problems)
        if not args.skip_static:
            check_static(p, out, problems)
    print(f"\nscreenshots in {out}")
    if problems:
        print(f"\n{len(problems)} problem(s):")
        for line in problems:
            print(" -", line)
        return 1
    print("\nall phone checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
