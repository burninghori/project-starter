---
name: verify
description: 커밋·PR 전에 돌릴 검사와 테스트 작성 규칙. backend ruff·pyright·pytest(unit/integration 자동 분류), frontend npm run verify(포맷·타입·lint·스타일 검사·Vitest·빌드), 브라우저 확인. "테스트 돌려", "검증해", "테스트 어디에 써?" 류로 진행할 때, 테스트를 새로 작성할 때 사용한다. 리뷰 관점은 pre-pr-review skill.
---

# 검사와 테스트

## 커밋·PR 전 — 바꾼 쪽은 전부 돌린다

### backend (`backend/` 에서)

```bash
uv run ruff format . && uv run ruff check .
uv run pyright
uv run pytest -m unit                 # 컨테이너 없이, 몇 초
uv run pytest -m integration          # 로컬 Postgres·S3 호환 스토리지 필요(make local-up)
```

또는 루트에서 `make verify-backend`(unit + integration). 컨테이너가 꺼져 있으면 integration 이 접속 오류로 실패한다 —
**그것을 통과로 보고하지 않는다.** 돌리지 못했으면 못 했다고 쓴다.

### frontend (`frontend/` 에서)

```bash
npm run verify     # format:check → typecheck → lint → lint:styles → test → build
```

실패하면 `npm run format` 으로 포맷을 맞추고 나머지는 원인을 고친다. lint·타입 오류를 `eslint-disable`·`as any`·`@ts-ignore` 로
덮지 않는다(정말 필요하면 이유를 주석으로).

### 셸 스크립트 (`.githooks/` · `infra/local/` 의 셸 스크립트를 바꿨으면)

```bash
make verify-scripts   # shellcheck + shfmt(-i 2 -ci -bn) — brew install shellcheck shfmt
```

shellcheck 지적을 `# shellcheck disable=` 로 덮을 때는 그 줄에 이유를 적는다. 셸 스크립트를 새로 더하면 Makefile 의 `verify-scripts` 대상에도 더한다.

### 브라우저 확인 (화면을 바꿨으면)

`make dev-backend` + `make dev-frontend` → http://localhost:5174. 바꾼 화면의 **모든 조작 요소를 실제로 눌러 본다**(기조 3).
로딩·오류·빈 상태도 확인한다(backend 를 끄면 오류 상태를 볼 수 있다).

## 테스트 작성 규칙

### backend

| 종류 | 위치 | 언제 | 픽스처 |
|---|---|---|---|
| unit | `tests/unit/<domain>/` | DB 없는 로직 — 계산, 변환, 입력 검증 | `client`(DB 를 건드리지 않는 API) |
| integration | `tests/integration/<domain>/` | DB·스토리지를 거치는 서비스·API | `db_session`(롤백됨), `db_client`(API 왕복, 실제 commit), `storage`(테스트 버킷의 `Storage`, 만든 객체는 테스트가 지운다) |

- 분류는 자동이다: DB·스토리지 픽스처를 쓰면 integration, 아니면 unit(`tests/plugins/markers.py`).
- 테스트 DB(`app_test`)는 세션마다 새로 만들고 **실제 마이그레이션**을 적용한다. 모델만 고치고 마이그레이션을 빠뜨리면 여기서 깨진다.
- `db_client` 로 만든 데이터는 커밋된다. 테스트마다 이름·업무 ID 를 다르게 만들어 서로 간섭하지 않게 한다.
- 업무 규칙(계산 · 상태 전이 · 입력 검증)은 순수 함수로 두고 **입력 → 결과** 표 형태(`pytest.mark.parametrize`)로 촘촘히 테스트한다.
  샘플 입력 파일은 `tests/fixtures/` 에 둔다.
- 오류 경로도 테스트한다: 404·409·422 응답의 `error.code`.

### frontend

| 종류 | 위치 | 방법 |
|---|---|---|
| 순수 함수 | 같은 폴더 `*.test.ts` | 그대로 호출 |
| 화면·컴포넌트 | 같은 폴더 `*.test.tsx` | `vi.spyOn(<domain>Api, "list")` 로 API 를 가로채고 실제 훅·화면을 그린다 |

- 가로채는 지점은 `<domain>Api` 객체 하나다. `fetch` 를 화면 테스트마다 흉내 내지 않는다(전송 계층은 `transport.test.ts` 가 맡는다).
- 찾을 때는 역할·이름으로(`getByRole("button", { name: "저장" })`). CSS 클래스·test id 에 기대지 않는다.
- 로딩·성공·오류 세 상태를 테스트한다.
- 예시: `src/app/pages/home/HomePage.test.tsx`, `src/components/overlay/Modal.test.tsx`.

## CI

PR 마다(그리고 main 에 들어간 뒤) `.github/workflows/ci.yml` 이 위와 같은 검사를 돌린다 — backend 는 로컬과 같은 `infra/local/docker-compose.yml`(Postgres·S3 호환 스토리지)을 띄워 integration 까지, frontend 는 `npm run verify`.
CI 는 로컬 검사를 대신하지 않는다. PR 을 올리기 전에 로컬에서 먼저 돌리고, CI 가 빨간불이면 머지하지 않는다.
검사 목록을 바꾸면 루트 `Makefile` 의 verify 대상과 CI 를 함께 고친다. 테스트가 새 컨테이너를 필요로 하면 그 PR 에서 `infra/local/docker-compose.yml` 에 더한다(CI 가 같은 파일을 쓴다).
