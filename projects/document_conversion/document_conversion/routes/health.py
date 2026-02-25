"""Health check routes."""

import document_conversion.global_vars as global_vars
import jpype
from common.health_contract import (
    build_health_response,
    dependency_failed,
    dependency_failed_from_exception,
    dependency_ok,
)
from common.logger import get_logger
from common.workflows.setup import wf_runtime
from fastapi import APIRouter

logger = get_logger(__name__)

router = APIRouter(tags=["health"])


@router.api_route("/healthz", methods=["GET", "HEAD"])
async def health_check():
    """Dependency-aware readiness endpoint for document conversion."""
    dependencies = []

    try:
        if not global_vars.asyncpg_pool:
            dependencies.append(
                dependency_failed(
                    "postgres",
                    "Database pool not initialized",
                    remediation="Verify document-conversion startup and Postgres connectivity",
                    logger=logger,
                    service="document_conversion",
                )
            )
        else:
            async with global_vars.asyncpg_pool.acquire() as connection:
                await connection.fetchval("SELECT 1")
            dependencies.append(dependency_ok("postgres"))

        if not jpype.isJVMStarted():
            dependencies.append(
                dependency_failed(
                    "jvm",
                    "JVM not started",
                    remediation="Check Tika/JVM initialization and document-conversion container logs",
                    logger=logger,
                    service="document_conversion",
                )
            )
        else:
            dependencies.append(dependency_ok("jvm"))

        if not wf_runtime or not global_vars.workflow_client:
            dependencies.append(
                dependency_failed(
                    "workflow-runtime",
                    "Workflow runtime not initialized",
                    remediation="Verify Dapr workflow sidecar and startup sequence",
                    logger=logger,
                    service="document_conversion",
                )
            )
        else:
            dependencies.append(dependency_ok("workflow-runtime"))

        return build_health_response(service="document_conversion", dependencies=dependencies)

    except Exception as e:
        logger.exception(message="Health check failed")
        dependencies.append(
            dependency_failed_from_exception(
                "health-check",
                e,
                remediation="Inspect document-conversion health check logs",
                logger=logger,
                service="document_conversion",
            )
        )
        return build_health_response(service="document_conversion", dependencies=dependencies)
