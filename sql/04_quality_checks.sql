-- 04_quality_checks.sql : data-quality checks over every earlier stage
-- Inputs : manifest (loaded by qc.py), snapshots, load_log, games, game_cohorts, panel, game_summary,
--          qc_expect_* tables (built by qc.py from config.yaml `qc:`), variables from config.yaml
-- Outputs: qc_results(check_id, description, value, expected, status) + three small detail tables
-- Status: PASS | WARN | FAIL, or INFO for report-only rows.

-- Detail table: months where a truncated file was replaced (check 02).
CREATE OR REPLACE TABLE qc_tbl_substitutions AS
SELECT month, chosen_date, status, rows, rejected
FROM manifest
WHERE status <> 'ok'
ORDER BY month;

-- Detail table: new releases with a missing month in k = 0..min(max_k, follow-up) (check 10).
-- 'internal gap' = a month is absent but a later one is present; 'dropped out' = ranking ended early.
CREATE OR REPLACE TABLE qc_tbl_missing_months AS
WITH per_game AS (
    SELECT
        c.game_id,
        c.entry_year,
        least(getvariable('max_k'), c.followup_available) + 1   AS months_expected,
        count(p.k)                                              AS months_observed,
        coalesce(max(p.k), -1) + 1                              AS span_observed
    FROM game_cohorts AS c
    LEFT JOIN panel AS p USING (game_id)
    WHERE c.is_new_release
    GROUP BY c.game_id, c.entry_year, c.followup_available
)
SELECT
    entry_year,
    count(*)                                                     AS new_releases,
    count(*) FILTER (WHERE months_observed < months_expected)    AS with_missing_month,
    count(*) FILTER (WHERE span_observed > months_observed)      AS with_internal_gap,
    count(*) FILTER (WHERE span_observed < months_expected)      AS dropped_out_early
FROM per_game
GROUP BY entry_year
ORDER BY entry_year;

-- Detail table: share of usable new_avg by months since entry, for each window (check 12).
CREATE OR REPLACE TABLE qc_tbl_new_avg_ok AS
SELECT
    k,
    count(*) FILTER (WHERE prev_n_1 IS NOT NULL)                 AS rows_w1,
    round(100.0 * count(*) FILTER (WHERE new_avg_ok_1)
          / nullif(count(*) FILTER (WHERE prev_n_1 IS NOT NULL), 0), 1) AS pct_ok_w1,
    count(*) FILTER (WHERE prev_n_3 IS NOT NULL)                 AS rows_w3,
    round(100.0 * count(*) FILTER (WHERE new_avg_ok_3)
          / nullif(count(*) FILTER (WHERE prev_n_3 IS NOT NULL), 0), 1) AS pct_ok_w3
FROM panel
WHERE (k IN (SELECT unnest(getvariable('milestones'))) OR k = 1) AND k > 0
GROUP BY k
ORDER BY k;

-- Spot-check games: actual values next to the expected ones from data_notes section 8.
CREATE OR REPLACE TABLE qc_tbl_spot_checks AS
WITH monthly AS (
    SELECT
        s.game_id,
        date_diff('month', g.first_month, s.snap_month) AS k,
        s.avg_rating,
        s.n_raters
    FROM snapshots AS s
    JOIN games AS g USING (game_id)
),
actual AS (
    SELECT
        e.id, e.name,
        c.entry_month, c.pub_year_at_entry, c.is_new_release,
        max(m.avg_rating) FILTER (WHERE m.k = 0)    AS avg_k0,
        max(m.n_raters)   FILTER (WHERE m.k = 0)    AS raters_k0,
        max(m.n_raters)   FILTER (WHERE m.k = 6)    AS raters_k6,
        max(m.avg_rating) FILTER (WHERE m.k = 12)   AS avg_k12,
        max(m.avg_rating) FILTER (WHERE m.k = 36)   AS avg_k36,
        max(m.n_raters)   FILTER (WHERE m.k = 36)   AS raters_k36
    FROM qc_expect_spot AS e
    LEFT JOIN game_cohorts AS c ON c.game_id = e.id
    LEFT JOIN monthly AS m ON m.game_id = e.id
    GROUP BY e.id, e.name, c.entry_month, c.pub_year_at_entry, c.is_new_release
)
SELECT
    e.id, e.name,
    a.entry_month, a.pub_year_at_entry, a.is_new_release, a.avg_k0, a.raters_k0, a.raters_k6,
    a.avg_k12, a.avg_k36, a.raters_k36,
    array_to_string(list_filter([
        CASE WHEN a.entry_month IS DISTINCT FROM e.entry THEN 'entry_month' END,
        CASE WHEN a.pub_year_at_entry IS DISTINCT FROM e.pub_year THEN 'pub_year' END,
        CASE WHEN a.is_new_release IS DISTINCT FROM e.in_cohort THEN 'in_cohort' END,
        CASE WHEN abs(a.avg_k0 - e.avg_k0) > 0.01 OR a.avg_k0 IS NULL THEN 'avg_k0' END,
        CASE WHEN a.raters_k0 IS DISTINCT FROM e.raters_k0 THEN 'raters_k0' END,
        CASE WHEN a.raters_k6 IS DISTINCT FROM e.raters_k6 THEN 'raters_k6' END,
        CASE WHEN abs(a.avg_k12 - e.avg_k12) > 0.01 OR a.avg_k12 IS NULL THEN 'avg_k12' END,
        CASE WHEN abs(a.avg_k36 - e.avg_k36) > 0.01 OR a.avg_k36 IS NULL THEN 'avg_k36' END,
        CASE WHEN a.raters_k36 IS DISTINCT FROM e.raters_k36 THEN 'raters_k36' END
    ], x -> x IS NOT NULL), ',')                    AS mismatches
