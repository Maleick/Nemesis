---
phase: 04-end-to-end-quality-gates
plan: 03
subsystem: testing
tags: [queues, contracts, pubsub, ci, dapr]
requires:
  - phase: 04-end-to-end-quality-gates
    provides: CI smoke-gate baseline from 04-01 and 04-02
provides:
  - canonical queue/topic contract metadata in shared common library
  - producer/consumer boundary contract tests across web_api, file_enrichment, and alerting
  - dedicated queue-contract quality gate in shared tooling and CI
affects: [ci-fast-gate, workflow-observability, cross-service-integrations]
tech-stack:
  added: []
  patterns: [centralized-queue-contract-catalog, cross-service-topic-contract-tests]
key-files:
  created:
    - libs/common/tests/test_queue_topic_contracts.py
    - projects/web_api/tests/test_queue_topic_contracts.py
    - projects/file_enrichment/tests/test_queue_topic_contracts.py
    - projects/alerting/tests/test_queue_topic_contracts.py
  modified:
    - libs/common/common/queues.py
    - projects/web_api/web_api/queue_monitor.py
    - tools/test.sh
    - .github/workflows/ci-fast.yml
key-decisions:
  - "Established shared queue contract metadata (pubsub/topic/producers/consumers/payload keys) as the source of truth in common/queues.py."
  - "Enforced queue-contract checks through shared tooling so CI and local runs execute the same contract gate."
patterns-established:
  - "Queue monitoring topic-to-queue mapping is now derived from canonical shared contract helpers."
  - "Cross-service queue contract tests validate topic binding and minimal payload compatibility assumptions before merge."
requirements-completed: [TEST-04]
duration: 5 min
completed: 2026-02-25
---

# Phase 4 Plan 03 Summary

**Queue/topic/payload contracts are now centrally defined and CI-enforced across web_api, file_enrichment, and alerting boundaries**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-25T19:45:00Z
- **Completed:** 2026-02-25T19:49:54Z
- **Tasks:** 3
- **Files modified:** 8

## Accomplishments
- Added canonical queue/topic contract metadata and helper APIs in `libs/common/common/queues.py`.
- Added service-owned queue contract tests for producer/consumer boundaries and payload-shape expectations.
- Added `--queue-contract` mode to `tools/test.sh` and wired it into `ci-fast`.

## Task Commits

1. **Task 1: Define and expose canonical queue/topic contract metadata** - `6c8daad` (feat)
2. **Task 2: Add queue/topic/payload contract tests per service boundary** - `e5a3f38` (test)
3. **Task 3: Enforce queue contract checks in shared tooling and CI fast gate** - `b07bb77` (ci)

## Files Created/Modified
- `libs/common/common/queues.py` - Added structured queue contract catalog and topic-to-queue helper mappings.
- `libs/common/tests/test_queue_topic_contracts.py` - Added shared contract metadata unit coverage.
- `projects/web_api/tests/test_queue_topic_contracts.py` - Added queue monitor and publisher contract tests.
- `projects/file_enrichment/tests/test_queue_topic_contracts.py` - Added producer/consumer boundary and payload-key assertions.
- `projects/alerting/tests/test_queue_topic_contracts.py` - Added alerting subscription and payload contract checks.
- `projects/web_api/web_api/queue_monitor.py` - Switched topic mapping to canonical shared helper.
- `tools/test.sh` - Added `--queue-contract` gate.
- `.github/workflows/ci-fast.yml` - Added queue-contract CI step.

## Decisions Made
- Treated queue contracts as first-class shared metadata to reduce drift between producers, consumers, and observability mapping.
- Kept contract tests service-local so failures point to the owning boundary quickly.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed queue monitor drift for `document_conversion_input` queue naming**
- **Found during:** Task 2 (web_api queue contract test gate)
- **Issue:** `WorkflowQueueMonitor.TOPIC_TO_QUEUE_MAPPING` used `files-document_conversion_input`, which diverged from canonical pubsub/topic binding.
- **Fix:** derive mapping from shared queue contract helper values in `common.queues`.
- **Files modified:** `projects/web_api/web_api/queue_monitor.py`
- **Verification:** `cd projects/web_api && uv run pytest tests/test_queue_topic_contracts.py -q`
- **Committed in:** `e5a3f38`

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Improved correctness and removed existing contract drift; no scope expansion.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

TEST-04 is CI-enforced and queue contract drift is now detected automatically, completing Phase 4 quality-gate objectives.

## Self-Check: PASSED

---
*Phase: 04-end-to-end-quality-gates*
*Completed: 2026-02-25*
