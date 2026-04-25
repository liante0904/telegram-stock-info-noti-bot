# PostgreSQL V2 Lowercase Schema

> V2는 운영 PostgreSQL 테이블을 바로 교체하기 전 검증용으로 만든 소문자 스키마입니다.
> 현재 운영 백본은 `models/PostgreSQLManager.py` + `"TB_SEC_REPORTS"`이고, V2는 검증 완료 후 운영 전환 후보입니다.

---

## 목적

PostgreSQL은 unquoted identifier를 기본적으로 소문자로 처리합니다.
현재 운영 테이블은 `"TB_SEC_REPORTS"`, `"SEC_FIRM_ORDER"`처럼 대문자 quoted identifier를 사용하므로 모든 SQL에서 큰따옴표가 필요합니다.
V2의 목표는 PostgreSQL 표준에 맞게 테이블/컬럼을 소문자 unquoted schema로 바꾸고, Python 애플리케이션 호환성은 단계적으로 유지하는 것입니다.

현재 방향:

- DB 물리 스키마: `tb_sec_reports_v2.sec_firm_order` 같은 소문자 컬럼 사용
- 앱 입력 데이터: 기존 스크래퍼 dict의 `SEC_FIRM_ORDER`, `ARTICLE_TITLE` 등 대문자 키 유지
- 앱 반환 데이터: 기존 메시지/스크래퍼 후처리 호환을 위해 가능한 한 대문자 키 호환 유지
- 운영 전환: 아직 `DB_BACKEND=postgres_v2`는 도입하지 않음

---

## 관련 파일

| 파일 | 역할 |
|---|---|
| `models/PostgreSQLManager.py` | 현재 운영 PostgreSQL manager. `"TB_SEC_REPORTS"` 대문자 quoted schema 사용 |
| `models/PostgreSQLManagerV2.py` | V2 검증용 manager. `tb_sec_reports_v2` 소문자 schema 사용 |
| `scripts/setup_postgresql_v2.py` | V2 테이블 생성 스크립트 |
| `scripts/migrate_to_v2.py` | V1 전체 데이터를 V2로 이관하는 초기 migration 스크립트 |
| `scripts/sync_recent_postgres_to_v2.py` | 최근 N일 V1 데이터를 JSON으로 추출한 뒤 V2에 upsert하고 비교 검증 |
| `utils/PostgreSQL_util.py` | 텔레그램 메시지 SQL/row 변환 유틸. V1/V2 schema profile 지원 |
| `tests/test_report_util.py` | V1/V2 메시지 변환 호환성 테스트 |

---

## 스키마 매핑

운영 V1:

```sql
FROM "TB_SEC_REPORTS"
SELECT "SEC_FIRM_ORDER", "ARTICLE_TITLE", "SAVE_TIME", "TELEGRAM_URL"
```

검증 V2:

```sql
FROM tb_sec_reports_v2
SELECT sec_firm_order, article_title, save_time, telegram_url
```

대표 매핑:

| V1 | V2 |
|---|---|
| `"TB_SEC_REPORTS"` | `tb_sec_reports_v2` |
| `"SEC_FIRM_ORDER"` | `sec_firm_order` |
| `"ARTICLE_BOARD_ORDER"` | `article_board_order` |
| `"FIRM_NM"` | `firm_nm` |
| `"ARTICLE_TITLE"` | `article_title` |
| `"SAVE_TIME"` | `save_time` |
| `"KEY"` | `key` |
| `"TELEGRAM_URL"` | `telegram_url` |
| `"PDF_URL"` | `pdf_url` |
| `"MAIN_CH_SEND_YN"` | `main_ch_send_yn` |
| `"DOWNLOAD_STATUS_YN"` | `download_status_yn` |

주의: `key`는 PostgreSQL 예약어는 아니지만 일반적인 단어라 혼동 여지가 있습니다.
장기적으로는 `report_key`가 더 명확하지만, 현재는 V1 호환성과 마이그레이션 단순성을 위해 `key`를 유지하고 있습니다.

---

## 최근 데이터 검증 절차

운영 V1 테이블을 읽고, 최근 2일치 데이터를 JSON으로 저장한 뒤 V2에 upsert하고 KEY 기준으로 컬럼 값을 비교합니다.
이 스크립트는 `DB_BACKEND`를 변경하지 않으며 운영 테이블에는 쓰지 않습니다.

JSON 추출만 확인:

```bash
python3 scripts/sync_recent_postgres_to_v2.py --dry-run
```

기본 출력:

```text
json/postgres_recent_2d_for_v2_YYYYMMDD_HHMMSS.json
```

이미 추출한 JSON으로 V2 upsert + 비교:

