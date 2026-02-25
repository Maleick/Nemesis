import logging
import os
import re
import sys
import warnings
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import urlsplit

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

_SENSITIVE_TEXT_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"(?i)\b(bearer)\s+[A-Za-z0-9._-]+"),
        r"\1 [REDACTED]",
    ),
    (
        re.compile(
            r"(?i)\b(password|passwd|token|secret|api[_-]?key|apikey|authorization|cookie|jwt|private[_-]?key)\b\s*[:=]\s*['\"]?([^'\",\s]+)['\"]?"
        ),
        r"\1=[REDACTED]",
    ),
    (
        re.compile(r"(?i)(password|passwd|token|secret|api[_-]?key|apikey|authorization|cookie|jwt)=([^&\s]+)"),
        r"\1=[REDACTED]",
    ),
    (
        re.compile(r"\b[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{8,}\b"),
        _REDACTED,
    ),
)


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(marker in lowered for marker in _SENSITIVE_KEY_MARKERS)


def _redact_sensitive_text(text: str) -> str:
    redacted = text
    for pattern, replacement in _SENSITIVE_TEXT_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def redact_sensitive_data(value: Any, key: str | None = None) -> Any:
    """Recursively redact values likely to contain secrets before logging."""
    if key and _is_sensitive_key(key):
        return _REDACTED

    if isinstance(value, Mapping):
        return {k: redact_sensitive_data(v, key=str(k)) for k, v in value.items()}

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [redact_sensitive_data(item, key=key) for item in value]

    return value


def sanitize_log_detail(detail: str, *, max_length: int = 300) -> str:
    """Bound noisy dependency details while preserving debugging utility."""
    normalized = " ".join(_redact_sensitive_text(str(detail)).split())
    if len(normalized) <= max_length:
        return normalized
    return f"{normalized[:max_length]}..."


def sanitize_exception_message(error: Any, *, max_length: int = 300) -> str:
    """Return a compact, redacted exception string for logs and status payloads."""
    return sanitize_log_detail(str(error), max_length=max_length)


def sanitize_url_for_logging(url: str, *, max_path_length: int = 64) -> str:
    """Return a URL representation with credentials/query redacted for logs."""
    if not url:
        return "<empty>"

    try:
        parsed = urlsplit(url)
    except ValueError:
        return sanitize_log_detail(url, max_length=max_path_length)

    if not parsed.scheme:
        return sanitize_log_detail(url, max_length=max_path_length)

    host = parsed.hostname or ""
    if parsed.port:
        host = f"{host}:{parsed.port}"
    if parsed.username or parsed.password:
        host = f"[REDACTED]@{host}" if host else "[REDACTED]"

    path = parsed.path or ""
    if len(path) > max_path_length:
        path = f"{path[:max_path_length]}..."

    query_suffix = "?..." if parsed.query else ""
    return f"{parsed.scheme}://{host}{path}{query_suffix}"


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
        "detail": sanitize_log_detail(detail),
    }
    if remediation:
        payload["remediation"] = remediation
    if context:
        payload["context"] = redact_sensitive_data(context)

    logger.warning("Dependency readiness check failed", **payload)
