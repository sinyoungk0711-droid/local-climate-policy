from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import date
from typing import Optional

app = FastAPI(
    title="우리동네 기후·정책 API",
    description="지역 기후·문제·정책 프로토타입 API. 응답은 시연용 예시 데이터입니다.",
    version="0.1.0",
)

# 개발용 CORS 설정입니다. 실제 배포에서는 허용할 도메인만 지정하세요.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEMO_NOTICE = "시연용 예시 데이터입니다. 실제 관측값 또는 공식 정책 정보가 아닙니다."

REGIONS = [
    {"region_code": "11", "region_name": "서울특별시", "level": "시·도"},
    {"region_code": "26", "region_name": "부산광역시", "level": "시·도"},
    {"region_code": "27", "region_name": "대구광역시", "level": "시·도"},
    {"region_code": "29", "region_name": "광주광역시", "level": "시·도"},
    {"region_code": "30", "region_name": "대전광역시", "level": "시·도"},
    {"region_code": "50", "region_name": "제주특별자치도", "level": "시·도"},
]

@app.get("/api/health")
def health():
    return {"status": "ok", "message": "API 서버가 실행 중입니다."}

@app.get("/api/regions")
def get_regions():
    return {"notice": DEMO_NOTICE, "items": REGIONS}

@app.get("/api/climate")
def get_climate(
    region_code: str = Query(default="11", description="지역 코드"),
    metric: str = Query(default="temp", description="temp, rain, heat, tropical"),
    start_year: int = Query(default=2016, ge=1900, le=2100),
    end_year: int = Query(default=2025, ge=1900, le=2100),
):
    if start_year > end_year:
        return {"error": "start_year는 end_year보다 클 수 없습니다."}
    allowed = {"temp", "rain", "heat", "tropical"}
    if metric not in allowed:
        return {"error": f"metric은 {', '.join(sorted(allowed))} 중 하나여야 합니다."}
    return {
        "notice": DEMO_NOTICE,
        "region_code": region_code,
        "metric": metric,
        "unit": {"temp": "°C", "rain": "mm", "heat": "일", "tropical": "일"}[metric],
        "start_year": start_year,
        "end_year": end_year,
        "items": [],
        "message": "실제 데이터베이스 또는 공식 기상 API를 연결하면 items에 자료가 반환됩니다."
    }

@app.get("/api/issues")
def get_issues(region_code: Optional[str] = None, category: Optional[str] = None):
    return {
        "notice": DEMO_NOTICE,
        "filters": {"region_code": region_code, "category": category},
        "items": [
            {"issue_id": 1, "title": "도심 폭염·열섬", "category": "heat", "verification": "근거자료 연결 필요"},
            {"issue_id": 2, "title": "집중호우·침수", "category": "flood", "verification": "근거자료 연결 필요"},
            {"issue_id": 3, "title": "생활권 녹지 접근성", "category": "green", "verification": "근거자료 연결 필요"},
            {"issue_id": 4, "title": "기후 취약계층", "category": "people", "verification": "근거자료 연결 필요"},
        ],
    }

@app.get("/api/policies")
def get_policies(region_code: Optional[str] = None, q: Optional[str] = None):
    return {
        "notice": DEMO_NOTICE,
        "filters": {"region_code": region_code, "q": q},
        "items": [],
        "message": "실제 지자체 정책 자료를 수집해 DB에 저장한 뒤 연결하세요."
    }

@app.get("/api/policies/{policy_id}/metrics")
def get_policy_metrics(policy_id: int):
    return {
        "notice": DEMO_NOTICE,
        "policy_id": policy_id,
        "items": [],
        "message": "전후 비교 지표의 기준 기간, 단위, 출처를 저장한 뒤 연결하세요."
    }

@app.post("/api/suggestions")
def create_suggestion(payload: dict):
    required = ["category", "region_code", "description"]
    missing = [key for key in required if not payload.get(key)]
    if missing:
        return {"ok": False, "error": "필수 항목 누락", "missing": missing}
    if len(str(payload["description"]).strip()) < 10:
        return {"ok": False, "error": "제안 내용은 10자 이상 입력해야 합니다."}
    # 현재는 DB에 저장하지 않는 안전한 시연용 엔드포인트입니다.
    return {
        "ok": True,
        "saved": False,
        "message": "입력 검증 완료. 실제 DB 저장은 아직 구현되지 않았습니다.",
        "received_at": date.today().isoformat(),
    }
