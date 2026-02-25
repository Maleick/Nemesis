"""Unit tests for shared readiness contract helpers."""

from common.health_contract import (
    build_health_response,
    dependency_degraded,
    dependency_failed,
    dependency_ok,
)
from common.logger import redact_sensitive_data
from common.models2.health import ReadinessLevel


def test_health_contract_healthy_response():
    payload = build_health_response(
        service="web_api",
        dependencies=[
            dependency_ok("postgres"),
            dependency_ok("workflow-runtime"),
        ],
    )

    assert payload["service"] == "web_api"
    assert payload["status"] == "healthy"
    assert payload["readiness"] == ReadinessLevel.HEALTHY
    assert len(payload["dependencies"]) == 2


def test_health_contract_required_dependency_failure_is_unhealthy():
    payload = build_health_response(
        service="document_conversion",
        dependencies=[
            dependency_ok("postgres"),
            dependency_failed("jvm", "JVM not started", remediation="Check document-conversion startup logs"),
        ],
    )

    assert payload["status"] == "unhealthy"
    assert payload["readiness"] == ReadinessLevel.UNHEALTHY
    assert payload["dependencies"][1]["remediation"] == "Check document-conversion startup logs"


def test_health_contract_optional_dependency_failure_is_degraded():
    payload = build_health_response(
        service="agents",
        dependencies=[
            dependency_ok("workflow-runtime"),
            dependency_degraded(
                "llm-auth",
                "LLM auth unavailable",
                remediation="Validate LLM auth mode credentials",
                optional=True,
            ),
        ],
    )

    # Keep status backward-compatible while exposing richer readiness detail.
    assert payload["status"] == "healthy"
    assert payload["readiness"] == ReadinessLevel.DEGRADED


def test_health_contract_supports_minimal_legacy_payload():
    payload = build_health_response(
        service="file_enrichment",
        dependencies=[dependency_failed("postgres", "Database unavailable")],
        include_details=False,
    )

    assert payload == {"status": "unhealthy"}


def test_redact_sensitive_data_masks_nested_secret_fields():
    redacted = redact_sensitive_data(
        {
            "auth": {
                "token": "abc",
                "refresh_token": "def",
                "mode": "official_key",
            },
            "password": "p@ssw0rd",
            "safe": "ok",
        }
    )

    assert redacted["auth"]["token"] == "[REDACTED]"
    assert redacted["auth"]["refresh_token"] == "[REDACTED]"
    assert redacted["password"] == "[REDACTED]"
    assert redacted["safe"] == "ok"
