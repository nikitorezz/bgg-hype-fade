# Data notes: verified facts and traps

Source: `github.com/beefsack/bgg-ranking-historicals`. All facts below were **verified on 2026-10-18** by a pilot run on the 121 first-of-month files (Oct 2016 → Oct 2026) loaded into DuckDB. Numbers marked *(pilot)* came from that run. The pilot used naive "first file of the month" selection, so a few numbers will shift slightly once the truncation fix in §3 is applied.

---

## 1. Repository layout

- Branch: `master`. Flat repo: **only** files named `YYYY-MM-DD.csv` at the root. No README, **no LICENSE file**.
- 3,658 daily files, 2016-10-12 → 2026-10-18 (one new file per day).
- **One missing day:** 2019-10-24 (doesn't affect monthly selection).
- First file is **2016-10-12** (so the Oct 2016 snapshot isn't on day 1). Every other month has a day-1 file.
- File size grows ~1.6 MB (12.8k rows, 2016) → ~6.9 MB (31.4k rows, 2026). The 121 monthly files total **~700 MB, ~2.6M rows**.
- ⚠️ In a blobless git clone, **don't run `git ls-tree -l`**: asking for sizes fetches every blob (≈ the whole archive). `git ls-tree --name-only HEAD` is fine.

## 2. Schema (stable across the whole period)

Header in every checked file (2016, 2018, 2020, 2023, 2026):
```
ID,Name,Year,Rank,Average,Bayes average,Users rated,URL,Thumbnail
```
| Column | Type | Notes |
|---|---|---|
| ID | BIGINT | BGG game id; join key |
| Name | VARCHAR | contains commas/quotes; DuckDB's CSV reader handles it. Names change over time, so use the latest name for display |
| Year | INTEGER | publication year. `0` = unknown (432 games). Junk values exist: 2200, 2500, 2600, 3000 (×3), 3500. **Changes over time for 1,592 games** |
| Rank | INTEGER | geek rank on that day; not perfectly unique (see duplicates) |
| Average | DOUBLE | **raw mean rating, rounded to 2 decimals** (range seen 1.03–10.00) |
| Bayes average | DOUBLE | 3 decimals; not used as outcome |
| Users rated | INTEGER | number of raters; **minimum is always 30** (BGG's ranking threshold) |
| URL, Thumbnail | VARCHAR | drop (URL is derivable: `https://boardgamegeek.com/boardgame/{ID}`) |

## 3. Truncated snapshot files ⚠️

Some daily files are **partial scrapes**: row count is far below the neighbouring days, and often a suspiciously round number.

| Month | Day 1 rows | Previous month rows | Following days | First complete file |
|---|---|---|---|---|
| 2024-01 | 22,100 | 25,488 | 01-02: 22,800 · 01-03: 23,800 · 01-04: 24,800 · **01-05: 25,646** | **2024-01-05** |
| 2024-09 | 22,300 | 26,731 | 09-02: 22,500 · **09-03: 26,940** | **2024-09-03** |

Also truncated: 2023-12-31 (20,000 rows) and 2024-08-31 (11,300 rows). Neither is a first-of-month file, but they matter for the later daily robustness check.

In the pilot, these two bad files caused most of the "games disappearing for a month" events (4,596 gap starts at 2024-09 and 3,550 at 2024-01) and made follow-up counts look lower than they are.

**Rule:** within each month, take the earliest file (days 1–10) whose row count is ≥ 0.99 × the row count of the previous month's accepted file. Log rejected candidates. With this rule the expected picks are day 1 everywhere except 2016-10-12, 2024-01-05 and 2024-09-03. Treat any other substitution as a finding and record it here.

## 4. Duplicate rows within a snapshot

*(pilot)* 721 (date, game) pairs appear twice in the same file, spread across 16 monthly files (worst: 2025-06-01 with 212 and 2026-08-01 with 136). Cause: the list is scraped page by page while ranks shift, so a game can land on two pages. 691 of the pairs are identical rows; the rest differ slightly (e.g. raters 6130 vs 6131).
**Rule:** keep one row per (snap_date, game_id), ordered by `n_raters DESC, rank ASC`. Report how many were removed.

## 5. Cohort facts *(pilot)*

- 31,676 distinct games ever ranked; 12,759 are already in the first snapshot → **left-censored, excluded**.
- New-release rule (pub year **at first appearance** ≥ entry year − 1, pub year > 0) reproduces the proposal's entry counts **exactly**:

| Entry year | New releases | Observed at k=12 | k=24 | k=36 (pilot, naive files) | k=36 (proposal) |
|---|---|---|---|---|---|
| 2016 (Nov–Dec) | 240 | 238 | 238 | 238 | – |
| 2017 | **1,033** | 1,030 | 1,028 | 1,028 | 1,028 |
| 2018 | **1,045** | 1,040 | 1,039 | 1,039 | 1,040 |
| 2019 | **1,068** | 1,064 | 1,064 | 1,062 | 1,062 |
| 2020 | **921** | 915 | 912 | 910 | 911 |
| 2021 | **978** | 975 | 975 | 965 | 973 |
| 2022 | **1,055** | 1,046 | 1,038 | 1,047 | 1,047 |
| 2023 | **1,213** | 1,196 | 1,202 | 869 (entry ≤ Oct 2023) | 779 (data to Sep 2026) |
| 2024 | 1,235 | 1,227 | 894 | – | – |
| 2025 | 1,267 | 912 | – | – | – |
| 2026 (to Oct) | 966 | – | – | – | – |
| **Total** | **11,021** | | | | |

  The k=36 gaps for 2021 (965 vs 973) come from the truncated 2024 files. After the §3 fix, expect values at or very near the proposal's.
- Excluded among post-2016 entrants: 287 with unknown pub year, 7,609 "old games entering late".
- Raters at entry (k=0) for new releases: p10 = 30, median = 34, p90 = 64. Most games enter just above the 30-rater threshold.
- 321 games drop out of the ranking before the end; follow-up is otherwise nearly complete.
- Pre-release entries happen (e.g. Frosthaven entered Jan 2020 with pub year 2021, from crowdfunding backers). The rule keeps them.

## 6. The new-rating average and 2-decimal rounding ⚠️

`new_avg = (avg_t·n_t − avg_p·n_p) / (n_t − n_p)`

Because `Average` is rounded to ±0.005, the worst-case error of `new_avg` is:

`err = 0.005 · (n_t + n_p) / (n_t − n_p)`

For a game with 60,000 raters gaining 100 in a month, err ≈ ±6 rating points, which is pure noise. A fixed "Δraters ≥ 10" rule doesn't catch this.
**Rule:** usable iff Δraters ≥ `min_delta_raters` **and** err ≤ `max_error_bound` **and** the result is in [1, 10].

*(pilot, 1-month window)* 274k month-steps with Δraters > 0; 103k have Δ ≥ 10; 207k have err ≤ 0.5. 3,439 values fall outside [1, 10], and 1,255 of those remain outside even with err ≤ 0.5 (rating edits/deletions).
**Usable share falls with game age** (err ≤ 0.5): k=1 100%, k=3 99%, k=6 96%, k=12 88%, k=24 64%, k=36 36%. At late ages, usable values over-represent fast-growing games, which is a selection effect to state in the analysis. A **3-month window** (k vs k−3) roughly triples Δ and cuts err ~3×, so compute both.

## 7. Other quirks

- *(pilot)* `Users rated` decreases month to month in ~1.5% of steps (4,769 of 324,736) and is unchanged in ~14%. Decreases mean deleted ratings: flag them and give no `new_avg` for those steps.
- Within months 0–36, 442 new-release games had at least one missing month *(pilot; most should disappear after the §3 fix)*. **Don't interpolate.** Missing months have no panel rows, and lagged values are only computed across exactly consecutive months.
- Rank isn't strictly unique per snapshot (e.g. 2026-10-01: 31,394 rows, 31,355 distinct ranks).

## 8. Sanity values for results *(pilot)*

Mean change in `Average` from k=0, all new releases (unbalanced):

| k | 1 | 6 | 12 | 24 | 36 |
|---|---|---|---|---|---|
| mean Δ | −0.046 | −0.161 | −0.238 | −0.332 | −0.400 |
| games | 10,851 | 10,353 | 9,643 | 8,390 | 7,158 |

Spot-check games (values from first-of-month files; none of these months are affected by the truncation fix):

| ID | Game | Entry | Pub yr | In cohort | avg k0 | raters k0 | raters k6 | avg k12 | avg k36 | raters k36 |
|---|---|---|---|---|---|---|---|---|---|---|
| 174430 | Gloomhaven | 2016-10 | 2016 | no (left-censored) | 8.67 | 58 | 2,516 | 9.01 | 8.87 | 28,171 |
| 233078 | Twilight Imperium (4th Ed.) | 2017-09 | 2017 | yes | 8.77 | 82 | 2,098 | 8.80 | 8.69 | 11,607 |
| 224517 | Brass: Birmingham | 2017-12 | 2018 | yes | 8.73 | 33 | 65 | 8.67 | 8.65 | 17,047 |
| 266192 | Wingspan | 2019-01 | 2019 | yes | 8.08 | 32 | 9,083 | 8.09 | 8.10 | 55,431 |
| 295770 | Frosthaven | 2020-01 | 2021 | yes | 7.09 | 48 | 305 | 7.18 | 7.75 | 1,052 |
| 291457 | Gloomhaven: Jaws of the Lion | 2020-07 | 2020 | yes | 9.22 | 438 | 5,822 | 8.78 | 8.50 | 29,202 |
| 312484 | Lost Ruins of Arnak | 2020-10 | 2020 | yes | 8.16 | 39 | 3,665 | 8.11 | 8.08 | 37,788 |
| 295947 | Cascadia | 2020-10 | 2021 | yes | 7.95 | 66 | 228 | 8.09 | 7.97 | 29,574 |
| 316554 | Dune: Imperium | 2020-12 | 2020 | yes | 8.04 | 71 | 4,877 | 8.31 | 8.42 | 39,421 |
| 342942 | Ark Nova | 2021-11 | 2021 | yes | 8.50 | 252 | 6,383 | 8.60 | 8.53 | 46,693 |

Not every hit declines (Dune: Imperium and Frosthaven rose), which makes for good dashboard examples.

## 9. Licence

The repository has **no LICENSE file** (checked 2026-10-18), so by default no reuse rights are granted. Until that's resolved: don't commit raw or processed data to a public repo. Ship the download script, cite the repository and BoardGameGeek, and use the data non-commercially. Whether derived aggregates may be published (for the dashboard) is an **open decision**; opening an issue to ask the repo owner is an option.

---

## 10. Findings from the full pipeline run *(2026-10-18, truncation fix applied)*

- **Download:** 121 files selected, 2,611,791 data rows, **541 MB** (the "~700 MB" above was an over-estimate). Took ~2 min over plain http from mainland China, no proxy needed. Substitutions are exactly 2024-01-05 and 2024-09-03; every other month is day 1 except 2016-10-12. Raw line count equals DuckDB's row count, so no `Name` contains an embedded newline.
- **First month:** the archive's first file is 2016-10-12, outside the `max_candidate_day` = 10 window. The selection falls back to the earliest file of a month when its day window is empty (logged as a WARNING, status `ok`).
- **CSV sniffer trap:** DuckDB's auto-detection fails on names such as `"Tarleton's Quarter!"` (written as `"""Tarleton's Quarter!"""`) and reports an unterminated quote. `sql/01_load.sql` therefore sets the dialect explicitly (`auto_detect = false`, comma, `"` quote and escape).
- **Dedup:** 721 duplicate rows removed in 16 files, identical to the pilot. Ties after `n_raters DESC, rank ASC` are broken by further keys purely for determinism.
- **Junk publication years at entry:** `Year = 3000` is a placeholder for ancient games, e.g. *Knucklebones* (id 11726, entered 2021-10). A naive "pub year ≥ entry year − 1" rule would call it a 2021 new release; the pilot did, which is why the proposal's 2021 count is 978. With the junk-year cleaning rule from config the correct count is **977** (unknown/junk pub year among later entrants is 288 = 287 zeros + this one; total new releases 11,020). Left-censored (12,759) and old games (7,609) match the pilot.
- **Cohort sizes after the fix** (new releases / observed at m36): 2017 1,033 / 1,028 · 2018 1,045 / 1,039 · 2019 1,068 / 1,062 · 2020 921 / 910 · 2021 977 / 972 · 2022 1,055 / 1,047. Observed-at-m36 is not below the pilot anywhere. The proposal's 1,040 (2018), 911 (2020) and 973 (2021) are one game higher than ours; the 2021 gap is Knucklebones, the other two were not investigated further (±1).
- **Missing months:** 286 new releases miss at least one month in k = 0…36 (pilot 442). 208 have an internal gap, 79 left the ranking early (one game can be in both).
- **Panel:** 335,973 rows, 11,020 games. Mean change in `Average` from k=0: −0.046 (k=1), −0.160 (6), −0.237 (12), −0.332 (24), −0.401 (36); matches §8. Raters decreased in 4,766 of 324,733 one-month steps (1.47%); unchanged in 14.0%.
- **Usable `new_avg` share (Δ ≥ 10 raters AND error bound ≤ 0.5 AND in [1, 10]), 1-month / 3-month window:** k=3 37% / 69%, k=12 33% / 59%, k=36 14% / 49%. Much lower than §6's err-only figures because the Δ ≥ 10 rule also binds early, when games gain few raters per month.

---

## 11. Analysis pre-checks *(2026-10-18, on the final processed data; sanity values for task 02)*

Quick checks run on `panel.parquet`, `game_summary.parquet` and `snapshots_monthly.parquet` before writing the analysis spec. They're sanity values, not results to aim for.

**Samples.** Main sample (in_main_sample AND observed_m36) = 6,927; balanced (also observed at k=12, 24) = 6,918.

**Q1, the fade.** Balanced mean change_12 / 24 / 36 = −0.245 / −0.341 / −0.401 (≈ 61% of the 3-year decline by month 12). Median change_36 −0.38; **86.9% of games decline**. Rater-weighted change_36 = −0.274: big games decline less. Mean change_36 by entry year ranges −0.36 (2022–23) … −0.44 (2020–21).

**Background drift (control group).** Games ranked in 2016-10 with ≥ 500 raters and present in all 121 snapshots: **2,428 games**. Their mean average falls 6.741 → 6.675 over 10 years (≈ −0.007/yr, slowing after 2022). Over each main-sample game's own 36-month window the control drifts **−0.016** on average, so the control-adjusted change_36 is **−0.385**: ~96% of the fade is game-specific, not site-wide.

**Starting level ≫ hype.** change_36 by avg_m0 quintile: −0.13 / −0.29 / −0.41 / −0.49 / −0.68. Part of this is regression to the mean: entry averages rest on ~34 raters (median), so they're noisy.

**Q2, hype.** Quartile means of change_36 (Q1 → Q4): −0.365 / −0.397 / −0.434 / −0.409, not monotonic. Raw corr(hype_log, change_36) = 0.01. hype_log correlates with ln(raters_m0) (0.36) and avg_m0 (0.18). Quick OLS (HC1, entry-year FE):
- Spec A: change_36 ~ hype_log + avg_m0 + ln raters_m0 → hype **+0.049 (SE 0.008)**, avg_m0 −0.246 (0.008)
- Spec B: (avg_m36 − avg_m6) ~ hype_log + avg_m6 + ln raters_m6 → hype **−0.004 (0.013)**
- Spec C: reach ln(raters_m6) instead of hype → +0.049 (0.008)

So conditional on the starting average, more-hyped games decline slightly **less**, and after month 6 hype predicts nothing. H2 as stated looks unsupported. Report it straight.

**New raters vs displayed average (trap!).** Among rows with `new_avg_ok_3`, the equal-weight mean of `new_avg_3 − avg_rating` is −0.147 (k=3), −0.190 (6), −0.203 (12), −0.216 (24), −0.231 (36). New raters keep rating below the displayed average even at month 36, so the decline isn't finished. Δ-weighted: −0.06 … −0.16. ⚠️ A Δ-weighted mean of new_avg (≈ 7.5) vs an unweighted mean of avg_rating (≈ 7.2) wrongly suggests new raters rate *higher*: the weighting lets big, highly rated games dominate. Always compute the gap row-wise, then average.

**Q4, when to trust.** Share of games within ±0.25 of their month-36 average: k=0 31.5%, 1 35.7%, 2 40%, 3 43.9%, 6 55.4%, 9 66.6%, 12 77.2%, 15 85.6%, 18 91.2%, 24 97.1%. MAE: 0.469 (k0), 0.345 (3), 0.281 (6), 0.192 (12), 0.082 (24). Large-k agreement is partly mechanical (the running average is sticky).

**Extremes worth knowing (raters_m36 ≥ 2,000).** The biggest risers started very low, e.g. *Descent: Legends of the Dark* 4.18 → 7.96 and *Pandemic Legacy: Season 0* 5.05 → 8.44 (likely pre-release protest/low ratings). The biggest fallers started very high, e.g. *Challengers!* 9.31 → 7.08 and *Fireball Island* 8.95 → 6.93. Median rank change k0 → k36: −2,960 places, and 74% of games *improve* in rank despite falling averages. Rank is based on the Bayes average, which pulls games with few raters strongly toward a low prior; as raters accumulate that pull weakens. This is a nice aside for the write-up: the visible rank rises while the raw average falls.
