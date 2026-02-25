# Nemesis Platform Evolution

## What This Is

Nemesis is an open-source, Docker-first offensive security data processing platform that ingests files from collection sources, enriches them through asynchronous pipelines, and exposes analyst workflows through API/UI surfaces. It is built as a polyglot service stack centered on Python services, Dapr pub/sub/workflows, PostgreSQL, MinIO, and optional LLM-assisted triage/chatbot capabilities.

This project context initializes GSD planning for the next evolution cycle of the existing brownfield codebase.

## Core Value

Turn collected offensive-operations artifacts into actionable, trustworthy findings quickly and safely.

## Requirements

### Validated

- ✓ Ingest and store assessment artifacts through API/CLI submission paths — existing
- ✓ Process artifacts through asynchronous enrichment workflows with Dapr + RabbitMQ — existing
- ✓ Surface results through web API, Hasura-backed data access, and analyst UI — existing
- ✓ Run specialized analysis modules (.NET, DPAPI, document conversion, scanner integrations) — existing
- ✓ Support optional LLM-assisted triage/chatbot workflows via agents + LiteLLM profile — existing

### Active

- [ ] Harden startup/readiness behavior across base, monitoring, and llm profiles
- [ ] Improve end-to-end observability and workflow health diagnostics
- [ ] Reduce security risk around secrets/logging/auth-mode drift
- [ ] Increase automated confidence for cross-service and frontend critical paths
- [ ] Simplify operator deployment, troubleshooting, and extension onboarding

### Out of Scope

- Kubernetes migration for this cycle — Docker Compose is the current operating model
- Multi-tenant SaaS control plane redesign — not part of current operator-focused mission
- Full rewrite away from Dapr/Python architecture — too disruptive for current milestone goals

## Context

- Brownfield monorepo with existing production-like service topology under `compose.yaml`
- Existing codebase map is available in `.planning/codebase/*.md`
- Runtime profiles are modular (`base`, `monitoring`, `llm`) and heavily configuration-driven via `.env`
- CI currently validates Python tests/type checks and nightly Docker buildability
- Known risk themes include startup ordering, cross-service coupling, and secret-handling hygiene

## Constraints

- **Architecture**: Preserve Docker Compose + Dapr service model — current deployment and tooling depend on it
- **Compatibility**: Maintain operator-facing workflows and API/UI expectations — avoid breaking established usage
- **Security**: No secret values in logs/docs/prompts — must remain explicit throughout planning and implementation
- **Execution**: Prefer incremental, phase-based changes with validation gates — reduces regression risk in a large system
- **Scope**: Prioritize reliability, quality, and operator leverage before net-new platform expansion

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Treat this as brownfield milestone planning, not greenfield product discovery | Existing capabilities are substantial and must be preserved while improving reliability | — Pending |
| Use balanced model profile with research + plan-check + verifier enabled | Good quality/cost tradeoff for multi-phase planning and verification | — Pending |
| Keep workflow mode interactive (auto-advance disabled) | Matches local preference for plan-led execution and explicit review points | — Pending |

---
*Last updated: 2026-02-25 after GSD project initialization*
