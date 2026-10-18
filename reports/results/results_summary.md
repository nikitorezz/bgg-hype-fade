# Results summary (auto-generated, facts only)

Source of truth: `reports/results/key_numbers.json`. Every number below comes from it.

## Headline numbers

| Quantity | Value [95% CI] | n |
|---|---|---|
| Main sample (games) | 6,927 | 6927 |
| Balanced sample (games) | 6,918 | 6918 |
| Mean change in rating, entry to month 12 | -0.245 [-0.253, -0.236] | 6918 |
| ... to month 24 | -0.341 [-0.351, -0.331] | 6918 |
| ... to month 36 | -0.401 [-0.412, -0.391] | 6918 |
| Share of 36-month decline reached by month 12 | 0.609 [0.600, 0.620] | 6918 |
| Median change to month 36 | -0.380 | 6927 |
| Share of games declining | 0.869 [0.861, 0.877] | 6927 |
| Rater-weighted change to month 36 | -0.274 | 6927 |
| Mature-control drift over 36 months | -0.016 | 6927 |
| Control-adjusted change to month 36 | -0.385 [-0.396, -0.375] | 6927 |
| New raters minus displayed, month 3 | -0.147 [-0.157, -0.137] | 4829 |
| ... month 12 | -0.203 [-0.214, -0.192] | 4110 |
| ... month 36 | -0.231 [-0.244, -0.218] | 3365 |
| Event study beta, month 12 | -0.244 [-0.252, -0.236] | 6927 |
| Event study beta, month 36 | -0.401 [-0.412, -0.391] | 6927 |
| Q2 Spec A hype coefficient (H2: negative) | 0.049 [0.033, 0.066] | 6914 |
| Q2 Spec B hype coefficient (H2: negative) | -0.004 [-0.030, 0.021] | 6914 |
| Q2 Spec C reach coefficient | 0.049 [0.032, 0.065] | 6914 |
| Q2 Spec D, no controls | 0.006 [-0.010, 0.022] | 6914 |
| First month with >=80% of games within ±0.25 of month-36 rating | 13 [13.000, 14.000] | 6927 |
| Share within ±0.25 of final, at entry | 0.315 [0.304, 0.326] | 6927 |
| ... month 6 | 0.554 [0.542, 0.565] | 6914 |
| ... month 12 | 0.772 [0.762, 0.782] | 6920 |
| Test set, raw entry rating within ±0.25 | 0.306 | 3798 |
| Test set, adjusted entry rating within ±0.25 | 0.554 | 3798 |

Q3 (crowdfunding): ran on entry years [2017, 2018, 2019, 2020, 2021]

Not done: daily-vs-monthly snapshot robustness (needs a multi-GB download).

## Comparison with data_notes section 11 sanity values

| key | expected | actual | diff | tolerance | status |
|---|---|---|---|---|---|
| n_main_sample | 6927.000 | 6927.000 | 0.000 | 0.000 | OK |
| n_balanced_sample | 6918.000 | 6918.000 | 0.000 | 0.000 | OK |
| n_control_games | 2428.000 | 2428.000 | 0.000 | 0.000 | OK |
| change_12 | -0.245 | -0.245 | 0.001 | 0.010 | OK |
| change_24 | -0.341 | -0.341 | 0.000 | 0.010 | OK |
| change_36 | -0.401 | -0.401 | -0.000 | 0.010 | OK |
| median_change_36 | -0.380 | -0.380 | 0.000 | 0.010 | OK |
| share_declining | 0.869 | 0.869 | 0.000 | 0.010 | OK |
| control_drift_36 | -0.016 | -0.016 | 0.000 | 0.010 | OK |
| change_36_control_adjusted | -0.385 | -0.385 | -0.000 | 0.010 | OK |
| change_36_rater_weighted | -0.274 | -0.274 | 0.000 | 0.010 | OK |
| gap_k3 | -0.150 | -0.147 | 0.003 | 0.010 | OK |
| gap_k12 | -0.200 | -0.203 | -0.003 | 0.010 | OK |
| gap_k36 | -0.230 | -0.231 | -0.001 | 0.010 | OK |
| spec_a_hype | 0.050 | 0.049 | -0.001 | 0.010 | OK |
| spec_b_hype | 0.000 | -0.004 | -0.004 | 0.020 | OK |
| q4_within_025_k0 | 0.315 | 0.315 | 0.000 | 0.010 | OK |
| q4_within_025_k6 | 0.550 | 0.554 | 0.004 | 0.010 | OK |
| q4_within_025_k12 | 0.770 | 0.772 | 0.002 | 0.010 | OK |
| q4_within_025_k18 | 0.910 | 0.912 | 0.002 | 0.010 | OK |
| change_6_by_hype_q1 | -0.099 | -0.099 | 0.000 | 0.010 | OK |
| change_6_by_hype_q2 | -0.156 | -0.156 | -0.001 | 0.010 | OK |
| change_6_by_hype_q3 | -0.210 | -0.210 | 0.000 | 0.010 | OK |
| change_6_by_hype_q4 | -0.193 | -0.193 | 0.000 | 0.010 | OK |
| gap_k36_by_hype_q1 | -0.300 | -0.295 | 0.005 | 0.020 | OK |
| gap_k36_by_hype_q2 | -0.240 | -0.235 | 0.005 | 0.010 | OK |
| gap_k36_by_hype_q3 | -0.220 | -0.215 | 0.005 | 0.010 | OK |
| gap_k36_by_hype_q4 | -0.230 | -0.228 | 0.002 | 0.010 | OK |
| ks_avg_m0 | 7.620 | 7.617 | -0.003 | 0.010 | OK |
| nonks_avg_m0 | 7.230 | 7.226 | -0.004 | 0.010 | OK |
| ks_gap_within_bands | -0.080 | -0.076 | 0.004 | 0.020 | OK |
| share_rank_improved_36 | 0.740 | 0.744 | 0.004 | 0.010 | OK |
| avg_rank100 | 7.930 | 7.930 | 0.000 | 0.010 | OK |
| avg_rank1000 | 7.300 | 7.300 | 0.000 | 0.010 | OK |

