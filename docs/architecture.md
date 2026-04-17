# Architecture & Roadmap

> 이 문서는 프로젝트의 현재 구조, 설계 결정 배경, 진행 중인 리팩토링 방향을 기록합니다.
> 작업 시작 전 이 문서를 먼저 읽고, 작업 완료 후 변경 내용을 반영해 주세요.

---

## 현재 스택 (2026-04-17 기준)

### 인프라 (`~/infra/`)

- `~/infra/docker-compose.yml` — portal, nginx, postgresql 등 include하는 루트 컴포즈
- `main-postgres` — `127.0.0.1:5432` 바인딩 (외부 차단, 2026-04-17 적용)
- `main-pgadmin` — https://ssh-oci.duckdns.org/pgadmin/ (oauth2-proxy 인증)
- DB 계정 현황:
  - `admin` — 비밀번호 회전 완료 (2026-04-17)
  - `ssh_reports_hub` — 비밀번호 회전 완료 (2026-04-17)
- 시크릿 관리: `~/secrets/{infra,ssh-reports-scraper,ssh-reports-hub}/secrets.json` (chmod 600)
- **PostgreSQL 비번은 `infra/secrets.json`이 단일 진실 소스** (`POSTGRES_SSH_REPORTS_HUB_PASSWORD`)
- `.env` 재생성: `python3 ~/secrets/generate_env.py` (전체) / `python3 ~/secrets/generate_env.py scraper` (개별)
- 비번 변경 절차: `infra/secrets.json` 수정 → `generate_env.py` 실행 → 컨테이너 `down && up`
- `ssh-reports-hub-fastAPI` JWT 하드코딩 제거 → git history rewrite 완료

```
스크래퍼 (scraper.py)
    │
    ▼
SQLite3  ──────────────────────────────────► Oracle ATP (ORDS REST API)
(telegram.db)                                        │
    │                                                ▼
    └──── sync ──► Oracle ATP (TB_SEC_REPORTS)    프론트엔드 (Read-only)
```

### 주요 구성 요소

| 구성 요소 | 역할 |
|---|---|
| `scraper.py` | 27개 증권사 스크래핑 스케줄러 |
| `modules/` | 증권사별 스크래퍼 (LS, 삼성, KB 등) |
| `models/SQLiteManager.py` | SQLite CRUD |
| `models/FirmInfo.py` | 증권사/게시판 메타 정보 관리 |
| `models/ConfigManager.py` | 환경별 설정 중앙화 (싱글톤) |
| `models/WebScraper.py` | HTTP/Selenium 공통 스크래퍼 |
| `scheduler_keyword_alert.py` | 키워드 알림 (PostgreSQL 사용 중) |

---

## 아키텍처 결정 기록 (ADR)

### ADR-001: FirmInfo를 하드코딩 배열에서 DB 기반으로 전환

- **상태:** 완료 (2026-04-17)
- **배경:** `models/FirmInfo.py`에 증권사 27개, 게시판 수십 개가 배열로 하드코딩되어 있어 증권사 추가/변경 시 코드 배포가 필요했음
- **결정:** `TBM_SEC_FIRM_INFO`, `TBM_SEC_FIRM_BOARD_INFO` 테이블에서 동적 로드
- **효과:** 증권사/게시판 변경이 DB 수정만으로 가능

### ADR-002: ConfigManager 도입

- **상태:** 완료 (2026-04-17)
- **배경:** DB 경로, 봇 토큰, 채널 ID 등이 각 파일에 분산되어 환경별(dev/prod) 분기 불가
- **결정:** `models/ConfigManager.py` 싱글톤으로 `secrets.json` + 환경변수 통합 관리
- **secrets.json 경로:** `~/secrets/ssh-reports-scraper/secrets.json`
- **구조:**
  ```json
  {
    "common": { "TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET": "..." },
    "dev":  { "DB_PATH": "~/sqlite3/telegram_dev.db", "CHANNEL_ID": "..." },
    "prod": { "DB_PATH": "~/sqlite3/telegram.db",     "CHANNEL_ID": "..." }
  }
  ```

### ADR-003: 스크래핑 대상 URL 숨김 처리 (Ghost Mode)

- **상태:** 진행 예정
- **배경:** 공개 GitHub 레포이므로 증권사 API 엔드포인트가 노출되어 있음
- **결정:** `TBM_SEC_FIRM_BOARD_INFO`에 `TARGET_URL` 컬럼 추가 → FirmInfo를 통해 로드
- **단기 처리:** SQLite → PostgreSQL 전환 전까지는 `secrets.json`의 `urls` 섹션에서 관리
  ```json
  {
    "urls": {
      "BNKfn_23": ["https://...", "https://..."],
      "HANA_3":   ["https://...", ...]
    }
  }
  ```
