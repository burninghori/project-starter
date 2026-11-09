"""실제 S3 호환 컨테이너(make local-up)를 상대로 한 put·get·delete 왕복과 조건부 저장, 접두사 목록·일괄 삭제."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

import app.api.health as health_module
from app.config import settings
from app.core.storage import (
    ObjectAlreadyExistsError,
    ObjectNotFoundError,
    Storage,
    StorageUnavailableError,
    build_client,
)
from tests.plugins.storage import unique_key


def test_bucket_is_reachable(storage: Storage) -> None:
    storage.check_bucket()


def test_put_then_stream_back(storage: Storage) -> None:
    key = unique_key()
    body = b'{"item": "ORD-0001"}'
    try:
        stored = storage.put_object(key, body, content_type="application/json")
        assert (stored.key, stored.size_bytes) == (key, len(body))
        assert stored.etag

        stream = storage.open_object(key, chunk_bytes=8)
        assert (stream.size_bytes, stream.content_type) == (len(body), "application/json")
        chunks = list(stream.chunks)
        assert len(chunks) > 1  # 정말 조각으로 온다
        assert b"".join(chunks) == body
        assert storage.read_object(key) == body
    finally:
        storage.delete_object(key)


def test_same_key_is_rejected_and_original_kept(storage: Storage) -> None:
    key = unique_key()
    try:
        storage.put_object(key, b"first", content_type="text/plain")
        with pytest.raises(ObjectAlreadyExistsError) as rejected:
            storage.put_object(key, b"second", content_type="text/plain")
        assert rejected.value.key == key
        assert storage.read_object(key) == b"first"
    finally:
        storage.delete_object(key)


def test_delete_then_not_found_and_key_reusable(storage: Storage) -> None:
    key = unique_key()
    storage.put_object(key, b"x", content_type="text/plain")
    storage.delete_object(key)

    with pytest.raises(ObjectNotFoundError):
        storage.open_object(key)
    storage.delete_object(key)  # 없는 키 삭제는 성공(S3 의미)

    try:
        storage.put_object(key, b"y", content_type="text/plain")  # 지운 뒤에는 같은 키를 다시 쓸 수 있다
    finally:
        storage.delete_object(key)


def test_prefix_lists_only_its_own_objects_and_deletes_them_all(storage: Storage) -> None:
    prefix = f"tests/{uuid4().hex}/"
    keys = [f"{prefix}{name}" for name in ("b.json", "a.json", "sub/c.json")]
    # 같은 글자로 시작하지만 다른 접두사 — 목록·삭제에 끌려 들어가지 않아야 한다
    sibling = f"{prefix[:-1]}-sibling/x.json"
    try:
        for key in keys:
            storage.put_object(key, b"x", content_type="application/json")
        storage.put_object(sibling, b"x", content_type="application/json")

        assert list(storage.iter_keys(prefix)) == sorted(keys)
        assert storage.delete_prefix(prefix) == len(keys)
        assert list(storage.iter_keys(prefix)) == []
        assert storage.delete_prefix(prefix) == 0  # 다시 돌려도 된다
        assert storage.read_object(sibling) == b"x"
        for key in keys:
            with pytest.raises(ObjectNotFoundError):
                storage.open_object(key)
    finally:
        storage.delete_object(sibling)
        for key in keys:
            storage.delete_object(key)


def test_missing_bucket_is_unavailable() -> None:
    missing = Storage(build_client(), f"{settings.storage_bucket}-missing")
    try:
        with pytest.raises(StorageUnavailableError):
            missing.check_bucket()
        with pytest.raises(StorageUnavailableError):
            missing.put_object(unique_key(), b"x", content_type="text/plain")
        with pytest.raises(StorageUnavailableError):
            list(missing.iter_keys("tests/missing/"))
    finally:
        missing.close()


def test_ready_reports_storage_unavailable(db_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    missing = Storage(build_client(), f"{settings.storage_bucket}-missing")
    monkeypatch.setattr(health_module, "get_storage", lambda: missing)
    try:
        response = db_client.get("/api/health/ready")
    finally:
        missing.close()

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "storage_unavailable"
