"""Shared service readiness models."""

from enum import StrEnum

from pydantic import BaseModel, Field


class ReadinessLevel(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class DependencyReadiness(BaseModel):
    """Dependency-level readiness details for operators and automation."""

    name: str = Field(description="Dependency name")
    readiness: ReadinessLevel = Field(description="Dependency readiness level")
    detail: str | None = Field(default=None, description="Dependency status detail")
    remediation: str | None = Field(default=None, description="Suggested remediation for failures")
    optional: bool = Field(default=False, description="Optional dependency marker")


class ServiceReadinessResponse(BaseModel):
    """Contract response used by service readiness endpoints."""

    service: str = Field(description="Service name")
    status: str = Field(description="Legacy liveness status used by existing consumers")
    readiness: ReadinessLevel = Field(description="Dependency-aware readiness level")
    dependencies: list[DependencyReadiness] = Field(default_factory=list, description="Dependency readiness details")
    summary: str | None = Field(default=None, description="Optional summary message")
