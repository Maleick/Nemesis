"""Workflow concurrency management."""

import asyncio
import os
from datetime import UTC, datetime, timedelta

import document_conversion.global_vars as global_vars
from common.logger import get_logger
from common.models import FileEnriched

from .workflow import document_conversion_workflow

logger = get_logger(__name__)

# Configuration
max_parallel_workflows = int(os.getenv("MAX_PARALLEL_WORKFLOWS", 3))
max_workflow_execution_time = int(os.getenv("MAX_WORKFLOW_EXECUTION_TIME", 300))

_EXPENSIVE_EXTENSIONS = {".zip", ".7z", ".rar", ".iso", ".vhd", ".vhdx", ".pdf", ".docx", ".xls", ".xlsx"}
_THROUGHPUT_POLICY_PRESETS = {
    "conservative": {
        "warn": max(1, max_parallel_workflows - 1),
        "critical": max(1, max_parallel_workflows),
        "sustained_seconds": 45,
        "cooldown_seconds": 90,
        "expensive_parallelism": 1,
        "baseline_parallelism": max(1, max_parallel_workflows - 1),
        "expensive_floor": 1,
        "throttle_sleep_seconds": 0.05,
    },
    "balanced": {
        "warn": max(1, max_parallel_workflows - 1),
        "critical": max(1, max_parallel_workflows),
        "sustained_seconds": 60,
        "cooldown_seconds": 120,
        "expensive_parallelism": max(1, max_parallel_workflows // 2),
        "baseline_parallelism": max(1, max_parallel_workflows),
        "expensive_floor": 1,
        "throttle_sleep_seconds": 0.03,
    },
    "aggressive": {
        "warn": max(1, max_parallel_workflows),
        "critical": max(1, max_parallel_workflows + 1),
        "sustained_seconds": 90,
        "cooldown_seconds": 120,
        "expensive_parallelism": max(1, max_parallel_workflows),
        "baseline_parallelism": max(1, max_parallel_workflows),
        "expensive_floor": 1,
        "throttle_sleep_seconds": 0.01,
    },
}
_throughput_policy_state: dict[str, datetime | bool | str | None] = {
    "active_since": None,
    "cooldown_until": None,
    "last_active": False,
    "last_level": "normal",
    "last_preset": "balanced",
}

# Semaphore for controlling concurrent workflow execution
workflow_semaphore = asyncio.Semaphore(max_parallel_workflows)
active_workflows = {}  # Track active workflows
workflow_lock = asyncio.Lock()  # For synchronizing access to active_workflows


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _policy_now(now: datetime | None = None) -> datetime:
    return now if now is not None else datetime.now(UTC)


def _resolve_throughput_preset(requested_preset: str | None) -> tuple[str, dict]:
    selected = (requested_preset or os.getenv("THROUGHPUT_POLICY_PRESET", "balanced")).strip().lower()
    if selected not in _THROUGHPUT_POLICY_PRESETS:
        selected = "balanced"
    return selected, _THROUGHPUT_POLICY_PRESETS[selected]


def reset_throughput_policy_state() -> None:
    _throughput_policy_state["active_since"] = None
    _throughput_policy_state["cooldown_until"] = None
    _throughput_policy_state["last_active"] = False
    _throughput_policy_state["last_level"] = "normal"
    _throughput_policy_state["last_preset"] = "balanced"


def evaluate_throughput_policy(
    active_workflow_count: int,
    telemetry_stale: bool = False,
    preset: str | None = None,
    now: datetime | None = None,
) -> dict:
    current_time = _policy_now(now)
    requested_preset, preset_cfg = _resolve_throughput_preset(preset)
    active_preset = "conservative" if telemetry_stale else requested_preset
    if telemetry_stale:
        preset_cfg = _THROUGHPUT_POLICY_PRESETS["conservative"]

    warning_threshold = int(preset_cfg["warn"])
    critical_threshold = int(preset_cfg["critical"])
    sustained_required = int(preset_cfg["sustained_seconds"])
    cooldown_seconds = int(preset_cfg["cooldown_seconds"])

    if telemetry_stale:
        queue_pressure_level = "critical"
    elif active_workflow_count >= critical_threshold:
        queue_pressure_level = "critical"
    elif active_workflow_count >= warning_threshold:
        queue_pressure_level = "warning"
    else:
        queue_pressure_level = "normal"

    if queue_pressure_level != "normal":
        if _throughput_policy_state["active_since"] is None:
            _throughput_policy_state["active_since"] = current_time
    else:
        if _throughput_policy_state["last_active"]:
            _throughput_policy_state["cooldown_until"] = current_time + timedelta(seconds=cooldown_seconds)
        _throughput_policy_state["active_since"] = None

    sustained_seconds = 0
    active_since = _throughput_policy_state["active_since"]
    if isinstance(active_since, datetime):
        sustained_seconds = int((current_time - active_since).total_seconds())

    cooldown_remaining_seconds = 0
    cooldown_until = _throughput_policy_state["cooldown_until"]
    if isinstance(cooldown_until, datetime):
        cooldown_remaining_seconds = max(0, int((cooldown_until - current_time).total_seconds()))
        if cooldown_remaining_seconds == 0:
            _throughput_policy_state["cooldown_until"] = None

    policy_active = (
        telemetry_stale
        or (
            queue_pressure_level in {"warning", "critical"}
            and sustained_seconds >= sustained_required
            and cooldown_remaining_seconds == 0
        )
    )
    if telemetry_stale:
        sustained_seconds = sustained_required

    _throughput_policy_state["last_active"] = policy_active
    _throughput_policy_state["last_level"] = queue_pressure_level
    _throughput_policy_state["last_preset"] = active_preset

    return {
        "requested_preset": requested_preset,
        "active_preset": active_preset,
        "queue_pressure_level": queue_pressure_level,
        "policy_active": policy_active,
        "active_workflow_count": active_workflow_count,
        "warning_threshold": warning_threshold,
        "critical_threshold": critical_threshold,
        "sustained_seconds": sustained_seconds,
        "sustained_seconds_required": sustained_required,
        "cooldown_seconds": cooldown_seconds,
        "cooldown_remaining_seconds": cooldown_remaining_seconds,
        "baseline_parallelism": max(1, min(max_parallel_workflows, int(preset_cfg["baseline_parallelism"]))),
        "expensive_parallelism": max(1, min(max_parallel_workflows, int(preset_cfg["expensive_parallelism"]))),
        "expensive_floor": max(1, min(max_parallel_workflows, int(preset_cfg["expensive_floor"]))),
        "throttle_sleep_seconds": float(preset_cfg["throttle_sleep_seconds"]),
        "fail_safe": telemetry_stale,
        "fail_safe_reason": (
            "Queue telemetry unavailable; fail-safe conservative throttling active." if telemetry_stale else None
        ),
    }


def _is_expensive_workload(file_enriched: FileEnriched) -> bool:
    file_name = (file_enriched.file_name or "").lower()
    _, extension = os.path.splitext(file_name)
    return extension in _EXPENSIVE_EXTENSIONS


def _current_effective_parallelism(policy_snapshot: dict, is_expensive_workload: bool) -> int:
    if not bool(policy_snapshot.get("policy_active", False)):
        return max(1, max_parallel_workflows)

    if is_expensive_workload:
        return max(
            int(policy_snapshot["expensive_floor"]),
            int(policy_snapshot["expensive_parallelism"]),
        )
    return max(1, int(policy_snapshot["baseline_parallelism"]))


async def start_workflow_with_concurrency_control(file_enriched: FileEnriched):
    """Start a workflow using semaphore for backpressure control."""
    assert global_vars.tracking_service is not None, "tracking_service must be initialized"
    assert global_vars.workflow_client is not None, "workflow_client must be initialized"

    is_expensive_workload = _is_expensive_workload(file_enriched)
    telemetry_stale = _env_bool("DOCUMENTCONVERSION_POLICY_TELEMETRY_STALE")
    throughput_policy = os.getenv("THROUGHPUT_POLICY_PRESET")

    while True:
        async with workflow_lock:
            active_count = len(active_workflows)
        policy_snapshot = evaluate_throughput_policy(
            active_workflow_count=active_count,
            telemetry_stale=telemetry_stale,
            preset=throughput_policy,
        )
        effective_parallelism = _current_effective_parallelism(policy_snapshot, is_expensive_workload)
        if active_count < effective_parallelism:
            break

        logger.debug(
            "Deferring workflow scheduling under throughput policy",
            active_count=active_count,
            effective_parallelism=effective_parallelism,
            queue_pressure_level=policy_snapshot["queue_pressure_level"],
            throughput_policy=policy_snapshot["active_preset"],
            fail_safe=policy_snapshot["fail_safe"],
            expensive_workload=is_expensive_workload,
        )
        await asyncio.sleep(float(policy_snapshot["throttle_sleep_seconds"]))

    # Acquire semaphore - this will block if we're at max capacity
    # This provides natural backpressure to the Dapr pub/sub system
    await workflow_semaphore.acquire()

    try:
        # Register workflow in database before scheduling
        object_id = file_enriched.object_id
        instance_id = await global_vars.tracking_service.register_workflow(
            object_id=object_id,
            filename=file_enriched.file_name,
        )

        # Add to active workflows tracking
        async with workflow_lock:
            active_workflows[instance_id] = {
                "object_id": object_id,
                "start_time": asyncio.get_event_loop().time(),
                "filename": file_enriched.file_name,
                "queue_pressure_level": policy_snapshot["queue_pressure_level"],
                "throughput_policy": policy_snapshot["active_preset"],
                "expensive_workload": is_expensive_workload,
            }

        logger.debug(
            "Scheduling document conversion workflow",
            instance_id=instance_id,
            object_id=object_id,
            file_name=file_enriched.file_name,
            active_count=len(active_workflows),
        )

        # Schedule the workflow (using asyncio.to_thread for sync client)
        await asyncio.to_thread(
            global_vars.workflow_client.schedule_new_workflow,
            workflow=document_conversion_workflow,
            instance_id=instance_id,
            input={"object_id": object_id},
        )

        # Start monitoring task for this workflow
        asyncio.create_task(monitor_workflow_completion(instance_id))

    except Exception:
        logger.exception("Error starting document conversion workflow")
        # Release semaphore on error
        workflow_semaphore.release()
        raise


async def monitor_workflow_completion(instance_id: str):
    """Monitor a workflow until completion and release semaphore."""
    assert global_vars.workflow_client is not None, "workflow_client must be initialized"
    try:
        # Poll for workflow completion
        start_time = asyncio.get_event_loop().time()

        while True:
            try:
                # Check if workflow is still running (using asyncio.to_thread for sync client)
                state = await asyncio.to_thread(global_vars.workflow_client.get_workflow_state, instance_id)

                if state and hasattr(state, "runtime_status"):
                    status = state.runtime_status.name

                    if status in ["COMPLETED", "FAILED", "TERMINATED", "ERROR"]:
                        elapsed_time = asyncio.get_event_loop().time() - start_time
                        logger.info(
                            "Document conversion workflow finished",
                            instance_id=instance_id,
                            status=status,
                            elapsed_time=f"{elapsed_time:.2f}s",
                        )
                        break

                # Check for timeout
                if (asyncio.get_event_loop().time() - start_time) > max_workflow_execution_time:
                    logger.warning(
                        "Document conversion workflow timed out",
                        instance_id=instance_id,
                        max_execution_time=max_workflow_execution_time,
                    )
                    # Try to terminate the workflow (using asyncio.to_thread for sync client)
                    try:
                        await asyncio.to_thread(global_vars.workflow_client.terminate_workflow, instance_id)
                    except Exception as term_error:
                        logger.error(f"Failed to terminate workflow {instance_id}: {term_error}")
                    break

                await asyncio.sleep(0.3)

            except Exception as check_error:
                logger.warning(f"Error checking workflow status for {instance_id}: {check_error}")
                await asyncio.sleep(2)  # Wait longer on error

    except Exception:
        logger.exception(message=f"Error monitoring workflow {instance_id}")

    finally:
        # Always clean up and release semaphore
        async with workflow_lock:
            if instance_id in active_workflows:
                del active_workflows[instance_id]

        workflow_semaphore.release()
        logger.debug(f"Released semaphore for workflow {instance_id}", active_count=len(active_workflows))
