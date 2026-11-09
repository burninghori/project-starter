"""워커만 읽는 설정 — 앱 부팅 설정(`app.config.settings`)이 아니라 워커 진입점이 만든다(`AdminSeedSettings` 와 같은 꼴).

api·migrate 환경에는 이 값이 없어도 된다(backend-conventions 「설정」 표). 필수 값에 기본값을 두지 않는다(기조 5).

동시 처리 수와 고아 회수 기준은 소비자(작업 큐)마다 따로 둔다 — 메모리를 많이 쓰고 분 단위로 도는 작업과 초 단위로 끝나는 작업은
값이 다르다. 칸 이름은 `worker_<ConsumerSpec.name>_<속성>`(환경변수 `WORKER_<이름 대문자>_<속성 대문자>`),
속성은 `CONSUMER_PROPERTIES`. 소비자를 더하는 사람이 아래 「소비자별」 묶음에 속성마다 한 줄 더하고(등록 지점), 진입점이
`for_consumer()` 로 찾는다 — 칸이 없으면 부팅에서 실패한다. `tests/unit/worker/test_settings.py` 가 등록된 소비자 ↔ 칸 ↔
`.env.example`·`.env.test` 가 맞는지 지킨다.
"""

from dataclasses import dataclass
from datetime import timedelta
from typing import Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# 스토리지 클라이언트의 기본 연결 풀(botocore max_pool_connections)이 10 이다 — 한 프로세스의 소비자별 동시 처리 수 합이 그보다
# 크면 S3 호출이 줄을 선다. 올리려면 storage.build_client 의 연결 풀도 함께 올린다
MAX_CONCURRENCY = 10
# 소비자마다 두는 속성(칸 이름 접미사). 공용 값이 소비자마다 달라져야 하면 여기에 더하고 공용 칸을 지운다(겹쳐 두지 않는다)
CONSUMER_PROPERTIES = ("concurrency", "orphan_minutes")


def consumer_field_name(consumer_name: str, prop: str) -> str:
    """소비자 이름(`ConsumerSpec.name`)과 속성 → `WorkerSettings` 의 칸 이름."""
    return f"worker_{consumer_name}_{prop}"


@dataclass(frozen=True, slots=True)
class ConsumerSettings:
    """소비자 하나의 설정값 묶음."""

    # 워커 프로세스 하나가 이 소비자의 작업을 동시에 돌리는 수
    concurrency: int
    # 집힌 뒤 이 시간이 지나도 끝나지 않은 작업은 워커가 죽은 것으로 보고 다시 큐에 넣는다
    orphan_after: timedelta


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", frozen=True)

    # ---- 프로세스 공용 ----
    # 알림을 놓쳤을 때를 대비한 보조 폴링 간격(초) — 고아 회수로 큐에 돌아온 작업도 이 간격으로 집힌다
    worker_poll_seconds: int = Field(ge=1)
    # 집힌 횟수가 이 값에 닿으면 고아 회수가 다시 큐에 넣지 않고 실패로 둔다
    worker_max_attempts: int = Field(ge=1)

    # ---- 소비자별 (등록 지점 — 소비자마다 속성 수만큼 한 줄씩, 이름은 worker_<소비자>_<속성>, 다른 줄은 손대지 않는다) ----
    # 예: 보고서 생성(domains/reports/jobs.py) — 칸마다 그 값의 근거를 한 줄 적는다
    # worker_report_build_concurrency: int = Field(ge=1)
    # worker_report_build_orphan_minutes: int = Field(ge=1)

    @classmethod
    def consumer_fields(cls) -> list[str]:
        """소비자별 칸 이름 전부(선언 순)."""
        suffixes = tuple(f"_{prop}" for prop in CONSUMER_PROPERTIES)
        return [name for name in cls.model_fields if name.endswith(suffixes)]

    def for_consumer(self, consumer_name: str) -> ConsumerSettings:
        """소비자의 설정값 묶음. 칸이 빠져 있으면 어느 칸인지 적고 실패한다."""
        names = {prop: consumer_field_name(consumer_name, prop) for prop in CONSUMER_PROPERTIES}
        missing = [name for name in names.values() if name not in type(self).model_fields]
        if missing:
            raise ValueError(f"소비자 {consumer_name} 의 설정 칸이 WorkerSettings 에 없다: {', '.join(missing)}")
        return ConsumerSettings(
            concurrency=int(getattr(self, names["concurrency"])),
            orphan_after=timedelta(minutes=int(getattr(self, names["orphan_minutes"]))),
        )

    @model_validator(mode="after")
    def _total_concurrency_within_storage_pool(self) -> Self:
        fields = [name for name in self.consumer_fields() if name.endswith("_concurrency")]
        total = sum(int(getattr(self, name)) for name in fields)
        if total > MAX_CONCURRENCY:
            listed = ", ".join(f"{name}={getattr(self, name)}" for name in fields)
            raise ValueError(f"소비자별 동시 처리 수의 합({total})이 상한 {MAX_CONCURRENCY} 을 넘는다: {listed}")
        return self
