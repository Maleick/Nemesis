---
phase: 04-end-to-end-quality-gates
plan: 01
subsystem: testing
tags: [smoke, web-api, ci, contracts, workflow]
requires:
  - phase: 03-security-auth-hardening
    provides: deterministic auth/readiness baseline for quality-gate expansion
provides:
  - backend smoke suite for upload -> workflow lifecycle -> retrieval contract
  - shared test tooling flag for backend smoke execution
  - CI fast-gate enforcement of backend smoke checks
affects: [phase-04-02, phase-04-03, ci-fast-gate]
tech-stack:
  added: []
  patterns: [deterministic-api-smoke-tests, ci-shared-smoke-invocation]
key-files:
  created:
    - projects/web_api/tests/test_ingestion_workflow_smoke.py
  modified:
    - projects/web_api/tests/conftest.py
    - tools/test.sh
    - .github/workflows/ci-fast.yml
    - docs/usage_guide.md
key-decisions:
  - "Smoke coverage uses mocked submit/lifecycle dependencies to avoid Dapr/RabbitMQ coupling while still validating API contracts."
  - "Backend smoke invocation is centralized in tools/test.sh so CI and local workflows run the same gate."
patterns-established:
  - "Upload, lifecycle, and retrieval API contracts are validated together in one deterministic smoke path."
  - "CI quality gates call shared tooling flags instead of duplicating test command strings in workflow YAML."
requirements-completed: [TEST-01]
duration: 3 min
completed: 2026-02-25
---

# Phase 4 Plan 01 Summary

**Deterministic backend smoke gates now enforce upload submission, workflow lifecycle correlation, and retrieval behavior in CI**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-25T19:34:56Z
- **Completed:** 2026-02-25T19:37:35Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments
- Added backend smoke tests that validate ingestion upload response contracts, workflow lifecycle correlation payloads, and retrieval range responses.
- Added `--smoke-backend` mode to shared test tooling for deterministic local/CI invocation.
- Integrated backend smoke execution into `ci-fast` and documented the command in the usage guide.

## Task Commits

1. **Task 1: Add backend ingestion/workflow/retrieval smoke tests** - `8583fe9` (test)
2. **Task 2: Expose a dedicated smoke mode in shared test tooling** - `4e2b811` (chore)
3. **Task 3: Integrate backend smoke gate into CI fast workflow** - `fb746c2` (ci)

## Files Created/Modified
- `projects/web_api/tests/test_ingestion_workflow_smoke.py` - Added upload/lifecycle/retrieval smoke contract tests with deterministic stubs.
- `projects/web_api/tests/conftest.py` - Added upload default return value for shared storage fixture.
- `tools/test.sh` - Added `--smoke-backend` mode to run the backend smoke suite.
- `.github/workflows/ci-fast.yml` - Added backend smoke step to PR fast gate.
- `docs/usage_guide.md` - Documented backend smoke gate usage.

## Decisions Made
- Kept smoke tests in `web_api` test scope with deterministic monkeypatches rather than introducing integration-test infrastructure.
- Used shared shell tooling as CI entrypoint to keep quality-gate commands stable and reusable.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

TEST-01 quality gate is in place and CI-enforced, enabling Wave 2 profile-aware and frontend smoke gate work.

## Self-Check: PASSED

---
*Phase: 04-end-to-end-quality-gates*
*Completed: 2026-02-25*
