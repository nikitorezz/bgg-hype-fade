# Task: Build pipeline steps 1–5 from scratch

**Goal:** a reproducible pipeline that turns the GitHub archive of daily BGG ranking snapshots into a clean monthly panel of newly released games, plus a quality-check report, run with one command (`uv run bgg all`).

Read first: `CLAUDE.md` (conventions), `docs/data_notes.md` (verified data facts; **most acceptance numbers below come from there**), and `config.yaml` (all parameters, already filled in).

Working style: build and **run** each stage in order, check its acceptance criteria, commit, then move on. If a criterion fails because the data disagrees with a research rule, stop and report; don't redefine the rule.

---

## 0. Project skeleton

Create:
```
.
├── CLAUDE.md, config.yaml            (exist, don't restructure)
├── README.md                         short: purpose, setup, how to run, data credit
├── pyproject.toml                    package "bgg" in src/, console script `bgg = bgg.cli:main`
├── .gitignore                        data/raw/, data/interim/, data/processed/, .venv/, __pycache__/, *.duckdb*, .ipynb_checkpoints/
├── .gitattributes                    * text=auto
├── data/{raw,interim,processed}/     (.gitkeep)
├── sql/
│   ├── 01_load.sql
│   ├── 02_entry_and_cohorts.sql
│   ├── 03_panel.sql
│   └── 04_quality_checks.sql
├── src/bgg/
│   ├── __init__.py
│   ├── cli.py          argparse/typer: download | load | cohorts | panel | qc | all  (+ --config path, --log-level)
│   ├── config.py       load + validate config.yaml (dataclasses or pydantic); derived values (e.g. main_entry_end)
│   ├── download.py     file listing, monthly selection, http + git backends, manifest
│   ├── build.py        DuckDB runner: open db, set variables, execute a sql file, export parquet
│   └── qc.py           runs 04, writes reports, spot-check figure
├── tests/
│   ├── test_download_selection.py
│   ├── test_new_avg.py
│   ├── test_dedup.py
│   └── test_processed_data.py   (skips if data/processed is empty)
└── reports/{qc,tables,figures}/
```
Dependencies: `duckdb>=1.1`, `requests`, `pyyaml`, `matplotlib`, `pandas` (for small exports/tests); dev: `pytest`, `ruff`. Python ≥ 3.11. Pin them.

**Done when:** `uv run bgg --help` lists the stages, `uv run pytest` runs (tests may skip), and `ruff check` is clean.

---

## Step 1: Download monthly snapshots (`bgg download`)

### Listing files
- **http backend:** one GET to the tree API (`config.source.tree_api_url`). The repo is flat, so no `recursive` is needed. Keep only names matching `filename_pattern`. If the response is `truncated`, or rate-limited (HTTP 403/429), log it and tell the user to rerun with `--backend git`.
- **git backend:** `git clone --filter=blob:none --no-checkout --depth 1 <git_url> data/raw/_git`, then `git ls-tree --name-only HEAD`. **Never** `git ls-tree -l` (it fetches every blob). Get a file with `git -C data/raw/_git checkout HEAD -- <file>` and move it into `data/raw/`.

### Monthly selection (handles truncated files, see data_notes §3)
For each month from `start_month` to `end_month` inclusive, in chronological order:
1. Candidates = that month's files with day ≤ `max_candidate_day`, ascending.
2. For each candidate: download (or reuse if already present), count data rows (lines − header).
3. Accept the first candidate with `rows ≥ min_row_ratio × rows_of_previous_accepted_month`. The first month has no reference, so accept its first file.
4. Move rejected candidates to `rejected_dir`. If no candidate passes, accept the one with the most rows, mark `status = "fallback"` and log a WARNING.
5. Keep the selection logic a **pure function** (`select_monthly(candidates_by_month, row_counter, ratio) -> decisions`) so it can be unit-tested without the network.

