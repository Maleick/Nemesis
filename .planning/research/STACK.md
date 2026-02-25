# Stack Research

**Domain:** Offensive-security file processing and analysis platform (brownfield evolution)
**Researched:** 2026-02-25
**Confidence:** HIGH

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.13 | Primary service/runtime language | Existing codebase and libraries are already standardized here; strong async ecosystem |
| FastAPI | 0.121.x | HTTP APIs for services | Mature async framework with good typing, OpenAPI, and operational familiarity |
| Dapr | 1.16.x | Pub/sub, workflows, service invocation, secrets | Reduces boilerplate and keeps infra concerns centralized |
| PostgreSQL + Hasura | 18.1 + 2.48.x | Data persistence and GraphQL data access | Proven current architecture; supports operational queries and subscriptions |
| MinIO | RELEASE.2025-09-07 | Object store for artifacts/transforms | S3-compatible, self-hosted, already integrated across services |
| RabbitMQ | 4.2.0 | Message backbone under Dapr pub/sub | Good fit for current queueing patterns and resource profile |
| Docker Compose | v2 family | Deployment/orchestration model | Current operator workflow and docs are Docker-first |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| structlog | 25.x | Structured logging | All services and shared libs for consistent log context |
| asyncpg / psycopg | 0.30.x / 3.2.x | Async/sync PostgreSQL access | Service DB interactions and pool-backed operations |
| pydantic | 2.10.x | Typed models and validation | API contracts, event payloads, and shared model schemas |
| gql (+ websocket transport) | 3.5.x | Hasura GraphQL query/subscription client | Agent/alerting integrations and live data subscriptions |
| dapr-ext-fastapi / dapr-ext-workflow | 1.16.x | Dapr framework integration | Services using subscriptions/workflows |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| uv | Python dependency/runtime management | Already used by CI and local scripts (`tools/test.sh`, `tools/typecheck.sh`) |
| Ruff | Lint + format | Centralized in root `pyproject.toml`, line length 120 |
| Pyright | Static type checking | Per-service configs under `projects/*/pyrightconfig.json` |
| GitHub Actions | CI + image build validation | Fast gate + nightly Docker validation already in place |

## Installation

```bash
# Root dependency + tooling setup
./tools/install_dev_env.sh

# Validate Python stack
./tools/test.sh
./tools/typecheck.sh

# Build and run compose stack
cp env.example .env
docker compose -f compose.yaml up -d
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Docker Compose + Dapr | Kubernetes-native controllers | When multi-cluster scaling/tenancy and stronger scheduling guarantees are required |
| RabbitMQ via Dapr pub/sub | Kafka/Redpanda | If replay/long-retention streaming semantics become mandatory |
| Hasura GraphQL over Postgres | Direct service-only SQL APIs | For constrained deployments where GraphQL layer is unnecessary |
| MinIO self-hosted | Cloud S3 + managed services | For cloud-native ops teams prioritizing managed control plane over local portability |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Ad-hoc queue/topic names in code | Causes producer/consumer drift and silent failures | Centralized constants in `libs/common/common/queues.py` |
| Logging secret values during startup | Credential leakage risk | Redacted health/status logging with explicit secret-safe helpers |
| Replacing workflow orchestration piecemeal per service | Inconsistent behavior and operational overhead | Keep Dapr workflow conventions and shared tracking patterns |

## Stack Patterns by Variant

**If operator deployment is base-only (no llm profile):**
- Keep Web API + enrichment + data/queue core profile only
- Favor deterministic startup and low moving parts

**If llm profile is enabled:**
- Add `agents`, `litellm`, `phoenix` with strict auth/readiness checks
- Treat model auth mode and token health as first-class SLO inputs

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| Python 3.13 | FastAPI 0.121.x, Pydantic 2.10.x | Current repo baseline |
| Dapr 1.16.x | dapr-ext-fastapi/workflow 1.16.x | Keep extensions pinned to Dapr minor |
| Postgres 18.x | psycopg 3.2.x, asyncpg 0.30.x | Validate migrations/driver behavior before major upgrades |
| Vite 6.x | React 18.x | Frontend package baseline |

## Sources

- Internal codebase map: `.planning/codebase/STACK.md`, `.planning/codebase/ARCHITECTURE.md`
- Repo docs: `README.md`, `docs/overview.md`, `docs/docker_compose.md`, `docs/agents.md`
- Runtime manifests: `compose.yaml`, `.github/workflows/*.yml`
- Official references used for alignment: [Dapr docs](https://docs.dapr.io/), [FastAPI docs](https://fastapi.tiangolo.com/), [Hasura docs](https://hasura.io/docs/)

---
*Stack research for: offensive-security file processing and analysis platform*
*Researched: 2026-02-25*
