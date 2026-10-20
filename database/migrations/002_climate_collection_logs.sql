USE local_climate_policy;

-- Apply only if climate_observations already exists and lacks collected_at.
-- MySQL 8.0 supports ADD COLUMN IF NOT EXISTS only in some versions, so inspect first:
-- SHOW COLUMNS FROM climate_observations LIKE 'collected_at';
-- If absent, run:
-- ALTER TABLE climate_observations ADD COLUMN collected_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP;

CREATE TABLE IF NOT EXISTS collection_logs (
  collection_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  source_name VARCHAR(255) NOT NULL,
  source_url VARCHAR(1000) NOT NULL,
  requested_start_date DATE NOT NULL,
  requested_end_date DATE NOT NULL,
  region_codes VARCHAR(500) NOT NULL,
  status ENUM('running','success','failed') NOT NULL DEFAULT 'running',
  api_days_processed INT NOT NULL DEFAULT 0,
  metric_rows_upserted INT NOT NULL DEFAULT 0,
  started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  finished_at DATETIME NULL,
  message TEXT NULL,
  error_message TEXT NULL,
  KEY ix_collection_status_started (status, started_at),
  KEY ix_collection_dates (requested_start_date, requested_end_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Deduplication relies on a unique key over region, station, metric, date and period.
-- Inspect existing indexes before adding a unique index to avoid duplicate-data failures.
-- SHOW INDEX FROM climate_observations;
-- If no equivalent unique key exists, first deduplicate existing rows, then run:
-- ALTER TABLE climate_observations ADD UNIQUE KEY uq_climate_observation
-- (region_id, station_code, metric_code, observation_date, aggregation_period);
