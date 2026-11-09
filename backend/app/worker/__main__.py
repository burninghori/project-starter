"""`python -m app.worker` — 비동기 작업 프로세스 진입점(결정 0005).

한 프로세스에서 LISTEN 접속 하나 + 소비자(작업 큐)마다 소비 루프 + 주기 작업(고아 회수·만료 정리)을 돌린다.
소비자·주기 작업은 아래 `CONSUMERS`·`PERIODIC` 에 **한 줄씩** 더한다(등록 지점) — 작업 함수는 도메인 폴더에 둔다.
소비자는 `settings.py` 의 소비자별 칸(`worker_<소비자>_concurrency` · `_orphan_minutes`)과 함께 더한다 — 부팅 때 이름 규칙으로
찾고 없으면 시작하지 않는다.
어느 태스크가 예외로 죽으면 반쯤 돌지 않고 프로세스를 멈춘다(종료 코드 1 — 실행 환경이 다시 띄운다).
"""

import asyncio
import signal
from collections.abc import Awaitable, Callable
from functools import partial

from app.config import settings
from app.core.storage import close_storage, init_storage
from app.db.engine import dispose_engine, init_engine, session_scope
from app.logging import get_logger, setup_logging
from app.worker.listener import Listener, listen_dsn
from app.worker.queue import ConsumerSpec, run_consumer, run_reclaimer
from app.worker.scheduler import every
from app.worker.settings import WorkerSettings

logger = get_logger("worker")

# 소비자 목록 — 도메인의 `jobs.py` 가 만든 `ConsumerSpec` 을 한 줄씩 더하고, 설정 칸은 settings.py 의 소비자별 묶음에 함께 더한다.
# 예: from app.domains.reports.jobs import report_build  →  CONSUMERS = [report_build]
CONSUMERS: list[ConsumerSpec] = []
# 주기 작업 (이름, 간격 초, 함수). 함수는 워커 설정을 받는다(만료 정리가 소비자의 고아 기준을 쓰는 경우 등).
# 예: ("purge_expired_uploads", 3600.0, purge_expired_uploads)
PERIODIC: list[tuple[str, float, Callable[[WorkerSettings], Awaitable[None]]]] = []
# 고아 회수를 돌리는 간격(초). 회수 기준(N분)은 소비자별 설정값이고 이 간격은 그 기준을 얼마나 촘촘히 보느냐일 뿐이라 코드에 둔다
RECLAIM_INTERVAL_SECONDS = 60.0


async def run() -> None:
    setup_logging(settings.log_level)
    worker_settings = WorkerSettings()  # pyright: ignore[reportCallIssue]  # 값은 환경변수에서 채운다
    init_engine()
    init_storage()
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)

    # 소비자별 설정값 — 칸이 없으면 태스크를 띄우기 전에 여기서 실패한다
    per_consumer = {spec.name: worker_settings.for_consumer(spec.name) for spec in CONSUMERS}
    wakeups = {spec.channel: asyncio.Event() for spec in CONSUMERS}
    listener = Listener(listen_dsn(), wakeups)
    tasks = [asyncio.create_task(listener.run(stop), name="listener")]
    for spec in CONSUMERS:
        tasks.append(
            asyncio.create_task(
                run_consumer(
                    spec,
                    wake=wakeups[spec.channel],
                    stop=stop,
                    concurrency=per_consumer[spec.name].concurrency,
                    poll_seconds=worker_settings.worker_poll_seconds,
                    open_session=session_scope,
                ),
                name=f"consumer:{spec.name}",
            )
        )
    if CONSUMERS:
        tasks.append(
            asyncio.create_task(
                run_reclaimer(
                    [(spec, per_consumer[spec.name].orphan_after) for spec in CONSUMERS],
                    stop=stop,
                    interval_seconds=RECLAIM_INTERVAL_SECONDS,
                    max_attempts=worker_settings.worker_max_attempts,
                    open_session=session_scope,
                ),
                name="reclaimer",
            )
        )
    for name, interval_seconds, fn in PERIODIC:
        job = partial(fn, worker_settings)
        tasks.append(asyncio.create_task(every(name, interval_seconds, job, stop), name=f"periodic:{name}"))

    logger.info(
        "worker started",
        extra={
            "app_env": settings.app_env,
            "consumers": {
                name: {"concurrency": c.concurrency, "orphan_minutes": int(c.orphan_after.total_seconds() // 60)}
                for name, c in per_consumer.items()
            },
            "periodic": [name for name, _, _ in PERIODIC],
            "poll_seconds": worker_settings.worker_poll_seconds,
            "max_attempts": worker_settings.worker_max_attempts,
        },
    )
    try:
        await _run_until_stop(tasks, stop)
    finally:
        await dispose_engine()
        close_storage()
        logger.info("worker stopped")


async def _run_until_stop(tasks: list[asyncio.Task[None]], stop: asyncio.Event) -> None:
    """`stop` 이 켜질 때까지 돈다. 어느 태스크가 먼저 끝나면(예외, 또는 멈추라는 신호 없이 돌아옴) 모두 멈추고 그 사실을 올린다.

    `stop` 이 켜진 같은 틱에 예외 없이 끝난 태스크(재접속 대기 중 SIGTERM 을 받은 리스너)는 `done` 에 함께 들어오지만 죽은 게 아니다.
    """
    stopper = asyncio.create_task(stop.wait(), name="stop")
    done, _pending = await asyncio.wait([*tasks, stopper], return_when=asyncio.FIRST_COMPLETED)
    died = [task for task in done if task is not stopper and (task.exception() is not None or not stop.is_set())]
    for task in died:
        logger.error("worker task died", extra={"task": task.get_name()}, exc_info=task.exception())
    stop.set()
    await asyncio.gather(*tasks, return_exceptions=True)
    stopper.cancel()
    await asyncio.gather(stopper, return_exceptions=True)
    if died:
        raise RuntimeError(f"워커 태스크가 죽었다: {[task.get_name() for task in died]}")


if __name__ == "__main__":
    asyncio.run(run())
