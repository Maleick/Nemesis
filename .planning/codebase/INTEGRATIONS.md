# External Integrations

**Analysis Date:** 2026-02-25

## APIs & External Services

**Service-to-service invocation (internal):**
- Dapr sidecars provide service invocation/pubsub/workflow plumbing across services (`compose.yaml`, `infra/dapr/components/**`).
- Example subscriptions are registered in:
  - `projects/file_enrichment/file_enrichment/controller.py`
  - `projects/document_conversion/document_conversion/main.py`
  - `projects/web_api/web_api/main.py`

**GraphQL/Data API layer:**
- Hasura GraphQL Engine fronts PostgreSQL (`compose.yaml` service `hasura`).
- Services query/subscribe Hasura via `gql`:
  - `projects/agents/agents/main.py`
  - `projects/alerting/alerting/main.py`

**Notification routing:**
- Apprise integration for outbound notifications (`projects/alerting/alerting/main.py`, `docs/alerting.md`).
- Endpoint inventory exposed via `/apprise-info` route (`projects/alerting/alerting/main.py`).

**C2 connector ecosystem (CLI):**
- Mythic, Cobalt Strike, and Outflank connectors (`projects/cli/cli/main.py`, `projects/cli/README.md`, `docs/cli.md`).
- Velociraptor connector artifacts documented under `projects/velociraptor_connector/README.md`.

## Data Storage

**Databases:**
- PostgreSQL is primary relational store (`compose.yaml` service `postgres`, schema init under `infra/postgres`).
- Hasura metadata points to the same PostgreSQL instance (`compose.yaml` `HASURA_GRAPHQL_DATABASE_URL`).

**Object Storage:**
- MinIO stores submitted and transformed file blobs (`compose.yaml` services `minio`/`minio-init`).
- Accessed through shared `StorageMinio` helper (`libs/common/common/storage.py`).

**Messaging/Queueing:**
- RabbitMQ under Dapr pub/sub (`compose.yaml` service `rabbitmq`, `infra/dapr/components/pubsub/*.yaml`).
- Topic names centralized in `libs/common/common/queues.py`.

## Authentication & Identity

**Ingress auth:**
- Traefik basic auth middleware controlled via `BASIC_AUTH_USERS` (`compose.yaml`, `env.example`).

**Service secrets:**
- Runtime services fetch secrets from Dapr `nemesis-secret-store` (`libs/common/common/db.py`, `libs/common/common/storage.py`).

**LLM auth options:**
- `official_key` and `codex_oauth` modes for agents/LiteLLM (`README.md`, `docs/agents.md`, `env.example`, `compose.yaml`).

## Monitoring & Observability

**Metrics and traces:**
- OpenTelemetry Collector + Jaeger + Prometheus + Grafana + Loki + Promtail (`compose.yaml`, `infra/otel-collector`, `infra/prometheus`, `infra/grafana`, `infra/loki`).

**LLM observability:**
- Phoenix service for trace/cost visibility in llm profile (`compose.yaml` service `phoenix`, `projects/agents/agents/phoenix_cost_sync.py`).

## CI/CD & Deployment

**CI pipeline:**
- Fast gate for tests + pyright (`.github/workflows/ci-fast.yml`).
- Nightly Docker build validation (`.github/workflows/docker-validate-nightly.yml`).

**Image build/publish:**
- Multi-arch image builds to GHCR (`.github/workflows/docker-build.yml`, `.github/workflows/docker-build-base.yml`, `.github/workflows/docker-build-noseyparker.yml`).

## Environment Configuration

**Local development:**
- `.env` from `env.example` plus `tools/nemesis-ctl.sh` startup paths (`README.md`, `docs/docker_compose.md`).

**Profile-specific runtime:**
- Monitoring profile adds telemetry stack.
- LLM profile adds `agents`, `litellm`, and `phoenix` services (`compose.yaml`).

## Webhooks & Callbacks

**Incoming event streams:**
- Hasura websocket subscriptions for alerting and agents logic (`projects/alerting/alerting/main.py`, `projects/agents/agents/main.py`).

**Internal callbacks:**
- Dapr pub/sub handlers in enrichment and conversion services for pipeline stage transitions (`projects/file_enrichment/file_enrichment/controller.py`, `projects/document_conversion/document_conversion/main.py`).

---

*Integration audit: 2026-02-25*
*Update when adding/removing external systems*
