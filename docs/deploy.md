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

## Publishing checklist (what needs the author)

`gh` (GitHub CLI) is not installed on this machine, so the repository is created in the browser.

**1. Create the GitHub repository** (public, empty: no README, no .gitignore, no licence):
<https://github.com/new>, name `bgg-hype-fade`. Then, in the project folder:

```bash
git remote add origin https://github.com/<YOUR-USER>/bgg-hype-fade.git
git push -u origin main
```

**2. Fill in `config.yaml` -> `publish:`** (`github_repo: "<YOUR-USER>/bgg-hype-fade"`), then
`uv run python scripts/render_readme.py` (adds the CI badge) and commit.

**3. GitHub Pages (offline dashboard):**

```bash
uv run python scripts/publish_pages.py --push      # one orphan commit on gh-pages
```

Then Settings -> Pages -> "Deploy from a branch" -> `gh-pages` / `(root)`. The URL is
`https://<YOUR-USER>.github.io/bgg-hype-fade/`; put it in `publish.pages_url`, rerun
`publish_pages.py --push` (so the social-preview image URL is absolute) and the README renderer.

**4. Streamlit Community Cloud (live dashboard).** Sign in at <https://share.streamlit.io> with GitHub,
click "Create app" -> "Deploy a public app from GitHub", and fill in:

| Field | Value |
|---|---|
| Repository | `<YOUR-USER>/bgg-hype-fade` |
| Branch | `main` |
| Main file path | `app/streamlit_app.py` |
| App URL (optional) | e.g. `bgg-hype-fade` |
| Advanced settings -> Python version | 3.11 or newer |
| Advanced settings -> Secrets / environment | `APP_MODE = "aggregates"`, `BGG_REPO_URL = "https://github.com/<YOUR-USER>/bgg-hype-fade"`, `BGG_WRITEUP_URL = "https://github.com/<YOUR-USER>/bgg-hype-fade/blob/main/reports/writeup.md"` |

Dependencies come from `app/requirements.txt` (pinned); the theme from `.streamlit/config.toml`. No
secrets are needed. Streamlit may ask for an app reboot after the first deploy.

**5. Send the URLs back** (repository, Pages, Streamlit) so the placeholders in the README
(`publish:` in `config.yaml`), the write-up links and `pyproject.toml` URLs can be filled in.

Caveat: Streamlit Community Cloud (`*.streamlit.app`) may be slow or unreachable from mainland
China. The intended audience is international, but the author cannot rely on it for local demos.

## Static page for GitHub Pages

```bash
uv run bgg export-static        # reports/site/: index.html (4 KB landing page for link previews) + dashboard.html (5 MB)
```

A single self-contained HTML file (Plotly inlined, no CDN, no lookup, no sliders). It opens offline
and needs only aggregate tables. It carries Open Graph / Twitter tags so links preview nicely on
LinkedIn. `scripts/publish_pages.py --push` publishes it to the `gh-pages` branch (see the checklist);
the file is git-ignored on `main` because of its size.

## Screenshots for the README

```bash
uv run python scripts/app_screenshots.py            # desktop, writes reports/figures/app_*.png
uv run python scripts/app_screenshots.py --mobile   # 400 px wide, app_*_mobile.png
```

Uses the installed Chrome through Playwright (no browser download).
