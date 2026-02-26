"""Regression tests for AI policy-mode and override contract helpers."""

from agents.policy_context import build_policy_context, build_reporting_policy_context, confidence_band, policy_mode_for_confidence


def test_policy_mode_for_confidence_thresholds():
    assert policy_mode_for_confidence(0.9) == "expedite"
    assert policy_mode_for_confidence(0.7) == "balanced"
    assert policy_mode_for_confidence(0.2) == "strict_review"


def test_confidence_band_thresholds():
    assert confidence_band(0.9) == "high"
    assert confidence_band(0.7) == "medium"
    assert confidence_band(0.4) == "low"


def test_build_policy_context_defaults_to_confidence_mode():
    payload = build_policy_context(0.62)

    assert payload["policy_mode"] == "balanced"
    assert payload["confidence_score"] == 0.62
    assert payload["confidence_band"] == "medium"
    assert payload["override"]["requested"] is False
    assert payload["override"]["requested_mode"] is None
    assert payload["override"]["applied_mode"] == "balanced"


def test_build_policy_context_honors_operator_override():
    payload = build_policy_context(
        0.35,
        policy_override={
            "requested_mode": "strict_review",
            "reason": "high-risk campaign",
            "source": "operator",
        },
    )

    assert payload["policy_mode"] == "strict_review"
    assert payload["override"]["requested"] is True
    assert payload["override"]["requested_mode"] == "strict_review"
    assert payload["override"]["applied_mode"] == "strict_review"
    assert payload["override"]["reason"] == "high-risk campaign"
    assert payload["override"]["source"] == "operator"


def test_reporting_policy_context_uses_override_and_confidence_band():
    payload = build_reporting_policy_context(
        "low",
        policy_override={"mode": "strict_review", "reason": "manual escalation", "source": "operator"},
    )

    assert payload["policy_mode"] == "strict_review"
    assert payload["confidence_score"] >= 0.6
    assert payload["confidence_band"] == "medium"
    assert payload["override"]["requested"] is True
    assert payload["override"]["source"] == "operator"
