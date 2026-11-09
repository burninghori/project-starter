# (서비스 이름)

(한 줄 소개 — 프로젝트를 시작할 때 채운다.)

새 풀스택 프로젝트를 시작할 때 복제해서 쓰는 저장소다. 인증(자체 계정 · JWT 쿠키), 오류 응답 계약, 로깅, 마이그레이션 체인,
Postgres 작업 큐 워커, S3 호환 파일 저장소, 디자인 시스템 · 앱 셸, 검사(CI) · AI 리뷰 · 협업 규약이 들어 있고 업무 기능은 없다.
처음 한 번 아래 「새 프로젝트 시작 시 바꿀 것」을 끝낸다.

| 영역 | 기술 |
|---|---|
| backend | Python 3.13 · FastAPI · SQLAlchemy 2.0 async · Alembic · PostgreSQL 17 (패키지 관리 uv) |
| frontend | React 18 · TypeScript 5.6 · Vite 6 · Tailwind CSS 4 · React Router 7 · TanStack Query 5 · Zustand 5 |
| 로컬 실행 | Docker Compose — Postgres · S3 호환 스토리지(SeaweedFS) |

개발 규약은 [CLAUDE.md](CLAUDE.md), 협업 방식은 [docs/development/collaboration.md](docs/development/collaboration.md).

## 새 프로젝트 시작 시 바꿀 것

메인 개발자가 첫 작업으로 한 번 한다(collaboration.md 1절 「① 골격」). 끝나면 이 절을 지워도 된다.

**짧은 이름 `app`** — 코드 · 설정 곳곳의 프로젝트 짧은 이름이다. 그대로 써도 동작한다. 바꾸려면 아래를 한 번에 바꾸고
`grep -rnw app --exclude-dir=node_modules --exclude-dir=.venv .` 로 남은 곳을 확인한다(파이썬 패키지 `backend/app/` 와 import 경로
`app.` 은 짧은 이름이 아니다 — 바꾸지 않는다).

- [ ] 로컬 컨테이너: `infra/local/docker-compose.yml`(compose 프로젝트 `name`, `POSTGRES_DB`, 버킷 목록),
      `infra/local/seaweedfs/`(S3 계정 · 버킷)
- [ ] backend 설정: `backend/.env.example` · `backend/.env.test`(`DB_NAME` · `DB_USER` · `DB_PASSWORD` · `STORAGE_BUCKET` · `S3_*`),
      루트 `Makefile` 의 앱 롤(`APP_DB_USER` · `APP_DB_PASSWORD`)
- [ ] 로거 이름: `backend/app/logging.py` 의 `APP_LOGGER_ROOT`
- [ ] 세션 쿠키 이름 `app_session`: `backend/app/domains/auth/tokens.py` 의 `SESSION_COOKIE`(api.md 「인증」도 함께)
- [ ] API 문서 제목 「App API」: `backend/app/main.py` 의 FastAPI `title`
- [ ] CSS 접두어 `app-`: `frontend/src/styles/app/`(폴더 이름 포함), 클래스를 쓰는 컴포넌트, `frontend/scripts/check-styles.mjs`,
      `.vscode/settings.json` 의 Tailwind 설정 경로, 디자인 문서 `frontend/docs/design/app-ui-spec.md`
- [ ] 로컬 DB 를 이미 띄웠다면 `make local-reset` 으로 새 이름의 DB · 버킷을 만든다

**포트** — 같은 PC 에서 다른 프로젝트의 로컬 환경과 겹치지 않게 고른다. 바꾸면 아래를 함께 바꾼다.

| 무엇 | 기본 | 바꾸는 곳 |
|---|---|---|
| backend API | 8001 | `backend/.env.example` 의 `APP_PORT`, `.claude/launch.json` |
| frontend 개발 서버 | 5174 | `frontend/vite.config.ts`, `.claude/launch.json`, `backend/.env.example` · `.env.test` 의 `ALLOWED_ORIGINS` |
| Postgres | 55434 | `infra/local/docker-compose.yml`, `backend/.env.example` · `.env.test` 의 `DB_PORT` |
| S3 호환 스토리지 API · master | 8334 · 9334 | `infra/local/docker-compose.yml`, `backend/.env.example` · `.env.test` 의 `S3_ENDPOINT_URL` |

포트를 바꾼 뒤 [로컬 개발 환경 세팅](docs/development/local-setup.md)의 포트 표 · 확인 주소도 고친다.

**이름 · 문서 · 사람**

- [ ] 서비스 이름: 이 README 제목, [CLAUDE.md](CLAUDE.md) 첫 줄과 서비스 소개, `frontend/index.html` 의 `<title>`, 화면 브랜드 문구
      (`frontend/src/app/brand.ts` — 서비스명 · 마크 · 부제 · 로그인 설명)
- [ ] [CLAUDE.md](CLAUDE.md) 「도메인 원칙」 · 「공통 어휘」 — 정해지는 대로 채운다
- [ ] [CLAUDE.md](CLAUDE.md) 「git」 의 개발자 표(역할 · GitHub 계정), [collaboration.md](docs/development/collaboration.md) 2절의
      인증 · 권한 담당자
- [ ] 배포 환경을 만들 때: 화면 도메인을 `ALLOWED_ORIGINS` 에 넣는다(빠지면 화면의 모든 쓰기 요청 · 로그인이 403),
      `COOKIE_SECURE=true`, `JWT_SECRET` 은 비밀 저장소로(backend-conventions 「설정」)
- [ ] 디자인 토큰(색 · 글꼴)을 프로젝트에 맞추면 `frontend/docs/design/` 의 디자인 정의도 함께

**git · GitHub**

- [ ] `make setup` — git hook(main 직접 push · force push 차단)을 켠다. 개발자마다 한 번
- [ ] 첫 커밋 뒤 GitHub 저장소를 만들고 연결한다
- [ ] 저장소 시크릿 `CLAUDE_CODE_OAUTH_TOKEN` 등록(AI 리뷰 — [collaboration.md 7절](docs/development/collaboration.md#7-github-구성))
- [ ] 라벨 `triage` · `ready` · `deferred` · `skip-ai-review` 만들기, main 브랜치 보호(룰셋)

## 처음 한 번 — 개발 환경

설치·셸 설정·VS Code·첫 설정·동작 확인까지 **[로컬 개발 환경 세팅](docs/development/local-setup.md)** 을 순서대로 따른다.
요약하면:

```bash
brew install uv fnm gh shellcheck shfmt && uv python install 3.13 && fnm install 26   # + Docker Desktop, ~/.zshrc 설정, gh 로그인
make setup && make local-up && make db-migrate && make verify
```

## 매일

```bash
make dev-backend    # http://127.0.0.1:8001  (API 문서 /api/docs)
make dev-frontend   # http://localhost:5174  (/api 는 backend 로 프록시)
make verify         # 커밋·PR 전 전체 검사
```

`make help` 로 전체 명령을 본다.

## 구조

```
backend/            API · 워커 · 마이그레이션 (컨테이너 하나, 명령만 다름)
frontend/           화면. docs/design/ 에 디자인 정의
docs/               협업 방식 · 명세 · 설계 결정 기록
infra/local/        로컬 전용 — docker-compose.yml(Postgres · S3 호환 스토리지)·seaweedfs/
.claude/            AI(Claude Code) 공용 설정 · skill · 리뷰 에이전트
.github/            CI · AI 리뷰 · PR 템플릿
```

## 문제 해결

[로컬 개발 환경 세팅 — 문제 해결](docs/development/local-setup.md#8-문제-해결)
