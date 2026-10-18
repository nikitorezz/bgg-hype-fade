-- 01_load.sql : monthly snapshot CSVs -> DuckDB tables
-- Inputs : variable snapshot_files (manifest file list, injected by build.py)
-- Outputs: snapshots_raw, snapshots (deduplicated), load_log, games
-- See docs/data_notes.md sections 2 and 4.

-- 1. Raw load with explicit types. URL/Thumbnail are read but dropped (URL is derivable from ID).
CREATE OR REPLACE TABLE snapshots_raw AS
SELECT
    strptime(regexp_extract(filename, '(\d{4}-\d{2}-\d{2})\.csv$', 1), '%Y-%m-%d')::DATE
                                    AS snap_date,
    date_trunc('month', snap_date)::DATE
                                    AS snap_month,
    "ID"                            AS game_id,
    "Name"                          AS name,
    "Year"                          AS pub_year,       -- 0 = unknown; junk values exist
    "Rank"                          AS rank,
    "Average"                       AS avg_rating,     -- raw mean, rounded to 2 decimals
    "Bayes average"                 AS bayes_avg,
    "Users rated"                   AS n_raters
FROM read_csv(
    getvariable('snapshot_files'),
    filename = true,
    header = true,
    -- Explicit dialect: the sniffer mis-detects the quoting on names such as "Tarleton's Quarter!"
    auto_detect = false,
    delim = ',',
    quote = '"',
    escape = '"',
    columns = {
        'ID': 'BIGINT', 'Name': 'VARCHAR', 'Year': 'INTEGER', 'Rank': 'INTEGER',
        'Average': 'DOUBLE', 'Bayes average': 'DOUBLE', 'Users rated': 'INTEGER',
        'URL': 'VARCHAR', 'Thumbnail': 'VARCHAR'
    }
);

-- 2. One row per (snap_date, game_id). The list is scraped page by page while ranks shift, so a game
--    can appear twice. Keep the row chosen by load.dedup_order; the trailing keys only make ties
--    deterministic so reruns give identical output.
CREATE OR REPLACE TABLE snapshots AS
SELECT *
FROM snapshots_raw
QUALIFY row_number() OVER (
    PARTITION BY snap_date, game_id
    ORDER BY {{dedup_order}}, bayes_avg DESC, avg_rating DESC, name
) = 1;

-- 3. How much dedup removed, per file.
CREATE OR REPLACE TABLE load_log AS
SELECT
    r.snap_date,
    r.rows_raw,
    d.rows_dedup,
    r.rows_raw - d.rows_dedup       AS dup_pairs_removed
FROM (SELECT snap_date, count(*) AS rows_raw FROM snapshots_raw GROUP BY snap_date) AS r
JOIN (SELECT snap_date, count(*) AS rows_dedup FROM snapshots GROUP BY snap_date) AS d
    USING (snap_date)
ORDER BY snap_date;

-- 4. One row per game: first/last appearance and publication-year history.
CREATE OR REPLACE TABLE games AS
SELECT
    game_id,
    arg_max(name, snap_date)        AS latest_name,
    min(snap_month)                 AS first_month,
    max(snap_month)                 AS last_month,
    count(DISTINCT snap_month)      AS months_present,
    arg_min(pub_year, snap_date)    AS pub_year_at_entry,
    arg_max(pub_year, snap_date)    AS pub_year_latest,
    count(DISTINCT pub_year)        AS n_distinct_pub_years
FROM snapshots
GROUP BY game_id;
