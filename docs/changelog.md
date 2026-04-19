# 프로젝트 변천사

> `master` 브랜치 원본 히스토리 + `main` 현재 코드 기반으로 재구성한 기술 변천 기록.

---

## 1기 — 단일 파일 시대 (2021)
**커밋:** `7e6a4eb` · `main.py` 3,680줄

### 구조
```
main.py (3,680줄)
  ├── 상수 하드코딩 (토큰, 채널ID, URL 전부)
  ├── EBEST_checkNewArticle()
  ├── EBEST_parse()
  ├── ShinHanInvest_checkNewArticle()
  ├── ... (증권사별 함수 93개)
  └── main() — 순차 반복 호출
requirements.txt
Procfile (Heroku 배포)
```

### 특징
- **DB:** MySQL (pymysql) → Heroku ClearDB
- **실행:** 동기(sync), `time.sleep()` 기반 폴링
- **배포:** Heroku (Procfile)
- **설정:** 소스 내 하드코딩 (`TELEGRAM_BOT_TOKEN = ""` 형태로 빈칸 → 실제값은 로컬에서만)
- **스크래핑:** `requests` + `BeautifulSoup`, 단순 HTML 파싱

### 한계
- 증권사 추가 시 `main.py` 직접 수정 필수
- 테스트/운영 분리 불가
- 한 파일에 모든 로직 → 유지보수 불가

---

## 2기 — 모듈 분리 + SQLite 전환 (2024~2026-03)
**커밋:** `d2fbea9` · 2026-03-18 누적 업데이트

### 구조
```
scraper.py          ← main.py 역할 (스케줄러)
modules/
  ├── LS_0.py
  ├── ShinHanInvest_1.py
  ├── ... (증권사별 30개 모듈)
models/
  ├── SQLiteManager.py   ← DB 추상화
  ├── FirmInfo.py        ← 증권사/게시판 메타 (하드코딩 배열)
  ├── WebScraper.py      ← HTTP 공통
  ├── OracleManager.py   ← Oracle ATP 연동
  └── SecretKey.py       ← 시크릿 로드
backup/              ← 레거시 보관
local_worker/        ← 로컬 테스트용
```

### 변경 내용
- **DB:** MySQL → **SQLite** (`telegram.db`) — 서버 로컬 운영으로 전환
- **구조:** `main.py` 3,680줄 → `scraper.py` + 모듈 30개로 분리
- **배포:** Heroku → 자체 서버 직접 실행
- **Oracle ATP:** 프론트엔드 Read-only 제공용으로 병행 운영
- **FirmInfo:** 증권사/게시판 정보를 Python 배열로 하드코딩

### 한계
- 증권사 URL이 각 모듈에 하드코딩 (공개 레포 노출 위험)
- FirmInfo 변경 시 코드 배포 필요
- 환경별(dev/prod) 설정 분리 없음
- 로깅 = `print()`

---

## 3기 — Docker + 로깅 + async (2026-04-05 ~ 04-13)

### 3-1. Docker화 (2026-04-05, `16d5116`)
```
Dockerfile
docker-compose.yml      ← dev/prod 분리
.github/workflows/      ← GHCR 자동 빌드/배포
```
- GitHub Actions → GHCR `:prod`, `:latest` 자동 빌드
- `uv` 패키지 매니저 도입 (pip → uv)
- ARM64 (Oracle Cloud) 대응

### 3-2. PostgreSQL 키워드 알림 (2026-04-06, `4938948`)
- `scheduler_keyword_alert.py` 분리
- 키워드 알림용 PostgreSQL 첫 도입 (스크래퍼 본체는 아직 SQLite)

### 3-3. Loguru 로깅 (2026-04-09, `9a2442c`)
- `print()` 전면 → `loguru.logger`
- 날짜별 자동 로테이션 (`/log/YYYYMMDD/`)
- 에러 레벨 정밀화 (초기 재시도는 WARNING 이하로 억제)

### 3-4. Async 전환 (2026-04-13, `c49e2e3`)
- 전체 스크래퍼 `async/await` 리팩토링
- `asyncio` 기반 병렬 스크래핑

---

---

## 5기 — 품질 관리 및 자동 검증 (2026-04-19 ~ 현재)

