# Task 02: Analysis (milestones M3–M5): figures, models, predictive rule, robustness

> **Archived build specification** given to an AI coding assistant (Claude Code) during the project; see [`../README.md`](../README.md) for context. Section references to `docs/data_notes.md` point to an earlier version of that file.

**Goal:** turn `data/processed/{panel,game_summary}.parquet` (+ `data/interim/snapshots_monthly.parquet` for the control group) into publication-ready figures, model tables and one machine-readable file of key numbers. The write-up and the Streamlit dashboard will be built from these later, so **every figure must be backed by a tidy CSV table** the dashboard can reuse.

Read first: `CLAUDE.md`, `docs/data_notes.md` (§10 = final pipeline facts, **§11 = analysis pre-checks with sanity values for this task**), `docs/implementation_plan.md` §1 (questions) and §6 (analysis).

Working style is the same as task 01: build → **run on the real data** → check against the sanity values → commit → next stage. Report results as they come out. **H2 may well be unsupported or reversed; that's a valid finding.** Never tune a specification to get a "nicer" answer. If you deviate from a definition below, write down why.

---

## 0. Setup

- Add dependencies: `numpy`, `scipy`, `statsmodels`, `linearmodels`, `pyarrow`. Optional: `jupyter`/`nbconvert` for the walkthrough notebook (step 7). Pin as before.
- New code lives in `src/bgg/analysis/`:
  ```
  src/bgg/analysis/
    __init__.py
    data.py          loaders (DuckDB → pandas), sample definitions, control series
    descriptives.py  curves, distributions, gap, cohort tables   (step 1–2)
    models.py        event study (Q1), cross-section (Q2)         (step 3–4)
    predictive.py    Q4 rule + adjusted predictor                 (step 5)
    robustness.py    robustness grid                               (step 6)
    crowdfunding.py  optional Q3                                   (step 8)
    keynumbers.py    collects every headline number → JSON + summary md
  src/bgg/plots.py   figure functions; take a tidy DataFrame, return a matplotlib Figure
  src/bgg/style.py   one shared figure style (font, sizes, colour-blind-safe palette, grid)
  ```
- Add an `analysis:` section to `config.yaml` with every choice below (samples, k grid, bootstrap reps, seed, thresholds, robustness variants, the train/test split for step 5). No magic numbers in code.
- CLI: `uv run bgg analysis [--only descriptives|models|predictive|robustness|crowdfunding|keynumbers]`. `uv run bgg all` stays the pipeline only; add `uv run bgg everything` = pipeline + analysis.
- Outputs:
  - `reports/figures/figNN_<slug>.png` (200 dpi) **and** `.svg`
  - `reports/tables/<name>.csv`: tidy/long format (e.g. `group_type, group_value, k, mean, ci_low, ci_high, n`)
  - `reports/results/model_*.csv` + `model_*.md` (readable regression tables)
  - `reports/results/key_numbers.json`: single source of truth for every number quoted later
  - `reports/results/results_summary.md`: auto-generated from key_numbers + tables (facts only, no narrative claims)

### Fixed definitions (use everywhere)
| Name | Definition | Expected n |
|---|---|---|
| **Main sample** | `in_main_sample AND observed_m36` (entry 2017-01…2023-10, observed at k=36) | 6,927 |
| **Balanced sample** | main sample also observed at k=12 and k=24 (used where comparing k=12/24/36) | 6,918 |
| **All new releases** | `is_new_release` rows of the panel, any follow-up (unbalanced; robustness and dashboard only) | 11,020 games |
| **Mature control group** | games already ranked in 2016-10 with ≥ 500 raters then, **present in every monthly snapshot** (from `snapshots_monthly`) | 2,428 |
| Weighting | **equal weight per game** is primary; rater-weighted is a robustness variant | |
| CI | 95%: per-k means use mean ± 1.96·SE (SE across games); derived ratios use a **game-level bootstrap** (`bootstrap_reps`, fixed seed) | |

---

## Step 1: Headline descriptives (`descriptives.py`)

**Fig 1, "The fade"** (`fig01_rating_change_by_age`): mean change in displayed average from entry (`d_rating`) by k = 0…36, main sample, CI band. Annotate k=12/24/36 values and "**X% of the 3-year decline happens in year 1**" (= mean change_12 / mean change_36 on the balanced sample, bootstrap CI). Table: `curve_overall.csv`.

**Fig 2, "What new raters say vs what's displayed"** (`fig02_new_vs_displayed_gap`): per k, mean of `new_avg_3 − avg_rating` over rows where `new_avg_ok_3`, **equal weight per row**, main sample, CI band; zero line. Second panel or inset: the share of rows usable by k (selection is visible). Compute the gap row-wise, then average. **Never compare a weighted mean of new_avg to an unweighted mean of avg_rating** (data_notes §11 explains the trap). Table: `gap_new_vs_displayed.csv` (also with the Δ-weighted variant as a column).

