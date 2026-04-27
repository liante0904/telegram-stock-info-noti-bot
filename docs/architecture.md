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
PostgreSQL (TB_SEC_REPORTS)      ← DB_BACKEND=postgres (운영 중)
    │
    ├── 텔레그램 채널 발송
    └── FastAPI / PostgREST 조회
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

### ADR-002: ConfigManager 도입
- **상태:** 완료 (2026-04-17)

### ADR-003: 스크래핑 대상 URL 숨김 처리 (Ghost Mode)
- **상태:** 완료 (2026-04-18)

### ADR-004: SQLite → PostgreSQL 전환
- **상태:** 완료 (2026-04-21)
- **현황:**
  - [x] PostgreSQL DDL 적용 및 데이터 이전 완료 (100% consistency)
  - [x] `db_factory.get_db()` 기반 무중단 전환 인터페이스 완료
  - [x] 2026-04-21 `DB_BACKEND=postgres` 운영 전환 및 안정화 완료
  - [x] 2026-04-24 DS투자증권 `TELEGRAM_URL`은 PostgreSQL trigger로 자동 보정
  - [x] 2026-04-26 URL 컬럼 정규화 (`ATTACH_URL` 코드 전수 제거) 완료
  - [ ] PostgreSQL V2 소문자 스키마 검증 진행 중 (`docs/postgresql-v2.md`)

### ADR-004-D: URL 컬럼 의미 정규화 및 ATTACH_URL 제거
- **상태:** 완료 (2026-04-26)
- **배경:** `ATTACH_URL`이 모듈별로 모호하게 사용되어 메시지 발송 및 다운로드 로직에서 충돌 발생
- **결정:** 전체 28개 스크래퍼 모듈 및 DB Manager에서 `ATTACH_URL` 참조 전면 제거
- **결과:** `TELEGRAM_URL`(대표), `PDF_URL`(파일), `ARTICLE_URL`(상세) 삼각 체계로 정규화 완료
- **문서:** [URL Column Semantics](url-semantics.md)

### ADR-004-E: DBfi endpoint 외부화
- **상태:** 완료 (2026-04-26)
- **배경:** DBfi 스크래퍼의 API 조합 규칙이 코드에 노출되어 Ghost Mode 원칙 위배
- **결정:** 모든 endpoint 조합 규칙을 `secrets.json`으로 이관하고 관련 히스토리 정리 완료

---

## 작업 우선순위

- [x] **인프라** PostgreSQL 운영 전환 및 데이터 정합성 검증 (100%)
- [x] **ADR-004-D** URL 컬럼 정규화 1차 (`ATTACH_URL` 코드 전수 제거)
- [x] **ADR-004-E** DBfi endpoint 전체 외부화
- [x] **LS 로직 강화** PDF 탐색 범위 확대 (+/- 10일) 및 Fallback URL 복구 가동
- [ ] **ADR-004-B** PostgreSQL Manager 책임 추가 통합
- [ ] **ADR-005** PostgREST 배포 + 프론트엔드 엔드포인트 교체
- [ ] **ADR-005** Oracle ATP 제거
- [ ] **ADR-006** pytest 기반 테스트 코드 도입
