import logging
import os
import sys
import warnings
from collections.abc import Mapping, Sequence
from typing import Any

import structlog
from structlog.stdlib import ProcessorFormatter

# Ignore DeprecationWarnings from third-party packages (site-packages)
warnings.filterwarnings("ignore", category=DeprecationWarning, module=r".*site-packages.*")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
NUMERIC_LEVEL = getattr(logging, LOG_LEVEL, logging.INFO)

WORKFLOW_RUNTIME_LOG_LEVEL = os.getenv("WORKFLOW_RUNTIME_LOG_LEVEL", "WARNING")
WORKFLOW_CLIENT_LOG_LEVEL = os.getenv("WORKFLOW_CLIENT_LOG_LEVEL", "WARNING")


def add_callsite_from_record(_logger: logging.Logger, _method_name: str, event_dict: dict) -> dict:
    record = event_dict.get("_record")
    if record is not None:
        event_dict.setdefault("logger", record.name)
        event_dict.setdefault("module", record.module)
        event_dict.setdefault("func", record.funcName)
        event_dict.setdefault("line", record.lineno)
    return event_dict


foreign_pre_chain = [
    add_callsite_from_record,
    structlog.stdlib.add_log_level,
    structlog.processors.StackInfoRenderer(),
    structlog.processors.format_exc_info,
]

formatter = ProcessorFormatter(
    processor=structlog.dev.ConsoleRenderer(colors=True),
    foreign_pre_chain=foreign_pre_chain,
)

handler = logging.StreamHandler(stream=sys.stdout)
handler.setFormatter(formatter)

root = logging.getLogger()
root.handlers[:] = [handler]
root.setLevel("WARNING")
logging.captureWarnings(True)

# structlog -> hand off to ProcessorFormatter (no direct rendering here)
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,  # adds "logger" for your own logs
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        # structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        ProcessorFormatter.wrap_for_formatter,  # defer final render
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    logging.getLogger(name).setLevel(LOG_LEVEL)
    return structlog.get_logger(name)


_REDACTED = "[REDACTED]"
_SENSITIVE_KEY_MARKERS = (
    "secret",
    "password",
    "passwd",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "credential",
    "private_key",
)


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(marker in lowered for marker in _SENSITIVE_KEY_MARKERS)


def redact_sensitive_data(value: Any, key: str | None = None) -> Any:
    """Recursively redact values likely to contain secrets before logging."""
    if key and _is_sensitive_key(key):
        return _REDACTED

    if isinstance(value, Mapping):
        return {k: redact_sensitive_data(v, key=str(k)) for k, v in value.items()}

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [redact_sensitive_data(item, key=key) for item in value]

    return value


def log_dependency_failure(
    logger: structlog.stdlib.BoundLogger,
    *,
    service: str,
    dependency: str,
    detail: str,
    remediation: str | None = None,
    readiness: str = "unhealthy",
    context: Mapping[str, Any] | None = None,
) -> None:
    """Emit a standardized, secret-safe readiness failure event."""
    payload: dict[str, Any] = {
        "service": service,
        "dependency": dependency,
        "readiness": readiness,
        "detail": detail,
    }
    if remediation:
        payload["remediation"] = remediation
    if context:
        payload["context"] = redact_sensitive_data(context)

    logger.warning("Dependency readiness check failed", **payload)
