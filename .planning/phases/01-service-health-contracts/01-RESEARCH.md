# Phase 1 Research: Service Health Contracts

**Phase:** 01 Service Health Contracts
**Researched:** 2026-02-25
**Status:** Complete
**Requirement IDs:** RELI-01, RELI-02, RELI-03, RELI-04

## Objective

Identify low-risk implementation patterns for deterministic readiness reporting across core services and profile combinations without breaking current operator workflows.

## Existing Baseline

- Health endpoints already exist in multiple services but semantics differ by service.
- Startup logic currently relies on a mix of dependency checks, retries, and implicit assumptions.
- LLM profile adds additional readiness dependencies (`agents`, `litellm`, `phoenix`) that can fail independently.

## Recommended Approach

1. Define a shared readiness contract structure (status, dependency checks, remediation hints).
2. Normalize health endpoint behavior incrementally in core Python services.
3. Add profile-matrix startup validation and workflow failure-state surfacing.
4. Back changes with smoke checks and contract assertions in CI-friendly scripts.

## Key Decisions for Planning

- Preserve existing endpoint paths where possible; improve response structure first.
- Keep Dapr/compose architecture intact; avoid topology redesign in this phase.
- Ensure all health failures are actionable (which dependency, expected state, fix hint).

## Risks and Mitigations

- **Risk:** Breaking existing health consumers.
  - **Mitigation:** Add backward-compatible response fields and phased rollout.
- **Risk:** Over-coupling readiness checks to transient dependencies.
  - **Mitigation:** Distinguish hard-fail vs degraded modes explicitly.
- **Risk:** Profile-specific drift over time.
  - **Mitigation:** Add profile startup matrix checks to CI and operational scripts.

## Validation Architecture

- Unit tests for readiness model/contract helpers.
- Service-level tests for health endpoint behavior under dependency-up/down scenarios.
- Profile smoke checks for base/monitoring/llm startup matrix.

## Outputs Expected from This Phase

- Shared readiness contract helper/module
- Updated service readiness endpoints
- Profile matrix startup check script(s)
- Documentation note for operational health interpretation

---
*Phase research complete: 2026-02-25*
