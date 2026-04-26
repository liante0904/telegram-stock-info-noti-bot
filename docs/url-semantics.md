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

하지만 실제 코드에서는 컬럼 이름보다 fallback 순서에 더 의존하고 있었습니다. 이로 인해 컬럼 의미와 런타임 동작이 서로 어긋난 상태였습니다.

---

## 확정 규약

### `KEY`
- 역할: 중복 제거 및 upsert 기준이 되는 식별자.

### `TELEGRAM_URL`
- 역할: 텔레그램 메시지에서 사용자에게 노출할 단일 대표 링크.
- 원칙: 메시지 렌더링은 이 컬럼만 신뢰.

### `PDF_URL`
- 역할: PDF 다운로드 및 외부 archiver 연동용 링크.
- 원칙: 파일 다운로드는 이 컬럼을 최우선으로 사용.

### `ARTICLE_URL`
- 역할: 원문 게시글 또는 상세 페이지 URL.
- 비고: 디버깅, 재수집, 링크 추적에 사용.

### `ATTACH_URL`
- 역할: 과거 설계의 잔존 컬럼.
- 상태: **deprecated / removed from code**.
- 원칙: 신규 코드에서 사용하지 않으며, 모든 스크래퍼 모듈에서 제거 완료.

---

## 마이그레이션 현황 (2026-04-26)

### 1. 작업 완료 (전체 28개 모듈 정규화 완료)
모든 증권사 모듈의 반환 딕셔너리에서 `ATTACH_URL` 컬럼이 제거되었으며, 데이터 분석을 통해 각 목적에 맞는 컬럼(`TELEGRAM_URL`, `PDF_URL`, `ARTICLE_URL`)으로 배분이 완료되었습니다.

- **대상 모듈**: `LS_0`, `ShinHanInvest_1`, `NHQV_2`, `HANA_3`, `KBsec_4`, `Samsung_5`, `Sangsanginib_6`, `Shinyoung_7`, `Miraeasset_8`, `Hmsec_9`, `Kiwoom_10`, `DS_11`, `eugenefn_12`, `Koreainvestment_13`, `DAOL_14`, `TOSSinvest_15`, `Leading_16`, `Daeshin_17`, `iMfnsec_18`, `DBfi_19`, `MERITZ_20`, `Hanwhawm_21`, `Hygood_22`, `BNKfn_23`, `Kyobo_24`, `IBKs_25`, `SKS_26`, `Yuanta_27`

### 2. 마이그레이션 종료
모든 주의 대상(LS, 신한, 메리츠 등)에 대한 전수 데이터 조사가 완료되었으며, 고유 데이터 손실이 없음을 확인했습니다. 이제 DB 스키마에서 `ATTACH_URL` 컬럼을 드랍할 준비가 되었습니다.

---

## 데이터 분석 결과 (2026-04-26)

운영 PostgreSQL DB의 전수 데이터를 분석한 결과, `ATTACH_URL`의 실체는 다음과 같으며 모두 정규화된 컬럼으로 대체 가능함이 확인되었습니다.

| 증권사 | ATTACH_URL의 실체 | 대체 컬럼 | 분석 결과 |
|---|---|---|---|
| **LS증권** | 리포트 상세 페이지 URL | `ARTICLE_URL` | 100% 일치. 중복 데이터임. |
| **메리츠증권** | PDF 직접 다운로드 URL | `PDF_URL` | `TELEGRAM_URL`과 동일. 중복 데이터임. |
| **신한증권** | PDF 첨부파일 서블릿 URL | `PDF_URL` | `DOWNLOAD_URL`과 동일. 중복 데이터임. |
| **유안타증권** | PDF 직접 다운로드 URL | `PDF_URL` | 모든 파일 관련 컬럼과 동일. 중복 데이터임. |
| **현대차증권** | 사이냅 뷰어 기반 링크 | `TELEGRAM_URL` | `ARTICLE_URL`과도 중복됨. 고유성 없음. |

### 분석 결론
`ATTACH_URL`은 초기 설계 시 "가장 중요한 링크 하나"를 담는 용도로 쓰였으나, 현재는 각 목적에 맞는 컬럼들이 완성되어 **의미가 모호한 단순 중복 컬럼**으로 전락했습니다. 모든 스크래퍼의 코드 수정을 완료하였으므로 이제 컬럼 드랍이 가능합니다.
