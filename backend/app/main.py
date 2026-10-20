import json
import os
import requests
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import date
from .climate_data import router as climate_router
from typing import Optional

load_dotenv()

app = FastAPI(
    title="우리동네 기후·정책 API",
    description="지역 기후·문제·정책 프로토타입 API. 응답은 시연용 예시 데이터입니다.",
    version="0.1.0",
)

# 개발용 CORS 설정입니다. 실제 배포에서는 허용할 도메인만 지정하세요.
app.include_router(climate_router)

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


class NewsDraftRequest(BaseModel):
    topic: str = Field(min_length=3, max_length=180)
    region: str = Field(min_length=2, max_length=80)
    audience: str = Field(default="일반 독자", max_length=100)
    format: str = Field(default="설명형 뉴스 기사", max_length=100)
    facts: str = Field(min_length=40, max_length=8000)
    sources: list[str] = Field(min_length=1, max_length=20)

@app.post("/api/news/draft")
def create_news_draft(payload: NewsDraftRequest):
    """Generate an unapproved draft from user-supplied facts; never auto-publish."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="서버의 OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
    for source in payload.sources:
        if not source.startswith(("https://", "http://")):
            raise HTTPException(status_code=422, detail="출처 URL은 http:// 또는 https://로 시작해야 합니다.")

    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    source_list = "\n".join("- " + source for source in payload.sources)
    system_prompt = (
        "당신은 근거 중심의 한국어 뉴스 편집자다. 입력된 Fact Sheet만 사실 근거로 사용한다. "
        "출처 URL의 본문을 실제로 열람했다고 주장하지 말고, 제공되지 않은 수치·인용·사실을 만들지 않는다. "
        "확인되지 않은 주장은 제외하거나 추가 확인이 필요하다고 명시한다. "
        "상관관계를 인과관계로 단정하지 않는다. 기사 초안은 사람의 검수를 거쳐야 한다. "
        'JSON 객체 {"headline":"기사 제목","article":"기사 본문"}만 반환한다.'
    )
    user_prompt = (
        f"주제: {payload.topic}\n지역: {payload.region}\n대상 독자: {payload.audience}\n"
        f"기사 형식: {payload.format}\n\nFact Sheet:\n{payload.facts}\n\n"
        f"제공된 원자료 URL(주소 목록일 뿐, 본문을 자동 검증한 것은 아님):\n{source_list}\n\n"
        "사실에 충실한 한국어 기사 초안을 작성하라. 핵심 수치와 기준 기간을 정확히 유지하고, "
        "본문 끝에 '편집자 확인 사항'을 짧게 덧붙여 사람이 원문에서 재확인해야 할 점을 제시하라."
    )
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.3,
            },
            timeout=60,
        )
        if response.status_code >= 400:
            detail = "OpenAI API 요청이 거부되었습니다. 모델 접근 권한, API 사용량 및 키 설정을 확인하세요."
            try:
                detail = response.json().get("error", {}).get("message", detail)
            except ValueError:
                pass
            raise HTTPException(status_code=502, detail=detail)
        result = response.json()["choices"][0]["message"]["content"]
        draft = json.loads(result)
        if not draft.get("headline") or not draft.get("article"):
            raise ValueError("headline/article missing")
        return {
            "headline": str(draft["headline"])[:220],
            "article": str(draft["article"])[:16000],
            "model": model,
            "status": "draft",
            "notice": "AI 초안입니다. 원자료 대조와 사람의 최종 승인이 필요하며 자동 게시되지 않았습니다.",
        }
    except HTTPException:
        raise
    except requests.Timeout:
        raise HTTPException(status_code=504, detail="기사 생성 시간이 초과되었습니다. 잠시 후 다시 시도하세요.")
    except (requests.RequestException, ValueError, KeyError, IndexError, TypeError):
        raise HTTPException(status_code=502, detail="기사 초안을 생성하지 못했습니다. 서버 로그와 API 응답을 확인하세요.")