## Figures

- [fig01_rating_change_by_age.png](../figures/fig01_rating_change_by_age.png)
- [fig02_new_vs_displayed_gap.png](../figures/fig02_new_vs_displayed_gap.png)
- [fig03_cohorts_and_control.png](../figures/fig03_cohorts_and_control.png)
- [fig04_change_distribution.png](../figures/fig04_change_distribution.png)
- [fig05_examples.png](../figures/fig05_examples.png)
- [fig06_by_hype_quartile.png](../figures/fig06_by_hype_quartile.png)
- [fig07_event_study.png](../figures/fig07_event_study.png)
- [fig08_when_to_trust.png](../figures/fig08_when_to_trust.png)
- [fig09_speed_not_size.png](../figures/fig09_speed_not_size.png)
- [fig10_kickstarter.png](../figures/fig10_kickstarter.png)

## Tables

- [change36_by_avg0_decile.csv](../tables/change36_by_avg0_decile.csv)
- [cohort_sizes.csv](../tables/cohort_sizes.csv)
- [control_adjusted_change36.csv](../tables/control_adjusted_change36.csv)
- [control_curve_by_age.csv](../tables/control_curve_by_age.csv)
- [control_series.csv](../tables/control_series.csv)
- [curve_by_entry_year.csv](../tables/curve_by_entry_year.csv)
- [curve_by_hype_quartile.csv](../tables/curve_by_hype_quartile.csv)
- [curve_by_segment.csv](../tables/curve_by_segment.csv)
- [curve_overall.csv](../tables/curve_overall.csv)
- [gap_new_vs_displayed.csv](../tables/gap_new_vs_displayed.csv)
- [kickstarter_by_band.csv](../tables/kickstarter_by_band.csv)
- [q3_change_by_kickstarted.csv](../tables/q3_change_by_kickstarted.csv)
- [q3_coverage.csv](../tables/q3_coverage.csv)
- [q4_accuracy_by_k.csv](../tables/q4_accuracy_by_k.csv)
- [q4_adjusted_predictor.csv](../tables/q4_adjusted_predictor.csv)
- [sample_waterfall.csv](../tables/sample_waterfall.csv)
- [segment_change.csv](../tables/segment_change.csv)
- [segments.csv](../tables/segments.csv)
- [speed_not_size.csv](../tables/speed_not_size.csv)
- [table1_sample.csv](../tables/table1_sample.csv)

## Model and robustness outputs

- [model_event_study.csv](model_event_study.csv)
- [model_event_study.md](model_event_study.md)
- [model_q2.csv](model_q2.csv)
- [model_q2.md](model_q2.md)
- [model_q3.csv](model_q3.csv)
- [model_q3.md](model_q3.md)
- [q4_notes.md](q4_notes.md)
- [robustness.csv](robustness.csv)
- [robustness.md](robustness.md)
- [robustness_gap.csv](robustness_gap.csv)
- [sanity_checks.csv](sanity_checks.csv)
- [table1_sample.md](table1_sample.md)
