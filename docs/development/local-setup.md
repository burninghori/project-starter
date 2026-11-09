# 로컬 개발 환경 세팅

모든 개발자가 **같은 도구·같은 버전·같은 명령**으로 개발하도록 맞추는 안내서다. 위에서부터 순서대로 하면 된다.
대상은 macOS(Apple Silicon)다. 끝까지 하면 마지막 「동작 확인」이 모두 통과해야 한다.

## 1. 설치할 것

| 도구 | 버전 | 용도 | 설치 | 확인 |
|---|---|---|---|---|
| Homebrew | 최신 | 패키지 관리 | https://brew.sh 의 설치 명령 | `brew --version` |
| git | 2.40+ | 형상 관리 | macOS 기본 또는 `brew install git` | `git --version` |
| uv | 0.13+ | Python 버전·패키지 관리 | `brew install uv` | `uv --version` |
| Python | 3.13 | backend | `uv python install 3.13` | `uv python list --only-installed` |
| fnm | 최신 | Node 버전 관리 | `brew install fnm` | `fnm --version` |
| Node.js | 26 (`.nvmrc`) | frontend | `fnm install 26` | `node --version` → v26.x |
| Docker Desktop | 최신 | 로컬 Postgres · S3 호환 스토리지 | https://www.docker.com/products/docker-desktop | `docker version` |
| VS Code | 최신 | 편집기 | https://code.visualstudio.com | `code --version` |
| Claude Code | 최신 | AI 개발 도구 | https://docs.claude.com/claude-code 의 설치 안내 | `claude --version` |
| GitHub CLI (gh) | 2.100+ | 이슈·PR 작업(사람과 Claude 공용) | `brew install gh` → 4절 로그인 | `gh --version` |

- Python 을 brew·pyenv 로 따로 설치하지 않는다. uv 가 프로젝트별로 3.13 을 쓴다(`backend/.python-version`).
- Node 를 brew 로 설치하지 않는다. fnm 이 저장소의 `.nvmrc`(26)를 따른다.
셸 스크립트 검사(`make verify` 에 포함)용으로 `brew install shellcheck shfmt`.

- pip·poetry·yarn·pnpm 을 쓰지 않는다. Python 은 uv, Node 는 npm 이다.

## 2. 셸 설정 (`~/.zshrc`)

아래를 `~/.zshrc` 끝에 추가하고 **새 터미널**을 연다.

```bash
# Node 버전 관리 — 저장소에 들어가면 .nvmrc 버전으로 자동 전환
eval "$(fnm env --use-on-cd --shell zsh)"

# Docker Desktop CLI — Docker Desktop 을 「사용자 설치」로 깔면 CLI 가 여기 있다
export PATH="$HOME/.docker/bin:$PATH"
```

- `fnm` 줄이 없으면 `fnm install` 을 했어도 터미널에서 `node`·`npm` 이 잡히지 않는다.
- Docker Desktop 이 설치돼 있는데 `docker: command not found` 가 나오면 두 번째 줄이 빠진 것이다.
  (또는 Docker Desktop → Settings → Advanced → 「System (requires password)」로 바꾸면 `/usr/local/bin` 에 설치된다.)

확인:

```bash
node --version      # v26.x
npm --version
docker version      # Client 와 Server 둘 다 나와야 한다(Server 가 없으면 Docker Desktop 을 실행)
```

## 3. VS Code

1. 명령 팔레트(⌘⇧P) → `Shell Command: Install 'code' command in PATH`.
2. 저장소 **루트 폴더**를 연다: `code <저장소 경로>`. backend·frontend 를 따로 열지 않는다.
3. 오른쪽 아래 「권장 확장 설치」를 누른다(`.vscode/extensions.json`: Python·Pylance·Ruff·ESLint·Prettier·Tailwind·EditorConfig·Claude Code).
4. 저장 시 자동 포맷(Python 은 Ruff, TS·CSS·JSON 은 Prettier)이 `.vscode/settings.json` 에 켜져 있다. 개인 설정으로 덮지 않는다.
5. Python 인터프리터는 `backend/.venv` 로 자동 지정된다. 아래 「5. 첫 설정」의 `make setup` 뒤에 잡힌다.

## 4. GitHub CLI 로그인

