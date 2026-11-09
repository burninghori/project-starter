"""마이그레이션은 앞으로만 간다.

운영 복귀는 스키마를 역변환하지 않고 배포 직전 DB 스냅숏을 복원한다. 각 revision 의 `downgrade()` 는
이 함수를 불러 지원하지 않는 연산임을 오류로 드러낸다.
"""

from typing import NoReturn


def downgrade_not_supported() -> NoReturn:
    raise RuntimeError("마이그레이션은 forward-only 다. downgrade 대신 배포 직전 DB 스냅숏을 복원한다.")
