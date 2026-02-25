# Architecture

**Analysis Date:** 2026-02-25

## Pattern Overview

**Overall:** Docker-compose microservice platform with Dapr sidecars and shared Python libraries.

**Key Characteristics:**
- Polyglot service fleet (mostly Python + one frontend + Rust scanner + .NET component).
- Event-driven processing via Dapr pub/sub on RabbitMQ.
- Workflow-oriented file processing in enrichment and document conversion.
- Shared `libs/*` packages for cross-service models, queue names, DB/storage access.

## Layers

**Ingress/API Layer:**
- Purpose: user-facing HTTP routes and API gateway behaviors.
- Contains: frontend, web API, Traefik routing/auth.
- Depends on: Hasura, storage, enrichment services.
- Used by: operators, CLI clients, browser UI.
- Key paths: `projects/frontend/*`, `projects/web_api/web_api/main.py`, `compose.yaml` (`traefik`).

**Processing/Workflow Layer:**
- Purpose: asynchronous enrichment and conversion orchestration.
- Contains: `file_enrichment`, `document_conversion`, scanner and .NET outputs.
- Depends on: Dapr runtime/workflows, pubsub topics, PostgreSQL, MinIO.
- Key paths: `projects/file_enrichment/file_enrichment/controller.py`, `projects/document_conversion/document_conversion/main.py`.

**Intelligence/Automation Layer (optional llm profile):**
- Purpose: AI-assisted triage/summarization/chatbot and model proxying.
- Contains: `agents`, LiteLLM proxy, Phoenix tracing.
- Key paths: `projects/agents/agents/main.py`, `infra/litellm/config.yml`, `compose.yaml` services `agents`, `litellm`, `phoenix`.

**Shared Domain Layer:**
- Purpose: reusable domain models/utilities.
- Contains: queue constants, db/storage wrappers, enrichment modules, DPAPI/chromium/file-linking libs.
- Key paths: `libs/common/common/*`, `libs/file_enrichment_modules/*`, `libs/nemesis_dpapi/*`, `libs/chromium/*`, `libs/file_linking/*`.

## Data Flow

**File ingestion and enrichment flow:**
1. Client uploads file via Web API (`projects/web_api/web_api/main.py`, `/files`).
2. File data stored in MinIO via `StorageMinio` (`libs/common/common/storage.py`).
3. Metadata/events published on Dapr pub/sub topics (`libs/common/common/queues.py`).
4. `file_enrichment` consumes events and executes workflow/modules (`projects/file_enrichment/file_enrichment/controller.py`).
5. Downstream services (e.g., `document_conversion`, `dotnet-service`, `noseyparker-scanner`) publish output topics.
6. Results are persisted in PostgreSQL and exposed through Hasura/Web API routes.

**Alerting/triage flow:**
1. Findings in Hasura/PostgreSQL are observed by `alerting` and optional `agents` subscriptions.
2. `alerting` filters/severity-checks and dispatches notifications via Apprise.
3. `agents` can produce triage/summaries via LiteLLM-backed model execution.

## Key Abstractions

**Queue Topic Constants:**
- Purpose: avoid topic-name drift across services.
- Location: `libs/common/common/queues.py`.
- Pattern: `*_PUBSUB` and `*_TOPIC` constants shared by publishers/subscribers.

**Storage/DB Service Facades:**
- `StorageMinio` for object operations (`libs/common/common/storage.py`).
- `get_postgres_connection_str()` and pool constructors (`libs/common/common/db.py`).

**Workflow Runtime Hooks:**
- Dapr workflow runtime setup and lifecycle helpers (`libs/common/common/workflows/setup.py`, service lifespan handlers).

## Entry Points

**Primary service entrypoints:**
- `projects/web_api/web_api/main.py`
- `projects/file_enrichment/file_enrichment/controller.py`
- `projects/document_conversion/document_conversion/main.py`
- `projects/alerting/alerting/main.py`
- `projects/agents/agents/main.py`
- `projects/housekeeping/housekeeping/main.py`
- `projects/cli/cli/main.py`

**Infra entrypoints:**
- `compose.yaml` for service topology.
- `.github/workflows/*.yml` for CI/build validation/publish pipelines.

## Error Handling

**Strategy:**
- Service boundaries use `try/except` with structured logging (`logger.exception`, `logger.warning`).
- Async background tasks are supervised in FastAPI lifespan contexts with explicit cancellation on shutdown.
- Retry loops are used for subscription/reconnect paths in alerting/agents workflows.

## Cross-Cutting Concerns

**Logging:**
- Primarily `structlog` and common logger helpers (`libs/common/common/logger.py`, service imports).

**Validation:**
- Pydantic models for API payloads and internal schemas (`common.models`, `common.models2`, project request/response models).

**Security and secrets:**
- Dapr secret store for runtime secret retrieval; environment variables for compose wiring.

**Observability:**
- Optional monitoring profile supplies trace, log, and metrics stack through OpenTelemetry + Grafana ecosystem.

---

*Architecture analysis: 2026-02-25*
*Update when major patterns or boundaries change*
