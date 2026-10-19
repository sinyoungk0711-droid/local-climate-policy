# 우리동네 기후·정책 — 실행 가능한 프로토타입

지역기후·지역문제·지역정책을 연결하는 7개 화면 웹서비스의 초급자용 프로젝트입니다.

## 포함된 기능
- 7개 화면: 메인, 지역 기후, 지역문제 지도, 문제 상세, 지역정책, 정책 효과 비교, 시민참여
- 지역 선택과 기후 지표 선택
- Chart.js 기반 그래프
- Leaflet 기반 인터랙티브 지도(인터넷 연결 필요)
- 정책 검색 및 분류 필터
- 정책 전후 지표 비교
- 시민 제안 폼 입력 검증
- FastAPI API 골격
- MySQL용 `database/schema.sql`

## 데이터 주의
프론트엔드에 포함된 값은 **화면 기능 확인용 예시 데이터**입니다. 실제 관측값, 공식 정책 현황, 정책 효과로 인용하거나 게시하지 마세요. 실제 운영 전 기상청·KOSIS·공공데이터포털 및 지자체 공식 자료로 교체하고 출처·기준일·단위를 검수해야 합니다.

## 1. 프론트엔드 실행 (가장 쉬운 방법)
1. ZIP 압축을 풉니다.
2. `frontend/index.html` 파일을 브라우저에서 엽니다.
3. 지도 타일과 Chart.js를 사용하므로 인터넷 연결이 필요합니다.

권장 방법은 VS Code에서 프로젝트 폴더를 열고 Live Server 확장으로 `frontend/index.html`을 실행하는 것입니다.

## 2. FastAPI 실행
Windows 11 PowerShell에서 프로젝트 루트로 이동합니다.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload
```

API 문서는 `http://127.0.0.1:8000/docs` 에서 확인할 수 있습니다.

Python 3.12가 없다면 `py --list`로 설치된 버전을 확인하고, 호환되는 Python 버전을 사용하세요.

## 3. MySQL 설정
1. MySQL에서 `database/schema.sql`을 실행합니다.
2. 프로젝트 루트의 `.env.example`을 `.env`로 복사합니다.
3. `.env`에 DB 접속 정보를 입력합니다.
4. API 코드의 DB 연결은 기본 예시이며, 실제 DB 연결 및 CRUD 기능은 다음 개발 단계에서 구현해야 합니다.

현재 API는 `/api/health`, `/api/regions`, `/api/climate`, `/api/issues`, `/api/policies` 등 기본 엔드포인트의 동작 예시를 제공합니다. 데이터베이스 연결 및 공식 API 연동은 아직 연결되지 않은 골격입니다.

## 폴더 구조
```text
local-climate-policy/
├── frontend/
│   ├── index.html
│   ├── css/styles.css
│   └── js/app.js
├── backend/
│   ├── app/main.py
│   └── requirements.txt
├── database/schema.sql
├── .env.example
└── README.md
```

## 실제 서비스 전 점검
- 공식 데이터의 이용 조건과 API 호출 한도
- 지역 코드와 관측 지점의 매핑
- 데이터 누락·중복·단위·기준 기간
- 정책 계획/시행/완료 상태 검증
- 정책 전후 비교에서 인과관계를 과장하지 않는지
- 시민 제안 개인정보 및 파일 업로드 보안
- API 키·DB 비밀번호를 GitHub에 올리지 않는지
