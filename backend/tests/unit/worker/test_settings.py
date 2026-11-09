"""워커 설정 — 소비자별 칸의 규칙을 지킨다: 동시 처리 수 합은 스토리지 연결 풀 이하, 등록된 소비자 ↔ 칸 ↔ `.env` 예시가 맞는다.

규칙 자체는 실제 소비자 칸 위에 소비자 둘을 더한 서브클래스로 검사한다 — 등록된 소비자 수와 무관하게 여럿일 때를 본다.
"""

import re
from datetime import timedelta
from pathlib import Path

import pytest
from pydantic import Field, ValidationError

from app.worker.__main__ import CONSUMERS
from app.worker.settings import CONSUMER_PROPERTIES, MAX_CONCURRENCY, WorkerSettings, consumer_field_name

BACKEND_DIR = Path(__file__).resolve().parents[3]
_COMMON = {"worker_poll_seconds": 60, "worker_max_attempts": 3}


class _TwoConsumers(WorkerSettings):
    """규칙 검사용 — 실제 소비자 칸 위에 소비자 둘(alpha·beta)을 더 가진 설정."""

    worker_alpha_concurrency: int = Field(ge=1)
    worker_alpha_orphan_minutes: int = Field(ge=1)
    worker_beta_concurrency: int = Field(ge=1)
    worker_beta_orphan_minutes: int = Field(ge=1)


# 실제 소비자 칸(등록된 소비자마다 속성 수만큼)에 넣는 값 — 동시 처리 수는 1 로 두어 합계 검사의 몫을 alpha·beta 가 갖는다
_REAL_CONSUMER_VALUES = {
    name: 1 for name in WorkerSettings.consumer_fields() if name.endswith(tuple(f"_{p}" for p in CONSUMER_PROPERTIES))
}
_REAL_CONCURRENCY_TOTAL = sum(value for name, value in _REAL_CONSUMER_VALUES.items() if name.endswith("_concurrency"))


def _two(alpha: int, beta: int) -> _TwoConsumers:
    # _env_file=None: 개발자의 backend/.env 를 읽지 않는다. 인자가 환경변수(.env.test)보다 우선한다
    return _TwoConsumers(
        _env_file=None,  # pyright: ignore[reportCallIssue]
        **_COMMON,
        **_REAL_CONSUMER_VALUES,
        worker_alpha_concurrency=alpha,
        worker_alpha_orphan_minutes=10,
        worker_beta_concurrency=beta,
        worker_beta_orphan_minutes=2,
    )


def test_consumer_fields_follow_the_naming_rule() -> None:
    assert consumer_field_name("alpha", "orphan_minutes") == "worker_alpha_orphan_minutes"
    assert _TwoConsumers.consumer_fields() == [
        *WorkerSettings.consumer_fields(),
        "worker_alpha_concurrency",
        "worker_alpha_orphan_minutes",
        "worker_beta_concurrency",
        "worker_beta_orphan_minutes",
    ]


def test_for_consumer_bundles_that_consumers_fields() -> None:
    settings = _two(3, 1)
    assert settings.for_consumer("alpha").concurrency == 3
    assert settings.for_consumer("alpha").orphan_after == timedelta(minutes=10)
    assert settings.for_consumer("beta").orphan_after == timedelta(minutes=2)


def test_for_consumer_names_the_missing_fields() -> None:
    with pytest.raises(ValueError, match="worker_nobody_concurrency, worker_nobody_orphan_minutes"):
        _two(1, 1).for_consumer("nobody")


def test_total_concurrency_may_fill_the_storage_pool() -> None:
    room = MAX_CONCURRENCY - _REAL_CONCURRENCY_TOTAL
    settings = _two(room - 1, 1)
    assert (
        settings.worker_alpha_concurrency + settings.worker_beta_concurrency + _REAL_CONCURRENCY_TOTAL
        == MAX_CONCURRENCY
    )


def test_total_concurrency_over_the_storage_pool_is_rejected() -> None:
    room = MAX_CONCURRENCY - _REAL_CONCURRENCY_TOTAL
    with pytest.raises(ValidationError, match="넘는다"):
        _two(room, 1)


def test_values_below_one_are_rejected() -> None:
    with pytest.raises(ValidationError):
        _two(0, 1)


def test_registered_consumers_and_fields_match() -> None:
    """소비자마다 속성 수만큼 칸이 있고, 칸마다 소비자가 있다(읽는 코드 없는 설정값을 두지 않는다)."""
    expected = {consumer_field_name(spec.name, prop) for spec in CONSUMERS for prop in CONSUMER_PROPERTIES}
    assert set(WorkerSettings.consumer_fields()) == expected


@pytest.mark.parametrize("env_file", [".env.example", ".env.test"])
def test_env_examples_list_exactly_the_worker_fields(env_file: str) -> None:
    text = (BACKEND_DIR / env_file).read_text(encoding="utf-8")
    keys = set(re.findall(r"^(WORKER_[A-Z0-9_]+)=", text, flags=re.MULTILINE))
    assert keys == {name.upper() for name in WorkerSettings.model_fields}
