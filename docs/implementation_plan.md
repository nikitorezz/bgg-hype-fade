# Does the Hype Fade? — Portfolio Implementation Plan

*Living document. Source: unused research proposal "Does the Hype Fade? Post-Release Rating Trajectories of Board Games on BoardGameGeek, 2016–2026". Last edited: 18 Oct 2026.*

---

## 0. What changes from the proposal

The proposal was written as an academic paper. As a portfolio piece for a move into data analytics, the audience is a hiring manager or analytics lead who will spend 2–5 minutes on it. So:

| Proposal (academic) | Portfolio version |
|---|---|
| Literature review of ~13 sources | 1 short "why this matters" paragraph citing 3–4 key sources |
| Hypotheses H1/H2 | Same questions, framed as business questions ("Can we trust launch-week ratings?") |
| Paper + slides | GitHub repo + readable write-up + interactive dashboard |
| Panel regression is the headline | Clear charts are the headline; regression backs them up |
| Deadline-driven timeline (Sep–Dec) | Self-paced, ~45 h over ~5–6 weeks |

What stays: the data source, the cohort design, the "new-rating average" trick, and the honesty about limitations. Those are the parts that show analyst judgement.

**Business framing (one line):** *Launch ratings on rating platforms are inflated by enthusiastic early adopters. Using 10 years of daily BoardGameGeek snapshots, I measure how much and how fast new board games' ratings fall, and whether the most-hyped launches fall hardest.*

---

## 1. Questions

**Q1 — Trajectory.** How does a game's average BGG rating change over the 36 months after it enters the ranking? How much of the change happens in year 1?

**Q2 — Hype.** Do games that gain raters fastest in their first 6 months decline more?

**Q3 (stretch) — Crowdfunding.** Do Kickstarter games decline more than retail games? (Needs Kaggle metadata; coverage may be limited.)

**Q4 (stretch, analyst-flavoured) — Practical rule.** At what age does a game's rating become a reliable predictor of its 36-month rating? (e.g. correlation / mean absolute error of rating at month *k* vs month 36, for k = 0, 3, 6, 12.) This turns the finding into a recommendation for a platform ("show a 'new release' badge until month X").

---

## 2. Deliverables

1. **GitHub repository** — reproducible pipeline, clean README with the key chart at the top, results summary, how to rerun.
2. **Write-up** — ~1,500-word article (README section, blog post or a published Doc), structured: question → data → 3–4 charts → findings → limitations → what a platform could do.
3. **Interactive dashboard** — Streamlit app: (a) cohort trajectory chart with filters (entry year, hype quartile, crowdfunded), (b) "look up any game" rating trajectory with the new-rating average overlaid.
4. **SQL showcase** — the DuckDB pipeline as readable, commented `.sql` files (this is the part interviewers ask about).
5. **Optional:** a 5-slide summary deck for interviews.

---

## 3. Data

### 3.1 Primary: daily ranking snapshots
- Repo: `github.com/beefsack/bgg-ranking-historicals` — one CSV per day, 12 Oct 2016 → present (3,633+ files checked 23–24 Sep 2026).
- Columns: `ID, Name, Year, Rank, Average, Bayes average, Users rated, URL, Thumbnail`.
- File size grows 12.7k → 31.4k rows; full daily set is several GB (~75M rows), monthly subset ~0.5 GB (~2.5M rows).
- Licence: not confirmed — check the repo before publishing; cite the repo and BGG; non-commercial use; **don't redistribute raw files in your repo** (ship the download script instead, and at most derived aggregates).

### 3.2 Optional: Kaggle metadata
- "Board Game Database from BoardGameGeek" (threnjen), CC BY-SA 3.0, ~22k games, includes a Kickstarted flag, complexity (weight), mechanics and themes.
- Older snapshot → covers mainly games released before it was made. Measure coverage of your cohort before committing to Q3.
- Join on BGG game ID.

### 3.3 Not used
- BGG XML API (now needs approved registration + token) and site scraping (bot check). Don't plan on either.

