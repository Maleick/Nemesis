# Phase 2 Research: Workflow Observability Baseline

**Phase:** 02 Workflow Observability Baseline
**Researched:** 2026-02-25
**Status:** Complete
**Requirement IDs:** OBS-01, OBS-02, OBS-03

## Objective

Define a low-risk implementation path to make workflow lifecycle behavior observable end-to-end, including object-level traceability, routine operator dashboard signals, and sustained-issue alert routing.

## User Constraints

- No phase context file exists at `.planning/phases/02-workflow-observability-baseline/02-CONTEXT.md`.
- Planning is based on `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md`, and current codebase behavior only.

## Existing Baseline

- Workflow lifecycle state is persisted in the `workflows` table with `wf_id`, `object_id`, status, runtime, and enrichment success/failure arrays in `infra/postgres/01-schema.sql`.
- Lifecycle writes are centralized in `libs/common/common/workflows/tracking_service.py`, and workflow startup/finalization paths are in `projects/file_enrichment/file_enrichment/workflow_manager.py` and `projects/file_enrichment/file_enrichment/activities/finalize_workflow.py`.
- API status surfaces already exist via `projects/web_api/web_api/main.py`:
  - `GET /workflows/status`
  - `GET /workflows/failed`
  - `GET /queues`
  - `GET /system/health`
- Queue telemetry is collected from RabbitMQ management API in `projects/web_api/web_api/queue_monitor.py`.
- Frontend dashboard polling already exists in `projects/frontend/src/components/Dashboard/StatsOverview.jsx` for workflow and queue endpoints.
- Alert delivery infrastructure already exists: alert events publish to `ALERTING_PUBSUB`/`ALERTING_NEW_ALERT_TOPIC` and are consumed in `projects/alerting/alerting/main.py`.

## Gaps Against Phase Goal

1. There is no single object lifecycle endpoint that correlates ingestion, workflow progression, and publication outcomes by `object_id`.
2. Dashboard signals exist but are not normalized around operational thresholds and service-health matrix visibility for routine triage.
3. Sustained backlog/failure conditions do not currently generate dedicated operational alerts; existing alerting is primarily findings-driven.
4. There is no focused test coverage for observability API contracts in `projects/web_api/tests/`.

## Recommended Approach

1. Add a workflow lifecycle correlation API in `web_api` that returns a timeline for a given `object_id` using existing `files_enriched`, `workflows`, `findings`, `transforms`, and `enrichments` data.
2. Extend observability response models in `projects/web_api/web_api/models/responses.py` so status and lifecycle payloads are explicit and stable for dashboard consumption.
3. Add service-health aggregation and queue/workflow threshold summaries in `web_api`, then consume them in the dashboard (`StatsOverview.jsx`) as operator-first cards/tables.
4. Implement sustained-condition alert emission using existing alert pubsub wiring instead of introducing a new alert transport.
5. Add dedicated API tests for lifecycle correlation, threshold evaluation, and alert gating/cooldown behavior.

## Risks and Mitigations

- **Risk:** Alert fatigue from noisy backlog spikes.
  - **Mitigation:** Require sustained duration + cooldown dedupe before publishing operational alerts.
- **Risk:** Dashboard regressions from expanded polling payloads.
  - **Mitigation:** Keep API payloads bounded and add fallback rendering for unavailable signals.
- **Risk:** Query overhead on large `workflows` tables.
  - **Mitigation:** Reuse existing indexed fields (`object_id`, active-status partial index) and avoid full-table scans in new endpoints.

## Validation Architecture

- API contract tests in `projects/web_api/tests/test_workflow_observability.py` for:
  - object lifecycle correlation payloads
  - queue/workflow summary threshold behavior
  - sustained-condition alert publish gating
- Frontend build validation (`cd projects/frontend && npm run build`) after dashboard updates.
- Manual operator smoke check:
  - submit file -> retrieve lifecycle by `object_id`
  - verify dashboard cards reflect queue/workflow/service health
  - verify sustained backlog/failure triggers one alert per cooldown window.

## Outputs Expected from This Phase

- Object-level lifecycle observability endpoint(s) in `web_api`
- Dashboard enhancements for queue/workflow/service-health operations
- Sustained operational alert routing built on existing alerting pubsub
- Web API observability-focused regression tests

---
*Phase research complete: 2026-02-25*
