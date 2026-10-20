USE local_climate_policy;

CREATE TABLE IF NOT EXISTS weather_observations (
  weather_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  region_code VARCHAR(10) NOT NULL,
  region_name VARCHAR(100) NOT NULL,
  latitude DECIMAL(9,6) NOT NULL,
  longitude DECIMAL(9,6) NOT NULL,
  observed_at DATETIME NOT NULL,
  collected_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  temperature_c DECIMAL(7,3) NULL,
  feels_like_c DECIMAL(7,3) NULL,
  humidity_pct TINYINT UNSIGNED NULL,
  pressure_hpa SMALLINT UNSIGNED NULL,
  wind_speed_ms DECIMAL(8,3) NULL,
  rainfall_mm DECIMAL(8,3) NULL,
  weather_code INT NULL,
  weather_description VARCHAR(255) NULL,
  source_name VARCHAR(255) NOT NULL,
  source_url VARCHAR(1000) NOT NULL,
  raw_json JSON NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_weather_region_observed (region_code, observed_at),
  KEY ix_weather_collected (collected_at),
  KEY ix_weather_region_observed (region_code, observed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS news_articles (
  article_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  topic VARCHAR(180) NOT NULL,
  region_code VARCHAR(10) NOT NULL,
  headline VARCHAR(220) NOT NULL,
  article_body MEDIUMTEXT NOT NULL,
  facts MEDIUMTEXT NOT NULL,
  sources_json JSON NOT NULL,
  model_name VARCHAR(100) NOT NULL DEFAULT 'manual',
  review_status ENUM('pending','approved','on_hold') NOT NULL DEFAULT 'pending',
  reviewer VARCHAR(100) NULL,
  review_note TEXT NULL,
  reviewed_at DATETIME NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY ix_news_status_updated (review_status, updated_at),
  KEY ix_news_region_created (region_code, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS news_reviews (
  review_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  article_id BIGINT NOT NULL,
  status ENUM('pending','approved','on_hold') NOT NULL,
  reviewer VARCHAR(100) NOT NULL,
  review_note TEXT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY ix_review_article_created (article_id, created_at),
  CONSTRAINT fk_news_reviews_article FOREIGN KEY (article_id)
    REFERENCES news_articles(article_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
