# Phase 6 Research: Extension Contracts & Performance

**Phase:** 06 Extension Contracts & Performance
**Researched:** 2026-02-25
**Status:** Complete
**Requirement IDs:** EXT-01, EXT-02

## Objective

Define implementation-ready planning input that standardizes extension onboarding contracts and introduces measurable workflow-throughput baseline and tuning guardrails without destabilizing core behavior.

## Context and Constraints

- `06-CONTEXT.md` is intentionally absent for this pass; planning proceeds with roadmap, requirements, and repository evidence.
- `branching_strategy=none`; execution will remain on `main`.
- `workflow.auto_advance=false`; planning output must end at docs commit.

## Source Surfaces Reviewed

- `.planning/ROADMAP.md`
- `.planning/REQUIREMENTS.md`
- `.planning/STATE.md`
- `docs/file_enrichment_modules.md`
- `libs/file_enrichment_modules/DEVELOPMENT_GUIDE.md`
- `projects/file_enrichment/file_enrichment/workflow.py`
- `projects/file_enrichment/file_enrichment/routes/enrichments.py`
- `libs/file_enrichment_modules/tests/harness/harness.py`
- `projects/cli/cli/config.py`
- `projects/cli/cli/main.py`
- `projects/cli/tests/test_config.py`
- `projects/cli/tests/test_sync.py`
- `projects/cli/settings_mythic.yaml`
- `projects/cli/settings_outflank.yaml`
- `projects/cli/settings_cobaltstrike.yaml`
- `docs/performance.md`
- `projects/file_enrichment/tests/benchmarks/README.md`
- `projects/file_enrichment/tests/benchmarks/bench_basic_analysis.py`

## Current Extension Onboarding Journey

1. Module authors start in `docs/file_enrichment_modules.md`, then often pivot to `libs/file_enrichment_modules/DEVELOPMENT_GUIDE.md` for detailed protocol and harness usage.
2. Runtime loading behavior is defined in `projects/file_enrichment/file_enrichment/workflow.py` (`ModuleLoader`, dependency graph, topological ordering, workflow filter by `workflows`).
3. Manual module execution path exists via `projects/file_enrichment/file_enrichment/routes/enrichments.py` (`/enrichments/{enrichment_name}`) and CLI helper `projects/cli/cli/module_runner.py`.
4. Connector onboarding is documented in `projects/cli/README.md` and bootstrapped with YAML templates in `projects/cli/settings_*.yaml` files.
5. Config schema enforcement is implemented in `projects/cli/cli/config.py` and validated via `projects/cli/tests/test_config.py` and `projects/cli/tests/test_sync.py`.
6. Performance guidance exists in `docs/performance.md`, and benchmark tooling exists in `projects/file_enrichment/tests/benchmarks/`.

## Contract Gap Inventory

| ID | Gap | Evidence | Impact |
|----|-----|----------|--------|
| CG-01 | Onboarding guidance is split between two docs with different depth and no single canonical checklist. | `docs/file_enrichment_modules.md` has lightweight steps; `libs/file_enrichment_modules/DEVELOPMENT_GUIDE.md` has full protocol details. | New module onboarding quality depends on individual interpretation. |
| CG-02 | No deterministic docs gate protects extension contract language from drift. | No script under `tools/tests/` currently checks extension onboarding docs. | Contract regressions can slip through doc edits unnoticed. |
| CG-03 | Connector onboarding docs are command-centric but lack explicit preflight validation workflow before runtime connection. | `projects/cli/README.md` explains commands and config files but no dedicated "validate config before connect" contract. | Miswired configs fail later during runtime instead of preflight. |
| CG-04 | Outflank settings example references stale key naming in comments. | `projects/cli/settings_outflank.yaml` comment mentions `outflank_upload_path`, while schema field is `downloads_dir_path` in `projects/cli/cli/config.py`. | Increased probability of invalid config keys and onboarding confusion. |
| CG-05 | Throughput guidance is broad but not anchored to a repeatable benchmark baseline runbook. | `docs/performance.md` offers tuning advice; `projects/file_enrichment/tests/benchmarks/README.md` documents benchmark usage but not a phase-level baseline and compare contract. | Performance tuning can be subjective and difficult to verify over time. |
| CG-06 | Benchmark scope centers on `process_basic_analysis` but lacks explicit linkage to workflow throughput decision-making. | `bench_basic_analysis.py` measures isolated basic analysis function and intentionally avoids full runtime side effects. | Operators may treat micro-benchmark changes as system throughput proof without guardrails. |

## Connector Miswiring Risk Matrix

| Risk ID | Failure Mode | Evidence | Prevention Direction |
|---------|--------------|----------|----------------------|
| RM-01 | Wrong YAML keys for connector-specific options | `projects/cli/settings_outflank.yaml` comment/key mismatch vs `downloads_dir_path` model field | Add explicit schema-key mapping docs and config validation/preflight flow. |
| RM-02 | URL formatting errors (query/fragment, missing host/protocol) | `StrictHttpUrl` in `projects/cli/cli/config.py`; tests in `projects/cli/tests/test_config.py` | Surface frequent validation failures in connector onboarding docs with remediation examples. |
| RM-03 | Mythic auth mode confusion (token vs username/password) | Union credential handling in `projects/cli/cli/config.py` and tests in `test_config.py` | Add a canonical credential matrix and validation-first steps before connector launch. |
| RM-04 | Runtime failure discovered late in sync loop | `SyncService` initialization guard behavior in `projects/cli/tests/test_sync.py` | Promote preflight checks that validate config structure and connector readiness before long-running sync. |
| RM-05 | Inconsistent template expectations across connectors | Separate settings templates in `projects/cli/settings_*.yaml` with differing optional guidance depth | Align template comments/fields and README onboarding contract. |

