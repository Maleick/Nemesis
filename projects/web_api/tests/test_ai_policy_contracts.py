"""Regression tests for AI synthesis policy-context and override contracts."""


class _DummyReport:
    def __init__(self, payload: dict):
        self._payload = payload

    def model_dump(self, mode: str = "python"):  # noqa: ARG002
        return self._payload


class _DummyResponse:
    def __init__(self, status_code: int, payload: dict, text: str = ""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        return self._payload


def test_source_synthesis_returns_policy_context_and_legacy_keys(client, monkeypatch):
    monkeypatch.setattr(
        "web_api.reporting_routes.get_source_report_data",
        lambda *args, **kwargs: _DummyReport({"summary": {"finding_count": 2}}),
    )
    monkeypatch.setattr("web_api.main.get_db_pool", lambda: object())

    captured = {}

    def _mock_post(url, json, timeout):  # noqa: ARG001
        captured["request"] = json
        return _DummyResponse(
            200,
            {
                "success": True,
                "risk_level": "medium",
                "critical_findings": ["critical finding"],
                "full_report_markdown": "## Executive Summary\n- details",
                "token_usage": 321,
                "policy_context": {
                    "policy_mode": "balanced",
                    "confidence_score": 0.74,
                    "confidence_band": "medium",
                    "override": {
                        "requested": True,
                        "requested_mode": "strict_review",
                        "applied_mode": "balanced",
                        "reason": "operator requested extra caution",
                        "source": "operator",
                    },
                },
            },
        )

    monkeypatch.setattr("web_api.main.requests.post", _mock_post)

    response = client.post(
        "/reports/source/synthesize?source=test-source&policy_mode=strict_review&policy_override_reason=operator-requested"
    )
    assert response.status_code == 200
    payload = response.json()

    # Legacy keys remain available for existing consumers.
    assert payload["success"] is True
    assert payload["risk_level"] == "medium"
    assert payload["token_usage"] == 321
    assert "report_markdown" in payload
    assert "key_findings" in payload

    # New policy context contract is present and override-aware.
    assert payload["policy_context"]["policy_mode"] == "balanced"
    assert payload["policy_context"]["confidence_band"] == "medium"
    assert payload["policy_context"]["override"]["requested"] is True
    assert payload["policy_context"]["override"]["requested_mode"] == "strict_review"

    # Request passes explicit operator override to agents service.
    assert captured["request"]["policy_override"]["requested_mode"] == "strict_review"
    assert captured["request"]["policy_override"]["reason"] == "operator-requested"


def test_system_synthesis_builds_default_policy_context_when_upstream_missing(client, monkeypatch):
    monkeypatch.setattr(
        "web_api.reporting_routes.get_system_report_data",
        lambda *args, **kwargs: _DummyReport({"summary": {"total_sources": 1}}),
    )
    monkeypatch.setattr("web_api.main.get_db_pool", lambda: object())

    monkeypatch.setattr(
        "web_api.main.requests.post",
        lambda *args, **kwargs: _DummyResponse(
            200,
            {
                "success": True,
                "risk_level": "low",
                "critical_findings": [],
                "full_report_markdown": "## Executive Summary\n- ok",
                "token_usage": 11,
            },
        ),
    )

    response = client.post("/reports/system/synthesize")
    assert response.status_code == 200
    payload = response.json()

    assert payload["success"] is True
    assert payload["risk_level"] == "low"
    assert payload["token_usage"] == 11
    assert payload["policy_context"]["policy_mode"] in {"balanced", "strict_review"}
    assert payload["policy_context"]["override"]["requested"] is False


def test_synthesis_failure_returns_fail_safe_policy_context(client, monkeypatch):
    monkeypatch.setattr(
        "web_api.reporting_routes.get_source_report_data",
        lambda *args, **kwargs: _DummyReport({"summary": {}}),
    )
    monkeypatch.setattr("web_api.main.get_db_pool", lambda: object())
    monkeypatch.setattr(
        "web_api.main.requests.post",
        lambda *args, **kwargs: _DummyResponse(
            200,
            {
                "success": False,
                "error": "agents unavailable",
            },
        ),
    )

    response = client.post("/reports/source/synthesize?source=test-source")
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"] == "agents unavailable"
    assert payload["policy_context"]["fail_safe"] is True
