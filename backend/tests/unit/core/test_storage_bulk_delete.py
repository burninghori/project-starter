"""접두사 일괄 삭제의 나눔·거부 처리 — S3 호출을 흉내 내는 작은 클라이언트로 본다(실제 컨테이너 왕복은 integration)."""

from typing import Any, cast

import pytest

from app.core.storage import DELETE_BATCH_SIZE, Storage, StorageUnavailableError


class _Paginator:
    def __init__(self, keys: list[str]) -> None:
        self._keys = keys

    def paginate(self, *, Bucket: str, Prefix: str) -> list[dict[str, Any]]:  # noqa: N803 — boto3 인자 이름
        matching = [key for key in self._keys if key.startswith(Prefix)]
        pages = [
            {"Contents": [{"Key": key} for key in matching[start : start + 500]]}
            for start in range(0, len(matching), 500)
        ]
        return pages or [{}]


class _FakeS3:
    """`list_objects_v2` 쪽 나눔과 `delete_objects` 호출만 흉내 낸다."""

    def __init__(self, keys: list[str], *, rejected: list[str] = []) -> None:  # noqa: B006 — 읽기만 한다
        self.keys = keys
        self.rejected = rejected
        self.deletes: list[list[str]] = []

    def get_paginator(self, name: str) -> _Paginator:
        assert name == "list_objects_v2"
        return _Paginator(self.keys)

    def delete_objects(self, *, Bucket: str, Delete: dict[str, Any]) -> dict[str, Any]:  # noqa: N803
        keys = [item["Key"] for item in Delete["Objects"]]
        self.deletes.append(keys)
        errors = [{"Key": key, "Code": "AccessDenied"} for key in keys if key in self.rejected]
        return {"Errors": errors} if errors else {}


def _storage(fake: _FakeS3) -> Storage:
    return Storage(cast(Any, fake), "bucket")


def test_deletes_in_batches_of_the_s3_limit_and_counts_all() -> None:
    keys = [f"files/1/2/{index}.json" for index in range(DELETE_BATCH_SIZE + 1)]
    fake = _FakeS3([*keys, "files/1/3/other.json"])

    assert _storage(fake).delete_prefix("files/1/2/") == DELETE_BATCH_SIZE + 1
    assert [len(chunk) for chunk in fake.deletes] == [DELETE_BATCH_SIZE, 1]
    assert sorted(key for chunk in fake.deletes for key in chunk) == sorted(keys)


def test_empty_prefix_deletes_nothing_and_calls_nothing() -> None:
    fake = _FakeS3(["files/9/1/a.json"])

    assert _storage(fake).delete_prefix("files/9/2/") == 0
    assert fake.deletes == []


def test_partial_rejection_is_reported_not_swallowed() -> None:
    fake = _FakeS3(["p/a.json", "p/b.json"], rejected=["p/b.json"])

    with pytest.raises(StorageUnavailableError, match=r"AccessDenied: p/b\.json"):
        _storage(fake).delete_prefix("p/")


def test_prefix_must_be_well_formed_before_any_call() -> None:
    fake = _FakeS3(["p/a.json"])

    with pytest.raises(ValueError):
        _storage(fake).delete_prefix("p")
    with pytest.raises(ValueError):
        list(_storage(fake).iter_keys("/p/"))
    assert fake.deletes == []
