# API 명세

> 상태: **틀** — 공통 규칙 · 인증만 정의되어 있다. 기능을 만들 때 「코드 도메인(폴더)」 · 「엔드포인트 목록」에 줄을 더하고 도메인별 절을 쓴다.
> 테이블은 [db-schema](db-schema.md). 어휘는 CLAUDE.md 공통 어휘를 따른다. 구현되면 코드(`router.py`·`schemas.py` → `/api/docs`)가 정본이다.

## 공통 규칙

- 경로: `/api/v1/<domain>` (목록·생성), `/api/v1/<domain>/{id}` (상세·수정·삭제), 동작은 `POST /api/v1/<domain>/{id}/<동사>`.
- 필드 이름은 camelCase. 목록 응답은 `{"rows": [...], "total": N, "pageCount": N}`, 쿼리 `page`(1부터)·`pageSize`.
- 오류 응답은 공통 형식(semantic-v1)이다:

  ```json
  {"error": {"contract": "semantic-v1", "family": "not_found", "code": "resource_not_found",
             "details": {"resource": "user", "id": 12}, "diagnostic": {"requestId": "…", "message": "…"}}}
  ```

  `code` 는 `<대상>_<사유>`. HTTP 상태와 family 는 code 가 정한다.
- **오류 code 목록의 정본은 `backend/app/api/error_contract.py`**(code → HTTP 상태), 화면 문구는
  `frontend/src/api/error-messages.ts` 다. 이 문서에는 엔드포인트별로 「어떤 상황에 어떤 code 가 나오는지」만 적는다.
- 값이 없거나 계산할 수 없으면 `null`·빈 배열. 그럴듯한 기본값으로 채우지 않는다(기조 1).
- 쿼리 파라미터 이름도 camelCase(`userId`·`pageSize`·`activeOnly`). 경로 변수는 `{id}` 또는 `{<대상>Id}`.
- 요청의 정수는 DB 범위 안인지 경계에서 본다. 행 id(경로·쿼리·폼·본문)는 1 ~ bigint 최댓값이고, DB 에서 OFFSET 으로 잘라 오는 목록의 `page` 는
  OFFSET 이 bigint 안에 드는 값(bigint 최댓값 ÷ 그 목록의 쪽 크기 상한)까지다. 벗어나면 DB 에 닿기 전에 422 `request_validation_failed`, 범위 안의 없는 행은 각 엔드포인트의 404 다.
- 열거값은 **코드 심볼 그대로**(snake_case: `in_progress`·`not_started`). 필드 이름만 camelCase 로 바꾸고 값은 바꾸지 않는다.
- 시각은 ISO 8601 UTC 문자열(`2026-10-16T02:00:00Z`). 화면 표기(최소 `YYYY-MM-DD`, 이력 일시 `YYYY-MM-DD HH:mm`)는 화면이 만든다.
- 식별자 이름: 내부 PK 는 `id`, 다른 리소스를 가리킬 때는 `<대상>Id`(`userId`). 화면에 보이는 업무 ID 는 `<대상>Code`(`itemCode`),
  번호는 `<대상>No`(`revisionNo`). 둘을 같은 응답에 함께 실어도 된다.
- 비동기 작업을 시작하는 요청은 **202** 와 작업 id 를 돌려주고, 진행은 조회 API 로 폴링한다.
- 파일 업로드는 multipart/form-data. 파일 필드 이름은 `files`(여러 개), 함께 가는 값은 camelCase 일반 필드. 공통 경계 검사는 아래 「업로드」.
- 인증([결정 0006](../decisions/0006-인증은-JWT-쿠키와-token-version-으로-한다.md)): 모든 요청은 미들웨어가 쿠키 JWT 를 검증하고
  **DB 에서 사용자 행(활성·`token_version`·역할)을 읽어 대조**한다. 불일치면 401. `must_change_password` 가 켜진 사용자는
  `/auth/me`·`/auth/logout`·`/auth/password` 외 요청이 403. 쓰기 요청(GET · HEAD · OPTIONS 가 아닌 것)은 그보다 먼저 `Origin` 헤더를
  `ALLOWED_ORIGINS` 와 대조한다(CSRF 방어 — 아래 「인증 계약」). 조회(GET)는 상태를 바꾸지 않는다 — 바꾸는 동작은 GET 으로 만들지 않는다. 권한 칸은 `없음` · `로그인` · `관리자` 로 적고, 역할을 더 나누면 그 이름을 쓴다.
  라우터가 쓰는 의존성은 아래 「인증 계약」이 정본이다.

