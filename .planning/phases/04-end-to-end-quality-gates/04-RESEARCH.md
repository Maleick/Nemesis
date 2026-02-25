# Phase 4 Research: End-to-End Quality Gates

**Phase:** 04 End-to-End Quality Gates
**Researched:** 2026-02-25
**Status:** Complete
**Requirement IDs:** TEST-01, TEST-02, TEST-03, TEST-04

## Objective

Define a low-friction quality-gate implementation that raises release confidence for critical Nemesis workflows without introducing flaky CI dependencies.

## Context and Constraints

- `04-CONTEXT.md` does not exist; this planning pass uses roadmap, requirements, and codebase evidence.
- Phase 3 completed and verified; auth/logging contract regressions are in place and should remain green.
- `workflow.auto_advance=false`; planning should stop after plan verification.

## Existing Baseline

### CI and automation

- Required PR gate is `.github/workflows/ci-fast.yml`.
- Current fast gate runs:
  - `./tools/install_dev_env.sh`
  - `./tools/test.sh`
  - `./tools/test.sh --readiness-contract`
  - `./tools/typecheck.sh`
- No explicit frontend smoke tests are executed in CI today.
- No explicit queue/topic contract gate is enforced in CI today.

### Runtime/profile controls

- Profile behavior is controlled through `tools/nemesis-ctl.sh` with `--monitoring`, `--jupyter`, and `--llm` flags.
- Compose profile topology is defined in `compose.yaml` and compose overlays (`compose.base.yaml`, `compose.prod.build.yaml`, `compose.override.yaml`).
- Readiness matrix support exists via `nemesis-ctl.sh status`, but there is no dedicated automated profile smoke contract test suite.

### Critical ingestion/enrichment/retrieval flow surfaces

- Ingestion endpoint: `POST /files` in `projects/web_api/web_api/main.py`.
- Workflow status/lifecycle endpoints: `/workflows/status`, `/workflows/failed`, `/workflows/lifecycle/{object_id}` in `projects/web_api/web_api/main.py`.
- Retrieval endpoint: `GET /files/{object_id}` in `projects/web_api/web_api/main.py` and existing range tests in `projects/web_api/tests/test_download_range.py`.
- Existing observability tests (`projects/web_api/tests/test_workflow_observability.py`) validate summary/lifecycle behavior, but not a full ingestion roundtrip smoke contract.

### Queue/topic contract surfaces

- Canonical constants live in `libs/common/common/queues.py`.
- Publishers/consumers are distributed across:
  - `projects/web_api/web_api/main.py`
  - `projects/file_enrichment/file_enrichment/controller.py`
  - `projects/file_enrichment/file_enrichment/workflow_completion.py`
  - `projects/file_enrichment/file_enrichment/activities/publish_findings.py`
  - `projects/alerting/alerting/main.py`
  - `projects/document_conversion/document_conversion/main.py`
- `WorkflowQueueMonitor.TOPIC_TO_QUEUE_MAPPING` in `projects/web_api/web_api/queue_monitor.py` duplicates queue naming assumptions and is drift-prone without dedicated contract checks.

### Frontend quality baseline

- `projects/frontend/package.json` only provides `dev`, `build`, and `preview` scripts.
- No frontend unit/smoke test harness exists (no Vitest/Jest/Playwright config, no smoke specs).

## Gap Findings Mapped to Requirements

1. **TEST-01 gap:** No dedicated automated smoke test proves upload -> enrichment/workflow -> retrieval contract in CI.
2. **TEST-02 gap:** Profile-aware readiness behavior is operationally available but not enforced by automated profile smoke checks in CI.
3. **TEST-03 gap:** Frontend critical navigation/result-view workflow lacks automated smoke coverage.
4. **TEST-04 gap:** Queue/topic/payload compatibility between producers and consumers is not protected by contract tests.

## Recommended Plan Split

### Plan 04-01 (TEST-01)

- Add backend smoke contract tests that validate ingestion/workflow/retrieval invariants using stable API/test fixtures.
- Wire a focused smoke gate into CI fast workflow.

### Plan 04-02 (TEST-02, TEST-03)

- Add profile-aware smoke checks for `nemesis-ctl` status behavior under `base`/`llm`/`monitoring` paths.
- Introduce frontend smoke test harness and critical navigation/result-view tests.
- Integrate both into CI fast gate.

### Plan 04-03 (TEST-04)

- Add queue/topic/payload contract tests validating constant usage and producer/consumer compatibility.
- Add contract gate invocation to CI fast workflow.

## Risks and Mitigations

- **Risk:** E2E smoke tests become flaky due to external services.
  - **Mitigation:** Use deterministic mocked/fixture-based API smoke contracts in unit-test scope for fast gate, keep heavy integration optional.
- **Risk:** Frontend smoke introduces heavy browser dependencies and slows PR checks.
  - **Mitigation:** Prefer lightweight component/route smoke tests (Vitest + jsdom) for fast gate; reserve browser E2E for later/nightly if needed.
- **Risk:** Queue-contract tests become brittle if based on string snapshots only.
  - **Mitigation:** Validate against canonical constants and explicit allowed topic mappings with focused invariants.
- **Risk:** Multiple plans touching `ci-fast.yml` cause sequencing conflicts.
  - **Mitigation:** Execute plans in ordered waves (04-01 -> 04-02 -> 04-03).

## Validation Architecture

### Gate 1: Backend smoke (TEST-01)

- `cd projects/web_api && uv run pytest tests/test_ingestion_workflow_smoke.py tests/test_download_range.py tests/test_workflow_observability.py -q`
- `./tools/test.sh --readiness-contract`

### Gate 2: Profile + frontend smoke (TEST-02, TEST-03)

- `bash tools/tests/test_nemesis_ctl_profiles.sh`
- `cd projects/frontend && npm run test:smoke && npm run build`

### Gate 3: Queue contract compatibility (TEST-04)

- `cd projects/web_api && uv run pytest tests/test_queue_topic_contracts.py -q`
- `cd projects/file_enrichment && uv run pytest tests/test_queue_topic_contracts.py -q`
- `cd projects/alerting && uv run pytest tests/test_queue_topic_contracts.py -q`

### CI fast gate integration target

- `.github/workflows/ci-fast.yml` should execute:
  - backend smoke suite
  - profile smoke script
  - frontend smoke suite
  - queue contract suites

## Execution Notes for Planner

- Keep plans executable with explicit file-level scope and command-level verification.
- Keep plan dependencies explicit to avoid cross-plan CI-file conflicts.
- Ensure all four TEST-* IDs are covered in plan frontmatter `requirements` fields.

---
*Phase research complete: 2026-02-25*
