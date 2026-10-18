# Deploying the dashboard

**Status: prepared, not deployed.** Nothing is published until decision D0 below is made.

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

1. Push the repository to GitHub. For option 2, build with `bgg dashboard-data --aggregates-only`
   and un-ignore only `app/data/tables`, `app/data/key_numbers.json` and `app/data/app_config.json`
   (edit `.gitignore`, then `git add -f`). For option 1 un-ignore all of `app/data/`.
2. On <https://share.streamlit.io>, create an app: repository = yours, branch = `main`, main file
   = `app/streamlit_app.py`. Dependencies come from `app/requirements.txt` (pinned). No secrets.
3. Set the environment variable `APP_MODE` (Advanced settings) to `aggregates` for option 2.
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
