"""Shared AI policy-context helpers with no external runtime dependencies."""

from typing import Any


def confidence_band(confidence: float) -> str:
    """Return a stable confidence band for policy/status contracts."""
    if confidence >= 0.85:
        return "high"
    if confidence >= 0.6:
        return "medium"
    return "low"


def policy_mode_for_confidence(confidence: float) -> str:
    """Map model confidence to a deterministic triage policy mode."""
    band = confidence_band(confidence)
    if band == "high":
        return "expedite"
    if band == "medium":
        return "balanced"
    return "strict_review"


def build_policy_context(confidence: float, policy_override: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build confidence-aware policy metadata with explicit override semantics."""
    override = policy_override or {}
    requested_mode = override.get("requested_mode") or override.get("mode")
    applied_mode = requested_mode or policy_mode_for_confidence(confidence)
    return {
        "policy_mode": applied_mode,
        "confidence_score": confidence,
        "confidence_band": confidence_band(confidence),
        "override": {
            "requested": requested_mode is not None,
            "requested_mode": requested_mode,
            "applied_mode": applied_mode,
            "reason": override.get("reason"),
            "source": override.get("source", "system"),
        },
    }


def risk_confidence_score(risk_level: str | None) -> float:
    """Map synthesis risk level to a deterministic confidence score band."""
    level = (risk_level or "").lower()
    if level == "high":
        return 0.9
    if level == "medium":
        return 0.75
    if level == "low":
        return 0.65
    return 0.5


def build_reporting_policy_context(risk_level: str | None, policy_override: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build policy metadata for synthesis responses, preserving explicit overrides."""
    override = policy_override or {}
    confidence = risk_confidence_score(risk_level)
    requested_mode = override.get("requested_mode") or override.get("mode")
    applied_mode = requested_mode or "balanced"
    if requested_mode is None and confidence < 0.7:
        applied_mode = "strict_review"
    return {
        "policy_mode": applied_mode,
        "confidence_score": confidence,
        "confidence_band": confidence_band(confidence),
        "override": {
            "requested": requested_mode is not None,
            "requested_mode": requested_mode,
            "applied_mode": applied_mode,
            "reason": override.get("reason"),
            "source": override.get("source", "system"),
        },
    }
