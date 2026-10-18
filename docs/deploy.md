# Deploying the dashboard

**Status: D0 decided (2026-10-18): option 2, aggregates-only.** The repo is prepared for a public
aggregates-only deployment; the app itself has not been deployed yet (needs a GitHub remote and a
Streamlit Cloud account; see the checklist below).

## Deployment checklist (aggregates-only)

- [x] `uv run bgg dashboard-data --aggregates-only` -> `app/data/` holds only `tables/*.csv`,
  `key_numbers.json`, `app_config.json` (0.2 MB, no game names or per-game numbers).
- [x] `.gitignore` keeps all game-level files out: `app/data/*.parquet`, `data/external/`,
  `reports/tables/examples.csv`, `reports/figures/app_lookup*.png`.
- [x] Without `games.parquet` the app switches to aggregates mode by itself (tested).
- [x] History purged (2026-10-18): `data/external/`, `reports/tables/examples.csv` and the lookup
  screenshots were removed from every commit (see "History").
- [ ] Create the GitHub repository, push, then deploy on Streamlit Community Cloud (steps below).

### History

`data/external/kaggle_bgg/*` (including `user_ratings.csv` with usernames) and a few game-level
files had been committed locally before they were ignored (first in commit `3b9e761`). Before any
push, history was rewritten with `git filter-branch` to drop them from every commit; the largest
blob left in the repository is under 1 MB. Commits before the Analysis steps 1-2 commit keep their
hashes; later ones changed (for example `3b9e761` -> `100ce64`, and `5faf5e1` -> `6b913b5`).

## Build the app data

```bash
uv run bgg all                       # pipeline (once)
uv run bgg analysis                  # figures, models, key_numbers.json
uv run bgg dashboard-data            # app/data (full)   -- or --aggregates-only
uv run streamlit run app/streamlit_app.py
```

`APP_MODE=full` (default) or `APP_MODE=aggregates`. In aggregates mode the app also falls back
automatically if `app/data/games.parquet` is absent.

## Streamlit Community Cloud (after D0)

1. Push the repository to GitHub (after the history clean-up). `app/data/` (tables, key numbers,
   app config) is already committed; the parquet files are ignored.
2. On <https://share.streamlit.io>, create an app: repository = yours, branch = `main`, main file
   = `app/streamlit_app.py`. Dependencies come from `app/requirements.txt` (pinned). No secrets.
3. Set the environment variable `APP_MODE` to `aggregates` (Advanced settings), to be explicit.
   Optionally set `BGG_REPO_URL` and `BGG_WRITEUP_URL` to show the links in the "Method & data" tab.
4. The theme is in `.streamlit/config.toml` at the repository root (light theme, minimal toolbar).

Caveat: Streamlit Community Cloud (`*.streamlit.app`) may be slow or unreachable from mainland
China. The intended audience is international, but the author cannot rely on it for local demos.

## Fallback: static page for GitHub Pages

```bash
uv run bgg export-static        # writes reports/site/index.html (about 5 MB)
```

A single self-contained HTML file (Plotly inlined, no CDN, no lookup, no sliders). It opens offline
and needs only aggregate tables. To host it on GitHub Pages, copy `reports/site/index.html` to a
`docs/` folder or a `gh-pages` branch (the file is git-ignored by default because of its size).

## Screenshots for the README

```bash
uv run python scripts/app_screenshots.py            # desktop, writes reports/figures/app_*.png
uv run python scripts/app_screenshots.py --mobile   # 400 px wide, app_*_mobile.png
```

Uses the installed Chrome through Playwright (no browser download).
