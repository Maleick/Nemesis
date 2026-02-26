"""Regression tests for queue-pressure throughput policy behavior."""

from datetime import UTC, datetime, timedelta
import importlib
import sys
import types


def _load_subscription_module():
    sys.modules.pop("file_enrichment.subscriptions.file", None)
    global_vars_stub = types.ModuleType("file_enrichment.global_vars")
    global_vars_stub.workflow_manager = None
    global_vars_stub.asyncpg_pool = None
    sys.modules["file_enrichment.global_vars"] = global_vars_stub
    return importlib.import_module("file_enrichment.subscriptions.file")


def test_policy_requires_sustained_queue_pressure_before_activation():
    file_subscription = _load_subscription_module()
    file_subscription.reset_throughput_policy_state()

    start = datetime(2026, 2, 25, 15, 0, tzinfo=UTC)
    first = file_subscription.evaluate_throughput_policy(queue_depth=80, preset="balanced", now=start)
    second = file_subscription.evaluate_throughput_policy(
        queue_depth=80,
        preset="balanced",
        now=start + timedelta(seconds=61),
    )

    assert first["policy_active"] is False
    assert second["policy_active"] is True
    assert second["queue_pressure_level"] in {"warning", "critical"}
    assert second["sustained_seconds"] >= second["sustained_seconds_required"]


def test_policy_enters_cooldown_after_recovery():
    file_subscription = _load_subscription_module()
    file_subscription.reset_throughput_policy_state()

    start = datetime(2026, 2, 25, 15, 30, tzinfo=UTC)
    file_subscription.evaluate_throughput_policy(queue_depth=120, preset="balanced", now=start)
    active = file_subscription.evaluate_throughput_policy(
        queue_depth=120,
        preset="balanced",
        now=start + timedelta(seconds=61),
    )
    recovered = file_subscription.evaluate_throughput_policy(
        queue_depth=0,
        preset="balanced",
        now=start + timedelta(seconds=62),
    )
    reattempt = file_subscription.evaluate_throughput_policy(
        queue_depth=120,
        preset="balanced",
        now=start + timedelta(seconds=70),
    )

    assert active["policy_active"] is True
    assert recovered["policy_active"] is False
    assert recovered["cooldown_remaining_seconds"] > 0
    assert reattempt["policy_active"] is False
    assert reattempt["cooldown_remaining_seconds"] > 0


def test_policy_uses_fail_safe_conservative_mode_when_telemetry_is_stale():
    file_subscription = _load_subscription_module()
    file_subscription.reset_throughput_policy_state()

    snapshot = file_subscription.evaluate_throughput_policy(
        queue_depth=1,
        preset="aggressive",
        telemetry_stale=True,
        now=datetime(2026, 2, 25, 16, 0, tzinfo=UTC),
    )

    assert snapshot["requested_preset"] == "aggressive"
    assert snapshot["active_preset"] == "conservative"
    assert snapshot["fail_safe"] is True
    assert snapshot["policy_active"] is True
    assert snapshot["defer_expensive_admission"] is True
    assert "fail-safe" in snapshot["fail_safe_reason"]
