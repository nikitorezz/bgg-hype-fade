# Q2: does hype predict the fade?

OLS, HC1 robust SEs, entry-year fixed effects, main sample. Cell = coefficient (SE); stars: * p<.05, ** p<.01, *** p<.001. H2 predicts a **negative** hype coefficient.

|  | A | B | C | D |
|---|---|---|---|---|
| Intercept | +1.142 (0.068)*** | +0.532 (0.054)*** | +1.140 (0.068)*** | -0.426 (0.015)*** |
| avg_m0 | -0.246 (0.008)*** |  | -0.246 (0.008)*** |  |
| avg_m6 |  | -0.141 (0.007)*** |  |  |
| hype_log | +0.049 (0.008)*** | -0.004 (0.013) |  | +0.006 (0.008) |
| log_reach |  |  | +0.049 (0.008)*** |  |
| np.log(raters_m0) | +0.046 (0.015)** |  | -0.002 (0.020) |  |
| np.log(raters_m6) |  | +0.048 (0.010)*** |  |  |
| N | 6,914 | 6,914 | 6,914 | 6,914 |
| R2 | 0.218 | 0.150 | 0.218 | 0.005 |

## Hype coefficient per 1 SD of the exposure

| spec | coef | se | p | coef_per_sd | se_per_sd | n |
|---|---|---|---|---|---|---|
| A | 0.049 | 0.008 | 0.000 | 0.037 | 0.006 | 6914 |
| B | -0.004 | 0.013 | 0.735 | -0.003 | 0.010 | 6914 |
| C | 0.049 | 0.008 | 0.000 | 0.047 | 0.008 | 6914 |
| D | 0.006 | 0.008 | 0.445 | 0.005 | 0.006 | 6914 |

## Sign and significance

- Spec A (as proposed: change_36 on hype, controlling start level and size): hype coefficient +0.049 (SE 0.008), positive, significant at 5%. H2 predicts a negative sign.
- Spec B (clean timing: change after the hype window (avg_m36 - avg_m6)): hype coefficient -0.004 (SE 0.013), negative, not significant at 5%. H2 predicts a negative sign.
- Spec C (absolute reach ln(raters_m6) instead of relative growth): hype coefficient +0.049 (SE 0.008), positive, significant at 5%. H2 predicts a negative sign.
- Spec D (no controls (entry-year FE only)): hype coefficient +0.006 (SE 0.008), positive, not significant at 5%. H2 predicts a negative sign.

## Quartile means of change_36 (from segments.csv)

| segment_value | mean | ci_low | ci_high | n |
|---|---|---|---|---|
| Q1 | -0.365 | -0.389 | -0.341 | 1731 |
| Q2 | -0.397 | -0.416 | -0.377 | 1730 |
| Q3 | -0.434 | -0.453 | -0.416 | 1719 |
| Q4 | -0.409 | -0.430 | -0.388 | 1734 |
