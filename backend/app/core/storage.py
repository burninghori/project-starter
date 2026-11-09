"""객체 스토리지 — 로컬(SeaweedFS)·배포(S3)를 코드 경로 하나로 다룬다(결정 0004).

boto3 + `S3_ENDPOINT_URL` + path-style 하나다. 로컬과 배포의 차이는 설정 값뿐이고 코드에 분기가 없다(기조 2).

- **객체는 덮어쓰지 않는다.** `put_object` 는 조건부 저장(`If-None-Match: *`)이라 같은 키가 이미 있으면
  `ObjectAlreadyExistsError` 다. 교체는 새 키로 한다 — DB 행이 가리키던 본문이 보존된다.
- **키 형식은 `validate_key` 가 정본**이다. 키는 DB 의 `storage_key varchar(512)` 칸에 그대로 들어간다. 도메인은 자기 키 함수를
  이 모듈에 `*_key`(객체 하나) · `*_prefix`(묶음) 로 더하고, 최상위 접두사 하나로 용도를 나눈다(버킷은 `STORAGE_BUCKET` 하나).
  키는 DB 에 그대로 저장되므로 키 규칙을 바꾸면 기존 객체 이관이 따라온다(설정이 아니라 코드인 이유).
- **접두사 단위 정리**는 `iter_keys`·`delete_prefix` 로 한다 — 한 묶음의 객체를 접두사로 모아 지운다.
- boto3 는 동기 라이브러리다. 요청 핸들러·워커(async)는 `await asyncio.to_thread(storage.put_object, ...)` 로 부른다.
- 앱 lifespan·워커 진입점이 `init_storage()` 로 클라이언트를 만들고, 그 뒤 `get_storage()` 로 얻는다(DB 엔진과 같은 모양).

실패는 `StorageError` 계열로만 올린다. 호출부는 boto3 예외를 알 필요가 없다.
"""

import re
from collections.abc import Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from ..config import settings

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client

# ---------- 오류 ----------


class StorageError(Exception):
    """스토리지 호출 실패의 기반. 호출부는 아래 세 하위 예외로 분기한다."""


class StorageUnavailableError(StorageError):
    """접속·인증·버킷 없음 등 호출 자체가 되지 않는다. 원인은 `__cause__` 에 있다."""


class ObjectAlreadyExistsError(StorageError):
    """같은 키의 객체가 이미 있어 저장하지 않았다(조건부 저장 거부)."""

    def __init__(self, key: str) -> None:
        super().__init__(f"객체가 이미 있다: {key}")
        self.key = key


class ObjectNotFoundError(StorageError):
    def __init__(self, key: str) -> None:
        super().__init__(f"객체가 없다: {key}")
        self.key = key


def storage_error_from(exc: ClientError | BotoCoreError, *, key: str | None) -> StorageError:
    """boto3 예외를 `StorageError` 계열로 옮긴다. `key` 는 객체 단위 호출에서만 넘긴다."""
    if isinstance(exc, ClientError):
        code = exc.response.get("Error", {}).get("Code", "")
        if key is not None and code == "PreconditionFailed":
            return ObjectAlreadyExistsError(key)
        if key is not None and code in ("NoSuchKey", "404"):
            return ObjectNotFoundError(key)
        return StorageUnavailableError(f"{code or type(exc).__name__}: {exc}")
    return StorageUnavailableError(f"{type(exc).__name__}: {exc}")


# ---------- 키 규칙 ----------

MAX_KEY_CHARS = 512  # db-schema 의 storage_key varchar(512)
_KEY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*(/[A-Za-z0-9][A-Za-z0-9._-]*)*$")


def validate_key(key: str) -> str:
    """객체 키 형식을 검사해 그대로 돌려준다. 도메인의 `*_key` 함수가 키를 만들 때와 저장·조회 경계에서 부른다."""
    if not key or len(key) > MAX_KEY_CHARS:
        raise ValueError(f"객체 키 길이는 1~{MAX_KEY_CHARS}자다: {len(key)}자")
    if ".." in key.split("/") or _KEY_PATTERN.fullmatch(key) is None:
        raise ValueError(f"객체 키 형식이 아니다(영숫자·._- 와 / 구분, 선행 / 와 .. 없음): {key!r}")
    return key


def validate_prefix(prefix: str) -> str:
    """접두사 형식을 검사해 그대로 돌려준다 — 끝이 `/` 이고 그 앞은 키 규칙을 따른다. 목록·일괄 삭제가 경계에서 부른다."""
    if not prefix.endswith("/"):
        raise ValueError(f"접두사는 / 로 끝난다: {prefix!r}")
    validate_key(prefix[:-1])
    return prefix


# ---------- 호출 ----------


@dataclass(frozen=True)
class StoredObject:
    key: str
    size_bytes: int
    etag: str


@dataclass(frozen=True)
class ObjectStream:
    """GET 결과. `chunks` 는 한 번만 소비할 수 있다(StreamingResponse 에 그대로 넘긴다)."""

    key: str
    size_bytes: int
    content_type: str
    chunks: Iterator[bytes]


DEFAULT_CHUNK_BYTES = 1024 * 1024
# S3 DeleteObjects 가 한 번에 받는 키 수의 상한
DELETE_BATCH_SIZE = 1000


