---
name: backend-conventions
description: backend(FastAPI·SQLAlchemy async·Alembic)의 규약 정본 — 설정, 모델·키·시간 컬럼, 마이그레이션 순번과 앱 DB 롤, 요청 입력의 범위 검사, 오류 응답 계약(semantic-v1), 로깅, 세션 사용법. 라우터·모델·마이그레이션·설정 값을 추가하거나, 오류를 어떻게 낼지·로그를 어떻게 남길지 판단할 때 사용한다. 기능 전체 순서는 feature-slice, 테스트·검사 명령은 verify skill 이 다룬다.
---

# backend 규약

명령은 모두 `backend/` 에서 실행한다.

## 설정 — `app/config.py`

- 환경변수 이름은 배포 환경과 **같은 이름, 접두어 없음**([결정 0002](../../../docs/decisions/0002-환경변수-이름은-배포-환경과-같게.md)).
- 필수 값에 기본값을 두지 않는다. 빠지면 부팅에서 실패한다(기조 5).
- 새 값이 필요하면 `Settings` 에 필드를 추가하고 `.env.example`·`.env.test` 에도 같은 키를 넣는다. 배포 환경이 이미 넣는 값이면 그 이름 그대로 쓰고,
  배포 설정에 없는 값이면 배포 설정에도 추가가 필요하다 — 사용자에게 알린다.
- 설정은 `from app.config import settings` 로만 읽는다. `os.environ` 을 직접 읽지 않는다(마이그레이션의 앱 롤 입력만 예외).
- 로컬은 `backend/.env`, 배포는 배포 환경이 환경변수·비밀 저장소로 **같은 이름**을 넣는다. 코드에 로컬/배포 분기를 두지 않는다(기조 2).
  기능별로 쓰는 이름:

| 이름 | 쓰는 곳 | 배포 |
|---|---|---|
| `JWT_SECRET` | 인증 — 쿠키 JWT 서명. 32바이트 이상(HS256 권장 최소 길이, 부팅 때 검사) | 비밀 저장소 |
| `JWT_TTL_MINUTES` · `COOKIE_SECURE` | 인증 — 만료, 쿠키 Secure(로컬 false·배포 true) | 환경변수. 배포는 `COOKIE_SECURE=true` 고정 |
| `LOGIN_MAX_FAILURES` · `LOGIN_LOCK_MINUTES` | 인증 — 계정 잠금까지의 연속 실패 횟수, 잠금 시간(분) | 환경변수 |
| `ALLOWED_ORIGINS` | 출처 검사(CSRF) — 화면이 열리는 출처, 쉼표로 여러 개(`scheme://host[:port]`, 끝 슬래시 없음). 로컬 `http://localhost:5174` | 환경변수. 화면 도메인 |
| `AWS_REGION` | 스토리지 — boto3 리전(boto3 는 `AWS_DEFAULT_REGION` 만 읽으므로 코드가 명시적으로 넘긴다) | 환경변수 |
| `STORAGE_BUCKET` | 스토리지 — 파일 버킷(결정 0004) | 환경변수 |
| `S3_ENDPOINT_URL` · `S3_ACCESS_KEY_ID` · `S3_SECRET_ACCESS_KEY` | 스토리지 — 로컬 S3 호환 컨테이너용. **배포에서는 비워 두고** 실행 역할로 붙는다(빈 문자열과 키 없음은 같은 뜻 = boto3 기본 자격 증명 체인, `config.py` 가 경계에서 정규화) | 넣지 않음 |
| `ADMIN_LOGIN_ID` · `ADMIN_INITIAL_PASSWORD` | 관리자 시드 명령만 읽는다(앱 부팅 설정이 아니다) | 명령 실행 환경에서 넣는다 |
| `WORKER_POLL_SECONDS` · `WORKER_MAX_ATTEMPTS` · 소비자마다 `WORKER_<소비자>_CONCURRENCY` · `WORKER_<소비자>_ORPHAN_MINUTES` | 워커만 읽는다(`app/worker/settings.py` 의 `WorkerSettings` — 앱 부팅 설정이 아니다). 보조 폴링 간격 · 시도 상한은 프로세스 공용이고, 동시 처리 수 · 고아 회수 기준(분)은 소비자(작업 큐)마다 둔다 — 칸 `worker_<ConsumerSpec.name>_<속성>`. 소비자를 더하는 PR 이 `WorkerSettings` 의 소비자별 묶음(속성마다 한 줄)과 `app/worker/__main__.py` 의 `CONSUMERS`(한 줄)에 더한다(등록 지점 — 다른 줄은 손대지 않는다). 동시 처리 수의 합은 10 이하(api.md 「워커」) | 워커 실행 환경. 소비자를 더하면 배포 설정에도 둘씩 더한다 |

