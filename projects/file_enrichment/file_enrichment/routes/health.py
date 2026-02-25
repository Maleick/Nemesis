import file_enrichment.global_vars as global_vars
from common.health_contract import (
    build_health_response,
    dependency_failed,
    dependency_failed_from_exception,
    dependency_ok,
)
from common.logger import get_logger
from fastapi import APIRouter

router = APIRouter()
logger = get_logger(__name__)


@router.api_route("/healthz", methods=["GET", "HEAD"])
async def healthcheck():
    """Dependency-aware readiness endpoint for file enrichment service."""
    dependencies = []

    try:
        if not global_vars.asyncpg_pool:
            dependencies.append(
                dependency_failed(
                    "postgres",
                    "Database pool not initialized",
                    remediation="Verify file-enrichment startup completed and Postgres is reachable",
                    logger=logger,
                    service="file_enrichment",
                )
            )
        else:
            async with global_vars.asyncpg_pool.acquire() as connection:
                await connection.fetchval("SELECT 1")
            dependencies.append(dependency_ok("postgres"))

        if not global_vars.workflow_client or not global_vars.workflow_manager:
            dependencies.append(
                dependency_failed(
                    "workflow-runtime",
                    "Workflow runtime not initialized",
                    remediation="Check Dapr sidecar and workflow runtime initialization logs",
                    logger=logger,
                    service="file_enrichment",
                )
            )
        else:
            dependencies.append(dependency_ok("workflow-runtime"))

        if not global_vars.module_execution_order:
            dependencies.append(
                dependency_failed(
                    "enrichment-modules",
                    "No enrichment modules loaded",
                    remediation="Check enrichment module configuration and startup logs",
                    logger=logger,
                    service="file_enrichment",
                )
            )
        else:
            dependencies.append(
                dependency_ok("enrichment-modules", detail=f"{len(global_vars.module_execution_order)} modules loaded")
            )

        return build_health_response(service="file_enrichment", dependencies=dependencies)
    except Exception as e:
        dependencies.append(
            dependency_failed_from_exception(
                "health-check",
                e,
                remediation="Inspect file_enrichment health check logs",
                logger=logger,
                service="file_enrichment",
            )
        )
        return build_health_response(service="file_enrichment", dependencies=dependencies)
