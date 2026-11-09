"""공용 모델 mixin — PK 와 시간 컬럼 쌍의 단일 출처."""

from datetime import datetime

from sqlalchemy import BigInteger, Identity, func
from sqlalchemy.orm import Mapped, mapped_column

from .types import UtcDateTime


class IdPkMixin:
    """`id BIGINT GENERATED ALWAYS AS IDENTITY` PK.

    화면·외부에 보이는 업무 식별자(주문 번호 `ORD-0001` 같은 것)는 PK 로 쓰지 않고
    별도 컬럼 + unique 로 둔다. 업무 ID 는 바뀔 수 있고 PK 는 바뀌지 않는다.
    """

    id: Mapped[int] = mapped_column(
        BigInteger, Identity(always=True), primary_key=True, sort_order=-1, comment="행 번호(PK, 자동 증가)"
    )


class TimestampMixin:
    """`created_at` + `updated_at`. 모든 entity 테이블에 붙인다.

    `updated_at` 의 `onupdate` 는 ORM 과 Core `update()` 에 적용되고 raw SQL 은 우회한다.
    """

    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime, nullable=False, server_default=func.now(), sort_order=9998, comment="행을 만든 시각"
    )
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        sort_order=9999,
        comment="행을 마지막으로 고친 시각",
    )
