"""Regression tests for document conversion throughput policy controls."""

from datetime import UTC, datetime, timedelta
import importlib
import sys
import types


def _load_workflow_manager_module():
    sys.modules.pop("document_conversion.workflow_manager", None)
    workflow_stub = types.ModuleType("document_conversion.workflow")
    workflow_stub.document_conversion_workflow = object()
    sys.modules["document_conversion.workflow"] = workflow_stub
    return importlib.import_module("document_conversion.workflow_manager")


def test_policy_sustained_and_cooldown_transitions():
    workflow_manager = _load_workflow_manager_module()
    workflow_manager.reset_throughput_policy_state()

    start = datetime(2026, 2, 25, 16, 30, tzinfo=UTC)
    first = workflow_manager.evaluate_throughput_policy(active_workflow_count=4, preset="balanced", now=start)
    second = workflow_manager.evaluate_throughput_policy(
        active_workflow_count=4,
        preset="balanced",
        now=start + timedelta(seconds=61),
    )
    recovered = workflow_manager.evaluate_throughput_policy(
        active_workflow_count=0,
        preset="balanced",
        now=start + timedelta(seconds=62),
    )
    reattempt = workflow_manager.evaluate_throughput_policy(
        active_workflow_count=4,
        preset="balanced",
        now=start + timedelta(seconds=70),
    )

    assert first["policy_active"] is False
    assert second["policy_active"] is True
    assert recovered["policy_active"] is False
    assert recovered["cooldown_remaining_seconds"] > 0
    assert reattempt["policy_active"] is False
    assert reattempt["cooldown_remaining_seconds"] > 0


def test_expensive_workload_parallelism_keeps_minimum_floor():
    workflow_manager = _load_workflow_manager_module()
    workflow_manager.reset_throughput_policy_state()

    start = datetime(2026, 2, 25, 17, 0, tzinfo=UTC)
    workflow_manager.evaluate_throughput_policy(active_workflow_count=4, preset="balanced", now=start)
    active = workflow_manager.evaluate_throughput_policy(
        active_workflow_count=4,
        preset="balanced",
        now=start + timedelta(seconds=61),
    )

    expensive_limit = workflow_manager._current_effective_parallelism(active, is_expensive_workload=True)
    baseline_limit = workflow_manager._current_effective_parallelism(active, is_expensive_workload=False)

    assert active["policy_active"] is True
    assert expensive_limit >= active["expensive_floor"]
    assert expensive_limit >= 1
    assert baseline_limit >= expensive_limit


def test_fail_safe_mode_forces_conservative_policy():
    workflow_manager = _load_workflow_manager_module()
    workflow_manager.reset_throughput_policy_state()

    snapshot = workflow_manager.evaluate_throughput_policy(
        active_workflow_count=0,
        preset="aggressive",
        telemetry_stale=True,
        now=datetime(2026, 2, 25, 17, 30, tzinfo=UTC),
    )

    assert snapshot["requested_preset"] == "aggressive"
    assert snapshot["active_preset"] == "conservative"
    assert snapshot["fail_safe"] is True
    assert snapshot["policy_active"] is True
    assert "fail-safe" in snapshot["fail_safe_reason"]