FROM qc_expect_spot AS e
JOIN actual AS a USING (id, name)
ORDER BY e.id;

CREATE OR REPLACE TABLE qc_results AS
WITH
-- 01 manifest completeness: every month from start_month to end_month present exactly once
expected_months AS (
    SELECT unnest(generate_series(getvariable('start_month'), getvariable('end_month'),
                                  INTERVAL 1 MONTH))::DATE AS month
),
c01 AS (
    SELECT
        (SELECT count(DISTINCT month) FROM manifest)                    AS n_manifest,
        (SELECT count(*) FROM expected_months)                          AS n_expected,
        (SELECT count(*) FROM expected_months e
          WHERE e.month NOT IN (SELECT month FROM manifest))            AS n_missing
),
-- 03 row count of the accepted file vs the previous accepted month
c03 AS (
    SELECT count(*) AS n_bad
    FROM (SELECT rows, lag(rows) OVER (ORDER BY month) AS prev_rows FROM manifest)
    WHERE rows < getvariable('min_row_ratio') * prev_rows
),
c02 AS (
    SELECT
        coalesce(string_agg(strftime(month, '%Y-%m'), ',' ORDER BY month), '') AS actual,
        (SELECT string_agg(strftime(month, '%Y-%m'), ',' ORDER BY month) FROM qc_expect_subst)
                                                                        AS expected,
        count(*) FILTER (WHERE status = 'fallback')                     AS n_fallback
    FROM manifest WHERE status <> 'ok'
),
c07 AS (
    SELECT
        count(*) FILTER (WHERE c.pub_year_at_entry = 0)                 AS n_zero,
        count(*) FILTER (WHERE c.pub_year_at_entry <> 0 AND c.pub_year_entry IS NULL) AS n_junk,
        count(*) FILTER (WHERE g.n_distinct_pub_years > 1)              AS n_changing
    FROM game_cohorts AS c JOIN games AS g USING (game_id)
),
c10 AS (
    SELECT sum(with_missing_month) AS n_missing, sum(with_internal_gap) AS n_gap,
           sum(dropped_out_early) AS n_dropped
    FROM qc_tbl_missing_months
),
c11 AS (
    SELECT count(*) FILTER (WHERE raters_decreased_1) AS n_dec,
           count(*) FILTER (WHERE delta_raters_1 IS NOT NULL) AS n_steps,
           count(*) FILTER (WHERE delta_raters_1 = 0) AS n_flat
    FROM panel
),
c13 AS (
    SELECT
        count(*) FILTER (WHERE new_avg_out_of_range_1)                 AS oor_w1,
        count(*) FILTER (WHERE new_avg_out_of_range_1
                         AND new_avg_err_1 <= getvariable('max_error_bound')) AS oor_err_ok_w1,
        count(*) FILTER (WHERE new_avg_out_of_range_3)                 AS oor_w3,
        count(*) FILTER (WHERE new_avg_out_of_range_3
                         AND new_avg_err_3 <= getvariable('max_error_bound')) AS oor_err_ok_w3,
        count(*) FILTER (WHERE new_avg_1 IS NOT NULL)                  AS n_w1,
        count(*) FILTER (WHERE new_avg_3 IS NOT NULL)                  AS n_w3
    FROM panel
),
c14 AS (
    SELECT
        (SELECT count(*) - count(DISTINCT (game_id, k)) FROM panel)    AS n_dup,
        (SELECT count(*) FROM game_cohorts g WHERE g.is_new_release
           AND NOT EXISTS (SELECT 1 FROM panel p WHERE p.game_id = g.game_id AND p.k = 0)) AS n_no_k0,
        (SELECT count(*) FROM panel WHERE k = 0 AND d_rating <> 0)     AS n_bad_d0,
        (SELECT count(*) FROM panel WHERE k < 0 OR k > getvariable('max_k')) AS n_bad_k
)
SELECT * FROM (
    -- 01
    SELECT '01' AS check_id, 'Manifest covers every month start..end exactly once' AS description,
           n_manifest::VARCHAR || ' months, ' || n_missing::VARCHAR || ' missing' AS value,
           n_expected::VARCHAR || ' months, 0 missing' AS expected,
           CASE WHEN n_manifest = n_expected AND n_missing = 0 THEN 'PASS' ELSE 'FAIL' END AS status
    FROM c01
    UNION ALL
    -- 02
    SELECT '02', 'Months where a truncated file was substituted', actual, expected,
           CASE WHEN actual = expected THEN 'PASS' ELSE 'WARN' END
    FROM c02
    UNION ALL
    SELECT '02b', 'Months with no valid candidate (fallback)', n_fallback::VARCHAR, '0',
           CASE WHEN n_fallback = 0 THEN 'PASS' ELSE 'WARN' END
    FROM c02
    UNION ALL
    -- 03
    SELECT '03', 'Months whose accepted file has < min_row_ratio x previous month rows',
           n_bad::VARCHAR, '0', CASE WHEN n_bad = 0 THEN 'PASS' ELSE 'FAIL' END
    FROM c03
    UNION ALL
    -- 04
    SELECT '04', 'Duplicate (snap_date, game_id) pairs after dedup',
           (count(*) - count(DISTINCT (snap_date, game_id)))::VARCHAR, '0',
           CASE WHEN count(*) = count(DISTINCT (snap_date, game_id)) THEN 'PASS' ELSE 'FAIL' END
    FROM snapshots
    UNION ALL
    -- 05
    SELECT '05', 'Duplicate rows removed in load (files affected in expected)',
           sum(dup_pairs_removed)::VARCHAR || ' rows in '
               || count(*) FILTER (WHERE dup_pairs_removed > 0)::VARCHAR || ' files',
           'report (reference: 721 in 16 files)', 'INFO'
    FROM load_log
    UNION ALL
    -- 06
    SELECT '06a', 'avg_rating outside valid range', count(*)::VARCHAR, '0',
           CASE WHEN count(*) = 0 THEN 'PASS' ELSE 'FAIL' END
    FROM snapshots
    WHERE avg_rating NOT BETWEEN getvariable('valid_min') AND getvariable('valid_max')
    UNION ALL
    SELECT '06b', 'n_raters below 30 (BGG ranking threshold)', count(*)::VARCHAR, '0',
           CASE WHEN count(*) = 0 THEN 'PASS' ELSE 'FAIL' END
    FROM snapshots WHERE n_raters < 30
    UNION ALL
    SELECT '06c', 'NULL game_id / avg_rating / n_raters', count(*)::VARCHAR, '0',
           CASE WHEN count(*) = 0 THEN 'PASS' ELSE 'FAIL' END
    FROM snapshots WHERE game_id IS NULL OR avg_rating IS NULL OR n_raters IS NULL
    UNION ALL
    -- 07
    SELECT '07', 'Publication year at entry: unknown (0) / junk (cleaned to NULL) / changes over time',
           n_zero::VARCHAR || ' / ' || n_junk::VARCHAR || ' / ' || n_changing::VARCHAR,
           'report (reference: 432 zero ever, 1,592 changing)', 'INFO'
    FROM c07
    UNION ALL
    -- 08
    SELECT '08.' || e.entry_year::VARCHAR, 'New releases entering in ' || e.entry_year::VARCHAR,
           coalesce(s.new_releases, 0)::VARCHAR, e.expected::VARCHAR,
           CASE WHEN coalesce(s.new_releases, 0) = e.expected THEN 'PASS' ELSE 'FAIL' END
    FROM qc_expect_entry AS e LEFT JOIN cohort_sizes AS s USING (entry_year)
    UNION ALL
    -- 09
    SELECT '09.' || e.entry_year::VARCHAR, 'Cohort observed at month 36, entry ' || e.entry_year::VARCHAR,
           coalesce(s.observed_m36, 0)::VARCHAR, '>= ' || e.pilot::VARCHAR,
           CASE WHEN coalesce(s.observed_m36, 0) >= e.pilot THEN 'PASS' ELSE 'WARN' END
    FROM qc_expect_m36 AS e LEFT JOIN cohort_sizes AS s USING (entry_year)
    UNION ALL
    -- 10
    SELECT '10', 'New releases with a missing month in k=0..36 (of which internal gap / dropped out)',
           n_missing::VARCHAR || ' (' || n_gap::VARCHAR || ' / ' || n_dropped::VARCHAR || ')',
           '< ' || getvariable('pilot_games_with_missing_month')::VARCHAR,
           CASE WHEN n_missing < getvariable('pilot_games_with_missing_month') THEN 'PASS'
                ELSE 'WARN' END
    FROM c10
    UNION ALL
    -- 11
    SELECT '11', 'One-month steps where n_raters decreased (deleted ratings)',
           n_dec::VARCHAR || ' of ' || n_steps::VARCHAR || ' ('
               || round(100.0 * n_dec / n_steps, 2)::VARCHAR || '%)',
           'report (reference ~1.5%)', 'INFO'
    FROM c11
    UNION ALL
    SELECT '11b', 'One-month steps with unchanged n_raters',
           n_flat::VARCHAR || ' of ' || n_steps::VARCHAR || ' ('
               || round(100.0 * n_flat / n_steps, 1)::VARCHAR || '%)',
           'report (reference ~14%)', 'INFO'
    FROM c11
    UNION ALL
    -- 12
    SELECT '12', 'Usable new_avg share by k (% ok: 1-month / 3-month window)',
           string_agg('k' || k::VARCHAR || ': ' || pct_ok_w1::VARCHAR || ' / '
                      || coalesce(pct_ok_w3::VARCHAR, '-'), '; ' ORDER BY k),
           'report (table below)', 'INFO'
    FROM qc_tbl_new_avg_ok
    UNION ALL
    -- 13
    SELECT '13', 'new_avg outside valid range: all / among err <= max_error_bound (1-month window)',
           oor_w1::VARCHAR || ' of ' || n_w1::VARCHAR || ' / ' || oor_err_ok_w1::VARCHAR,
           'report (reference: 3,439 / 1,255)', 'INFO'
    FROM c13
    UNION ALL
    SELECT '13b', 'new_avg outside valid range: all / among err <= max_error_bound (3-month window)',
           oor_w3::VARCHAR || ' of ' || n_w3::VARCHAR || ' / ' || oor_err_ok_w3::VARCHAR,
           'report', 'INFO'
    FROM c13
    UNION ALL
    -- 14
    SELECT '14', 'Panel unique on (game_id, k); k in 0..max_k; every game has k=0; d_rating=0 at k=0',
           'dup=' || n_dup::VARCHAR || ', no_k0=' || n_no_k0::VARCHAR || ', bad_d0='
               || n_bad_d0::VARCHAR || ', bad_k=' || n_bad_k::VARCHAR,
           'all 0',
           CASE WHEN n_dup + n_no_k0 + n_bad_d0 + n_bad_k = 0 THEN 'PASS' ELSE 'FAIL' END
    FROM c14
    UNION ALL
    -- 15
    SELECT '15.' || e.k::VARCHAR, 'Mean d_rating at k=' || e.k::VARCHAR || ' (all new releases)',
           round(avg(p.d_rating), 3)::VARCHAR,
           e.expected::VARCHAR || ' +/- ' || getvariable('tolerance_mean_change')::VARCHAR,
           CASE WHEN abs(avg(p.d_rating) - e.expected) <= getvariable('tolerance_mean_change')
                THEN 'PASS' ELSE 'WARN' END
    FROM qc_expect_mean AS e JOIN panel AS p ON p.k = e.k
    GROUP BY e.k, e.expected
    UNION ALL
    -- 16
    SELECT '16.' || id::VARCHAR, 'Spot check: ' || name,
           CASE WHEN mismatches = '' THEN 'match' ELSE 'mismatch: ' || mismatches END,
           'match', CASE WHEN mismatches = '' THEN 'PASS' ELSE 'FAIL' END
    FROM qc_tbl_spot_checks
)
ORDER BY check_id;
