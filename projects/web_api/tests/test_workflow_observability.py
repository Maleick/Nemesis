"""Regression tests for workflow observability lifecycle, summary, and alert gates."""

from datetime import UTC, datetime, timedelta

import web_api.main as web_main


def _summary_payload(queue_severity: str, workflow_severity: str = "normal", health_severity: str = "normal") -> dict:
    return {
        "queue_backlog": {
            "severity": queue_severity,
            "total_queued_messages": 120,
            "total_processing_messages": 8,
            "bottleneck_queues": ["new_file"],
            "queues_without_consumers": [],
            "warning_threshold": 50,
            "critical_threshold": 200,
        },
        "workflow_failures": {
            "severity": workflow_severity,
            "failed_workflows": 6,
            "active_workflows": 2,
            "warning_threshold": 5,
            "critical_threshold": 20,
        },
        "service_health": {
            "severity": health_severity,
            "readiness": "healthy" if health_severity == "normal" else "degraded",
            "unhealthy_dependencies": [],
            "degraded_dependencies": ["agents-llm-auth"] if health_severity != "normal" else [],
        },
        "timestamp": "2026-02-25T00:00:00+00:00",
    }


def test_workflow_lifecycle_route_returns_correlated_payload(client, monkeypatch):
    def _mock_fetch(_object_id: str):
        return {
            "object_id": "abc-123",
            "ingestion": {
                "object_id": "abc-123",
                "agent_id": "agent-1",
                "source": "test-source",
                "project": "proj-1",
                "path": "/tmp/example.txt",
                "file_name": "example.txt",
                "ingested_at": datetime(2026, 2, 25, 0, 0, tzinfo=UTC),
                "observed_at": datetime(2026, 2, 25, 0, 1, tzinfo=UTC),
            },
            "workflows": [
                {
                    "workflow_id": "FileEnrichment.123.abc-123",
                    "status": "COMPLETED",
                    "started_at": datetime(2026, 2, 25, 0, 2, tzinfo=UTC),
                    "runtime_seconds": 5.5,
                    "filename": "example.txt",
                    "success_modules": ["noseyparker"],
                    "failure_modules": [],
                    "error": None,
                }
            ],
            "publication": {
                "enrichments_count": 3,
                "transforms_count": 1,
                "findings_count": 2,
                "last_enrichment_at": datetime(2026, 2, 25, 0, 3, tzinfo=UTC),
                "last_transform_at": datetime(2026, 2, 25, 0, 4, tzinfo=UTC),
                "last_finding_at": datetime(2026, 2, 25, 0, 5, tzinfo=UTC),
            },
            "summary": {
                "latest_status": "COMPLETED",
                "workflow_count": 1,
                "running_count": 0,
                "completed_count": 1,
                "failed_count": 0,
            },
            "timestamp": "2026-02-25T00:06:00+00:00",
        }

    monkeypatch.setattr("web_api.main._fetch_object_lifecycle_payload", _mock_fetch)
    response = client.get("/workflows/lifecycle/abc-123")

    assert response.status_code == 200
    payload = response.json()
    assert payload["object_id"] == "abc-123"
    assert payload["ingestion"]["path"] == "/tmp/example.txt"
    assert payload["summary"]["latest_status"] == "COMPLETED"
    assert payload["publication"]["findings_count"] == 2


def test_workflow_lifecycle_route_returns_404_for_missing_object(client, monkeypatch):
    monkeypatch.setattr("web_api.main._fetch_object_lifecycle_payload", lambda _object_id: None)

    response = client.get("/workflows/lifecycle/missing-id")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_observability_summary_reports_signal_severities(client, monkeypatch):
    async def _mock_inputs():
        return (
            {
                "summary": {
                    "total_queued_messages": 250,
                    "total_processing_messages": 11,
                    "bottleneck_queues": ["new_file", "dotnet_input"],
                    "queues_without_consumers": ["noseyparker_output"],
                }
            },
            {"active_workflows": 4},
            {"failed_count": 24},
            {
                "readiness": "unhealthy",
                "dependencies": [{"name": "postgres", "readiness": "unhealthy"}],
            },
        )

    monkeypatch.setattr("web_api.main._load_observability_inputs", _mock_inputs)

    response = client.get("/workflows/observability/summary")
    assert response.status_code == 200
    payload = response.json()
    assert payload["queue_backlog"]["severity"] == "critical"
    assert payload["workflow_failures"]["severity"] == "critical"
    assert payload["service_health"]["severity"] == "critical"
    assert payload["service_health"]["unhealthy_dependencies"] == ["postgres"]


