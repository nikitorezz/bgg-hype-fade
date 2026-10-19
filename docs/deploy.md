# Deployment

The results are published in three places:

| Where | What | Source |
|---|---|---|
| [bgg-hype-fade.streamlit.app](https://bgg-hype-fade.streamlit.app/) | Interactive dashboard, including the game lookup | `app/` on the `main` branch (Streamlit Community Cloud) |
| [nikitorezz.github.io/bgg-hype-fade](https://nikitorezz.github.io/bgg-hype-fade/) | Project page and static dashboard | `reports/site/`, published to the `gh-pages` branch |
| [github.com/nikitorezz/bgg-hype-fade](https://github.com/nikitorezz/bgg-hype-fade) | Code, write-up and reports | `main` branch |

## What is published

`app/data/` (about 4 MB) holds aggregate tables, `key_numbers.json` and a compact per-game extract: monthly rating, rank and rater counts for each new release, which powers the game lookup. It contains no user data and no Kickstarter flag. Raw and intermediate data (`data/`), the third-party metadata and `reports/tables/examples.csv` stay local; see [data notes §8](data_notes.md#8-licence-and-publication) for the licence position.

The static project page and static dashboard on GitHub Pages are aggregate-only and have no game lookup.

The dashboard decides its mode by itself: without `app/data/games.parquet` it runs in aggregates mode and hides the lookup (`BGG_APP_MODE=aggregates` forces this).

## Updating after a change

```bash
uv run bgg analysis                           # figures, models, key_numbers.json
uv run bgg dashboard-data                     # refresh app/data (tables and per-game extract)
uv run python scripts/render_readme.py        # README numbers
uv run pytest && uv run ruff check .
git add -A && git commit -m "..." && git push # Streamlit Cloud redeploys on push
uv run python scripts/publish_pages.py --push # rebuild and publish the GitHub Pages site
```

## Streamlit Community Cloud settings

| Setting | Value |
|---|---|
| Repository / branch | `nikitorezz/bgg-hype-fade` / `main` |
| Main file | `app/streamlit_app.py` |
| Dependencies | `app/requirements.txt` (pinned) |
| Theme | `.streamlit/config.toml` |
| Environment (optional) | `BGG_APP_MODE = "aggregates"` hides the lookup (leave it unset to show it); `BGG_REPO_URL`, `BGG_WRITEUP_URL`, `BGG_PAGES_URL` override the default links |

No secrets are needed.

## GitHub Pages

`uv run bgg export-static` writes two pages to `reports/site/`:

- `index.html`: the project page (about 15 KB, no scripts), with the fade drawn as inline SVG and Open Graph tags for link previews. It is kept small because some link-preview scrapers reject large pages.
- `dashboard.html`: the static dashboard, one self-contained file with Plotly inlined (about 5 MB), which also works offline.

`scripts/publish_pages.py --push` publishes both, plus `social_card.png`, as a single commit on the `gh-pages` branch (Settings → Pages → deploy from `gh-pages`, root).

## Screenshots

```bash
uv run python scripts/app_screenshots.py            # desktop, reports/figures/app_*.png
uv run python scripts/app_screenshots.py --mobile   # 400 px wide, app_*_mobile.png
```

## Phone check

Most visitors arrive from LinkedIn on a phone. `uv run python scripts/mobile_check.py` loads the app and both static pages in an emulated iPhone (390 px, touch) and fails on horizontal overflow, text under 11 px, small tap targets, and charts that would capture touch scrolling. It saves full-height screenshots to `data/interim/mobile_check/`. The app switches to a compact chart layout automatically for phone user agents (or with `?compact=1`); the static page ships both layouts and shows one by screen width.
