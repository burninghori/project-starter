"""모든 테이블 · 컬럼에 설명(`comment`)이 있는가 — DB 를 직접 보는 사람을 위한 한 줄(backend-conventions 「모델」).

모델의 `comment` 가 autogenerate 로 DB 설명(`COMMENT ON`)이 된다. 새 테이블 · 컬럼에서 빠뜨리면 여기서 잡는다.
"""

from app.db import model_registry  # noqa: F401
from app.db.base import Base


def test_every_table_and_column_has_a_comment() -> None:
    missing = [
        f"{table.name}" if column is None else f"{table.name}.{column.name}"
        # sorted_tables 는 순환 FK 가 있으면 경고를 내므로 이름 순으로 돈다
        for table in sorted(Base.metadata.tables.values(), key=lambda t: t.name)
        for column in (None, *table.columns)
        if not (table.comment if column is None else column.comment)
    ]
    assert missing == [], f"설명(comment)이 없는 테이블 · 컬럼: {missing}"
