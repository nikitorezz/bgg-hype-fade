# CLAUDE.md: BGG Hype Fade

Context for AI coding assistants working in this repository.

## What this project is

A published data-analytics portfolio project: *"Does the hype fade? How board-game ratings change after launch."* It uses ten years of daily BoardGameGeek ranking snapshots to measure how much and how fast new games' average ratings fall, whether hype predicts the fall, and when a rating can be trusted. The audience is hiring managers and analytics leads, so readable SQL, honest reporting and a clean interface matter as much as the results.

- Write-up: `reports/writeup.md` · technical findings: `docs/findings.md`
- Data facts, quality fixes and definitions: `docs/data_notes.md` (**read before changing SQL**)
- Deployment: `docs/deploy.md` · how it was built: `docs/project-history/`

## Status

Complete and published (Streamlit dashboard, GitHub Pages project page, GitHub repository). Work now is maintenance: fixes, small improvements, keeping docs and numbers consistent.

## Rules

- **Publication (data):** the dashboard publishes a compact per-game extract (`app/data/games.parquet`, `trajectories.parquet`, `other_games.parquet`: ratings, rater counts and ranks per game and month, no personal data), by the author's decision; the source archive has no licence. Never commit or deploy `data/external/`, `data/raw|interim|processed/` or `reports/tables/examples.csv`, and keep the Kickstarter flag out of the per-game files (it derives from CC BY-SA metadata; only group averages are published).
- **Numbers:** every number in docs, figures, the app and the static site comes from `reports/results/key_numbers.json` or a `reports/tables/*.csv`. The README is rendered from `README.template.md` (`scripts/render_readme.py`; CI fails if it is stale). Format numbers with `fmt()` (half-up rounding).
- **Research definitions are decisions:** entry month, left-censoring, the new-release rule, the main-sample window, the raw average as outcome, the new-rater usability rule, equal weight per game, model specifications A–D. Don't change them silently, and never pick a specification because its result looks better.
- **Config, not constants:** thresholds and dates live in `config.yaml`; SQL lives in numbered files under `sql/`.
- **Design:** charts follow `app/lib/charts.py` (quiet axes, horizontal grid only, end labels instead of legends, bands only on single-series charts, blue ramp for ordered groups, palette blue `#1F5AA6`, red `#C62F2F` for worse, green `#1E8A4C` for better, Kickstarter green `#05CE78` for Kickstarter games; only two text colours, ink and muted). Matplotlib figures use the same palette via `src/bgg/style.py`.

## Environment

- Author's machine: Windows, project path with spaces (quote it; use `pathlib`). Python ≥ 3.11 with `uv`.
- Entry point: `uv run bgg <stage>` (`all`, `analysis`, `dashboard-data`, `export-static`, ...); no `make`.
- Checks: `uv run pytest`, `uv run ruff check .`, `uv run python scripts/render_readme.py --check`.
- Downloads come from GitHub; if slow, set `HTTPS_PROXY` or use `--backend git`.
