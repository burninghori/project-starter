"""스토리지 설정의 경계 정규화 — 배포에서는 S3_* 가 비어 있고(실행 역할), 로컬은 컨테이너 계정을 넣는다."""

import os

import pytest
from pydantic import SecretStr, ValidationError

from app.config import Settings, settings

STORAGE_ENV_KEYS = ("AWS_REGION", "STORAGE_BUCKET", "S3_ENDPOINT_URL", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY")

_BASE = {
    "app_env": "test",
    "app_host": "127.0.0.1",
    "app_port": 8001,
    "app_reload": False,
    "log_level": "DEBUG",
    "db_host": "127.0.0.1",
    "db_port": 55434,
    "db_name": "app_test",
    "db_user": "postgres",
    "db_password": "postgres",
    "aws_region": "ap-northeast-2",
    "storage_bucket": "app-files-test",
}


@pytest.fixture(autouse=True)
def _no_storage_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # conftest 가 올린 .env.test 의 S3_* 가 섞이지 않게 — 이 파일의 테스트는 인자로 넘긴 값만 본다
    for key in STORAGE_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    assert not any(key in os.environ for key in STORAGE_ENV_KEYS)


def _settings(**overrides: object) -> Settings:
    # _env_file=None: 개발자의 backend/.env 를 읽지 않는다
    return Settings(_env_file=None, **{**_BASE, **overrides})  # pyright: ignore[reportCallIssue]


def test_blank_s3_values_mean_default_credential_chain() -> None:
    loaded = _settings(s3_endpoint_url="", s3_access_key_id="  ", s3_secret_access_key="")

    assert loaded.s3_endpoint_url is None
    assert loaded.s3_access_key_id is None
    assert loaded.s3_secret_access_key is None


def test_missing_s3_keys_mean_the_same_as_blank() -> None:
    loaded = _settings()

    assert (loaded.s3_endpoint_url, loaded.s3_access_key_id, loaded.s3_secret_access_key) == (None, None, None)


def test_local_container_values_are_kept() -> None:
    loaded = _settings(
        s3_endpoint_url="http://127.0.0.1:8334", s3_access_key_id="app", s3_secret_access_key="app-secret"
    )

    assert loaded.s3_endpoint_url == "http://127.0.0.1:8334"
    assert loaded.s3_access_key_id == "app"
    assert loaded.s3_secret_access_key == SecretStr("app-secret")


@pytest.mark.parametrize("partial", [{"s3_access_key_id": "app"}, {"s3_secret_access_key": "app-secret"}])
def test_half_credentials_fail_at_boot(partial: dict[str, str]) -> None:
    with pytest.raises(ValidationError, match="둘 다"):
        _settings(**partial)


def test_bucket_is_required() -> None:
    values = {key: value for key, value in _BASE.items() if key != "storage_bucket"}
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **values)  # pyright: ignore[reportCallIssue]


def test_test_env_points_at_the_test_bucket() -> None:
    # 테스트가 실수로 로컬 개발 버킷에 쓰지 않게 — .env.test 의 값
    assert settings.storage_bucket.endswith("-test")
