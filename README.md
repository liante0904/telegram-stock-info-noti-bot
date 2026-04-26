# SSH Reports Scraper

> 국내 28개 증권사 리서치 보고서를 실시간 수집·분류·발송하는 개인 운영 자동화 시스템 (2021~)

![Python](https://img.shields.io/badge/Python-3.12-blue)
![Docker](https://img.shields.io/badge/Docker-GHCR-2496ED)
![PostgreSQL](https://img.shields.io/badge/DB-PostgreSQL-336791)
![Uptime](https://img.shields.io/badge/운영기간-4년-brightgreen)

---

## 어떤 프로젝트인가

증권사 리서치 보고서는 각사 홈페이지에 분산돼 있고, 공식 통합 API가 없다.  
이걸 하나의 파이프라인으로 묶어 텔레그램 채널에 자동 발송하는 시스템을 2021년부터 혼자 설계·운영 중이다.

**단순 크롤러가 아니라 4년간 실제 사용하면서 진화한 운영 시스템이다.**

---

## 현재 상태

- 28개 증권사, 30분 간격 자동 수집
- Oracle Cloud (OCI) 서버에서 Docker 컨테이너로 24/7 운영 중
- GitHub Actions → GHCR → SSH 자동 배포 (main 브랜치 푸시 시)
- AI 요약 (Gemini), 키워드 알림 독립 프로세스로 병렬 운영

---

## 기술적으로 풀었던 문제들

### 1. 28개 사이트, 28가지 방식

증권사마다 HTML 구조, 인증 방식, 페이지네이션이 전부 다르다.  
공통 인터페이스(`WebScraper`)를 설계하고 증권사별 모듈이 이를 구현하는 구조로 확장성을 확보했다.  
일부는 Selenium 헤드리스, 일부는 aiohttp 비동기, 일부는 세션 쿠키 유지가 필요하다.

### 2. 3680줄 단일 파일 → 모듈 시스템

2021년 첫 버전은 `main.py` 한 파일에 모든 증권사 로직이 들어있었다.  
운영하면서 기능을 추가할수록 유지보수가 불가능해졌고, 2024년에 전면 모듈 분리를 단행했다.  
현재는 증권사 추가 시 모듈 파일 하나만 작성하면 된다.

### 3. SQLite → PostgreSQL 무중단 전환

운영 중인 서비스의 DB를 바꾸는 건 까다롭다.  
`DB_BACKEND` 환경변수 하나로 SQLite ↔ PostgreSQL을 즉시 전환할 수 있는 팩토리 패턴을 설계했다.  
이 덕분에 실서버에서 PostgreSQL로 전환하고 문제 발생 시 SQLite로 롤백하는 데 30초면 충분하다.

```python
# db_factory.py
def get_db():
    backend = os.getenv("DB_BACKEND", "sqlite")
    if backend == "postgres":
        return PostgreSQLManager()
    return SQLiteManager()
```

### 4. 시크릿 관리

API 키, DB 비밀번호, 수집 대상 URL(경쟁 우위 정보)을 소스코드에서 완전히 분리했다.  
`secrets.json` → `generate_env.py` → `.env` 파이프라인으로 컨테이너에 환경변수로 주입한다.  
수집 URL은 Git 히스토리 포함 전체 삭제(`git filter-repo`)하고 컨테이너 런타임에만 노출된다.

### 5. 중복 제거 전략

같은 보고서가 여러 번 수집될 수 있다.  
`KEY` 컬럼(보고서 고유 식별자)에 `ON CONFLICT DO UPDATE` 를 적용해 DB 레벨에서 멱등성을 보장한다.  
애플리케이션 코드에서 중복 체크 없이 그냥 upsert하면 된다.

---

## 아키텍처

```
[GitHub Actions]
      │ push to main
      ▼
[GHCR :prod 이미지 빌드]
      │ SSH 자동 배포
      ▼
[Oracle Cloud (OCI)]
  ├── nginx (리버스 프록시 + SSL)
  ├── main-scraper (30분 스케줄, 28개 증권사)
  ├── keyword-alert (키워드 매칭 → 개인 DM)
  └── PostgreSQL + pgAdmin4
```

**관심사 분리:** 뉴스(네이버), 한경컨센서스는 별도 레포·컨테이너로 독립 운영 중

---

## 기술 스택

| 영역 | 기술 |
|---|---|
| Language | Python 3.12, uv |
| Scraping | aiohttp, BeautifulSoup4, Selenium (headless) |
| Scheduler | APScheduler |
| Database | PostgreSQL (운영), SQLite (로컬/폴백) |
| AI | Gemini API (리포트 요약) |
| Logging | Loguru (날짜별 자동 로테이션) |
| Infra | Docker, GitHub Actions, GHCR, Oracle Cloud |

---

## 프로젝트 구조

```
ssh-reports-scraper/
├── scraper.py                      # 메인 스케줄러
├── scheduler_keyword_alert.py      # 키워드 알림 스케줄러
├── modules/                        # 증권사별 스크래퍼 (28개)
├── models/
│   ├── ConfigManager.py            # 환경별 설정 싱글톤
│   ├── FirmInfo.py                 # 증권사/게시판 메타 (DB 기반)
│   ├── PostgreSQLManager.py        # PostgreSQL CRUD
│   ├── SQLiteManager.py            # SQLite CRUD (동일 인터페이스)
│   ├── db_factory.py               # DB_BACKEND 팩토리
│   └── WebScraper.py               # HTTP/Selenium 공통 추상화
├── docs/
│   ├── architecture.md             # ADR 및 설계 결정 기록
│   ├── changelog.md                # 2021~현재 변천사
│   ├── url-semantics.md            # URL 컬럼 의미 및 ATTACH_URL 퇴역 계획
│   └── postgresql-v2.md            # PostgreSQL 소문자 스키마 검증 메모
└── scripts/
    └── migrate_sqlite_to_postgres.py
```

---

## 수집 대상 (28개 증권사)

LS증권 · 신한투자증권 · NH투자증권 · 하나증권 · KB증권 · 삼성증권 · 상상인증권 · 신영증권 · 미래에셋증권 · 현대차증권 · 키움증권 · DS투자증권 · 유진투자증권 · 한국투자증권 · 다올투자증권 · 토스증권 · 리딩투자증권 · 대신증권 · iM증권 · DB금융투자 · 메리츠증권 · 한화투자증권 · 흥국증권 · BNK투자증권 · 교보증권 · IBK투자증권 · SK증권 · 유안타증권

---

## 운영 이력

| 시기 | 상태 |
|---|---|
| 2021 | `main.py` 단일 파일, MySQL, Heroku |
| 2024 | 모듈 분리, SQLite, Docker 전환 |
| 2026.04 | PostgreSQL, GitHub Actions CI/CD, AI 요약 |

전체 변천사 → [docs/changelog.md](docs/changelog.md)  
설계 결정 배경 → [docs/architecture.md](docs/architecture.md)  
URL 컬럼 정리 기준 → [docs/url-semantics.md](docs/url-semantics.md)  
PostgreSQL V2 소문자 스키마 → [docs/postgresql-v2.md](docs/postgresql-v2.md)

---

## 실행

```bash
# Docker (운영)
python3 ~/secrets/generate_env.py scraper
docker compose pull && docker compose up -d

# 로컬
uv sync && cp .env.example .env
uv run scraper.py
```

---

*본 프로젝트는 개인 투자 정보 확인 목적으로 제작되었습니다. 리서치 자료의 저작권은 각 증권사에 있으며 상업적 이용을 금지합니다.*