### Robustness
- `requests.Session` with urllib3 `Retry` (`max_retries`, `backoff_factor`, status 429/5xx) and `timeout_seconds`. Proxies come from env vars (requests' default; just don't disable `trust_env`).
- Write to `<file>.part`, then atomic rename. Existing complete files are skipped (but still row-counted for the selection rule).
- Progress logging (`month i/121, file, rows, decision`).

### Manifest: `data/raw/manifest.csv`
Columns: `month, chosen_file, chosen_date, rows, status (ok|substituted|fallback), rejected (e.g. "2024-01-01:22100;2024-01-02:22800"), bytes, sha256, downloaded_at`.
Later stages read **only the files listed in the manifest**, never a glob of `data/raw/`.

### Acceptance
- 121 manifest rows (2016-10 … 2026-10), no month missing.
- `chosen_date` is day 1 for every month **except** 2016-10-12 (first file in the archive), 2024-01-05 and 2024-09-03 (`substituted`). Any other substitution must be written into `docs/data_notes.md` §3.
- Total ~700 MB, ~2.6M data rows. A rerun downloads nothing new and produces an identical manifest (apart from `downloaded_at` for new files).
- Unit tests: the selection function reproduces the 2024-01 case (22100, 22800, 23800, 24800, 25646 with previous 25488 → picks day 5) and the first-month rule.

---

## Step 2: Load into DuckDB → Parquet (`bgg load`, `sql/01_load.sql`)

- Python creates/opens `data/interim/bgg.duckdb` and passes the manifest file list into `read_csv([...], filename = true, header = true, columns = {...})` with **explicit types**: ID BIGINT, Name VARCHAR, Year INTEGER, Rank INTEGER, Average DOUBLE, "Bayes average" DOUBLE, "Users rated" INTEGER, URL VARCHAR, Thumbnail VARCHAR.
- Table `snapshots_raw`: `snap_date` (parsed from file name), `snap_month = date_trunc('month', snap_date)`, `game_id, name, pub_year, rank, avg_rating, bayes_avg, n_raters`. Drop URL/Thumbnail.
- Table `snapshots`: dedup to one row per (snap_date, game_id) via `QUALIFY row_number() OVER (PARTITION BY snap_date, game_id ORDER BY n_raters DESC, rank ASC) = 1`.
- Table `load_log`: per snap_date: rows_raw, rows_dedup, dup_pairs_removed.
- Table `games`: game_id, latest_name (name at last appearance), first_month, last_month, months_present, `pub_year_at_entry` (pub_year at first appearance, via `arg_min`), pub_year_latest, n_distinct_pub_years.
- Export `data/interim/snapshots_monthly.parquet` and `data/interim/games.parquet`.

### Acceptance
- ~2.6M rows; 121 distinct snap_date; ~31.7k distinct game_id (pilot: 31,676).
- Zero duplicates on (snap_date, game_id) in `snapshots`. Pairs removed reported (pilot ~721, may differ slightly after file substitution).
- `avg_rating` within [1, 10]; `n_raters ≥ 30`; no NULL in game_id/avg_rating/n_raters.

---

## Step 3: Entry month and cohorts (`bgg cohorts`, `sql/02_entry_and_cohorts.sql`)

Table `game_cohorts` (one row per game):
- `entry_month` = first_month; `entry_year`
- `pub_year_entry` (cleaned): NULL if `< min_valid_pub_year` or `> year(end_month) + max_pub_year_slack`
- flags, each a boolean column:
  - `left_censored` = entry_month = `first_snapshot_month`
  - `pub_year_unknown` = pub_year_entry IS NULL
  - `old_game` = pub_year_entry < entry_year − `new_release_max_age_years`
  - `is_new_release` = NOT left_censored AND NOT pub_year_unknown AND NOT old_game
  - `followup_available` = months between entry_month and end_month
  - `in_main_sample` = is_new_release AND entry_month BETWEEN `main_entry_start` AND `end_month − followup_months` (= 2023-10-01)
  - `observed_m12`, `observed_m24`, `observed_m36` = a snapshot exists at exactly that k