**Fig 3, "By launch year + background drift"** (`fig03_cohorts_and_control`): left: curves by entry year (2017…2023). Right: mature control group mean average by calendar month, rebased to 0 at 2016-10. Plus the **control-adjusted** 36-month change for the main sample: `change_36 − (control_mean[entry_month+36] − control_mean[entry_month])`, game by game. Tables: `curve_by_entry_year.csv`, `control_series.csv`.

**Fig 4, "Distribution + regression to the mean"** (`fig04_change_distribution`): left: histogram of change_36 with share declining (`change_36 < 0`) and median. Right: binned means of change_36 by `avg_m0` decile with CI. This shows high starters fall most, part of which is statistical regression to the mean from noisy ~34-rater entry averages. Table: `change36_by_avg0_decile.csv`.

**Fig 5, "Example trajectories"** (`fig05_examples`): small multiples of displayed average (+ `new_avg_3` dots where ok) for 6 named games, chosen **by rule** among main-sample games with `raters_m36 ≥ 5,000`: the 2 largest declines, the 2 largest rises, and the 2 with change_36 closest to the sample mean. Table: `examples.csv`.

**Table 1** `table1_sample.csv/.md`: sample waterfall (reuse `sample_waterfall.csv`) + cohort sizes.

## Step 2: Segment cuts (also `descriptives.py`)

Tables for the dashboard and the write-up, each with mean change_12/change_36, CI, n:
- by hype quartile → also **Fig 6** (`fig06_by_hype_quartile`): curves by quartile
- by `avg_m0` quintile, by entry raters bucket (`<35, 35–49, 50–99, 100+`), by popularity (top 10% of `raters_m36` vs rest)
- Long format with a single file `segments.csv` (`segment_type, segment_value, metric, mean, ci_low, ci_high, n`).

## Step 3: Q1 event study (`models.py`)

`avg_rating_it = α_i + Σ_{k=1..36} β_k·1[k_it = k] + ε_it` on the main-sample panel. `linearmodels.PanelOLS(entity_effects=True)`, SEs clustered by game.
- Report all β_k with CIs (`model_event_study.csv`) and **Fig 7** (`fig07_event_study`) coefficient plot. Headline: β12, β24, β36 and the share β12/β36 with bootstrap CI (resample games).
- Sanity: β_k ≈ the balanced means (β12 ≈ −0.245, β36 ≈ −0.40).
- **Don't add calendar-month fixed effects.** With game FE, age dummies and calendar FE, age = calendar − entry is perfectly collinear (the age–period–cohort problem). Background drift is handled by the control-adjusted variant (step 6) instead. Say this in the model notes.

## Step 4: Q2 does hype predict the fade? (`models.py`)

Cross-section on the main sample, OLS with HC1 robust SEs, entry-year fixed effects. Report **standardised** hype coefficients (per 1 SD) alongside raw ones.

| Spec | Outcome | Hype | Controls | Why |
|---|---|---|---|---|
| **A** (as proposed) | change_36 | hype_log | avg_m0, ln(raters_m0), entry-year FE | the original hypothesis test |
| **B** (clean timing) | avg_m36 − avg_m6 | hype_log | avg_m6, ln(raters_m6), entry-year FE | outcome measured *after* the hype window; baseline from more raters, so less noisy, so less mechanical regression to the mean |
| **C** (alt. measure) | change_36 | ln(raters_m6) ("reach") | avg_m0, ln(raters_m0), FE | absolute reach instead of relative growth |
| **D** (no controls) | change_36 | hype_log | FE only | shows how much the controls matter |

H2 predicts a **negative** hype coefficient. Output `model_q2.csv/.md` (all specs side by side: coef, SE, p, n, R²) and a plain table of quartile means (from step 2). In the notes, add one line per spec stating the sign and significance. Don't interpret beyond that; interpretation is done later.

## Step 5: Q4 when can you trust a new game's rating? (`predictive.py`)

On the main sample, for every k = 0…30:
- MAE of `avg_rating(k)` vs `avg_m36`, and the share of games within ±0.25 and ±0.5 of their 36-month rating (`q4_accuracy_by_k.csv`).
- **Rule:** the first k where ≥ 80% of games are within ±0.25 (make both numbers config values), with bootstrap CI for that k.
- **Fig 8** (`fig08_when_to_trust`): share within ±0.25 by k, with the rule marked.
- **Adjusted predictor (mini model):** for k ∈ {0, 3, 6, 12}, fit `avg_m36 ~ avg_k + ln(raters_k) + ln(raters_k/raters_0 + 1)` (OLS) on entry years **2017–2019** and evaluate on **2020–2023**. Report test MAE and within-±0.25 share for raw vs adjusted (`q4_adjusted_predictor.csv`). This is the "a platform could display an adjusted launch rating" result.
- Note in the output that agreement at large k is partly mechanical: the running average at k=24 already contains most of the raters of k=36.

