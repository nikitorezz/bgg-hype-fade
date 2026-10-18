-- 03_panel.sql : monthly panel of new releases + per-game summary
-- Inputs : snapshots, game_cohorts, games; variables from config.yaml
-- Outputs: panel (game x observed month, k = 0..max_k), game_summary (one row per new release)
-- Rules (data_notes sections 6 and 7):
--   * lagged values come only from exactly k - w; a missing month is never interpolated
--   * new_avg = (avg_t*n_t - avg_p*n_p) / (n_t - n_p), defined only when raters increased
--   * Average is rounded to 2 decimals, so new_avg has a worst-case error of
--     rounding_half_unit * (n_t + n_p) / (n_t - n_p); "ok" requires a large enough delta AND a
--     small enough error bound AND a value inside the valid rating range.

-- 1. All observed months of every new release, k months after entry.
CREATE OR REPLACE TABLE panel_base AS
SELECT
    c.game_id,
    s.snap_month,
    date_diff('month', c.entry_month, s.snap_month)     AS k,
    c.entry_month,
    c.entry_year,
    c.in_main_sample,
    s.avg_rating,
    s.bayes_avg,
    s.n_raters,
    s.rank
FROM snapshots AS s
JOIN game_cohorts AS c USING (game_id)
WHERE c.is_new_release
  AND date_diff('month', c.entry_month, s.snap_month) BETWEEN 0 AND getvariable('max_k');

-- 2. For each window w: the value observed exactly w months earlier (NULL if that month is missing).
-- @repeat windows
CREATE OR REPLACE TABLE panel_lag_{{item}} AS
SELECT
    b.game_id,
    b.k,
    p.n_raters      AS prev_n_{{item}},
    p.avg_rating    AS prev_avg_{{item}}
FROM panel_base AS b
LEFT JOIN panel_base AS p
    ON p.game_id = b.game_id AND p.k = b.k - {{item}};
-- @end

-- 3. Panel with change since entry and the new-rating average for each window.
CREATE OR REPLACE TABLE panel AS
WITH joined AS (
    SELECT
        b.*
        -- @repeat windows
        , l{{item}}.prev_n_{{item}}
        , l{{item}}.prev_avg_{{item}}
        -- @end
    FROM panel_base AS b
    -- @repeat windows
    LEFT JOIN panel_lag_{{item}} AS l{{item}} USING (game_id, k)
    -- @end
),
with_delta AS (
    SELECT
        *,
        avg_rating - max(avg_rating) FILTER (WHERE k = 0) OVER (PARTITION BY game_id) AS d_rating
        -- @repeat windows
        , n_raters - prev_n_{{item}} AS delta_raters_{{item}}
        -- @end
    FROM joined
),
with_new_avg AS (
    SELECT
        *
        -- @repeat windows
        , delta_raters_{{item}} < 0 AS raters_decreased_{{item}}
        , CASE WHEN delta_raters_{{item}} > 0
               THEN (avg_rating * n_raters - prev_avg_{{item}} * prev_n_{{item}})
                    / delta_raters_{{item}} END AS new_avg_{{item}}
        , CASE WHEN delta_raters_{{item}} > 0
               THEN getvariable('rounding_half_unit') * (n_raters + prev_n_{{item}})
                    / delta_raters_{{item}} END AS new_avg_err_{{item}}
        -- @end
    FROM with_delta
)
SELECT
    game_id, snap_month, k, entry_month, entry_year, in_main_sample,
    avg_rating, bayes_avg, n_raters, rank, d_rating
    -- @repeat windows
    , prev_n_{{item}}
    , prev_avg_{{item}}
    , delta_raters_{{item}}
    , raters_decreased_{{item}}
    , new_avg_{{item}}
    , new_avg_err_{{item}}
    , coalesce(delta_raters_{{item}} >= getvariable('min_delta_raters')
               AND new_avg_err_{{item}} <= getvariable('max_error_bound')
               AND new_avg_{{item}} BETWEEN getvariable('valid_min') AND getvariable('valid_max'),
               FALSE)                                    AS new_avg_ok_{{item}}
    , new_avg_{{item}} NOT BETWEEN getvariable('valid_min') AND getvariable('valid_max')
                                                         AS new_avg_out_of_range_{{item}}
    -- @end
