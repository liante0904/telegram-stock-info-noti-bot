# Architecture & Roadmap

> 이 문서는 프로젝트의 현재 구조, 설계 결정 배경, 진행 중인 리팩토링 방향을 기록합니다.
> 작업 시작 전 이 문서를 먼저 읽고, 작업 완료 후 변경 내용을 반영해 주세요.

---

## 현재 스택 (2026-04-26 기준)

### 인프라 (`~/infra/`)

- `~/infra/docker-compose.yml` — portal, nginx, postgresql 등 include하는 루트 컴포즈
- `main-postgres` — `127.0.0.1:5432` 바인딩 (외부 차단)
- `main-pgadmin` — https://oci-infra.tailb32978.ts.net/pgadmin/ (Tailscale VPN 경유)
- DB 계정 현황:
  - `admin` — 비밀번호 회전 완료 (2026-04-17)
  - `ssh_reports_hub` — 비밀번호 회전 완료 (2026-04-17)
- 시크릿 관리: `~/secrets/{infra,ssh-reports-scraper,ssh-reports-hub}/secrets.json` (chmod 600)
- **PostgreSQL 비번은 `infra/secrets.json`이 단일 진실 소스** (`POSTGRES_SSH_REPORTS_HUB_PASSWORD`)
- `.env` 재생성: `python3 ~/secrets/generate_env.py` (전체) / `python3 ~/secrets/generate_env.py scraper` (개별)
- 비번 변경 절차: `infra/secrets.json` 수정 → `generate_env.py` 실행 → 컨테이너 `down && up`

```
스크래퍼 (scraper.py)
    │
    ▼
PostgreSQL (TB_SEC_REPORTS)      ← DB_BACKEND=postgres (2026-04-21 재전환 완료)
    │
    ├── 텔레그램 채널 발송
    └── FastAPI ORDS 호환 API 조회

SQLite (telegram.db)는 롤백/최근 동기화 소스로 유지
※ Oracle ATP / ORDS → ADR-005에서 제거 예정
```

### 주요 구성 요소

| 구성 요소 | 역할 |
|---|---|
| `scraper.py` | 28개 증권사 스크래핑 스케줄러 |
| `modules/` | 증권사별 스크래퍼 (LS, 삼성, KB 등) |
| `models/db_factory.py` | DB_BACKEND 기반 팩토리 (SQLite ↔ PostgreSQL) |
| `models/PostgreSQLManager.py` | PostgreSQL CRUD |
| `models/PostgreSQLManagerV2.py` | PostgreSQL 소문자 스키마 검증용 CRUD |
| `models/SQLiteManager.py` | SQLite CRUD (호환 인터페이스) |
| `models/FirmInfo.py` | 증권사/게시판 메타 정보 (DB 기반 동적 로드) |
| `models/ConfigManager.py` | 환경별 설정 중앙화 (싱글톤) |
| `models/WebScraper.py` | HTTP/Selenium 공통 스크래퍼 |
| `scheduler_keyword_alert.py` | 키워드 알림 (PostgreSQL) |

---

## 아키텍처 결정 기록 (ADR)

### ADR-001: FirmInfo를 하드코딩 배열에서 DB 기반으로 전환

- **상태:** 완료 (2026-04-17)
- **배경:** `models/FirmInfo.py`에 증권사 28개, 게시판 수십 개가 배열로 하드코딩되어 있어 증권사 추가/변경 시 코드 배포가 필요했음
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
    "prod": { "DB_PATH": "~/sqlite3/telegram.db",     "CHANNEL_ID": "...", "DB_BACKEND": "postgres" },
    "urls": { "BNKfn_23": ["https://..."], ... }
  }
  ```

### ADR-003: 스크래핑 대상 URL 숨김 처리 (Ghost Mode)

- **상태:** 완료 (2026-04-18)
- **배경:** 공개 GitHub 레포이므로 증권사 API 엔드포인트가 노출되어 있음
- **결정:** `secrets.json`의 `urls` 섹션에서 관리 → `generate_env.py`가 `URLS_{key}` 환경변수로 주입
- **git 히스토리:** `git filter-repo`로 과거 커밋의 URL 흔적 전체 제거 완료
  ```python
  # 기존: 하드코딩
  TARGET_URL = "https://www.bnkfn.co.kr/..."
  # 변경 후: 환경변수 경유
  TARGET_URL = config.get_urls("BNKfn_23")[0]
  ```
- **장기 방향:** `TBM_SEC_FIRM_BOARD_INFO.TARGET_URL` 컬럼으로 DB 통합 (ADR-004 완료 후)

### ADR-004: SQLite → PostgreSQL 전환

- **상태:** 완료 (2026-04-21 재전환)
- **배경:**
  - SQLite는 서버 SSH 접속 없이 관리 불가 → PostgreSQL 전환 시도
  - Oracle ATP ORDS도 걷어내고 단일 DB로 통합하려는 방향
- **결정:** PostgreSQL을 운영 DB로 사용하고, SQLite는 롤백/최근 동기화 소스로 유지
- **롤백:** `DB_BACKEND=sqlite` 환경변수 변경 후 재시작으로 즉시 롤백 가능
- **현황:**
  - [x] PostgreSQL DDL 적용 및 데이터 이전 완료 (100% consistency)
  - [x] `db_factory.get_db()` 기반 무중단 전환 인터페이스 완료
  - [x] 2026-04-20 SQLite 롤백 이력 있음
  - [x] 2026-04-21 최근 2일 SQLite 데이터를 JSON export 후 PostgreSQL upsert
  - [x] 2026-04-21 `DB_BACKEND=postgres` 운영 재전환 완료
  - [x] 2026-04-24 DS투자증권 `TELEGRAM_URL`은 PostgreSQL trigger로 `https://ssh-oci.netlify.app/share?id={report_id}` 자동 보정
  - [ ] PostgreSQL V2 소문자 스키마 검증 진행 중 (`docs/postgresql-v2.md`)
