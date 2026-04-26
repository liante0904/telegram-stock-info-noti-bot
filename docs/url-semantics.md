# URL Column Semantics

> 이 문서는 리포트 테이블의 URL 관련 컬럼 의미를 고정하고, `ATTACH_URL` 퇴역 절차를 정리합니다.
> 기준일: 2026-04-26

---

## 문제 배경

현재 스키마에는 다음 URL 컬럼이 공존합니다.

- `ATTACH_URL`
- `ARTICLE_URL`
- `TELEGRAM_URL`
- `PDF_URL`
- `DOWNLOAD_URL`

하지만 실제 코드에서는 컬럼 이름보다 fallback 순서에 더 의존하고 있습니다.

- 메시지 생성: `TELEGRAM_URL -> ATTACH_URL -> DOWNLOAD_URL -> ARTICLE_URL`
- 다운로드: `DOWNLOAD_URL -> ATTACH_URL -> ARTICLE_URL -> TELEGRAM_URL`
- 일부 스크래퍼는 동일 URL을 여러 컬럼에 중복 저장
- 일부 모듈은 `KEY`를 기사 URL로, 일부는 PDF URL로 사용

이 상태는 단순 네이밍 문제가 아니라, 컬럼 의미와 런타임 동작이 서로 어긋난 상태입니다.

---

## 확정 규약

### `KEY`

- 역할: 중복 제거 및 upsert 기준이 되는 식별자
- 상태: 유지
- 비고: 당장 컬럼 의미를 재정의하지 않고, 모듈별 생성 규칙만 통제

### `TELEGRAM_URL`

- 역할: 텔레그램 메시지에서 사용자에게 노출할 단일 대표 링크
- 허용 값:
  - 게시글 상세 페이지
  - 공유용 우회 링크
  - PDF 직접 링크
- 원칙: 메시지 렌더링은 장기적으로 이 컬럼만 신뢰

### `PDF_URL`

- 역할: PDF 다운로드 및 외부 archiver 연동용 링크
- 허용 값:
  - PDF 직접 URL
  - viewer/doc gateway를 거친 실제 다운로드 URL
- 원칙: 파일 다운로드는 장기적으로 이 컬럼을 우선 사용

### `ARTICLE_URL`

- 역할: 원문 게시글 또는 상세 페이지 URL
- 허용 값:
  - 증권사 리서치 상세 페이지
  - 문서 메타 페이지
- 비고: 디버깅, 재수집, 링크 추적에 사용 가능

### `ATTACH_URL`

- 역할: 과거 설계의 잔존 컬럼
- 상태: deprecated
- 원칙:
  - 신규 의미를 추가하지 않음
  - 신규 코드에서 primary source로 사용하지 않음
  - read/write 경로를 제거한 뒤 최종 스키마에서 드랍

### `DOWNLOAD_URL`

- 역할: 과거 다운로드 fallback용 컬럼
- 상태: transitional
- 원칙: 장기적으로 `PDF_URL`에 흡수

---

## 목표 상태

장기적으로 앱 로직은 아래 세 컬럼만 의미 있게 사용합니다.

- `KEY`
- `TELEGRAM_URL`
- `PDF_URL`
- `ARTICLE_URL`

`ATTACH_URL`과 `DOWNLOAD_URL`은 호환 계층을 거친 뒤 제거 후보로 봅니다.

---

## 단계별 실행 계획

### 1단계: 문서화 및 규약 고정

- 이 문서와 `docs/architecture.md`에 규약을 기록
- 신규 수정 시 위 규약을 우선 적용

### 2단계: read path 정리

- 메시지 생성 로직에서 `ATTACH_URL` fallback 제거
- 다운로드 로직에서 `PDF_URL` 우선 규칙으로 재정의

### 3단계: write path 정리

- 각 `modules/*.py`가 반환하는 dict를 새 의미에 맞춰 조정
- `ATTACH_URL`에 새 값을 적극적으로 넣는 로직 제거

### 4단계: 호환 계층 축소

- DB manager와 유틸에서 `ATTACH_URL` 의존 제거
- 테스트와 운영 스크립트의 fallback 정리

### 5단계: 최종 스키마 정리

- 운영에서 `ATTACH_URL`/`DOWNLOAD_URL` 비의존이 확인되면 PostgreSQL에서 드랍 검토
- lowercase schema 전환 시 새 의미를 그대로 반영

---

## 당장 손볼 코드 우선순위

1. `utils/sqlite_util.py` 메시지 링크 선택
2. `utils/file_util.py` 다운로드 URL 선택
3. 각 스크래퍼 모듈의 반환 dict
4. DB manager의 fallback/update 규칙
5. 테스트 및 운영 스크립트

---

## 주의 사항

- `KEY`는 현재 운영 dedup 축이므로 이번 리팩토링에서 의미 변경을 피함
- 외부 워크스페이스가 `PDF_URL`에 의존하므로 `PDF_URL`는 보수적으로 유지
- `ATTACH_URL`는 즉시 드랍하지 않음
- PostgreSQL lowercase schema 전환은 이 문서의 의미 정리가 선행된 뒤 진행
