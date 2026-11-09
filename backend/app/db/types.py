"""공용 컬럼 타입 — 모든 모델이 같은 저장 표현을 쓰게 한다.

- `Json` = JSONB. Python `None` 을 SQL NULL 로 저장한다(`'null'` JSON 스칼라와 갈리지 않게).
- `UtcDateTime` = timestamptz.
"""

from sqlalchemy import TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB

type JsonValue = str | int | float | bool | list[JsonValue] | dict[str, JsonValue] | None
type JsonObject = dict[str, JsonValue]

Json = JSONB(none_as_null=True)
UtcDateTime = TIMESTAMP(timezone=True)
