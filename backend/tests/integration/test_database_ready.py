"""테스트 DB 가 마이그레이션까지 적용된 상태로 뜨는지 — integration 픽스처의 동작 예시.

`/ready` 는 DB 와 스토리지 버킷을 둘 다 보므로 이 테스트는 S3 호환 컨테이너도 필요하다(make local-up).
"""

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def test_ready_checks_database_and_storage(db_client: TestClient) -> None:
    response = db_client.get("/api/health/ready")

    assert response.status_code == 200


async def test_migrations_created_app_role(db_session: AsyncSession) -> None:
    exists = (await db_session.execute(text("SELECT 1 FROM pg_roles WHERE rolname = 'app_app'"))).scalar()

    assert exists == 1
