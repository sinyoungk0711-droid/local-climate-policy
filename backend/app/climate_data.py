import os
from datetime import datetime
import requests
import pymysql
from pymysql.cursors import DictCursor
from fastapi import APIRouter, HTTPException, Query

router = APIRouter()
STATIONS = {
    "11": ("서울특별시", "108"), "26": ("부산광역시", "159"),
    "27": ("대구광역시", "143"), "29": ("광주광역시", "156"),
    "30": ("대전광역시", "133"), "50": ("제주특별자치도", "184"),
}
SOURCE_NAME = "기상청 기상자료개방포털 ASOS 일자료"
SOURCE_URL = "https://data.kma.go.kr/"
KMA_URL = "https://apis.data.go.kr/1360000/AsosDalyInfoService/getWthrDataList"

def connect_db():
    missing = [k for k in ("DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD") if not os.getenv(k)]
    if missing:
        raise HTTPException(503, "MySQL 환경변수가 없습니다: " + ", ".join(missing))
    try:
        return pymysql.connect(
            host=os.getenv("DB_HOST", "127.0.0.1"), port=int(os.getenv("DB_PORT", "3306")),
            user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME", "local_climate_policy"), charset="utf8mb4",
            cursorclass=DictCursor, autocommit=False,
        )
    except pymysql.MySQLError as exc:
        raise HTTPException(503, "MySQL 연결 실패: " + str(exc)[:200])

@router.get("/api/climate")
def climate(region_code: str = "11", metric: str = "temp",
            start_year: int = Query(2016, ge=1900, le=2100),
            end_year: int = Query(2025, ge=1900, le=2100)):
    if region_code not in STATIONS or metric not in ("temp", "rain", "heat", "tropical") or start_year > end_year:
        raise HTTPException(422, "지역·지표·연도 조건을 확인하세요.")
    conn = connect_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT region_id FROM regions WHERE region_code=%s", (region_code,))
            region = cur.fetchone()
            if not region:
                raise HTTPException(503, "database/schema.sql을 먼저 실행하세요.")
            cur.execute("""SELECT YEAR(observation_date) year, metric_code,
                AVG(metric_value) avg_value, SUM(metric_value) sum_value
                FROM climate_observations WHERE region_id=%s AND observation_date BETWEEN %s AND %s
                GROUP BY YEAR(observation_date), metric_code""",
                (region["region_id"], f"{start_year}-01-01", f"{end_year}-12-31"))
            rows = cur.fetchall()
        grouped = {}
        for row in rows:
            grouped.setdefault(int(row["year"]), {})[row["metric_code"]] = row
        code = {"temp":"tavg", "rain":"rain_mm", "heat":"heat_day", "tropical":"tropical_day"}[metric]
        label = {"temp":"연평균기온", "rain":"연강수량", "heat":"폭염일수(최고기온 33°C 이상)", "tropical":"열대야일수(최저기온 25°C 이상)"}[metric]
        unit = {"temp":"°C", "rain":"mm", "heat":"일", "tropical":"일"}[metric]
        items = []
        for year in range(start_year, end_year + 1):
            row = grouped.get(year, {}).get(code)
            raw = (row.get("avg_value") if metric == "temp" else row.get("sum_value")) if row else None
            items.append({"year": year, "value": round(float(raw), 2 if metric == "temp" else 1) if raw is not None else None})
        exists = any(x["value"] is not None for x in items)
        return {"region_code":region_code, "region_name":STATIONS[region_code][0],
                "station_code":STATIONS[region_code][1], "metric":metric, "metric_label":label,
                "unit":unit, "items":items, "source":{"name":SOURCE_NAME,"url":SOURCE_URL},
                "data_status":"official_db" if exists else "no_data",
                "notice":"MySQL에 저장된 기상청 ASOS 일자료입니다." if exists else "자료가 없습니다. POST /api/climate/collect로 먼저 수집하세요."}
    finally:
        conn.close()

