# Coding Conventions

**Analysis Date:** 2026-02-25

## Naming Patterns

**Files:**
- Python modules use snake_case file names and package folders (`projects/web_api/web_api/main.py`, `libs/common/common/storage.py`).
- Tests follow `test_*.py` naming in `tests/` directories (`projects/web_api/tests/test_download_range.py`).
- Frontend mostly uses `.jsx` and utility `.ts` files (`projects/frontend/src/App.jsx`, `projects/frontend/src/lib/utils.ts`).

**Functions and Variables:**
- Python uses snake_case (`get_postgres_connection_str`, `check_llm_enabled`, `workflow_purge_interval`).
- Constants are uppercase with underscores (`FILES_PUBSUB`, `MAX_CONCURRENT_ALERTS`).

**Types:**
- Pydantic models and typed classes use PascalCase (`TriageRequest`, `HealthResponse`, `TestAlert`).

## Code Style

**Formatting/Linting:**
- Ruff is the primary formatter/linter (`pyproject.toml` root `tool.ruff*`).
- Config highlights:
  - `line-length = 120`
  - `target-version = "py313"`
  - import sorting enabled (`I` rules)
  - quotes normalized to double quotes by Ruff formatter.

**Type Checking:**
- Pyright is run per project with `pyrightconfig.json` (`tools/typecheck.sh`).
- CI fast gate includes pyright checks (`.github/workflows/ci-fast.yml`).

## Import Organization

**Order:**
- Standard library first, then third-party, then local application imports (common across service entrypoints).
- Example pattern visible in:
  - `projects/web_api/web_api/main.py`
  - `projects/file_enrichment/file_enrichment/controller.py`
  - `projects/alerting/alerting/main.py`

**Shared package usage:**
- Heavy reuse of `common.*` modules and shared queue constants.
- Local path dependencies wired with `tool.uv.sources` in each `pyproject.toml`.

## Error Handling

**Patterns:**
- Service code wraps external I/O and long-lived loops in `try/except` and logs via `logger.exception`.
- Async background tasks are explicitly cancelled on lifespan shutdown.
- Many functions return safe defaults on failure for service resilience (e.g., cleanup queries returning empty lists).

**Boundary handling:**
- API layers raise `HTTPException` for user-facing errors (`projects/web_api/web_api/main.py`).
- Worker/subscription loops retry with sleep backoff (`projects/alerting/alerting/main.py`).

## Logging

**Framework:**
- Structured logging via `structlog` and shared `get_logger` helper.

**Patterns:**
- Context-rich log records (component/action metadata) instead of plain print statements.
- Startup/shutdown lifecycle logs are expected in service entrypoints.

## Comments

**Usage style:**
- Comments are practical and implementation-oriented (task rationale, startup order, retry logic).
- TODO markers used for deferred refactors/coverage (`projects/web_api/web_api/main.py`, `pyproject.toml`).

## Function and Module Design

**Design tendencies:**
- Service startup logic is centralized in `lifespan` context managers.
- Shared infrastructure wrappers live in `libs/common/common/` and are reused broadly.
- Domain-specific logic is separated into project-specific packages and route/subscription submodules.

**Exports and boundaries:**
- Entrypoint modules include router registration and subscription wiring.
- Topic/queue names are centralized to avoid string duplication (`libs/common/common/queues.py`).

## Frontend-Specific Notes

**Current pattern:**
- React components and context providers are colocated under `projects/frontend/src/components` and `projects/frontend/src/contexts`.
- Build tooling is Vite + Tailwind (`projects/frontend/vite.config.js`, `projects/frontend/tailwind.config.js`).

---

*Convention analysis: 2026-02-25*
*Update when lint/type policies or style norms change*
