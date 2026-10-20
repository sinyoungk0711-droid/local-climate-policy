import json
import logging
import os
from datetime import datetime, timezone
from typing import Literal, Optional

import requests
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
import pymysql
from pymysql.cursors import DictCursor

router = APIRouter(prefix="/api", tags=["weather and newsroom"])
logger = logging.getLogger(__name__)

# OpenWeather coordinates are explicit city-center approximations, not regional averages.
CITIES = {
    "11": {"name": "서울특별시", "lat": 37.5665, "lon": 126.9780},
    "26": {"name": "부산광역시", "lat": 35.1796, "lon": 129.0756},
    "27": {"name": "대구광역시", "lat": 35.8714, "lon": 128.6014},
    "29": {"name": "광주광역시", "lat": 35.1595, "lon": 126.8526},
    "30": {"name": "대전광역시", "lat": 36.3504, "lon": 127.3845},
    "50": {"name": "제주특별자치도", "lat": 33.4996, "lon": 126.5312},
}
OWM_URL = "https://api.openweathermap.org/data/2.5/weather"

def db():
    missing = [key for key in ("DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD") if not os.getenv(key)]
    if missing:
        raise HTTPException(503, "MySQL 환경변수가 없습니다: " + ", ".join(missing))
    try:
        return pymysql.connect(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            port=int(os.getenv("DB_PORT", "3306")),
            user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME", "local_climate_policy"),
            charset="utf8mb4", cursorclass=DictCursor, autocommit=False,
        )
    except pymysql.MySQLError:
        logger.exception("MySQL connection failed")
        raise HTTPException(503, "MySQL 연결에 실패했습니다.")

class ArticleCreate(BaseModel):
    topic: str = Field(min_length=3, max_length=180)
    region_code: str = Field(min_length=2, max_length=10)
    headline: str = Field(min_length=3, max_length=220)
    article: str = Field(min_length=30, max_length=16000)
    facts: str = Field(min_length=10, max_length=10000)
    sources: list[str] = Field(min_length=1, max_length=20)
    model: str = Field(default="manual", max_length=100)

class ReviewUpdate(BaseModel):
    status: Literal["pending", "approved", "on_hold"]
    reviewer: str = Field(min_length=1, max_length=100)
    review_note: str = Field(default="", max_length=4000)

def validate_sources(sources):
    if not sources or any(not u.startswith(("https://", "http://")) for u in sources):
        raise HTTPException(422, "출처는 http:// 또는 https:// URL이어야 합니다.")

