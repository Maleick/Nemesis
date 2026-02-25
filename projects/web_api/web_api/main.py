import asyncio
import fcntl
import json
import ntpath
import os
import urllib.parse
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path as PathLib
from typing import Annotated
from urllib.parse import urlparse

import httpx
import psycopg
import requests
from common.db import get_postgres_connection_str
from common.health_contract import (
    build_health_response,
    dependency_degraded,
    dependency_failed_from_exception,
    dependency_ok,
)
from common.helpers import get_drive_from_path
from common.logger import get_logger
from common.models import Alert, BulkEnrichmentEvent, CloudEvent
from common.models import File as FileModel
from common.models2.api import (
    APIInfo,
    ErrorResponse,
    FileMetadata,
    FileWithMetadataResponse,
    YaraReloadResponse,
)
from common.models2.dpapi import DpapiCredentialRequest
from common.models2.health import ServiceReadinessResponse
from common.queues import (
    ALERTING_NEW_ALERT_TOPIC,
    ALERTING_PUBSUB,
    FILES_BULK_ENRICHMENT_TASK_TOPIC,
    FILES_NEW_FILE_TOPIC,
    FILES_PUBSUB,
    WORKFLOW_MONITOR_COMPLETED_TOPIC,
    WORKFLOW_MONITOR_PUBSUB,
)
from common.storage import StorageMinio
from dapr.aio.clients import DaprClient
from dapr.ext.fastapi import DaprApp
from fastapi import Body, FastAPI, File, Form, HTTPException, Path, Query, Request, UploadFile
from fastapi.responses import Response, StreamingResponse
from psycopg import Connection
from psycopg.rows import TupleRow
from psycopg_pool import ConnectionPool
from pydantic import ValidationError
from web_api.container_monitor import get_monitor, start_monitor, stop_monitor
from web_api.large_containers import LargeContainerProcessor
from web_api.models.requests import ChatbotRequest, CleanupRequest, EnrichmentRequest
from web_api.models.responses import (
    ContainerStatusResponse,
    ContainerSubmissionResponse,
    EnrichmentResponse,
    EnrichmentsListResponse,
    FailedWorkflowsResponse,
    LLMSynthesisResponse,
    ObjectLifecycleResponse,
    ObservabilityAlertEvaluationResponse,
    ObservabilitySummaryResponse,
    QueuesResponse,
    SingleQueueResponse,
    SourceReport,
    SourceSummary,
    SystemReport,
    WorkflowStatusResponse,
)
from web_api.pdf_generator import generate_source_report_pdf
from web_api.queue_monitor import WorkflowQueueMonitor

logger = get_logger(__name__)

