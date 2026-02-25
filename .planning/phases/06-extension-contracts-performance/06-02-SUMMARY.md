---
phase: 06-extension-contracts-performance
plan: 02
subsystem: cli-docs-performance
tags: [connector-preflight, config-validation, throughput-baseline, benchmark-guardrails]
requires:
  - phase: 06-extension-contracts-performance
    provides: extension contract/checklist baseline and docs-gate pattern from 06-01
provides:
  - connector preflight validation command and connector-specific validation helpers
  - validation-first connector onboarding runbook with schema-aligned settings guidance
  - measurable throughput baseline/save/compare guardrails in performance docs and benchmark assets
affects: [phase-06-verification, connector-onboarding, performance-tuning]
tech-stack:
  added: []
  patterns: [validation-first-onboarding, benchmark-baseline-guardrail]
key-files:
  created: []
  modified:
    - projects/cli/cli/config.py
    - projects/cli/cli/main.py
    - projects/cli/README.md
    - projects/cli/settings_mythic.yaml
    - projects/cli/settings_outflank.yaml
    - projects/cli/settings_cobaltstrike.yaml
    - docs/performance.md
    - projects/file_enrichment/tests/benchmarks/README.md
    - projects/file_enrichment/tests/benchmarks/bench_basic_analysis.py
key-decisions:
  - "Added a dedicated `validate-config` CLI command and connector-specific preflight helpers to catch miswiring before connector loops start."
  - "Aligned settings examples and README onboarding around explicit preflight-first command flow for connect-outflank/connect-mythic/connect-cobaltstrike."
  - "Made throughput guidance baseline-driven with benchmark-save/benchmark-compare commands and explicit micro-benchmark scope guardrails."
patterns-established:
  - "Connector onboarding now follows validate-first then connect execution."
  - "Performance tuning claims are tied to repeatable benchmark baselines plus queue-level validation."
requirements-completed: [EXT-02]
duration: 20 min
completed: 2026-02-25
---

# Phase 6 Plan 02 Summary

**Connector onboarding is now validation-first and throughput tuning is baseline-driven with benchmark guardrails**

## Performance

- **Duration:** 20 min
- **Started:** 2026-02-25T20:51:00Z
- **Completed:** 2026-02-25T21:11:00Z
- **Tasks:** 3
- **Files modified:** 9

## Accomplishments

- Added connector preflight validation helpers in `cli/config.py`, wired them in `cli/main.py`, and introduced `validate-config` for deterministic preflight checks.
- Published a dedicated README runbook for validate-config and connect-* command sequencing, and aligned settings examples (including `downloads_dir_path`).
- Added throughput baseline/save/compare guardrails in `docs/performance.md` and benchmark docs; fixed benchmark fixture resolution for deterministic `--benchmark-only` execution.

## Task Commits

1. **Task 1: Add connector config preflight validation contract and schema-key alignment** - `d8da772` (feat)
2. **Task 2: Publish connector onboarding validation runbook in CLI docs** - `3fec908` (docs)
3. **Task 3: Add workflow-throughput baseline and tuning guardrail guidance** - `48c9147` (docs/test)

## Files Created/Modified

- `projects/cli/cli/config.py` - Added connector alias resolution, section presence checks, and connector-specific preflight validators.
- `projects/cli/cli/main.py` - Added `validate-config` command and preflight checks before connector startup paths.
- `projects/cli/README.md` - Added validation-first connector onboarding section and command flow.
- `projects/cli/settings_outflank.yaml` - Corrected optional key guidance to `downloads_dir_path` and added preflight check hint.
- `projects/cli/settings_mythic.yaml` - Added preflight check hint.
- `projects/cli/settings_cobaltstrike.yaml` - Added preflight check hint.
- `docs/performance.md` - Added throughput baseline capture/compare workflow and guardrail interpretation notes.
- `projects/file_enrichment/tests/benchmarks/README.md` - Added benchmark baseline/tuning guardrail procedure.
- `projects/file_enrichment/tests/benchmarks/bench_basic_analysis.py` - Added fixture path resolver and scope metadata note for benchmark context.

## Decisions Made

- Kept preflight validation lightweight and deterministic (schema + connector section checks) so operators can run it on every startup.
- Explicitly documented that benchmark results are micro-benchmark signals, not standalone proof of end-to-end throughput.

## Deviations from Plan

### Auto-fixed Issues

**1. Missing benchmark fixture wiring surfaced during verification**
- **Found during:** Task 3 verification (`bench_basic_analysis.py --benchmark-only`)
- **Issue:** `get_file_path` fixture was undefined, causing benchmark collection failures.
- **Fix:** Added local benchmark fixture resolver inside `bench_basic_analysis.py`.
- **Files modified:** `projects/file_enrichment/tests/benchmarks/bench_basic_analysis.py`
- **Verification:** Benchmark command passed after fixture addition.

## Issues Encountered

- Local environment lacked LevelDB/libmagic dependencies for required verification commands. Installed Homebrew `leveldb` and `libmagic`, and installed `pytest-benchmark` into the local file_enrichment virtual environment.
- CLI config tests required compiler include/library path hints (`CPATH=/opt/homebrew/include LIBRARY_PATH=/opt/homebrew/lib`) for local `plyvel-ci` build.

## User Setup Required

None.

## Next Phase Readiness

EXT-02 connector onboarding and throughput guardrails are complete; phase can proceed to verifier and phase completion updates.

## Self-Check: PASSED

---
*Phase: 06-extension-contracts-performance*
*Completed: 2026-02-25*