@router.post("/weather/collect")
def collect_openweather(region_code: str = Query("11", description="지원 지역 코드")):
    """Fetch current OpenWeather data and persist a timestamped snapshot."""
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        raise HTTPException(503, "OPENWEATHER_API_KEY를 .env에 설정하세요.")
    if region_code not in CITIES:
        raise HTTPException(422, "지원하지 않는 지역 코드입니다.")
    city = CITIES[region_code]
    try:
        response = requests.get(OWM_URL, params={
            "lat": city["lat"], "lon": city["lon"], "appid": api_key, "units": "metric", "lang": "kr"
        }, timeout=20)
        response.raise_for_status()
        payload = response.json()
        current = payload["main"]
        weather = payload.get("weather", [{}])[0]
        observed_at = datetime.fromtimestamp(int(payload.get("dt", datetime.now(timezone.utc).timestamp())), tz=timezone.utc).replace(tzinfo=None)
    except requests.HTTPError as exc:
        logger.warning("OpenWeather HTTP error for region=%s: %s", region_code, exc)
        raise HTTPException(502, "OpenWeather 요청에 실패했습니다. API 키, 구독 권한 및 호출 제한을 확인하세요.")
    except (requests.RequestException, ValueError, KeyError, TypeError, IndexError):
        logger.exception("OpenWeather response parsing failed for region=%s", region_code)
        raise HTTPException(502, "OpenWeather 응답을 처리하지 못했습니다.")
    conn = db()
    try:
        with conn.cursor() as cur:
            cur.execute("""INSERT INTO weather_observations
                (region_code, region_name, latitude, longitude, observed_at, collected_at,
                 temperature_c, feels_like_c, humidity_pct, pressure_hpa, wind_speed_ms,
                 rainfall_mm, weather_code, weather_description, source_name, source_url, raw_json)
                VALUES (%s,%s,%s,%s,%s,NOW(),%s,%s,%s,%s,%s,%s,%s,%s,'OpenWeather Current Weather API',
                        'https://openweathermap.org/current',%s)
                ON DUPLICATE KEY UPDATE collected_at=NOW(), temperature_c=VALUES(temperature_c),
                feels_like_c=VALUES(feels_like_c), humidity_pct=VALUES(humidity_pct),
                pressure_hpa=VALUES(pressure_hpa), wind_speed_ms=VALUES(wind_speed_ms),
                rainfall_mm=VALUES(rainfall_mm), weather_code=VALUES(weather_code),
                weather_description=VALUES(weather_description), raw_json=VALUES(raw_json)""",
                (region_code, city["name"], city["lat"], city["lon"], observed_at,
                 current.get("temp"), current.get("feels_like"), current.get("humidity"),
                 current.get("pressure"), payload.get("wind", {}).get("speed"),
                 payload.get("rain", {}).get("1h"), weather.get("id"), weather.get("description"),
                 json.dumps(payload, ensure_ascii=False)))
            conn.commit()
        return {"ok": True, "region_code": region_code, "region_name": city["name"],
                "observed_at_utc": observed_at.isoformat(), "collected_at": datetime.now().isoformat(timespec="seconds"),
                "temperature_c": current.get("temp"), "humidity_pct": current.get("humidity"),
                "weather_description": weather.get("description"),
                "source": "OpenWeather Current Weather API",
                "notice": "도시 중심 좌표의 현재 날씨 스냅샷이며 시·도 전체 평균이나 기후 평년값이 아닙니다."}
    except pymysql.MySQLError:
        conn.rollback()
        logger.exception("OpenWeather DB write failed")
        raise HTTPException(500, "OpenWeather 자료를 MySQL에 저장하지 못했습니다. 마이그레이션 적용 여부를 확인하세요.")
    finally:
        conn.close()

@router.get("/weather")
def get_openweather_history(region_code: str = Query("11"), limit: int = Query(50, ge=1, le=500)):
    if region_code not in CITIES:
        raise HTTPException(422, "지원하지 않는 지역 코드입니다.")
    conn = db()
    try:
        with conn.cursor() as cur:
            cur.execute("""SELECT weather_id, region_code, region_name, observed_at, collected_at,
                temperature_c, feels_like_c, humidity_pct, pressure_hpa, wind_speed_ms,
                rainfall_mm, weather_code, weather_description, source_name, source_url
                FROM weather_observations WHERE region_code=%s
                ORDER BY observed_at DESC LIMIT %s""", (region_code, limit))
            rows = cur.fetchall()
        return {"items": [dict(row) for row in rows], "count": len(rows),
                "notice": "OpenWeather 기록은 호출 시점의 날씨 스냅샷이며 공식 기후 관측 자료와 구분해야 합니다."}
    finally:
        conn.close()

@router.post("/news/articles", status_code=201)
def create_article(payload: ArticleCreate):
    validate_sources(payload.sources)
    conn = db()
    try:
        with conn.cursor() as cur:
            cur.execute("""INSERT INTO news_articles
                (topic, region_code, headline, article_body, facts, sources_json, model_name, review_status)
                VALUES (%s,%s,%s,%s,%s,%s,%s,'pending')""",
                (payload.topic, payload.region_code, payload.headline, payload.article,
                 payload.facts, json.dumps(payload.sources, ensure_ascii=False), payload.model))
            article_id = cur.lastrowid
            cur.execute("SELECT * FROM news_articles WHERE article_id=%s", (article_id,))
            row = cur.fetchone()
            conn.commit()
        row["sources"] = json.loads(row.pop("sources_json"))
        return {"item": row, "notice": "기사 초안은 검수 대기 상태로 저장되며 자동 게시되지 않습니다."}
    except pymysql.MySQLError:
        conn.rollback()
        logger.exception("Article creation failed")
        raise HTTPException(500, "기사 저장에 실패했습니다. 마이그레이션 적용 여부를 확인하세요.")
    finally:
        conn.close()

