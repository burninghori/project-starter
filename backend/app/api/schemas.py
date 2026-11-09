"""API 입출력 모델의 공용 기반.

- `ApiBase`: 응답·내부 조립용. Python 에서는 snake_case 로 만들고 wire 는 camelCase 로 나간다.
  ORM 객체에서 바로 읽을 수 있다(`model_validate(row)`).
- `ApiRequestBase`: 요청 body·query 전용. camelCase 키만 받고 계약 밖 키는 422 로 거부한다 —
  선택 필드의 오타가 기본값으로 조용히 바뀌지 않게 한다.
- `PageEnvelope`: offset 페이지 목록의 공용 응답.
- `BIGINT_MAX`·`IdPath`: 요청 정수의 범위(쓰는 법은 backend-conventions 「요청 입력」). DB 범위(bigint)를 넘는 값은
  DB 드라이버가 보내지 못해 처리되지 않은 예외(500)가 되므로 경계에서 422 `request_validation_failed` 로 막는다(기조 5).
"""

from typing import Annotated

from fastapi import Path
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

# PostgreSQL bigint 최댓값 — 모든 PK(`IdPkMixin`)와 OFFSET 의 범위
BIGINT_MAX = 2**63 - 1

# 경로의 행 id — PK 는 1 부터라 범위 밖(0·음수·bigint 초과)은 422, 범위 안의 없는 행은 각 엔드포인트의 404
IdPath = Annotated[int, Path(ge=1, le=BIGINT_MAX)]


class ApiBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, alias_generator=to_camel)


class ApiRequestBase(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_name=False,
        validate_by_alias=True,
        extra="forbid",
    )


class PageEnvelope[RowT](ApiBase):
    """`rows` 는 요청한 페이지의 행, `total` 은 필터 적용 후·페이지 자르기 전 전체 건수,
    `page_count` 는 마지막 페이지 번호(0건이면 0). `total` 을 반환 행 수에서 역산하지 않는다(기조 1)."""

    rows: list[RowT]
    total: int
    page_count: int


def page_count_for(total: int, page_size: int) -> int:
    """`PageEnvelope.page_count` 산식의 단일 출처."""
    if page_size < 1:
        raise ValueError("page_size 는 1 이상")
    if total == 0:
        return 0
    return -(-total // page_size)
