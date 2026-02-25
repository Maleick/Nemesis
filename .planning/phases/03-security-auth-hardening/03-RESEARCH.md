# Phase 3 Research: Security & Auth Hardening

**Phase:** 03 Security & Auth Hardening
**Researched:** 2026-02-25
**Status:** Complete
**Requirement IDs:** SEC-01, SEC-02, SEC-03

## Objective

Define a low-risk implementation plan that hardens authentication behavior and secret safety in operator-visible startup/runtime paths without broad repo-wide refactors.

## User Constraints

- `03-CONTEXT.md` does not exist and is intentionally skipped for this pass.
- Scope for SEC-01 is locked to **core auth paths**:
  - `projects/agents/`
  - `projects/web_api/`
  - `projects/alerting/`
  - auth-adjacent `projects/file_enrichment/file_enrichment/subscriptions/noseyparker.py`
- Run mode is standard planning (no `--gaps`, no `--skip-research`, no `--skip-verify`, no `--prd`).

## Existing Baseline

### Auth-mode and status plumbing

- `projects/agents/agents/auth_provider.py` resolves auth mode (`official_key` vs `codex_oauth`) and returns secret-safe status metadata.
- `projects/agents/agents/model_manager.py` stores runtime auth health, exposes `get_auth_status()`, and is used by health/status endpoints.
- `projects/agents/agents/main.py` exposes `/agents/auth-status` and health dependency entries for `llm-auth`.
- `projects/web_api/web_api/main.py` proxies auth status via `/system/llm-auth-status` and incorporates degraded auth in `/system/health`.

### Chatbot DB credential preflight

- `projects/agents/agents/tasks/chatbot.py` validates chatbot DB credentials before starting MCP server.
- Current behavior fails fast and includes a structured context block that excludes password material.
- Existing tests already assert password non-leak behavior (`projects/agents/tests/test_chatbot_preflight.py`).

### Existing secret-safe logging primitives

- `libs/common/common/logger.py` contains recursive redaction helpers (`redact_sensitive_data`) and standardized dependency-failure logging.
- Usage is inconsistent across services; several files still log raw exception strings or payload bodies that may contain sensitive values.

## Concrete Risk Findings

1. `projects/file_enrichment/file_enrichment/subscriptions/noseyparker.py` logs raw `jwt_token` when decode/parse fails.
2. `projects/agents/agents/litellm_startup.py` logs raw upstream `response_text` and broad exception strings in token provisioning flow.
3. `projects/agents/agents/tasks/chatbot.py` and `projects/agents/agents/main.py` include logging patterns that may emit unsanitized `str(e)` from auth/preflight/startup flows.
4. `projects/alerting/alerting/main.py` contains broad `error=str(e)` logging and startup logging around alert routing configuration; this needs normalization against secret-safe standards.
5. Web API fallback paths (`/system/llm-auth-status`) can surface raw request exception text; messages should be deterministic and operator-focused.

## Test Baseline (Current)

The following pass before Phase 3 implementation and should remain green:

- `cd projects/agents && uv run pytest tests/test_chatbot_preflight.py tests/test_auth_provider_auth_json.py tests/test_auth_provider_expiry.py tests/test_model_manager_modes.py -q`
- `cd projects/web_api && uv run pytest tests/test_llm_auth_status.py -q`

## Recommended Plan Split

### Plan 03-01 (SEC-01)

Secret-safe logging hardening for scoped auth paths:

- Standardize redaction usage via shared logger helpers.
- Remove raw secret-adjacent fields (JWTs, response bodies, token values, DSN/password traces) from logs and exception contexts.
- Add regression tests proving secret literals are not emitted in auth-path errors.

### Plan 03-02 (SEC-02, SEC-03)

Auth-mode and credential-preflight determinism:

- Ensure invalid/missing auth-mode configuration yields explicit unhealthy status and remediation hints.
- Tighten chatbot preflight failure categories and user-facing errors to deterministic, non-secret forms.
- Expand status-contract tests for agents and web_api surfaces.

## Risks and Mitigations

- **Risk:** Over-redaction harms debugging utility.
  - **Mitigation:** Preserve structured context (`mode`, `source`, host/port/db) while redacting secret-bearing values only.
- **Risk:** Auth-mode contract changes could break existing dashboard assumptions.
  - **Mitigation:** Keep response keys backward-compatible and add tests around fallback payload shape.
- **Risk:** Preflight hardening could block startup unexpectedly.
  - **Mitigation:** Keep fail-fast semantics but improve diagnostics with deterministic remediation messages.

## Validation Architecture

### Automated checks per plan

1. **Agents auth and preflight suite**
- `cd projects/agents && uv run pytest tests/test_chatbot_preflight.py tests/test_auth_provider_auth_json.py tests/test_auth_provider_expiry.py tests/test_model_manager_modes.py -q`

2. **Web API auth-status and health integration**
- `cd projects/web_api && uv run pytest tests/test_llm_auth_status.py -q`

3. **New secret-safe logging tests (to be added in Plan 03-01)**
- Assert no secret literals (password/token/JWT/raw response body) appear in log records for forced error paths.

### Manual spot checks

- Trigger auth-mode misconfiguration (`LLM_AUTH_MODE` invalid/unsupported) and verify:
  - `/agents/auth-status` and `/system/llm-auth-status` return unhealthy/degraded with remediation-oriented message.
  - No secret value is present in logs.
- Trigger chatbot preflight credential failure and verify:
  - startup fails deterministically,
  - error text is actionable,
  - no password literal is emitted.

## Outputs Expected from Phase 3 Planning

- `03-01-PLAN.md` covering SEC-01 with scoped logging hardening.
- `03-02-PLAN.md` covering SEC-02 and SEC-03 with auth-mode/preflight determinism.
- Checker-validated wave/dependency graph ready for `$gsd-execute-phase 3`.

---
*Phase research complete: 2026-02-25*
