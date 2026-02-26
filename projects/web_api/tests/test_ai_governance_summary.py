"""Regression tests for AI governance observability summary contracts."""

import web_api.main as web_main


def _base_inputs():
    queue_metrics = {
        "summary": {
            "total_queued_messages": 10,
            "total_processing_messages": 2,
            "bottleneck_queues": [],
            "queues_without_consumers": [],
        }
    }
    workflow_status = {"active_workflows": 1}
    failed_workflows = {"failed_count": 0}
    health_payload = {"readiness": "healthy", "dependencies": []}
    return queue_metrics, workflow_status, failed_workflows, health_payload


def test_observability_summary_ai_governance_critical_when_budget_exceeded(monkeypatch):
    monkeypatch.setenv("AI_GOV_BUDGET_LIMIT", "100")
    monkeypatch.setenv("AI_GOV_BUDGET_WARN_RATIO", "0.75")
    monkeypatch.setenv("AI_GOV_BUDGET_CRITICAL_RATIO", "1.0")

    queue_metrics, workflow_status, failed_workflows, health_payload = _base_inputs()
    payload = web_main._build_observability_summary_payload(
        queue_metrics=queue_metrics,
        workflow_status=workflow_status,
        failed_workflows=failed_workflows,
        health_payload=health_payload,
        ai_governance_data={
            "total_spend": 120.0,
            "total_tokens": 5000,
            "total_requests": 20,
        },
        llm_auth_status={"mode": "official_key", "healthy": True},
    )

    assert payload["ai_governance"]["severity"] == "critical"
    assert payload["ai_governance"]["utilization_ratio"] == 1.2
    assert payload["ai_governance"]["fail_safe"] is False


def test_observability_summary_ai_governance_warning_when_spend_telemetry_unavailable(monkeypatch):
    monkeypatch.setenv("AI_GOV_BUDGET_LIMIT", "100")
    monkeypatch.setenv("AI_GOV_BUDGET_WARN_RATIO", "0.75")
    monkeypatch.setenv("AI_GOV_BUDGET_CRITICAL_RATIO", "1.0")

    queue_metrics, workflow_status, failed_workflows, health_payload = _base_inputs()
    payload = web_main._build_observability_summary_payload(
        queue_metrics=queue_metrics,
        workflow_status=workflow_status,
        failed_workflows=failed_workflows,
        health_payload=health_payload,
        ai_governance_data={"error": "agents service unavailable"},
        llm_auth_status={"mode": "codex_oauth", "healthy": False},
    )

    assert payload["ai_governance"]["severity"] == "warning"
    assert payload["ai_governance"]["fail_safe"] is True
    assert "Spend telemetry unavailable" in payload["ai_governance"]["fail_safe_reason"]
    assert "LLM auth unhealthy" in payload["ai_governance"]["fail_safe_reason"]


def test_observability_summary_route_includes_ai_governance_block(client, monkeypatch):
    async def _mock_obs_inputs():
        return _base_inputs()

    async def _mock_ai_inputs():
        return (
            {"total_spend": 40.0, "total_tokens": 1200, "total_requests": 8},
            {"mode": "official_key", "healthy": True},
        )

    monkeypatch.setattr("web_api.main._load_observability_inputs", _mock_obs_inputs)
    monkeypatch.setattr("web_api.main._load_ai_governance_inputs", _mock_ai_inputs)

    response = client.get("/workflows/observability/summary")
    assert response.status_code == 200
    payload = response.json()
    assert "ai_governance" in payload
    assert payload["ai_governance"]["total_spend"] == 40.0
    assert payload["ai_governance"]["total_requests"] == 8


def test_observability_summary_ai_governance_warning_threshold(monkeypatch):
    monkeypatch.setenv("AI_GOV_BUDGET_LIMIT", "200")
    monkeypatch.setenv("AI_GOV_BUDGET_WARN_RATIO", "0.60")
    monkeypatch.setenv("AI_GOV_BUDGET_CRITICAL_RATIO", "0.90")

    queue_metrics, workflow_status, failed_workflows, health_payload = _base_inputs()
    payload = web_main._build_observability_summary_payload(
        queue_metrics=queue_metrics,
        workflow_status=workflow_status,
        failed_workflows=failed_workflows,
        health_payload=health_payload,
        ai_governance_data={
            "total_spend": 130.0,
            "total_tokens": 7000,
            "total_requests": 33,
        },
        llm_auth_status={"mode": "official_key", "healthy": True},
    )

    assert payload["ai_governance"]["severity"] == "warning"
    assert payload["ai_governance"]["fail_safe"] is False
    assert payload["ai_governance"]["utilization_ratio"] == 0.65


def test_observability_summary_ai_governance_normal_when_under_warning(monkeypatch):
    monkeypatch.setenv("AI_GOV_BUDGET_LIMIT", "500")
    monkeypatch.setenv("AI_GOV_BUDGET_WARN_RATIO", "0.80")
    monkeypatch.setenv("AI_GOV_BUDGET_CRITICAL_RATIO", "0.95")

    queue_metrics, workflow_status, failed_workflows, health_payload = _base_inputs()
    payload = web_main._build_observability_summary_payload(
        queue_metrics=queue_metrics,
        workflow_status=workflow_status,
        failed_workflows=failed_workflows,
        health_payload=health_payload,
        ai_governance_data={
            "total_spend": 120.0,
            "total_tokens": 3200,
            "total_requests": 11,
        },
        llm_auth_status={"mode": "official_key", "healthy": True},
    )

    assert payload["ai_governance"]["severity"] == "normal"
    assert payload["ai_governance"]["fail_safe_reason"] is None
