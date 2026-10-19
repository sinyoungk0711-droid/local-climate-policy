CREATE DATABASE IF NOT EXISTS local_climate_policy
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE local_climate_policy;

CREATE TABLE regions (
  region_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  region_code VARCHAR(20) NOT NULL UNIQUE,
  parent_region_id BIGINT UNSIGNED NULL,
  region_name VARCHAR(100) NOT NULL,
  region_level VARCHAR(20) NOT NULL,
  CONSTRAINT fk_regions_parent FOREIGN KEY (parent_region_id)
    REFERENCES regions(region_id) ON DELETE SET NULL
);

CREATE TABLE data_sources (
  source_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  source_name VARCHAR(200) NOT NULL,
  source_url VARCHAR(1000) NOT NULL,
  license_note VARCHAR(500) NULL,
  checked_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE climate_observations (
  observation_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  region_id BIGINT UNSIGNED NOT NULL,
  source_id BIGINT UNSIGNED NOT NULL,
  station_code VARCHAR(40) NULL,
  metric_code VARCHAR(50) NOT NULL,
  observation_date DATE NOT NULL,
  aggregation_period VARCHAR(20) NOT NULL DEFAULT 'daily',
  metric_value DECIMAL(12,3) NULL,
  unit VARCHAR(30) NOT NULL,
  quality_flag VARCHAR(30) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_climate_region FOREIGN KEY (region_id) REFERENCES regions(region_id),
  CONSTRAINT fk_climate_source FOREIGN KEY (source_id) REFERENCES data_sources(source_id),
  INDEX idx_climate_region_metric_date (region_id, metric_code, observation_date),
  INDEX idx_climate_station_date (station_code, observation_date)
);

CREATE TABLE regional_issues (
  issue_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  region_id BIGINT UNSIGNED NOT NULL,
  source_id BIGINT UNSIGNED NULL,
  issue_title VARCHAR(200) NOT NULL,
  issue_category VARCHAR(50) NOT NULL,
  evidence_summary TEXT NULL,
  reference_date DATE NULL,
  latitude DECIMAL(10,7) NULL,
  longitude DECIMAL(10,7) NULL,
  verification_status VARCHAR(30) NOT NULL DEFAULT 'needs_review',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_issue_region FOREIGN KEY (region_id) REFERENCES regions(region_id),
  CONSTRAINT fk_issue_source FOREIGN KEY (source_id) REFERENCES data_sources(source_id),
  INDEX idx_issue_region_category (region_id, issue_category)
);

CREATE TABLE policies (
  policy_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  region_id BIGINT UNSIGNED NOT NULL,
  source_id BIGINT UNSIGNED NULL,
  policy_title VARCHAR(250) NOT NULL,
  policy_summary TEXT NULL,
  responsible_agency VARCHAR(200) NULL,
  status VARCHAR(30) NOT NULL DEFAULT 'unverified',
  start_date DATE NULL,
  end_date DATE NULL,
  budget_amount DECIMAL(16,2) NULL,
  official_url VARCHAR(1000) NULL,
  verified_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_policy_region FOREIGN KEY (region_id) REFERENCES regions(region_id),
  CONSTRAINT fk_policy_source FOREIGN KEY (source_id) REFERENCES data_sources(source_id),
  INDEX idx_policy_region_status (region_id, status)
);

CREATE TABLE issue_policies (
  issue_id BIGINT UNSIGNED NOT NULL,
  policy_id BIGINT UNSIGNED NOT NULL,
  relationship_note VARCHAR(500) NULL,
  PRIMARY KEY (issue_id, policy_id),
  CONSTRAINT fk_ip_issue FOREIGN KEY (issue_id) REFERENCES regional_issues(issue_id) ON DELETE CASCADE,
  CONSTRAINT fk_ip_policy FOREIGN KEY (policy_id) REFERENCES policies(policy_id) ON DELETE CASCADE
);

CREATE TABLE policy_metrics (
  policy_metric_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  policy_id BIGINT UNSIGNED NOT NULL,
  source_id BIGINT UNSIGNED NULL,
  metric_name VARCHAR(100) NOT NULL,
  before_value DECIMAL(12,3) NULL,
  after_value DECIMAL(12,3) NULL,
  unit VARCHAR(30) NOT NULL,
  before_period_start DATE NULL,
  before_period_end DATE NULL,
  after_period_start DATE NULL,
  after_period_end DATE NULL,
  calculation_note VARCHAR(1000) NULL,
  verified_at DATETIME NULL,
  CONSTRAINT fk_metric_policy FOREIGN KEY (policy_id) REFERENCES policies(policy_id) ON DELETE CASCADE,
  CONSTRAINT fk_metric_source FOREIGN KEY (source_id) REFERENCES data_sources(source_id),
  INDEX idx_policy_metric (policy_id, metric_name)
);

CREATE TABLE citizen_suggestions (
  suggestion_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  region_id BIGINT UNSIGNED NOT NULL,
  category VARCHAR(50) NOT NULL,
  place_description VARCHAR(120) NULL,
  description TEXT NOT NULL,
  status VARCHAR(30) NOT NULL DEFAULT 'received',
  is_public BOOLEAN NOT NULL DEFAULT FALSE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_suggestion_region FOREIGN KEY (region_id) REFERENCES regions(region_id),
  INDEX idx_suggestion_region_status (region_id, status)
);

INSERT INTO regions (region_code, region_name, region_level) VALUES
('11','서울특별시','시·도'),
('26','부산광역시','시·도'),
('27','대구광역시','시·도'),
('29','광주광역시','시·도'),
('30','대전광역시','시·도'),
('50','제주특별자치도','시·도');
