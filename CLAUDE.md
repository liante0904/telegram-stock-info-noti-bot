# CLAUDE.md — ssh-reports-scraper

> **LLM에게:** 이 문서는 세션 시작 시 반드시 읽고, 작업 전에 아키텍처를 이해하세요.
> 자세한 결정 배경은 `docs/architecture.md`를 참조하세요.

---

## 프로젝트 개요

28개 증권사 리서치 리포트를 스크래핑하여 PostgreSQL에 저장 후 텔레그램 채널로 배신하는 시스템.

```
scraper.py (스케줄러)
  └── modules/{증권사명}_{번호}.py  (증권사별 스크래퍼)
        └── models/db_factory.get_db()  → PostgreSQL (tbl_sec_reports)
              └── utils/telegram_util.py  → 텔레그램 발송
```

---

## 필독: 작업 전 체크리스트

1. **URL을 코드에 직접 쓰지 말 것** — 모든 TARGET_URL은 `~/secrets/ssh-reports-scraper/secrets.json`의 `urls` 섹션에서 관리 (Ghost Mode / ADR-003)
2. **DB는 반드시 `db_factory.get_db()` 사용** — `SQLiteManager` / `PostgreSQLManager`를 직접 인스턴스화하지 않음
3. **`secrets.json`에 불필요한 키를 추가하지 말 것** — `common` 섹션은 `generate_env.py`가 실제로 쓰는 키만 존재
4. **`OracleManager` / Oracle 관련 코드를 건드리지 말 것** — ADR-005에서 제거 예정, 현재 비활성
5. **.env는 자동 생성** — `python3 ~/secrets/generate_env.py scraper`로 생성. 직접 편집하지 않음
6. **`.env` 갱신 원칙** — 워크스페이스별 `.env`는 `~/secrets/generate_env.py scraper`가 단일 진실 소스이며, 변경이 필요하면 먼저 `~/secrets/ssh-reports-scraper/secrets.json` 또는 `~/secrets/infra/secrets.json`를 확인할 것

---

## 핵심 파일 요약

| 파일 | 역할 |
|---|---|
| `scraper.py` | 메인 스케줄러 · 진입점 |
| `modules/{Name}_{N}.py` | 증권사별 스크래퍼 (N=0~27) |
| `models/ConfigManager.py` | 환경설정 싱글톤. `config.get_urls(key)`로 URL 취득 |
| `models/db_factory.py` | `DB_BACKEND` 환경변수로 SQLite/PostgreSQL 전환 |
| `models/PostgreSQLManager.py` | 운영 DB (tbl_sec_reports) CRUD |
| `models/FirmInfo.py` | 증권사 메타 정보 — DB에서 동적 로드 |
| `utils/telegram_util.py` | 텔레그램 전송 유틸리티 |
| `~/secrets/ssh-reports-scraper/secrets.json` | 시크릿 단일 진실 소스 |
| `~/secrets/generate_env.py` | secrets.json → .env 생성 스크립트 |

---

## secrets.json 구조

```json
{
  "common": {
    "TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET": "...",
    "TELEGRAM_CHANNEL_ID_REPORT_ALARM": "...",
    ...
  },
  "dev":  { "DB_PATH": "...", "BOT_TOKEN": "...", "CHANNEL_ID": "..." },
  "prod": { "DB_PATH": "...", "BOT_TOKEN": "...", "CHANNEL_ID": "...", "DB_BACKEND": "postgres" },
  "urls": {
    "LS_0": ["https://..."],
    "Samsung_5": ["https://...", "https://..."],
    ...
  }
}
```

- `common`에는 `generate_env.py`가 `.env`에 기록하는 키만 존재
- `urls` 섹션이 Ghost Mode의 핵심 — 스크래핑 대상 URL은 여기에만 기재
- `generate_env.py`가 `URLS_{key}` 환경변수로 변환 → `config.get_urls(key)`로 취득

---

## URL 처리 방식 (Ghost Mode)

```python
# 올바른 방법: secrets.json의 urls 섹션 경유
from models.ConfigManager import config
TARGET_URLS = config.get_urls("Samsung_5")   # list 반환

# 잘못된 방법: 하드코딩 (공개 레포지토리이므로 금지)
TARGET_URL = "https://www.samsungpop.com/..."
```

**예외 (코드에 직접 써도 되는 URL):**
- API 응답에서 받은 경로를 기본 도메인에 붙이는 경우 (예: `f"https://www.bnkfn.co.kr{base_path}/{file_name}"`)
- 이는 "구성"이지 "설정"이 아니므로, 변경 빈도가 낮고 노출해도 무방한 케이스

---

## 새 스크래퍼 추가 절차

1. `modules/{Name}_{N}.py` 생성 — 명명 규칙: `{이름}_{연번}.py` (예: `Heungkuk_28.py`)
2. `~/secrets/ssh-reports-scraper/secrets.json`의 `urls` 섹션에 URL 추가
3. `python3 ~/secrets/generate_env.py scraper`로 `.env` 재생성
4. `scraper.py`의 `async_functions` 또는 `sync_funcs` 리스트에 함수 추가
5. `FirmInfo`에서 참조한다면 DB의 `TBM_SEC_FIRM_INFO` / `TBM_SEC_FIRM_BOARD_INFO`에 행 추가

---

## 환경변수 & DB 백엔드

| 변수 | 값 | 의미 |
|---|---|---|
| `DB_BACKEND` | `postgres` | 운영 (PostgreSQL) |
| `DB_BACKEND` | `sqlite` | 롤백용 |
| `ENV` | `prod` / `dev` | ConfigManager 환경 분기 |

롤백 방법: `.env`의 `DB_BACKEND=sqlite`로 변경 → 컨테이너 재시작

---

## 아키텍처 결정 기록 (ADR) 요약

| ADR | 내용 | 상태 |
|---|---|---|
| ADR-001 | FirmInfo를 DB 동적 로드로 전환 | 완료 |
| ADR-002 | ConfigManager로 시크릿 일원 관리 | 완료 |
| ADR-003 | Ghost Mode — URL을 secrets.json으로 격리 | 완료 |
| ADR-004 | SQLite → PostgreSQL 마이그레이션 (DB_BACKEND=postgres) | 완료 |
| ADR-004B | PostgreSQL V2 소문자 스키마 검증 중 | 검증 중 |
| ADR-005 | Oracle ATP 제거 | 미착수 — OracleManager 건드리지 말 것 |
| ADR-006 | pytest 테스트 도입 | 진행 중 |
| ADR-007 | 텔레그램 시스템 알림 | 완료 |

상세 내용: `docs/architecture.md`

---

## 하면 안 되는 것

- `secrets.json`의 `common`에 `API_URL_*`, `*_BASE`, `*_LIST_PATH`, `*_PARAM_*` 같은 분해된 URL 키를 추가하지 말 것 (Gemini가 추가해서 문제가 된 전례 있음)
- `OracleManager`를 새 코드에서 참조하지 말 것
- `.env`를 직접 편집하지 말 것 — `generate_env.py`로 재생성할 것
- `.env`가 어긋나 보이면 먼저 `~/secrets/generate_env.py scraper`를 다시 실행하고, 그 다음 `POSTGRES_*` / `SQLITE_DB_PATH`가 기대값인지 확인할 것
- `docs/architecture.md`의 ADR에 반하는 설계 변경을 하지 말 것
- `PostgreSQLManagerV2`를 `DB_BACKEND=postgres_v2`로 운영에 사용하지 말 것 (검증 전용)
