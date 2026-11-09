"""SQLAlchemy 선언 Base 와 제약·인덱스 자동 명명 규약의 단일 출처.

마이그레이션 diff 가 이름으로 제약을 찾으므로, 이름 없는 제약이 DB 마다 다른 이름을 갖지 않게 한다.
복합 unique 는 이 규약(첫 컬럼만 반영)에 기대지 말고 `Index("uq_<table>_<전 컬럼>", ..., unique=True)` 로 쓴다.
"""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
