# Roadmap: Nemesis Platform Evolution

## Overview

This roadmap hardens Nemesis's existing brownfield platform before expanding feature surface. The sequence prioritizes deterministic operations (startup, observability, security, and quality gates), then improves operator workflows and extension velocity.

## Phases

- [x] **Phase 1: Service Health Contracts** - Make startup/readiness deterministic across all supported profiles (completed 2026-02-25)
- [x] **Phase 2: Workflow Observability Baseline** - Establish object-level workflow visibility and actionable monitoring (completed 2026-02-25)
- [x] **Phase 3: Security & Auth Hardening** - Eliminate secret/logging risks and tighten auth-mode safety (completed 2026-02-25)
- [x] **Phase 4: End-to-End Quality Gates** - Add CI smoke/contract validation for critical cross-service paths (completed 2026-02-25)
- [ ] **Phase 5: Operator Experience & Docs** - Align runbooks/docs with real deployment and troubleshooting workflows
- [ ] **Phase 6: Extension Contracts & Performance** - Standardize extension onboarding and tune major throughput bottlenecks

## Phase Details

### Phase 1: Service Health Contracts
**Goal**: Establish deterministic startup/readiness contracts for all key services and profiles.
**Depends on**: Nothing (first phase)
**Requirements**: [RELI-01, RELI-02, RELI-03, RELI-04]
**Success Criteria** (what must be TRUE):
  1. Every core service exposes health status that reflects real dependency readiness.
  2. Startup for `base`, `monitoring`, and `llm` profiles yields a clear pass/fail readiness summary.
  3. Workflow failure states are explicit and recoverable instead of silent stalls.
**Plans**: 3 plans

Plans:
- [x] 01-01: Define and normalize startup/readiness contract behavior across services (completed 2026-02-25)
- [x] 01-02: Implement profile-aware readiness matrix checks and service health reporting (completed 2026-02-25)
- [x] 01-03: Add workflow failure/recovery state instrumentation at service boundaries (completed 2026-02-25)

### Phase 2: Workflow Observability Baseline
**Goal**: Make queue/workflow/object lifecycle behavior easy to observe and diagnose.
**Depends on**: Phase 1
**Requirements**: [OBS-01, OBS-02, OBS-03]
**Success Criteria** (what must be TRUE):
  1. Operators can trace an object from ingestion through enrichment outcomes.
  2. Dashboards expose backlog/failure/service-health signals with useful granularity.
  3. Alert routing highlights sustained operational issues with actionable context.
**Plans**: 2 plans

Plans:
- [x] 02-01: Implement object-level workflow correlation and status signal propagation (completed 2026-02-25)
- [x] 02-02: Build/validate dashboards and alerts for queue/workflow/service health (completed 2026-02-25)

### Phase 3: Security & Auth Hardening
**Goal**: Harden auth and logging paths so credential and mode drift is visible and safe.
**Depends on**: Phase 2
**Requirements**: [SEC-01, SEC-02, SEC-03]
**Success Criteria** (what must be TRUE):
  1. No secret values are emitted by startup/runtime logs under nominal or error paths.
  2. Auth-mode misconfiguration surfaces as explicit unhealthy status with remediation hints.
  3. Chatbot/agent DB credential preflight behavior is deterministic and testable.
**Plans**: 2 plans

Plans:
- [ ] 03-01: Enforce secret-safe logging and redact sensitive startup/error outputs
- [ ] 03-02: Tighten auth-mode and chatbot credential preflight validation + status behavior

### Phase 4: End-to-End Quality Gates
**Goal**: Raise release confidence with smoke and contract validation for critical workflows.
**Depends on**: Phase 3
**Requirements**: [TEST-01, TEST-02, TEST-03, TEST-04]
**Success Criteria** (what must be TRUE):
  1. CI blocks regressions in upload->enrichment->retrieval critical path.
  2. Profile-aware smoke tests cover llm and alerting-dependent behavior.
  3. Queue/payload contract drift is caught automatically before merge.
**Plans**: 3 plans

Plans:
- [ ] 04-01: Add cross-service ingestion/enrichment/retrieval smoke automation
- [ ] 04-02: Add frontend critical-path smoke checks and CI integration
- [ ] 04-03: Add queue/topic/payload contract tests for producer-consumer boundaries

### Phase 5: Operator Experience & Docs
**Goal**: Make operational workflows clear, executable, and aligned with current runtime behavior.
**Depends on**: Phase 4
**Requirements**: [OPS-01, OPS-02]
**Success Criteria** (what must be TRUE):
  1. Runbooks accurately cover startup validation and incident triage workflows.
  2. Compose profile docs match tested commands and expected outcomes.
  3. Repeated operational confusion points are resolved in docs and status surfaces.
**Plans**: 2 plans

Plans:
- [ ] 05-01: Update/validate startup and incident runbooks against real profile behavior
- [ ] 05-02: Align operator documentation and health-summary UX with current workflows

### Phase 6: Extension Contracts & Performance
**Goal**: Improve extension velocity and performance confidence without destabilizing core behavior.
**Depends on**: Phase 5
**Requirements**: [EXT-01, EXT-02]
**Success Criteria** (what must be TRUE):
  1. New module/connector onboarding follows documented contract and verification steps.
  2. Performance tuning targets major observed bottlenecks with measurable improvement.
  3. Extension and performance guidance remains compatible with existing core architecture.
**Plans**: 2 plans

Plans:
- [ ] 06-01: Define extension contracts/checklists for enrichment modules and connectors
- [ ] 06-02: Baseline and tune key throughput bottlenecks with guardrail metrics

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Service Health Contracts | 3/3 | Complete   | 2026-02-25 |
| 2. Workflow Observability Baseline | 2/2 | Complete    | 2026-02-25 |
| 3. Security & Auth Hardening | 2/2 | Complete    | 2026-02-25 |
| 4. End-to-End Quality Gates | 3/3 | Complete    | 2026-02-25 |
| 5. Operator Experience & Docs | 0/2 | Not started | - |
| 6. Extension Contracts & Performance | 0/2 | Not started | - |