- **2026-04-21 재전환 검증:**
  ```bash
  uv run python scripts/sync_recent_sqlite_to_postgres.py --days 2 --output /tmp/sqlite_recent_2d_reports.json
  DB_BACKEND=postgres uv run pytest tests/test_db_logic.py -q
  ```
  - SQLite export: 282 rows (`SAVE_TIME >= 2026-04-20`)
  - PostgreSQL upsert: inserted 70, updated 212
  - Final consistency check: sqlite 282 keys, postgres 282 keys

### ADR-004-B: PostgreSQL V2 소문자 스키마 검증

- **상태:** 검증 중 (2026-04-25)
- **배경:** 운영 PostgreSQL 테이블이 `"TB_SEC_REPORTS"`, `"SEC_FIRM_ORDER"`처럼 대문자 quoted identifier를 사용해 SQL 작성과 유지보수 비용이 큼
- **결정:** 운영 V1은 유지하되, `tb_sec_reports_v2` 소문자 schema를 별도 테이블로 검증
- **원칙:** `DB_BACKEND=postgres_v2`는 아직 도입하지 않고, 운영 전환 전까지 명시 스크립트로만 검증
- **문서:** [PostgreSQL V2 Lowercase Schema](postgresql-v2.md)
- **최근 검증:** `scripts/sync_recent_postgres_to_v2.py`로 최근 2일 V1 280건을 JSON export → V2 upsert → KEY/컬럼 비교 통과

### ADR-004-C: PostgreSQLManager 책임 통합

- **상태:** 진행 중 (2026-04-26)
- **배경:** PostgreSQL 전환 이후에도 일부 DB 접근 로직이 모듈/유틸 단에 남아 있어 dedup 기준과 조회 로직이 분산돼 있었음
- **결정:** `PostgreSQLManager`에 공통 조회 책임을 점진적으로 모으고, 스크래퍼는 manager 인터페이스만 사용하도록 정리
- **최근 반영:**
  - DBfi 중복 제거용 기존 KEY 조회를 `PostgreSQLManager` 경유로 통합
  - 여러 경로에 흩어진 raw query를 manager 메서드로 옮기는 리팩토링 진행
- **의도:** URL 컬럼 정리와 lowercase schema 전환 전에 DB 접근면을 줄여 변경 파급을 통제

### ADR-004-D: URL 컬럼 의미 정규화

- **상태:** 설계 확정, 단계적 적용 예정 (2026-04-26)
- **배경:** `ATTACH_URL`, `ARTICLE_URL`, `TELEGRAM_URL`, `PDF_URL`가 모듈별로 서로 다른 의미로 채워져 메시지 발송, 다운로드, 보강 로직에서 fallback 충돌이 발생함
- **결정:**
  - `KEY`: 중복 식별자. 당장 스키마 의미 변경 없이 유지
  - `TELEGRAM_URL`: 텔레그램 발송 메시지의 단일 대표 링크
  - `PDF_URL`: PDF 다운로드 및 외부 archiver 연동용 링크
  - `ARTICLE_URL`: 원문 게시글 또는 상세 페이지 링크
  - `ATTACH_URL`: deprecated. 읽기/쓰기 경로를 제거한 뒤 최종 드랍
- **원칙:**
  - 메시지 생성 로직은 장기적으로 `TELEGRAM_URL` 단일 컬럼만 신뢰
  - 다운로드 로직은 장기적으로 `PDF_URL` 단일 컬럼을 우선 사용
  - 신규 모듈/수정 모듈은 `ATTACH_URL`에 새 의미를 부여하지 않음
- **문서:** [URL Column Semantics](url-semantics.md)

### ADR-004-E: DBfi endpoint 외부화

- **상태:** 완료 (2026-04-26)
- **배경:** DBfi 스크래퍼는 base URL뿐 아니라 viewer/auth/document endpoint 조합도 코드에 남아 있어 Ghost Mode 원칙을 완전히 만족하지 못했음
- **결정:** `modules/DBfi_19.py`의 endpoint 조합 규칙을 `~/secrets/ssh-reports-scraper/secrets.json`의 `urls.DBfi_19` 구조로 이동
- **효과:**
  - 코드에는 endpoint key 이름만 남고 실제 URL 문자열은 외부 시크릿으로 격리
  - 과거 `modules/DBfi_19.py` 히스토리의 DBfi URL 흔적도 추가 `git filter-repo`로 정리
