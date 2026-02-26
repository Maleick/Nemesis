"""Handler for file subscription events."""

import asyncio
import os
from datetime import UTC, datetime, timedelta

import file_enrichment.global_vars as global_vars
from common.logger import get_logger
from common.models import CloudEvent, File

logger = get_logger(__name__)


# Configuration
NUM_WORKERS = int(os.getenv("MAX_PARALLEL_WORKFLOWS", 5))

_EXPENSIVE_EXTENSIONS = {".zip", ".7z", ".rar", ".iso", ".vhd", ".vhdx", ".dll", ".exe"}
_THROUGHPUT_POLICY_PRESETS = {
    "conservative": {
        "queue_warn": 10,
        "queue_critical": 20,
        "sustained_seconds": 45,
        "cooldown_seconds": 90,
        "expensive_floor": 1,
        "queue_capacity": max(NUM_WORKERS, 12),
        "expensive_admission_threshold": 4,
        "expensive_admission_delay_seconds": 0.05,
    },
    "balanced": {
        "queue_warn": 18,
        "queue_critical": 35,
        "sustained_seconds": 60,
        "cooldown_seconds": 120,
        "expensive_floor": 1,
        "queue_capacity": max(NUM_WORKERS, NUM_WORKERS * 3),
        "expensive_admission_threshold": 8,
        "expensive_admission_delay_seconds": 0.03,
    },
    "aggressive": {
        "queue_warn": 30,
        "queue_critical": 60,
        "sustained_seconds": 90,
        "cooldown_seconds": 120,
        "expensive_floor": 1,
        "queue_capacity": max(NUM_WORKERS, NUM_WORKERS * 5),
        "expensive_admission_threshold": 12,
        "expensive_admission_delay_seconds": 0.01,
    },
}
_throughput_policy_state: dict[str, datetime | bool | str | None] = {
    "active_since": None,
    "cooldown_until": None,
    "last_active": False,
    "last_level": "normal",
    "last_preset": "balanced",
}

# Queue for file processing
file_queue: asyncio.Queue | None = None
worker_tasks: list[asyncio.Task] = []


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
    queue_depth: int,
    telemetry_stale: bool = False,
    preset: str | None = None,
    now: datetime | None = None,
) -> dict:
    current_time = _policy_now(now)
    requested_preset, preset_cfg = _resolve_throughput_preset(preset)
    active_preset = "conservative" if telemetry_stale else requested_preset
    if telemetry_stale:
        preset_cfg = _THROUGHPUT_POLICY_PRESETS["conservative"]

    warning_threshold = int(preset_cfg["queue_warn"])
    critical_threshold = int(preset_cfg["queue_critical"])
    sustained_required = int(preset_cfg["sustained_seconds"])
    cooldown_seconds = int(preset_cfg["cooldown_seconds"])
    fail_safe_reason = "Queue telemetry unavailable; fail-safe conservative throttling active." if telemetry_stale else None

    if telemetry_stale:
        queue_pressure_level = "critical"
    elif queue_depth >= critical_threshold:
        queue_pressure_level = "critical"
    elif queue_depth >= warning_threshold:
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

    defer_expensive_admission = policy_active and queue_pressure_level in {"warning", "critical"}
    expensive_floor = max(1, int(preset_cfg["expensive_floor"]))
    expensive_admission_threshold = max(expensive_floor, int(preset_cfg["expensive_admission_threshold"]))
    expensive_admission_delay_seconds = (
        float(preset_cfg["expensive_admission_delay_seconds"]) if defer_expensive_admission else 0.0
    )

    return {
        "requested_preset": requested_preset,
        "active_preset": active_preset,
        "queue_pressure_level": queue_pressure_level,
        "policy_active": policy_active,
        "queue_depth": queue_depth,
        "warning_threshold": warning_threshold,
        "critical_threshold": critical_threshold,
        "sustained_seconds": sustained_seconds,
        "sustained_seconds_required": sustained_required,
        "cooldown_seconds": cooldown_seconds,
        "cooldown_remaining_seconds": cooldown_remaining_seconds,
        "defer_expensive_admission": defer_expensive_admission,
        "expensive_floor": expensive_floor,
        "expensive_admission_threshold": expensive_admission_threshold,
        "expensive_admission_delay_seconds": expensive_admission_delay_seconds,
        "queue_capacity": max(NUM_WORKERS, int(preset_cfg["queue_capacity"])),
        "fail_safe": telemetry_stale,
        "fail_safe_reason": fail_safe_reason,
        "queue_defaults": {
            "files-new_file": {
                "warning_threshold": warning_threshold,
                "critical_threshold": critical_threshold,
            }
        },
    }


def _is_expensive_workload(file: File) -> bool:
    path = getattr(file, "path", "")
    _, extension = os.path.splitext(path.lower())
    return extension in _EXPENSIVE_EXTENSIONS


async def worker(worker_id: int):
    """Worker task that continuously processes files from the queue"""
    logger.info(f"Worker {worker_id} started")

    assert file_queue is not None
    while True:
        try:
            # Get the next file from the queue
            file = await file_queue.get()

            try:
                logger.debug(f"Worker {worker_id} processing file", object_id=file.object_id)

                # Save file and run workflow
                await save_file_message(file)
                assert global_vars.workflow_manager is not None
                await global_vars.workflow_manager.run_workflow(file)

                logger.debug(f"Worker {worker_id} completed file", object_id=file.object_id)

            except Exception:
                logger.exception(message=f"Worker {worker_id} error processing file", object_id=file.object_id)
            finally:
                # Mark the task as done
                file_queue.task_done()

        except asyncio.CancelledError:
            logger.info(f"Worker {worker_id} cancelled")
            break
        except Exception:
            logger.exception(message=f"Worker {worker_id} unexpected error")


