# Event study notes

Model: avg_rating_it = alpha_i + sum_k beta_k * 1[k_it = k] + e_it, k = 1..36, month 0 omitted. `linearmodels.PanelOLS` with game fixed effects, SEs clustered by game, on the main sample panel (6,927 games, 256,022 rows).

No calendar-month fixed effects: with game FE and age dummies, calendar month = entry month + age is perfectly collinear (age-period-cohort problem). Background drift is handled by the control-adjusted variant in the robustness grid.

| k | beta | se | ci_low | ci_high |
|---|---|---|---|---|
| 12 | -0.244 | 0.004 | -0.252 | -0.236 |
| 24 | -0.341 | 0.005 | -0.350 | -0.331 |
| 36 | -0.401 | 0.005 | -0.412 | -0.391 |
