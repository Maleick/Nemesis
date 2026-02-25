---
phase: 04-end-to-end-quality-gates
plan: 02
subsystem: testing
tags: [profiles, frontend, vitest, ci, smoke]
requires:
  - phase: 04-end-to-end-quality-gates
    provides: backend smoke gate and CI wiring from 04-01
provides:
  - profile-aware `nemesis-ctl` readiness smoke contracts
  - frontend critical-path smoke harness and route tests
  - CI fast-gate enforcement for profile and frontend smoke checks
affects: [phase-04-03, ci-fast-gate, operator-workflows]
tech-stack:
  added: [vitest, jsdom, @testing-library/react, @testing-library/jest-dom]
  patterns: [shell-profile-contract-tests, mocked-frontend-route-smoke]
key-files:
  created:
    - tools/tests/test_nemesis_ctl_profiles.sh
    - projects/frontend/vitest.config.js
    - projects/frontend/src/test/setup.js
    - projects/frontend/src/__tests__/app_navigation_smoke.test.jsx
    - projects/frontend/src/__tests__/result_view_smoke.test.jsx
  modified:
    - tools/nemesis-ctl.sh
    - projects/frontend/package.json
    - projects/frontend/package-lock.json
    - .github/workflows/ci-fast.yml
key-decisions:
  - "Added shell smoke tests around a fake docker shim so profile readiness logic is validated without real containers."
  - "Frontend smoke tests mock heavy route dependencies and focus on navigation/result-view contract paths for deterministic CI runtime."
patterns-established:
  - "Profile-specific readiness assertions are tested through tooling contracts before compose/runtime execution."
  - "Frontend critical-path smoke checks run in jsdom with explicit network and subscription stubs."
requirements-completed: [TEST-02, TEST-03]
duration: 6 min
completed: 2026-02-25
---

# Phase 4 Plan 02 Summary

**Profile-aware readiness contracts and frontend critical-path smoke tests now gate pull requests in CI**

## Performance

- **Duration:** 6 min
- **Started:** 2026-02-25T19:38:00Z
- **Completed:** 2026-02-25T19:44:26Z
- **Tasks:** 3
- **Files modified:** 9

## Accomplishments
- Added deterministic profile smoke tests for `nemesis-ctl` status behavior across `base`, `monitoring`, and `llm` modes.
- Added Vitest/jsdom frontend smoke harness with route-level checks for dashboard navigation and result-view object routing.
- Updated CI fast gate to run profile smoke checks and frontend smoke+build commands.

## Task Commits

1. **Task 1: Add profile-aware readiness smoke contracts for nemesis-ctl** - `935d5bd` (test)
2. **Task 2: Introduce frontend smoke harness and critical navigation/result-view tests** - `629d4ca` (test)
3. **Task 3: Integrate profile and frontend smoke checks into CI fast gate** - `327bd1c` (ci)

## Files Created/Modified
- `tools/tests/test_nemesis_ctl_profiles.sh` - Added profile readiness smoke suite with a fake docker shim.
- `tools/nemesis-ctl.sh` - Fixed llm-only env-prefix handling so `status --llm` executes correctly.
- `projects/frontend/vitest.config.js` - Added smoke test runner configuration for jsdom.
- `projects/frontend/src/test/setup.js` - Added deterministic browser/network stubs for route smoke tests.
- `projects/frontend/src/__tests__/app_navigation_smoke.test.jsx` - Added dashboard/upload/files navigation smoke checks.
- `projects/frontend/src/__tests__/result_view_smoke.test.jsx` - Added `/files/:objectId` result-view route smoke check.
- `projects/frontend/package.json` and `projects/frontend/package-lock.json` - Added smoke test script and dependencies.
- `.github/workflows/ci-fast.yml` - Added profile and frontend smoke steps.

## Decisions Made
- Kept shell smoke tests dependency-free by stubbing `docker` instead of requiring running compose services.
- Scoped frontend smoke tests to critical navigation and result-view route behavior, with deterministic mocks for fetch and websocket subscriptions.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed `nemesis-ctl status --llm` command prefix handling**
- **Found during:** Task 1 (profile smoke contracts)
- **Issue:** llm-only profile mode built a prefix without `env`, causing command execution failure.
- **Fix:** ensured llm mode initializes `CMD_PREFIX` with `env` before appending `PHOENIX_ENABLED=...`.
- **Files modified:** `tools/nemesis-ctl.sh`
- **Verification:** `bash tools/tests/test_nemesis_ctl_profiles.sh`
- **Committed in:** `935d5bd`

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Critical correctness fix and no scope expansion.

## Issues Encountered

- Initial smoke setup surfaced a `localStorage.clear` compatibility issue in test setup; resolved by adding a fallback localStorage shim in `src/test/setup.js`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

TEST-02 and TEST-03 are CI-enforced, enabling queue/topic/payload contract gate implementation in 04-03.

## Self-Check: PASSED

---
*Phase: 04-end-to-end-quality-gates*
*Completed: 2026-02-25*