def start_workers():
    """Start the worker tasks"""
    global file_queue, worker_tasks

    if file_queue is not None:
        logger.warning("Workers already started")
        return

    policy_snapshot = evaluate_throughput_policy(
        queue_depth=0,
        telemetry_stale=_env_bool("FILE_ENRICHMENT_POLICY_TELEMETRY_STALE"),
    )
    queue_capacity = int(policy_snapshot["queue_capacity"])
    # Create a bounded queue that follows throughput policy queue defaults.
    file_queue = asyncio.Queue(maxsize=queue_capacity)
    worker_tasks = []

    for i in range(NUM_WORKERS):
        task = asyncio.create_task(worker(i))
        worker_tasks.append(task)

    logger.info(
        "Started file enrichment workers",
        num_workers=NUM_WORKERS,
        queue_capacity=queue_capacity,
        throughput_policy=policy_snapshot["active_preset"],
    )


async def stop_workers():
    """Stop all worker tasks"""
    global worker_tasks, file_queue

    if not worker_tasks:
        logger.warning("No workers to stop")
        return

    logger.info("Stopping workers...")

    # Cancel all worker tasks
    for task in worker_tasks:
        task.cancel()

    # Wait for all workers to finish
    await asyncio.gather(*worker_tasks, return_exceptions=True)

    worker_tasks = []
    file_queue = None

    logger.info("All workers stopped")


async def file_subscription_handler(event: CloudEvent[File]):
    """Handler for incoming file events"""
    file = event.data

    assert file_queue is not None
    try:
        queue_depth = file_queue.qsize()
        policy_snapshot = evaluate_throughput_policy(
            queue_depth=queue_depth,
            telemetry_stale=_env_bool("FILE_ENRICHMENT_POLICY_TELEMETRY_STALE"),
        )
        workload_class = "expensive" if _is_expensive_workload(file) else "baseline"

        if workload_class == "expensive" and bool(policy_snapshot["defer_expensive_admission"]):
            threshold = int(policy_snapshot["expensive_admission_threshold"])
            if queue_depth >= threshold:
                delay_seconds = float(policy_snapshot["expensive_admission_delay_seconds"])
                if delay_seconds > 0:
                    logger.info(
                        "Deferring expensive workload admission under queue pressure",
                        object_id=file.object_id,
                        queue_depth=queue_depth,
                        threshold=threshold,
                        delay_seconds=delay_seconds,
                        throughput_policy=policy_snapshot["active_preset"],
                        fail_safe=policy_snapshot["fail_safe"],
                    )
                    await asyncio.sleep(delay_seconds)

        # Try to add file to the queue
        # put() will block until a worker is available (queue has space)
        # This ensures we only accept work when there's capacity
        await file_queue.put(file)

        logger.debug(
            "File added to queue",
            object_id=file.object_id,
            queue_size=file_queue.qsize(),
            queue_pressure_level=policy_snapshot["queue_pressure_level"],
            throughput_policy=policy_snapshot["active_preset"],
            fail_safe=policy_snapshot["fail_safe"],
            workload_class=workload_class,
        )

    except Exception:
        logger.exception(message="Error adding file to queue")
        raise


async def save_file_message(file: File):
    """Save the file message to the database for recovery purposes"""
    try:
        # Only save files that are not nested (originating files)
        if file.nesting_level and file.nesting_level > 0:
            logger.debug(
                "nesting_level > 0, not saving file message",
                nesting_level=file.nesting_level,
                object_id=file.object_id,
            )
            return

        query = """
        INSERT INTO files (
            object_id, agent_id, source, project, timestamp, expiration,
            path, originating_object_id, originating_container_id, nesting_level,
            file_creation_time, file_access_time, file_modification_time
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13
        ) ON CONFLICT (object_id) DO UPDATE SET
            agent_id = EXCLUDED.agent_id,
            source = EXCLUDED.source,
            project = EXCLUDED.project,
            timestamp = EXCLUDED.timestamp,
            expiration = EXCLUDED.expiration,
            path = EXCLUDED.path,
            originating_object_id = EXCLUDED.originating_object_id,
            originating_container_id = EXCLUDED.originating_container_id,
            nesting_level = EXCLUDED.nesting_level,
            file_creation_time = EXCLUDED.file_creation_time,
            file_access_time = EXCLUDED.file_access_time,
            file_modification_time = EXCLUDED.file_modification_time,
            updated_at = CURRENT_TIMESTAMP;
        """

        assert global_vars.asyncpg_pool is not None
        async with global_vars.asyncpg_pool.acquire() as conn:
            await conn.execute(
                query,
                file.object_id,
                file.agent_id,
                file.source,
                file.project,
                file.timestamp,
                file.expiration,
                file.path,
                file.originating_object_id,
                getattr(file, "originating_container_id", None),
                file.nesting_level,
                datetime.fromisoformat(file.creation_time) if file.creation_time else None,
                datetime.fromisoformat(file.access_time) if file.access_time else None,
                datetime.fromisoformat(file.modification_time) if file.modification_time else None,
            )

        logger.debug("Successfully saved file message to database", object_id=file.object_id)

    except Exception:
        logger.exception(message="Error saving file message to database", object_id=file.object_id)
        raise
