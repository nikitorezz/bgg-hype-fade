# Data notes

A reference for the data behind this project: what the source looks like, the quality problems it has and how the pipeline handles them, how the sample is built, and how the derived metrics are defined. Read it before changing the SQL. Thresholds live in [`config.yaml`](../config.yaml); results are in [`findings.md`](findings.md).

---

## 1. Source

[beefsack/bgg-ranking-historicals](https://github.com/beefsack/bgg-ranking-historicals) stores BoardGameGeek's full ranked list once a day as `YYYY-MM-DD.csv` files in a flat repository (branch `master`).

- The archive starts on **2016-10-12** and gains one file per day. One day is missing (2019-10-24).
- Files grow from about 12,800 games (2016) to 31,400 (2026).
- The project uses one file per month, **October 2016 to October 2026 (121 files, 2,611,791 rows, 541 MB)**. The end month is fixed in the config so results are reproducible.
- The repository has **no licence file**, so no reuse rights are granted. Raw and processed data are not redistributed; see §8.

## 2. Schema

The header is identical in every file:

```
ID,Name,Year,Rank,Average,Bayes average,Users rated,URL,Thumbnail
```

| Column | Used as | Notes |
|---|---|---|
| `ID` | `game_id` | BGG game id; the join key |
| `Name` | `name` | Can contain commas and quotes; names change over time, so the latest name is used for display |
| `Year` | `pub_year` | Publication year. `0` means unknown; a few placeholders (2200–3500) are junk. Changes over time for about 1,600 games |
| `Rank` | `rank` | BGG rank on that day; not strictly unique within a file |
| `Average` | `avg_rating` | **Raw mean rating, published with two decimals.** The outcome variable |
| `Bayes average` | `bayes_avg` | BGG's shrunk average used for the rank; not used as the outcome |
| `Users rated` | `n_raters` | Number of ratings; **always at least 30**, BGG's ranking threshold |
| `URL`, `Thumbnail` | dropped | The URL is derivable from the id |

## 3. Data-quality issues and how they are handled

**Truncated snapshots.** Some daily files are partial scrapes, often stopping at a round row count. Two first-of-month files are affected:

| Month | Day-1 rows | Previous month | Replacement |
|---|---|---|---|
| January 2024 | 22,100 | 25,488 | 5 January (25,646 rows) |
| September 2024 | 22,300 | 26,731 | 3 September (26,940 rows) |

*Rule:* in each month, take the earliest file (days 1–10) with at least 99% of the previous month's rows; rejected candidates are logged in `data/raw/manifest.csv`. Without this rule, thousands of games appear to drop out for a month and follow-up counts are understated. Two other truncated files (2023-12-31 and 2024-08-31) are not first-of-month files, but any daily-data extension must apply the same check.

**Duplicate rows.** 721 (date, game) pairs appear twice in the same file, across 16 files, because ranks shift while the list is scraped page by page. Most pairs are identical. *Rule:* keep one row per (date, game), preferring more raters, then the better rank.

**CSV quoting.** DuckDB's dialect detection fails on names such as `"""Tarleton's Quarter!"""`. The loader sets the dialect explicitly (comma delimiter, `"` as quote and escape, no auto-detection).

**Publication years.** `Year = 0` (unknown) and placeholder years are treated as missing; *Knucklebones* (`Year = 3000`, entered 2021) would otherwise count as a 2021 release. Because the year changes over time for some games, the year **at the game's first appearance** is used.

**Falling rater counts.** `Users rated` decreases from one month to the next in 1.5% of steps (deleted ratings) and is unchanged in 14%. Steps with a decrease get no new-rater average.

**Gaps.** 286 new releases miss at least one month within their first 36 (208 with an internal gap, 79 that left the ranking early). Missing months are not interpolated, and lagged values are only computed across exactly consecutive months.

**Non-unique ranks.** Ranks are not strictly unique within a file (for example 31,394 rows but 31,355 distinct ranks on 2026-10-01). Rank is used only descriptively.

## 4. Sample construction

- **Entry month:** the first monthly snapshot in which a game appears.
- **Left-censoring:** games already present in the first snapshot (October 2016) are excluded, because their launch was not observed.
- **New release:** publication year at entry is known and no earlier than the year before entry. Pre-release entries are kept (for example *Frosthaven* entered in January 2020 with publication year 2021, rated by crowdfunding backers).
- **Main sample:** new releases entering January 2017 to October 2023 (so 36 months of follow-up are possible) and still ranked at month 36.
- **Balanced sample:** the main sample also observed at months 12 and 24; used where months 12, 24 and 36 are compared.

| Step | Games |
|---|---|
| All games ever ranked | 31,676 |
| Not already ranked in October 2016 | 18,917 |
| With a usable publication year | 18,629 |
| New releases | 11,020 |
| Launched January 2017 – October 2023 | 6,980 |
| Still ranked at month 36 (main sample) | 6,927 |

New releases by launch year, and how many are observed at months 12, 24 and 36:

| Launch year | New releases | Month 12 | Month 24 | Month 36 |
|---|---|---|---|---|
| 2016 (Nov–Dec) | 240 | 238 | 238 | 238 |
| 2017 | 1,033 | 1,030 | 1,028 | 1,028 |
| 2018 | 1,045 | 1,040 | 1,039 | 1,039 |
| 2019 | 1,068 | 1,064 | 1,064 | 1,062 |
| 2020 | 921 | 915 | 912 | 910 |
| 2021 | 977 | 974 | 974 | 972 |
| 2022 | 1,055 | 1,046 | 1,047 | 1,047 |
| 2023 | 1,213 | 1,205 | 1,202 | 869 |
| 2024 | 1,235 | 1,227 | 894 | – |
| 2025 | 1,267 | 912 | – | – |
| 2026 (to Oct) | 966 | – | – | – |

Most games enter just above the 30-rater threshold (10th percentile 30 raters, median 34, 90th percentile 64). 2023 has fewer month-36 observations because only games entering by October 2023 can reach month 36 by October 2026.

## 5. Derived metrics

**Change since entry.** `d_rating = avg_rating(k) − avg_rating(0)`, where `k` is months since entry.

**New-rater average.** From two running averages `w` months apart (the main analysis uses `w = 3`), the average of just the ratings added in between:

```
new_avg = (avg_t · n_t − avg_s · n_s) / (n_t − n_s)        s = t − w
```

Because `Average` is rounded to ±0.005, the worst-case error is `0.005 · (n_t + n_s) / (n_t − n_s)`. For a game with 60,000 raters gaining 100 ratings, that is about ±6 points, which a simple minimum on new ratings would not catch. A value is **usable** only when at least 10 ratings were added, the error bound is at most 0.5 points, and the result lies between 1 and 10. The usable share falls with age (3-month window: 69% at month 3, 59% at month 12, 49% at month 36), and usable values over-represent fast-growing games.

**Hype.** `hype = ln(raters at month 6 + 1) − ln(raters at entry + 1)`, the growth in raters over the first six months. Quartiles are assigned within each launch year.

**Control group.** 2,428 established games: already ranked in October 2016 with at least 500 raters and present in all 121 snapshots. For each new release, the control group's change over the same 36 calendar months is subtracted to remove site-wide drift (on average −0.016).

**Trust month.** The first month at which at least 80% of main-sample games are within ±0.25 of their month-36 rating. The tolerance and share are configurable, and the dashboard lets readers change them.

## 6. Analysis traps

- **Weighting the gap.** Compute `new_avg − avg_rating` row by row, then average with equal weight. Comparing a rater-weighted mean of `new_avg` (about 7.5) with an unweighted mean of `avg_rating` (about 7.2) wrongly suggests that new raters rate *higher*, because weighting lets big, highly rated games dominate.
- **Age, period and cohort.** With game fixed effects and months-since-entry dummies, calendar-month fixed effects are perfectly collinear. Site-wide drift is handled with the control group instead.
- **Mechanical agreement.** The running average at month 24 already contains most of month 36's ratings, so agreement at late months partly reflects overlap, not settled opinion.
- **Regression to the mean.** Launch averages rest on few ratings, so high starters fall further partly by chance. Specification B (change after month 6, controlling for the month-6 rating) reduces this.

## 7. Reference values

Mean change from entry for all 11,020 new releases (unbalanced): −0.046 at month 1, −0.160 at month 6, −0.237 at month 12, −0.332 at month 24 and −0.401 at month 36.

Spot-check games, verified by the quality checks:

| ID | Game | Entry | Publication year | New release | Rating at entry | Raters at entry | Raters at month 6 | Rating at month 12 | Rating at month 36 | Raters at month 36 |
|---|---|---|---|---|---|---|---|---|---|---|
| 174430 | Gloomhaven | 2016-10 | 2016 | no (already ranked) | 8.67 | 58 | 2,516 | 9.01 | 8.87 | 28,171 |
| 233078 | Twilight Imperium (4th Ed.) | 2017-09 | 2017 | yes | 8.77 | 82 | 2,098 | 8.80 | 8.69 | 11,607 |
| 224517 | Brass: Birmingham | 2017-12 | 2018 | yes | 8.73 | 33 | 65 | 8.67 | 8.65 | 17,047 |
| 266192 | Wingspan | 2019-01 | 2019 | yes | 8.08 | 32 | 9,083 | 8.09 | 8.10 | 55,431 |
| 295770 | Frosthaven | 2020-01 | 2021 | yes | 7.09 | 48 | 305 | 7.18 | 7.75 | 1,052 |
| 291457 | Gloomhaven: Jaws of the Lion | 2020-07 | 2020 | yes | 9.22 | 438 | 5,822 | 8.78 | 8.50 | 29,202 |
| 312484 | Lost Ruins of Arnak | 2020-10 | 2020 | yes | 8.16 | 39 | 3,665 | 8.11 | 8.08 | 37,788 |
| 295947 | Cascadia | 2020-10 | 2021 | yes | 7.95 | 66 | 228 | 8.09 | 7.97 | 29,574 |
| 316554 | Dune: Imperium | 2020-12 | 2020 | yes | 8.04 | 71 | 4,877 | 8.31 | 8.42 | 39,421 |
| 342942 | Ark Nova | 2021-11 | 2021 | yes | 8.50 | 252 | 6,383 | 8.60 | 8.53 | 46,693 |

Not every hit declines: *Dune: Imperium* and *Frosthaven* rose.

## 8. Licence and publication

- The source archive has no licence file, so the raw and processed snapshot files are never committed or published; the pipeline downloads the data itself.
- The dashboard's game lookup publishes a compact derived extract (`app/data/*.parquet`: rating, rank and rater count per game and month, plus derived fields). These are facts BoardGameGeek shows publicly on every game page, with no user-level data. The author chose to publish them without a licence from the archive owner, so this is a documented risk decision, not a granted permission. The extract is easy to remove (`bgg dashboard-data --aggregates-only`) if the archive owner or BoardGameGeek objects.
- The Kickstarter flag is not part of the published per-game files; only group averages derived from it appear.
- Metadata for the crowdfunding comparison comes from "Board Game Database from BoardGameGeek" (threnjen, Kaggle, CC BY-SA 3.0), a January 2022 snapshot that is downloaded manually and not redistributed; only group averages derived from it are published.
- Data © BoardGameGeek. This project is not affiliated with BoardGameGeek.