### 3.4 Pilot findings (verified 18 Oct 2026; details in `docs/data_notes.md`)
- Branch `master`, flat repo of `YYYY-MM-DD.csv` files, **no LICENSE file**. Schema unchanged since 2016. One missing day (2019-10-24).
- **Truncated snapshot files:** 2024-01-01 and 2024-09-01 are partial scrapes (~22k rows instead of ~25.5k / ~26.7k) → monthly selection must validate row counts (use 2024-01-05 and 2024-09-03).
- **Duplicate rows** within a snapshot (~720 pairs, from rank shifts during the scrape) → dedup per (date, game).
- **`Average` has 2 decimals** → the new-rating average needs a rounding-error bound, not just a minimum Δraters.
- Publication year changes over time for ~1.6k games → use the year **at entry**. Year 0 = unknown; a few junk years (2200–3500).
- The cohort rule reproduces the proposal's entry counts **exactly** (2017: 1,033 … 2023: 1,213).
- First look at H1: mean rating change from entry is −0.24 at 12 months, −0.33 at 24, −0.40 at 36, so ~60% of the 3-year decline happens in year 1.

---

## 4. Repository layout

```
bgg-hype-fade/
├── README.md                  # headline chart + 5-bullet findings + how to run
├── pyproject.toml             # or requirements.txt (pin versions)
├── (no Makefile — Windows)     # orchestration via CLI: uv run bgg download|load|cohorts|panel|qc|all
├── config.yaml                # date range, thresholds, cohort rules
├── data/
│   ├── raw/                   # gitignored — downloaded CSVs
│   ├── interim/               # gitignored — monthly.parquet
│   └── processed/             # panel.parquet, game_summary.parquet (small enough to commit or release)
├── sql/
│   ├── 01_load_monthly.sql
│   ├── 02_entry_and_cohorts.sql
│   ├── 03_panel.sql
│   └── 04_quality_checks.sql
├── src/bgg/
│   ├── download.py
│   ├── build.py               # runs the SQL via DuckDB
│   ├── analysis.py            # models
│   └── plots.py               # figure functions, shared by notebook + app
├── notebooks/
│   ├── 01_pilot.ipynb
│   ├── 02_eda.ipynb
│   └── 03_results.ipynb
├── app/streamlit_app.py
├── reports/
│   ├── figures/
│   └── writeup.md
└── tests/test_panel.py        # a few sanity tests on derived data
```

---

## 5. Pipeline

> **Build spec for steps 1–5:** `docs/handoff/01_TASK_pipeline_steps_1-5.md` is authoritative where it differs from the sketch below (truncated-file validation, dedup, rounding-error bound, 3-month window, manifest-driven loading).

### Step 1 — Download (monthly subset first)
- Get the file list via the GitHub trees API (`/repos/beefsack/bgg-ranking-historicals/git/trees/<branch>?recursive=1`; <100k entries, so not truncated).
- For each calendar month, select the **first available date** (some days are missing). Download those ~120 files from `raw.githubusercontent.com`.
- Alternative: `git clone --depth 1 --filter=blob:none --sparse` + `git sparse-checkout set --no-cone` with a pattern list of the chosen file names.
- Full daily download only later, for the daily-vs-monthly robustness check.
- Make the script idempotent (skip files already present) and log failures.

### Step 2 — Load to DuckDB → Parquet (`01_load_monthly.sql`)
```sql
CREATE OR REPLACE TABLE snapshots AS
SELECT
    CAST(regexp_extract(filename, '(\d{4}-\d{2}-\d{2})', 1) AS DATE) AS snap_date,
    "ID"            AS game_id,
    "Name"          AS name,
    "Year"          AS pub_year,
    "Rank"          AS rank,
    "Average"       AS avg_rating,
    "Bayes average" AS bayes_avg,
    "Users rated"   AS n_raters
FROM read_csv('data/raw/*.csv', filename = true, union_by_name = true);

COPY snapshots TO 'data/interim/monthly.parquet' (FORMAT parquet);
```
- Add `snap_month = date_trunc('month', snap_date)`.
- Check header/column changes across years (`union_by_name` handles renames only if names match — inspect a 2016 and a 2026 file first).

