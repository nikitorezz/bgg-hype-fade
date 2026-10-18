# Task 03: Analysis polish + interactive dashboard (milestone M6)

**Goal:** (A) close the gaps found in the analysis review, (B) give the static figures portfolio-grade "action" titles, (C) build a Streamlit dashboard that tells the story and lets visitors look up any game, (D) prepare deployment, but **don't deploy** until the user confirms the data-publication decision (step D0).

Read first: `CLAUDE.md`; `docs/findings.md` (**the review: verdict, interpreted findings F1–F9, story, caveats, and the items for this task**); `reports/writeup.md` (draft article; the dashboard text must agree with it); `reports/results/key_numbers.json`.

Rules carried over: every number shown anywhere comes from `key_numbers.json` or a `reports/tables/*.csv` (never typed into code or text); config-driven; build → run → check → commit per step.

---

## Part A: Analysis additions (extend `src/bgg/analysis/`, rerun `bgg analysis`)

### A1. New key numbers (marked [review check] in findings.md)
Add to `key_numbers.json` (with CI where it makes sense) and to `segments.csv` where it fits:
| key | definition | review value (sanity, ±0.01) |
|---|---|---|
| `change_6_by_hype_q{1..4}` | mean avg_m6 − avg_m0 by hype quartile, main sample | −0.099 / −0.156 / −0.210 / −0.193 |
| `rater_growth_m6_by_hype_q{1..4}` | mean raters_m6 / raters_m0 | ≈ 1.2 / 1.7 / 2.6 / 7+ (report the mean and the median) |
| `entry_rater_share_m36_by_hype_q{1..4}` | median raters_m0 / raters_m36 (share of today's raters who are the entry batch) | Q1 ≈ 0.5 |
| `gap_k36_by_hype_q{1..4}` | as `gap_k36`, by quartile | −0.30 / −0.24 / −0.22 / −0.23 (Q1 n is small, ~280) |
| `ks_avg_m0`, `nonks_avg_m0` | starting average by Kickstarted flag (Q3 sample) | 7.62 / 7.23 |
| `ks_gap_within_bands` | mean of (KS − non-KS change_36) across 0.5-wide avg_m0 bands 6.5–9.0, weighted by band size | ≈ −0.08 |
| `share_rank_improved_36` | share of main-sample games with rank_m36 < rank_m0 | ≈ 0.74 |
| `avg_rank100_vs_rank1000` | median raw avg of ranks 90–110 vs 990–1010 in the end-month snapshot | 7.93 / 7.30 |

### A2. Two new figures
- **Fig 9 `fig09_speed_not_size`**: per hype quartile, a dot at mean change by month 6 and a dot at month 36, joined by a line (dumbbell), with CIs. The title states the finding (see A3). This is the key Q2 visual.
- **Fig 10 `fig10_kickstarter`**: change_36 by starting-rating band (x), two series (Kickstarted vs not) with CIs, plus a small inset/label with the raw means. Footnote: the 2022 snapshot flag, descriptive only.
- Tables: `speed_not_size.csv`, `kickstarter_by_band.csv`.

### A3. Figure polish (all 10 figures)
- **Action titles** generated from key_numbers (a template in config, numbers filled at runtime), with the descriptive text moved to a subtitle. Examples:
  - Fig 1: "New games lose 0.40 rating points in 3 years, 61% of it in year one"
  - Fig 2: "New raters still rate games 0.23 below the displayed average at month 36"
  - Fig 6/9: "Hype changes how fast ratings fall, not how far"
  - Fig 8: "It takes ~13 months before a new game's rating can be trusted"
- Fig 6: ordered **sequential** palette for quartiles (light → dark), not categorical.
- Fig 3: add the mature-control change over the same calendar months as a dashed grey line on the **left** panel (same y-scale); keep the right panel but label it clearly as a zoomed scale.
- Fig 4: histogram x-range clipped to [−3, 2], with a note on the count outside the range.
- Fig 5: subtitle on the "largest rise" panels: "entered with unusually low early ratings".
- Export a 1200×630 PNG of Fig 1 as `reports/figures/social_card.png` (for README/LinkedIn).
- Rerun, check the figures by eye (look at every PNG), and commit.

## Part B: Dashboard data extract (`bgg dashboard-data`)

Build `app/data/` (git-ignored until D0 is decided) from processed data + reports:
- `games.parquet`: all 11,020 new releases: game_id, latest_name, entry_month, entry_year, pub_year_entry, in_main_sample, avg/raters at milestones, change_12/24/36, hype_log, hype_quartile, kickstarted (nullable), rank_m0, rank_m36, plus the **adjusted launch rating** at k=0/3/6/12 from the Q4 model (store the coefficients in key_numbers and apply them).
- `trajectories.parquet`: one row per game × k (0–36): k, snap_month, avg_rating, n_raters, rank, new_avg_3 (NULL unless `new_avg_ok_3`). Only the columns the app uses; float32 where safe.
- Copy the needed `reports/tables/*.csv` and `key_numbers.json` into `app/data/` (the app must not read from `reports/` directly, so it's self-contained for deployment).
- Target total < 20 MB. Log the size.

## Part C: Streamlit app (`app/streamlit_app.py` + `app/pages/` or tabs)

Stack: `streamlit`, `plotly`, `pandas`, `pyarrow`. Put the app's own requirements in `app/requirements.txt` (for cloud deploy). Charts use Plotly with a palette matching `src/bgg/style.py`. Cache all loads with `st.cache_data`. Wide layout; every chart must still read at ~400 px width (phone).

Sections (tabs or pages, in this order):

1. **Overview: "Does the hype fade?"**
   - One-sentence headline (the story from findings.md §3).
   - 4 KPI tiles: −0.40 (3-year change), 61% (share in year 1), 87% (share declining), month 13 (trust point). Each tile has a one-line caption.
   - Interactive Fig 1: a "Compare by" selector [none, launch year, hype quartile, popularity (top 10% vs rest), Kickstarted] and a toggle "adjust for site-wide drift". Hover shows mean, CI and n.
2. **New raters vs displayed**: interactive Fig 2 + a 3-sentence explainer of the new-rating average (formula in an expander) + the usable-share panel.
3. **Hype: speed, not size**: Fig 9 interactive + Fig 6 curves + a compact coefficient chart for Specs A–D (dot ± CI, zero line, H2's predicted direction shaded) + Kickstarter Fig 10. Plain-language takeaway box.
4. **When can you trust a rating?**: Fig 8 with **two sliders**: tolerance (±0.10 … ±0.50, default 0.25) and target share (60 … 95%, default 80%). Recompute the trust month live from `trajectories` + `games` (main sample) and show it as a big number. Below: raw vs adjusted launch rating comparison (test set) as a small grouped bar.
5. **Look up a game**: searchable select over latest_name (shows entry year to disambiguate duplicates). It shows:
   - line: displayed average by month since entry; dots: new_avg_3 where available; secondary axis or small panel: raters
   - dashed reference: the mean trajectory of the game's launch-year cohort, shifted to start at the game's avg_m0
   - stat cards: entry month, start → month-36 rating (or latest), change vs cohort (percentile), hype quartile, adjusted launch rating vs what actually happened, rank start → now
   - games with < 36 months of follow-up are shown with "still in follow-up"
   - default selection: a famous example from the spot-check list (e.g. Ark Nova)
6. **Method & data**: short method (reuse write-up sections), sample waterfall, QC summary (36/36 PASS), limitations (from findings.md §4), credits/licence line, link to repo and write-up.

Footer on every page: data source + "© BoardGameGeek" + "not affiliated with BGG".

Don't build: user accounts, live data fetching, editing.

## Part D: Deployment prep

- **D0, decision required from the user (ask; don't assume):** the source archive has no licence, and publishing `app/data/` (game-level numbers) is an open decision (`docs/implementation_plan.md` §11). Present the options: (1) deploy with the full extract after asking the archive owner (open a GitHub issue; draft its text for the user), (2) deploy an **aggregates-only** mode (`APP_MODE=aggregates`: hides "Look up a game" and only ships the curve/segment tables), (3) local only + screenshots/GIF in the README. Implement the `APP_MODE` switch either way.
- Prepare Streamlit Community Cloud: entry point `app/streamlit_app.py`, `app/requirements.txt`, no secrets needed. Write the deploy steps into `docs/deploy.md`. Note that Streamlit Cloud may be unreachable from mainland China and that the target audience is international. Add a fallback: `bgg export-static` builds `reports/site/index.html`, a single self-contained page with the Overview, Gap, Hype and Trust charts (Plotly, inline data, no lookup) that can be hosted on GitHub Pages.
- Record a short GIF or screenshots of the app for the README (`reports/figures/app_*.png`).

## Tests
- `tests/test_app_smoke.py` with `streamlit.testing.v1.AppTest`: each section renders without exceptions in both APP_MODEs.
- Trust-month function: with defaults it returns 13 (equals key_numbers).
- The extract builder: row counts, no main-sample game missing, size < 20 MB.
- The adjusted-rating column equals the model formula applied to the stored coefficients.

## Acceptance
- `bgg analysis` reruns with figs 1–10 and the new key numbers within the review values.
- `uv run streamlit run app/streamlit_app.py` starts locally in under ~3 s after caching. Every tile/number matches key_numbers. Lookup works for all 10 spot-check games (Gloomhaven is *not* a new release, so it must be handled gracefully as "not in sample").
- `bgg export-static` produces a single HTML file that opens offline.
- Tests pass, ruff clean, README "Run" section updated (dashboard + static export).
- Final message to the user: what was built, screenshots, the D0 question with the drafted GitHub issue text, and any number that changed.

## Out of scope
The final README rewrite and the write-up polish (task 04, after deployment), the slide deck, and the daily-snapshot robustness check.