@router.get("/news/articles")
def list_articles(status: Optional[Literal["pending", "approved", "on_hold"]] = None,
                  limit: int = Query(50, ge=1, le=200)):
    conn = db()
    try:
        with conn.cursor() as cur:
            if status:
                cur.execute("SELECT article_id, topic, region_code, headline, model_name, review_status, reviewer, review_note, created_at, updated_at FROM news_articles WHERE review_status=%s ORDER BY updated_at DESC LIMIT %s", (status, limit))
            else:
                cur.execute("SELECT article_id, topic, region_code, headline, model_name, review_status, reviewer, review_note, created_at, updated_at FROM news_articles ORDER BY updated_at DESC LIMIT %s", (limit,))
            rows = cur.fetchall()
        return {"items": rows, "count": len(rows)}
    finally:
        conn.close()

@router.get("/news/articles/{article_id}")
def get_article(article_id: int):
    conn = db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM news_articles WHERE article_id=%s", (article_id,))
            row = cur.fetchone()
        if not row:
            raise HTTPException(404, "기사를 찾을 수 없습니다.")
        row["sources"] = json.loads(row.pop("sources_json"))
        return {"item": row}
    finally:
        conn.close()


class ArticleEdit(BaseModel):
    topic: str = Field(min_length=3, max_length=180)
    region_code: str = Field(min_length=2, max_length=10)
    headline: str = Field(min_length=3, max_length=220)
    article: str = Field(min_length=30, max_length=16000)
    facts: str = Field(min_length=10, max_length=10000)
    sources: list[str] = Field(min_length=1, max_length=20)

@router.put("/news/articles/{article_id}")
def update_article(article_id: int, payload: ArticleEdit):
    validate_sources(payload.sources)
    conn = db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT article_id FROM news_articles WHERE article_id=%s", (article_id,))
            if not cur.fetchone():
                raise HTTPException(404, "기사를 찾을 수 없습니다.")
            cur.execute("""UPDATE news_articles SET topic=%s, region_code=%s, headline=%s,
                article_body=%s, facts=%s, sources_json=%s, review_status='pending',
                reviewer=NULL, review_note=NULL, reviewed_at=NULL, updated_at=NOW()
                WHERE article_id=%s""",
                (payload.topic, payload.region_code, payload.headline, payload.article,
                 payload.facts, json.dumps(payload.sources, ensure_ascii=False), article_id))
            conn.commit()
        return {"ok": True, "article_id": article_id, "review_status": "pending",
                "notice": "수정된 기사는 재검수가 필요하므로 검수 대기 상태로 전환했습니다."}
    except pymysql.MySQLError:
        conn.rollback()
        logger.exception("Article update failed")
        raise HTTPException(500, "기사 수정에 실패했습니다.")
    finally:
        conn.close()

@router.delete("/news/articles/{article_id}")
def delete_article(article_id: int):
    conn = db()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM news_articles WHERE article_id=%s", (article_id,))
            if cur.rowcount == 0:
                raise HTTPException(404, "기사를 찾을 수 없습니다.")
            conn.commit()
        return {"ok": True, "article_id": article_id, "deleted": True}
    except pymysql.MySQLError:
        conn.rollback()
        logger.exception("Article deletion failed")
        raise HTTPException(500, "기사 삭제에 실패했습니다.")
    finally:
        conn.close()

@router.patch("/news/articles/{article_id}/review")
def review_article(article_id: int, payload: ReviewUpdate):
    conn = db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT article_id FROM news_articles WHERE article_id=%s", (article_id,))
            if not cur.fetchone():
                raise HTTPException(404, "기사를 찾을 수 없습니다.")
            cur.execute("""UPDATE news_articles SET review_status=%s, reviewer=%s,
                review_note=%s, reviewed_at=NOW(), updated_at=NOW() WHERE article_id=%s""",
                (payload.status, payload.reviewer, payload.review_note, article_id))
            cur.execute("""INSERT INTO news_reviews (article_id, status, reviewer, review_note)
                VALUES (%s,%s,%s,%s)""",
                (article_id, payload.status, payload.reviewer, payload.review_note))
            conn.commit()
            cur.execute("SELECT article_id, review_status, reviewer, review_note, reviewed_at FROM news_articles WHERE article_id=%s", (article_id,))
            row = cur.fetchone()
        return {"item": row, "notice": "검수 상태가 저장되었습니다. 승인 상태만 게시 가능 상태로 표시되며 실제 게시 기능은 별도 구현입니다."}
    except pymysql.MySQLError:
        conn.rollback()
        logger.exception("Article review update failed")
        raise HTTPException(500, "검수 상태 저장에 실패했습니다.")
    finally:
        conn.close()
