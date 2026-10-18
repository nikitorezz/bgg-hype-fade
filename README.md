# Does the Hype Fade?

Post-release rating trajectories of board games on BoardGameGeek, 2016–2026. This repo holds the
data pipeline (download → load → cohorts → panel → quality checks). Analysis comes later.

## Run (Windows, uv)

```bash
uv sync
uv run bgg all            # or one stage: download | load | cohorts | panel | qc
uv run pytest
uv run ruff check .
```

Outputs: `data/processed/{panel,game_summary}.parquet`, `reports/qc/qc_report.md`,
`reports/tables/*.csv`, `reports/figures/qc_spotcheck_trajectories.png`. `bgg qc` exits non-zero on any FAIL.

In mainland China set `HTTPS_PROXY` or use `uv run bgg download --backend git`.
All parameters live in `config.yaml`; data facts and traps are in `docs/data_notes.md`.

## Data credit

Daily BGG ranking snapshots from [beefsack/bgg-ranking-historicals](https://github.com/beefsack/bgg-ranking-historicals)
(no licence file: raw and processed data are not redistributed here). Data © BoardGameGeek.
