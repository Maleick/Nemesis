# Codebase Concerns

**Analysis Date:** 2026-02-25

## Tech Debt

**Large monolithic service modules:**
- Issue: core service files carry many responsibilities and long route/task sections.
- Files: `projects/web_api/web_api/main.py`, `projects/housekeeping/housekeeping/main.py`, `projects/alerting/alerting/main.py`.
- Impact: harder reviewability, slower onboarding, higher regression risk during edits.
- Fix approach: split by bounded context (routing, query services, orchestration, background workers).

**Import-time side effects in service modules:**
- Issue: initialization logic triggers external clients/secrets during import in several modules.
- Files: `projects/web_api/web_api/main.py`, `libs/common/common/storage.py`, `projects/agents/agents/main.py`, `projects/alerting/alerting/main.py`.
- Impact: brittle tests and hidden startup dependencies.
- Fix approach: move side effects into explicit startup factories/lifespan hooks.

**Compose topology complexity:**
- Issue: one large `compose.yaml` combines core, monitoring, and llm profiles plus many sidecars.
- File: `compose.yaml`.
- Impact: cognitive overhead and misconfiguration risk for operators.
- Fix approach: keep profile docs tight, consider factoring role-specific compose fragments.

## Known Bugs / Reliability Risks

**Startup ordering sensitivity:**
- Symptoms: optional services (especially llm profile) rely on dependent services becoming healthy in time.
- Trigger: cold start, token/auth mismatch, or delayed dependency boot.
- Evidence: health/preflight/retry logic in `projects/alerting/alerting/main.py` and `projects/agents/agents/auth_provider.py`.
- Mitigation: keep robust health checks, retries, and explicit readiness dashboards.

**Cross-service coupling through shared infra assumptions:**
- Symptoms: service failures can cascade when queue/db/secret store assumptions drift.
- Trigger: changed env vars, secret names, topic names, or sidecar config.
- Evidence: shared constants + Dapr secret retrieval (`libs/common/common/queues.py`, `libs/common/common/db.py`).
- Mitigation: add stricter startup assertions and compatibility checks per service.

## Security Considerations

**Sensitive value logging risk:**
- Risk: some startup log messages include secret-derived material.
- Files: `projects/alerting/alerting/main.py` (logs Hasura secret value), `projects/agents/agents/main.py` (secret retrieval logs).
- Current mitigation: service-level logging infrastructure exists, but not all secret-adjacent logs are sanitized.
- Recommendation: remove/redact any secret values from logs and add lint checks for obvious secret-log patterns.

**Development defaults in env template:**
- Risk: `env.example` includes placeholder credential values that may be copied unchanged into deployments.
- File: `env.example`.
- Current mitigation: comments indicate these are configurable; no enforcement at startup.
- Recommendation: enforce first-run secret rotation checks and document minimum password policy.

## Performance Bottlenecks

**CPU-heavy enrichment modules:**
- Problem: OCR, YARA, archive extraction, PE/registry parsing can spike CPU/memory under load.
- Evidence: module mix in `libs/file_enrichment_modules/pyproject.toml`, compose resource hints for selected services.
- Improvement path: tune parallel workflow counts, profile high-cost modules, and isolate heavy workloads by queue.

**Database pressure under concurrent workflows:**
- Problem: enrichment/conversion workflows rely on frequent DB operations and status tracking.
- Files: `projects/file_enrichment/file_enrichment/controller.py`, `projects/document_conversion/document_conversion/main.py`.
- Improvement path: pool tuning by profile, query indexing review, and workload partitioning.

## Fragile Areas

**Dapr topic wiring:**
- Why fragile: topic names must align across code constants and `infra/dapr/components/pubsub/*.yaml`.
- Common failures: silent no-op processing or dropped subscriptions when names drift.
- Safe modification: update constants and Dapr component config in one change set; validate with integration smoke tests.

**Hasura subscription loops:**
- Why fragile: long-lived websocket subscriptions are sensitive to auth and schema drift.
- Files: `projects/alerting/alerting/main.py`, `projects/agents/agents/main.py`.
- Safe modification: keep reconnection logic and add explicit subscription health metrics.

## Scaling Limits

**Single-node compose baseline:**
- Current capacity: tuned for local/dev and moderate workloads, not multi-node distributed scaling.
- Limit symptoms: queue growth, delayed enrichments, and memory pressure under heavy ingestion.
- Scaling path: horizontal replicas for enrichment workers, queue partitioning, and eventual orchestrator migration if needed.

## Dependencies at Risk

**Pre-release/edge dependencies:**
- Risk: alpha or fast-moving dependencies may introduce instability.
- Example: `durabletask-dapr==0.2.0a8` in `projects/file_enrichment/pyproject.toml`.
- Migration path: track stable releases and pin to tested versions in lock updates.

## Test Coverage Gaps

**Frontend automated tests not obvious in repo layout:**
- Risk: UI regressions may escape Python-centric CI checks.
- Evidence: no dedicated frontend test commands in `tools/test.sh`.
- Priority: Medium.
- Recommendation: add frontend unit/integration test job in CI.

**Cross-service e2e workflow coverage:**
- Risk: compose-level event chain regressions can surface only at runtime.
- Evidence: strong unit tests, but limited full-pipeline automated validation.
- Priority: High for release confidence.
- Recommendation: add smoke/e2e workflow checks (upload -> enrichment -> alert/report paths).

---

*Concerns audit: 2026-02-25*
*Update as issues are fixed or new risks emerge*