## 코드 도메인(폴더)

아래 표의 「도메인」은 코드 폴더(`backend/app/domains/<domain>/`, `frontend/src/api/<domain>/`, `frontend/src/app/pages/<domain>/`)다.
한 폴더 = 보통 한 사람(feature-slice skill).

| 도메인(폴더) | 테이블(db-schema) | API | 담당 |
|---|---|---|---|
| `auth` | app_user | `/auth/*` · `/users/*` | 인증 · 권한 담당자(collaboration.md 2절) |

- 모델 파일의 소유는 폴더 담당자에게 있고, 마이그레이션 체인은 메인 개발자 소유로 남는다(collaboration.md 2절).
- 도메인 사이의 호출은 service 함수 import 로 한다. 라우터를 가로질러 부르지 않는다.

## 인증 계약

모든 라우터가 쓴다. 이름과 반환 형태를 고정한다.

| 항목 | 정의 |
|---|---|
| 파일 | `app.domains.auth.deps` |
| `CurrentUser` | FastAPI 의존성. `user: AuthUser = CurrentUser`. 쿠키 JWT → DB 대조까지 끝난 **활성 사용자**를 준다. 실패는 401 `auth_required`(쿠키 없음·만료·버전 불일치) 또는 403 `auth_user_inactive` |
| `AuthUser` | 불변 dataclass: `id · login_id · name · role · must_change_password · default_page · token_version`. `default_page` 는 `/auth/me` 응답에, `token_version` 은 본인 비밀번호 변경의 기대 버전에 쓴다. ORM 객체를 라우터에 넘기지 않는다 |
| `RequireAdmin` | 관리자 역할만. 역할 값 목록은 프로젝트가 정하므로 **관리자 판별은 `is_admin`(`role == "admin"`) 한 곳**으로 두고 값 목록이 정해지면 이 한 곳만 고친다. 아니면 403 `auth_forbidden`. 기능별 권한이 필요해지면 같은 파일에 의존성을 더한다 |
| 출처 검사(CSRF) | `app.middleware.origin_check`. `/api` 아래 쓰기 요청의 `Origin` 이 `ALLOWED_ORIGINS` 밖이거나 `null` 이면 403 `request_origin_forbidden`(details `origin`) — 인증보다 먼저라 로그인 요청도 막는다. `Origin` 이 없는 요청(브라우저가 아닌 명령 · 테스트 클라이언트)은 통과한다. 쿠키의 SameSite=Lax 가 다른 사이트를, 이 검사가 같은 사이트의 다른 출처(서브도메인 등)를 막는다 |
| `must_change_password` 게이트 | 미들웨어가 `/auth/me`·`/auth/logout`·`/auth/password` 외 요청을 403 `auth_password_change_required` 로 막는다 |
| 테스트 fixture | `auth_client`(관리자로 로그인된 `db_client`), `login_as(login_id, password)`(지정 사용자로 로그인된 클라이언트), `make_user(must_change_password=…, role=…)`(계정 생성 — 역할을 주지 않으면 admin, `(login_id, password)` 반환). `tests/plugins/auth.py`. 다른 도메인의 integration 테스트는 이 셋만 쓴다. TestClient 하나가 세션 하나다 — 같은 테스트에서 `login_as` 로 사용자를 바꾸면 이전 쿠키는 사라진다. unit 테스트는 `stub_auth(client, **overrides)` 로 DB 없이 인증된 요청을 보낸다 |
| 역할 값 | 미정. `app_user.role` 은 CHECK 없는 문자열, 시드 관리자는 `admin`. 정해지면 CHECK 와 역할→메뉴 표를 `app/domains/auth/roles.py` 에 둔다 |

## 엔드포인트 목록