## 시드

- **참조 데이터**(코드 표처럼 코드가 전제하는 행)는 마이그레이션의 데이터 단계로 넣는다(`op.bulk_insert`). 로컬·배포가 같은 경로로 같은 행을 갖는다.
- **관리자 계정**은 마이그레이션이 아니라 명령 `python -m app.domains.auth.seed_admin` 으로 만든다 — 비밀번호가 마이그레이션 파일에 남으면 안 된다.
  `ADMIN_LOGIN_ID`·`ADMIN_INITIAL_PASSWORD` 를 읽고, 이미 있으면 아무것도 하지 않는다(멱등). 만든 계정은 `must_change_password=true`, `role=admin`.
- **다른 계정**은 관리자가 사용자 관리 API(`/api/v1/users`, api.md 「사용자 관리」)로 만든다. 계정 생성 로직은 `domains/auth/service.py` 의
  `create_user` 하나다(시드 명령과 공유).
- **관리자가 자기 비밀번호를 잊었을 때**(다른 관리자가 없으면 API 로 초기화할 수 없다):
  `python -m app.domains.auth.reset_password --login-id <id>` — 새 임시 비밀번호를 발급해 **표준 출력에 한 번** 보여 주고, `token_version` 을 +1 해
  그 사용자의 기존 세션을 모두 끊고 · 로그인 잠금을 풀고 · `must_change_password=true` 로 둔다. 없는 아이디면 종료 코드 1.
  비밀번호를 로거에 남기지 않는다. 사람이 붙은 터미널에서 돌리고, 출력이 로그 저장소로 가는 일회성 작업으로는 돌리지 않는다.
- 개발 편의용 가짜 데이터 시드는 두지 않는다(기조 1). 화면 확인은 실제 입력 · 실제 처리로 한다.

## 모델

- 기반: `app.db.base.Base`. PK 는 `IdPkMixin`(`BIGINT IDENTITY`), 시간은 `TimestampMixin`(`created_at`·`updated_at`).
- 컬럼 타입: JSON 은 `app.db.types.Json`(JSONB, None → SQL NULL), 시각은 `UtcDateTime`(timestamptz).
- 화면에 보이는 업무 ID(`ORD-0012` 같은 코드)는 PK 가 아니라 별도 컬럼 + unique.
- 상태값은 PostgreSQL ENUM 대신 `String` + `CheckConstraint` 로 둔다(값 추가가 마이그레이션 한 줄로 끝난다).
- 제약 이름은 `NAMING_CONVENTION` 이 정한다. 복합 unique 는 `Index("uq_<table>_<전 컬럼>", ..., unique=True)`.
- 테이블 이름은 영문 snake_case 단수(`app_user`, `order_item`).
- 모델을 추가하면 `app/db/model_registry.py` 에 import 한 줄.
- 테이블 · 컬럼마다 설명을 단다 — 테이블은 `__table_args__` 의 `{"comment": ...}`, 컬럼은 `mapped_column(..., comment=...)`.
  내용은 「이 칸이 무엇인지」 한 줄이고 업무 규칙 · 근거는 db-schema.md 에 둔다. autogenerate 가 DB 설명(`COMMENT ON`)으로 옮기고,
  빠뜨리면 unit 테스트 `test_model_comments.py` 가 실패한다.

