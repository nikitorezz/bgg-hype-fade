# Q3: crowdfunded launches (optional)

Source: Kaggle *Board Game Database from BoardGameGeek* (threnjen, CC BY-SA 3.0), a January 2022 snapshot, so only entry years with at least 50% coverage are modelled: [2017, 2018, 2019, 2020, 2021]. The `Kickstarted` flag is the dataset's own binary variable, taken as given (as of 2022, not at launch).

## Coverage of the main sample

| entry_year | n_main_sample | n_matched | n_kickstarted | coverage | share_kickstarted_of_matched | modelled |
|---|---|---|---|---|---|---|
| 2017 | 1028 | 1028 | 329 | 1.000 | 0.320 | True |
| 2018 | 1039 | 1038 | 331 | 0.999 | 0.319 | True |
| 2019 | 1062 | 1053 | 334 | 0.992 | 0.317 | True |
| 2020 | 910 | 882 | 279 | 0.969 | 0.316 | True |
| 2021 | 972 | 909 | 279 | 0.935 | 0.307 | True |
| 2022 | 1047 | 31 | 8 | 0.030 | 0.258 | False |
| 2023 | 869 | 0 | 0 | 0.000 | - | False |

## Mean change_36 by flag (covered games, modelled years)

| kickstarted | mean | se | ci_low | ci_high | n |
|---|---|---|---|---|---|
| 0 | -0.361 | 0.007 | -0.374 | -0.348 | 3355 |
| 1 | -0.535 | 0.012 | -0.559 | -0.511 | 1547 |

## Regressions (change_36, HC1 SEs, entry-year FE)

| model | term | coef | se | p | n | r2 |
|---|---|---|---|---|---|---|
| A (baseline) | Intercept | 1.177 | 0.081 | 0.000 | 4902 | 0.222 |
| A (baseline) | hype_log | 0.055 | 0.010 | 0.000 | 4902 | 0.222 |
| A (baseline) | avg_m0 | -0.242 | 0.010 | 0.000 | 4902 | 0.222 |
| A (baseline) | ln_raters_m0 | 0.028 | 0.016 | 0.086 | 4902 | 0.222 |
| A + kickstarted | Intercept | 1.122 | 0.081 | 0.000 | 4902 | 0.229 |
| A + kickstarted | hype_log | 0.049 | 0.010 | 0.000 | 4902 | 0.229 |
| A + kickstarted | kickstarted | -0.079 | 0.013 | 0.000 | 4902 | 0.229 |
| A + kickstarted | avg_m0 | -0.232 | 0.011 | 0.000 | 4902 | 0.229 |
| A + kickstarted | ln_raters_m0 | 0.031 | 0.016 | 0.062 | 4902 | 0.229 |
| A + kickstarted x hype | Intercept | 1.122 | 0.081 | 0.000 | 4902 | 0.229 |
| A + kickstarted x hype | hype_log | 0.047 | 0.011 | 0.000 | 4902 | 0.229 |
| A + kickstarted x hype | kickstarted | -0.083 | 0.022 | 0.000 | 4902 | 0.229 |
| A + kickstarted x hype | hype_log:kickstarted | 0.005 | 0.019 | 0.802 | 4902 | 0.229 |
| A + kickstarted x hype | avg_m0 | -0.232 | 0.011 | 0.000 | 4902 | 0.229 |
| A + kickstarted x hype | ln_raters_m0 | 0.031 | 0.016 | 0.057 | 4902 | 0.229 |
