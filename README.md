# Does the Hype Fade?

Post-release rating trajectories of board games on BoardGameGeek, 2016–2026. This repo holds the
data pipeline (download → load → cohorts → panel → quality checks). Analysis comes later.

## Run (Windows, uv)

```bash
uv sync
uv run bgg all            # pipeline; or one stage: download | load | cohorts | panel | qc
uv run bgg analysis       # figures, models, key numbers (--only descriptives|models|predictive|
                          #   robustness|crowdfunding|keynumbers)
uv run bgg everything     # pipeline + analysis
uv run pytest
uv run ruff check .
```

Outputs: `data/processed/{panel,game_summary}.parquet`, `reports/qc/qc_report.md`,
`reports/tables/*.csv`, `reports/figures/qc_spotcheck_trajectories.png`. `bgg qc` exits non-zero on any FAIL.

### Dashboard

```bash
uv run bgg dashboard-data        # build app/data (self-contained extract; --aggregates-only for a public-safe version)
uv run streamlit run app/streamlit_app.py     # interactive dashboard; APP_MODE=aggregates hides game-level views
uv run bgg export-static         # reports/site/index.html: one offline page, no server needed
```

Deployment is aggregates-only (decision D0): no game-level data is published. See `docs/deploy.md`.

In mainland China set `HTTPS_PROXY` or use `uv run bgg download --backend git`.
All parameters live in `config.yaml`; data facts and traps are in `docs/data_notes.md`.

## Data credit

Daily BGG ranking snapshots from [beefsack/bgg-ranking-historicals](https://github.com/beefsack/bgg-ranking-historicals)
(no licence file: raw and processed data are not redistributed here). Data © BoardGameGeek.

Analysis outputs: `reports/figures/fig*.png|svg`, `reports/tables/*.csv`, `reports/results/` (model tables,
`key_numbers.json`, `results_summary.md`). Optional Q3 uses the Kaggle dataset *Board Game Database from
BoardGameGeek* (threnjen, CC BY-SA 3.0), placed manually in `data/external/kaggle_bgg/`.
