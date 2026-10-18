# Deployment

The results are published in three places, all built from aggregate data only:

| Where | What | Source |
|---|---|---|
| [bgg-hype-fade.streamlit.app](https://bgg-hype-fade.streamlit.app/) | Interactive dashboard | `app/` on the `main` branch (Streamlit Community Cloud) |
| [nikitorezz.github.io/bgg-hype-fade](https://nikitorezz.github.io/bgg-hype-fade/) | Project page and static dashboard | `reports/site/`, published to the `gh-pages` branch |
| [github.com/nikitorezz/bgg-hype-fade](https://github.com/nikitorezz/bgg-hype-fade) | Code, write-up and reports | `main` branch |

## What is published

Only aggregate outputs: group curves, segment summaries, model results and `key_numbers.json` (about 0.2 MB in `app/data/`). Game-level files (`app/data/*.parquet`, `data/external/`, `reports/tables/examples.csv`, lookup screenshots) are git-ignored, because the source archive carries no licence; see [data notes §8](data_notes.md#8-licence-and-publication). Before the first push, the git history was checked and rewritten so that no game-level file or third-party user data appears in any commit.

The dashboard decides its mode by itself: without `app/data/games.parquet` it runs in aggregates mode, which hides the game lookup. The lookup is available locally after building the full extract.

## Updating after a change

```bash
uv run bgg analysis                           # figures, models, key_numbers.json
uv run bgg dashboard-data --aggregates-only   # refresh app/data
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
| Environment (optional) | `APP_MODE = "aggregates"`; `BGG_REPO_URL`, `BGG_WRITEUP_URL`, `BGG_PAGES_URL` override the default links |

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
