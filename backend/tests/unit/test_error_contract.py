"""오류 응답 계약(semantic-v1) — 어떤 경로로 실패해도 같은 envelope 이 나간다."""

from collections.abc import Callable, Iterator

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient

from app.api.error_contract import ERROR_CODE_STATUS, SemanticHTTPException, error_family
from app.api.schemas import ApiRequestBase
from app.domains.auth.deps import AuthUser
from app.main import create_app

router = APIRouter(prefix="/api/v1/_test")


class SampleIn(ApiRequestBase):
    item_code: str
    weight: int


@router.get("/missing")
async def missing() -> None:
    raise SemanticHTTPException(
        code="resource_not_found",
        details={"itemCode": "ITEM-999"},
        diagnostic_message="no row",
    )


@router.post("/echo")
async def echo(body: SampleIn) -> dict[str, str]:
    return {"itemCode": body.item_code}


@router.get("/boom")
async def boom() -> None:
    raise RuntimeError("unexpected")


@pytest.fixture
def test_client(stub_auth: Callable[..., AuthUser]) -> Iterator[TestClient]:
    app = create_app()
    app.include_router(router)
    with TestClient(app, raise_server_exceptions=False) as client:
        # 모든 API 가 인증 뒤에 있다. 오류 계약 자체를 보는 테스트라 DB 없이 세션을 고정한다
        stub_auth(client)
        yield client


def test_semantic_exception_renders_envelope(test_client: TestClient) -> None:
    response = test_client.get("/api/v1/_test/missing")

    assert response.status_code == 404
    error = response.json()["error"]
    assert error["contract"] == "semantic-v1"
    assert error["family"] == "not_found"
    assert error["code"] == "resource_not_found"
    assert error["details"] == {"itemCode": "ITEM-999"}
    assert error["diagnostic"]["requestId"] == response.headers["x-request-id"]


def test_unknown_route_is_not_found_envelope(test_client: TestClient) -> None:
    response = test_client.get("/api/v1/_test/nothing-here")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "resource_not_found"


def test_request_body_accepts_camel_case_only(test_client: TestClient) -> None:
    ok = test_client.post("/api/v1/_test/echo", json={"itemCode": "ITEM-001", "weight": 1})
    snake = test_client.post("/api/v1/_test/echo", json={"item_code": "ITEM-001", "weight": 1})

    assert ok.status_code == 200
    assert snake.status_code == 422
    assert snake.json()["error"]["code"] == "request_validation_failed"


def test_unhandled_exception_hides_cause(test_client: TestClient) -> None:
    response = test_client.get("/api/v1/_test/boom")

    assert response.status_code == 500
    error = response.json()["error"]
    assert error["code"] == "internal_failure"
    assert "unexpected" not in response.text
    assert error["diagnostic"]["requestId"] == response.headers["x-request-id"]


def test_code_decides_status_and_family() -> None:
    exc = SemanticHTTPException(code="database_unavailable")

    assert (exc.status_code, exc.family) == (503, "unavailable")


def test_every_code_has_a_family() -> None:
    for code in ERROR_CODE_STATUS:
        assert error_family(code)