```bash
python3 scripts/sync_recent_postgres_to_v2.py --input json/postgres_recent_2d_for_v2_YYYYMMDD_HHMMSS.json
```

옵션:

```bash
python3 scripts/sync_recent_postgres_to_v2.py --days 3
python3 scripts/sync_recent_postgres_to_v2.py --output /tmp/postgres_recent_for_v2.json --dry-run
python3 scripts/sync_recent_postgres_to_v2.py --input /tmp/postgres_recent_for_v2.json --skip-compare
```

2026-04-25 검증 결과:

```text
PostgreSQL V1 rows exported: 280
V2 upsert complete: inserted=1, updated=279
Compare keys: v1=280, v2=280
PostgreSQL V1 and V2 recent data match by KEY and compared columns.
```

---

## 메시지 변환 유틸

`utils/PostgreSQL_util.py`는 두 종류의 호환성을 지원합니다.

1. SQL 생성 시 V1/V2 schema 선택

```python
from utils.PostgreSQL_util import build_sql_telegram_message_query

query, params = build_sql_telegram_message_query(schema_version="v1")
query, params = build_sql_telegram_message_query(schema_version="v2")
```

기본값은 `schema_version="v1"`입니다.
따라서 기존 운영 호출은 `"TB_SEC_REPORTS"`를 계속 사용합니다.
V2를 명시하면 `tb_sec_reports_v2`와 소문자 컬럼으로 SQL을 생성합니다.

2. Row 변환 시 대문자/소문자 key 모두 지원

```python
from utils.PostgreSQL_util import convert_pg_rows_to_telegram_messages

convert_pg_rows_to_telegram_messages([
    {"SEC_FIRM_ORDER": 11, "ARTICLE_TITLE": "V1 row", "TELEGRAM_URL": "..."}
])

convert_pg_rows_to_telegram_messages([
    {"sec_firm_order": 11, "article_title": "V2 row", "telegram_url": "..."}
])
```

이 처리는 V2 검증 중 소문자 cursor row가 들어와도 텔레그램 메시지 포맷이 깨지지 않게 하기 위한 것입니다.

---

## 현재 리스크

운영 전환 전 반드시 확인해야 할 항목입니다.

- `models/PostgreSQLManagerV2.py`의 `execute_query()`는 현재 raw SQL 전체에 `.lower()`를 적용하는 방식이라 안전하지 않습니다. 문자열 리터럴 `'Y'`, `'N'`, URL, keyword도 바뀔 수 있으므로 운영 전에는 안전한 table/column 매핑 방식으로 교체해야 합니다.
- 일부 코드 경로는 `report_id` 소문자 키를 기대합니다. V2 manager가 모든 select 결과를 대문자 키로 바꾸면 `scraper.py` 후처리, LS/DBfi enrichment 등에서 충돌할 수 있습니다.
- `FirmInfo` 메타 테이블은 아직 `"TBM_SEC_FIRM_INFO"`, `"TBM_SEC_FIRM_BOARD_INFO"` 대문자 quoted schema를 사용합니다. V2 범위를 리포트 테이블에만 둘지, 메타 테이블까지 소문자화할지 결정해야 합니다.
- `DB_BACKEND=postgres_v2`는 아직 도입하지 않았습니다. 현재 검증은 명시 스크립트와 직접 import 기반으로만 수행합니다.
- `key` 컬럼명 유지 여부를 운영 전 확정해야 합니다.

---

## 권장 작업 순서

1. `scripts/sync_recent_postgres_to_v2.py --days 2`를 반복 실행해 최근 운영 데이터 정합성을 확인합니다.
2. `utils/PostgreSQL_util.py`처럼 V1/V2를 명시 선택하는 코드는 기본값을 V1로 유지합니다.
3. V2 manager의 `execute_query()`에서 전체 `.lower()`를 제거하고 안전한 identifier 변환 함수로 교체합니다.
4. `daily_select_data`, `daily_update_data`, `fetch_all_empty_telegram_url_articles`, `fetch_keyword_reports`를 V1/V2 같은 입력 fixture로 비교합니다.
5. 전환 직전까지 운영 `models/db_factory.py`는 V1을 유지합니다.
6. 충분히 검증된 뒤 별도 단계에서만 `DB_BACKEND=postgres_v2` 또는 V2 manager 교체를 논의합니다.

---

## 검증 명령

```bash
python3 -m py_compile scripts/sync_recent_postgres_to_v2.py
python3 -m py_compile utils/PostgreSQL_util.py tests/test_report_util.py
uv run pytest tests/test_report_util.py -q
```

현재 기대 결과:

```text
tests/test_report_util.py: 4 passed
```
