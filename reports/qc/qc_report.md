# QC report

- Run: 2026-10-18T15:37:02+08:00
- Config end_month: 2026-10-01
- Git commit: 542db23+uncommitted changes
- Summary: **36 PASS, 0 WARN, 0 FAIL** (7 report-only INFO rows)

## Results

| check_id | description | value | expected | status |
|---|---|---|---|---|
| 01 | Manifest covers every month start..end exactly once | 121 months, 0 missing | 121 months, 0 missing | PASS |
| 02 | Months where a truncated file was substituted | 2024-01,2024-09 | 2024-01,2024-09 | PASS |
| 02b | Months with no valid candidate (fallback) | 0 | 0 | PASS |
| 03 | Months whose accepted file has < min_row_ratio x previous month rows | 0 | 0 | PASS |
| 04 | Duplicate (snap_date, game_id) pairs after dedup | 0 | 0 | PASS |
| 05 | Duplicate rows removed in load (files affected in expected) | 721 rows in 16 files | report (pilot: 721 in 16 files) | INFO |
| 06a | avg_rating outside valid range | 0 | 0 | PASS |
| 06b | n_raters below 30 (BGG ranking threshold) | 0 | 0 | PASS |
| 06c | NULL game_id / avg_rating / n_raters | 0 | 0 | PASS |
| 07 | Publication year at entry: unknown (0) / junk (cleaned to NULL) / changes over time | 394 / 6 / 1593 | report (pilot: 432 zero ever, 1,592 changing) | INFO |
| 08.2017 | New releases entering in 2017 | 1033 | 1033 | PASS |
| 08.2018 | New releases entering in 2018 | 1045 | 1045 | PASS |
| 08.2019 | New releases entering in 2019 | 1068 | 1068 | PASS |
| 08.2020 | New releases entering in 2020 | 921 | 921 | PASS |
| 08.2021 | New releases entering in 2021 | 977 | 977 | PASS |
| 08.2022 | New releases entering in 2022 | 1055 | 1055 | PASS |
| 08.2023 | New releases entering in 2023 | 1213 | 1213 | PASS |
| 09.2017 | Cohort observed at month 36, entry 2017 | 1028 | >= 1028 | PASS |
| 09.2018 | Cohort observed at month 36, entry 2018 | 1039 | >= 1039 | PASS |
| 09.2019 | Cohort observed at month 36, entry 2019 | 1062 | >= 1062 | PASS |
| 09.2020 | Cohort observed at month 36, entry 2020 | 910 | >= 910 | PASS |
| 09.2021 | Cohort observed at month 36, entry 2021 | 972 | >= 965 | PASS |
| 09.2022 | Cohort observed at month 36, entry 2022 | 1047 | >= 1047 | PASS |
| 10 | New releases with a missing month in k=0..36 (of which internal gap / dropped out) | 286 (208 / 79) | < 442 | PASS |
| 11 | One-month steps where n_raters decreased (deleted ratings) | 4766 of 324733 (1.47%) | report (pilot ~1.5%) | INFO |
| 11b | One-month steps with unchanged n_raters | 45387 of 324733 (14.0%) | report (pilot ~14%) | INFO |
| 12 | Usable new_avg share by k (% ok: 1-month / 3-month window) | k1: 44.0 / -; k3: 37.2 / 69.4; k6: 33.5 / 63.0; k12: 33.4 / 59.2; k24: 26.8 / 52.4; k36: 14.1 / 48.6 | report (table below) | INFO |
| 13 | new_avg outside valid range: all / among err <= max_error_bound (1-month window) | 3443 of 274580 / 1260 | report (pilot: 3,439 / 1,255) | INFO |
| 13b | new_avg outside valid range: all / among err <= max_error_bound (3-month window) | 2506 of 288675 / 1452 | report | INFO |
| 14 | Panel unique on (game_id, k); k in 0..max_k; every game has k=0; d_rating=0 at k=0 | dup=0, no_k0=0, bad_d0=0, bad_k=0 | all 0 | PASS |
| 15.12 | Mean d_rating at k=12 (all new releases) | -0.237 | -0.238 +/- 0.03 | PASS |
| 15.24 | Mean d_rating at k=24 (all new releases) | -0.332 | -0.332 +/- 0.03 | PASS |
| 15.36 | Mean d_rating at k=36 (all new releases) | -0.401 | -0.4 +/- 0.03 | PASS |
| 16.174430 | Spot check: Gloomhaven | match | match | PASS |
| 16.224517 | Spot check: Brass: Birmingham | match | match | PASS |
| 16.233078 | Spot check: Twilight Imperium (4th Ed.) | match | match | PASS |
| 16.266192 | Spot check: Wingspan | match | match | PASS |
| 16.291457 | Spot check: Gloomhaven: Jaws of the Lion | match | match | PASS |
| 16.295770 | Spot check: Frosthaven | match | match | PASS |
| 16.295947 | Spot check: Cascadia | match | match | PASS |
| 16.312484 | Spot check: Lost Ruins of Arnak | match | match | PASS |
| 16.316554 | Spot check: Dune: Imperium | match | match | PASS |
| 16.342942 | Spot check: Ark Nova | match | match | PASS |

