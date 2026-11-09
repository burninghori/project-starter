"""스토리지 integration 픽스처.

- `storage` (function): 테스트 설정(.env.test)의 버킷에 붙는 `Storage`. 컨테이너가 없으면 skip 이 아니라
  **실패**한다 — 로컬·CI 모두 실제 컨테이너를 상대로 돈다(make local-up).
- 테스트가 만든 객체는 테스트가 지운다. 키는 `unique_key()` 로 테스트마다 다르게 만든다.
"""

import uuid
from collections.abc import Iterator

import pytest

from app.config import settings
from app.core.storage import Storage, build_client


@pytest.fixture
def storage() -> Iterator[Storage]:
    instance = Storage(build_client(), settings.storage_bucket)
    try:
        yield instance
    finally:
        instance.close()


def unique_key(suffix: str = ".json") -> str:
    """테스트끼리 섞이지 않는 객체 키. `tests/` 접두사라 도메인 키와 겹치지 않는다."""
    return f"tests/{uuid.uuid4().hex}{suffix}"