> 원격 저장소(GitHub)를 연결한 뒤에 한다. 저장소가 생기기 전에는 건너뛴다.

이슈·PR 은 `gh` 로 만든다. Claude 가 이슈를 만들거나 PR 을 올릴 때도 이 로그인을 쓴다 — **이슈·PR 작성자는 `gh` 에 로그인한
GitHub 계정으로 기록된다.** 공용 계정으로 작업하는 머신이면 그 계정으로 로그인한다.

```bash
# github.com 이면 --hostname 을 빼고, 사내 GitHub Enterprise 면 그 주소를 넣는다
gh auth login --hostname <사내 GitHub 주소> --git-protocol https --web --scopes workflow
```

1. 명령을 실행하면 **일회용 코드**(예: `ABCD-1234`)가 터미널에 나온다.
2. Enter 를 누르면 브라우저가 열린다. GitHub 에 로그인한 뒤 코드를 입력하고 권한을 승인한다.
3. 터미널에 `Logged in as <계정>` 이 나오면 끝.

- `--git-protocol https` 를 고르면 `git push`·`git pull` 도 같은 로그인을 쓴다(따로 SSH 키를 만들지 않아도 된다).
- `--scopes workflow` 는 `.github/workflows/` 파일을 push 할 때 필요하다. 빠지면 CI 설정을 올릴 때 push 가 거부된다.
- Claude Code 안에서 하려면 입력창에 `! gh auth login …` 처럼 `!` 를 붙여 실행한다(브라우저 인증이 필요해 Claude 가 대신할 수 없다).

확인:

```bash
gh auth status          # 로그인한 호스트·계정·권한(scopes)
gh repo view            # 저장소 폴더 안에서 실행하면 연결된 원격 저장소 정보
```

토큰이 만료되거나 권한을 바꿔야 하면 `gh auth refresh --scopes workflow`, 계정을 바꾸려면 `gh auth logout` 후 다시 로그인한다.

## 5. 첫 설정

```bash
git clone <저장소 주소> <폴더 이름>     # 원격 연결 전에는 저장소를 전달받아 같은 위치에 둔다
cd <폴더 이름>

make setup        # git hook 켜기 · backend: uv sync (.venv 생성) · frontend: npm ci · backend/.env 생성(.env.example 복사)
make local-up     # 로컬 컨테이너 — Postgres 17 (localhost:55434, app-postgres-1) · S3 호환 스토리지 SeaweedFS (localhost:8334, app-s3-1). 마지막에 1회성 s3-init 이 버킷을 만들고 끝난다
make db-migrate   # 마이그레이션 적용 + 앱 DB 계정(app_app) 생성·권한 정비
cd backend && uv run python -m app.domains.auth.seed_admin   # 관리자 계정(backend/.env 의 ADMIN_LOGIN_ID·ADMIN_INITIAL_PASSWORD). 이미 있으면 그대로
```

첫 관리자는 명령으로 만들고, 다른 계정은 관리자가 사용자 관리 API(`/api/v1/users` — api.md 「사용자 관리」, 화면은 프로젝트에서 만든다)로 만든다.
로그인 뒤 `http://localhost:8001/api/docs` 에서 API 를 직접 불러 볼 수 있다. `backend/` 에서:

| 명령 | 하는 일 |
|---|---|
| `uv run python -m app.domains.auth.seed_admin` | 관리자 계정. 첫 로그인 때 비밀번호를 바꿔야 한다 |
| `uv run python -m app.domains.auth.reset_password --login-id <id>` | 비밀번호를 잊었거나 계정이 잠겼을 때(관리자 본인 포함). 새 임시 비밀번호를 발급하고 그 계정의 기존 로그인을 모두 끊고 잠금을 푼다 |

| 포트 | 무엇 |
|---|---|
| 8001 | backend API (`make dev-backend`) |
| 5174 | frontend 개발 서버 (`make dev-frontend`) |
| 55434 | 로컬 Postgres (계정 postgres/postgres, 앱 계정 app_app/app_app) |
| 8334 | 로컬 S3 호환 스토리지 API (계정 app/app-secret, 버킷 app-files · app-files-test — `infra/local/seaweedfs/`) |
| 9334 | 로컬 S3 호환 스토리지 master (헬스체크·`weed shell`) |

