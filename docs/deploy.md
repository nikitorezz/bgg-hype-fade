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
- [ ] **Before the first push: purge game-level files from git history** (see "History" below).
- [ ] Create the GitHub repository, push, then deploy on Streamlit Community Cloud (steps below).

### History

`data/external/kaggle_bgg/*` (including `user_ratings.csv` with usernames) and a few game-level
files were committed locally before they were ignored (first in commit `3b9e761`). The repository
has no remote yet, so nothing has been published, but the history must be rewritten (for example
`git filter-repo --invert-paths --path data/external --path reports/tables/examples.csv`) **before**
pushing. That changes commit hashes, including the `5faf5e1` cited in `docs/findings.md`.

## D0: what may be published? (decision needed)

The source archive (`beefsack/bgg-ranking-historicals`) has **no licence file**, so by default no
reuse rights are granted (`docs/data_notes.md` §9). Three options:

1. **Ask the archive owner, then deploy the full app.** Open an issue (draft below). Deploy only
   after a yes. Until then use option 3.
2. **Deploy an aggregates-only app** (`APP_MODE=aggregates`). It ships only curve, segment and
   model tables plus `key_numbers.json`: no game names, no per-game numbers, no "Look up a game"
   tab, and the trust-month sliders are limited to the precomputed tolerances.
3. **Local only.** Keep the app on your machine and publish screenshots / the static page.

Note: `reports/tables/*.csv`, `reports/results/` and `reports/figures/` (all aggregates) are already
committed to the local git history. If the repository goes public, those aggregates are public
whichever option is chosen. `app/data/` (which contains game-level data) is git-ignored until D0.

### Drafted GitHub issue (for `beefsack/bgg-ranking-historicals`)

> **Title:** Licence / permission to use the data in a non-commercial analytics project
>
> Hi, thanks for maintaining this archive. I'm using the daily ranking snapshots for a
> non-commercial data-analytics portfolio project on how board-game ratings change after launch
> (monthly snapshots, 2016-2026). The repository has no LICENSE file, so I wanted to ask before
> publishing anything derived from it.
>
> 1. Could you add a licence, or tell me the terms you'd like people to follow?
> 2. Would it be OK for me to publish **aggregate** statistics (curves, regression tables) and
>    an interactive dashboard showing **per-game rating trajectories** (game name, rating and
>    number of raters by month)? I would not redistribute the raw CSV files, I'd cite this
>    repository and BoardGameGeek, and I'd state that the data are © BoardGameGeek and not
>    affiliated with them.
>
> The code downloads the files from your repository itself rather than copying them. Happy to
> adjust to whatever you prefer. Thanks!

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