## 마이그레이션

- 파일 이름 `NNNN_<slug>.py`, 4자리 순번: `uv run alembic revision --autogenerate --rev-id 0002 -m "주문 테이블"`
- autogenerate 결과는 **전부 읽고** 고친다(서버 기본값·제약 이름·데이터 이관은 자동으로 맞지 않는다).
- **forward-only**: `downgrade()` 는 `downgrade_not_supported()` 를 부른다(템플릿 기본). 운영 복구는 DB 스냅숏.
- **머지된 마이그레이션은 고치지 않는다.** 바꾸려면 새 revision 을 만든다.
- autogenerate 는 **로컬 DB 와 모델을 비교**한다. 마이그레이션이 다른 브랜치로 옮기면 `make local-reset` 후 작업한다(다른 브랜치의 revision 이
  로컬 DB 에 남아 있으면 그 테이블이 `drop_table` 로 초안에 섞인다). 로컬 DB 를 손으로 고치지 않는다. 스테이징·운영 DB 에는 autogenerate 를 돌리지 않는다.
- 순번 충돌: 먼저 머지한 쪽이 번호를 갖는다. 뒤에 머지하는 쪽이 번호와 `down_revision` 을 고친다(collaboration.md).
  `tests/unit/test_migration_chain.py` 가 사슬이 한 줄인지, 번호가 0001 부터 빠짐없이 이어지는지, 파일 이름 번호와 `revision` 이 같은지를
  DB 없이 검사한다(`pytest -m unit` 에 포함).
- 매 `upgrade head` 의 마지막에 `migrations/app_role.py` 가 앱 롤(`APP_DB_USER`)을 만들고 권한을 맞춘다. 앱은 DML 만 되는 앱 롤로,
  마이그레이션은 스키마 변경 권한 계정으로 돈다. 로컬은 `make db-migrate` 가 두 계정을 넣어 준다.

## 세션

- 라우터: `db: AsyncSession = DbDep`. 요청이 성공하면 commit, 예외면 rollback 된다. 핸들러·서비스에서 `commit()` 을 부르지 않는다.
  예외 — 오류 응답으로 끝나도 남아야 하는 쓰기(로그인 실패 횟수)는 그 쓰기 직후 서비스가 `commit()` 하고 raise 한다. 별도 세션을 열지 않는다 —
  요청 세션이 연결을 쥔 채 두 번째 연결을 기다리면 동시 요청에 풀이 막힌다(`domains/auth/service.py` 「authenticate」).
- commit 은 핸들러가 돌아온 뒤, **응답을 보내기 전에** 끝난다(`DbDep` 의 `scope="function"`) — 2xx 를 받았으면 커밋된 것이고,
  commit 이 실패하면 오류 응답(500)이 나간다. 스트리밍 응답(`StreamingResponse`)은 본문을 보내기 전에 세션이 닫히므로 본문 생성기에서 세션을 쓰지 않는다.
- 서비스 함수는 세션을 첫 인자로 받는다: `async def list_orders(db: AsyncSession, ...)`.
- 워커·스크립트: `async with session_scope() as db:`.
- 예외 — commit 이 끝난 뒤에 외부 부작용(S3 객체 삭제 등)을 내야 하는 라우터는 `DbDep` 대신 `session_scope()` 블록을 열고
  블록 밖에서 부작용을 낸다. `DbDep` 의 commit 은 핸들러가 돌아온 뒤에 돌아 핸들러 안에는 그 뒤에 끼울 자리가 없다
  (예: 파일 행 삭제 — 행 삭제가 commit 되기 전에 객체를 지우면 commit 실패 때 객체만 사라진다).

### 읽기 전용 복제본(리더)을 붙일 때