### Step 3 — Entry month and cohorts (`02_entry_and_cohorts.sql`)
- `entry_month` = first `snap_month` in which a game appears.
- **Exclude** games present in the first snapshot (Oct 2016) — left-censored, true entry unknown.
- **New release rule:** `pub_year >= year(entry_month) - 1`. Treat `pub_year = 0` / null as unknown → exclude (report how many).
- Main sample: entry between Jan 2017 and the latest month that still allows 36 months of follow-up (~Sep 2023). Report the 24-month sample separately.
- `months_since_entry` = month difference between `snap_month` and `entry_month` (0…36).
- Expected counts (from pilot): ~10.9k new releases overall, ~7.1k with ≥36 months.

### Step 4 — Panel and derived variables (`03_panel.sql`)
Per game-month:
- `avg_rating`, `n_raters`, `rank`
- `delta_raters = n_raters - lag(n_raters)`
- **New-rating average** (the "analyst touch"):
  `new_avg = (avg_t * n_t - avg_{t-1} * n_{t-1}) / (n_t - n_{t-1})`
  - Set to NULL when `delta_raters < 10` (noisy) — make the threshold a config value and test 5/10/25.
  - Flag values outside [1, 10]: these reveal rating edits/deletions; count them rather than silently drop.
  - Note: `Average` is rounded in the CSV (check decimals); rounding error × large n can swamp small increments → another reason for the minimum-Δ threshold.
- Rating change vs month 0: `d_rating = avg_rating - avg_rating_at_m0`.

Per game (`game_summary`):
- `avg_m0, avg_m12, avg_m24, avg_m36`, `raters_m0, raters_m6, raters_m36`
- **Hype proxy:** `hype = log(raters_m6 + 1) - log(raters_m0 + 1)` (relative growth). Also keep absolute raters added by month 6 as an alternative.
- `hype_quartile` within entry year (so 2017 and 2022 launches are comparable).
- `change_36 = avg_m36 - avg_m0`.

### Step 5 — Quality checks (`04_quality_checks.sql` + `tests/`)
- Duplicates per (game_id, snap_month) = 0.
- Games that disappear and reappear (count; keep, forward-fill not needed for monthly).
- `n_raters` decreasing month to month (count; indicates deletions).
- Missing months in the snapshot series (list).
- Cohort size table vs pilot numbers (should match within a few %).
- Spot-check 5 well-known games (e.g. one big Kickstarter hit, one mass-market release) against what you'd expect on BGG.

---

## 6. Analysis

### 6.1 Descriptive (the headline)
- **Figure 1:** mean rating change from month 0 by months since entry (0–36), with 95% CI band. Overlay the mean **new-rating average** — this is the most interesting chart: it shows what *current* raters think vs the sticky running average.
- **Figure 2:** same, split by hype quartile.
- **Figure 3:** by entry year (cohort lines) — checks whether the pattern is stable and shows the 2020–21 COVID cohorts.
- **Figure 4 (Q4):** "how predictive is the month-k rating of the month-36 rating?" — MAE or R² by k.
- **Table 1:** cohort sizes (entering / ≥24 m / ≥36 m).

### 6.2 Models
**Q1 — event-study panel regression**
- `avg_rating_it = α_i + Σ_k β_k·1[months_since_entry = k] + ε_it`, k = 1…36, month 0 omitted.
- Game fixed effects; SEs clustered by game. Python `linearmodels.PanelOLS` (or R `fixest::feols`).
- Report β at 12, 24, 36 with CIs, and the share of the 36-month decline reached by month 12.
- Caveat to state: age, period and cohort can't all be separated. As a robustness check add calendar-year effects (captures site-wide rating drift) — interpret carefully.

