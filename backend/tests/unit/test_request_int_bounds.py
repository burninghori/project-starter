"""요청 정수의 범위 — DB 범위(bigint)를 벗어난 id·쪽 번호는 DB 에 닿기 전에 422 `request_validation_failed`.

넘는 값이 DB 까지 가면 드라이버가 값을 보내지 못해 처리되지 않은 예외(500)가 된다. PK 는 1 부터라 0·음수도 범위 밖이다.
검증이 DB 앞에서 끝나므로 DB 없이 본다. 도메인 라우터는 아래 테스트 라우터와 같은 선언(backend-conventions 「요청 입력」)을
쓰고, 범위 끝의 값이 DB 까지 가서 404·빈 목록이 되는 쪽은 각 도메인의 integration 이 본다.
"""

from collections.abc import Callable, Iterator
from typing import Annotated, Any

import pytest
from fastapi import APIRouter, Query
from fastapi.testclient import TestClient
from pydantic import Field

from app.api.schemas import BIGINT_MAX, ApiRequestBase, IdPath
from app.domains.auth.deps import AuthUser
from app.main import create_app

PREFIX = "/api/v1/_bounds_test"
MAX_PAGE_SIZE = 100
# OFFSET = (page - 1) × page_size 가 bigint 를 넘지 않는 가장 큰 쪽 번호
MAX_PAGE = BIGINT_MAX // MAX_PAGE_SIZE
OUT_OF_RANGE_IDS = (0, -1, BIGINT_MAX + 1)

router = APIRouter(prefix=PREFIX)


class ItemIn(ApiRequestBase):
    owner_id: int = Field(ge=1, le=BIGINT_MAX)


@router.get("/items/{item_id}")
async def item(item_id: IdPath) -> dict[str, int]:
    return {"id": item_id}


@router.get("/items")
async def items(
    page: Annotated[int, Query(ge=1, le=MAX_PAGE)],
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=MAX_PAGE_SIZE)],
    owner_id: Annotated[int | None, Query(alias="ownerId", ge=1, le=BIGINT_MAX)] = None,
) -> dict[str, int | None]:
    return {"page": page, "pageSize": page_size, "ownerId": owner_id}


@router.post("/items")
async def create_item(body: ItemIn) -> dict[str, int]:
    return {"ownerId": body.owner_id}


Call = Callable[[TestClient, int], Any]

# (이름, 값 하나로 요청을 보내는 호출, 거부된 칸의 loc) — 경로 id 는 파라미터 이름, 쿼리·본문은 wire 이름
ID_INPUTS: list[tuple[str, Call, list[str]]] = [
    ("경로 id", lambda c, v: c.get(f"{PREFIX}/items/{v}"), ["path", "item_id"]),
    (
        "쿼리 id",
        lambda c, v: c.get(f"{PREFIX}/items", params={"page": 1, "pageSize": 10, "ownerId": v}),
        ["query", "ownerId"],
    ),
    ("본문 id", lambda c, v: c.post(f"{PREFIX}/items", json={"ownerId": v}), ["body", "ownerId"]),
]


@pytest.fixture
def test_client() -> Iterator[TestClient]:
    app = create_app()
    app.include_router(router)
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


def _assert_rejected_before_the_db(response: Any, loc: list[str]) -> None:
    assert response.status_code == 422, response.text
    error = response.json()["error"]
    assert error["code"] == "request_validation_failed"
    assert [issue["loc"] for issue in error["details"]["issues"]] == [loc]


@pytest.mark.parametrize("value", OUT_OF_RANGE_IDS)
@pytest.mark.parametrize(("call", "loc"), [pytest.param(call, loc, id=name) for name, call, loc in ID_INPUTS])
def test_ids_outside_the_db_range_are_rejected_before_the_db(
    test_client: TestClient, stub_auth: Callable[..., AuthUser], call: Call, loc: list[str], value: int
) -> None:
    stub_auth(test_client)

    _assert_rejected_before_the_db(call(test_client, value), loc)


def test_ids_at_the_edges_of_the_range_pass(test_client: TestClient, stub_auth: Callable[..., AuthUser]) -> None:
    stub_auth(test_client)

    assert test_client.get(f"{PREFIX}/items/1").status_code == 200
    assert test_client.get(f"{PREFIX}/items/{BIGINT_MAX}").status_code == 200


def test_page_whose_offset_leaves_the_db_range_is_rejected_before_the_db(
    test_client: TestClient, stub_auth: Callable[..., AuthUser]
) -> None:
    stub_auth(test_client)

    def call(page: int) -> Any:
        return test_client.get(f"{PREFIX}/items", params={"page": page, "pageSize": MAX_PAGE_SIZE})

    assert call(MAX_PAGE).status_code == 200
    _assert_rejected_before_the_db(call(MAX_PAGE + 1), ["query", "page"])
