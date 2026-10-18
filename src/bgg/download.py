"""Step 1: list archive files, select one valid snapshot per month, download, write manifest."""

from __future__ import annotations

import csv
import hashlib
import logging
import os
import re
import shutil
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from bgg.config import Config

log = logging.getLogger(__name__)

EXPECTED_HEADER = "ID,Name,Year,Rank,Average,Bayes average,Users rated,URL,Thumbnail"
MANIFEST_COLUMNS = ["month", "chosen_file", "chosen_date", "rows", "status", "rejected",
                    "bytes", "sha256", "downloaded_at"]
CHUNK = 1 << 20


# --------------------------------------------------------------------------- selection
@dataclass
class Decision:
    """Outcome of the monthly selection for one month."""

    month: date
    chosen: date | None
    rows: int
    status: str  # ok | substituted | fallback | missing
    rejected: list[tuple[date, int]] = field(default_factory=list)


def select_monthly(
    candidates_by_month: dict[date, list[date]],
    row_counter: Callable[[date], int],
    ratio: float,
    prev_rows: int | None = None,
) -> list[Decision]:
    """Pick one complete snapshot per month (pure apart from ``row_counter``).

    Months are processed chronologically. A candidate is accepted when its row count is at least
    ``ratio`` x the rows of the previous accepted month; with no reference (first month) the first
    candidate is accepted. If nothing passes, the candidate with the most rows is taken and flagged
    ``fallback``. Months without candidates are ``missing``. ``prev_rows`` seeds the reference when
    the function is called one month at a time.
    """
    decisions: list[Decision] = []
    for month in sorted(candidates_by_month):
        cands = sorted(candidates_by_month[month])
        if not cands:
            decisions.append(Decision(month, None, 0, "missing"))
            continue
        tried: list[tuple[date, int]] = []
        accepted: tuple[date, int] | None = None
        for c in cands:
            rows = row_counter(c)
            if prev_rows is None or rows >= ratio * prev_rows:
                accepted = (c, rows)
                break
            tried.append((c, rows))
        if accepted is not None:
            status = "substituted" if tried else "ok"
            decisions.append(Decision(month, accepted[0], accepted[1], status, tried))
        else:
            best = max(tried, key=lambda t: t[1])
            log.warning("%s: no candidate passed the row-count rule; fallback to %s (%d rows)",
                        month, best[0], best[1])
            decisions.append(Decision(month, best[0], best[1], "fallback",
                                      [t for t in tried if t[0] != best[0]]))
            accepted = best
        prev_rows = accepted[1]
    return decisions


def build_candidates(files: list[str], months: list[date], max_day: int) -> dict[date, list[date]]:
    """Group file dates by month, keeping days <= ``max_day``.

    If a month has files but none within the window (the archive's first file is 2016-10-12), the
    earliest file of that month is used instead.
    """
    in_window: dict[date, list[date]] = {m: [] for m in months}
    anywhere: dict[date, list[date]] = {m: [] for m in months}
    for name in files:
        d = date.fromisoformat(name[:-4])
        m = d.replace(day=1)
        if m in in_window:
            anywhere[m].append(d)
            if d.day <= max_day:
                in_window[m].append(d)
    for m in months:
        if not in_window[m] and anywhere[m]:
            first = min(anywhere[m])
            log.warning("%s: no file on days 1-%d; using earliest file %s", m, max_day, first)
            in_window[m] = [first]
    return in_window


# --------------------------------------------------------------------------- file helpers
def count_rows(path: Path) -> int:
    """Data rows = line count - header (handles a missing final newline)."""
    last = b"\n"
    with path.open("rb") as fh:
        header = fh.readline().decode("utf-8-sig").strip()
        if header != EXPECTED_HEADER:
            raise ValueError(f"{path.name}: unexpected header {header!r}")
        lines = 1
        while chunk := fh.read(CHUNK):
            lines += chunk.count(b"\n")
            last = chunk[-1:]
    if last != b"\n":
        lines += 1
    return lines - 1


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(CHUNK):
            h.update(chunk)
    return h.hexdigest()


def _filename(d: date) -> str:
    return f"{d.isoformat()}.csv"


# --------------------------------------------------------------------------- backends
class HttpBackend:
    """GitHub tree API for listing, raw.githubusercontent.com for files (resumable)."""

    def __init__(self, cfg: Config) -> None:
        d, self.s = cfg.section("download"), cfg.section("source")
        self.timeout = d["timeout_seconds"]
        self.session = requests.Session()  # trust_env stays on: HTTPS_PROXY is honoured
        retry = Retry(total=d["max_retries"], backoff_factor=d["backoff_factor"],
                      status_forcelist=[429, 500, 502, 503, 504], allowed_methods=["GET"],
                      respect_retry_after_header=True)
        self.session.mount("https://", HTTPAdapter(max_retries=retry))
        self.session.headers["User-Agent"] = "bgg-hype-fade-pipeline"

    def list_files(self) -> list[str]:
        url = self.s["tree_api_url"].format(repo=self.s["repo"], branch=self.s["branch"])
        resp = self.session.get(url, timeout=self.timeout)
        if resp.status_code in (403, 429):
            raise RuntimeError(f"GitHub API rate-limited (HTTP {resp.status_code}); "
                               "rerun with --backend git")
        resp.raise_for_status()
        data = resp.json()
        if data.get("truncated"):
            raise RuntimeError("GitHub tree response is truncated; rerun with --backend git")
        pat = re.compile(self.s["filename_pattern"])
        return sorted(e["path"] for e in data["tree"] if pat.match(e["path"]))

    def fetch(self, name: str, dest: Path) -> None:
        url = self.s["raw_url_template"].format(repo=self.s["repo"], branch=self.s["branch"],
                                                file=name)
        part = dest.with_suffix(dest.suffix + ".part")
        for attempt in range(1, 4):
            have = part.stat().st_size if part.exists() else 0
            headers = {"Range": f"bytes={have}-"} if have else {}
            try:
                with self.session.get(url, headers=headers, stream=True,
                                      timeout=self.timeout) as r:
                    if r.status_code != 416:  # 416: .part is already complete
                        r.raise_for_status()
                        mode = "ab" if r.status_code == 206 else "wb"
                        with part.open(mode) as fh:
                            for chunk in r.iter_content(CHUNK):
                                fh.write(chunk)
                break
            except (requests.RequestException, OSError) as exc:
                log.warning("download of %s failed (attempt %d): %s", name, attempt, exc)
                if attempt == 3:
                    raise
                time.sleep(2 ** attempt)
        os.replace(part, dest)