| 메서드 | 경로 | 설명 | 권한 | 도메인 | 상태 |
|---|---|---|---|---|---|
| GET | /api/health | 프로세스 생존 | 없음 | 시스템 | 구현됨 |
| GET | /api/health/ready | DB 연결 + 파일 버킷 확인(503 `database_unavailable` · `storage_unavailable`) | 없음 | 시스템 | 구현됨 |
| POST | /api/v1/auth/login | 로그인 → JWT httpOnly 쿠키 발급(SameSite=Lax, 만료 설정값) | 없음 | 인증 | 구현됨 |
| POST | /api/v1/auth/logout | 쿠키 삭제 | 로그인 | 인증 | 구현됨 |
| GET | /api/v1/auth/me | 현재 사용자·역할·`mustChangePassword` | 로그인 | 인증 | 구현됨 |
| POST | /api/v1/auth/password | 본인 비밀번호 변경(기대 `token_version` 조건부 증가 → 쿠키 재발급) | 로그인 | 인증 | 구현됨 |
| GET | /api/v1/users?page= | 사용자 목록(쪽당 50건, id 순) | 관리자 | 인증 | 구현됨 |
| POST | /api/v1/users | 사용자 생성 + 임시 비밀번호 발급 | 관리자 | 인증 | 구현됨 |
| GET | /api/v1/users/{id} | 사용자 하나 | 관리자 | 인증 | 구현됨 |
| PUT | /api/v1/users/{id} | 이름 · 소속 · 역할 · 사용 여부 교체 | 관리자 | 인증 | 구현됨 |
| POST | /api/v1/users/{id}/password-reset | 비밀번호 초기화(세션 회수 · 잠금 해제) + 임시 비밀번호 발급 | 관리자 | 인증 | 구현됨 |

---

## 업로드

파일을 받는 엔드포인트가 함께 쓰는 경계 검사다(`app/api/uploads.py`). 한도 값은 쓰는 엔드포인트가 정한다.

- 한도의 MB 는 1,048,576 바이트다(화면의 한도 표시와 같은 단위).
- 본문을 읽기 전에 `Content-Length` 로 막는다 — 없으면 411 `upload_length_required`, 한도(+ multipart 포장 여유)를 넘으면 413 `upload_too_large`.
  파일 크기의 정확한 검사는 파싱 뒤에 한 번 더 한다.
- 파일 이름은 경로를 떼고 이름만 쓴다. 비었거나 255자를 넘거나 제어 문자가 있으면 422 `upload_file_name_invalid`.
- 내려받기는 `app/api/downloads.py` 의 `content_disposition` 으로 첨부 헤더를 만든다(한글 이름은 `filename*`).

## 인증

### POST /api/v1/auth/login

- 권한: 없음. 요청 `{loginId, password}`. 응답 200: `{user:{id, loginId, name, role, mustChangePassword, defaultPage}}` + `Set-Cookie`(이름 `app_session`, httpOnly, SameSite=Lax, `Path=/api`, `Secure` 는 `COOKIE_SECURE` 설정값, 만료 `JWT_TTL_MINUTES`).
- `defaultPage` 는 로그인 직후 화면의 **경로**(새 계정은 `/`). 화면은 그 경로로 그대로 간다 — 등록되지 않은 경로를 다른 곳으로 대체하지 않는다(기조 5).
- 오류: 401 `auth_invalid_credentials` · 403 `auth_user_inactive` · 429 `auth_login_locked`. 아이디 없음과 비밀번호 틀림을 구분하지 않는다(응답 본문·응답 시간 모두).
- 잠금: 같은 계정의 연속 실패가 `LOGIN_MAX_FAILURES` 에 닿으면 그 실패부터 `LOGIN_LOCK_MINUTES` 동안 429 `auth_login_locked`(details `lockedUntil` — ISO 8601)이고,
  잠긴 동안은 비밀번호를 보지 않는다. 풀리면 0 부터 다시 센다. 성공하면 0 으로 되돌린다. 관리자 비밀번호 초기화가 잠금을 푼다.
  잠금은 계정 단위라 없는 아이디는 잠그지 않는다 — 출처(IP) 단위 제한은 앞단(프록시 · WAF)에서 한다.
  잠긴 계정의 429 는 계정이 있다는 것을 드러낸다 — 대입 공격을 멈추는 쪽을 택했다.
- 로그: 거부(아이디 없음 · 비밀번호 틀림 · 잠김 · 사용 중지)와 잠금은 `warning` 으로 아이디 · 사유를 남긴다. 비밀번호는 남기지 않는다.
- 설정값: `JWT_SECRET`(배포 환경의 비밀 저장소, 32바이트 이상) · `JWT_TTL_MINUTES` · `COOKIE_SECURE`(로컬 false, 배포 true) · `LOGIN_MAX_FAILURES` · `LOGIN_LOCK_MINUTES`. 이름은 backend-conventions 「설정」.
- 인증 제외 경로는 이 엔드포인트와 `/api/health`·`/api/health/ready` 뿐이다. API 문서(`/api/docs`)도 로그인 뒤에 열린다.

