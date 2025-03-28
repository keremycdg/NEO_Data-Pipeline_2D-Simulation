EXPORT DATA OPTIONS(
  uri='gs://project-kerem2025-demobucket/nasa_cad_export/cad_data_*.csv',
  format='CSV',
  overwrite=true,
  header=true
)
AS
SELECT * FROM `de-zoomcamp2025-project.nasa_cad_data.nasa_cad`;

CREATE OR REPLACE EXTERNAL TABLE `de-zoomcamp2025-project.nasa_cad_data.df_final_ext` (
  col1  STRING,       -- des
  col2  STRING,       -- orbit_id
  col3  STRING,       -- jd
  col4  STRING,       -- dist
  col5  STRING,       -- dist_min
  col6  STRING,       -- dist_max
  col7  STRING,       -- v_rel
  col8  STRING,       -- v_inf
  col9  STRING,       -- t_sigma_f
  col10 STRING,       -- h
  col11 STRING,       -- fullname
  col12 STRING,       -- _dlt_load_id
  col13 STRING,       -- _dlt_id
  col14 STRING,       -- diameter
  col15 STRING,       -- diameter_sigma (will be dropped later)
  col16 TIMESTAMP,    -- cd_ts: the timestamp column (e.g. "1999-06-12T05:23:00.000Z")
  col17 STRING,       -- h_v_rel_ratio
  col18 STRING        -- h_diameter_ratio
)
OPTIONS (
  format = 'CSV',
  uris = ['gs://project-kerem2025-demobucket/df_final/*.csv'],
  skip_leading_rows = 1
);

CREATE OR REPLACE TABLE `de-zoomcamp2025-project.nasa_cad_data.df_final_partitioned_clustered`
PARTITION BY RANGE_BUCKET(year, GENERATE_ARRAY(1900, 2100, 1))
CLUSTER BY des
AS
SELECT
  col1 AS des,
  col2 AS orbit_id,
  SAFE_CAST(col3 AS FLOAT64) AS jd,
  SAFE_CAST(col4 AS FLOAT64) AS dist,
  SAFE_CAST(col5 AS FLOAT64) AS dist_min,
  SAFE_CAST(col6 AS FLOAT64) AS dist_max,
  SAFE_CAST(col7 AS FLOAT64) AS v_rel,
  SAFE_CAST(REGEXP_REPLACE(col8, r'_.*', '') AS FLOAT64) AS v_inf_numeric,
  col9 AS t_sigma_f,
  SAFE_CAST(col10 AS FLOAT64) AS h_numeric,
  col11 AS fullname,
  col12 AS _dlt_load_id,
  col13 AS _dlt_id,
  SAFE_CAST(col14 AS FLOAT64) AS diameter,
  -- Drop col15 (diameter_sigma)
  col16 AS cd_ts,
  SAFE_CAST(col17 AS FLOAT64) AS h_v_rel_ratio,
  SAFE_CAST(col18 AS FLOAT64) AS h_diameter_ratio,
  EXTRACT(YEAR FROM col16) AS year
FROM `de-zoomcamp2025-project.nasa_cad_data.df_final_ext`;
