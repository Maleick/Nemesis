"""Regression tests for throughput policy status/evaluation contracts."""

from datetime import UTC, datetime, timedelta

import web_api.main as web_main


def _queue_metrics(new_file_ready: int, doc_ready: int = 0, nosey_ready: int = 0) -> dict:
    total_queued = new_file_ready + doc_ready + nosey_ready
    return {
        "queue_details": {
            "new_file": {"ready_messages": new_file_ready},
            "document_conversion_input": {"ready_messages": doc_ready},
            "noseyparker_input": {"ready_messages": nosey_ready},
        },
        "summary": {
            "total_queued_messages": total_queued,
            "total_processing_messages": 0,
            "bottleneck_queues": [],
            "queues_without_consumers": [],
        },
    }


def test_throughput_policy_status_reports_fail_safe_conservative_mode(client, monkeypatch):
    web_main._reset_throughput_policy_state()

    async def _mock_inputs():
        return (_queue_metrics(new_file_ready=5), {}, {}, {})

    monkeypatch.setattr("web_api.main._load_observability_inputs", _mock_inputs)

    response = client.get("/workflows/throughput-policy/status?preset=aggressive&telemetry_stale=true")

    assert response.status_code == 200
    payload = response.json()
    assert payload["requested_preset"] == "aggressive"
    assert payload["active_preset"] == "conservative"
    assert payload["fail_safe"] is True
    assert payload["policy_active"] is True
    assert "fail-safe" in payload["fail_safe_reason"]
    assert payload["queue_pressure_level"] == "critical"


def test_throughput_policy_status_requires_sustained_window_before_activation(client, monkeypatch):
    web_main._reset_throughput_policy_state()

    async def _mock_inputs():
        return (_queue_metrics(new_file_ready=250, doc_ready=120), {}, {}, {})

    monkeypatch.setattr("web_api.main._load_observability_inputs", _mock_inputs)

    start = datetime(2026, 2, 25, 13, 0, tzinfo=UTC)
    clock = iter([start, start + timedelta(seconds=30), start + timedelta(seconds=61)])
    monkeypatch.setattr("web_api.main._utcnow", lambda: next(clock))

    first = client.get("/workflows/throughput-policy/status?preset=balanced")
    second = client.get("/workflows/throughput-policy/status?preset=balanced")
    third = client.get("/workflows/throughput-policy/status?preset=balanced")

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 200

    assert first.json()["policy_active"] is False
    assert second.json()["policy_active"] is False
    assert third.json()["policy_active"] is True
    assert third.json()["queue_pressure_level"] == "critical"
    assert third.json()["sustained_seconds"] >= third.json()["sustained_seconds_required"]


def test_throughput_policy_status_respects_cooldown_before_reactivation(client, monkeypatch):
    web_main._reset_throughput_policy_state()

    state = {"queue_ready": 250}

    async def _mock_inputs():
        return (_queue_metrics(new_file_ready=state["queue_ready"]), {}, {}, {})

    monkeypatch.setattr("web_api.main._load_observability_inputs", _mock_inputs)

    start = datetime(2026, 2, 25, 14, 0, tzinfo=UTC)
    clock = iter(
        [
            start,
            start + timedelta(seconds=61),
            start + timedelta(seconds=62),
            start + timedelta(seconds=70),
        ]
    )
    monkeypatch.setattr("web_api.main._utcnow", lambda: next(clock))

    first = client.post("/workflows/throughput-policy/evaluate?preset=balanced")
    second = client.post("/workflows/throughput-policy/evaluate?preset=balanced")

    state["queue_ready"] = 0
    third = client.post("/workflows/throughput-policy/evaluate?preset=balanced")

    state["queue_ready"] = 250
    fourth = client.post("/workflows/throughput-policy/evaluate?preset=balanced")

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 200
    assert fourth.status_code == 200

    assert second.json()["policy_active"] is True
    assert third.json()["policy_active"] is False
    assert third.json()["cooldown_remaining_seconds"] > 0
    assert fourth.json()["policy_active"] is False
    assert fourth.json()["cooldown_remaining_seconds"] > 0
