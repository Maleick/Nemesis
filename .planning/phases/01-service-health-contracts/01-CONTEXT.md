# Phase 1: Service Health Contracts - Context

**Gathered:** 2026-02-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver deterministic startup and readiness behavior for core Nemesis services across `base`, `monitoring`, and `llm` profiles, including explicit failure/recovery signaling for workflow-critical dependencies.

</domain>

<decisions>
## Implementation Decisions

### Readiness Contract Scope
- Include `web-api`, `file-enrichment`, `document-conversion`, `alerting`, and `agents` (when llm profile enabled)
- Readiness must reflect dependency state, not only process liveness
- Profile startup must emit concise pass/fail summary for operator triage

### Failure Signaling
- Workflow stalls and dependency outages must surface explicit service status and log context
- Recovery paths should prefer actionable remediation hints over opaque errors

### Compatibility Constraints
- Keep existing compose topology and Dapr wiring intact
- Changes must be backward compatible for current operator flows

### Claude's Discretion
- Exact readiness-report data structure and formatting
- Minimal-touch refactor boundaries to avoid unnecessary churn
- Best balance between testability and implementation effort for first milestone plans

</decisions>

<specifics>
## Specific Ideas

- Prioritize startup matrix behavior that can be validated in CI and local runs
- Reuse existing health endpoints where possible; avoid introducing redundant status surfaces
- Treat llm auth-mode health visibility as part of profile readiness (not a separate concern)

</specifics>

<deferred>
## Deferred Ideas

- Deep performance benchmarking (Phase 6)
- Documentation polish and broader runbook refinement (Phase 5)
- Full cross-service smoke and contract gates (Phase 4)

</deferred>

---

*Phase: 01-service-health-contracts*
*Context gathered: 2026-02-25*
