"""런타임 설정의 단일 출처 — 환경변수(로컬은 backend/.env)를 부팅 시 한 번 검증한다.

환경변수 이름은 배포 환경이 넣는 이름과 같다(결정 0002). 접두어를 붙이지 않는다 — 배포 환경도 `DB_HOST`·`APP_ENV` 로
주입한다.

필수 값에는 기본값을 두지 않는다. 빠진 값은 첫 요청이 아니라 부팅에서 실패해야 한다(기조 5).
배포 환경이 더 넘기는 값은 그 값을 쓰는 기능이 생길 때 필드로 추가한다.
그 전까지는 `extra="ignore"` 로 무시된다.
"""

import re
from typing import Annotated, Literal, Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

AppEnv = Literal["local", "test", "dev", "stg", "prod"]
LogLevel = Literal["TRACE", "DEBUG", "INFO", "WARNING", "ERROR"]

# 브라우저가 보내는 `Origin` 헤더 값의 모양 — scheme://host[:port], 경로 · 끝 슬래시 없음
_ORIGIN_PATTERN = re.compile(r"^https?://[^/\s]+$")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", frozen=True)

    # ---------- 실행 ----------
    # 로컬 local, 자동 테스트 test, 배포 환경은 dev·stg·prod
    app_env: AppEnv
    app_host: str
    app_port: int = Field(ge=1, le=65535)
    # 코드 변경 시 자동 재시작. 로컬 개발에서만 true
    app_reload: bool
    log_level: LogLevel

    # ---------- 데이터베이스 ----------
    # 배포에서는 DB_USER·DB_PASSWORD 에 앱 롤을 넣는다. 마이그레이션 작업은 같은 이름으로 스키마 변경 권한 계정을 받는다.
    db_host: str
    db_port: int = Field(ge=1, le=65535)
    db_name: str
    db_user: str
    db_password: SecretStr

    # ---------- 스토리지 (결정 0004) ----------
    # boto3 는 AWS_DEFAULT_REGION 만 읽는다. 리전은 AWS_REGION 으로 받아 명시적으로 넘긴다.
    aws_region: str
    storage_bucket: str
    # 로컬 S3 호환 컨테이너(infra/local/docker-compose.yml)용. 배포에서는 셋 다 비어 있고 실행 역할로 붙는다.
    # 「키 없음」과 「빈 문자열」은 같은 뜻(= boto3 기본 자격 증명 체인)이라 아래 validator 가 둘 다 None 으로 맞춘다 —
    # 빈 엔드포인트 문자열로 접속을 시도하지 않게 경계에서 한 번 정규화하는 것이고, 값이 있을 때의 fallback 이 아니다.
    s3_endpoint_url: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: SecretStr | None = None

    # ---------- 인증(결정 0006) ----------
    # 세션 쿠키 JWT(HS256) 서명 키 — HMAC-SHA256 권장 최소 길이 32바이트(RFC 7518). 배포에서는 비밀 저장소가 주입한다
    jwt_secret: SecretStr = Field(min_length=32)
    # 세션 만료(분). JWT exp 와 쿠키 Max-Age 가 같은 값을 쓴다
    jwt_ttl_minutes: int = Field(ge=1)
    # 세션 쿠키의 Secure 속성 — 로컬(http) false, 배포(https) true
    cookie_secure: bool
    # 로그인 잠금 — 같은 계정의 연속 실패가 이 횟수에 닿으면 그 계정을 일정 시간 잠근다
    login_max_failures: int = Field(ge=1)
    # 잠금 시간(분). 지나면 실패 횟수 0 에서 다시 센다
    login_lock_minutes: int = Field(ge=1)
    # 화면이 열리는 출처(쉼표로 여러 개). 쓰기 요청의 `Origin` 이 이 목록 밖이면 403 — CSRF 방어(middleware/origin_check.py)
    allowed_origins: Annotated[frozenset[str], NoDecode]

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        origins = frozenset(part.strip() for part in value.split(",") if part.strip())
        if not origins:
            raise ValueError("ALLOWED_ORIGINS 에 출처를 하나 이상 넣는다(예: https://app.example.com)")
        malformed = sorted(o for o in origins if not _ORIGIN_PATTERN.fullmatch(o))
        if malformed:
            raise ValueError(f"ALLOWED_ORIGINS 는 scheme://host[:port] 꼴이다(경로 · 끝 슬래시 없음): {malformed}")
        return origins

    @field_validator("s3_endpoint_url", "s3_access_key_id", "s3_secret_access_key", mode="before")
    @classmethod
    def _blank_means_unset(cls, value: object) -> object:
        if isinstance(value, str) and value.strip() == "":
            return None
        return value

    @model_validator(mode="after")
    def _s3_credentials_come_in_pairs(self) -> Self:
        if (self.s3_access_key_id is None) != (self.s3_secret_access_key is None):
            raise ValueError("S3_ACCESS_KEY_ID 와 S3_SECRET_ACCESS_KEY 는 둘 다 넣거나 둘 다 비운다")
        return self


class AdminSeedSettings(BaseSettings):
    """관리자 시드 명령(`python -m app.domains.auth.seed_admin`)만 읽는 값.

    앱 부팅 설정이 아니므로 `settings` 처럼 import 시점에 만들지 않는다 — 명령의 `main()` 이 만든다.
    api·worker 환경에는 이 값이 없어도 된다(backend-conventions 「설정」 표).
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", frozen=True)

    admin_login_id: str = Field(min_length=1, max_length=64)
    admin_initial_password: SecretStr


settings = Settings()  # pyright: ignore[reportCallIssue]  # 값은 환경변수에서 채운다
