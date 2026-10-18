# Q4: when can you trust a new game's rating?

Rule: first month k where at least 80% of main-sample games have a displayed average within ±0.25 of their month-36 average: **month 13** (bootstrap 95% CI 13-14).

Caveat: agreement at large k is partly mechanical. The running average at k=24 already contains most of the raters that make up the month-36 average.

## Adjusted launch rating (train on entry years 2017-2019, test on 2020-2023)

Model: avg_m36 ~ avg_k + ln(raters_k) + ln(raters_k / raters_0 + 1) (growth term dropped at k=0, where it is constant).

| k | n_train | n_test | raw_mae | adj_mae | raw_within_0.25 | adj_within_0.25 | raw_within_0.5 | adj_within_0.5 |
|---|---|---|---|---|---|---|---|---|
| 0 | 3129 | 3798 | 0.476 | 0.289 | 0.306 | 0.554 | 0.614 | 0.848 |
| 3 | 3120 | 3790 | 0.356 | 0.220 | 0.407 | 0.691 | 0.794 | 0.924 |
| 6 | 3125 | 3789 | 0.291 | 0.186 | 0.532 | 0.767 | 0.882 | 0.951 |
| 12 | 3127 | 3793 | 0.198 | 0.132 | 0.765 | 0.878 | 0.957 | 0.978 |