## Substituted months (check 02)

| month | chosen_date | status | rows | rejected |
|---|---|---|---|---|
| 2024-01-01 | 2024-01-05 | substituted | 25646 | 2024-01-01:22100;2024-01-02:22800;2024-01-03:23800;2024-01-04:24800 |
| 2024-09-01 | 2024-09-03 | substituted | 26940 | 2024-09-01:22300;2024-09-02:22500 |

## New releases with a missing month, by entry year (check 10)

`with_internal_gap`: a month is absent but later months exist (the game fell out of the ranking and came back, or a snapshot lacked it). `dropped_out_early`: ranking history ends before the end of follow-up.

| entry_year | new_releases | with_missing_month | with_internal_gap | dropped_out_early |
|---|---|---|---|---|
| 2016 | 240 | 4 | 2 | 2 |
| 2017 | 1033 | 11 | 6 | 5 |
| 2018 | 1045 | 15 | 9 | 6 |
| 2019 | 1068 | 20 | 14 | 6 |
| 2020 | 921 | 20 | 9 | 11 |
| 2021 | 977 | 12 | 7 | 5 |
| 2022 | 1055 | 26 | 19 | 8 |
| 2023 | 1213 | 52 | 38 | 14 |
| 2024 | 1235 | 57 | 47 | 10 |
| 2025 | 1267 | 47 | 36 | 11 |
| 2026 | 966 | 22 | 21 | 1 |

## Share of usable new_avg by months since entry (check 12)

Among panel rows whose lagged month is observed. Usable = delta raters >= threshold AND rounding-error bound <= threshold AND value in the valid range.

| k | rows_w1 | pct_ok_w1 | rows_w3 | pct_ok_w3 |
|---|---|---|---|---|
| 1 | 10861 | 44.0 | 0 | - |
| 3 | 10619 | 37.2 | 10639 | 69.4 |
| 6 | 10344 | 33.5 | 10337 | 63.0 |
| 12 | 9644 | 33.4 | 9642 | 59.2 |
| 24 | 8396 | 26.8 | 8390 | 52.4 |
| 36 | 7160 | 14.1 | 7163 | 48.6 |

## Spot-check games (check 16)

| id | name | entry_month | pub_year_at_entry | is_new_release | avg_k0 | raters_k0 | raters_k6 | avg_k12 | avg_k36 | raters_k36 | mismatches |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 174430 | Gloomhaven | 2016-10-01 | 2016 | False | 8.67 | 58 | 2516 | 9.01 | 8.87 | 28171 |  |
| 224517 | Brass: Birmingham | 2017-12-01 | 2018 | True | 8.73 | 33 | 65 | 8.67 | 8.65 | 17047 |  |
| 233078 | Twilight Imperium (4th Ed.) | 2017-09-01 | 2017 | True | 8.77 | 82 | 2098 | 8.8 | 8.69 | 11607 |  |
| 266192 | Wingspan | 2019-01-01 | 2019 | True | 8.08 | 32 | 9083 | 8.09 | 8.1 | 55431 |  |
| 291457 | Gloomhaven: Jaws of the Lion | 2020-07-01 | 2020 | True | 9.22 | 438 | 5822 | 8.78 | 8.5 | 29202 |  |
| 295770 | Frosthaven | 2020-01-01 | 2021 | True | 7.09 | 48 | 305 | 7.18 | 7.75 | 1052 |  |
| 295947 | Cascadia | 2020-10-01 | 2021 | True | 7.95 | 66 | 228 | 8.09 | 7.97 | 29574 |  |
| 312484 | Lost Ruins of Arnak | 2020-10-01 | 2020 | True | 8.16 | 39 | 3665 | 8.11 | 8.08 | 37788 |  |
| 316554 | Dune: Imperium | 2020-12-01 | 2020 | True | 8.04 | 71 | 4877 | 8.31 | 8.42 | 39421 |  |
| 342942 | Ark Nova | 2021-11-01 | 2021 | True | 8.5 | 252 | 6383 | 8.6 | 8.53 | 46693 |  |