**Q2 — cross-sectional regression**
- `change_36_i = γ·hype_i + δ·avg_m0_i + entry-year FE + log(raters_m0) + u_i`, robust SEs.
- Controlling for `avg_m0` matters: high starting averages mechanically regress toward the mean.
- Also report the simple quartile comparison (Figure 2) — easier to read than a coefficient.

**Q3 (stretch)** — add `kickstarted` (and its interaction with hype) on the Kaggle-covered subset; report coverage.

### 6.3 Robustness (pick 3–4, keep short)
- Monthly vs daily snapshots for one cohort.
- Exclude 2020–21 entry cohorts.
- Popular vs niche: split by raters at month 36 (top 10% vs rest).
- New-rating threshold 5 / 10 / 25.
- Unweighted vs weighted by raters.

### 6.4 Limitations (write them plainly — this signals maturity)
- Entry requires a minimum number of ratings, so the earliest ratings are bundled into month 0; analysis measures change *after* entry.
- Rating edits make the new-rating average approximate.
- Rater growth also reflects print run and distribution, not only hype.
- One platform; BGG users are enthusiasts; observational → no causal claims.

---

## 7. Dashboard (Streamlit)

- **Tab 1 — The pattern:** Figure 1 with filters (entry year range, hype quartile, crowdfunded if available, min. raters).
- **Tab 2 — Look up a game:** searchable name box → monthly average, new-rating average, raters, rank over time; annotate the game's cohort mean for comparison.
- **Tab 3 — Method:** 5-bullet explanation + link to repo.
- Data for the app: ship only `panel.parquet` (new releases, monthly, needed columns) and `game_summary.parquet`; target <50 MB. Load with DuckDB or polars, cache with `st.cache_data`.
- Hosting: Streamlit Community Cloud (free; GitHub-based). Check it's reachable for you and for overseas viewers; fallback = Hugging Face Spaces, or a static HTML page with Plotly charts.

---

## 8. Tools

| Purpose | Tool |
|---|---|
| Environment | Python 3.11+, `uv` or `venv`, pinned versions |
| Download | `requests` + GitHub API (or sparse git clone) |
| Storage / SQL | DuckDB → Parquet |
| Data handling | polars or pandas |
| Models | `linearmodels` (PanelOLS), `statsmodels` (OLS) — or R `fixest` |
| Figures | matplotlib/seaborn for static, Plotly for the app |
| App | Streamlit |
| Orchestration | Makefile (one command per stage) |
| Quality | `pytest` sanity tests, `ruff` for linting |

---

## 9. Milestones (~45 h, ~5–6 weeks, self-paced)

| # | Milestone | Tasks | Done when | Est. h |
|---|---|---|---|---|
| M1 | Setup + pilot | Repo skeleton, env, download monthly files, load to DuckDB, plot 5 games | 5 trajectories plotted; cohort counts match pilot | 5 |
| M2 | Clean panel | SQL steps 2–4, entry/cohort rules, new-rating average, quality checks + tests | `panel.parquet` + `game_summary.parquet` built by `make panel`; QC report clean | 9 |
| M3 | EDA + headline chart | Figures 1–3, Table 1 | Headline chart you'd put at the top of the README | 6 |
| M4 | Models | Q1 event study, Q2 regression, Q4 predictive check, robustness | Results table + 3–4 robustness lines | 9 |
| M5 | Stretch: crowdfunding | Kaggle join, coverage check, Q3 | Coverage reported; Q3 result or a clear "insufficient coverage" note | 3 |
| M6 | Dashboard | Streamlit app, deploy | Public URL works on phone and desktop | 7 |
| M7 | Write-up + polish | Article, README, figure polish, limitations, slide summary | Someone unfamiliar can get the finding in 2 minutes | 6 |

Suggested pacing from 19 Oct: M1–M2 by early Nov, M3–M4 by mid/late Nov, M6–M7 by early Dec.

---

## 10. Risks

