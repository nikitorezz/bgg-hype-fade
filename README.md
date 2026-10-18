# Does the Hype Fade?

**Post-release rating trajectories of board games on BoardGameGeek, 2016–2026**

[![CI](https://github.com/nikitorezz/bgg-hype-fade/actions/workflows/ci.yml/badge.svg)](https://github.com/nikitorezz/bgg-hype-fade/actions/workflows/ci.yml) ![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue) ![Code licence: MIT](https://img.shields.io/badge/code%20licence-MIT-green) ![Data: not redistributed](https://img.shields.io/badge/data-not%20redistributed-lightgrey)

<p align="center"><img src="reports/figures/social_card.png" width="720" alt="New games lose 0.40 rating points in 3 years, 61% of it in year one"></p>

## TL;DR

- The average new board game's rating on BoardGameGeek (BGG) **falls 0.40 points in its first three years**. **61%** of that drop comes in year one, and **87%** of games decline.
- The decline isn't finished at three years: **new raters still score games 0.23 below the displayed average**.
- **Hype doesn't decide how far a game falls; it decides how fast.** Heavily hyped games reach their lower rating within months; quiet releases take years.
- A rating becomes reliable (within ±0.25 of its 3-year value for 80% of games) at about **month 13**. A simple adjusted launch rating gets close to that by month 6.

## Links

**[Live dashboard](https://bgg-hype-fade.streamlit.app/)** · **[Offline dashboard (static page)](https://nikitorezz.github.io/bgg-hype-fade/)** · **[Full write-up](reports/writeup.md)** · [Method notes and data traps](docs/data_notes.md) · [Findings review](docs/findings.md)

Run the dashboard locally in one command (see [Reproduce](#reproduce)): `uv run streamlit run app/streamlit_app.py`.

## Key findings

### 1. Launch ratings oversell, and the correction is front-loaded

<img src="reports/figures/fig01_rating_change_by_age.png" width="720" alt="Mean rating change by months since entry">

Followed for 36 months from the month they enter the ranking, **6,927 new releases** lose 0.24 points by month 12, 0.34 by month 24 and 0.40 by month 36. A control group of 2,428 established games drifted only 0.016 over the same windows, so the fall is specific to new releases.

### 2. The decline isn't finished at three years

<img src="reports/figures/fig02_new_vs_displayed_gap.png" width="720" alt="New raters minus displayed average">

Backing out the average of only the *recently added* ratings shows new raters score games 0.15 below the displayed average at month 3 and still 0.23 below at month 36. The displayed number is a running average that carries the launch crowd's enthusiasm for years.

### 3. Hype changes the speed of the fall, not its size

<img src="reports/figures/fig09_speed_not_size.png" width="720" alt="Change by hype quartile at month 6 and month 36">

By month 6 the most-hyped quarter of games has lost 0.19 points and the least-hyped quarter 0.10; by month 36 they are close (0.41 vs 0.36). Hype does not predict a bigger fall: the hype coefficient is +0.049 with controls and -0.004 measured after the hype window. **The hypothesis that hyped games fade more is not supported**, and the write-up reports it that way.

### 4. You can trust a rating after about a year, or adjust it sooner

<img src="reports/figures/fig08_when_to_trust.png" width="720" alt="Share of games within the tolerance of their final rating, by month">

At launch only 32% of games are within ±0.25 of their 3-year rating; the 80% mark is reached at month 13. A three-variable adjusted launch rating (trained on 2017–2019 releases, tested on 2020–2023) is within ±0.25 for 55% of test games at launch (displayed rating: 31%) and for 77% by month 6. Also, 74% of games *climb* in BGG's rank while their raw average falls.

## What this project demonstrates

- **SQL/DuckDB pipeline** over 2,611,791 rows in 121 monthly snapshots: numbered, commented SQL files, a single config file, idempotent stages, one CLI.
- **Data-quality engineering:** truncated files (row-count rule), 721 duplicate rows, junk metadata, and a rounding-error bound on the derived new-rater average. 36 automated checks pass (0 fail).
- **Cohort and panel analysis** of 11,020 new releases with a clear sample waterfall.
- **Econometrics:** a game fixed-effects event study, robust regression with entry-year effects, game-level bootstrap intervals and an eight-variant robustness grid.
- **Out-of-sample predictive check** (train 2017–2019, test 2020–2023).
- **Honest reporting of a null result** on the headline hypothesis.
- **Interactive dashboard** (Streamlit, Plotly) and a static offline version, built from aggregate data only.
- **Engineering hygiene:** type hints, ruff, pytest and CI, and every number in the docs generated from one file (`key_numbers.json`).

## Method in brief

One snapshot per month (October 2016 to October 2026) of BGG's ranked list. A game's *entry month* is the first month it appears; games already ranked in the first snapshot are excluded, and a *new release* is a game whose publication year at entry is no earlier than the year before entry. The outcome is the raw average rating (not the Bayes average). Standard errors are clustered by game or robust (HC1); intervals are 95%, with game-level bootstrap for ratios. The full definitions are in [`docs/data_notes.md`](docs/data_notes.md) and [`config.yaml`](config.yaml).

## Limitations

- A game only enters the ranking at 30 ratings, so its very first ratings are folded into month 0: the analysis measures change *after* entry.
- Observational data: patterns, not causal effects. "Hype" (rater growth) also reflects print runs, distribution and price.
- Regression to the mean and self-selection of the launch audience can't be cleanly separated.
- The new-rater estimate is approximate (rounding, edited ratings) and over-represents fast-growing games.
- One enthusiast platform. The Kickstarter flag (0.54 vs 0.36 fall) comes from a 2022 snapshot of a public Kaggle set and is descriptive only.
- Monthly snapshots only; a daily-data robustness check is future work.

## Repository structure

```
sql/            numbered, commented SQL: load, cohorts, panel, quality checks
src/bgg/        pipeline (download, build, qc), analysis/ (descriptives, models, predictive,
                robustness, crowdfunding, key numbers), plots, dashboard extract, static export
app/            Streamlit dashboard (reads only app/data: aggregate tables and key numbers)
config.yaml     every threshold, date and rule used anywhere
reports/        figures, tables, model outputs, key_numbers.json, quality-check report, write-up
tests/          unit and integration tests (data-dependent ones skip when data is absent)
docs/           data notes, findings review, deployment notes, how the project was built
scripts/        README renderer, screenshots, GitHub Pages publisher
```

## Reproduce

Requires [uv](https://docs.astral.sh/uv/) and Python 3.11+.

```bash
uv sync
uv run bgg all                  # download (541 MB), load, cohorts, panel, quality checks
uv run bgg analysis             # figures, models, key_numbers.json
uv run bgg dashboard-data --aggregates-only
uv run streamlit run app/streamlit_app.py
uv run bgg export-static        # reports/site/index.html: one offline page
uv run pytest && uv run ruff check .
```

The download comes from GitHub. In mainland China set `HTTPS_PROXY`, or use `uv run bgg download --backend git`; downloads are resumable and retried. Individual stages: `bgg download | load | cohorts | panel | qc`.

## Data and licence

- **Code:** MIT (see [`LICENSE`](LICENSE)). The licence covers the code only, **not the data**.
- **Data:** daily BGG ranking snapshots from [beefsack/bgg-ranking-historicals](https://github.com/beefsack/bgg-ranking-historicals) (no licence file, so no data is redistributed here: the pipeline downloads it). Data © BoardGameGeek; this project is not affiliated with BoardGameGeek. Only aggregate results are published.
- **Metadata:** "Board Game Database from BoardGameGeek" by threnjen on Kaggle, CC BY-SA 3.0, used for the optional crowdfunding analysis and not redistributed.
