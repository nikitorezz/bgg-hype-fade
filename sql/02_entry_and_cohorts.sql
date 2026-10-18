-- 02_entry_and_cohorts.sql : entry month, new-release rule, sample flags, waterfall
-- Inputs : snapshots, games; variables from config.yaml (cohort section, end_month)
-- Outputs: game_cohorts (one row per game), sample_waterfall, cohort_sizes
-- Research rules (do not change silently): entry month = first month present; games present in the
-- first snapshot are left-censored; new release = publication year AT ENTRY >= entry year - 1.

-- Months-since-entry at which each game has a snapshot (used for the observed_m* flags).
CREATE OR REPLACE TABLE game_cohorts AS
WITH obs AS (
    SELECT s.game_id, date_diff('month', g.first_month, s.snap_month) AS k
    FROM snapshots AS s
    JOIN games AS g USING (game_id)
),
obs_flags AS (
    SELECT
        game_id
        -- @repeat horizons
        , count(*) FILTER (WHERE k = {{item}}) > 0 AS observed_m{{item}}
        -- @end
    FROM obs
    GROUP BY game_id
),
base AS (
    SELECT
        g.game_id,
        g.latest_name,
        g.first_month                           AS entry_month,
        year(g.first_month)                     AS entry_year,
        g.last_month,
        g.months_present,
        g.pub_year_at_entry,
        -- Cleaned publication year: 0 (unknown) and junk values (e.g. 2200, 3500) become NULL.
        CASE
            WHEN g.pub_year_at_entry < getvariable('min_valid_pub_year') THEN NULL
            WHEN g.pub_year_at_entry > year(getvariable('end_month')) + getvariable('max_pub_year_slack')
                THEN NULL
            ELSE g.pub_year_at_entry
        END                                     AS pub_year_entry
    FROM games AS g
),
flagged AS (
    SELECT
        *,
        entry_month = getvariable('first_snapshot_month')       AS left_censored,
        pub_year_entry IS NULL                                  AS pub_year_unknown,
        coalesce(pub_year_entry
                 < entry_year - getvariable('new_release_max_age_years'), FALSE) AS old_game
    FROM base
)
SELECT
    f.game_id,
    f.latest_name,
    f.entry_month,
    f.entry_year,
    f.last_month,
    f.months_present,
    f.pub_year_at_entry,
    f.pub_year_entry,
    f.left_censored,
    f.pub_year_unknown,
    f.old_game,
    NOT f.left_censored AND NOT f.pub_year_unknown AND NOT f.old_game   AS is_new_release,
    date_diff('month', f.entry_month, getvariable('end_month'))        AS followup_available,
    (NOT f.left_censored AND NOT f.pub_year_unknown AND NOT f.old_game
        AND f.entry_month BETWEEN getvariable('main_entry_start') AND getvariable('main_entry_end'))
                                                                        AS in_main_sample
    -- @repeat horizons
    , coalesce(o.observed_m{{item}}, FALSE)                             AS observed_m{{item}}
    -- @end
FROM flagged AS f
LEFT JOIN obs_flags AS o USING (game_id);

-- Sample waterfall: each step removes one group, in a fixed order.
CREATE OR REPLACE TABLE sample_waterfall AS
WITH steps AS (
    SELECT 1 AS step_no, 'All games ever ranked' AS step, count(*) AS n_games
    FROM game_cohorts
    UNION ALL
    SELECT 2, 'Excluding left-censored (already in first snapshot)', count(*)
    FROM game_cohorts WHERE NOT left_censored
    UNION ALL
    SELECT 3, 'Excluding unknown / junk publication year', count(*)
    FROM game_cohorts WHERE NOT left_censored AND NOT pub_year_unknown
    UNION ALL
    SELECT 4, 'Excluding old games entering late = new releases', count(*)
    FROM game_cohorts WHERE is_new_release
    UNION ALL
    SELECT 5, 'New releases in main entry window (full follow-up possible)', count(*)
    FROM game_cohorts WHERE in_main_sample
    UNION ALL
    SELECT 6, 'Main sample observed at month 36', count(*)
    FROM game_cohorts WHERE in_main_sample AND observed_m36
)
SELECT
    step_no,
    step,
    n_games,
    lag(n_games) OVER (ORDER BY step_no) - n_games AS removed
FROM steps
ORDER BY step_no;

-- New releases by entry year, with how many are observed at each horizon.
CREATE OR REPLACE TABLE cohort_sizes AS
SELECT
    entry_year,
    count(*)                                AS new_releases
    -- @repeat horizons
    , count(*) FILTER (WHERE observed_m{{item}}) AS observed_m{{item}}
    -- @end
    , count(*) FILTER (WHERE in_main_sample) AS in_main_sample
FROM game_cohorts
WHERE is_new_release
GROUP BY entry_year
ORDER BY entry_year;
