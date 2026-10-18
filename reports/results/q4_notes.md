# Q4: when can you trust a new game's rating?

Rule: first month k where at least 80% of main-sample games have a displayed average within ±0.25 of their month-36 average: **month 13** (bootstrap 95% CI 13-14).

Caveat: agreement at large k is partly mechanical. The running average at k=24 already contains most of the raters that make up the month-36 average.

## Adjusted launch rating (train on entry years 2017-2019, test on 2020-2023)

Model: avg_m36 ~ avg_k + ln(raters_k) + ln(raters_k / raters_0 + 1) (growth term dropped at k=0, where it is constant).

| k | n_train | n_test | raw_mae | adj_mae | raw_within_0.1 | adj_within_0.1 | raw_within_0.15 | adj_within_0.15 | raw_within_0.2 | adj_within_0.2 | raw_within_0.25 | adj_within_0.25 | raw_within_0.3 | adj_within_0.3 | raw_within_0.35 | adj_within_0.35 | raw_within_0.4 | adj_within_0.4 | raw_within_0.45 | adj_within_0.45 | raw_within_0.5 | adj_within_0.5 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 3129 | 3798 | 0.476 | 0.289 | 0.121 | 0.252 | 0.177 | 0.357 | 0.236 | 0.456 | 0.306 | 0.554 | 0.367 | 0.630 | 0.426 | 0.695 | 0.483 | 0.758 | 0.548 | 0.808 | 0.614 | 0.848 |
| 3 | 3120 | 3790 | 0.356 | 0.220 | 0.143 | 0.331 | 0.223 | 0.474 | 0.300 | 0.595 | 0.407 | 0.691 | 0.498 | 0.768 | 0.584 | 0.826 | 0.661 | 0.864 | 0.725 | 0.900 | 0.794 | 0.924 |
| 6 | 3125 | 3789 | 0.291 | 0.186 | 0.183 | 0.396 | 0.285 | 0.552 | 0.391 | 0.673 | 0.532 | 0.767 | 0.628 | 0.832 | 0.718 | 0.880 | 0.784 | 0.912 | 0.837 | 0.935 | 0.882 | 0.951 |
| 12 | 3127 | 3793 | 0.198 | 0.132 | 0.296 | 0.551 | 0.463 | 0.717 | 0.619 | 0.814 | 0.765 | 0.878 | 0.840 | 0.921 | 0.888 | 0.951 | 0.922 | 0.963 | 0.940 | 0.972 | 0.957 | 0.978 |
