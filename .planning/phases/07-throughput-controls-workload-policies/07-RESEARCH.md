# Phase 7 Research: Throughput Controls & Workload Policies

**Phase:** 07 Throughput Controls & Workload Policies  
**Researched:** 2026-02-25  
**Status:** Complete  
**Requirement IDs:** SCALE-01, SCALE-02

## Objective

Produce implementation-ready planning input for queue-pressure-driven throughput controls and workload throttling that preserves baseline workflow responsiveness under high volume.

## Context and Constraints

- Locked planning shape: exactly 2 plans in 2 waves (`07-01` then `07-02`).
- Locked operator surface: CLI + API only (no dashboard/frontend scope in Phase 7).
- Locked infra scope: docs/validation only for Dapr/RabbitMQ tuning (no direct `infra/dapr/components/pubsub/*.yaml` edits in this phase).
- Phase context is present in `.planning/phases/07-throughput-controls-workload-policies/07-CONTEXT.md` and is treated as binding.

## Source Surfaces Reviewed

- `.planning/phases/07-throughput-controls-workload-policies/07-CONTEXT.md`
- `.planning/ROADMAP.md`
- `.planning/REQUIREMENTS.md`
- `.planning/STATE.md`
- `projects/web_api/web_api/main.py`
- `projects/web_api/web_api/queue_monitor.py`
- `projects/web_api/web_api/models/responses.py`
- `projects/file_enrichment/file_enrichment/subscriptions/file.py`
- `projects/document_conversion/document_conversion/workflow_manager.py`
- `tools/nemesis-ctl.sh`
- `tools/test.sh`
- `docs/performance.md`
- `projects/file_enrichment/tests/benchmarks/bench_basic_analysis.py`
- `projects/file_enrichment/tests/benchmarks/README.md`
- `projects/web_api/tests/test_workflow_observability.py`

## Baseline Findings

1. Queue pressure signals already exist in `web_api` observability (`_get_observability_thresholds`, `_build_observability_summary_payload`, `_evaluate_observability_alerts`) and provide sustained-window + cooldown semantics for alerting, but not runtime throughput policy actuation.
2. `file_enrichment` currently uses static `MAX_PARALLEL_WORKFLOWS` and a bounded in-process queue (`asyncio.Queue(maxsize=NUM_WORKERS)`) in `subscriptions/file.py`; there is no class-aware throttling or operator override path.
3. `document_conversion` currently uses static semaphore concurrency (`asyncio.Semaphore(max_parallel_workflows)`) in `workflow_manager.py`; there is no queue-pressure policy mode or per-class floor behavior.
4. `web_api` has observability summary/alert endpoints, but lacks explicit throughput-policy status/control contracts in `responses.py` + `main.py`.
5. `nemesis-ctl.sh` currently exposes `start|status|stop|clean` and profile flags, but no throughput-policy preset/override/status commands.
6. Docs contain benchmark baseline guidance and observability triage sequence, but no explicit evidence bundle contract that combines benchmark compare + queue-drain metrics + operator status snapshots with rollback triggers.

## Throughput Trigger/Threshold Model

### Existing signal model

- Queue backlog and sustained/cooldown thresholds are centralized in `web_api` (`OBS_QUEUE_BACKLOG_*`, `OBS_SUSTAINED_DURATION_SECONDS`, `OBS_ALERT_COOLDOWN_SECONDS`).
- Queue metrics are aggregated by `WorkflowQueueMonitor.get_workflow_queue_metrics()` with `bottleneck_queues`, `queues_without_consumers`, and per-topic details.

### Gaps

- Thresholds are global and alert-oriented, not policy-profile oriented with per-queue defaults.
- No fail-safe throttling mode is activated when telemetry is stale/unavailable.
- No shared policy state between queue consumers (`file_enrichment` and `document_conversion`).

### Planning direction

- Reuse queue-pressure-first signals from current observability path.
- Add named policy presets with per-queue threshold defaults and sustained/cooldown gates for runtime action.
- Introduce explicit conservative fail-safe mode with operator-visible warning state when telemetry cannot be trusted.

## Tiered Workload Class Strategy

### Existing behavior

- Work intake is queue/topic based and not currently mapped to explicit workload classes.
- Concurrency control is global per service (`NUM_WORKERS`, `workflow_semaphore`) and does not differentiate expensive classes.

### Gaps

- No policy-class abstraction to separate baseline versus expensive workload handling.
- No anti-starvation floor for expensive workloads under pressure.

### Planning direction