같은 PC 에서 다른 프로젝트의 로컬 환경과 포트가 겹치면 README 「새 프로젝트 시작 시 바꿀 것」의 포트 위치를 한꺼번에 바꾼다.

`backend/.env` 는 개인 로컬 설정이다(커밋하지 않는다). 새 설정 키가 생기면 `.env.example` 이 먼저 바뀌므로, 부팅 오류가 나면 둘을 비교한다.

## 6. 동작 확인 — 전부 통과해야 세팅 완료

```bash
make verify
```

- backend: ruff · pyright · pytest(unit + integration — Postgres 와 S3 호환 스토리지를 실제로 상대한다) — 마지막 줄이 `N passed`
- frontend: 포맷 · 타입 · lint · 스타일 검사 · 테스트 · 빌드 — 마지막 줄이 `✓ built`
- 셸 스크립트: shellcheck · shfmt — 출력 없이 끝나면 통과

그다음 세 터미널에서:

```bash
make dev-backend     # 터미널 1
make dev-frontend    # 터미널 2
make dev-worker      # 터미널 3 — 비동기 작업 워커. 작업 큐(소비자)를 등록한 뒤에 쓴다
```

- http://127.0.0.1:8001/api/health/ready → `{"status":"ok"}` (DB 와 파일 버킷을 둘 다 확인한다)
- 워커 터미널에 `worker started` 와 `listener connected` 가 보인다(LISTEN 전용 접속 1개). 종료는 Ctrl+C — 진행 중 작업을 기다린 뒤 `worker stopped`
- http://localhost:5174 → 로그인 화면 → 관리자 계정(`backend/.env` 의 `ADMIN_LOGIN_ID`·`ADMIN_INITIAL_PASSWORD`)으로 로그인 → 비밀번호 변경 →
  「홈」 화면에 서버 · 데이터베이스 · 파일 저장소 연결 상태
- http://localhost:5174/api/docs → API 문서(Swagger). **로그인 뒤 같은 브라우저에서** 연다 — 모든 API 가 세션 쿠키를 요구해
  로그인 전에는 401 이다. 쿠키는 포트가 아니라 호스트 이름으로 나뉘므로 backend 에 직접 http://localhost:8001/api/docs 로 열어도
  되지만, `127.0.0.1:8001` 은 `localhost` 와 다른 호스트라 쿠키가 가지 않아 401 이다

## 7. Claude Code

- 저장소 **루트**에서 `claude` 를 실행한다. `CLAUDE.md`(공통 규약)는 자동으로 읽고, `.claude/skills/`(영역별 규약)·`.claude/agents/`(리뷰 에이전트)는
  이름과 설명만 알고 있다가 필요할 때 본문을 연다.
- 팀 공용 설정 `.claude/settings.json` 은 커밋돼 있다(force push, git hook 우회 차단). 개인 설정은
  `.claude/settings.local.json` 에 둔다(커밋하지 않는다).
- 규칙을 개인 프롬프트·개인 메모에 두지 않는다. 필요한 규칙은 CLAUDE.md·skill 을 고치는 변경으로 올린다([협업 방식](collaboration.md)).
- 자주 쓰는 요청 예:
  - "feature-slice skill 로 사용자 목록 기능을 만들어줘" — 기능 하나를 DB 부터 화면까지
  - "verify skill 로 검사 돌려줘" — 커밋 전 검사
  - "이 브랜치 리뷰해줘" — PR 전 자기 리뷰, 다른 사람의 PR 리뷰(메인 세션이 `pre-pr-review` 기준으로)
  - "리뷰 에이전트로 리뷰해줘" — 코드를 작성한 대화의 맥락 없이 새로 보는 리뷰(`pr-reviewer` 에이전트, 같은 기준)

## 8. 문제 해결