- **각 모듈 변경 방향:**
  ```python
  # 기존
  TARGET_URL = "REMOVED"
  # 변경 후
  TARGET_URL = config.get_urls("BNKfn_23")[0]
  ```

### ADR-004: SQLite → PostgreSQL 전환

- **상태:** 진행 중 (2026-04-17)
- **배경:**
  - SQLite는 서버 SSH 접속 없이 관리 불가
  - 프론트엔드 검색 기능 추가 시 Oracle ATP에 증권사/게시판 테이블을 또 만들어야 하는 중복 문제
  - Oracle ATP ORDS도 걷어내고 단일 DB로 통합하려는 방향
- **결정:** PostgreSQL로 완전 전환 (SQLite 원장 유지 방식은 sync 복잡도 문제로 기각)
- **목표 아키텍처:**
  ```
  스크래퍼 → PostgreSQL ◄── PostgREST ◄── 프론트엔드 (Read-only)
                 │
              pgAdmin4 (웹 GUI)
  ```
- **전환 시 처리 항목:**
  - [x] PostgreSQL DDL 적용 (`data_main_daily_send`, `TBM_SEC_FIRM_INFO`, `TBM_SEC_FIRM_BOARD_INFO`, `hankyungconsen_research`, `naver_research`)
  - [x] 데이터 이전 완료 (270,914 rows → `data_main_daily_send`, 28 firms, 120 boards)
  - [x] `models/PostgreSQLManager.py` 확장 — SQLiteManager 인터페이스와 호환
  - [x] `scripts/migrate_sqlite_to_postgres.py` 작성 (idempotent, batch 5000)
  - [ ] `scraper.py` 및 모듈에서 SQLiteManager → PostgreSQLManager 교체
  - [ ] FirmInfo DB 경로를 PostgreSQL로 전환
  - [ ] `TARGET_URL` 컬럼 추가 (ADR-003 통합)
  - [ ] Oracle ATP / ORDS 제거

### ADR-005: Oracle ATP 제거

- **상태:** ADR-004 이후 진행
- **배경:** ADR-004 완료 시 Oracle ATP의 역할(REST API 제공)을 PostgREST가 대체
- **프론트엔드 영향:** Read-only 쿼리만 하므로 엔드포인트 URL 교체 수준으로 마이그레이션 가능
  - ORDS: `GET /ords/{schema}/data_main_daily_send?firm_nm=eq.삼성증권`
  - PostgREST: `GET /reports?firm_nm=eq.삼성증권` (파라미터 방식 동일)

---

## 브랜치 전략

| 브랜치 | 용도 |
|---|---|
| `main` | 프로덕션. CI/CD로 `:prod`, `:latest` 이미지 자동 빌드/배포 |
| `feat/*` | 기능 개발. 완료 후 main에 머지 |

- 현재 활성 브랜치: `feat/ghost-mode-config-refactor` (ADR-003 작업용)
- dev 전용 Docker 이미지는 별도 운영하지 않음 (로컬 테스트 후 main 머지)

---

## CI/CD

- `main` 푸시 → GitHub Actions → GHCR `:prod`, `:latest`, `:sha-*` 빌드
- 서버에서 `APP_ENV=prod` → `docker-compose pull` → `:prod` 이미지로 컨테이너 재시작
- `scheduler_keyword_alert.py` 관련 파일 변경 시에만 해당 컨테이너 재배포 (선택적 배포)

---

## 작업 우선순위

- [x] **인프라** `ssh_reports_hub` DB 계정 비밀번호 교체 + 앱 env 반영
- [ ] **ADR-003** `secrets.json` URL 관리 + ConfigManager `get_urls()` 추가 + 모듈 교체
- [x] **ADR-004** PostgreSQL DDL 적용 및 데이터 이전 (270,914 rows)
- [x] **ADR-004** `PostgreSQLManager` SQLiteManager 호환 인터페이스 구현
- [ ] **ADR-004** `scraper.py` 및 모듈에서 PostgreSQLManager로 교체
- [ ] **ADR-004** `FirmInfo` PostgreSQL 기반으로 전환
- [ ] **ADR-005** PostgREST 배포 + 프론트엔드 엔드포인트 교체
- [ ] **ADR-005** Oracle ATP 제거