- Define tiered workload classes backed by policy data (curated defaults + operator overrides).
- Under pressure: reduce parallelism and defer admissions for expensive class first.
- Enforce minimum floor capacity for expensive class to prevent total starvation.

## API + CLI Operator Control/Status Contract Options

### API baseline

- Existing observability routes:
  - `GET /workflows/observability/summary`
  - `POST /workflows/observability/alerts/evaluate`
- Existing response models support queue/workflow/health severity summaries only.

### CLI baseline

- `nemesis-ctl.sh` supports profile-aware startup/readiness, but no policy controls.

### Planning direction

- Phase 7 API contract additions should expose throughput policy status and control primitives (preset mode, override TTL metadata, per-class active state, fail-safe reason).
- CLI should provide deterministic wrappers for policy status and override lifecycle via `nemesis-ctl` command surface.
- Keep scope strictly API/CLI; do not introduce dashboard components.

## Acceptance Evidence Architecture (Benchmark + Queue + Status)

### Required evidence bundle (locked)

1. Benchmark compare evidence from repeatable stress profile (`bench_basic_analysis.py` baseline/compare workflow).
2. Queue-drain metrics evidence (queue backlog deltas and bottleneck topics from observability/queue APIs).
3. Operator status snapshots (policy mode + per-class active state via API/CLI status output).

### Current readiness

- Benchmark save/compare workflows already exist in docs/benchmark README.
- Queue metrics and observability endpoints already provide machine-readable telemetry.
- Missing: a deterministic gate combining these into one acceptance policy and rollback trigger checks.

## Rollback Trigger Model

### Required rollback contract

- Mandatory rollback triggers when critical regression indicators are observed.
- Explicit revert path for policy mode/override and throughput knobs.

### Suggested trigger classes for planning

- Critical health degradation while policy override active.
- Queue drain deterioration over sustained window compared to baseline profile.
- Throughput KPI regression beyond declared acceptable threshold for the selected workload profile.

### Planning direction

- Add operator runbook and deterministic validation script coverage for rollback triggers and explicit revert commands.

## Scope Guardrails to Enforce in Plans

- No frontend/dashboard file modifications.
- No direct edits to `infra/dapr/components/pubsub/*.yaml`.
- Dapr/RabbitMQ tuning work is limited to docs/validation and policy guidance.

## Recommended Plan Split

### Plan 07-01 (Wave 1, SCALE-01)

- Implement queue-pressure trigger model, profile presets with per-queue defaults, sustained/cooldown behavior, and fail-safe conservative mode across runtime + API status contracts.
- Primary files: `file.py`, `workflow_manager.py`, `web_api/main.py`, `web_api/models/responses.py` (+ focused regression tests).

### Plan 07-02 (Wave 2, SCALE-02, depends on 07-01)

- Implement tiered-class throttling controls with anti-starvation floor, config + `nemesis-ctl` control/status path, TTL override lifecycle, acceptance-evidence gate, and rollback guardrails.
- Primary files: `tools/nemesis-ctl.sh`, `tools/tests/test_throughput_policy_controls.sh`, `docs/performance.md`, `docs/troubleshooting.md`, `docs/usage_guide.md`, benchmark docs/assets.

## Validation Architecture

### Gate 1: Throughput trigger and status contract

```bash
cd /opt/Nemesis/projects/web_api && uv run pytest tests/test_workflow_observability.py tests/test_throughput_policy_status.py -q
cd /opt/Nemesis/projects/file_enrichment && uv run pytest tests/test_queue_pressure_policies.py -q
cd /opt/Nemesis/projects/document_conversion && uv run pytest tests/test_workflow_manager_policy.py -q
```

### Gate 2: Operator control and rollback gate

```bash
cd /opt/Nemesis && bash tools/tests/test_throughput_policy_controls.sh
cd /opt/Nemesis && rg -n "throughput policy|preset|override ttl|rollback|queue-drain|status snapshot" docs/performance.md docs/troubleshooting.md docs/usage_guide.md
```

### Gate 3: Evidence bundle repeatability

```bash
cd /opt/Nemesis/projects/file_enrichment && uv run pytest tests/benchmarks/bench_basic_analysis.py --benchmark-only --benchmark-save=phase7_baseline
cd /opt/Nemesis/projects/file_enrichment && uv run pytest tests/benchmarks/bench_basic_analysis.py --benchmark-only --benchmark-compare=phase7_baseline
cd /opt/Nemesis && rg -n "workflows/observability/summary|/queues|nemesis-ctl.sh status" docs/performance.md docs/troubleshooting.md
```

---
*Phase research complete: 2026-02-25*
