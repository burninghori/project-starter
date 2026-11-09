"""로깅 단일 모듈 — TRACE 레벨, request_id 주입, 민감값 마스킹, TTY 에 따른 출력 형식.

출력 형식은 stderr 가 터미널인지로 한 번 정한다.

- 터미널(로컬 개발): 사람이 읽는 한 줄 텍스트. `extra=` 필드는 줄 끝에 `key=value` 로 붙는다.
- 그 밖(컨테이너 stdout → 로그 수집기): JSON line. 필드로 검색·집계할 수 있다.

JSON 공통 필드: `ts` · `level` · `logger` · `request_id` · `msg` (+ 예외 시 `exc_info`).
엔티티 식별자는 메시지 보간이 아니라 `extra={"run_id": ...}` 처럼 필드로 싣는다.

`LOG_LEVEL` 은 앱 로거(`app.*`)의 상세도다. 서드파티 로거는 INFO 미만을 내보내지 않는다 —
`LOG_LEVEL=DEBUG` 로 SQLAlchemy·asyncio 디버그가 쏟아지지 않게 한다.

앱 코드는 `get_logger` 로만 로거를 얻는다(ruff TID251 이 `logging.getLogger` 직접 호출을 막는다).
"""

import logging
import sys
import time
from typing import Any, ClassVar, cast

from pythonjsonlogger.json import JsonFormatter

from .context import get_request_id

APP_LOGGER_ROOT = "app"

# DEBUG(10) 아래의 상세 진단 레벨. uvicorn 과 같은 값 5를 쓴다.
TRACE = 5
logging.addLevelName(TRACE, "TRACE")


def _trace(self: logging.Logger, msg: object, *args: object, **kwargs: Any) -> None:
    if self.isEnabledFor(TRACE):
        self._log(TRACE, msg, args, **kwargs)


logging.Logger.trace = _trace  # type: ignore[attr-defined]


class TraceLogger(logging.Logger):
    """`.trace()` 를 타입 체커에 알리기 위한 선언. 직접 만들지 않는다 — `get_logger` 를 쓴다."""

    def trace(self, msg: object, *args: object, **kwargs: Any) -> None:
        raise TypeError("TraceLogger 는 직접 만들지 않는다 — get_logger() 를 쓴다")


# 키 이름에 이 조각이 들어가면 extra 값을 가린다(대소문자 무시).
SENSITIVE_KEY_FRAGMENTS = ("password", "secret", "token", "authorization", "apikey", "credential")
MAX_LOG_VALUE_CHARS = 2000
REDACTED = "***"

# LogRecord 가 원래 가진 속성. 이 밖의 속성이 `extra=` 로 들어온 필드다.
_RESERVED_ATTRS = frozenset(logging.LogRecord("", 0, "", 0, "", None, None).__dict__) | {"message", "asctime"}


def _is_sensitive(key: str) -> bool:
    lowered = key.lower()
    return any(fragment in lowered for fragment in SENSITIVE_KEY_FRAGMENTS)


def _bounded(value: object) -> object:
    if isinstance(value, str) and len(value) > MAX_LOG_VALUE_CHARS:
        return value[:MAX_LOG_VALUE_CHARS] + f"…(+{len(value) - MAX_LOG_VALUE_CHARS})"
    return value


class RequestContextFilter(logging.Filter):
    """모든 레코드에 request_id 를 붙이고 extra 필드를 마스킹·길이 제한한다."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        # uvicorn 이 붙이는 ANSI 색 버전 메시지. msg 와 같은 내용이라 버린다.
        record.__dict__.pop("color_message", None)
        for key in list(record.__dict__):
            if key in _RESERVED_ATTRS or key == "request_id":
                continue
            record.__dict__[key] = REDACTED if _is_sensitive(key) else _bounded(record.__dict__[key])
        return True


def _utc_iso(created: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(created))


class _TextFormatter(logging.Formatter):
    _COLORS: ClassVar[dict[str, str]] = {
        "TRACE": "\033[90m",
        "DEBUG": "\033[36m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
    }
    _RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        level = record.levelname
        color = self._COLORS.get(level, "")
        extras = " ".join(
            f"{key}={value}"
            for key, value in record.__dict__.items()
            if key not in _RESERVED_ATTRS and key != "request_id"
        )
        line = (
            f"{_utc_iso(record.created)} {color}{level:<7}{self._RESET if color else ''} "
            f"[{record.name}] ({record.__dict__.get('request_id', '-')}) {record.getMessage()}"
        )
        if extras:
            line += f"  {extras}"
        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)
        return line


class _JsonFormatter(JsonFormatter):
    def add_fields(self, log_data: dict[str, Any], record: logging.LogRecord, message_dict: dict[str, Any]) -> None:
        super().add_fields(log_data, record, message_dict)
        log_data["ts"] = _utc_iso(record.created)
        log_data["level"] = record.levelname
        log_data["logger"] = record.name
        log_data["msg"] = log_data.pop("message", record.getMessage())


def setup_logging(level: str) -> None:
    """프로세스당 한 번 호출한다(앱 lifespan·워커 진입점). 같은 프로세스에서 다시 불러도 핸들러는 하나다."""
    handler = logging.StreamHandler(sys.stderr)
    handler.addFilter(RequestContextFilter())
    if sys.stderr.isatty():
        handler.setFormatter(_TextFormatter())
    else:
        handler.setFormatter(_JsonFormatter())

    root = logging.getLogger()
    root.handlers = [handler]
    # 서드파티는 INFO 까지만. 앱 로거만 LOG_LEVEL 을 따른다.
    root.setLevel(logging.INFO)
    logging.getLogger(APP_LOGGER_ROOT).setLevel(level)
    # uvicorn 의 자체 접근 로그는 끈다 — request_context 미들웨어가 request_id 와 함께 남긴다.
    logging.getLogger("uvicorn.access").disabled = True


def get_logger(name: str) -> TraceLogger:
    """앱 로거. `name` 은 모듈 축약(`api.errors`, `domains.auth` 등)이고 `app.` 아래에 놓인다."""
    return cast(TraceLogger, logging.getLogger(f"{APP_LOGGER_ROOT}.{name}"))
