# Project Research Summary

**Project:** Nemesis Platform Evolution
**Domain:** Offensive-security file ingestion, enrichment, and analyst triage platform
**Researched:** 2026-02-25
**Confidence:** HIGH

## Executive Summary

Nemesis already has strong brownfield foundations: a Docker-compose service topology, Dapr-backed async workflows, PostgreSQL/Hasura data access, and rich enrichment modules. The next roadmap should prioritize reliability and operational confidence over net-new feature surface area.

The recommended path is a six-phase hardening cycle: startup/readiness contracts, observability baseline, security/auth tightening, end-to-end quality gates, operator UX/runbook improvements, and extension-contract consolidation. This sequence aligns with current architecture dependencies and reduces production-style risk early.

The highest risks are topic-contract drift, profile startup fragility, secret leakage in logs, and insufficient cross-service validation. Each has clear prevention phases and measurable verification outcomes.

## Key Findings

### Recommended Stack

Keep the current stack trajectory and optimize operational rigor:
- Python/FastAPI/Dapr remain appropriate for service logic and workflow orchestration.
- PostgreSQL + Hasura + MinIO + RabbitMQ remain the core data/event substrate.
- `uv`, Ruff, Pyright, and CI workflows remain the right quality baseline.

**Core technologies:**
- Dapr workflows/pubsub for service orchestration and decoupling
- PostgreSQL + Hasura for state/query workflows and subscriptions
- MinIO for artifact storage and transform payloads

### Expected Features

**Must have (table stakes):**
- Deterministic ingestion/enrichment flow with clear status and failure handling
- Reliable operational health visibility across deployment profiles
- Security-safe auth and logging behavior in all startup/runtime paths

**Should have (competitive):**
- High-signal enrichment depth with stable module contracts
- Optional LLM triage/chatbot flows that remain trustworthy and bounded

**Defer (v2+):**
- Large-scale horizontal partitioning and multi-tenant abstractions

### Architecture Approach

Use the existing event-driven architecture but tighten contracts at integration boundaries. The most leverage comes from hardening cross-service behaviors (startup, queue contracts, observability, smoke tests) rather than replacing core components.

**Major components:**
1. Ingress + API/UI surfaces
2. Workflow processing services with Dapr sidecars
3. Shared data/event/storage infrastructure

### Critical Pitfalls

1. **Topic contract drift** — prevent with shared constants and contract checks
2. **Profile startup fragility** — prevent with explicit readiness matrix
3. **Secret leakage in logs** — prevent with redaction policy + scanning
4. **Weak end-to-end validation** — prevent with CI smoke flows
5. **Runbook drift** — prevent with release-coupled doc updates

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Service Health Contracts
**Rationale:** Startup/readiness failures block all later improvements.
**Delivers:** Profile-specific health matrix and dependency contracts.
**Addresses:** Table-stakes reliability and startup pitfalls.
**Avoids:** Startup order fragility and contract drift.

### Phase 2: Workflow Observability Baseline
**Rationale:** Observability is needed before deeper hardening decisions.
**Delivers:** Queue/workflow/object correlation and failure visibility.
**Uses:** Existing OpenTelemetry/monitoring profile foundations.
**Implements:** Cross-service signal clarity for operators.

### Phase 3: Security & Auth Hardening
**Rationale:** Security correctness should follow stable visibility.
**Delivers:** Secret-safe logging and explicit auth-mode safeguards.
**Uses:** Existing llm profile/auth pathways.

### Phase 4: End-to-End Quality Gates
**Rationale:** Once reliability/security controls are defined, enforce them.
**Delivers:** Deterministic smoke coverage for critical journeys.

### Phase 5: Operator Experience & Docs
**Rationale:** Reduce operational burden after technical hardening.
**Delivers:** Updated runbooks and clearer startup/troubleshooting flows.

### Phase 6: Extension Contracts & Performance Tuning
**Rationale:** Standardize future module growth and tune scaling bottlenecks.
**Delivers:** Extension contract guidance + bounded performance tuning.

### Phase Ordering Rationale

- Early phases reduce systemic risk (startup + observability) before expanding scope.
- Security and quality gates are most effective once baseline behavior is visible.
- Operator and extension improvements are higher leverage after core reliability is stabilized.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3:** LLM auth mode edge cases and secret-safe startup patterns across providers
- **Phase 6:** Performance bottleneck characterization under realistic ingestion load

Phases with standard patterns (skip dedicated research-phase):
- **Phase 1, 2, 4, 5:** Well-bounded improvements with strong repo-local context

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Strong alignment with existing validated architecture |
| Features | HIGH | Current capabilities and operator needs are well-documented |
| Architecture | HIGH | Existing deployment and service boundaries are clear |
| Pitfalls | HIGH | Directly supported by current codebase concerns and runtime patterns |

**Overall confidence:** HIGH

### Gaps to Address

- Validate startup/health matrix in each profile combination (`base`, `monitoring`, `llm`).
- Quantify acceptable backlog/latency thresholds for workflow operations.
- Ensure frontend critical-path smoke coverage aligns with current auth/UI behavior.

## Sources

### Primary (HIGH confidence)
- Repository artifacts: `README.md`, `compose.yaml`, `.github/workflows/*`, `docs/*`
- `.planning/codebase/*.md` generated map artifacts

### Secondary (MEDIUM confidence)
- Current ecosystem operational norms for Dapr/FastAPI/PostgreSQL service stacks

### Tertiary (LOW confidence)
- Forward-looking scaling assumptions beyond current operator footprint

---
*Research completed: 2026-02-25*
*Ready for roadmap: yes*
