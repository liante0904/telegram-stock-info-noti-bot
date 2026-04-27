# 프로젝트 변천사

> `master` 브랜치 원본 히스토리 + `main` 현재 코드 기반으로 재구성한 기술 변천 기록.

---

## 운영 변경 기록

### 2026-04-26 — ATTACH_URL 전수 제거 및 LS 로직 강화 완료

- **URL 컬럼 정규화 완료**: 전체 28개 증권사 스크래퍼 모듈 및 `PostgreSQLManager`, `SQLiteManager`에서 `ATTACH_URL` 참조를 전면 제거했습니다.
- **데이터 검증**: 주의 대상(LS, 신한, 메리츠 등) 전수 조사 결과 고유 데이터 손실 0건을 확인하고 마이그레이션 종료를 선언했습니다.
- **LS증권 PDF 획득률 개선**: `msg.ls-sec.co.kr` 서버의 날짜 탐색 범위를 기존 +/- 2일에서 **+/- 10일**로 확대하여 정적 PDF 링크 확보 성공률을 극대화했습니다.
- **Fallback URL 복구 자동화**: `run/fix_ls_db.py`를 통해 기존 `upload/` 방식의 Fallback URL들을 정적 URL로 일괄 복구하는 프로세스를 가동했습니다.
- **스키마 관리 체계화**: 실제 운영 중인 PostgreSQL DB에서 테이블별 DDL을 추출하여 `sql/*.sql` 파일로 최신화하여 관리하기 시작했습니다.
- `docs/url-semantics.md` 문서를 생성하여 정규화된 URL 규약을 고정했습니다.
- `modules/ShinHanInvest_1.py` 리팩토링 시 누락되었던 모바일 뷰 전용 `ARTICLE_URL` 생성 로직을 추가했습니다.
- **DBfi endpoint 외부화**: DBfi 전용 endpoint 조합을 `secrets.json`으로 이관하고 관련 히스토리 정리했습니다.

### 2026-04-21 — PostgreSQL 재전환

- `scripts/sync_recent_sqlite_to_postgres.py`를 추가해 최근 SQLite 데이터를 JSON으로 export한 뒤 PostgreSQL `TB_SEC_REPORTS`에 `KEY` 기준 upsert하고 정합성을 비교할 수 있게 했습니다.
- 운영 DB backend를 `DB_BACKEND=postgres`로 재전환했습니다.
- `PostgreSQLManager.execute_query()`를 추가해 기존 `SQLiteManager` 기반 DB 테스트와 동일한 인터페이스를 지원합니다.
- architecture 문서를 2026-04-21 PostgreSQL 재전환 상태와 검증 커맨드 기준으로 갱신했습니다.
... (후략) ...
