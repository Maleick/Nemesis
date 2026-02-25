# Architecture Research (v1.1)

**Domain:** Throughput governance and AI policy controls
**Researched:** 2026-02-25
**Confidence:** HIGH

## Current Architecture Fit

The existing event-driven architecture can absorb v1.1 changes without introducing new core infrastructure. The highest leverage changes are contracts and controls at existing integration points.

## Primary Integration Points

| Surface | Existing Role | v1.1 Change Direction |
|---------|---------------|-----------------------|
| `projects/file_enrichment/*` | Primary workflow throughput bottleneck | Add policy-aware workload controls and measurable tuning gates |
| `projects/document_conversion/*` | Secondary bottleneck for heavy content | Align max parallel workflow contracts and profile guidance |
| `projects/web_api/web_api/main.py` | Operator/system status + report synthesis routes | Add policy/cost/status contract surfaces for AI and throughput |
| `projects/frontend/src/components/*` | Analyst/operator visibility | Expose governance indicators and override pathways |
| `docs/performance.md` + runbooks | Existing tuning guidance | Convert guidance into milestone-locked operational contracts |

## Proposed Milestone Data Flow

```text
Queue metrics + benchmark baseline
  -> throughput policy evaluation
      -> service/runtime profile controls
          -> operator status + runbook actions

Report synthesis request
  -> policy mode + confidence contract
      -> operator review/override
          -> cost/governance summary signals
```

## Phase-Friendly Boundaries

1. Phase 7 should own throughput targets and throttling contract behavior.
2. Phase 8 should own deployment topology/capacity and scale runbooks.
3. Phase 9 should own AI governance contracts and cost/status UX wiring.

## Key Architectural Risks

- Contract drift between docs, runtime settings, and UI cues.
- Throughput tuning that improves micro-benchmarks but degrades queue drain behavior.
- AI governance UX that hides confidence or bypasses analyst control.

## Validation Commands

```bash
cd /opt/Nemesis && ./tools/test.sh --queue-contract
cd /opt/Nemesis/projects/file_enrichment && uv run pytest tests/benchmarks/bench_basic_analysis.py --benchmark-only
cd /opt/Nemesis/projects/web_api && uv run pytest -q
cd /opt/Nemesis/projects/frontend && npm run test:smoke && npm run build
```

---
*Architecture recommendation: contract-first incremental evolution on existing stack*