| Risk | Mitigation |
|---|---|
| CSV schema changed over 10 years | Inspect earliest/latest headers in M1; normalise names in SQL |
| Missing days in archive | Use first available date per month; log gaps |
| New-rating average noisy | Minimum Δraters threshold; show it as a smoothed line |
| Kaggle coverage of 2017–23 games too low | Keep Q3 optional; report coverage honestly |
| Data licence unclear (repo has no LICENSE) | Don't commit raw or processed data; cite source; non-commercial; consider asking the repo owner |
| Truncated daily files | Row-count validation when selecting files (see data notes §3) |
| GitHub slow/blocked from mainland China | Proxy support, retries, resumable downloads, git fallback backend |
| Hosting blocked/slow | Static Plotly HTML fallback; screenshots/GIF in README |
| Scope creep | Q3/Q4 and the deck are stretch; the core is Q1 + Q2 + Figure 1 + app |

---

## 11. Open decisions

- [x] Python only (`linearmodels`/`statsmodels`) for models (decided 2026-10-18)
- [ ] Write-up home: README only, a blog (Medium/personal site), or both?
- [x] Q3 (crowdfunding) included: Kaggle data provided, descriptive result (decided 2026-10-18)
- [x] Include Q4 (predictive rule) + an adjusted-predictor mini model (decided 2026-10-18)
- [x] Dashboard: Streamlit + static HTML fallback (decided 2026-10-18)
- [ ] May derived data (panel/game_summary) be published for the dashboard, given the source repo has no licence?

---

## 12. Key sources (for the write-up)

- Li & Hitt (2008), *Information Systems Research* — self-selection in early reviews.
- Godes & Silva (2012), *Marketing Science* — sequential/temporal dynamics of ratings.
- Hu, Pavlou & Zhang (2017), *MIS Quarterly* — self-selection biases.
- Kovács & Sharkey (2014), *ASQ* — publicity lowers later ratings.
- Booth (2022), *Material Game Studies* — the "cult of the new".
- Wachs & Vedres (2021); Butticè & Noonan (2020) — BGG + crowdfunding studies that treat ratings as fixed.
- Heron et al. (2018) — rationale for raw Average over Bayes average (as in the proposal; verify the claim before citing).

---

## 13. Progress log

| Date | Milestone | Notes |
|---|---|---|
| 2026-10-18 | Plan | Plan created from proposal |
| 2026-10-18 | Pilot + handoff | Monthly files checked in DuckDB; data traps documented (`docs/data_notes.md`); Claude Code spec for steps 1–5 written (`docs/handoff/`) |
| 2026-10-18 | Pipeline steps 1-5 | `uv run bgg all` runs download, load, cohorts, panel and qc end to end and is idempotent. 121 months, 2.61M rows, 11,020 new releases, 335,973 panel rows. QC: 36 PASS, 0 WARN, 0 FAIL (+7 INFO). Deviations from spec: first-month window fallback; 2021 cohort is 977, not 978 (junk pub year 3000, see data_notes section 10). |
| 2026-10-18 | Analysis handoff | Pre-checks on processed data (data_notes §11): fade −0.40 at 36 m, ~61% in year 1, 87% decline; site drift only −0.016; H2 looks unsupported (hype coef +0.05 with controls). Task 02 spec written (`docs/handoff/02_TASK_analysis.md`) |
| 2026-10-18 | Analysis M3-M5 | `uv run bgg analysis` runs descriptives, event study, Q2 specs A-D, Q4 rule and adjusted predictor, robustness grid, Q3 (Kaggle data present) and key_numbers.json (117 numbers). All 20 data_notes section 11 sanity values reproduced. H2 not supported (hype coefficients A +0.049, B -0.004). Skipped: daily-vs-monthly robustness, walkthrough notebook. See data_notes section 12. |
| 2026-10-18 | Analysis review + dashboard handoff | Analysis validated (all 20 sanity values, consistent robustness). New insight: hype changes the *speed* of the fade, not its size (dilution of entry ratings); Kickstarter games fade more even at equal start. Written: `docs/findings.md`, draft `reports/writeup.md`, task 03 spec `docs/handoff/04_TASK_dashboard.md` |