@router.post("/api/climate/collect")
def collect(start_date: str = Query(..., description="YYYYMMDD"),
            end_date: str = Query(..., description="YYYYMMDD"),
            region_code: str | None = None):
    key = os.getenv("KMA_SERVICE_KEY") or os.getenv("DATA_GO_KR_SERVICE_KEY")
    if not key:
        raise HTTPException(503, "공공데이터포털에서 기상청 ASOS 일자료 API 키를 발급받아 KMA_SERVICE_KEY에 설정하세요.")
    try:
        start = datetime.strptime(start_date, "%Y%m%d").date()
        end = datetime.strptime(end_date, "%Y%m%d").date()
    except ValueError:
        raise HTTPException(422, "날짜는 YYYYMMDD 형식이어야 합니다.")
    if start > end or (end - start).days > 3660:
        raise HTTPException(422, "날짜 범위가 잘못되었거나 10년을 초과했습니다.")
    codes = [region_code] if region_code else list(STATIONS)
    if any(c not in STATIONS for c in codes):
        raise HTTPException(422, "지원하지 않는 지역 코드입니다.")
    conn = connect_db()
    count = 0
    days = 0
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT source_id FROM data_sources WHERE source_name=%s AND source_url=%s LIMIT 1", (SOURCE_NAME, SOURCE_URL))
            src = cur.fetchone()
            source_id = src["source_id"] if src else None
            if source_id is None:
                cur.execute("INSERT INTO data_sources (source_name,source_url,license_note,checked_at) VALUES (%s,%s,%s,NOW())",
                            (SOURCE_NAME,SOURCE_URL,"기상자료개방포털의 자료별 이용 조건과 출처 표기 기준 준수"))
                source_id = cur.lastrowid
            for code in codes:
                cur.execute("SELECT region_id FROM regions WHERE region_code=%s", (code,))
                region = cur.fetchone()
                if not region:
                    raise HTTPException(503, "지역 기본 데이터가 없습니다. database/schema.sql을 실행하세요.")
                page = 1
                while True:
                    params = {"serviceKey":key,"pageNo":page,"numOfRows":999,"dataType":"JSON",
                              "dataCd":"ASOS","dateCd":"DAY","startDt":start.strftime("%Y%m%d"),
                              "endDt":end.strftime("%Y%m%d"),"stnIds":STATIONS[code][1]}
                    try:
                        response = requests.get(KMA_URL, params=params, timeout=45)
                        response.raise_for_status()
                        payload = response.json()
                    except (requests.RequestException, ValueError) as exc:
                        raise HTTPException(502, "기상청 API 요청 실패: " + str(exc)[:200])
                    try:
                        body = payload["response"]["body"]
                        records = body.get("items", {}).get("item", [])
                        if isinstance(records, dict): records = [records]
                    except (KeyError, TypeError):
                        msg = payload.get("response", {}).get("header", {}).get("resultMsg", "응답 형식 오류")
                        raise HTTPException(502, "기상청 API 응답 오류: " + str(msg))
                    if not records: break
                    for item in records:
                        try: day = datetime.strptime(item.get("tm",""), "%Y-%m-%d").date()
                        except ValueError: continue
                        vals = [("tavg",item.get("avgTa"),"°C"),("tmin",item.get("minTa"),"°C"),
                                ("tmax",item.get("maxTa"),"°C"),("rain_mm",item.get("sumRn"),"mm")]
                        try:
                            if item.get("maxTa") not in (None,"") and float(item["maxTa"]) >= 33: vals.append(("heat_day",1,"일"))
                            if item.get("minTa") not in (None,"") and float(item["minTa"]) >= 25: vals.append(("tropical_day",1,"일"))
                        except (TypeError,ValueError): pass
                        for metric_code, raw, unit in vals:
                            if raw in (None,""): continue
                            try: value = float(raw)
                            except (TypeError,ValueError): continue
                            cur.execute("""INSERT INTO climate_observations
                                (region_id,source_id,station_code,metric_code,observation_date,aggregation_period,metric_value,unit,quality_flag)
                                VALUES (%s,%s,%s,%s,%s,'daily',%s,%s,'raw_kma')
                                ON DUPLICATE KEY UPDATE metric_value=VALUES(metric_value),unit=VALUES(unit),quality_flag='raw_kma'""",
                                (region["region_id"],source_id,STATIONS[code][1],metric_code,day,value,unit))
                            count += 1
                        days += 1
                    total = body.get("totalCount")
                    if total is None or page * 999 >= int(total) or len(records) < 999: break
                    page += 1
            conn.commit()
        return {"ok":True,"source":SOURCE_NAME,"source_url":SOURCE_URL,
                "date_range":{"start":start.isoformat(),"end":end.isoformat()},
                "regions":[STATIONS[c][0] for c in codes],"api_days_processed":days,
                "metric_rows_upserted":count,"message":"공식 ASOS 일자료를 MySQL에 저장했습니다. 결측일은 0으로 대체하지 않았습니다."}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