FROM with_new_avg
ORDER BY game_id, k;

-- helper tables are not part of the output
-- @repeat windows
DROP TABLE panel_lag_{{item}};
-- @end
DROP TABLE panel_base;

-- 4. One row per new release.
CREATE OR REPLACE TABLE game_summary AS
WITH agg AS (
    SELECT
        game_id
        -- @repeat milestones
        , max(avg_rating) FILTER (WHERE k = {{item}}) AS avg_m{{item}}
        , max(n_raters)   FILTER (WHERE k = {{item}}) AS raters_m{{item}}
        -- @end
        , max(rank) FILTER (WHERE k = 0)                    AS rank_m0
        , max(rank) FILTER (WHERE k = getvariable('max_k')) AS rank_m{{max_k}}
        -- Delta-weighted mean of usable one-window new_avg over year 1 (k 1-12) and year 3 (25-36).
        , sum(new_avg_{{main_window}} * delta_raters_{{main_window}})
              FILTER (WHERE new_avg_ok_{{main_window}} AND k BETWEEN 1 AND 12)
          / nullif(sum(delta_raters_{{main_window}})
              FILTER (WHERE new_avg_ok_{{main_window}} AND k BETWEEN 1 AND 12), 0) AS new_avg_y1
        , sum(new_avg_{{main_window}} * delta_raters_{{main_window}})
              FILTER (WHERE new_avg_ok_{{main_window}} AND k BETWEEN 25 AND 36)
          / nullif(sum(delta_raters_{{main_window}})
              FILTER (WHERE new_avg_ok_{{main_window}} AND k BETWEEN 25 AND 36), 0) AS new_avg_y3
        , count(*) FILTER (WHERE new_avg_ok_{{main_window}} AND k BETWEEN 1 AND 12)  AS n_ok_y1
        , count(*) FILTER (WHERE new_avg_ok_{{main_window}} AND k BETWEEN 25 AND 36) AS n_ok_y3
    FROM panel
    GROUP BY game_id
),
hype AS (
    -- Hype = growth in raters between entry and month hype_month (log scale and absolute).
    SELECT
        game_id,
        ln(raters_m{{hype_month}} + 1) - ln(raters_m0 + 1)  AS hype_log,
        raters_m{{hype_month}} - raters_m0                  AS hype_abs
    FROM agg
),
hype_q AS (
    SELECT
        h.game_id,
        h.hype_log,
        h.hype_abs,
        -- 1 = least hyped; quartiles within each entry year (or other configured partition)
        ntile(4) OVER (PARTITION BY c.{{hype_quartile_partition}}
                       ORDER BY h.hype_log, h.game_id)      AS hype_quartile
    FROM hype AS h
    JOIN game_cohorts AS c USING (game_id)
    WHERE h.hype_log IS NOT NULL
)
SELECT
    c.game_id,
    c.latest_name,
    c.entry_month,
    c.entry_year,
    c.pub_year_entry,
    c.in_main_sample
    -- @repeat horizons
    , c.observed_m{{item}}
    -- @end
    , a.* EXCLUDE (game_id)
    -- @repeat horizons
    , a.avg_m{{item}} - a.avg_m0 AS change_{{item}}
    -- @end
    , hq.hype_log
    , hq.hype_abs
    , hq.hype_quartile
FROM game_cohorts AS c
JOIN agg AS a USING (game_id)
LEFT JOIN hype_q AS hq USING (game_id)
WHERE c.is_new_release
ORDER BY c.game_id;
