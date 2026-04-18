# SSH Reports Scraper

국내 28개 증권사 리서치 보고서를 자동 수집해 텔레그램 채널로 발송하는 실서비스 봇입니다.

![Python](https://img.shields.io/badge/Python-3.12-blue)
![Docker](https://img.shields.io/badge/Docker-GHCR-2496ED)
![PostgreSQL](https://img.shields.io/badge/DB-PostgreSQL-336791)
![License](https://img.shields.io/badge/license-MIT-green)

---

## 주요 기능

- **28개 증권사 리서치 자동 수집** — 30분 간격 스케줄링, 증권사별 독립 모듈
- **텔레그램 채널 실시간 발송** — 중복 방지, 마크다운 포맷
- **키워드 알림** — 사용자 등록 키워드 매칭 시 개인 DM 발송

> 뉴스 수집(네이버), 한경컨센서스는 관심사 분리 원칙에 따라 별도 컨테이너/레포로 독립 운영 중

---

## 아키텍처

```
스케줄러 (scraper.py)
    │
    ├── modules/ (28개 증권사별 async 스크래퍼)
    │       │
    │       └── WebScraper (HTTP / Selenium)
    │
    ▼
PostgreSQL (TB_SEC_REPORTS)
    │
    ├── pgAdmin4 (웹 GUI)
    └── 텔레그램 채널 발송
```

**DB 전환 전략:** `DB_BACKEND` 환경변수 하나로 SQLite ↔ PostgreSQL 무중단 전환 가능 (롤백 30초)

---

## 기술 스택

| 영역 | 기술 |
|---|---|
| Language | Python 3.12, uv |
| Scraping | aiohttp, BeautifulSoup4, Selenium (headless) |
| Scheduler | APScheduler |
| Database | PostgreSQL (운영), SQLite (로컬) |
| Logging | Loguru (날짜별 자동 로테이션) |
| Infra | Docker, GitHub Actions, GHCR |
| Secrets | secrets.json + generate_env.py → .env 자동 생성 |

---

## 수집 대상 (28개 증권사)

LS증권 · 신한투자증권 · NH투자증권 · 하나증권 · KB증권 · 삼성증권 · 상상인증권 · 신영증권 · 미래에셋증권 · 현대차증권 · 키움증권 · DS투자증권 · 유진투자증권 · 한국투자증권 · 다올투자증권 · 토스증권 · 리딩투자증권 · 대신증권 · iM증권 · DB금융투자 · 메리츠증권 · 한화투자증권 · 흥국증권 · BNK투자증권 · 교보증권 · IBK투자증권 · SK증권 · 유안타증권

---

## 프로젝트 구조

```
ssh-reports-scraper/
├── scraper.py                  # 메인 스케줄러
├── scheduler_keyword_alert.py  # 키워드 알림 스케줄러
├── modules/                    # 증권사별 스크래퍼 (28개)
├── models/
│   ├── ConfigManager.py        # 환경별 설정 싱글톤
│   ├── FirmInfo.py             # 증권사/게시판 메타 (DB 기반)
│   ├── PostgreSQLManager.py    # PostgreSQL CRUD
│   ├── SQLiteManager.py        # SQLite CRUD (호환 인터페이스)
│   ├── db_factory.py           # DB_BACKEND 기반 팩토리
│   └── WebScraper.py           # HTTP/Selenium 공통
├── docs/
│   ├── architecture.md         # ADR 및 설계 결정 기록
│   └── changelog.md            # 2021~현재 변천사
└── scripts/
    └── migrate_sqlite_to_postgres.py
```

---

## 실행 방법

### Docker (운영)

```bash
# 환경변수 생성
python3 ~/secrets/generate_env.py scraper

# 배포
docker compose pull && docker compose up -d
```

### 로컬

```bash
uv sync
cp .env.example .env  # 환경변수 설정
uv run scraper.py
```

### 환경변수 주요 항목

```env
APP_ENV=prod
DB_BACKEND=postgres          # sqlite | postgres
POSTGRES_HOST=localhost
POSTGRES_PASSWORD=...
TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET=...
TELEGRAM_CHANNEL_ID_REPORT_ALARM=...
```

---

## CI/CD

`main` 브랜치 푸시 → GitHub Actions → GHCR `:prod` / `:latest` 빌드 → SSH 자동 배포

관련 파일 변경 시에만 선택적 재배포 (`scheduler_keyword_alert.py` 등)

---

## 설계 문서

- [Architecture & ADR](docs/architecture.md) — 설계 결정 배경 및 로드맵
- [Changelog](docs/changelog.md) — 2021년 단일 파일 → 현재까지 변천사

---

## 유의사항

본 프로젝트는 개인 투자 정보 확인 목적으로 제작되었습니다. 리서치 자료의 저작권은 각 증권사에 있으며 상업적 이용을 금지합니다.
