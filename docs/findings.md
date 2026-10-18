# Findings and analysis review

*Review of the task 02 outputs (commit 5faf5e1, run 2026-10-18). Numbers come from `reports/results/key_numbers.json` unless marked **[review check]**. Those were computed during this review from `data/processed/*.parquet` and the Kaggle file, and should be added to key_numbers in task 03.*

---

## 1. Validation verdict: **pass**

- All 20 pre-registered sanity values reproduced within tolerance (`sanity_checks.csv`).
- The event study matches the balanced descriptive means exactly (β12 −0.244, β36 −0.401), as it should with game FE on a near-balanced panel.
- The robustness grid tells one consistent story: the fade is −0.27 to −0.41 at 36 months in every variant, ~54–66% of it by month 12, and no variant yields a significantly negative hype coefficient.
- The figures plot the right quantities, the gap is computed row-wise (the weighting trap was avoided), and the examples were chosen by rule.
- Methodological choices that held up: the clean-timing Spec B, the mature control group (instead of collinear calendar FE), and the out-of-sample split for the adjusted predictor.

Minor issues (cosmetic, fixed in task 03): descriptive rather than "action" figure titles; non-sequential colours for ordered quartiles (Fig 6); different y-scales in Fig 3's two panels; a too-wide histogram range in Fig 4.

## 2. What the data says

**F1. Launch ratings are inflated, and the correction is slow.** The average new game's displayed rating falls **0.40 points over 3 years** (95% CI 0.39–0.41). **61%** of that happens in year 1. **87%** of games decline. Only ~0.016 of it is site-wide drift, so ~96% is specific to new games (control-adjusted −0.385).

**F2. The fade isn't over at 3 years.** New raters score games **0.15 below the displayed average at month 3 and 0.23 below at month 36**. The running average is still catching up to current opinion. The sign holds under all 9 threshold combinations (−0.13 … −0.26).

**F3. Hype doesn't predict how far a game falls (H2 not supported).** Raw correlation is 0.01. Conditional on the starting rating, more-hyped games fall *slightly less* (+0.049 per log-unit, about +0.04 per SD). After the hype window (Spec B), hype predicts nothing (−0.004, SE 0.013).

**F4. …but hype predicts how *fast* it falls.** **[review check]** Mean change by month 6: Q1 −0.10, Q2 −0.16, Q3 −0.21, Q4 −0.19. By month 36 they're close: −0.37 / −0.40 / −0.43 / −0.41. Mechanism: the displayed rating is a running average. Hyped games gain ~7× their entry raters by month 6 (Q1: ~1.2×), so the enthusiastic entry ratings are diluted quickly. Low-hype games at month 36 still have about half their ratings from the entry batch (median 34 → 69 raters), and new raters score them ~0.30 below displayed. *Hype changes the speed of the correction, not its size, and the slow movers aren't finished.*

**F5. Where a game starts matters most.** Change by entry-rating decile: from −0.05 (lowest, mean 5.8) to −0.76 (highest, mean 8.8). Part of this is regression to the mean (entry averages rest on a median of 34 raters), and part is self-selection: games that launch high have the most enthusiastic early audience. These can't be fully separated with this data. Say so.

**F6. Big games fade less.** Rater-weighted change −0.27. Top 10% by popularity −0.29 vs rest −0.41.

**F7. Crowdfunded games fade more (descriptive).** Among 2017–2021 entries matched to the Kaggle data (93–100% coverage), "Kickstarted" games fall −0.54 vs −0.36. **[review check]** They start higher (7.62 vs 7.23). Even within the same starting-rating band they fall 0.05–0.16 more. The regression gap is −0.079 (CI −0.10 to −0.05), with no hype interaction. Caveat: the flag covers ~31% of games and is likely broader than "launched via Kickstarter".

**F8. When to trust a rating: around month 13.** That's the first month when ≥ 80% of games are within ±0.25 of their 3-year rating (CI 13–14); at entry it's 31%. A simple **adjusted launch rating** (trained on 2017–19, tested on 2020–23) raises that from 31% to 55% at entry (MAE 0.48 → 0.29) and from 77% to 88% at month 12. It works mostly by shrinking toward the mean (coefficient 0.77 on the displayed rating at entry).

**F9. The rank paradox.** **[review check]** 74% of games improve in rank by month 36 while their raw average falls. BGG's rank uses a Bayes average that pulls low-rater games toward a low prior, so accumulating raters lifts the rank. A casual user sees the "proof" of quality (rank) rise while actual opinion falls.

## 3. The story (for write-up, dashboard and interviews)

> **Launch ratings oversell. On BoardGameGeek the typical new game loses 0.4 points over three years, most of it in year one, and new raters still rate it lower at the end. Hype doesn't decide how far a game falls; it decides how fast the number catches up. A platform could fix most of this with an "adjusted launch rating" or a "new release" badge for the first ~13 months.**

Business translation (the analytics-role angle): this is the same problem as app-store, e-commerce or streaming launch ratings. Cohort the products by launch, separate new feedback from the running average, and measure when the metric becomes trustworthy.

## 4. Caveats to state plainly

1. The ranking requires 30 raters, so the earliest ratings are bundled into month 0. We measure change after entry, not from the first rating.
2. Observational data, so no causal claims. "Hype" (rater growth) also reflects print run, distribution and price.
3. Regression to the mean vs self-selection can't be separated cleanly (F5).
4. The new-rating average is approximate (2-decimal rounding, rating edits) and is available for ~50–70% of game-months. Usable rows over-represent fast-growing games.
5. One platform of enthusiasts. The Kickstarted flag comes from a 2022 snapshot and may be broad.
6. Not done: the daily-vs-monthly snapshot robustness check.

## 5. Items for task 03

- Add review-check numbers to key_numbers: change_6 by hype quartile; raters growth ratio m0→m6 by quartile; share of entry raters remaining at m36 by quartile; gap at k=36 by quartile; Kickstarted starting average + within-band comparison; share of games improving rank.
- New figures: Fig 9 "speed, not size" and Fig 10 "Kickstarter within starting bands".
- Figure polish (action titles etc.).
- Then build the dashboard.
