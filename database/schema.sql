CREATE DATABASE IF NOT EXISTS local_climate_policy DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE local_climate_policy;

-- Canonical schema used by backend/app/climate_data.py and backend/app/auth.py.
-- This file is additive-safe for existing compatible tables.
CREATE TABLE IF NOT EXISTS regions (
  region_id INT AUTO_INCREMENT PRIMARY KEY,
  region_code VARCHAR(10) NOT NULL UNIQUE,
  parent_region_id INT NULL,
  region_name VARCHAR(100) NOT NULL,
  region_level VARCHAR(20) NOT NULL DEFAULT '시·도',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_regions_parent FOREIGN KEY (parent_region_id) REFERENCES regions(region_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS data_sources (
  source_id INT AUTO_INCREMENT PRIMARY KEY,
  source_name VARCHAR(255) NOT NULL,
  source_url VARCHAR(1000) NOT NULL,
  license_note TEXT NULL,
  checked_at DATETIME NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_data_sources_name_url (source_name(150), source_url(250))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS climate_observations (
  observation_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  region_id INT NOT NULL,
  source_id INT NOT NULL,
  station_code VARCHAR(20) NOT NULL,
  metric_code VARCHAR(40) NOT NULL,
  observation_date DATE NOT NULL,
  aggregation_period VARCHAR(20) NOT NULL DEFAULT 'daily',
  metric_value DECIMAL(12,4) NULL,
  unit VARCHAR(20) NOT NULL,
  quality_flag VARCHAR(40) NOT NULL DEFAULT 'raw_kma',
  collected_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_climate_observation (region_id, station_code, metric_code, observation_date, aggregation_period),
  KEY ix_climate_date_metric (observation_date, metric_code),
  KEY ix_climate_region_date (region_id, observation_date),
  CONSTRAINT fk_climate_region FOREIGN KEY (region_id) REFERENCES regions(region_id),
  CONSTRAINT fk_climate_source FOREIGN KEY (source_id) REFERENCES data_sources(source_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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

CREATE TABLE IF NOT EXISTS users (
  user_id INT AUTO_INCREMENT PRIMARY KEY,
  email VARCHAR(254) NOT NULL UNIQUE,
  display_name VARCHAR(60) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO regions (region_code, region_name, region_level) VALUES
 ('11','서울특별시','시·도'),('26','부산광역시','시·도'),('27','대구광역시','시·도'),
 ('29','광주광역시','시·도'),('30','대전광역시','시·도'),('50','제주특별자치도','시·도')
ON DUPLICATE KEY UPDATE region_name=VALUES(region_name), region_level=VALUES(region_level);