- Table `sample_waterfall`: ordered steps with counts (all games → minus left-censored → minus unknown pub year → minus old games → new releases → in main window → observed at m36). Export to `reports/tables/sample_waterfall.csv`.
- Table `cohort_sizes`: by entry_year: new releases, observed at m12/m24/m36. Export to `reports/tables/cohort_sizes.csv`.

### Acceptance (data_notes §5)
- New releases by entry year **exactly**: 2017 1,033 · 2018 1,045 · 2019 1,068 · 2020 921 · 2021 978 · 2022 1,055 · 2023 1,213. A mismatch is a FAIL to investigate.
- Left-censored = 12,759. Pub year unknown among later entrants ≈ 287; old games ≈ 7,609. Total new releases ≈ 11,021.
- Observed at m36 for 2017–2022 entries at or near the proposal's values (1,028 / 1,040 / 1,062 / 911 / 973 / 1,047), and **not lower** than the pilot's (1,028 / 1,039 / 1,062 / 910 / 965 / 1,047).

---

## Step 4: Panel and derived variables (`bgg panel`, `sql/03_panel.sql`)

### `panel` (one row per new-release game × observed month, k = 0 … max_k)
Include **all** `is_new_release` games (later cohorts help the dashboard) and carry `in_main_sample`.

Columns: `game_id, snap_month, k (months_since_entry), entry_month, entry_year, in_main_sample, avg_rating, bayes_avg, n_raters, rank, d_rating (avg_rating − avg at k=0)`, then for each window w in `windows` (1 and 3):
- `prev_n_w`, `prev_avg_w`: values at exactly k − w (NULL if that month isn't observed; **no interpolation**, no "previous available row")
- `delta_raters_w = n_raters − prev_n_w`
- `raters_decreased_w = delta_raters_w < 0`
- `new_avg_w = (avg_rating·n_raters − prev_avg_w·prev_n_w) / delta_raters_w`, only when delta > 0
- `new_avg_err_w = rounding_half_unit · (n_raters + prev_n_w) / delta_raters_w`
- `new_avg_ok_w = delta ≥ min_delta_raters AND err ≤ max_error_bound AND new_avg_w BETWEEN 1 AND 10`
- `new_avg_out_of_range_w = new_avg_w NOT BETWEEN 1 AND 10` (kept for QC counts)

Keep the raw `new_avg_w` even when not ok, so later sensitivity checks can apply other thresholds.

### `game_summary` (one row per new-release game)
`game_id, latest_name, entry_month, entry_year, pub_year_entry, in_main_sample, observed_m12/m24/m36`, then:
- `avg_m{0,3,6,12,24,36}`, `raters_m{0,6,12,36}`, `rank_m0`, `rank_m36` (NULL if that k isn't observed)
- `change_12, change_24, change_36` = avg_mK − avg_m0
- `hype_log = ln(raters_m6 + 1) − ln(raters_m0 + 1)`, `hype_abs = raters_m6 − raters_m0`
- `hype_quartile` = `NTILE(4) OVER (PARTITION BY entry_year ORDER BY hype_log)` among games with non-NULL hype_log (1 = least hyped)
- `new_avg_y1` = Δ-weighted mean of ok `new_avg_1` over k 1–12; `new_avg_y3` = same over k 25–36; plus `n_ok_y1`, `n_ok_y3`

Exports: `data/processed/panel.parquet`, `data/processed/game_summary.parquet`. Expect ~330k panel rows; both files small (< 30 MB).

### Acceptance
- `panel` unique on (game_id, k); every game has a k=0 row; `d_rating = 0` at k=0; k within 0…36.
- Mean `d_rating` over all new releases ≈ −0.24 at k=12, −0.33 at k=24, −0.40 at k=36 (±0.03; data_notes §8).
- `new_avg` formula unit test passes. Use a hand-built case: avg 8.00 at 100 raters → 7.90 at 150 raters ⇒ new_avg = 7.70, err = 0.005·250/50 = 0.025.
- Hype quartiles 1–4 roughly equal in size within each entry year.

---

## Step 5: Quality checks (`bgg qc`, `sql/04_quality_checks.sql`, `src/bgg/qc.py`)

`04_quality_checks.sql` builds a table `qc_results(check_id, description, value, expected, status)` with status PASS / WARN / FAIL. Checks:

| # | Check | Expected | Severity if violated |
|---|---|---|---|
| 1 | Manifest has 121 months, none missing | 121 | FAIL |
| 2 | Substituted months | exactly 2024-01, 2024-09 | WARN (log any new ones) |
| 3 | Snapshot row count < 0.99 × previous month | 0 months | FAIL |
| 4 | Duplicates on (snap_date, game_id) after dedup | 0 | FAIL |
| 5 | Dup pairs removed in load | report (≈700) | info |
| 6 | avg_rating outside [1, 10]; n_raters < 30; NULL keys | 0 | FAIL |
| 7 | pub_year unknown / junk counts | report | info |
| 8 | Entry counts 2017–2023 vs data_notes §5 | exact | FAIL |
| 9 | Observed at m36, 2017–2022 entries | ≥ pilot values | WARN |
| 10 | New-release games with a missing month in k 0–36 | report; well below pilot's 442 | WARN if ≥ 442 |
| 11 | Month steps where raters decreased | report (≈1.5%) | info |
| 12 | new_avg_ok share by k (1, 3, 6, 12, 24, 36), both windows | report | info |
| 13 | new_avg out of [1, 10] (all / among err-ok) | report | info |
| 14 | panel unique (game_id, k), k=0 present, d_rating(0)=0 | true | FAIL |
| 15 | Mean d_rating at k = 12/24/36 vs §8 | ±0.03 | WARN |
| 16 | Spot-check games (data_notes §8 table): entry month, pub year, in-cohort flag exact; avg ±0.01; raters exact | match | FAIL |

`qc.py` writes:
- `reports/qc/qc_report.md`: run timestamp, config end_month, git commit hash, summary (n PASS/WARN/FAIL), the results table, plus the small tables behind checks 2, 10 and 12.
- `reports/qc/qc_results.csv`
- `reports/figures/qc_spotcheck_trajectories.png`: one small panel per spot-check game (avg_rating by k, plus `new_avg_3` points where ok). Plain matplotlib; it's a QC visual, not the headline chart.

`bgg qc` exits non-zero if any FAIL.

### Tests (`tests/`)
- `test_download_selection.py`: truncation case, first-month rule, fallback when nothing passes.
- `test_new_avg.py`: formula and err on the hand-built case; Δ ≤ 0 gives NULL; threshold logic.
- `test_dedup.py`: a tiny in-memory DuckDB table with a duplicate pair keeps the row with more raters.
- `test_processed_data.py`: if `data/processed/*.parquet` exist, the structural checks of step 4.

---

## Final deliverables of this task

1. Working `uv run bgg all` (download → load → cohorts → panel → qc), idempotent.
2. `data/processed/panel.parquet`, `data/processed/game_summary.parquet`.
3. `reports/qc/qc_report.md` with 0 FAIL, plus `reports/tables/{sample_waterfall,cohort_sizes}.csv` and the spot-check figure.
4. Tests passing, ruff clean, README with setup + run instructions.
5. `docs/data_notes.md` updated with anything new; a progress-log line in `docs/implementation_plan.md`.
6. A short final summary for the user: what was built, QC outcome (PASS/WARN/FAIL counts and any WARN explained), any deviation from this spec and why, and how long the download took.

## Out of scope (next tasks)
Regressions (Q1 event study, Q2), analysis notebooks and figures, Q4 predictive check, Kaggle join (Q3), daily-file robustness download, Streamlit app, write-up.