### POST /api/v1/auth/logout

- 권한: 로그인. 쿠키를 지운다(서버에 세션 상태가 없다). 응답 204.

### GET /api/v1/auth/me

- 권한: 로그인. 응답 200: 로그인 응답과 같은 `{user:{…}}`.

### POST /api/v1/auth/password

- 권한: 로그인(`must_change_password` 게이트 안에서도 허용). 요청 `{currentPassword, newPassword}`. 현재 비밀번호 검증 → 규칙 검증 → 기대 `token_version` 조건부 증가 → `must_change_password` 해제 → 쿠키 재발급. 응답 200: 바뀐 사용자의 `{user:{…}}` + 새 `Set-Cookie`.
- 오류: 422 `auth_current_password_invalid`(현재 비밀번호 틀림 — 세션은 유효하므로 401 이 아니다. 화면은 그 칸 아래에 보인다) · 422 `auth_password_rule_violation`(details `rule`: `too_short` · `too_long` · `whitespace`) · 409 `auth_token_version_stale`(그 사이 관리자가 회수함 — 다시 로그인).

## 사용자 관리

모든 경로가 관리자 전용(`RequireAdmin`, 아니면 403 `auth_forbidden`)이다. 코드는 `app/domains/auth/users.py` · `users_router.py`.
사용자 응답 `user` 의 칸: `{id, loginId, name, org, role, isActive, mustChangePassword, lockedUntil, createdAt, updatedAt}` —
`lockedUntil` 은 잠금이 풀리는 시각(잠긴 적 없으면 null, 지난 시각이면 이미 풀림).

- 계정을 지우는 경로는 없다. 그만 쓰는 계정은 사용 중지한다(다른 테이블의 사람 칸이 FK 로 가리킨다).
- 사용 중지 · 역할 변경은 다음 요청부터 먹는다(미들웨어가 매 요청 DB 행을 읽는다).
- 관리자는 자기 역할 · 사용 여부를 바꾸거나 자기 비밀번호를 초기화하지 않는다 — 409 `user_self_change_forbidden`(details `action`: `update` · `password_reset`).
  자기 비밀번호는 `/auth/password` 로 바꾼다.
- 활성 관리자는 늘 한 명 이상 남는다 — 마지막 활성 관리자를 강등 · 사용 중지하면 409 `user_last_admin_required`. 활성 관리자 행을 잠그고 세므로
  두 관리자가 동시에 서로를 강등해도 한쪽만 된다.
- 임시 비밀번호는 생성 · 초기화 응답에서 한 번만 보인다. 서버는 해시만 두고 로그에 남기지 않는다.

### GET /api/v1/users?page=

- `page` 필수(1 ~ `MAX_PAGE`). 응답 200: `PageEnvelope` — `{rows:[user…], total, pageCount}`.

### POST /api/v1/users

- 요청 `{loginId, name, org, role}`(길이는 app_user 컬럼과 같다, 역할 값은 프로젝트가 정할 때까지 자유 문자열). 응답 201: `{user, temporaryPassword}`.
  새 계정은 `mustChangePassword=true` · `defaultPage="/"`.
- 오류: 409 `user_login_id_taken`(details `loginId`).

### GET /api/v1/users/{id}

- 응답 200: `{user}`. 없으면 404 `resource_not_found`.

### PUT /api/v1/users/{id}

- 요청 `{name, org, role, isActive}` — 전체 교체라 칸을 모두 보낸다. 응답 200: `{user}`.
- 오류: 404 `resource_not_found` · 409 `user_self_change_forbidden` · 409 `user_last_admin_required`.

### POST /api/v1/users/{id}/password-reset

- `token_version` 을 무조건 올려 그 계정의 세션을 모두 끊고, 잠금을 풀고, 다음 로그인에 비밀번호를 바꾸게 한다. 응답 200: `{user, temporaryPassword}`.
- 오류: 404 `resource_not_found` · 409 `user_self_change_forbidden`.

---

## 오류 code

정본은 `backend/app/api/error_contract.py` 다. 도메인을 더하면 그 도메인의 code 를 이 표와 코드에 함께 더한다.