### 5-1. pytest 자동화 테스트 도입 (ADR-006)
- **기본 검증:** `tests/test_db_logic.py` — DB 연결 및 최근 7일 데이터 적재 여부 자동 체크
- **CI/CD 연동:** GitHub Actions에서 빌드 전 테스트 수행 단계 추가
- **도구:** `pytest`, `pytest-asyncio` 기반 비동기 테스트 환경 구축

### 5-2. 데이터 추출 및 감사 도구 고도화
- `tests/test_db_export.py` — 운영 데이터를 JSON으로 추출하여 테스트 Fixture로 활용할 수 있는 기반 마련
- `tests/test_db_compare_all.py` — SQLite ↔ PostgreSQL 27만 건 전수 조사 도구 도입
- **성과:** PostgreSQL 데이터 마이그레이션 정합성 100% 달성 (271,038 rows 일치 확인)

### 5-3. 텔레그램 통합 시스템 알림 도입 (ADR-007)
- `traceback` 모듈 연동을 통한 상세 에러 위치 텔레그램 발송 기능 추가
- 별도 외부 서비스 가입 없이 텔레그램만으로 디버깅 가능한 환경 구축

### 4-1. ConfigManager 도입 (ADR-002, `3e89282`)
```python
# 기존: 각 파일에 분산
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# 변경: 싱글톤 ConfigManager
from models.ConfigManager import config
token = config.BOT_TOKEN
```
- `~/secrets/ssh-reports-scraper/secrets.json` 단일 소스
- `generate_env.py`로 앱별 `.env` 자동 생성
- dev/prod 환경 분기 통합

### 4-2. FirmInfo DB 전환 (ADR-001, `3e89282`)
```python
# 기존: Python 배열 하드코딩
FIRM_NAME = ("LS증권", "신한투자", ...)

# 변경: DB에서 동적 로드
# TBM_SEC_FIRM_INFO, TBM_SEC_FIRM_BOARD_INFO 테이블
```

### 4-3. Ghost Mode — URL 숨김 (ADR-003, `6160b75`)
```python
# 기존: 각 모듈에 하드코딩 (공개 레포 노출)
TARGET_URL = "https://www.bnkfn.co.kr/research/analysingCompany.jspx"

# 변경: secrets.json + 환경변수 주입
TARGET_URL = config.get_urls("BNKfn_23")[0]
# → .env: URLS_BNKfn_23=["https://..."]
```
- git 히스토리 전체 rewrite (`git filter-repo`)로 과거 URL 흔적 제거

### 4-4. PostgreSQL 전면 전환 (ADR-004, `83b69ad`)
```
SQLite (telegram.db)
    ↓ migrate (270,914 rows)
PostgreSQL (TB_SEC_REPORTS)
    ↑
PostgreSQLManager (SQLiteManager 호환 인터페이스)
db_factory.get_db()  ← DB_BACKEND 환경변수로 무중단 전환
```
- `DB_BACKEND=sqlite` (기본) → `DB_BACKEND=postgres`로 롤백 없이 전환 가능
- pgAdmin4 웹 GUI (Tailscale VPN 경유)

---

## 아키텍처 변천 요약

```
[2021]
main.py → MySQL (Heroku) → 텔레그램

[2024~2026-03]
scraper.py + modules/ → SQLite → 텔레그램
                      → Oracle ATP → 프론트엔드

[2026-04 현재]
scraper.py + modules/ → PostgreSQL ← pgAdmin
  (async, loguru,       (TB_SEC_REPORTS)
   ConfigManager,
   ghost mode)
                      → 텔레그램
```

---

## DB 변천

| 시기 | DB | 이유 |
|---|---|---|
| 2021 | MySQL (Heroku ClearDB) | 무료 클라우드 DB |
| 2024 | SQLite | 서버 이전, 단순화 |
| 2026-04 (병행) | Oracle ATP | 프론트엔드 REST API |
| 2026-04 (현재) | PostgreSQL | Oracle 의존 제거, 단일 DB 통합 |

## 증권사 수

| 시기 | 증권사 수 |
|---|---|
| 2021 | 12개 |
| 2026-03 | 28개 |
| 2026-04 (현재) | 28개 (DB 관리) |
