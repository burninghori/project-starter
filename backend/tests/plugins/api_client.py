"""API 테스트 클라이언트.

- `client`: DB 없이 도는 API 테스트용. 앱 lifespan 은 엔진만 만들고 접속하지 않으므로 DB 를
  건드리지 않는 endpoint 는 Postgres 없이 시험할 수 있다.
- `db_client`: 마이그레이션된 테스트 DB 위의 API 테스트용(integration). 요청마다 실제 commit 된다 —
  테스트가 만든 데이터는 다음 테스트 세션의 DB 재생성 때 사라진다. 테스트끼리 데이터가 섞이지
  않게 이름·ID 를 테스트마다 다르게 만든다.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app(), raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture
def db_client(migrated_database: str) -> Iterator[TestClient]:
    with TestClient(create_app(), raise_server_exceptions=False) as test_client:
        yield test_client
