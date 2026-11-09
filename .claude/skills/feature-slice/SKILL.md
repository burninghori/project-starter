---
name: feature-slice
description: 기능 하나를 DB 모델 → 마이그레이션 → 서비스·API → 화면 → 테스트로 끝까지 만드는 순서와 파일 위치. 새 도메인(주문·사용자·보고서 등)을 추가하거나, 기존 도메인에 목록·상세·등록·수정 기능을 붙이거나, "이 기능 만들어줘" 류로 풀스택 작업을 시작할 때 사용한다. 화면 디자인 세부는 frontend/CLAUDE.md, 백엔드 세부 규약은 backend-conventions skill 이 정본이다 — 이 skill 은 순서와 연결을 다룬다.
---

# 기능 하나를 끝까지 — 풀스택 슬라이스

이 프로젝트는 기능(도메인) 단위로 한 사람이 DB 부터 화면까지 만든다([collaboration.md](../../../docs/development/collaboration.md)).
아래 순서를 따르면 여러 사람의 결과물이 같은 모양이 된다.

## 0. 시작 전에 확인

1. **레퍼런스 구현**이 있으면 먼저 전부 읽는다(collaboration.md 의 레퍼런스 슬라이스). 같은 종류의 화면·API 면 그 구조를 따른다.
2. 이 기능의 테이블·API 가 [DB 스키마 정의](../../../docs/specs/db-schema.md)·[API 명세](../../../docs/specs/api.md)에 있는지 본다.
   없으면 먼저 명세에 적고 사용자 확인을 받는다. 구현 중 명세와 달라지면 같은 변경에서 명세를 고친다.
3. 이 기능이 **공통 테이블**(두 기능 이상이 쓰는 테이블)을 만들거나 바꾸는가? 그렇다면 [결정 기록](../../../docs/decisions/README.md)이
   있는지 보고, 없으면 구현 전에 사용자에게 알린다. 공통 테이블은 함께 확정한다.
4. 화면 작업이 있으면 목업 HTML 과 화면 기능 정의(프로젝트에서 `frontend/docs/design/` 아래에 둔다)가 있는지 본다.
   없으면 무엇이 필요한지 사용자에게 묻는다.
5. CLAUDE.md 「공통 어휘」 표에서 이 기능의 용어와 코드 어휘를 확인한다. 코드 칸이 비어 있으면 이 작업에서 정하고 표를 채운다.

## 1. 파일 위치

`<domain>` 폴더 이름은 영문 snake_case 복수형(`orders`, `purchase_requests`)이다(테이블 이름은 단수, backend-conventions).
한 도메인 = 한 폴더 = 보통 한 사람.

```
backend/app/domains/<domain>/
  __init__.py
  models.py        SQLAlchemy 모델 (IdPkMixin + TimestampMixin)
  schemas.py       요청(ApiRequestBase)·응답(ApiBase) 모델
  service.py       업무 로직. 세션을 인자로 받는다. HTTP 를 모른다
  router.py        FastAPI 라우터. 검증·권한·응답 변환만, 로직은 service 로
backend/migrations/versions/NNNN_<slug>.py
backend/tests/unit/<domain>/test_*.py          DB 없는 로직(계산·변환 등)
backend/tests/integration/<domain>/test_*.py   DB·API 를 거치는 동작

frontend/src/api/<domain>/index.ts             타입 · query key · 호출 함수 · 조회/변경 훅
frontend/src/app/pages/<domain>/<Name>Page.tsx 화면 (+ 같은 폴더에 화면 전용 컴포넌트)
frontend/src/app/pages/<domain>/<Name>Page.test.tsx
```

## 2. 순서