class GitBackend:
    """Blobless clone; list with ``ls-tree --name-only`` (never ``-l``), check out per file."""

    def __init__(self, cfg: Config) -> None:
        self.url = cfg.section("source")["git_url"]
        self.repo_dir = cfg.path("raw_dir") / "_git"
        self.pat = re.compile(cfg.section("source")["filename_pattern"])

    def _git(self, *args: str) -> str:
        res = subprocess.run(["git", "-C", str(self.repo_dir), *args], check=True,
                             capture_output=True, text=True)
        return res.stdout

    def list_files(self) -> list[str]:
        if not (self.repo_dir / ".git").exists():
            log.info("cloning %s (blobless) ...", self.url)
            subprocess.run(["git", "clone", "--filter=blob:none", "--no-checkout", "--depth", "1",
                            self.url, str(self.repo_dir)], check=True)
        names = self._git("ls-tree", "--name-only", "HEAD").split()
        return sorted(n for n in names if self.pat.match(n))

    def fetch(self, name: str, dest: Path) -> None:
        self._git("checkout", "HEAD", "--", name)
        src = self.repo_dir / name
        part = dest.with_suffix(dest.suffix + ".part")
        shutil.copyfile(src, part)
        os.replace(part, dest)
        src.unlink()


# --------------------------------------------------------------------------- orchestration
def _read_old_manifest(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as fh:
        return {r["month"]: r for r in csv.DictReader(fh)}


def run_download(cfg: Config, backend: str | None = None) -> list[Decision]:
    """Select, download and record one valid snapshot per month; returns the decisions."""
    dl = cfg.section("download")
    backend = backend or dl["backend"]
    raw_dir, rej_dir, manifest = cfg.path("raw_dir"), cfg.path("rejected_dir"), cfg.path("manifest")
    raw_dir.mkdir(parents=True, exist_ok=True)
    rej_dir.mkdir(parents=True, exist_ok=True)
    be = HttpBackend(cfg) if backend == "http" else GitBackend(cfg)

    files = be.list_files()
    log.info("archive lists %d snapshot files (%s .. %s)", len(files), files[0], files[-1])
    months = cfg.months
    cands = build_candidates(files, months, dl["max_candidate_day"])
    old = _read_old_manifest(manifest)
    new_files = 0

    def counter(d: date) -> int:
        nonlocal new_files
        name = _filename(d)
        for folder in (raw_dir, rej_dir):  # rejected files from earlier runs are reused too
            if (folder / name).exists():
                return count_rows(folder / name)
        t0 = time.time()
        be.fetch(name, raw_dir / name)
        new_files += 1
        log.info("  downloaded %s: %.1f MB in %.1fs", name,
                 (raw_dir / name).stat().st_size / 1e6, time.time() - t0)
        return count_rows(raw_dir / name)

    decisions: list[Decision] = []
    prev_rows: int | None = None
    for i, month in enumerate(months, 1):
        d = select_monthly({month: cands[month]}, counter, dl["min_row_ratio"], prev_rows)[0]
        decisions.append(d)
        if d.chosen is not None:
            prev_rows = d.rows
        else:
            log.error("%s: no snapshot file exists", month)
        log.info("month %d/%d %s -> %s rows=%d status=%s rejected=%s", i, len(months),
                 month.strftime("%Y-%m"), d.chosen, d.rows, d.status, d.rejected or "-")
        for rd, _ in d.rejected:
            src = raw_dir / _filename(rd)
            if src.exists():
                os.replace(src, rej_dir / src.name)

    _write_manifest(manifest, decisions, raw_dir, old)
    log.info("download done: %d months, %d newly downloaded files, manifest -> %s",
             len(decisions), new_files, manifest)
    return decisions


def _write_manifest(path: Path, decisions: list[Decision], raw_dir: Path,
                    old: dict[str, dict[str, str]]) -> None:
    rows = []
    for d in decisions:
        if d.chosen is None:
            continue
        name = _filename(d.chosen)
        f = raw_dir / name
        key = d.month.isoformat()
        prev = old.get(key)
        if prev and prev["chosen_file"] == name:
            when = prev["downloaded_at"]  # keep the original timestamp so reruns are identical
        else:
            when = datetime.fromtimestamp(f.stat().st_mtime, UTC).isoformat(timespec="seconds")
        rows.append({
            "month": key, "chosen_file": name, "chosen_date": d.chosen.isoformat(),
            "rows": d.rows, "status": d.status,
            "rejected": ";".join(f"{rd.isoformat()}:{n}" for rd, n in d.rejected),
            "bytes": f.stat().st_size, "sha256": sha256_of(f), "downloaded_at": when,
        })
    tmp = path.with_suffix(".csv.part")
    with tmp.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=MANIFEST_COLUMNS)
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, path)