지금은 DB 연결이 하나(쓰기 DB)다. 부하 때문에 읽기 전용 복제본을 쓰게 되면 아래 규칙으로 붙인다 — 그 전에는 만들지 않는다.
먼저 앱 밖(커넥션 풀러 · DB 의 읽기 엔드포인트 · 인스턴스 크기)으로 풀 수 있는지 본다.

- **기본은 전부 쓰기 DB 다.** 복제본은 지연을 감수해도 되는 조회 전용 엔드포인트(목록 · 통계 · 내려받기용 조회)만, 별도 의존성
  (예: `ReadOnlyDbDep` — 별도 엔진, 설정 `DB_READ_HOST` 등)으로 **명시해서** 쓴다. 엔드포인트를 옮길 때 PR 본문에 「복제본 조회: 무엇」을 적는다.
- 복제본 설정에 「없으면 쓰기 DB」 fallback 을 두지 않는다(기조 5). 복제본을 쓰는 배포는 값을 넣고, 로컬 · 테스트도 같은 이름에 같은 DB 주소를 넣는다(기조 2).
- 복제본은 늦다(수 ms ~ 수 초). 그래서 **쓰기 DB 에 남겨야 하는 것**:
  - 쓰기와 그 쓰기 판단에 쓰는 읽기 — 한 트랜잭션 안에서 복제본 세션과 쓰기 세션을 섞지 않는다.
  - 인증 · 권한 대조(미들웨어의 `token_version` · 사용 여부) — 늦으면 끊은 세션이 몇 초 통한다.
  - 행 잠금 · 조건부 UPDATE 로 판정하는 로직(로그인 잠금 등).
  - 방금 쓴 값을 다시 보여 주는 조회(쓰기 직후 화면이 다시 읽는 목록 · 상세) — 늦으면 옛 값을 지금 값처럼 보인다(기조 1).
- 로컬 · CI 는 같은 DB 라 복제 지연이 드러나지 않는다. 복제본으로 옮기는 엔드포인트는 「옛 값을 보여도 되는가」를 리뷰에서 확인한다.

## 요청 입력 — 경계에서 범위 검사

- 요청 값은 라우터 파라미터·요청 모델(경계)에서 한 번 검증하고 서비스 시그니처는 그대로 둔다(기조 5). 벗어난 값은 FastAPI 검증이
  422 `request_validation_failed` 로 답한다(`errors.py`).
- 정수는 DB 범위 안에서만 받는다. 맨 `int` 로 두면 bigint 를 넘는 값이 DB 드라이버(asyncpg)에서 실패해 처리되지 않은 예외(500)가 된다.
  - 경로의 행 id: `IdPath`(`app/api/schemas.py` — 1 ~ `BIGINT_MAX`, PK 는 1 부터). 범위 안의 없는 행은 서비스의 404 그대로다.
  - 쿼리·폼·본문의 행 id: `Query(..., ge=1, le=BIGINT_MAX)` · `Form(..., ge=1, le=BIGINT_MAX)` · `Field(ge=1, le=BIGINT_MAX)`.
  - DB 에서 OFFSET 으로 잘라 오는 목록의 `page`: `le=BIGINT_MAX // 쪽 크기 상한`(라우터의 `MAX_PAGE`) — OFFSET 이 bigint 안에 들게.

## 오류 — semantic-v1

- product 코드는 `app.api.error_contract.SemanticHTTPException` 만 낸다. FastAPI `HTTPException` 은 쓰지 않는다.
- **오류 code 목록의 정본은 `error_contract.py` 의 `ApiErrorCode`(목록)와 `ERROR_CODE_STATUS`(code → HTTP 상태)다.**
  HTTP 상태와 family 는 code 가 정한다 — 호출부는 `SemanticHTTPException(code=..., details=..., diagnostic_message=...)` 만 쓴다.
  목록에 없는 code 를 쓰면 pyright 가 잡는다.
- `code` 이름은 `<대상>_<사유>` snake_case(`order_not_found`, `order_already_closed`). 새로 만들기 전에 목록에서
  같은 뜻의 code 가 있는지 먼저 찾는다. 목록은 도메인별 주석으로 묶어 두고, 그 묶음 끝에 한 줄 추가한다.
