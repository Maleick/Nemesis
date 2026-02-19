"""Unit tests for LLM auth mode parsing."""

from agents.auth_modes import LLMAuthMode


def test_parse_defaults_to_official_key_when_missing():
    mode, fallback_used = LLMAuthMode.parse(None)
    assert mode is LLMAuthMode.OFFICIAL_KEY
    assert fallback_used is False


def test_parse_accepts_case_and_whitespace():
    mode, fallback_used = LLMAuthMode.parse("  CoDeX_OaUtH ")
    assert mode is LLMAuthMode.CODEX_OAUTH
    assert fallback_used is False


def test_parse_invalid_value_falls_back():
    mode, fallback_used = LLMAuthMode.parse("unsupported_mode")
    assert mode is LLMAuthMode.OFFICIAL_KEY
    assert fallback_used is True
