# Technology Stack

**Analysis Date:** 2026-02-25

## Languages

**Primary:**
- Python 3.13 across service code and shared libraries (`projects/*/pyproject.toml`, `libs/*/pyproject.toml`).

**Secondary:**
- JavaScript/TypeScript/TSX for the frontend (`projects/frontend/package.json`, `projects/frontend/src/*`).
- Rust for Nosey Parker scanner (`projects/noseyparker_scanner/Cargo.toml`).
- C# for .NET enrichment service (`projects/dotnet_service/*`).
- Shell/YAML for orchestration and automation (`tools/*.sh`, `compose.yaml`, `.github/workflows/*.yml`).

## Runtime

**Environment:**
- Docker Compose orchestrates runtime services and infra (`compose.yaml`, `compose.override.yaml`, `compose.prod.build.yaml`).
- Python services run as containerized FastAPI apps with Dapr sidecars (`projects/web_api/web_api/main.py`, `projects/file_enrichment/file_enrichment/controller.py`).

**Package Managers:**
- `uv` for Python dependency management and execution (`tools/install_dev_env.sh`, `tools/test.sh`, project `pyproject.toml` files).
- `npm` for frontend dependencies (`projects/frontend/package-lock.json`, `projects/frontend/package.json`).

## Frameworks

**Core Service Frameworks:**
- FastAPI for HTTP APIs (`projects/web_api/web_api/main.py`, `projects/alerting/alerting/main.py`, `projects/agents/agents/main.py`).
- Dapr runtime and extensions for pub/sub and workflows (`dapr==1.16.0` in service/library `pyproject.toml` files).
- Async DB clients and pools via `asyncpg` and `psycopg` (`libs/common/common/db.py`, service dependencies).

**Workflow/Async Infrastructure:**
- Dapr workflows and tracking (`libs/common/common/workflows/*`, `projects/file_enrichment/file_enrichment/controller.py`).
- APScheduler for cleanup jobs (`projects/housekeeping/housekeeping/main.py`).

**Frontend Stack:**
- React 18 + React Router + Vite (`projects/frontend/package.json`).
- Tailwind CSS + Radix UI + Recharts (`projects/frontend/package.json`, `projects/frontend/tailwind.config.js`).

## Key Dependencies

**Critical Platform Dependencies:**
- `fastapi`, `uvicorn`: API services (`projects/*/pyproject.toml`).
- `dapr`, `dapr-ext-fastapi`, `dapr-ext-workflow`: service communication and orchestration.
- `structlog`: structured logging in Python services (`projects/*/pyproject.toml`, `libs/common/pyproject.toml`).
- `minio`, `asyncpg`, `psycopg`: object and relational storage clients.
- `gql` + websocket transport: Hasura GraphQL query/subscription integration (`projects/agents/agents/main.py`, `projects/alerting/alerting/main.py`).

**Enrichment/Domain-Specific:**
- Malware/document tooling such as `yara-x`, `pymupdf`, `msoffcrypto-tool`, `oletools`, `pypykatz`, `regipy` (`libs/file_enrichment_modules/pyproject.toml`, `projects/file_enrichment/pyproject.toml`).

## Configuration

**Environment and Secrets:**
- `.env`/`env.example` drive deployment parameters (`env.example`, `compose.yaml`).
- Dapr secret store abstraction is used for runtime secret retrieval (`libs/common/common/db.py`, `libs/common/common/storage.py`).

**Build/Runtime Config Files:**
- Compose and infra configs (`compose*.yaml`, `infra/**`).
- Python lint/format rules in root `pyproject.toml` (`tool.ruff*`).
- Frontend build config (`projects/frontend/vite.config.js`, `projects/frontend/postcss.config.js`).

## Platform Requirements

**Development:**
- Docker + Docker Compose for end-to-end stack startup (`README.md`, `docs/docker_compose.md`).
- Python 3.13 + `uv` for local test/typecheck flows (`.github/workflows/ci-fast.yml`, `tools/test.sh`).
- System package dependency for CLI transitive build in CI (`libleveldb-dev` in `.github/workflows/ci-fast.yml`).

**Production:**
- Multi-container deployment via published GHCR images (`.github/workflows/docker-build.yml`).
- Optional profiles: monitoring (`prometheus`, `grafana`, `loki`, `jaeger`) and llm (`agents`, `litellm`, `phoenix`) in `compose.yaml`.

---

*Stack analysis: 2026-02-25*
*Update after major dependency/runtime changes*
