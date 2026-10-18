# CLAUDE.md — BGG Hype Fade

Context for Claude Code. Read this first, then `docs/handoff/01_TASK_pipeline_steps_1-5.md`.

## What this project is

A data-analytics **portfolio piece**: *"Does the Hype Fade? Post-release rating trajectories of board games on BoardGameGeek, 2016–2026."*
It uses daily snapshots of BGG's ranked list to measure how much and how fast new games' average ratings fall after launch, and whether the most-hyped launches fall hardest.

The audience is hiring managers and analytics leads, so code quality, readable SQL and honest data-quality reporting matter as much as the results.

- Full plan: `docs/implementation_plan.md` (sections 5 = pipeline, 6 = analysis)
- Original research proposal: `docs/proposal.md`
- Verified facts about the data, with traps: `docs/data_notes.md` ← **read before writing any SQL**

## Current scope

- ✅ **Done:** pipeline steps 1–5 (`docs/handoff/01_TASK_pipeline_steps_1-5.md`): `uv run bgg all`, QC 36 PASS / 0 FAIL.
- 🔨 **Now:** analysis, milestones M3–M5 (`docs/handoff/02_TASK_analysis.md`): descriptive figures, Q1 event study, Q2 hype regressions, Q4 "when to trust" rule, robustness grid, key_numbers.json, optional Q3 crowdfunding.
- ⏭ **Not yet (don't build):** Streamlit dashboard, narrative write-up, slides, daily-snapshot download.

Treat the pipeline (sql/, download/build/qc) as stable: change it only to fix a real bug, rerun `uv run bgg all` + QC afterwards, and note the change.

## Environment

- The user is on **Windows**. Project root: `G:\PROJECTS\Data Analytics\Personal\BGG Hype Fade` (**the path contains spaces**, so quote it in shell commands and use `pathlib` in code).
- Python ≥ 3.11. Use `uv` if available (`uv --version`); otherwise `python -m venv .venv` + pip. Pin dependencies (commit `uv.lock` or a pinned `requirements.txt`).
- **Don't rely on `make`** (usually missing on Windows). The orchestration entry point is a Python CLI: `uv run bgg <stage>` (console script defined in `pyproject.toml`). A Makefile is optional sugar only.
- When passing file paths into DuckDB SQL, use forward slashes (`Path.as_posix()`).
- The user is in mainland China, where GitHub (especially `raw.githubusercontent.com`) can be slow or blocked. Downloads must honour `HTTPS_PROXY`/`HTTP_PROXY`, retry with backoff, be resumable, and offer a `git` fallback backend (see the task file).

## Conventions

- **SQL first.** Transformations live in numbered, commented `sql/*.sql` files executed by `src/bgg/build.py` against a persistent DuckDB database (`data/interim/bgg.duckdb`). Every statement uses `CREATE OR REPLACE`, so each stage can be rerun.
- **Config, not constants.** Every threshold, date and rule comes from `config.yaml`. Pass scalars to SQL as DuckDB variables (`SET VARIABLE x = …;` / `getvariable('x')`). Inject file paths/lists from Python. Never hard-code a threshold in SQL.
- **Idempotent stages.** Rerunning a stage gives the same outputs. Downloads skip files already present and valid, and write via temp file + atomic rename.
- **Logging, not print.** Use the `logging` module; each stage logs row counts in and out.
- Type hints, docstrings on public functions, small functions. Lint with `ruff` and test with `pytest`.
- **Data hygiene:** never modify files in `data/raw/`. `data/raw/` and `data/interim/` are git-ignored. `data/processed/` is also git-ignored for now (redistribution decision pending; see data notes §Licence).
- **Don't use** the BGG XML API or scrape boardgamegeek.com (token required + bot check). The only data source is the GitHub archive.
- Git: `git init` if needed. Commit after each completed stage with a clear message. Add a `.gitattributes` with `* text=auto`.

## Research rules: don't change silently

These definitions are decisions, not implementation details. If the data seems to contradict one, **stop and report** instead of changing it:
- entry month, left-censoring exclusion, the new-release rule (publication year *at entry* ≥ entry year − 1)
- main-sample window (entry 2017-01 … end_month − 36 months)
- raw `Average` as the outcome (not `Bayes average`)
- new-rating average formula and its usability rule (Δraters threshold **and** rounding-error bound)
- analysis definitions in task 02 (main/balanced samples, equal weight per game as primary, control group, model specs A–D). **Never pick a specification because its result looks better.** A null or reversed H2 is a finding.

## Keeping docs current

- When you discover a new data quirk, add it to `docs/data_notes.md`.
- Append to the progress log at the bottom of `docs/implementation_plan.md` when a stage is done.
- Keep `README.md` short: what the project is, how to run steps 1–5, data source credit.
