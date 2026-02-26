# Roadmap: Nemesis Platform Evolution

## Milestones

- [x] **v1.0 milestone** - 6 phases / 14 plans shipped 2026-02-25 ([archive](/opt/Nemesis/.planning/milestones/v1.0-ROADMAP.md))
- [ ] **v1.1 scale-ai-operations** - active milestone (phases 7-9)

## Overview

v1.1 builds on the v1.0 hardening baseline by adding measurable workflow throughput controls and AI governance contracts. The roadmap prioritizes scale safety first, then deployment/capacity reproducibility, and finally confidence/cost-aware AI operations.

## Phases

- [x] **Phase 7: Throughput Controls & Workload Policies** - Add measurable throughput targets and policy-driven throttling for expensive workloads. (completed 2026-02-26)
- [x] **Phase 8: Capacity & Multi-Node Operations** - Provide executable multi-node deployment and capacity runbooks with validation checks. (completed 2026-02-26)
- [ ] **Phase 9: AI Governance & Cost Controls** - Implement confidence-aware AI triage policy controls and budget-governed operational signals.

## Phase Details

### Phase 7: Throughput Controls & Workload Policies
**Goal**: Ensure high-volume processing remains predictable through explicit throughput targets and queue-pressure policy controls.
**Depends on**: Nothing (first phase of v1.1)
**Requirements**: [SCALE-01, SCALE-02]
**Success Criteria** (what must be TRUE):
1. Operators can measure queue-drain and throughput targets before and after tuning changes.
2. Policy controls prevent expensive enrichment classes from starving core workflow processing.
3. Throughput changes are accepted only with benchmark + queue-level evidence.
**Plans**: 0 plans (not yet planned)

### Phase 8: Capacity & Multi-Node Operations
**Goal**: Convert scale guidance into deterministic, executable deployment/capacity runbooks for multi-node operation.
**Depends on**: Phase 7
**Requirements**: [SCALE-03]
**Success Criteria** (what must be TRUE):
1. Operators can execute documented multi-node startup and validation commands without undocumented steps.
2. Capacity profile guidance is aligned with current compose/runtime behavior.
3. Runbook validation checks prevent documentation drift.
**Plans**: 0 plans (not yet planned)

### Phase 9: AI Governance & Cost Controls
**Goal**: Make AI analysis behavior transparent, operator-controllable, and budget-aware.
**Depends on**: Phase 8
**Requirements**: [AI-01, AI-02]
**Success Criteria** (what must be TRUE):
1. AI synthesis/triage outputs include confidence-aware policy context and operator override affordances.
2. AI usage/cost governance signals are visible in operational summary surfaces.
3. Governance contracts are regression-tested and fail safely when dependencies are unavailable.
**Plans**: 0 plans (not yet planned)

## Progress

**Execution Order:**
Phases execute in numeric order: 7 -> 8 -> 9

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 7. Throughput Controls & Workload Policies | 0/0 | Complete    | 2026-02-26 |
| 8. Capacity & Multi-Node Operations | 0/0 | Complete    | 2026-02-26 |
| 9. AI Governance & Cost Controls | 0/0 | Not started | - |

## Next Up

**Phase 7: Throughput Controls & Workload Policies** - define implementation approach and plan artifacts.

Use:
- `$gsd-discuss-phase 7` to gather additional constraints/context
- `$gsd-plan-phase 7` to begin formal planning
