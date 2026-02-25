"""Security regressions for NoseyParker JWT handling logs."""

import sys
import types

# NoseyParker module imports file_enrichment.global_vars, which initializes
# Dapr-backed clients at import time. Stub it for isolated unit tests.
_global_vars_stub = types.ModuleType("file_enrichment.global_vars")
_global_vars_stub.tracking_service = None
_global_vars_stub.asyncpg_pool = None
sys.modules.setdefault("file_enrichment.global_vars", _global_vars_stub)

# Avoid importing the heavy file_enrichment.activities package (libmagic dependency)
# while unit-testing JWT parsing helpers.
_activities_stub = types.ModuleType("file_enrichment.activities")
_publish_findings_stub = types.ModuleType("file_enrichment.activities.publish_findings")


async def _noop_publish_alerts_for_findings(*_args, **_kwargs):
    return None


_publish_findings_stub.publish_alerts_for_findings = _noop_publish_alerts_for_findings
_activities_stub.publish_findings = _publish_findings_stub
sys.modules.setdefault("file_enrichment.activities", _activities_stub)
sys.modules.setdefault("file_enrichment.activities.publish_findings", _publish_findings_stub)

from file_enrichment.subscriptions import noseyparker


class _DummyLogger:
    def __init__(self):
        self.calls = []

    def exception(self, *args, **kwargs):
        self.calls.append({"args": args, "kwargs": kwargs})


def test_is_jwt_expired_invalid_format_does_not_log_raw_token(monkeypatch):
    dummy_logger = _DummyLogger()
    token = "very-secret-token-without-dots"
    monkeypatch.setattr(noseyparker, "logger", dummy_logger)

    expired, payload = noseyparker.is_jwt_expired(token)

    assert expired is False
    assert payload == {}
    assert dummy_logger.calls
    call = dummy_logger.calls[-1]
    assert "jwt_token" not in call["kwargs"]
    assert call["kwargs"].get("jwt_length") == len(token)


def test_is_jwt_expired_decode_failure_does_not_log_raw_token(monkeypatch):
    dummy_logger = _DummyLogger()
    token = "aaaa.b@d_payload.cccc"
    monkeypatch.setattr(noseyparker, "logger", dummy_logger)

    expired, payload = noseyparker.is_jwt_expired(token)

    assert expired is True
    assert payload == {}
    assert dummy_logger.calls
    call = dummy_logger.calls[-1]
    assert "jwt_token" not in call["kwargs"]
    assert call["kwargs"].get("jwt_length") == len(token)
