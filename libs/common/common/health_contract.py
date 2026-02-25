"""Shared helpers for dependency-aware readiness contracts."""

from collections.abc import Iterable, Mapping
from typing import Any

import structlog

from common.logger import log_dependency_failure
from common.models2.health import DependencyReadiness, ReadinessLevel, ServiceReadinessResponse


def dependency_ok(name: str, detail: str | None = None, *, optional: bool = False) -> DependencyReadiness:
    return DependencyReadiness(name=name, readiness=ReadinessLevel.HEALTHY, detail=detail, optional=optional)


def dependency_degraded(
    name: str,
    detail: str,
    remediation: str | None = None,
    *,
    optional: bool = True,
    logger: structlog.stdlib.BoundLogger | None = None,
    service: str | None = None,
    context: Mapping[str, Any] | None = None,
) -> DependencyReadiness:
    if logger and service:
        log_dependency_failure(
            logger,
            service=service,
            dependency=name,
            detail=detail,
            remediation=remediation,
            readiness=ReadinessLevel.DEGRADED.value,
            context=context,
        )
    return DependencyReadiness(
        name=name,
        readiness=ReadinessLevel.DEGRADED,
        detail=detail,
        remediation=remediation,
        optional=optional,
    )


def dependency_failed(
    name: str,
    detail: str,
    remediation: str | None = None,
    *,
    optional: bool = False,
    logger: structlog.stdlib.BoundLogger | None = None,
    service: str | None = None,
    context: Mapping[str, Any] | None = None,
) -> DependencyReadiness:
    if logger and service:
        log_dependency_failure(
            logger,
            service=service,
            dependency=name,
            detail=detail,
            remediation=remediation,
            readiness=ReadinessLevel.UNHEALTHY.value,
            context=context,
        )
    return DependencyReadiness(
        name=name,
        readiness=ReadinessLevel.UNHEALTHY,
        detail=detail,
        remediation=remediation,
        optional=optional,
    )


def compute_readiness(dependencies: Iterable[DependencyReadiness]) -> ReadinessLevel:
    dependency_list = list(dependencies)

    has_required_failure = any(d.readiness == ReadinessLevel.UNHEALTHY and not d.optional for d in dependency_list)
    has_any_issue = any(d.readiness != ReadinessLevel.HEALTHY for d in dependency_list)

    if has_required_failure:
        return ReadinessLevel.UNHEALTHY
    if has_any_issue:
        return ReadinessLevel.DEGRADED
    return ReadinessLevel.HEALTHY


def build_health_response(
    *,
    service: str,
    dependencies: Iterable[DependencyReadiness] | None = None,
    summary: str | None = None,
    include_details: bool = True,
) -> dict[str, Any]:
    """Build a contract response while preserving the legacy status field."""
    dependency_list = list(dependencies or [])
    readiness = compute_readiness(dependency_list)
    legacy_status = "unhealthy" if readiness == ReadinessLevel.UNHEALTHY else "healthy"

    if not include_details:
        return {"status": legacy_status}

    response = ServiceReadinessResponse(
        service=service,
        status=legacy_status,
        readiness=readiness,
        dependencies=dependency_list,
        summary=summary,
    )
    return response.model_dump(exclude_none=True)