| # | 단계 | 하는 일 | 확인 |
|---|---|---|---|
| ① | 모델 | `models.py` 작성. `app/db/model_registry.py` 에 import 한 줄 추가 | 업무 ID 는 PK 가 아니라 별도 unique 컬럼. 테이블 · 컬럼마다 `comment`(이 칸이 무엇인지 한 줄) |
| ② | 마이그레이션 | `uv run alembic revision --autogenerate --rev-id NNNN -m "<요약>"` → 생성 파일을 **전부 읽고** 손본다 | 순번은 main 최신 + 1. `make db-migrate` 로 로컬 적용 |
| ③ | 서비스 | `service.py` — 조회·생성·수정 로직. 없는 대상은 `SemanticHTTPException(404, ...)` | 계산·변환 로직은 순수 함수로 빼서 unit 테스트 |
| ④ | 라우터 | `router.py` — `APIRouter(prefix="/<domain>")`. `app/api/router.py` `_DOMAIN_ROUTERS` 에 한 줄 추가. | 목록은 `PageEnvelope`. 요청 모델은 `ApiRequestBase` |
| ⑤ | 백엔드 테스트 | integration: `db_client` 로 API 왕복, `db_session` 으로 서비스. unit: 순수 로직 | `verify` skill |
| ⑥ | API 모듈 | `src/api/<domain>/index.ts` — 응답 타입(camelCase), `<domain>Keys`, `<domain>Api`, `use…` 훅 | `src/api/health/index.ts` 가 형태 예시 |
| ⑦ | 화면 | frontend/CLAUDE.md 의 「화면 한 장을 만드는 순서」 6단계 | 로딩·오류·빈 상태를 모두 그린다 |
| ⑧ | 메뉴 | 기능이 완성됐으면 `pages-config.tsx` 에서 그 메뉴를 「준비 중」에서 열림으로 바꿔 화면을 잇는다(메뉴에 없는 화면은 `nav: null` 한 줄 추가) | 미완성 기능을 열림으로 두지 않는다(결정 0003) |
| ⑨ | 화면 테스트 | `<domain>Api` 를 `vi.spyOn` 으로 가로채고 화면을 그려 확인 | `HomePage.test.tsx` 가 형태 예시 |
| ⑩ | 검증 | `verify` skill 전체. 리뷰는 사용자가 요청할 때만(아래) | 브라우저로 실제 조작(기조 3) |

사용자가 리뷰를 요청하면 `pre-pr-review` skill 을 따른다. 「리뷰해줘」는 메인 세션이 직접, 리뷰 에이전트를 명시하면 `pr-reviewer` 가
리뷰한다(에이전트를 부를 때 할 일·재리뷰 규칙도 그 skill 에 있다).

## 3. API 계약 규칙

- 경로: `/api/v1/<domain>` 목록·생성, `/api/v1/<domain>/{id}` 상세·수정·삭제. 동작은 `POST /api/v1/<domain>/{id}/<동사>`
  (예: `/orders/{id}/confirm`).
- wire 필드는 camelCase(`ApiBase` 가 자동 변환). 백엔드 코드는 snake_case.
- 목록 응답: `{"rows": [...], "total": N, "pageCount": N}`. 쿼리 `page`(1부터)·`pageSize`.
- 요청 정수(경로 id·쪽 번호 등)는 DB 범위 안에서만 받는다 — 범위 밖은 422, 범위 안의 없는 행은 404. 방법은 backend-conventions 「요청 입력」.
- 오류: `SemanticHTTPException(code=...)` 만. 새 code 는 backend-conventions 「오류」의 세 단계(목록 추가 →
  `make gen-error-codes` → `error-messages.ts` 문구)를 같은 변경에 담는다. 화면은 `apiErrorMessage(error)` 로 문구를 얻는다.
- 값이 없거나 계산할 수 없으면 `null`·빈 배열. 그럴듯한 기본값으로 채우지 않는다(기조 1).

## 4. 공통 영역을 고쳐야 할 때

기능 작업 중 백엔드 공통·마이그레이션 체인·인증 등 **소유자가 있는 영역**을 바꿔야 하면, 그 변경을 기능 PR 에 섞지 않는다.
사용자에게 알리고 별도의 작은 변경으로 분리한다(collaboration.md 「공통 영역 소유」).

프론트 영역(공통 컴포넌트 · 스타일 · 디자인 정의 · 셸)은 인증 · 권한을 빼고 소유자가 없어 기능 PR 에서 함께 고친다(결정 0001). 공통 부품을 새로 만들 때는 다른 개발자의
열린 PR 에 같은 용도가 있는지 `gh pr list` · `gh pr diff` 로 확인하고, PR 본문에 「공통 부품 추가: 무엇」을 적는다.