class Storage:
    """버킷 하나에 대한 put·get·delete. 인스턴스는 `init_storage()` 가 만든다."""

    def __init__(self, client: "S3Client", bucket: str) -> None:
        self._client = client
        self.bucket = bucket

    def check_bucket(self) -> None:
        """버킷에 닿고 권한이 있는지(`HeadBucket`). 준비 상태 확인용 — 실패는 `StorageUnavailableError`."""
        try:
            self._client.head_bucket(Bucket=self.bucket)
        except (ClientError, BotoCoreError) as exc:
            raise storage_error_from(exc, key=None) from exc

    def put_object(self, key: str, body: bytes, *, content_type: str) -> StoredObject:
        """새 키로만 저장한다. 같은 키가 있으면 `ObjectAlreadyExistsError` 이고 기존 객체는 그대로다."""
        validate_key(key)
        try:
            response = self._client.put_object(
                Bucket=self.bucket, Key=key, Body=body, ContentType=content_type, IfNoneMatch="*"
            )
        except (ClientError, BotoCoreError) as exc:
            raise storage_error_from(exc, key=key) from exc
        return StoredObject(key=key, size_bytes=len(body), etag=response["ETag"])

    def open_object(self, key: str, *, chunk_bytes: int = DEFAULT_CHUNK_BYTES) -> ObjectStream:
        """객체를 스트림으로 연다. 본문은 `chunks` 를 소비할 때 받는다. 없으면 `ObjectNotFoundError`."""
        validate_key(key)
        try:
            response = self._client.get_object(Bucket=self.bucket, Key=key)
        except (ClientError, BotoCoreError) as exc:
            raise storage_error_from(exc, key=key) from exc
        return ObjectStream(
            key=key,
            size_bytes=response["ContentLength"],
            content_type=response["ContentType"],
            chunks=response["Body"].iter_chunks(chunk_bytes),
        )

    def read_object(self, key: str) -> bytes:
        """객체 전체를 메모리로 읽는다(작은 객체용)."""
        return b"".join(self.open_object(key).chunks)

    def delete_object(self, key: str) -> None:
        """객체를 지운다. S3 의미대로 없는 키도 성공이다(정리 작업을 다시 돌려도 된다)."""
        validate_key(key)
        try:
            self._client.delete_object(Bucket=self.bucket, Key=key)
        except (ClientError, BotoCoreError) as exc:
            raise storage_error_from(exc, key=key) from exc

    def iter_keys(self, prefix: str) -> Iterator[str]:
        """접두사 아래 객체 키를 키 순서로 낸다. 없으면 아무것도 내지 않는다. 쪽 넘김은 boto3 paginator 가 한다."""
        validate_prefix(prefix)
        try:
            for page in self._client.get_paginator("list_objects_v2").paginate(Bucket=self.bucket, Prefix=prefix):
                for item in page.get("Contents", []):
                    key = item.get("Key")
                    if key is None:
                        # S3 계약상 늘 있다 — 없으면 응답이 깨진 것이고 조용히 건너뛰면 정리가 빠진다
                        raise StorageUnavailableError(f"목록 항목에 Key 가 없다: {item!r}")
                    yield key
        except (ClientError, BotoCoreError) as exc:
            raise storage_error_from(exc, key=None) from exc

    def delete_prefix(self, prefix: str) -> int:
        """접두사 아래 객체를 모두 지우고 지운 수를 돌려준다. `DELETE_BATCH_SIZE` 개씩 나눠 보낸다. 없으면 0 이다 —
        정리 작업을 다시 돌려도 된다. 일부 키가 거부되면 `StorageUnavailableError`(남은 객체는 다음 정리가 다시 집는다)."""
        keys = list(self.iter_keys(prefix))
        for start in range(0, len(keys), DELETE_BATCH_SIZE):
            chunk = keys[start : start + DELETE_BATCH_SIZE]
            try:
                response = self._client.delete_objects(
                    Bucket=self.bucket, Delete={"Objects": [{"Key": key} for key in chunk], "Quiet": True}
                )
            except (ClientError, BotoCoreError) as exc:
                raise storage_error_from(exc, key=None) from exc
            errors = response.get("Errors", [])
            if errors:
                first = errors[0]
                raise StorageUnavailableError(
                    f"{first.get('Code', '')}: {first.get('Key', '')} (거부 {len(errors)}건 / {len(chunk)}건)"
                )
        return len(keys)

    def close(self) -> None:
        self._client.close()


def build_client() -> "S3Client":
    """설정으로 S3 클라이언트를 만든다. 자격 증명이 비어 있으면 boto3 기본 체인(배포: 실행 역할)이다."""
    secret = settings.s3_secret_access_key
    return boto3.client(
        "s3",
        region_name=settings.aws_region,
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=secret.get_secret_value() if secret is not None else None,
        config=Config(
            s3={"addressing_style": "path"},
            retries={"max_attempts": 3, "mode": "standard"},
            connect_timeout=5,
            read_timeout=60,
        ),
    )


_storage: Storage | None = None


def init_storage() -> Storage:
    global _storage
    if _storage is not None:
        raise RuntimeError("스토리지가 이미 초기화됐다")
    _storage = Storage(build_client(), settings.storage_bucket)
    return _storage


def close_storage() -> None:
    global _storage
    if _storage is not None:
        _storage.close()
    _storage = None


def get_storage() -> Storage:
    if _storage is None:
        raise RuntimeError("스토리지가 초기화되지 않았다 — 앱 lifespan 또는 init_storage() 를 먼저 거친다")
    return _storage