- **새 code 추가 절차** — 셋을 같은 변경에 담는다:
  1. `ApiErrorCode` 와 `ERROR_CODE_STATUS` 에 한 줄씩(둘이 어긋나면 import 시 실패).
  2. 루트에서 `make gen-error-codes` → `frontend/src/api/error-codes.generated.ts` 갱신(빠뜨리면 unit 테스트
     `test_error_codes_generated.py` 가 실패).
  3. `frontend/src/api/error-messages.ts` 에 화면 문구(빠뜨리면 TypeScript 컴파일 에러).
- `details` 는 화면이 문구를 만들 때 쓸 값만, camelCase 키로. 문구 표가 그 값을 문장에 넣는다.
- `diagnostic_message` 는 원인 원문(개발·지원용). 사용자 문장을 넣지 않는다 — 문구는 화면이 code 로 만든다. 비밀 값을 넣지 않는다.
- unique 위반을 409 로 바꿀 때는 `violates_unique_constraint(exc, "uq_...")` 로 **그 제약만** 확인하고, 다른 무결성 오류는 그대로 올린다.
- 하위 예외를 바꿔 올릴 때 `raise SemanticHTTPException(...) from exc`.

## 로깅

- 로거는 `from app.logging import get_logger` → `logger = get_logger("domains.orders")`. `logging.getLogger` 직접 호출은 ruff 가 막는다.
- 엔티티 식별자는 메시지 보간이 아니라 `extra={"order_id": ...}` 로. request_id 는 자동으로 붙는다.
- 키 이름에 password·secret·token 등이 들어간 extra 값은 자동으로 가려진다. 그래도 비밀 값을 일부러 싣지 않는다.
- 레벨: 운영자 행동이 필요하면 warning/error, 정상 흐름의 예상 실패는 debug. 상세 진단은 `logger.trace(...)`.
  예외 — 보안 사건(로그인 거부 · 계정 잠금)은 운영에서 보여야 하므로 warning 이다.
- 접근 로그는 미들웨어가 한 줄 남긴다(`app.http`). 핸들러에서 같은 내용을 또 남기지 않는다.

## 구조

```
app/
  config.py · logging.py · context.py · main.py · __main__.py
  worker/     워커 진입점 __main__.py(소비자·주기 작업 등록 지점) · queue.py(소비 루프) · listener.py(LISTEN 전용 접속) · scheduler.py · notify.py · settings.py(워커 설정 — 소비자별 동시 처리 수·고아 회수 기준 등록 지점)
  api/        error_contract.py · errors.py · schemas.py(ApiBase·ApiRequestBase·PageEnvelope·BIGINT_MAX·IdPath) · router.py · health.py · uploads.py · downloads.py(업로드 경계 검사 · 첨부 헤더, api.md 「업로드」)
  db/         base.py · mixins.py · types.py · engine.py · deps.py · model_registry.py
  middleware/ request_context.py (request_id·접근 로그) · origin_check.py (쓰기 요청의 Origin 대조 — CSRF) · auth.py (쿠키 JWT → DB 대조 → must_change_password 게이트, 인증 · 권한 담당자 소유)
  core/       두 도메인 이상이 쓰는 공용 로직 — storage.py(파일 객체 스토리지·키 규칙, 결정 0004)
  domains/<domain>/  models · schemas · service · router (폴더 목록은 docs/specs/api.md 「코드 도메인」)
  domains/auth/deps.py   CurrentUser · RequireAdmin (api.md 「인증 계약」)
migrations/   env.py · app_role.py · forward_only.py · versions/
scripts/      generate_error_codes.py (오류 code → frontend 타입)
```

진입점: API `python -m app`, 워커 `python -m app.worker`, 마이그레이션 `alembic upgrade head` — 컨테이너 하나로 명령만 바꿔 돈다.