- **주의:** repo rewrite 이후 원격은 force push로만 동기화 가능하며, `origin` remote가 자동 제거될 수 있음

### ADR-005: Oracle ATP 제거

- **상태:** ADR-004 이후 진행
- **배경:** ADR-004 완료로 Oracle ATP의 REST API 역할을 PostgREST가 대체 가능
- **프론트엔드 영향:** Read-only 쿼리만 하므로 엔드포인트 URL 교체 수준으로 마이그레이션 가능
  - ORDS: `GET /ords/{schema}/data_main_daily_send?firm_nm=eq.삼성증권`
  - PostgREST: `GET /reports?firm_nm=eq.삼성증권`

### ADR-006: 테스트 코드 도입

- **상태:** 진행 중 (2026-04-19)
- **배경:** PostgreSQL 전환 및 증권사 모듈 증가로 인해 코드 변경 시 기존 기능의 회귀(Regression) 방지 및 무결성 보증 필요
- **결정:** `pytest` 기반의 자동화 테스트 도입
- **범위:**
  - **DB Logic:** `db_factory`, `SQLiteManager` / `PostgreSQLManager` 연결 및 기본 쿼리 검증
  - **Data Integrity:** 필수 필드 누락 여부 및 최근 수집 데이터 존재 여부 체크
  - **Data Audit Tools:** SQLite ↔ PostgreSQL 전수 비교 및 동기화 검증 도구 (`test_db_compare_all.py`)
  - **Scrapers (예정):** HTML Fixture를 활용한 오프라인 파싱 검증
- **도구:** `pytest`, `pytest-asyncio`
- **프로세스:** 로컬 실행 (`uv run pytest`) → GitHub Actions 자동 검증 → 배포 (CI/CD 연동)

### ADR-007: 텔레그램 통합 시스템 알림 도입

- **상태:** 완료 (2026-04-19)
- **배경:** 복잡한 외부 모니터링 도구 대신 익숙한 텔레그램을 통해 즉각적인 장애 인지 및 디버깅 정보 확보 필요
- **결정:** 텔레그램 기반의 상세 에러 알림 시스템 구축
- **구현:** 
  - `utils/telegram_util.py`에 `send_system_alert` 비동기 함수 추가
  - `traceback` 모듈을 활용하여 에러 스택 트레이스를 텔레그램 메시지에 포함
- **효과:** 별도 도구 가입 없이 텔레그램만으로 장애 위치(파일, 라인) 파악 가능

---

## 브랜치 전략

| 브랜치 | 용도 |
|---|---|
| `main` | 프로덕션. CI/CD로 `:prod`, `:latest` 이미지 자동 빌드/배포 |
| `feat/*` | 기능 개발. 완료 후 main에 머지 |
| `legacy` | 구버전 master 보존 (참고용) |

---

## CI/CD

- `main` 푸시 → GitHub Actions → GHCR `:prod`, `:latest`, `:sha-*` 빌드
- 서버에서 `APP_ENV=prod` → `docker-compose pull` → `:prod` 이미지로 컨테이너 재시작
- `scheduler_keyword_alert.py` 관련 파일 변경 시에만 해당 컨테이너 재배포 (선택적 배포)

---

## 작업 우선순위

- [x] **인프라** `ssh_reports_hub` DB 계정 비밀번호 교체 + 앱 env 반영
- [x] **ADR-003** Ghost Mode — URL secrets.json 관리 + 환경변수 주입
- [x] **ADR-004** PostgreSQL DDL 적용 및 데이터 이전 (271,038 rows)
- [x] **ADR-004** `PostgreSQLManager` SQLiteManager 호환 인터페이스 구현
- [x] **ADR-004** `db_factory.get_db()` 팩토리 도입
- [x] **ADR-004** `FirmInfo` PostgreSQL 기반으로 전환
- [x] **ADR-004** 프로덕션 `DB_BACKEND=sqlite` 롤백 완료 (2026-04-20)
- [x] **ADR-004** 최근 2일 SQLite→PostgreSQL 동기화 후 `DB_BACKEND=postgres` 재전환 (2026-04-21)
- [x] **ADR-004** DBfi endpoint 전체 외부화 + 관련 히스토리 정리 (2026-04-26)
- [ ] **ADR-004** `TARGET_URL` 컬럼 추가 (ADR-003 통합)
- [ ] **ADR-004** URL 컬럼 의미 정규화 1차 (`ATTACH_URL` read path 제거)
- [ ] **ADR-004-B** PostgreSQLManager로 DB 접근면 추가 통합
- [ ] **ADR-004-D** `TELEGRAM_URL`/`PDF_URL` 단일 목적 fallback 재설계

- [ ] **ADR-005** PostgREST 배포 + 프론트엔드 엔드포인트 교체
- [ ] **ADR-005** Oracle ATP 제거
- [ ] **ADR-006** pytest 기반 테스트 코드 도입
