"""모든 도메인 모델을 `Base.metadata` 에 등록하는 단일 지점.

alembic autogenerate 와 테스트 DB 가 이 모듈 하나를 import 해 전체 테이블을 본다.
도메인을 추가하면 그 도메인의 `models` 모듈 import 를 여기에 한 줄 더한다(정렬·재배치 없이 한 줄 추가만).
폴더 목록은 docs/specs/api.md 「코드 도메인(폴더)」.
"""

from app.domains.auth import models as _auth  # noqa: F401
