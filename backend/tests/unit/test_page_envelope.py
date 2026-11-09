import pytest

from app.api.schemas import ApiBase, PageEnvelope, page_count_for


class Row(ApiBase):
    item_code: str


@pytest.mark.parametrize(("total", "size", "expected"), [(0, 20, 0), (1, 20, 1), (20, 20, 1), (21, 20, 2)])
def test_page_count(total: int, size: int, expected: int) -> None:
    assert page_count_for(total, size) == expected


def test_envelope_serializes_camel_case() -> None:
    envelope = PageEnvelope[Row](rows=[Row(item_code="ORD-0001")], total=1, page_count=1)

    assert envelope.model_dump(by_alias=True) == {"rows": [{"itemCode": "ORD-0001"}], "total": 1, "pageCount": 1}
