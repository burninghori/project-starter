"""unit / integration 자동 분류.

외부 컨테이너가 필요한 픽스처(DB: `db_engine`·`db_session`·`db_client`·`migrated_database`, 스토리지: `storage`)를
쓰는 테스트는 integration, 나머지는 unit 이다. 컨테이너를 간접으로만 쓰는 테스트(픽스처 없이 닿는 경우)는
`@pytest.mark.integration` 을 직접 붙인다.

    uv run pytest -m unit          # 컨테이너 없이
    uv run pytest -m integration   # 로컬 Postgres·S3 호환 컨테이너(make local-up) 필요
"""

import pytest

INTEGRATION_FIXTURES = frozenset({"db_engine", "db_session", "db_client", "migrated_database", "storage"})


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if item.get_closest_marker("integration") is not None:
            continue
        if INTEGRATION_FIXTURES.intersection(getattr(item, "fixturenames", ())):
            item.add_marker(pytest.mark.integration)
        else:
            item.add_marker(pytest.mark.unit)