# TODO: is this needed really?
VERSION = "0.1.0"
MOUNTED_CONTAINER_PATH = "/mounted-containers"
DAPR_PORT = os.getenv("DAPR_HTTP_PORT", 3500)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events"""
    lock_file = None
    monitor_started = False

    # Startup
    try:
        # Try to acquire exclusive lock for container monitoring
        # This ensures only one worker process handles container monitoring
        lock_path = "/tmp/nemesis_container_monitor.lock"
        lock_file = open(lock_path, "w")
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

        # If we got here, we acquired the lock - start the monitor
        await start_monitor()
        monitor_started = True
        logger.info("Container monitor started successfully (acquired lock)")

    except OSError:
        # Lock is held by another process
        logger.info("Container monitor already running in another worker")
        if lock_file:
            lock_file.close()
            lock_file = None
    except Exception as e:
        logger.exception(f"Error starting container monitor: {e}")
        if lock_file:
            lock_file.close()
            lock_file = None

    yield

    # Shutdown
    try:
        if monitor_started:
            await stop_monitor()
            logger.info("Container monitor stopped successfully")
        if lock_file:
            lock_file.close()
    except Exception as e:
        logger.exception(f"Error stopping container monitor: {e}")
        if lock_file:
            try:
                lock_file.close()
            except Exception:
                pass


app = FastAPI(
    title="Enrichment API",
    description="API for file enrichment services",
    version=VERSION,
    root_path="/api",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "files", "description": "File management operations"},
        {"name": "workflows", "description": "Workflow management operations"},
        {"name": "enrichments", "description": "Enrichment management operations"},
        {"name": "dpapi", "description": "DPAPI credential and masterkey operations"},
        {"name": "queues", "description": "Internal pub/sub queue operations"},
        {"name": "reports", "description": "Reporting and analytics operations"},
        {"name": "system", "description": "System and health check endpoints"},
    ],
)


# Add timeout middleware for requests
@app.middleware("http")
async def timeout_middleware(request: Request, call_next):
    try:
        # Set timeout for file uploads (10 minutes), PDF generation (5 minutes), and other requests (60 seconds)
        if request.url.path.endswith("/files") or request.url.path.endswith("/containers"):
            timeout = 600
        elif "/pdf" in request.url.path or "/synthesize" in request.url.path:
            # PDF generation and AI synthesis can take longer
            timeout = 300
        else:
            timeout = 60
        return await asyncio.wait_for(call_next(request), timeout=timeout)
    except TimeoutError:
        raise HTTPException(status_code=504, detail="Request timeout") from None


storage = StorageMinio()
DOWNLOAD_SIZE_LIMIT_MB = 500
default_expiration_days = int(os.getenv("DEFAULT_EXPIRATION_DAYS", 100))

# Initialize container processor
container_processor = LargeContainerProcessor()

# Initialize Dapr app for pub/sub
dapr_app = DaprApp(app)

# Initialize database connection pool for workflow status queries
_db_pool: ConnectionPool[Connection[TupleRow]] | None = None


def get_db_pool() -> ConnectionPool[Connection[TupleRow]]:
    global _db_pool
    if _db_pool is None:
        _db_pool = ConnectionPool(get_postgres_connection_str(), min_size=1, max_size=5)
    return _db_pool


_OBSERVABILITY_CONDITIONS = ("queue_backlog", "workflow_failures", "service_health")
_observability_signal_state: dict[str, dict[str, datetime | None]] = {
    name: {"active_since": None, "last_alert_at": None} for name in _OBSERVABILITY_CONDITIONS
}


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _reset_observability_state() -> None:
    for state in _observability_signal_state.values():
        state["active_since"] = None
        state["last_alert_at"] = None


def _env_int(*keys: str, default: int) -> int:
    for key in keys:
        raw = os.getenv(key)
        if raw is None:
            continue
        try:
            return int(raw)
        except ValueError:
            logger.warning("Invalid integer environment override", key=key, value=raw)
    return default


def _get_observability_thresholds() -> dict[str, int]:
    return {
        "queue_warn": _env_int("OBS_QUEUE_BACKLOG_WARN", "OBS_QUEUE_BACKLOG_WARNING", default=50),
        "queue_critical": _env_int("OBS_QUEUE_BACKLOG_CRITICAL", default=200),
        "workflow_warn": _env_int("OBS_WORKFLOW_FAILURE_WARN", "OBS_WORKFLOW_FAILURE_WARNING", default=5),
        "workflow_critical": _env_int("OBS_WORKFLOW_FAILURE_CRITICAL", default=20),
        "sustained_seconds": _env_int("OBS_SUSTAINED_DURATION_SECONDS", default=300),
        "cooldown_seconds": _env_int("OBS_ALERT_COOLDOWN_SECONDS", default=900),
    }


def _severity_for_threshold(value: int, warning: int, critical: int) -> str:
    if value >= critical:
        return "critical"
    if value >= warning:
        return "warning"
    return "normal"


async def send_postgres_notify(channel: str, payload: str = ""):
    """
    Send PostgreSQL NOTIFY command to a specific channel.

    Used so we can signal _all_ UVICORN workers in one or more replicas.
    """
    try:
        postgres_connection_string = get_postgres_connection_str()

        # Send NOTIFY using async connection
        async with await psycopg.AsyncConnection.connect(postgres_connection_string) as conn:
            # Use psycopg.sql for type-safe query construction
            from psycopg import sql

            notify_cmd = sql.SQL("NOTIFY {}, {}").format(sql.Identifier(channel), sql.Literal(payload))
            logger.debug(f"PostgreSQL NOTIFY: {channel} with payload: {payload}")
            await conn.execute(notify_cmd)
            logger.info(f"Sent PostgreSQL NOTIFY: {channel} with payload: {payload}")

    except Exception as e:
        logger.exception(f"Error sending PostgreSQL NOTIFY to {channel}", error=str(e))
        raise


def is_valid_uri(uri):
    try:
        result = urlparse(uri)
        # Check if scheme and netloc are present (for absolute URIs)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


#######################################
#
# file routes
#
#######################################


def normalize_path(path: str) -> str:
    """Normalize file paths to use forward slashes and remove redundant separators.

    TODO: Standardize on URIs?
    """
    if is_valid_uri(path):
        return path

    if ntpath.isabs(path):
        path = ntpath.abspath(path)
    else:
        pass

    path = path.replace("\\", "/")

    drive = get_drive_from_path(path)
    if drive is not None and len(drive) == 2 and drive[1] == ":":
        path = "/" + path

    return path


@app.post(
    "/files",
    response_model=FileWithMetadataResponse,
    tags=["files"],
    summary="Upload file with metadata",
    description="""
    Upload a file using multipart/form-data with metadata.
    Returns an object_id for the uploaded file and submission_id for the metadata submission.

    Example:
    ```
    curl -k -u n:n -F "file=@example.txt" \
         -F 'metadata={"agent_id":"agent123","project":"proj1","timestamp":"2024-01-29T12:00:00Z","expiration":"2024-02-29T12:00:00Z","path":"/tmp/example.txt"}' \
         https://nemesis:7443/api/files
    ```

    Example:
    ```
    curl -k -u n:n -F "file=@example.txt" \
         -F 'metadata={"agent_id":"agent123","project":"proj1","path":"/tmp/example.txt"}' \
         https://nemesis:7443/api/files
    ```
    """,
)
async def upload_file(
    file: Annotated[UploadFile, File(description="The file to upload")],
    metadata: Annotated[str, Form(description="JSON string containing file metadata")],
) -> FileWithMetadataResponse:
    try:
        # Parse the metadata string into FileMetadata model
        logger.debug("Metadata received", metadata=metadata)
        metadata_dict = json.loads(metadata)

        # Handle timestamp - use current UTC time if not provided
        if metadata_dict.get("timestamp") is None:
            current_utc = datetime.now(UTC)
            metadata_dict["timestamp"] = current_utc.isoformat()

        file_metadata = FileMetadata(**metadata_dict)

        logger.debug("Received file upload request")

        object_id = await asyncio.to_thread(storage.upload_uploadfile, file)
        logger.info("File uploaded to datalake", object_id=object_id)

        file_metadata.path = normalize_path(file_metadata.path)

        # Handle expiration - use timestamp + default_expiration_days if not provided
        if file_metadata.expiration is None:
            timestamp_dt = file_metadata.timestamp
            if timestamp_dt is None:
                timestamp_dt = datetime.now(UTC)

            expiration_dt = timestamp_dt + timedelta(days=default_expiration_days)
            file_metadata.expiration = expiration_dt
            logger.debug("Set default expiration", expiration=file_metadata.expiration.isoformat())

        file_model = FileModel.from_file_metadata(file_metadata, str(object_id))
        submission_id = await submit_file(file_model)

        logger.info("File metadata submitted", submission_id=str(submission_id), object_id=object_id)
        return FileWithMetadataResponse(object_id=uuid.UUID(object_id), submission_id=submission_id)

    except Exception as e:
        logger.exception(message="Error processing file upload")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get(
    "/files/{object_id}",
    tags=["files"],
    responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Download a file",
    description="Download a file by its object ID with optional raw format and custom filename",
)
async def download_file(
    object_id: str = Path(..., description="Unique identifier of the file to download"),
    raw: bool = Query(False, description="Whether to return the file in raw format"),
    name: str = Query("", description="Custom filename for the downloaded file"),
    offset: int = Query(0, ge=0, description="Byte offset to start reading from"),
    length: int = Query(0, ge=0, description="Number of bytes to read (0 = entire file)"),
):
    try:
        if not storage.check_file_exists(object_id):
            raise HTTPException(status_code=404, detail=f"File {object_id} not found")

        file_data = storage.get_object_stats(object_id)

        if not file_data:
            raise HTTPException(status_code=404, detail=f"File data for {object_id} not retrieved")

        if not file_data.size:
            raise HTTPException(status_code=404, detail=f"File data for {object_id} has no size information")

        if offset >= file_data.size:
            raise HTTPException(status_code=400, detail=f"Offset {offset} is beyond file size {file_data.size}")

        # For range requests, check the effective size instead of total file size
        is_range_request = offset > 0 or length > 0
        if is_range_request:
            effective_size = min(length, file_data.size - offset) if length > 0 else (file_data.size - offset)
        else:
            effective_size = file_data.size

        if effective_size > DOWNLOAD_SIZE_LIMIT_MB * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail=f"File too large to download directly. Maximum size is {DOWNLOAD_SIZE_LIMIT_MB}MB.",
            )

        headers = {"Content-Type": "text/plain" if raw else "application/octet-stream"}

        if raw:
            # For raw view, display inline in browser instead of downloading
            headers["Content-Disposition"] = "inline"
            headers["X-Content-Type-Options"] = "nosniff"
        elif name:
            filename = urllib.parse.quote(name)
            headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        else:
            headers["Content-Disposition"] = f'attachment; filename="{object_id}"'

        if is_range_request:
            data = await asyncio.to_thread(storage.download_bytes, object_id, offset, length)
            headers["Content-Length"] = str(len(data))
            return Response(content=data, headers=headers, media_type=headers["Content-Type"])

        return StreamingResponse(
            storage.download_stream(object_id), headers=headers, media_type=headers["Content-Type"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(message="Error downloading file")
        raise HTTPException(status_code=500, detail=str(e)) from e


#######################################
#
# container routes
#
#######################################


@app.post(
    "/containers",
    response_model=ContainerSubmissionResponse,
    tags=["files"],
    summary="Submit large container file for processing with optional filtering",
    description="""...""",
)
async def submit_container(
    file: Annotated[UploadFile, File(description="The container file to process")],
    metadata: Annotated[str, Form(description="JSON string containing file metadata with optional file_filters")],
) -> ContainerSubmissionResponse:
    try:
        # Parse the metadata string into FileMetadata model
        logger.debug("Container metadata received", metadata=metadata)
        metadata_dict = json.loads(metadata)
        file_metadata = FileMetadata(**metadata_dict)

        logger.info(
            "Received container submission request",
            filename=file.filename,
            content_type=file.content_type,
            size=file.size,
            has_filters=file_metadata.file_filters is not None,
        )

        # Log filter configuration if present
        if file_metadata.file_filters:
            logger.info(
                "Container submission includes file filters",
                pattern_type=file_metadata.file_filters.pattern_type,
                include_count=len(file_metadata.file_filters.include) if file_metadata.file_filters.include else 0,
                exclude_count=len(file_metadata.file_filters.exclude) if file_metadata.file_filters.exclude else 0,
            )

        # Generate container ID
        container_id = str(uuid.uuid4())

        # Save uploaded file to temporary location
        temp_dir = os.getenv("TEMP_CONTAINER_PATH", "/tmp/containers")
        os.makedirs(temp_dir, exist_ok=True)

        temp_file_path = os.path.join(temp_dir, f"{container_id}_{file.filename}")

        with open(temp_file_path, "wb") as temp_file:
            file.file.seek(0)
            while chunk := file.file.read(8192):  # Read in 8KB chunks
                temp_file.write(chunk)

        try:
            # Prepare file metadata for processing
            processing_metadata = file_metadata.model_dump()
            processing_metadata["filename"] = file.filename
            processing_metadata["content_type"] = file.content_type
            processing_metadata["size"] = file.size

            # Process the container from file path
            result = container_processor.process_container_from_path(
                container_id, PathLib(temp_file_path), processing_metadata
            )

            logger.info("Container extraction + file submission completed", container_id=container_id, result=result)

            response = ContainerSubmissionResponse(
                container_id=container_id,
                message="Files extracted from container and processing initiated",
                estimated_files=result["estimated_files"],
                estimated_size=result["estimated_size"],
            )

            # Add filter configuration to response if filters were used
            if file_metadata.file_filters:
                filter_config = {
                    "pattern_type": file_metadata.file_filters.pattern_type,
                    "include_patterns": file_metadata.file_filters.include or [],
                    "exclude_patterns": file_metadata.file_filters.exclude or [],
                    "filters_enabled": True,
                }
                response.filter_config = filter_config

            return response

        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except Exception as cleanup_error:
                logger.warning(f"Error cleaning up temporary file {temp_file_path}: {cleanup_error}")

    except ValidationError as e:
        logger.error("Validation error in container metadata", errors=e.errors())
        raise HTTPException(status_code=400, detail=e.errors()) from e
    except Exception as e:
        logger.exception(message="Error processing container submission")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get(
    "/containers/{container_id}/status",
    response_model=ContainerStatusResponse,
    tags=["files"],
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Get container processing status",
    description="Get the current processing status and progress of a submitted container",
)
async def get_container_status(
    container_id: str = Path(..., description="Unique identifier of the container"),
) -> ContainerStatusResponse:
    try:
        # Check database first (source of truth)
        db_status = container_processor.get_container_status(container_id)
        if not db_status:
            raise HTTPException(status_code=404, detail="Container not found")

        # Calculate progress percentages
        progress_percent_files = None
        progress_percent_bytes = None

        if db_status["workflows_total"] > 0:
            completed_workflows = db_status["workflows_completed"] + db_status["workflows_failed"]
            progress_percent_files = round((completed_workflows / db_status["workflows_total"]) * 100, 2)

        if db_status["total_bytes_extracted"] > 0:
            progress_percent_bytes = round(
                (db_status["total_bytes_processed"] / db_status["total_bytes_extracted"]) * 100, 2
            )

        # Get current_file from in-memory tracking if container is still extracting
        current_file = None
        if db_status["status"] in ["processing", "extracting"]:
            progress = container_processor.get_container_progress(container_id)
            if progress and "error" not in progress:
                current_file = progress.get("current_file")

        return ContainerStatusResponse(
            container_id=container_id,
            status=db_status["status"],
            progress_percent_files=progress_percent_files,
            progress_percent_bytes=progress_percent_bytes,
            processed_files=db_status["workflows_completed"] + db_status["workflows_failed"],
            total_files=db_status["workflows_total"],
            processed_bytes=db_status["total_bytes_processed"],
            total_bytes=db_status["total_bytes_extracted"],
            current_file=current_file,
            started_at=db_status["processing_started_at"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(message="Error getting container status")
        raise HTTPException(status_code=500, detail=str(e)) from e


#######################################
#
# workflow routes
#
#######################################


@app.get(
    "/workflows/status",
    response_model=WorkflowStatusResponse,
    tags=["workflows"],
    responses={500: {"model": ErrorResponse}},
    summary="Get workflow enrichment workflow status",
    description="Get the current status of the enrichment workflow system",
)
async def get_status():
    """Gets the current enrichment pipeline status with metrics."""
    try:
        # Get metrics and workflow information from database
        def get_db_metrics():
            pool = get_db_pool()
            with pool.connection() as conn:
                with conn.cursor() as cur:
                    # Get metrics: counts and processing times
                    cur.execute("""
                        SELECT
                            COUNT(*) FILTER (WHERE status = 'COMPLETED') as completed_count,
                            COUNT(*) FILTER (WHERE status IN ('FAILED', 'ERROR', 'TIMEOUT')) as failed_count,
                            COUNT(*) FILTER (WHERE status = 'RUNNING') as running_count,
                            AVG(runtime_seconds) FILTER (WHERE runtime_seconds IS NOT NULL) as avg_time,
                            MIN(runtime_seconds) FILTER (WHERE runtime_seconds IS NOT NULL) as min_time,
                            MAX(runtime_seconds) FILTER (WHERE runtime_seconds IS NOT NULL) as max_time,
                            COUNT(runtime_seconds) FILTER (WHERE runtime_seconds IS NOT NULL) as samples_count
                        FROM workflows
                    """)
                    metrics_row = cur.fetchone()
                    if metrics_row is None:
                        # No workflows found, return default values
                        completed_count = failed_count = running_count = samples_count = 0
                        avg_time = min_time = max_time = None
                    else:
                        completed_count, failed_count, running_count, avg_time, min_time, max_time, samples_count = (
                            metrics_row
                        )

                    # Get active workflow details from database
                    cur.execute("""
                        SELECT
                            wf_id,
                            object_id,
                            status,
                            EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - start_time)) as runtime_seconds,
                            start_time,
                            enrichments_success,
                            enrichments_failure,
                            filename
                        FROM workflows
                        WHERE status = 'RUNNING'
                    """)
                    active_workflows_db = []
                    for row in cur.fetchall():
                        wf_id, object_id, status, runtime_seconds, start_time, success_modules, failure_modules, filename = row
                        active_workflows_db.append(
                            {
                                "id": wf_id,
                                "workflow_id": wf_id,
                                "status": status,
                                "runtime_seconds": runtime_seconds,
                                "started_at": start_time,
                                "timestamp": start_time,
                                "filename": filename,
                                "object_id": str(object_id) if object_id else None,
                                "success_modules": success_modules or [],
                                "failure_modules": failure_modules or [],
                                "error": (failure_modules[-1] if failure_modules else None),
                            }
                        )

                    # Get status counts
                    cur.execute("""
                        SELECT status, COUNT(*) FROM workflows GROUP BY status
                    """)
                    status_counts = {row[0]: row[1] for row in cur.fetchall()}

                    # Calculate percentiles
                    percentiles = {}
                    if samples_count >= 5:
                        cur.execute("""
                            SELECT
                                percentile_cont(0.5) WITHIN GROUP (ORDER BY runtime_seconds) as p50,
                                percentile_cont(0.9) WITHIN GROUP (ORDER BY runtime_seconds) as p90,
                                percentile_cont(0.95) WITHIN GROUP (ORDER BY runtime_seconds) as p95,
                                percentile_cont(0.99) WITHIN GROUP (ORDER BY runtime_seconds) as p99
                            FROM workflows
                            WHERE runtime_seconds IS NOT NULL
                        """)
                        result = cur.fetchone()
                        if result:
                            p50, p90, p95, p99 = result
                            percentiles = {
                                "p50_seconds": round(float(p50), 2) if p50 is not None else None,
                                "p90_seconds": round(float(p90), 2) if p90 is not None else None,
                                "p95_seconds": round(float(p95), 2) if p95 is not None else None,
                                "p99_seconds": round(float(p99), 2) if p99 is not None else None,
                            }

                    return {
                        "metrics": {
                            "completed_count": completed_count or 0,
                            "failed_count": failed_count or 0,
                            "running_count": running_count or 0,
                            "total_processed": (completed_count or 0) + (failed_count or 0),
                            "success_rate": round(
                                (completed_count or 0) / ((completed_count or 0) + (failed_count or 0)) * 100, 2
                            )
                            if ((completed_count or 0) + (failed_count or 0)) > 0
                            else None,
                            "processing_times": {
                                "avg_seconds": round(avg_time, 2) if avg_time else None,
                                "min_seconds": round(min_time, 2) if min_time else None,
                                "max_seconds": round(max_time, 2) if max_time else None,
                                "samples_count": samples_count or 0,
                                **percentiles,
                            },
                        },
                        "status_counts": status_counts,
                        "active_workflows_db": active_workflows_db,
                    }

        # Get database metrics and status information
        db_info = await asyncio.to_thread(get_db_metrics)
        metrics = db_info["metrics"]
        status_counts = db_info["status_counts"]
        db_active_workflows = db_info["active_workflows_db"]

        # Use database count for active workflows
        db_active_count = metrics.get("running_count", 0)

        return {
            "active_workflows": db_active_count,
            "available_capacity": 0,  # This was specific to workflow manager's semaphore
            "max_concurrent": 3,  # Default value, could be made configurable
            "status_counts": status_counts,
            "active_details": db_active_workflows,
            "metrics": metrics,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    except Exception as e:
        logger.exception(message="Error getting workflow status")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get(
    "/workflows/failed",
    response_model=FailedWorkflowsResponse,
    tags=["workflows"],
    responses={500: {"model": ErrorResponse}},
    summary="Get failed workflows",
    description="Get the set of failed enrichment workflows",
)
async def get_failed():
    """Gets the set of failed enrichment workflows."""
    try:
        # Query failed workflows from database
        def get_failed_workflows_from_db():
            pool = get_db_pool()
            with pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT
                            wf_id as id,
                            object_id,
                            status,
                            runtime_seconds,
                            start_time,
                            enrichments_failure,
                            filename
                        FROM workflows
                        WHERE status IN ('FAILED', 'ERROR', 'TIMEOUT')
                        ORDER BY start_time DESC
                        LIMIT 100
                    """)
                    columns = [desc[0] for desc in cur.description] if cur.description else []
                    failed_workflows = []

                    for row in cur.fetchall():
                        workflow_dict = dict(zip(columns, row, strict=True))

                        # Convert UUID to string if present
                        if workflow_dict.get("object_id"):
                            workflow_dict["object_id"] = str(workflow_dict["object_id"])

                        # Convert datetime to string
                        if "start_time" in workflow_dict:
                            workflow_dict["timestamp"] = workflow_dict["start_time"].isoformat()
                            workflow_dict["started_at"] = workflow_dict["start_time"].isoformat()
                            del workflow_dict["start_time"]

                        workflow_dict["workflow_id"] = workflow_dict.get("id")
                        workflow_dict["success_modules"] = []

                        # Add error from failure list if available
                        if workflow_dict.get("enrichments_failure") and len(workflow_dict["enrichments_failure"]) > 0:
                            workflow_dict["error"] = workflow_dict["enrichments_failure"][-1]  # Most recent failure
                            workflow_dict["failure_modules"] = workflow_dict["enrichments_failure"]
                        else:
                            workflow_dict["failure_modules"] = []

                        failed_workflows.append(workflow_dict)

                    return failed_workflows

        failed_workflows = await asyncio.to_thread(get_failed_workflows_from_db)

        return {
            "failed_count": len(failed_workflows),
            "workflows": failed_workflows,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        logger.exception(message="Error getting failed workflow information")
        raise HTTPException(status_code=500, detail=str(e)) from e


def _fetch_object_lifecycle_payload(object_id: str) -> dict | None:
    pool = get_db_pool()
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT object_id, agent_id, source, project, path, file_name, timestamp, created_at
                FROM files_enriched
                WHERE object_id = %s
                """,
                [object_id],
            )
            enriched_row = cur.fetchone()

            if enriched_row:
                (
                    row_object_id,
                    agent_id,
                    source,
                    project,
                    path,
                    file_name,
                    ingested_at,
                    observed_at,
                ) = enriched_row
            else:
                cur.execute(
                    """
                    SELECT object_id, agent_id, source, project, path, timestamp, created_at
                    FROM files
                    WHERE object_id = %s
                    """,
                    [object_id],
                )
                file_row = cur.fetchone()
                if not file_row:
                    return None
                row_object_id, agent_id, source, project, path, ingested_at, observed_at = file_row
                file_name = None

            row_object_id = str(row_object_id)

            cur.execute(
                """
                SELECT
                    wf_id,
                    status,
                    start_time,
                    runtime_seconds,
                    filename,
                    enrichments_success,
                    enrichments_failure
                FROM workflows
                WHERE object_id = %s
                ORDER BY start_time DESC
                """,
                [object_id],
            )
            workflow_rows = cur.fetchall()

            workflow_records = []
            running_count = 0
            completed_count = 0
            failed_count = 0

            for wf_id, status, start_time, runtime_seconds, filename, success_modules, failure_modules in workflow_rows:
                if status == "RUNNING":
                    running_count += 1
                elif status == "COMPLETED":
                    completed_count += 1
                elif status in {"FAILED", "ERROR", "TIMEOUT"}:
                    failed_count += 1

                workflow_records.append(
                    {
                        "workflow_id": wf_id,
                        "status": status,
                        "started_at": start_time,
                        "runtime_seconds": runtime_seconds,
                        "filename": filename,
                        "success_modules": success_modules or [],
                        "failure_modules": failure_modules or [],
                        "error": (failure_modules[-1] if failure_modules else None),
                    }
                )

            cur.execute("SELECT COUNT(*), MAX(created_at) FROM enrichments WHERE object_id = %s", [object_id])
            enrichments_count, last_enrichment_at = cur.fetchone() or (0, None)

            cur.execute("SELECT COUNT(*), MAX(created_at) FROM transforms WHERE object_id = %s", [object_id])
            transforms_count, last_transform_at = cur.fetchone() or (0, None)

            cur.execute("SELECT COUNT(*), MAX(created_at) FROM findings WHERE object_id = %s", [object_id])
            findings_count, last_finding_at = cur.fetchone() or (0, None)

    return {
        "object_id": row_object_id,
        "ingestion": {
            "object_id": row_object_id,
            "agent_id": agent_id,
            "source": source,
            "project": project,
            "path": path,
            "file_name": file_name,
            "ingested_at": ingested_at,
            "observed_at": observed_at,
        },
        "workflows": workflow_records,
        "publication": {
            "enrichments_count": enrichments_count or 0,
            "transforms_count": transforms_count or 0,
            "findings_count": findings_count or 0,
            "last_enrichment_at": last_enrichment_at,
            "last_transform_at": last_transform_at,
            "last_finding_at": last_finding_at,
        },
        "summary": {
            "latest_status": workflow_records[0]["status"] if workflow_records else None,
            "workflow_count": len(workflow_records),
            "running_count": running_count,
            "completed_count": completed_count,
            "failed_count": failed_count,
        },
        "timestamp": _utcnow().isoformat(),
    }


async def _load_observability_inputs() -> tuple[dict, dict, dict, dict]:
    async with WorkflowQueueMonitor() as monitor:
        queue_metrics = await monitor.get_workflow_queue_metrics()

    workflow_status = await get_status()
    failed_workflows = await get_failed()
    health_payload = await healthcheck()

    return queue_metrics, workflow_status, failed_workflows, health_payload


def _build_observability_summary_payload(
    queue_metrics: dict, workflow_status: dict, failed_workflows: dict, health_payload: dict
) -> dict:
    thresholds = _get_observability_thresholds()

    queue_summary = queue_metrics.get("summary", {})
    total_queued_messages = int(queue_summary.get("total_queued_messages", 0))
    total_processing_messages = int(queue_summary.get("total_processing_messages", 0))

    queue_severity = _severity_for_threshold(
        total_queued_messages,
        warning=thresholds["queue_warn"],
        critical=thresholds["queue_critical"],
    )

    failed_count = int(failed_workflows.get("failed_count", 0))
    active_workflows = int(workflow_status.get("active_workflows", 0))
    workflow_severity = _severity_for_threshold(
        failed_count,
        warning=thresholds["workflow_warn"],
        critical=thresholds["workflow_critical"],
    )

    readiness = str(health_payload.get("readiness", health_payload.get("status", "unknown"))).lower()
    if readiness == "unhealthy":
        health_severity = "critical"
    elif readiness == "degraded":
        health_severity = "warning"
    else:
        health_severity = "normal"

    unhealthy_dependencies = []
    degraded_dependencies = []
    for dependency in health_payload.get("dependencies", []):
        dep_readiness = str(dependency.get("readiness", "")).lower()
        if dep_readiness == "unhealthy":
            unhealthy_dependencies.append(dependency.get("name", "unknown"))
        elif dep_readiness == "degraded":
            degraded_dependencies.append(dependency.get("name", "unknown"))

    return {
        "queue_backlog": {
            "severity": queue_severity,
            "total_queued_messages": total_queued_messages,
            "total_processing_messages": total_processing_messages,
            "bottleneck_queues": queue_summary.get("bottleneck_queues", []),
            "queues_without_consumers": queue_summary.get("queues_without_consumers", []),
            "warning_threshold": thresholds["queue_warn"],
            "critical_threshold": thresholds["queue_critical"],
        },
        "workflow_failures": {
            "severity": workflow_severity,
            "failed_workflows": failed_count,
            "active_workflows": active_workflows,
            "warning_threshold": thresholds["workflow_warn"],
            "critical_threshold": thresholds["workflow_critical"],
        },
        "service_health": {
            "severity": health_severity,
            "readiness": readiness,
            "unhealthy_dependencies": unhealthy_dependencies,
            "degraded_dependencies": degraded_dependencies,
        },
        "timestamp": _utcnow().isoformat(),
    }


def _build_operational_alert_message(condition: str, summary_payload: dict) -> str:
    timestamp = summary_payload.get("timestamp") or _utcnow().isoformat()
    if condition == "queue_backlog":
        queue_backlog = summary_payload["queue_backlog"]
        return (
            "Nemesis operational alert: queue backlog is sustained above threshold.\n"
            f"- Severity: {queue_backlog['severity']}\n"
            f"- Total queued messages: {queue_backlog['total_queued_messages']}\n"
            f"- Bottleneck queues: {', '.join(queue_backlog['bottleneck_queues']) or 'none'}\n"
            f"- Timestamp: {timestamp}"
        )

    if condition == "workflow_failures":
        workflow_failures = summary_payload["workflow_failures"]
        return (
            "Nemesis operational alert: workflow failures are sustained above threshold.\n"
            f"- Severity: {workflow_failures['severity']}\n"
            f"- Failed workflows: {workflow_failures['failed_workflows']}\n"
            f"- Active workflows: {workflow_failures['active_workflows']}\n"
            f"- Timestamp: {timestamp}"
        )

    service_health = summary_payload["service_health"]
    return (
        "Nemesis operational alert: unhealthy service readiness is sustained.\n"
        f"- Severity: {service_health['severity']}\n"
        f"- Readiness: {service_health['readiness']}\n"
        f"- Unhealthy dependencies: {', '.join(service_health['unhealthy_dependencies']) or 'none'}\n"
        f"- Timestamp: {timestamp}"
    )


def _alert_severity_value(severity: str) -> int:
    if severity == "critical":
        return 9
    if severity == "warning":
        return 5
    return 1


async def _publish_operational_alert(condition: str, severity: str, message: str) -> bool:
    try:
        alert = Alert(
            title=f"Nemesis Operational Alert: {condition.replace('_', ' ').title()}",
            body=message,
            service="web_api",
            category="operational_observability",
            severity=_alert_severity_value(severity),
        )
        async with DaprClient() as client:
            await client.publish_event(
                pubsub_name=ALERTING_PUBSUB,
                topic_name=ALERTING_NEW_ALERT_TOPIC,
                data=json.dumps(alert.model_dump(exclude_unset=True)),
                data_content_type="application/json",
            )
        return True
    except Exception as e:
        logger.exception("Failed to publish operational observability alert", condition=condition, error=str(e))
        return False


async def _evaluate_observability_alerts(summary_payload: dict, emit_alerts: bool = True) -> dict:
    now = _utcnow()
    thresholds = _get_observability_thresholds()
    condition_to_severity = {
        "queue_backlog": summary_payload["queue_backlog"]["severity"],
        "workflow_failures": summary_payload["workflow_failures"]["severity"],
        "service_health": summary_payload["service_health"]["severity"],
    }

    condition_states = []
    alerts_emitted = []

    for condition, severity in condition_to_severity.items():
        active = severity in {"warning", "critical"}
        state = _observability_signal_state[condition]

        if active and state["active_since"] is None:
            state["active_since"] = now
        elif not active:
            state["active_since"] = None

        sustained_seconds = int((now - state["active_since"]).total_seconds()) if state["active_since"] else 0

        last_alert_at = state["last_alert_at"]
        if last_alert_at is None:
            cooldown_remaining_seconds = 0
        else:
            elapsed = int((now - last_alert_at).total_seconds())
            cooldown_remaining_seconds = max(0, thresholds["cooldown_seconds"] - elapsed)

        eligible = (
            active
            and sustained_seconds >= thresholds["sustained_seconds"]
            and cooldown_remaining_seconds == 0
        )

        if eligible and emit_alerts:
            message = _build_operational_alert_message(condition, summary_payload)
            emitted = await _publish_operational_alert(condition=condition, severity=severity, message=message)
            alerts_emitted.append(
                {
                    "condition": condition,
                    "severity": severity,
                    "emitted": emitted,
                    "message": message,
                    "emitted_at": now.isoformat() if emitted else None,
                }
            )
            if emitted:
                state["last_alert_at"] = now

        condition_states.append(
            {
                "condition": condition,
                "active": active,
                "severity": severity,
                "sustained_seconds": sustained_seconds,
                "cooldown_remaining_seconds": cooldown_remaining_seconds,
                "eligible": eligible,
            }
        )

    return {
        "evaluated_at": now.isoformat(),
        "sustained_duration_seconds": thresholds["sustained_seconds"],
        "cooldown_seconds": thresholds["cooldown_seconds"],
        "alerts_emitted": alerts_emitted,
        "condition_states": condition_states,
        "summary": summary_payload,
    }


@app.get(
    "/workflows/lifecycle/{object_id}",
    response_model=ObjectLifecycleResponse,
    tags=["workflows"],
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Get object workflow lifecycle",
    description="Get object-level ingestion to enrichment/publication lifecycle correlation by object_id.",
)
async def get_workflow_lifecycle(
    object_id: str = Path(..., description="Object ID to correlate across ingestion and workflow lifecycle"),
):
    try:
        payload = await asyncio.to_thread(_fetch_object_lifecycle_payload, object_id)
        if payload is None:
            raise HTTPException(status_code=404, detail=f"Object {object_id} not found")
        return payload
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(message="Error getting workflow lifecycle", object_id=object_id)
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get(
    "/workflows/observability/summary",
    response_model=ObservabilitySummaryResponse,
    tags=["workflows"],
    responses={500: {"model": ErrorResponse}},
    summary="Get observability summary",
    description="Aggregate queue backlog, workflow failure, and service-health signals with threshold severity.",
)
async def get_observability_summary():
    try:
        queue_metrics, workflow_status, failed_workflows, health_payload = await _load_observability_inputs()
        return _build_observability_summary_payload(
            queue_metrics=queue_metrics,
            workflow_status=workflow_status,
            failed_workflows=failed_workflows,
            health_payload=health_payload,
        )
    except Exception as e:
        logger.exception(message="Error getting observability summary")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post(
    "/workflows/observability/alerts/evaluate",
    response_model=ObservabilityAlertEvaluationResponse,
    tags=["workflows"],
    responses={500: {"model": ErrorResponse}},
    summary="Evaluate sustained observability conditions",
    description="Evaluate sustained backlog/failure/health conditions and publish operational alerts when eligible.",
)
async def evaluate_observability_alerts(
    emit_alerts: bool = Query(True, description="Publish alerts for eligible sustained conditions"),
):
    try:
        queue_metrics, workflow_status, failed_workflows, health_payload = await _load_observability_inputs()
        summary_payload = _build_observability_summary_payload(
            queue_metrics=queue_metrics,
            workflow_status=workflow_status,
            failed_workflows=failed_workflows,
            health_payload=health_payload,
        )
        return await _evaluate_observability_alerts(summary_payload=summary_payload, emit_alerts=emit_alerts)
    except Exception as e:
        logger.exception(message="Error evaluating observability alerts")
        raise HTTPException(status_code=500, detail=str(e)) from e


#######################################
#
# enrichment routes
#
#######################################


@app.get(
    "/enrichments",
    response_model=EnrichmentsListResponse,
    tags=["enrichments"],
    responses={500: {"model": ErrorResponse}},
    summary="List enrichment modules",
    description="Get a list of all available enrichment modules",
)
async def list_enrichments():
    """List all available enrichment modules by forwarding to file-enrichment service."""
    try:
        url = f"http://localhost:{DAPR_PORT}/v1.0/invoke/file-enrichment/method/enrichments"

        response = requests.get(url)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=f"Error listing enrichments: {response.text}")

        return response.json()

    except requests.RequestException as e:
        logger.exception(message="Error connecting to enrichment service")
        raise HTTPException(status_code=503, detail="Enrichment service unavailable") from e
    except Exception as e:
        logger.exception(message="Error listing enrichment modules")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post(
    "/enrichments/{enrichment_name}",
    response_model=EnrichmentResponse,
    tags=["enrichments"],
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
    summary="Run enrichment module",
    description="Run a specific enrichment module on a file",
)
async def run_enrichment(
    enrichment_name: str = Path(..., description="Name of the enrichment module to run"),
    request: EnrichmentRequest = Body(..., description="The enrichment request containing the object ID"),
):
    """Run a specific enrichment module by forwarding the request to file-enrichment service."""
    try:
        # First verify the file exists in our storage
        if not storage.check_file_exists(request.object_id):
            raise HTTPException(status_code=404, detail=f"File {request.object_id} not found")

        # Forward the request to the enrichment service
        url = f"http://localhost:{DAPR_PORT}/v1.0/invoke/file-enrichment/method/enrichments/{enrichment_name}"

        logger.info("Forwarding enrichment request", enrichment_name=enrichment_name, object_id=request.object_id)

        response = requests.post(
            url,
            json=request.model_dump(),
            timeout=30,  # Add reasonable timeout
        )

        # Handle various response status codes
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Enrichment module '{enrichment_name}' not found")
        elif response.status_code == 503:
            raise HTTPException(status_code=503, detail="Enrichment service is unavailable or not initialized")
        elif response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code, detail=f"Error from enrichment service: {response.text}"
            )

        return response.json()

    except requests.Timeout as e:
        logger.error("Timeout connecting to enrichment service", enrichment_name=enrichment_name)
        raise HTTPException(status_code=504, detail="Request to enrichment service timed out") from e
    except requests.RequestException as e:
        logger.exception(message="Error connecting to enrichment service")
        raise HTTPException(status_code=503, detail="Enrichment service unavailable") from e
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error running enrichment", enrichment_name=enrichment_name, object_id=request.object_id)
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post(
    "/enrichments/{enrichment_name}/bulk",
    tags=["enrichments"],
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
    summary="Start bulk enrichment",
    description="Start bulk enrichment for a specific module against all files in the system using distributed processing",
)
async def run_bulk_enrichment(
    enrichment_name: str = Path(..., description="Name of the enrichment module to run"),
):
    """Start bulk enrichment for a specific module by publishing individual tasks to pub/sub."""
    raise HTTPException(status_code=500, detail="Currently disabled")

    try:
        # First verify enrichment module exists
        enrichments_url = f"http://localhost:{DAPR_PORT}/v1.0/invoke/file-enrichment/method/enrichments"

        enrichments_response = requests.get(enrichments_url, timeout=10)
        if enrichments_response.status_code != 200:
            raise HTTPException(status_code=503, detail="Enrichment service unavailable")

        available_modules = enrichments_response.json().get("modules", [])
        if enrichment_name not in available_modules:
            raise HTTPException(status_code=404, detail=f"Enrichment module '{enrichment_name}' not found")

        # Get all object_ids from files_enriched table
        def get_all_object_ids():
            pool = get_db_pool()
            with pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT object_id FROM files_enriched ORDER BY created_at")
                    return [row[0] for row in cur.fetchall()]

        object_ids = await asyncio.to_thread(get_all_object_ids)

        if not object_ids:
            return {
                "status": "success",
                "message": "No files found in files_enriched table",
                "total_files": 0,
                "enrichment_name": enrichment_name,
            }

        # Publish individual enrichment tasks to pub/sub
        async with DaprClient() as client:
            for object_id in object_ids:
                # Create strongly-typed task model
                task = BulkEnrichmentEvent(enrichment_name=enrichment_name, object_id=str(object_id))

                await client.publish_event(
                    pubsub_name=FILES_PUBSUB,
                    topic_name=FILES_BULK_ENRICHMENT_TASK_TOPIC,
                    data=json.dumps(task.model_dump()),
                    data_content_type="application/json",
                )

        logger.info("Published bulk enrichment tasks", enrichment_name=enrichment_name, total_tasks=len(object_ids))

        return {
            "status": "started",
            "message": f"Bulk enrichment started for module '{enrichment_name}' using distributed processing. {len(object_ids)} tasks published.",
            "total_files": len(object_ids),
            "enrichment_name": enrichment_name,
            "note": "Monitor progress using /workflows/status endpoint to see active single enrichment workflows",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(message="Error starting bulk enrichment", enrichment_name=enrichment_name)
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get(
    "/enrichments/{enrichment_name}/bulk/status",
    tags=["enrichments"],
    summary="Get bulk enrichment status",
    description="Bulk enrichment status tracking has been simplified",
)
async def get_bulk_enrichment_status(
    enrichment_name: str = Path(..., description="Name of the enrichment module to check status for"),
):
    """Bulk enrichment status is now tracked through the general workflow status."""
    return {
        "message": f"Bulk enrichment status for '{enrichment_name}' is not tracked individually. Use /workflows/status to see active single enrichment workflows with filename pattern 'bulk:{enrichment_name}'",
        "enrichment_name": enrichment_name,
        "status_endpoint": "/workflows/status",
    }


@app.post(
    "/enrichments/{enrichment_name}/bulk/stop",
    tags=["enrichments"],
    summary="Stop bulk enrichment",
    description="Bulk enrichment cannot be stopped once tasks are published",
)
async def stop_bulk_enrichment(
    enrichment_name: str = Path(..., description="Name of the enrichment module to stop"),
):
    """Bulk enrichment cannot be stopped once tasks are published to pub/sub."""
    return {
        "message": f"Bulk enrichment for '{enrichment_name}' cannot be stopped once tasks are published. Individual tasks will complete naturally as workers process them.",
        "enrichment_name": enrichment_name,
        "note": "The distributed nature of pub/sub means tasks are already queued across workers",
    }


#######################################
#
# dpapi routes
#
#######################################


@app.post(
    "/dpapi/credentials",
    tags=["dpapi"],
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
    summary="Submit DPAPI credential for masterkey decryption",
    description="Submit credential material to decrypt DPAPI master keys. Supports passwords, NTLM hashes, cred keys, domain backup keys, decrypted master keys, and Chromium app-bound-encryption keys.",
)
async def submit_dpapi_credential(
    request: DpapiCredentialRequest = Body(..., description="The DPAPI credential data"),
):
    """Submit DPAPI credential for masterkey decryption by forwarding to file-enrichment service."""
    try:
        # Forward the request to the enrichment service
        url = f"http://localhost:{DAPR_PORT}/v1.0/invoke/file-enrichment/method/dpapi/credentials"

        has_user_sid = hasattr(request, "user_sid")
        logger.info("Forwarding DPAPI credential request", credential_type=request.type, has_user_sid=has_user_sid)

        response = requests.post(
            url,
            json=request.model_dump(),
            timeout=30,
        )

        # Handle various response status codes
        if response.status_code == 400:
            raise HTTPException(status_code=400, detail=response.text)
        elif response.status_code == 503:
            raise HTTPException(status_code=503, detail="File enrichment service is unavailable")
        elif response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code, detail=f"Error from file enrichment service: {response.text}"
            )

        return response.json()

    except requests.Timeout as e:
        logger.error("Timeout connecting to file enrichment service for DPAPI credential")
        raise HTTPException(status_code=504, detail="Request to file enrichment service timed out") from e
    except requests.RequestException as e:
        logger.exception(message="Error connecting to file enrichment service")
        raise HTTPException(status_code=503, detail="File enrichment service unavailable") from e
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(message="Error submitting DPAPI credential", credential_type=request.type)
        raise HTTPException(status_code=500, detail=str(e)) from e


#######################################
#
# queue routes
#
#######################################


@app.get(
    "/queues",
    response_model=QueuesResponse,
    tags=["queues"],
    responses={500: {"model": ErrorResponse}},
    summary="Get queue statistics",
    description="Get comprehensive queue metrics for all workflow topics",
)
async def get_queue_metrics():
    """Get queue metrics for all workflow topics."""
    try:
        async with WorkflowQueueMonitor() as monitor:
            metrics = await monitor.get_workflow_queue_metrics()
            return metrics
    except Exception as e:
        logger.exception(message="Error getting queue metrics")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get(
    "/queues/{queue_name}",
    response_model=SingleQueueResponse,
    tags=["queues"],
    responses={500: {"model": ErrorResponse}},
    summary="Get single queue statistics",
    description="Get metrics for a specific queue topic",
)
async def get_single_queue_metrics(queue_name: str = Path(..., description="Name of the queue to get metrics for")):
    """Get metrics for a specific queue topic."""
    try:
        async with WorkflowQueueMonitor() as monitor:
            metrics = await monitor.get_single_queue_metrics(queue_name)
            return metrics
    except Exception as e:
        logger.exception(message="Error getting single queue metrics", queue_name=queue_name)
        raise HTTPException(status_code=500, detail=str(e)) from e


#######################################
#
# system routes
#
#######################################


@app.post(
    "/system/yara/reload",
    response_model=YaraReloadResponse,
    tags=["system"],
    responses={500: {"model": ErrorResponse}},
    summary="Reload Yara rules",
    description="Trigger a reload of all Yara rules in the backend across all workers/replicas",
)
async def reload_yara_rules():
    try:
        # Send PostgreSQL NOTIFY to trigger yara reload on all workers/replicas
        await send_postgres_notify("nemesis_yara_reload", "reload")
        logger.info("Sent PostgreSQL NOTIFY for Yara rules reload")
        return {"message": "Yara rules reload triggered across all workers"}
    except Exception as e:
        logger.exception(message="Error triggering Yara rules reload")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post(
    "/system/cleanup",
    tags=["system"],
    responses={500: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
    summary="Trigger database and datalake cleanup",
    description="Trigger the housekeeping service to clean up expired files and database entries, "
    "and reset the workflow manager state. Optionally specify an expiration date or 'all' to remove all files.",
)
async def trigger_cleanup(request: CleanupRequest = Body(default=None, description="Optional cleanup parameters")):
    """
    Trigger the housekeeping service to clean up expired files and reset the workflow manager
    by forwarding requests through Dapr service invocation.
    """
    try:
        # Create request payload (default to empty dict if no request body provided)
        payload = {} if request is None else request.model_dump(exclude_unset=True)
        results = {}

        # 1. Purge everything in the RabbitMQ queues
        async with WorkflowQueueMonitor() as monitor:
            results["queues"] = await monitor.purge_all_rabbitmq_queues()

        # 2. Send PostgreSQL NOTIFY to trigger workflow reset across all workers/replicas
        try:
            logger.info("Sending PostgreSQL NOTIFY for workflow reset")
            await send_postgres_notify("nemesis_workflow_reset", "reset")
            results["file_enrichment"] = {
                "status": "success",
                "message": "Workflow reset notification sent to all workers/replicas",
            }
        except Exception as reset_error:
            logger.exception("Error sending workflow reset notification", error=str(reset_error))
            results["file_enrichment"] = {
                "status": "error",
                "message": f"Error sending workflow reset notification: {str(reset_error)}",
            }

        # 3. Call housekeeping service
        housekeeping_url = f"http://localhost:{DAPR_PORT}/v1.0/invoke/housekeeping/method/trigger-cleanup"
        logger.info("Forwarding cleanup request to housekeeping service", expiration=payload.get("expiration"))

        housekeeping_response = requests.post(
            housekeeping_url,
            json=payload,
            timeout=30,  # Add reasonable timeout
        )

        # 3.5 Handle housekeeping response
        if housekeeping_response.status_code != 200:
            logger.warning(
                "Error from housekeeping service",
                status_code=housekeeping_response.status_code,
                response=housekeeping_response.text,
            )
            results["housekeeping"] = {
                "status": "error",
                "message": f"Error from housekeeping service: {housekeeping_response.text}",
            }
        else:
            results["housekeeping"] = housekeeping_response.json()

        # 4. Purge everything in the RabbitMQ queues (again)
        async with WorkflowQueueMonitor() as monitor:
            await monitor.purge_all_rabbitmq_queues()

        # Return combined results
        return {"status": "completed", "services": results, "timestamp": datetime.now(UTC).isoformat()}

    except requests.Timeout as e:
        service = getattr(e, "request", None)
        if service and hasattr(service, "url"):
            service_name = "housekeeping" if "housekeeping" in service.url else "file-enrichment"
            logger.error(f"Timeout connecting to {service_name} service")
            raise HTTPException(status_code=504, detail=f"Request to {service_name} service timed out") from e
        else:
            logger.error("Timeout connecting to services")
            raise HTTPException(status_code=504, detail="Request to services timed out") from e
    except requests.RequestException as e:
        logger.exception(message="Error connecting to services")
        raise HTTPException(status_code=503, detail="One or more services unavailable") from e
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(message="Error triggering cleanup")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get(
    "/system/health",
    response_model=ServiceReadinessResponse,
    tags=["system"],
    summary="Health check",
    description="Health check endpoint for Docker healthcheck",
)
@app.head("/healthz", include_in_schema=False)
async def healthcheck():
    dependencies = []

    try:
        pool = get_db_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        dependencies.append(dependency_ok("postgres"))
    except Exception as e:
        dependencies.append(
            dependency_failed_from_exception(
                "postgres",
                e,
                remediation="Check Postgres availability and web-api database settings",
                logger=logger,
                service="web_api",
            )
        )

    auth_status = await get_llm_auth_status()
    if auth_status.get("healthy"):
        dependencies.append(
            dependency_ok(
                "agents-llm-auth",
                detail=f"mode={auth_status.get('mode', 'unknown')}, source={auth_status.get('source', 'unknown')}",
            )
        )
    else:
        dependencies.append(
            dependency_degraded(
                "agents-llm-auth",
                auth_status.get("message", "LLM auth status unavailable"),
                remediation="Check agents service readiness and configured LLM auth mode",
                optional=True,
                logger=logger,
                service="web_api",
                context={
                    "mode": auth_status.get("mode"),
                    "source": auth_status.get("source"),
                },
            )
        )

    return build_health_response(service="web_api", dependencies=dependencies)


@app.get(
    "/system/info",
    response_model=APIInfo,
    tags=["system"],
    summary="API information",
    description="Root endpoint that shows API information",
)
async def root():
    return {
        "name": "Enrichment API",
        "version": VERSION,
    }


@app.get(
    "/system/apprise-info",
    tags=["system"],
    summary="Get Apprise alert information",
    description="Get information about configured alert channels (currently Slack only)",
)
async def get_apprise_info():
    """Forward request to alerting service to get Apprise configuration info."""
    try:
        url = f"http://localhost:{DAPR_PORT}/v1.0/invoke/alerting/method/apprise-info"

        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            logger.error(f"Error from alerting service: {response.status_code}")
            raise HTTPException(
                status_code=response.status_code, detail=f"Error from alerting service: {response.text}"
            )

        return response.json()

    except requests.Timeout as e:
        logger.error("Timeout connecting to alerting service")
        raise HTTPException(status_code=504, detail="Request to alerting service timed out") from e
    except requests.RequestException as e:
        logger.exception(message="Error connecting to alerting service")
        raise HTTPException(status_code=503, detail="Alerting service unavailable") from e
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(message="Error getting apprise info")
        raise HTTPException(status_code=500, detail=str(e)) from e


def _scan_agent_metadata():
    """
    Scan agent files to extract metadata (name, description, has_prompt).
    This function queries the agents service to get the agent information.
    """
    try:
        url = f"http://localhost:{DAPR_PORT}/v1.0/invoke/agents/method/agents/metadata"

        response = requests.get(url, timeout=5)  # Short timeout to prevent blocking
        if response.status_code == 200:
            return response.json().get("agents", [])
        else:
            logger.warning(f"Failed to get agent metadata from agents service: {response.status_code}")
            return []

    except requests.Timeout:
        logger.warning("Timeout getting agent metadata (agents service may be busy)")
        return []
    except requests.RequestException as e:
        logger.warning(f"Could not connect to agents service for metadata: {e}")
        return []


@app.get(
    "/agents",
    tags=["system"],
    summary="Get available agents",
    description="Get a list of available AI agents with their metadata and capabilities",
)
async def get_available_agents():
    """
    Get a list of available agents with their descriptions and capabilities.
    Returns agent metadata including whether they use prompts.
    """
    try:
        # Get agent metadata from the agents service
        agents = await asyncio.to_thread(_scan_agent_metadata)

        # If agents service is unavailable, return empty list
        if not agents:
            return {
                "agents": [],
                "total_count": 0,
                "timestamp": datetime.now(UTC).isoformat(),
                "note": "Agents service unavailable or no agents found",
            }

        return {"agents": agents, "total_count": len(agents), "timestamp": datetime.now(UTC).isoformat()}

    except Exception as e:
        logger.exception(message="Error getting available agents")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get(
    "/agents/spend-data",
    tags=["system"],
    summary="Get LLM spend and usage data",
    description="Get total spend and token usage statistics from LiteLLM logs",
)
async def get_agents_spend_data():
    """
    Get LLM spend and token usage data by forwarding request to agents service.
    Returns total spend, token counts, and request statistics.
    """
    try:
        url = f"http://localhost:{DAPR_PORT}/v1.0/invoke/agents/method/agents/spend-data"

        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            logger.warning(f"Failed to get spend data from agents service: {response.status_code}")
            # Return default values if service is unavailable
            return {
                "total_spend": 0.0,
                "total_tokens": 0,
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0,
                "total_requests": 0,
                "error": "Agents service unavailable",
                "timestamp": datetime.now(UTC).isoformat(),
            }

    except requests.RequestException as e:
        logger.warning(f"Could not connect to agents service for spend data: {e}")
        # Return default values if service is unavailable
        return {
            "total_spend": 0.0,
            "total_tokens": 0,
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "total_requests": 0,
            "error": f"Connection error: {str(e)}",
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        logger.exception(message="Error getting agents spend data")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post(
    "/agents/text_summarizer",
    tags=["system"],
    summary="Run text summarization",
    description="Trigger text summarization in background (non-blocking)",
)
async def run_text_summarizer(request: dict = Body(..., description="Request containing object_id")):
    """Trigger text summarization in agents service (returns immediately)."""
    try:
        url = f"http://localhost:{DAPR_PORT}/v1.0/invoke/agents/method/agents/text_summarizer"

        response = requests.post(url, json=request, timeout=10)  # Short timeout since it returns immediately
        if response.status_code == 200:
            return response.json()
        else:
            logger.warning(f"Failed to start text summarizer: {response.status_code}")
            raise HTTPException(status_code=response.status_code, detail=f"Error from agents service: {response.text}")

    except requests.Timeout as e:
        logger.error("Timeout starting text summarizer")
        raise HTTPException(status_code=504, detail="Request to agents service timed out") from e
    except requests.RequestException as e:
        logger.exception(message="Error connecting to agents service")
        raise HTTPException(status_code=503, detail="Agents service unavailable") from e
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(message="Error starting text summarizer")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post(
    "/agents/llm_credential_analysis",
    tags=["system"],
    summary="Run credential analysis",
    description="Trigger credential analysis in background (non-blocking)",
)
async def run_llm_credential_analysis(request: dict = Body(..., description="Request containing object_id")):
    """Trigger credential analysis in agents service (returns immediately)."""
    try:
        url = f"http://localhost:{DAPR_PORT}/v1.0/invoke/agents/method/agents/llm_credential_analysis"

        response = requests.post(url, json=request, timeout=10)  # Short timeout since it returns immediately
        if response.status_code == 200:
            return response.json()
        else:
            logger.warning(f"Failed to start credential analysis: {response.status_code}")
            raise HTTPException(status_code=response.status_code, detail=f"Error from agents service: {response.text}")

    except requests.Timeout as e:
        logger.error("Timeout starting credential analysis")
        raise HTTPException(status_code=504, detail="Request to agents service timed out") from e
    except requests.RequestException as e:
        logger.exception(message="Error connecting to agents service")
        raise HTTPException(status_code=503, detail="Agents service unavailable") from e
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(message="Error starting credential analysis")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post(
    "/agents/dotnet_analysis",
    tags=["system"],
    summary="Run .NET assembly analysis",
    description="Trigger .NET assembly analysis in background (non-blocking)",
)
async def run_dotnet_analysis(request: dict = Body(..., description="Request containing object_id")):
    """Trigger .NET assembly analysis in agents service (returns immediately)."""
    try:
        url = f"http://localhost:{DAPR_PORT}/v1.0/invoke/agents/method/agents/dotnet_analysis"
        response = requests.post(url, json=request, timeout=10)  # Short timeout since it returns immediately
        if response.status_code == 200:
            return response.json()
        else:
            logger.warning(f"Failed to start .NET analysis: {response.status_code}")
            raise HTTPException(status_code=response.status_code, detail=f"Error from agents service: {response.text}")
    except requests.Timeout as e:
        logger.error("Timeout starting .NET analysis")
        raise HTTPException(status_code=504, detail="Request to agents service timed out") from e
    except requests.RequestException as e:
        logger.exception(message="Error connecting to agents service")
        raise HTTPException(status_code=503, detail="Agents service unavailable") from e
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(message="Error starting .NET analysis")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post(
    "/agents/translate",
    tags=["system"],
    summary="Run text translation",
    description="Trigger text translation in background (non-blocking)",
)
async def run_translation(
    request: dict = Body(..., description="Request containing object_id and optional target_language"),
):
    """Trigger text translation in agents service (returns immediately)."""
    try:
        url = f"http://localhost:{DAPR_PORT}/v1.0/invoke/agents/method/agents/translate"
        response = requests.post(url, json=request, timeout=10)  # Short timeout since it returns immediately
        if response.status_code == 200:
            return response.json()
        else:
            logger.warning(f"Failed to start translation: {response.status_code}")
            raise HTTPException(status_code=response.status_code, detail=f"Error from agents service: {response.text}")
    except requests.Timeout as e:
        logger.error("Timeout starting translation")
        raise HTTPException(status_code=504, detail="Request to agents service timed out") from e
    except requests.RequestException as e:
        logger.exception(message="Error connecting to agents service")
        raise HTTPException(status_code=503, detail="Agents service unavailable") from e
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(message="Error starting translation")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post(
    "/chatbot/stream",
    tags=["chatbot"],
    summary="Stream chatbot responses",
    description="Stream interactive chatbot responses for querying Nemesis data",
)
async def chatbot_stream(
    request: ChatbotRequest = Body(..., description="Chatbot request with message and conversation history"),
):
    """
    Stream chatbot responses via Dapr to agents service.
    Uses HTTP streaming to provide real-time token-by-token responses.
    """
    try:
        url = f"http://localhost:{DAPR_PORT}/v1.0/invoke/agents/method/agents/chatbot/stream"

        logger.debug("Proxying chatbot request to agents service", message_length=len(request.message))

        async def stream_proxy():
            """Generator function that streams chunks from agents service."""
            try:
                async with httpx.AsyncClient() as client:
                    async with client.stream(
                        "POST",
                        url,
                        json=request.model_dump(),
                        timeout=120.0,
                    ) as response:
                        response.raise_for_status()
                        async for chunk in response.aiter_bytes():
                            if chunk:
                                yield chunk
            except httpx.HTTPStatusError as e:
                logger.error("HTTP error from agents service", status_code=e.response.status_code)
                error_msg = f"\n\n[Error: Agents service returned {e.response.status_code}]"
                yield error_msg.encode()
            except httpx.TimeoutException:
                logger.error("Timeout streaming from agents service")
                yield b"\n\n[Error: Request timeout]"
            except Exception as e:
                logger.exception("Error in stream proxy")
                error_msg = f"\n\n[Error: {str(e)}]"
                yield error_msg.encode()

        return StreamingResponse(
            stream_proxy(),
            media_type="text/plain",
        )

    except Exception as e:
        logger.exception(message="Error initiating chatbot stream")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get(
    "/system/available-services",
    tags=["system"],
    summary="Get available services",
    description="Query Traefik to determine which optional services are currently available",
)
async def get_available_services():
    """
    Query Traefik's API to determine which services are available.
    Returns a list of service paths that are currently routed by Traefik.
    """
    try:
        # Query Traefik's internal API
        traefik_api_url = "http://traefik:8080/api/http/routers"

        try:
            response = requests.get(traefik_api_url, timeout=5)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.warning(f"Failed to query Traefik API: {e}")
            # Return all services if we can't determine what's available
            return {
                "available": True,
                "services": ["/grafana", "/jaeger", "/prometheus", "/jupyter", "/llm"],
                "source": "fallback",
            }

        routers = response.json()

        # Extract service paths from router rules
        available_services = []
        service_mapping = {
            "grafana": "/grafana",
            "jaeger": "/jaeger",
            "prometheus": "/prometheus",
            "jupyter": "/jupyter",
            "litellm": "/llm",
            "phoenix": "/phoenix",
        }

        for router in routers:
            router_name = router.get("name", "").lower()
            # Check if this router matches one of our optional services
            for service_key, service_path in service_mapping.items():
                if service_key in router_name and router.get("status") == "enabled":
                    if service_path not in available_services:
                        available_services.append(service_path)

        logger.info(f"Available services detected: {available_services}")

        return {"available": True, "services": available_services, "source": "traefik"}

    except Exception as e:
        logger.exception(f"Error getting available services: {e}")
        # On error, return all services to avoid breaking the UI
        return {
            "available": True,
            "services": ["/grafana", "/jaeger", "/prometheus", "/jupyter", "/llm"],
            "source": "error_fallback",
        }


@app.get(
    "/system/llm-auth-status",
    tags=["system"],
    summary="Get LLM authentication status",
    description="Return secret-safe runtime LLM authentication mode and health metadata",
)
async def get_llm_auth_status():
    default_mode = os.getenv("LLM_AUTH_MODE", "official_key")
    fallback_payload = {
        "mode": default_mode,
        "healthy": False,
        "available": False,
        "source": "web-api-fallback",
        "message": "Agents service unavailable",
        "model_name": None,
        "base_url": None,
        "expires_at": None,
        "expires_in_seconds": None,
    }

    try:
        url = f"http://localhost:{DAPR_PORT}/v1.0/invoke/agents/method/agents/auth-status"
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            logger.warning("Unexpected status from agents auth endpoint", status_code=response.status_code)
            return {
                **fallback_payload,
                "message": f"Agents auth endpoint returned {response.status_code}",
            }

        payload = response.json()
        if not isinstance(payload, dict):
            logger.warning("Unexpected payload type from agents auth endpoint", payload_type=type(payload).__name__)
            return {
                **fallback_payload,
                "message": "Agents auth endpoint returned non-object payload",
            }

        payload.setdefault("mode", default_mode)
        payload.setdefault("source", "agents")
        return payload
    except requests.Timeout:
        logger.warning("Timeout retrieving LLM auth status from agents service")
        return {
            **fallback_payload,
            "message": "Timeout retrieving LLM auth status from agents service",
        }
    except requests.RequestException as e:
        logger.warning("Failed retrieving LLM auth status from agents service", error=str(e))
        return {
            **fallback_payload,
            "message": "Failed retrieving LLM auth status from agents service",
        }
    except Exception as e:
        logger.exception("Unexpected error retrieving LLM auth status", error=str(e))
        return {
            **fallback_payload,
            "message": "Unexpected error retrieving LLM auth status",
        }


@app.get(
    "/system/container-monitor/status",
    tags=["system"],
    summary="Container monitor status",
    description="Get the status of the container file monitor",
)
async def get_container_monitor_status():
    """Get container monitor status information"""
    try:
        monitor = get_monitor()
        status = monitor.get_status()
        return status
    except Exception as e:
        logger.exception(f"Error getting container monitor status: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


async def submit_file(file_data: FileModel) -> uuid.UUID:
    """
    Internal function to handle metadata submission.
    Returns a submission ID.
    """
    try:
        if not storage.check_file_exists(file_data.object_id):
            logger.error("File doesn't exist", object_id=file_data.object_id)
            raise HTTPException(status_code=400, detail=f"File {file_data.object_id} doesn't exist")

        submission_id = uuid.uuid4()

        async with DaprClient() as client:
            data = file_data.model_dump(
                exclude_unset=True,
                mode="json",
            )
            await client.publish_event(
                pubsub_name=FILES_PUBSUB,
                topic_name=FILES_NEW_FILE_TOPIC,
                data=json.dumps(data),
                data_content_type="application/json",
            )
            logger.debug(
                "Published file metadata for enrichment", object_id=file_data.object_id, submission_id=submission_id
            )

        return submission_id

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(message="Error submitting file metadata")
        raise HTTPException(status_code=500, detail=str(e)) from e


@dapr_app.subscribe(pubsub=WORKFLOW_MONITOR_PUBSUB, topic=WORKFLOW_MONITOR_COMPLETED_TOPIC)
async def process_workflow_completion(event: CloudEvent):
    """Handler for workflow completion events to update container processing progress"""
    try:
        data = event.data
        object_id = data.get("object_id")
        originating_container_id = data.get("originating_container_id")
        completed = data.get("completed", False)
        file_size = data.get("file_size", 0)

        logger.debug(
            f"workflow-completed event received, object_id={object_id}, originating_container_id={originating_container_id}, completed={completed}"
        )

        if not object_id or not originating_container_id:
            logger.warning("Workflow completion event missing required fields", data=data)
            return

        # Update container processing progress
        all_complete = container_processor.update_container_workflow_progress(
            originating_container_id, file_size=file_size, increment_completed=completed, increment_failed=not completed
        )

        if all_complete:
            # Clean up in-memory progress tracking
            container_processor.progress_tracker.cleanup(originating_container_id)

            logger.info(
                "Container processing completed", container_id=originating_container_id, final_object_id=object_id
            )

    except Exception:
        logger.exception(message="Error processing workflow completion event", cloud_event=event)


#######################################
#
# reporting routes
#
#######################################


@app.get(
    "/reports/sources",
    tags=["reports"],
    summary="List all sources",
    description="Get a list of all sources with summary statistics",
    response_model=list[SourceSummary],
)
async def list_sources(
    project: str | None = Query(None, description="Filter by project name"),
    start_date: datetime | None = Query(None, description="Filter by start date"),
    end_date: datetime | None = Query(None, description="Filter by end date"),
):
    """Get list of all sources with summary statistics."""
    try:
        from web_api.reporting_routes import get_sources_list

        sources = await asyncio.to_thread(get_sources_list, get_db_pool(), project, start_date, end_date)
        return sources

    except Exception as e:
        logger.exception(message="Error listing sources")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get(
    "/reports/source",
    tags=["reports"],
    summary="Get source report",
    description="Get detailed report for a specific source. Use query parameter to support sources with special characters (e.g., URLs)",
    response_model=SourceReport,
)
async def get_source_report(
    source: str = Query(..., description="Source name (supports URLs and special characters, case-insensitive)"),
    start_date: datetime | None = Query(None, description="Filter by start date"),
    end_date: datetime | None = Query(None, description="Filter by end date"),
):
    """
    Get detailed report for a specific source.

    The source parameter is a query parameter to handle special characters like:
    - URLs: http://www.site.com
    - Host URIs: host://BLAH
    - Any other source identifier with special chars
    """
    try:
        from web_api.reporting_routes import get_source_report_data

        report = await asyncio.to_thread(get_source_report_data, get_db_pool(), source, start_date, end_date)
        return report

    except Exception as e:
        logger.exception(message="Error generating source report", source=source)
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get(
    "/reports/system",
    tags=["reports"],
    summary="Get system-wide report",
    description="Get system-wide statistics and findings across all sources",
    response_model=SystemReport,
)
async def get_system_report(
    start_date: datetime | None = Query(None, description="Filter by start date"),
    end_date: datetime | None = Query(None, description="Filter by end date"),
    project: str | None = Query(None, description="Filter by project name"),
):
    """Get system-wide statistics and findings."""
    try:
        from web_api.reporting_routes import get_system_report_data

        report = await asyncio.to_thread(get_system_report_data, get_db_pool(), start_date, end_date, project)
        return report

    except Exception as e:
        logger.exception(message="Error generating system report")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post(
    "/reports/source/synthesize",
    tags=["reports"],
    summary="Generate LLM synthesis for source report",
    description="Generate AI-based risk assessment synthesis for a specific source. NOT CACHED - regenerated each time.",
    response_model=LLMSynthesisResponse,
)
async def synthesize_source_report(
    source: str = Query(..., description="Source name (supports URLs and special characters, case-insensitive)"),
    include_findings_details: bool = Query(True, description="Include detailed findings in the analysis"),
    max_tokens: int = Query(150000, description="Maximum tokens for LLM analysis"),
):
    """
    Generate LLM-based risk assessment for a source.

    WARNING: This endpoint regenerates the report each time (NOT CACHED).
    Token limit: 150k tokens maximum.
    """
    try:
        # First get the source report data
        from web_api.reporting_routes import get_source_report_data

        report = await asyncio.to_thread(get_source_report_data, get_db_pool(), source)

        # Convert report to dict for passing to agent (mode='json' handles datetime serialization)
        report_data = report.model_dump(mode="json")

        # Call agents service via Dapr
        url = f"http://localhost:{DAPR_PORT}/v1.0/invoke/agents/method/agents/report_generator"
        request_data = {
            "report_data": report_data,
            "report_type": "source",
            "source_name": source,
            "max_tokens": max_tokens,
        }

        response = requests.post(url, json=request_data, timeout=120)

        if response.status_code != 200:
            logger.error("Error calling agents service", status_code=response.status_code, response=response.text)
            raise HTTPException(status_code=503, detail="Agents service unavailable")

        result = response.json()

        if not result.get("success"):
            error_msg = result.get("error", "Unknown error")
            logger.error("Report synthesis failed", error=error_msg)
            return LLMSynthesisResponse(
                success=False,
                error=error_msg,
                report_markdown=None,
                risk_level=None,
            )

        # Build full markdown report
        full_markdown = f"""# Risk Assessment Report: {source}

{result.get("full_report_markdown", "")}
"""

        return LLMSynthesisResponse(
            success=True,
            report_markdown=full_markdown,
            risk_level=result.get("risk_level"),
            key_findings=result.get("critical_findings", []),
            recommendations=[],  # Not providing recommendations as per requirements
            token_usage=result.get("token_usage"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(message="Error generating source synthesis", source=source)
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post(
    "/reports/system/synthesize",
    tags=["reports"],
    summary="Generate LLM synthesis for system report",
    description="Generate AI-based risk assessment synthesis for the entire system. NOT CACHED - regenerated each time.",
    response_model=LLMSynthesisResponse,
)
async def synthesize_system_report(
    max_tokens: int = Query(150000, description="Maximum tokens for LLM analysis"),
    start_date: datetime | None = Query(None, description="Filter by start date"),
    end_date: datetime | None = Query(None, description="Filter by end date"),
    project: str | None = Query(None, description="Filter by project name"),
):
    """
    Generate LLM-based system-wide risk assessment.

    WARNING: This endpoint regenerates the report each time (NOT CACHED).
    Token limit: 150k tokens maximum.
    """
    try:
        # First get the system report data
        from web_api.reporting_routes import get_system_report_data

        report = await asyncio.to_thread(get_system_report_data, get_db_pool(), start_date, end_date, project)

        # Convert report to dict for passing to agent (mode='json' handles datetime serialization)
        report_data = report.model_dump(mode="json")

        # Call agents service via Dapr
        url = f"http://localhost:{DAPR_PORT}/v1.0/invoke/agents/method/agents/report_generator"
        request_data = {
            "report_data": report_data,
            "report_type": "system",
            "source_name": "System-Wide",
            "max_tokens": max_tokens,
        }

        response = requests.post(url, json=request_data, timeout=120)

        if response.status_code != 200:
            logger.error("Error calling agents service", status_code=response.status_code, response=response.text)
            raise HTTPException(status_code=503, detail="Agents service unavailable")

        result = response.json()

        if not result.get("success"):
            error_msg = result.get("error", "Unknown error")
            logger.error("Report synthesis failed", error=error_msg)
            return LLMSynthesisResponse(
                success=False,
                error=error_msg,
                report_markdown=None,
                risk_level=None,
            )

        # Build full markdown report
        full_markdown = f"""# System-Wide Risk Assessment Report

{result.get("full_report_markdown", "")}
"""

        return LLMSynthesisResponse(
            success=True,
            report_markdown=full_markdown,
            risk_level=result.get("risk_level"),
            key_findings=result.get("critical_findings", []),
            recommendations=[],  # Not providing recommendations as per requirements
            token_usage=result.get("token_usage"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(message="Error generating system synthesis")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post(
    "/reports/source/pdf",
    tags=["reports"],
    summary="Download source report as PDF",
    description="Generate and download a PDF report for a specific source. POST allows including pre-generated AI synthesis.",
    response_class=Response,
)
async def download_source_report_pdf(
    source: str = Query(..., description="Source name (supports URLs and special characters, case-insensitive)"),
    start_date: datetime | None = Query(None, description="Filter by start date"),
    end_date: datetime | None = Query(None, description="Filter by end date"),
    ai_synthesis: dict | None = Body(None, description="Optional pre-generated AI synthesis to include in PDF"),
):
    """
    Generate and download a PDF report for a specific source.

    Args:
        source: Source name to generate report for
        start_date: Optional start date filter
        end_date: Optional end date filter
        ai_synthesis: Optional pre-generated AI synthesis to include

    Returns:
        PDF file download
    """
    try:
        # Get the source report data
        from web_api.reporting_routes import get_source_report_data

        report = await asyncio.to_thread(get_source_report_data, get_db_pool(), source, start_date, end_date)

        # Convert report to dict for PDF generation
        report_data = report.model_dump()

        # Debug logging
        logger.debug(f"Received ai_synthesis: {ai_synthesis}")

        # Add AI synthesis to report data if provided
        # The body comes as {"ai_synthesis": {...}}, so extract the inner dict
        if ai_synthesis and "ai_synthesis" in ai_synthesis:
            actual_synthesis = ai_synthesis["ai_synthesis"]
            logger.debug(
                f"Adding ai_synthesis to report_data: risk_level={actual_synthesis.get('risk_level')}, markdown length={len(actual_synthesis.get('report_markdown', ''))}"
            )
            report_data["ai_synthesis"] = actual_synthesis
        elif ai_synthesis:
            # Fallback if it's already the right structure
            logger.debug(
                f"Adding ai_synthesis to report_data (direct): risk_level={ai_synthesis.get('risk_level')}, markdown length={len(ai_synthesis.get('report_markdown', ''))}"
            )
            report_data["ai_synthesis"] = ai_synthesis

        pdf_bytes = await asyncio.to_thread(generate_source_report_pdf, report_data)

        # Create safe filename from source name
        safe_source = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in source)
        filename = f"nemesis_source_report_{safe_source}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.pdf"

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(message="Error generating source PDF", source=source)
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}") from e


@app.get(
    "/reports/system/pdf",
    tags=["reports"],
    summary="Download system-wide report as PDF",
    description="Generate and download a PDF report for the entire system",
    response_class=Response,
)
async def download_system_report_pdf(
    start_date: datetime | None = Query(None, description="Filter by start date"),
    end_date: datetime | None = Query(None, description="Filter by end date"),
    project: str | None = Query(None, description="Filter by project name"),
):
    """
    Generate and download a PDF report for the entire system.

    Args:
        start_date: Optional start date filter
        end_date: Optional end date filter
        project: Optional project filter

    Returns:
        PDF file download
    """
    try:
        # Get the system report data
        from web_api.reporting_routes import get_system_report_data

        report = await asyncio.to_thread(get_system_report_data, get_db_pool(), start_date, end_date, project)

        # Convert report to dict for PDF generation
        report_data = report.model_dump()

        # Generate PDF
        from web_api.pdf_generator import generate_system_report_pdf

        pdf_bytes = await asyncio.to_thread(generate_system_report_pdf, report_data)

        # Create filename with timestamp
        filename = f"nemesis_system_report_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.pdf"

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(message="Error generating system PDF")
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}") from e