def test_observability_alert_emits_after_sustained_duration(client, monkeypatch):
    web_main._reset_observability_state()
    monkeypatch.setenv("OBS_SUSTAINED_DURATION_SECONDS", "60")
    monkeypatch.setenv("OBS_ALERT_COOLDOWN_SECONDS", "300")

    async def _mock_inputs():
        return ({}, {}, {}, {})

    monkeypatch.setattr("web_api.main._load_observability_inputs", _mock_inputs)
    monkeypatch.setattr(
        "web_api.main._build_observability_summary_payload",
        lambda **_kwargs: _summary_payload(queue_severity="warning"),
    )

    emitted = []

    async def _mock_publish(condition: str, severity: str, message: str) -> bool:
        emitted.append((condition, severity, message))
        return True

    monkeypatch.setattr("web_api.main._publish_operational_alert", _mock_publish)

    start = datetime(2026, 2, 25, 10, 0, tzinfo=UTC)
    clock = iter([start, start + timedelta(seconds=61)])
    monkeypatch.setattr("web_api.main._utcnow", lambda: next(clock))

    first = client.post("/workflows/observability/alerts/evaluate")
    second = client.post("/workflows/observability/alerts/evaluate")

    assert first.status_code == 200
    assert first.json()["alerts_emitted"] == []
    assert second.status_code == 200
    assert len(second.json()["alerts_emitted"]) == 1
    assert emitted[0][0] == "queue_backlog"


def test_observability_alert_respects_cooldown(client, monkeypatch):
    web_main._reset_observability_state()
    monkeypatch.setenv("OBS_SUSTAINED_DURATION_SECONDS", "60")
    monkeypatch.setenv("OBS_ALERT_COOLDOWN_SECONDS", "300")

    async def _mock_inputs():
        return ({}, {}, {}, {})

    monkeypatch.setattr("web_api.main._load_observability_inputs", _mock_inputs)
    monkeypatch.setattr(
        "web_api.main._build_observability_summary_payload",
        lambda **_kwargs: _summary_payload(queue_severity="warning"),
    )

    emitted = []

    async def _mock_publish(condition: str, severity: str, message: str) -> bool:
        emitted.append(condition)
        return True

    monkeypatch.setattr("web_api.main._publish_operational_alert", _mock_publish)

    start = datetime(2026, 2, 25, 11, 0, tzinfo=UTC)
    clock = iter([start, start + timedelta(seconds=61), start + timedelta(seconds=120)])
    monkeypatch.setattr("web_api.main._utcnow", lambda: next(clock))

    client.post("/workflows/observability/alerts/evaluate")
    second = client.post("/workflows/observability/alerts/evaluate")
    third = client.post("/workflows/observability/alerts/evaluate")

    assert second.status_code == 200
    assert len(second.json()["alerts_emitted"]) == 1
    assert third.status_code == 200
    assert third.json()["alerts_emitted"] == []
    assert third.json()["condition_states"][0]["cooldown_remaining_seconds"] > 0
    assert emitted.count("queue_backlog") == 1


def test_observability_alert_recovery_resets_sustained_timer(client, monkeypatch):
    web_main._reset_observability_state()
    monkeypatch.setenv("OBS_SUSTAINED_DURATION_SECONDS", "60")
    monkeypatch.setenv("OBS_ALERT_COOLDOWN_SECONDS", "10")

    async def _mock_inputs():
        return ({}, {}, {}, {})

    monkeypatch.setattr("web_api.main._load_observability_inputs", _mock_inputs)

    state = {"severity": "warning"}

    def _mock_summary(**_kwargs):
        return _summary_payload(queue_severity=state["severity"])

    monkeypatch.setattr("web_api.main._build_observability_summary_payload", _mock_summary)

    emitted = []

    async def _mock_publish(condition: str, severity: str, message: str) -> bool:
        emitted.append(condition)
        return True

    monkeypatch.setattr("web_api.main._publish_operational_alert", _mock_publish)

    start = datetime(2026, 2, 25, 12, 0, tzinfo=UTC)
    clock = iter(
        [
            start,  # first warning sample
            start + timedelta(seconds=61),  # first sustained trigger
            start + timedelta(seconds=120),  # recovery sample
            start + timedelta(seconds=170),  # warning resumes but not sustained yet
            start + timedelta(seconds=240),  # warning sustained again
        ]
    )
    monkeypatch.setattr("web_api.main._utcnow", lambda: next(clock))

    client.post("/workflows/observability/alerts/evaluate")
    client.post("/workflows/observability/alerts/evaluate")

    state["severity"] = "normal"
    client.post("/workflows/observability/alerts/evaluate")

    state["severity"] = "warning"
    fourth = client.post("/workflows/observability/alerts/evaluate")
    fifth = client.post("/workflows/observability/alerts/evaluate")

    assert fourth.status_code == 200
    assert fourth.json()["alerts_emitted"] == []
    assert fifth.status_code == 200
    assert len(fifth.json()["alerts_emitted"]) == 1
    assert emitted.count("queue_backlog") == 2
