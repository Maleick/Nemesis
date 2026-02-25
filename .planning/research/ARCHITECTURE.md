# Architecture Research

**Domain:** Event-driven offensive-security processing platform
**Researched:** 2026-02-25
**Confidence:** HIGH

## Standard Architecture

### System Overview

```text
┌─────────────────────────────────────────────────────────────┐
│                    Ingress & Analyst Layer                  │
├─────────────────────────────────────────────────────────────┤
│  frontend  │  web-api  │  cli/connectors  │  alerting UI   │
├─────────────────────────────────────────────────────────────┤
│                  Orchestration & Processing Layer           │
├─────────────────────────────────────────────────────────────┤
│  Dapr sidecars │ workflow runtime │ enrichment services      │
│  document conversion │ scanner/.NET workers │ housekeeping   │
├─────────────────────────────────────────────────────────────┤
│                      Data & Infra Layer                     │
│  PostgreSQL/Hasura │ MinIO │ RabbitMQ │ Traefik │ Monitoring │
└─────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| Web/API ingress | Accept uploads/queries and return analyst-facing responses | FastAPI + Dapr invocation + storage/DB adapters |
| Workflow processors | Execute asynchronous enrichment/conversion pipelines | Dapr workflows + pub/sub subscribers |
| Shared domain libraries | Keep contracts (models/queues/db/storage) consistent | Python packages under `libs/` |
| Data/queue substrate | Persist files/results and propagate events | PostgreSQL + Hasura + MinIO + RabbitMQ |
| Operator edge | Auth/routing and profile composition | Traefik + Compose profiles |

## Recommended Project Structure

```text
projects/
├── web_api/                  # Primary API ingress and orchestration endpoints
├── file_enrichment/          # Main enrichment workflow orchestrator
├── document_conversion/      # Document conversion workflow service
├── alerting/                 # Notification routing and filters
├── agents/                   # Optional LLM triage/chatbot service
├── frontend/                 # Analyst web application
├── cli/                      # Operator/connector CLI
└── ...                       # Additional service modules

libs/
├── common/                   # Shared contracts/utilities
├── file_enrichment_modules/  # Enrichment plugin modules
├── nemesis_dpapi/            # DPAPI domain logic
├── chromium/                 # Chromium artifact processing
└── file_linking/             # File correlation/linking logic
```

### Structure Rationale

- Service code and shared domain code remain separate for clear ownership boundaries.
- Shared `libs/` prevent queue/model/config drift across independently evolving services.
- Compose + infra directories make runtime behavior reviewable and version-controlled.

## Architectural Patterns

### Pattern 1: Event-Driven Pipeline

**What:** Services subscribe/publish to Dapr-backed topics and workflow events.
**When to use:** Long-running enrichment and fan-out/fan-in processing.
**Trade-offs:** Great decoupling and resilience; requires strict contract hygiene.

### Pattern 2: Shared Contract Library

**What:** Centralize queue names, models, and DB/storage helpers in `libs/common`.
**When to use:** Any cross-service payload/contract.
**Trade-offs:** Reduces drift; increases dependency coupling that must be version-controlled carefully.

### Pattern 3: Profile-Based Topology Composition

**What:** Compose profiles control optional capabilities (`monitoring`, `llm`, `jupyter`).
**When to use:** Operator environments with variable resource/security needs.
**Trade-offs:** Flexible deployments; adds startup matrix complexity to validate.

## Data Flow

### Request Flow

```text
Upload/API request
    ↓
web-api ingress
    ↓
MinIO + metadata publish
    ↓
file_enrichment workflow subscribers
    ↓
downstream module outputs (document conversion, scanner, dotnet)
    ↓
PostgreSQL/Hasura + alerting/agents consumers
    ↓
frontend/API query and triage workflows
```

### State Management

- Persistent workflow and result state live in PostgreSQL.
- Object payloads/transforms live in MinIO.
- Event progression is transport-backed by RabbitMQ through Dapr pub/sub.

### Key Data Flows

1. **Artifact processing flow:** upload -> enqueue -> enrich -> store -> present.
2. **Operational signal flow:** workflow state/finding changes -> alerting/agents -> operator action.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 0-10 operators | Single-node compose with strict health gates is sufficient |
| 10-50 operators / heavier throughput | Increase worker replicas and tune workflow concurrency/pool sizes |
| 50+ operators / sustained high-volume ingestion | Partition processing domains and evaluate orchestrator upgrade path |

### Scaling Priorities

1. **First bottleneck:** workflow + queue backlogs in enrichment services.
2. **Second bottleneck:** DB and object-storage contention under high concurrent processing.

## Anti-Patterns

### Anti-Pattern 1: Topic/Schema Drift

**What people do:** introduce new payload/topic strings ad hoc.
**Why it's wrong:** subscribers silently miss events or parse incorrectly.
**Do this instead:** route all topic constants and model contracts through shared libs and validation tests.

### Anti-Pattern 2: Hidden Startup Side Effects

**What people do:** perform external network/secret calls during module import.
**Why it's wrong:** fragile startup and test behavior.
**Do this instead:** isolate external initialization in explicit lifespan/startup paths.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| C2 connectors (Mythic/CobaltStrike/Outflank) | CLI-managed pull/sync flows | Keep connector-specific config isolated and validated |
| Notification providers | Apprise URL adapters | Route through alert severity/filter controls |
| LLM providers via LiteLLM | Proxy model path from agents service | Treat auth-mode health as hard dependency in llm profile |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| web-api ↔ enrichment | Dapr pub/sub + service invocation | Ingestion integrity and idempotency are critical |
| enrichment ↔ conversion/scanner/.NET | Topic-driven async handoff | Preserve object_id traceability through every stage |
| alerting/agents ↔ Hasura | GraphQL query/subscription | Needs robust reconnect and auth validation behavior |

## Sources

- Existing architecture docs and runtime manifests in this repo
- `.planning/codebase/ARCHITECTURE.md` and `.planning/codebase/STRUCTURE.md`
- [Dapr architecture reference](https://docs.dapr.io/)

---
*Architecture research for: event-driven offensive-security processing platform*
*Researched: 2026-02-25*
