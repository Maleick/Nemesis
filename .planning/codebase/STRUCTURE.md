# Codebase Structure

**Analysis Date:** 2026-02-25

## Directory Layout

```text
Nemesis/
├── docs/                  # Published docs (usage, architecture, operations)
├── infra/                 # Dapr components, DB init, monitoring, proxy configs
├── libs/                  # Shared Python libraries used by multiple services
├── projects/              # Deployable services (API, enrichment, CLI, frontend, etc.)
├── tools/                 # Dev/ops helper scripts (test, lint, startup helpers)
├── compose.yaml           # Main multi-service topology
├── compose.override.yaml  # Dev overrides
├── pyproject.toml         # Root Ruff config
└── README.md              # Project overview and operations guidance
```

## Directory Purposes

**`docs/`:**
- Purpose: operator/developer documentation and MkDocs source.
- Key files: `docs/overview.md`, `docs/usage_guide.md`, `docs/api.md`, `docs/cli.md`.

**`infra/`:**
- Purpose: infrastructure runtime definitions.
- Subdirs: `infra/dapr/`, `infra/postgres/`, `infra/hasura/`, `infra/traefik/`, `infra/litellm/`, `infra/grafana/`, `infra/prometheus/`.

**`libs/`:**
- Purpose: reusable Python packages.
- Key packages:
  - `libs/common/`
  - `libs/file_enrichment_modules/`
  - `libs/nemesis_dpapi/`
  - `libs/chromium/`
  - `libs/file_linking/`

**`projects/`:**
- Purpose: deployable services and app components.
- Service directories: `web_api`, `file_enrichment`, `document_conversion`, `alerting`, `agents`, `housekeeping`, `frontend`, `cli`, `dotnet_service`, `noseyparker_scanner`, `jupyter`.

**`tools/`:**
- Purpose: cross-repo scripts for lifecycle tasks.
- Key files: `tools/test.sh`, `tools/typecheck.sh`, `tools/lint.sh`, `tools/nemesis-ctl.sh`.

## Key File Locations

**Entry Points:**
- `projects/web_api/web_api/main.py` (main API ingress).
- `projects/file_enrichment/file_enrichment/controller.py` (enrichment orchestrator).
- `projects/document_conversion/document_conversion/main.py` (conversion workflow service).
- `projects/agents/agents/main.py` (LLM/agent service, optional profile).
- `projects/cli/cli/main.py` (CLI command entrypoint).

**Configuration:**
- `compose.yaml`, `compose.base.yaml`, `compose.prod.build.yaml`.
- `env.example` for runtime environment template.
- Root `pyproject.toml` for lint/format policy.
- `projects/frontend/package.json` for frontend dependency/runtime scripts.

**Testing:**
- `libs/*/tests/` and `projects/*/tests/` for pytest suites.
- CI workflow definitions in `.github/workflows/`.

**Documentation:**
- `README.md` (root), project READMEs under `projects/*/README.md`.

## Naming Conventions

**Files (Python services/libs):**
- Snake case module names and `test_*.py` test files.

**Directories:**
- Service names often use snake_case (`projects/file_enrichment`, `projects/document_conversion`).
- Shared package dirs are concise nouns (`libs/common`, `libs/chromium`).

**Special Patterns:**
- Service entrypoint generally `main.py` or `controller.py`.
- Dapr sidecar service names use `*-dapr` in compose (`compose.yaml`).

## Where to Add New Code

**New backend service behavior:**
- Service logic: corresponding `projects/<service>/<package>/` directory.
- Shared contracts/helpers: `libs/common/common/` or targeted shared lib.
- Tests: `projects/<service>/tests/`.

**New enrichment module:**
- Implementation: `libs/file_enrichment_modules/file_enrichment_modules/<module>/`.
- Tests: `libs/file_enrichment_modules/tests/`.

**New frontend features:**
- Components/contexts/utils in `projects/frontend/src/`.

**Infra wiring changes:**
- Dapr component config: `infra/dapr/components/`.
- Container/service wiring: `compose.yaml` and profile-specific compose files.

## Special Directories

**`.venv/` directories under many libs/projects:**
- Purpose: local virtual environments per package/service.
- Source: developer environment setup (`uv sync`/local tooling).
- Committed: generally no (workspace artifacts).

**`.pytest_cache/` directories:**
- Purpose: pytest runtime cache.
- Source: local test execution.
- Committed: no.

**`docs/images/`:**
- Purpose: static assets for published documentation.
- Committed: yes.

---

*Structure analysis: 2026-02-25*
*Update when directory layout or ownership boundaries change*