## Throughput Baseline & Bottleneck Hypotheses

### Baseline Facts

- `docs/performance.md` identifies queue-backed bottlenecks and tuning levers for file_enrichment, document_conversion, and noseyparker workers.
- `projects/file_enrichment/tests/benchmarks/bench_basic_analysis.py` provides deterministic local benchmarks for file metadata/hash extraction path.
- `projects/file_enrichment/tests/benchmarks/README.md` already supports benchmark save/compare workflows (`--benchmark-save`, `--benchmark-compare`).

### Hypotheses (workflow throughput focus)

1. **H-01:** Introducing a standard benchmark capture-and-compare runbook for basic analysis path will reduce ambiguity when evaluating throughput tuning changes.
2. **H-02:** Explicitly linking queue-level tuning guidance (`ENRICHMENT_MAX_PARALLEL_WORKFLOWS`, `DOCUMENTCONVERSION_MAX_PARALLEL_WORKFLOWS`) to baseline benchmark collection will improve tuning decision quality.
3. **H-03:** Throughput guardrails should separate micro-benchmark gains from end-to-end workflow gains to avoid over-claiming performance improvement.
4. **H-04:** A docs+test gate that enforces presence of baseline/tuning instructions can keep performance guidance current as tuning knobs evolve.

## Recommended Plan Split

### Plan 06-01 (Wave 1, EXT-01)

- Unify extension onboarding contract/checklist across `docs/file_enrichment_modules.md` and `libs/file_enrichment_modules/DEVELOPMENT_GUIDE.md`.
- Add deterministic docs-check script for extension contract requirements under `tools/tests/`.
- Ensure verification path references existing harness tests (`libs/file_enrichment_modules/tests/test_harness_integration.py`).

### Plan 06-02 (Wave 2, EXT-02, depends on 06-01)

- Add connector onboarding preflight validation guidance and schema-key alignment across `projects/cli/README.md` + settings examples + config validation surfaces.
- Add workflow-throughput baseline/tuning guardrail guidance via `docs/performance.md` and benchmark assets in `projects/file_enrichment/tests/benchmarks/`.
- Keep metrics claims measurable and command-backed.

## Risks and Mitigations

- **Risk:** Contract docs become stale as module protocol evolves.
  - **Mitigation:** Add deterministic docs check script and include it in plan verification checklist.
- **Risk:** Connector guidance changes but settings templates remain inconsistent.
  - **Mitigation:** Treat settings templates as part of plan file scope and add `rg`-based alignment checks.
- **Risk:** Benchmark changes interpreted as full workflow throughput proof.
  - **Mitigation:** Require explicit guardrail language separating micro-benchmark and end-to-end effects.

## Validation Architecture

### Gate 1: Extension contract integrity

```bash
cd /opt/Nemesis && bash tools/tests/test_extension_contract_docs.sh
cd /opt/Nemesis && rg -n "create_enrichment_module|should_process|process|workflows|verification checklist" docs/file_enrichment_modules.md libs/file_enrichment_modules/DEVELOPMENT_GUIDE.md
cd /opt/Nemesis/libs/file_enrichment_modules && uv run pytest tests/test_harness_integration.py -q
```

### Gate 2: Connector schema/onboarding alignment

```bash
cd /opt/Nemesis/projects/cli && uv run pytest tests/test_config.py tests/test_sync.py -q
cd /opt/Nemesis && rg -n "downloads_dir_path|validate|connect-outflank|connect-mythic|connect-cobaltstrike" projects/cli/README.md projects/cli/settings_outflank.yaml projects/cli/settings_mythic.yaml projects/cli/settings_cobaltstrike.yaml projects/cli/cli/config.py
```

### Gate 3: Throughput baseline and tuning guardrails

```bash
cd /opt/Nemesis/projects/file_enrichment && uv run pytest tests/benchmarks/bench_basic_analysis.py --benchmark-only
cd /opt/Nemesis/projects/file_enrichment && uv run pytest tests/benchmarks/bench_basic_analysis.py --benchmark-only --benchmark-save=phase6_baseline
cd /opt/Nemesis && rg -n "ENRICHMENT_MAX_PARALLEL_WORKFLOWS|DOCUMENTCONVERSION_MAX_PARALLEL_WORKFLOWS|benchmark-save|benchmark-compare|throughput" docs/performance.md projects/file_enrichment/tests/benchmarks/README.md
```

## Planning Notes for Executor Compatibility

- Plans must preserve wave/dependency semantics for `$gsd-execute-phase 6` (`06-01` before `06-02`).
- `EXT-01` and `EXT-02` IDs must appear in plan frontmatter and verification sections.
- `06-02` must include measurable throughput baseline/tuning outcomes in `must_haves.truths` and verification commands.

---
*Phase research complete: 2026-02-25*