## Step 6: Robustness grid (`robustness.py`)

One table `robustness.csv/.md`: rows = variants, columns = β12, β36, share-by-12, Spec A hype coef, Spec B hype coef, n.
1. Baseline
2. Rater-weighted (weights = raters_m36; WLS / weighted means)
3. Excluding 2020–2021 entry cohorts (COVID)
4. Popular only (top 10% raters_m36) / rest
5. Entered with ≥ 50 raters (less noisy starting average)
6. Control-adjusted outcome (subtract mature-control change over the same calendar months; for the event study, subtract the control series from avg_rating by calendar month)
7. Unbalanced: all new releases with whatever follow-up exists (event study only)
8. Gap sensitivity (Fig 2 numbers at k = 6/12/36): `min_delta_raters` ∈ {5, 10, 25} × `max_error_bound` ∈ {0.25, 0.5, 1.0}, using the stored raw `new_avg_3` / `new_avg_err_3` / `delta_raters_3`. Separate small table `robustness_gap.csv`.

(Daily vs monthly snapshots is postponed: it needs a multi-GB download. List it as "not done" in the summary.)

## Step 7: Key numbers, summary, notebook

- `keynumbers.py` writes `key_numbers.json` with (at least): sample sizes; mean change at 12/24/36 + CI; median change_36; share declining; share of decline by month 12 + CI; control drift over 36 months; control-adjusted change_36; rater-weighted change_36; gap at k = 3/6/12/24/36; β12/β24/β36; hype coefficients for specs A–D (raw, standardised, p); quartile means; Q4 rule month + CI; MAE / within-0.25 at k = 0/3/6/12; adjusted-predictor test results; Q3 status. Each entry has `value`, `ci_low`, `ci_high` (if any), `n`, `source` (table/model), `definition`.
- `results_summary.md`: a facts-only rendering of key_numbers + links to every figure/table.
- `notebooks/02_results_walkthrough.ipynb` (optional, if jupyter is installed): loads the tables/figures and walks through them in order, saved **with outputs** so GitHub renders it. No new computations in the notebook.

## Step 8 (optional): Q3 crowdfunding (`crowdfunding.py`)

Needs the Kaggle dataset *"Board Game Database from BoardGameGeek"* (threnjen, CC BY-SA 3.0), which **the user downloads manually** (Kaggle needs a login) into `data/external/kaggle_bgg/`.
- If the folder is missing: skip with a clear log message and `"q3_status": "skipped: data not provided"` in key_numbers. Don't fail.
- If present: inspect `games.csv` columns first (expected an id column like `BGGId` and a `Kickstarted` flag; **verify, don't assume**). Report coverage of the main sample by entry year (`q3_coverage.csv`). Run Spec A + `kickstarted` (and `kickstarted × hype_log`) only on entry years with ≥ 50% coverage; otherwise report coverage only. Add the licence/attribution line to the README.

---

## Tests (`tests/`)
- `test_event_study.py`: simulate a small panel with known β_k and game effects, and confirm the estimator recovers them (tolerance).
- `test_curves.py`: mean/CI helper on a toy frame; the gap is computed row-wise; equal vs weighted options.
- `test_control_adjust.py`: calendar alignment of the control adjustment on toy data (entry month + 36).
- `test_keynumbers.py`: the JSON has all required keys, finite values, and CI low ≤ value ≤ high.

## Acceptance (sanity values from data_notes §11; tolerance ±0.01 unless stated)
- Main sample 6,927; balanced 6,918; control group 2,428 games.
- Balanced mean change_12 / 24 / 36 = −0.245 / −0.341 / −0.401; median change_36 −0.38; share declining 0.869.
- Control drift over the games' own 36-month windows ≈ −0.016; control-adjusted change_36 ≈ −0.385.
- Rater-weighted change_36 ≈ −0.274.
- Gap (equal weight, ok_3 rows) at k = 3 / 12 / 36 ≈ −0.15 / −0.20 / −0.23.
- Q2 Spec A hype coefficient ≈ +0.05 (SE ≈ 0.008); Spec B ≈ 0.00 (±0.02). Small differences from sample handling are fine. A sign flip versus these values is not: investigate it.
- Q4 within ±0.25: k=0 31.5%, k=6 55%, k=12 77%, k=18 91% (so the 80% rule lands around k = 13–15).
- All tests pass, ruff clean, `uv run bgg analysis` reruns end to end.

## Final report to the user
What was built; a table of the headline numbers (from key_numbers.json); any acceptance value that differed and why; what was skipped (Q3 if no data, daily robustness); exact rerun commands. Append a progress-log line to `docs/implementation_plan.md` and update the README "Run" section.

## Out of scope
Streamlit dashboard, narrative write-up, slide deck, daily-snapshot download. These come next, from the outputs of this task.
