# Nemesis Platform Evolution

## Current State

- **Shipped milestone:** `v1.0` on 2026-02-25
- **Delivery footprint:** 6 phases, 14 plans, 42 tasks
- **Historical records:** `.planning/milestones/v1.0-ROADMAP.md`, `.planning/milestones/v1.0-REQUIREMENTS.md`, `.planning/MILESTONES.md`, `.planning/v1.0-MILESTONE-AUDIT.md`

## Current Milestone: v1.1 Scale & AI Operations

**Goal:** Improve high-volume workflow throughput and AI analysis trust/cost controls without breaking current operator workflows.

**Target features:**
- Policy-driven throughput controls for expensive enrichment classes and queue pressure.
- Deployment/capacity guidance for multi-node scale beyond current single-host defaults.
- Confidence-aware AI triage modes with explicit operator override controls.
- AI usage/cost observability tied to runtime budgets and health diagnostics.

## What This Is

Nemesis is an open-source, Docker-first offensive security data processing platform that ingests files from collection sources, enriches them through asynchronous pipelines, and exposes analyst workflows through API/UI surfaces. It is built as a polyglot service stack centered on Python services, Dapr pub/sub/workflows, PostgreSQL, MinIO, and optional LLM-assisted triage/chatbot capabilities.

## Core Value

Turn collected offensive-operations artifacts into actionable, trustworthy findings quickly and safely.

## Requirements

### Validated

- ✓ Ingest and store assessment artifacts through API/CLI submission paths — existing
- ✓ Process artifacts through asynchronous enrichment workflows with Dapr + RabbitMQ — existing
- ✓ Surface results through web API, Hasura-backed data access, and analyst UI — existing
- ✓ Run specialized analysis modules (.NET, DPAPI, document conversion, scanner integrations) — existing
- ✓ Support optional LLM-assisted triage/chatbot workflows via agents + LiteLLM profile — existing
- ✓ Enforce profile-aware readiness, observability, security hardening, quality gates, and operator runbook alignment — v1.0

### Active

- [ ] Partition high-volume enrichment workloads with explicit throughput targets.
- [ ] Add policy-driven throttling for expensive enrichment classes under queue pressure.
- [ ] Extend deployment/capacity guidance for multi-node scale operations.
- [ ] Introduce confidence-aware AI triage policy modes with operator override controls.
- [ ] Add AI usage/cost governance signals tied to operational budgets.

### Out of Scope

- Kubernetes migration in this cycle — Docker Compose remains the operator baseline.
- Multi-tenant control-plane redesign — outside current operator/team deployment model.
- Full architecture rewrite away from Dapr/Python architecture — too disruptive for this milestone.
- Autonomous auto-triage actions that mutate findings without operator controls — trust/safety risk.

## Context

- Brownfield monorepo with production-like service topology under `compose.yaml`.
- Existing codebase map is available in `.planning/codebase/*.md`.
- v1.0 delivered deterministic startup contracts, workflow observability, auth safety, CI quality gates, operator docs, and extension/performance guardrails.
- Existing AI synthesis endpoints (`/reports/source/synthesize`, `/reports/system/synthesize`) are available but uncached and currently require stronger governance signals.
- Existing throughput guidance and benchmark tooling exist but need milestone-scoped operational contracts.

## Constraints

- **Architecture**: Preserve Docker Compose + Dapr service model — current deployment and tooling depend on it.
- **Compatibility**: Maintain operator-facing workflows and API/UI expectations — avoid breaking established usage.
- **Security**: No secret values in logs/docs/prompts — must remain explicit throughout planning and implementation.
- **Execution**: Prefer incremental, phase-based changes with validation gates — reduces regression risk in a large system.
- **Performance**: Throughput changes must be baseline-driven and measurable before claiming improvement.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Start milestone v1.1 on SCALE-* and AI-* backlog requirements | v1.0 established a stable reliability base, enabling controlled scale/analysis expansion | — Pending |
| Keep research-first planning enabled for v1.1 | New milestone scope spans scale behavior and AI governance tradeoffs | Accepted |
| Continue numeric phase sequence from 7 | Preserve milestone continuity and traceability across roadmap history | Accepted |
| Maintain verification-first execution and no auto-advance | Matches local operating model and reduces hidden regressions | Accepted |

---
*Last updated: 2026-02-25 after milestone v1.1 initialization*