| code | status | 도메인 |
|---|---|---|
| resource_not_found | 404 | 공통 |
| method_not_allowed | 405 | 공통 |
| request_validation_failed | 422 | 공통 |
| request_origin_forbidden | 403 | 공통(출처 검사) |
| internal_failure | 500 | 공통 |
| database_unavailable · storage_unavailable | 503 | 시스템 |
| auth_invalid_credentials · auth_required | 401 | 인증 |
| auth_user_inactive · auth_forbidden · auth_password_change_required | 403 | 인증 |
| auth_token_version_stale | 409 | 인증 |
| auth_current_password_invalid · auth_password_rule_violation | 422 | 인증 |
| auth_login_locked | 429 | 인증 |
| user_login_id_taken · user_self_change_forbidden · user_last_admin_required | 409 | 사용자 관리 |
| upload_length_required | 411 | 업로드 공통 |
| upload_too_large | 413 | 업로드 공통 |
| upload_file_name_invalid | 422 | 업로드 공통 |

---

## 워커 — 비동기 작업 ([결정 0005](../decisions/0005-비동기-작업은-Postgres-작업-행과-워커로-처리한다.md))

시스템의 비동기 작업은 전부 Postgres 작업 행 + 워커 프로세스(`python -m app.worker`)로 처리한다. 공용 틀은 `app/worker/`, 작업 함수는 도메인 폴더(`domains/<domain>/jobs.py`)에 둔다.
처음에는 등록된 소비자가 없다 — 작업 큐를 만드는 기능이 `app/worker/__main__.py` 의 `CONSUMERS` · `PERIODIC` 에 한 줄씩 더하고, 그 소비자의 절을 여기에 쓴다.

- 즉시형 작업: 작업 행을 `SELECT … FOR UPDATE SKIP LOCKED LIMIT n` 으로 집는다 — 집을 행은 CTE 에서 한 번만 고른다(`WITH picked AS MATERIALIZED (SELECT … LIMIT n FOR UPDATE SKIP LOCKED) UPDATE … FROM picked`). `UPDATE … WHERE id IN (SELECT … LIMIT n …)` 꼴은 실행 계획이 안쪽 SELECT 를 다시 돌리면 n 건을 넘겨 집는다. API 가 행을 커밋한 뒤 `NOTIFY` 를 보내고 워커는 전용 접속으로 `LISTEN` 해 즉시 깨어난다. 알림 유실에 대비한 보조 폴링은 60초(설정값 `WORKER_POLL_SECONDS` — 고아 회수로 큐에 돌아온 작업도 이 폴링이 집는다). 커넥션 풀러(PgBouncer transaction 모드 등)를 도입하면 알림 접속만 우회시킨다.
- 예약형 작업: 행에 `next_attempt_at` 을 두고 워커 타이머가 집는다. 외부 호출 작업은 `attempt`·`last_error` 를 남긴다.
- 동시성: 워커 프로세스 안에서 소비자(작업 큐)마다 세마포어로 동시 처리 수를 정한다(설정값 `WORKER_<소비자>_CONCURRENCY` — 메모리 · CPU · 외부 API 상한이 근거). 한 프로세스의 합은 10 이하(스토리지 클라이언트의 기본 연결 풀 — 올리려면 `storage.build_client` 의 `max_pool_connections` 도 함께). 프로세스 수는 배포 설정이 정한다.
- 집기 · 완료 펜싱: 집을 때 `claimed_at=now(), attempt=attempt+1`. 완료 UPDATE 는 `WHERE <진행 중 상태> AND attempt=집을 때 값` — 0건이면 고아 회수 뒤 다른 워커가 처리한 것이라 결과를 버린다(롤백).
- 실패: 다시 해도 같은 결과인 실패(입력이 깨짐 등)는 바로 실패 상태와 사유로 끝낸다. 그 밖의 예외(DB · 저장소)는 사유만 남기고 진행 중 상태를 그대로 둔다 — 고아 회수가 다시 큐에 넣으므로 그 시간이 자연 백오프다.
- 고아 회수: 진행 중인데 `claimed_at` 이 `WORKER_<소비자>_ORPHAN_MINUTES` 지난 행은 큐로 되돌린다. `attempt` 가 상한(`WORKER_MAX_ATTEMPTS`)이면 실패로 끝내고 사유 앞에 `attempts_exhausted: ` 를 붙인다(기존 사유 보존).
