# DB 스키마 정의

> 상태: **틀** — 공통 규칙과 인증 테이블만 정의되어 있다. 기능을 만들 때 「테이블 목록」에 줄을 더하고 도메인별 절을 쓴다.
> 설계 결정은 [docs/decisions](../decisions/README.md)가 근거다. 어휘는 CLAUDE.md 공통 어휘를 따른다. 구현되면 코드(`backend/app/domains/*/models.py`)가 정본이다.

## 공통 규칙 (모든 테이블)

- PK `id BIGINT GENERATED ALWAYS AS IDENTITY`. 화면에 보이는 업무 ID 는 별도 컬럼 + unique.
- 시각 `created_at`·`updated_at` (timestamptz). 테이블 이름은 영문 snake_case 단수.
- `created_at` 은 DB 기본값(`now()`)이 채우고, `updated_at` 은 ORM `onupdate` 가 갱신한다. 마이그레이션 · 직접 SQL 은 `onupdate` 를 거치지 않으므로 기존 행을 고치는 UPDATE 에 **`updated_at = now()` 를 직접 넣는다**. 빠뜨리면 「수정자 NULL + `updated_at` > `created_at` = 시스템이 고침」을 구분할 수 없다.
- 상태값은 `VARCHAR + CHECK`. JSON 은 JSONB.
- 테이블 · 컬럼마다 DB 설명(`COMMENT ON`)이 있다 — 아래 표 설명에서 「이 칸이 무엇인지」 한 줄만 옮긴 것이고 정본은 모델의 `comment` 다. 업무 규칙 · 근거는 이 문서에 둔다.
- 상세 규약은 `.claude/skills/backend-conventions/SKILL.md` 「모델」.
- 아래 표의 「NULL = Y」는 **그 값이 없는 것이 정상인 경우**에만 쓴다(기조 5). 조건부 NOT NULL 은 CHECK 로 건다.
- 「미정」 표시가 있는 값 목록은 확인 주체가 정할 때까지 시드를 넣지 않는다. 컬럼 이름과 NOT NULL 은 고정이다.
- 「누가」는 행위별 칸만 둔다(`registered_by` · `confirmed_by` · `closed_by` …). 시스템(워커 등)이 쓰는 테이블에는 두지 않는다. **사람이 화면에서 고치는 마스터**(코드 표 · 설정 등)에는 `created_by` · `updated_by` 를 두고, 조회 API 응답에 등록 · 수정 일시와 사람 네 필드를 모두 싣는다(화면이 쓰지 않아도). 시드로 들어간 행의 등록자 · 수정자는 NULL 이고 「시스템(시드)」을 뜻한다.

## 테이블 목록

「담당 기능」이 들어가는 코드 폴더는 [api.md 「코드 도메인(폴더)」](api.md#코드-도메인폴더) 표가 정한다.

| 테이블 | 한 줄 설명 | 공통 여부 | 담당 기능 | 상태 |
|---|---|---|---|---|
| app_user | 사용자 | 공통 | 인증·권한 | 확정(역할 값 미정, 결정 0006) |

## 관계도

```
app_user ← (사람이 남는 칸: created_by · updated_by · <행위>_by)
```

**저장하지 않고 파생하는 값**은 이 절에 적는다 — 함수 하나로 계산하고 목록·상세가 같은 값을 쓴다.

---

## 인증·권한 (결정 0006)

### app_user — 사용자

| 컬럼 | 타입 | NULL | 제약 | 설명 |
|---|---|---|---|---|
| id | bigint | N | PK | |
| login_id | varchar(64) | N | unique | |
| name | varchar(100) | N | | |
| org | varchar(100) | N | | 소속 |
| role | varchar(32) | N | 값 목록 미정 — CHECK 없음 | 시드 관리자 `admin` |
| is_active | boolean | N | | 「중지」 |
| password_hash | varchar(255) | N | | |
| token_version | int | N | ≥ 0 | 쿠키 JWT 무효화 카운터. 매 요청 대조 |
| must_change_password | boolean | N | | 관리자 생성 · 초기화 후 |
| failed_login_count | int | N | ≥ 0 | 연속 로그인 실패 횟수. 성공 · 잠금 · 관리자 초기화 때 0 |
| locked_until | timestamptz | Y | | 로그인 잠금이 풀리는 시각. null = 잠긴 적 없음, 지난 시각 = 풀림(api.md 「POST /api/v1/auth/login」) |
| default_page | varchar(32) | N | | 로그인 직후 화면의 경로. 새 계정은 `/`. 화면은 이 경로로 그대로 간다 |
| created_at · updated_at | timestamptz | N | | 공통 규칙 |

- 역할→메뉴·기능 표는 코드에 둔다. `user` 는 PostgreSQL 예약어라 `app_user`.