| 증상 | 원인 · 해결 |
|---|---|
| `node: command not found` | `~/.zshrc` 의 fnm 줄 누락. 2절 추가 후 새 터미널 |
| `docker: command not found` (Docker Desktop 설치됨) | `~/.docker/bin` 이 PATH 에 없음. 2절 |
| `Cannot connect to the Docker daemon` | Docker Desktop 앱이 꺼져 있음. 실행 후 다시 |
| `make local-up` 이 포트 55434·8334·9334 사용 중 | 다른 컨테이너·프로세스가 그 포트를 씀. `lsof -i :<포트>` 로 확인 |
| `make local-up` 의 `run --rm s3-init` 단계가 실패 | 버킷 생성 실패. 출력에 찍힌 `weed shell` 오류를 보고 `make local-up` 다시(이미 만든 버킷은 건너뛴다) |
| frontend 시작 시 `APP_PORT 가 필요하다` | `backend/.env` 없음. `make setup` |
| push 가 `pre-push: main 으로 직접 push 할 수 없다` 로 거부 | 의도한 차단이다(`.githooks/pre-push`). 작업 브랜치를 만들어 push 하고 PR 로 머지한다 |
| push 가 `pre-push: … 되감는 push(force push)는 할 수 없다` 로 거부 | 공유한 브랜치를 rebase·reset 으로 고쳐 쓴 것이다. `git merge` 로 맞춘다 |
| push 가 `pre-push: 원격 … 커밋이 로컬에 없어 … 판정할 수 없다` 로 거부 | 다른 사람이 같은 브랜치에 push 했다. `git fetch` 후 merge 하고 다시 push |
| **급해서 hook 을 우회해야 함** | 담당자 부재 중 배포본 긴급 수정처럼 PR 을 기다릴 수 없을 때만, **사람이 직접** `git push --no-verify` 로 우회하고 이유를 PR·Issue 에 남긴다. Claude 는 우회하지 못한다(`.claude/settings.json`) |
| push 가 hook 없이 그냥 됨 | hook 이 꺼져 있다. `make setup`(또는 `git config core.hooksPath .githooks`) |
| backend 부팅 시 `Field required` | `backend/.env` 에 새 키 누락. `.env.example` 과 비교 |
| backend 부팅 시 `jwt_secret … at least 32` | `JWT_SECRET` 이 32바이트보다 짧다. `.env.example` 의 값처럼 길게 |
| 로그인 화면에서 「아이디 또는 비밀번호가 맞지 않습니다」 | 관리자 계정을 아직 안 만들었다(`seed_admin`) 또는 `.env` 의 `ADMIN_*` 와 다른 값을 넣었다 |
| 비밀번호를 잊음 | `cd backend && uv run python -m app.domains.auth.reset_password --login-id <id>` — 임시 비밀번호로 로그인한 뒤 바꾼다 |
| `/api/docs` 가 401 | 로그인 전이거나, 로그인한 곳과 다른 호스트 이름으로 열었다(`localhost` 와 `127.0.0.1` 은 다른 호스트다). http://localhost:5174 에서 로그인한 뒤 http://localhost:5174/api/docs 또는 http://localhost:8001/api/docs |
| `/api/health/ready` 503 `database_unavailable` | Postgres 꺼짐 또는 마이그레이션 전. `make local-up && make db-migrate` |
| `/api/health/ready` 503 `storage_unavailable` | S3 호환 스토리지 꺼짐 또는 버킷 없음. `make local-up` (버킷은 자동 생성). `backend/.env` 의 `STORAGE_BUCKET`·`S3_*` 를 `.env.example` 과 비교 |
| integration 테스트가 접속 오류 | Postgres 또는 S3 호환 스토리지 꺼짐. `make local-up` (테스트 DB `app_test` 와 버킷 `app-files-test` 는 자동 생성) |
| 로컬 DB·스토리지를 처음부터 다시 | `make local-reset` (데이터 삭제 → 재기동 → 마이그레이션. 저장한 객체도 지워진다) |
| `npm ci` 가 install script 승인을 요구 | `package.json` 의 `allowScripts` 에 없는 새 패키지다. 승인 여부를 팀에 확인 후 `npm install-scripts approve <패키지>` |
| `gh: command not found` | `brew install gh` |
| `gh` 명령이 `authentication required`·`HTTP 401` | 로그인 안 됨 또는 만료. 4절 다시 실행, 또는 `gh auth refresh` |
| workflow 파일 push 가 `refusing to allow … without workflow scope` 로 거부 | `gh auth refresh --scopes workflow` |
| Python 패키지 추가 | `cd backend && uv add <패키지>` (개발용은 `uv add --dev`). `pyproject.toml`·`uv.lock` 둘 다 커밋 |
| npm 패키지 추가 | `cd frontend && npm install <패키지>` (개발용 `-D`). `package.json`·`package-lock.json` 둘 다 커밋 |
