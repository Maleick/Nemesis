# Stack Research (v1.1)

**Domain:** Nemesis scale controls and AI governance
**Researched:** 2026-02-25
**Confidence:** HIGH

## Recommended Stack Direction

Keep the current stack and add milestone-specific guardrail capabilities instead of introducing platform rewrites.

### Keep As-Is

| Component | Why |
|-----------|-----|
| Python + FastAPI services | Existing service surfaces already expose required control/observability endpoints. |
| Dapr workflows/pubsub | Current queue/workflow model supports adding throttling and policy logic incrementally. |
| PostgreSQL + Hasura | Existing query/reporting pathways can carry AI usage and throughput governance data. |
| RabbitMQ + MinIO | Existing scale bottlenecks are tunable through worker/prefetch/profile controls. |
| Frontend React dashboard | Existing triage/observability UI can absorb AI governance signals. |

### Additions for v1.1 (No stack replacement)

| Capability | Existing Surface | Suggested Addition |
|------------|------------------|--------------------|
| Throughput policy controls | `file_enrichment`, `document_conversion`, queue stats routes | Configurable guardrails for expensive modules and queue-pressure thresholds |
| Scale runbook contracts | `docs/performance.md`, benchmark harness | Baseline/compare contracts tied to operational acceptance checks |
| AI governance policy modes | report synthesis endpoints + reporting UI | Confidence thresholds and operator override metadata |
| AI usage/cost visibility | web_api reporting routes + dashboard | Budget-oriented counters and summary status panels |

## Libraries/Tooling to Reuse

- `pytest` + `pytest-benchmark` for throughput guardrail validation.
- Existing CLI/tooling patterns in `tools/test.sh` and `tools/nemesis-ctl.sh` for deterministic checks.
- Existing response model structure in `projects/web_api/web_api/models/responses.py` for status contracts.

## What Not To Add This Milestone

- No Kubernetes migration.
- No new message broker.
- No separate AI orchestration service.
- No broad auth/provider rewrite.

## Validation Commands

```bash
cd /opt/Nemesis/projects/file_enrichment && uv run pytest tests/benchmarks/bench_basic_analysis.py --benchmark-only
cd /opt/Nemesis/projects/web_api && uv run pytest -q
cd /opt/Nemesis/projects/frontend && npm run build
```

---
*Research focus: SCALE-* and AI-* requirements only*
