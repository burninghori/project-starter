"""객체 키 규칙 — 키는 DB 의 storage_key 에 그대로 들어가므로 형식을 코드가 보장한다."""

import pytest
from botocore.exceptions import ClientError, EndpointConnectionError

from app.core.storage import (
    MAX_KEY_CHARS,
    ObjectAlreadyExistsError,
    ObjectNotFoundError,
    StorageUnavailableError,
    storage_error_from,
    validate_key,
    validate_prefix,
)


@pytest.mark.parametrize("prefix", ["", "/", "files/7", "/files/7/", "files//7/", "files/../7/", "a b/"])
def test_validate_prefix_rejects_malformed(prefix: str) -> None:
    with pytest.raises(ValueError):
        validate_prefix(prefix)


@pytest.mark.parametrize("prefix", ["a/", "files/7/", "tests/abc-1/"])
def test_validate_prefix_accepts_well_formed(prefix: str) -> None:
    assert validate_prefix(prefix) == prefix


@pytest.mark.parametrize(
    "key",
    [
        "",
        "/leading-slash",
        "double//slash",
        "trailing/",
        "dots/../escape",
        ".hidden",
        "space in key",
        "한글",
        "a" * (MAX_KEY_CHARS + 1),
    ],
)
def test_validate_key_rejects_malformed(key: str) -> None:
    with pytest.raises(ValueError):
        validate_key(key)


@pytest.mark.parametrize("key", ["a", "files/1/2/3.json", "x_y.z-1/B", "a" * MAX_KEY_CHARS])
def test_validate_key_accepts_well_formed(key: str) -> None:
    assert validate_key(key) == key


def _client_error(code: str) -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": code}}, "PutObject")


def test_precondition_failed_means_object_exists() -> None:
    error = storage_error_from(_client_error("PreconditionFailed"), key="k")

    assert isinstance(error, ObjectAlreadyExistsError)
    assert error.key == "k"


@pytest.mark.parametrize("code", ["NoSuchKey", "404"])
def test_missing_object_codes_mean_not_found(code: str) -> None:
    assert isinstance(storage_error_from(_client_error(code), key="k"), ObjectNotFoundError)


def test_bucket_level_404_is_unavailable_not_object_not_found() -> None:
    # HeadBucket 의 404 는 버킷이 없는 것이다 — 객체 없음으로 오해하지 않는다
    assert isinstance(storage_error_from(_client_error("404"), key=None), StorageUnavailableError)


def test_other_failures_are_unavailable() -> None:
    assert isinstance(storage_error_from(_client_error("AccessDenied"), key="k"), StorageUnavailableError)
    connection = EndpointConnectionError(endpoint_url="http://127.0.0.1:1")
    assert isinstance(storage_error_from(connection, key="k"), StorageUnavailableError)
