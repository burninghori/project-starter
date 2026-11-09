# 자주 쓰는 명령. 루트에서 `make <대상>`. 목록은 `make help`.

COMPOSE := docker compose -f infra/local/docker-compose.yml
# 마이그레이션은 스키마 변경 권한 계정(로컬 postgres)으로 돌고, 마지막에 앱 롤(app_app)을 정비한다.
# 앱(backend/.env)은 그 앱 롤로 붙는다. 배포도 같은 구조다(backend-conventions skill 「마이그레이션」).
MIGRATE_ENV := DB_USER=postgres DB_PASSWORD=postgres APP_DB_USER=app_app APP_DB_PASSWORD=app_app

.PHONY: help setup local-up local-down local-reset db-migrate dev-backend dev-worker dev-frontend \
        verify verify-backend verify-frontend verify-scripts gen-error-codes

help:
	@grep -E '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-16s %s\n", $$1, $$2}'

setup: ## git hook 켜기(main 직접 push·force push 차단), 의존성 설치(backend uv sync, frontend npm ci), backend/.env 가 없으면 예시에서 복사
	git config core.hooksPath .githooks
	cd backend && uv sync
	cd frontend && npm ci
	@test -f backend/.env || (cp backend/.env.example backend/.env && echo "backend/.env 를 만들었다")

local-up: ## 로컬 컨테이너 기동 — Postgres(55434)·S3 호환 스토리지(8334) + 버킷 생성
	$(COMPOSE) up -d --wait postgres s3
	$(COMPOSE) run --rm s3-init

local-down: ## 로컬 컨테이너 정지(데이터 유지)
	$(COMPOSE) down

local-reset: ## 로컬 컨테이너 데이터(DB·스토리지)를 지우고 다시 띄운 뒤 마이그레이션
	$(COMPOSE) down -v
	$(MAKE) local-up
	$(MAKE) db-migrate

db-migrate: ## 로컬 DB 에 마이그레이션 적용(alembic upgrade head)
	cd backend && $(MIGRATE_ENV) uv run alembic upgrade head

dev-backend: ## API 서버(http://127.0.0.1:8001, 코드 변경 시 재시작)
	cd backend && uv run python -m app

dev-worker: ## 워커 프로세스
	cd backend && uv run python -m app.worker

dev-frontend: ## 화면 개발 서버(http://localhost:5174, /api 는 backend 로 프록시)
	cd frontend && npm run dev

verify: verify-backend verify-frontend verify-scripts ## 커밋·PR 전 전체 검사

verify-backend: ## ruff · pyright · pytest(unit + integration, 로컬 컨테이너 필요: make local-up)
	cd backend && uv run ruff format --check . && uv run ruff check . && uv run pyright && uv run pytest

verify-frontend: ## 포맷 · 타입 · lint · 스타일 검사 · 테스트 · 빌드
	cd frontend && npm run verify

verify-scripts: ## 셸 스크립트(git hook · 로컬 버킷 생성) shellcheck · shfmt 검사 (brew install shellcheck shfmt)
	shellcheck .githooks/pre-push infra/local/seaweedfs/create-buckets.sh
	shfmt -d -i 2 -ci -bn .githooks/pre-push infra/local/seaweedfs/create-buckets.sh

gen-error-codes: ## 오류 code 목록(backend)을 frontend 타입으로 다시 생성
	cd backend && uv run python -m scripts.generate_error_codes

