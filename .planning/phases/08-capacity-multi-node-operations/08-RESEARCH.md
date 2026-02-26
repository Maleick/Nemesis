# Phase 8 Research: Capacity & Multi-Node Operations

**Phase:** 08 Capacity & Multi-Node Operations  
**Researched:** 2026-02-26  
**Status:** Complete  
**Requirement IDs:** SCALE-03

## User Constraints

- No `08-CONTEXT.md` exists for this phase; planning proceeds from roadmap, requirements, and repository evidence only.
- Docker Compose remains the milestone baseline (`Kubernetes migration in v1.1` is out of scope per `.planning/REQUIREMENTS.md`).
- Phase 8 scope is requirement `SCALE-03`: operators must be able to deploy and validate multi-node capacity profiles with documented, executable runbooks.

## Objective

Produce implementation-ready planning input that turns existing scale guidance into deterministic operator workflows and validation gates for multi-node capacity operations.

## Source Surfaces Reviewed

- `.planning/ROADMAP.md`
- `.planning/REQUIREMENTS.md`
- `.planning/STATE.md`
- `.planning/PROJECT.md`
- `CLAUDE.md`
- `compose.yaml`
- `compose.prod.build.yaml`
- `docs/docker_compose.md`
- `docs/performance.md`
- `docs/troubleshooting.md`
- `docs/quickstart.md`
- `tools/nemesis-ctl.sh`
- `tools/test.sh`
- `tools/tests/test_nemesis_ctl_profiles.sh`
- `.github/workflows/ci-fast.yml`

## Baseline Findings

1. `docs/docker_compose.md` is profile-aware (`--monitoring`, `--jupyter`, `--llm`) but does not provide a deterministic multi-node runbook sequence (prepare profile, scale workers, validate, rollback).
2. `compose.yaml` and `compose.prod.build.yaml` already contain commented `file-enrichment-1/2/3` replica placeholders, but no executable operator guardrails prevent drift between those placeholders and docs.
3. `tools/nemesis-ctl.sh` is the operational entrypoint for `start|status|stop|clean` and currently checks profile readiness, but it does not expose a capacity-focused contract for scale-out profile validation.
4. `tools/tests/test_nemesis_ctl_profiles.sh` validates baseline/monitoring/llm readiness behavior with a fake Docker harness, but there is no deterministic test that enforces multi-node/capacity runbook command contract.
5. `tools/test.sh` already provides explicit contract gates (`--readiness-contract`, `--smoke-backend`, `--queue-contract`) and is a natural place to add a capacity runbook/contract gate.
6. `.github/workflows/ci-fast.yml` runs profile-readiness smoke (`test_nemesis_ctl_profiles.sh`) but does not run a dedicated capacity/multi-node contract check.
7. `docs/performance.md` includes scale hints and throughput evidence flow, including file-enrichment replica placeholders, but cross-doc guidance is not normalized into a single capacity profile runbook.

## Current Capacity Workflow Model (Observed)

### Operator startup/status baseline

- Startup and readiness are profile-aligned via `nemesis-ctl`:
  - `./tools/nemesis-ctl.sh start <dev|prod> [--monitoring] [--jupyter] [--llm]`
  - `./tools/nemesis-ctl.sh status <dev|prod> [--monitoring] [--jupyter] [--llm]`
- Existing readiness output is service-level matrix driven by container health states.

### Scale-out primitives already in repo

- `compose.yaml` contains commented file-enrichment replica templates and matching Dapr sidecars.
- `compose.prod.build.yaml` mirrors replica placeholders for local prod builds.
- Environment-level workflow tuning already exists in compose (`ENRICHMENT_MAX_PARALLEL_WORKFLOWS`, `DOCUMENTCONVERSION_MAX_PARALLEL_WORKFLOWS`, scheduler notes in `docs/performance.md`).

## Contract Gaps Blocking SCALE-03

1. No canonical profile matrix for "single-node baseline" vs "multi-node scale-out" execution paths.
2. No deterministic validation command proving runbook commands remain aligned with `nemesis-ctl` and compose profile semantics.
3. No CI gate for capacity runbook drift.
4. No unified rollback path in capacity docs when scale-out introduces degradation.
5. No standardized evidence bundle for capacity changes (readiness + queue-drain + benchmark compare + rollback artifacts).

## Multi-Node Runbook Structure Recommended

### Capacity profile classes

- `baseline`: core services with profile flags only.
- `observability`: baseline plus monitoring profile for queue/service analysis under load.
- `scale-out`: baseline/observability plus file-enrichment replica enablement and worker tuning.

### Deterministic operator sequence

1. Prepare and validate selected profile inputs.
2. Start profile with explicit `nemesis-ctl` command.
3. Validate readiness using matching status flags.
4. Apply scale-out changes (replica placeholders and worker vars) using documented compose edits.
5. Collect evidence (status matrix, queue-drain, benchmark compare).
6. Execute rollback sequence when thresholds regress.

## Drift Matrix (Code vs Docs)

| Surface | Current State | Drift Risk | Planning Direction |
|---|---|---|---|
| `tools/nemesis-ctl.sh` | profile-aware lifecycle + throughput-policy controls | capacity profile behavior not explicitly modeled | add explicit capacity contract/flags or deterministic output surface |
| `tools/tests/test_nemesis_ctl_profiles.sh` | profile readiness smoke only | does not lock multi-node contract | extend + add dedicated capacity contract test script |
| `tools/test.sh` | has dedicated contract flags | no capacity contract flag | add `--capacity-contract` to standardize local/CI usage |
| `docs/docker_compose.md` | profile startup examples | no end-to-end multi-node runbook | add profile matrix + scale-out + rollback + validation commands |
| `docs/quickstart.md` | startup/readiness baseline | no capacity progression path | add quick path to capacity runbook |
| `.github/workflows/ci-fast.yml` | profile smoke covered | capacity runbook drift unchecked | add capacity contract gate step |

## Recommended Plan Split

### Plan 08-01 (Wave 1)

Focus: define executable capacity profile control/validation contract in operator tooling.

- Update `tools/nemesis-ctl.sh` capacity profile command contract (without changing infra manifests).
- Add deterministic capacity contract gate script under `tools/tests/`.
- Extend `tools/test.sh` with a dedicated capacity contract command.
- Extend profile smoke coverage where needed.

### Plan 08-02 (Wave 2, depends on 08-01)

Focus: publish multi-node runbooks and wire drift prevention into CI.

- Update `docs/docker_compose.md` with profile matrix, multi-node scale-out path, validation, and rollback.
- Align `docs/performance.md`, `docs/troubleshooting.md`, and `docs/quickstart.md` with the same sequence.
- Add CI step in `.github/workflows/ci-fast.yml` to run capacity contract gate.

## Validation Architecture

### Gate 1: Operator profile contract remains deterministic

```bash
cd /opt/Nemesis && bash tools/tests/test_nemesis_ctl_profiles.sh
cd /opt/Nemesis && bash tools/tests/test_capacity_profile_contracts.sh
```

### Gate 2: Standard test harness exposes capacity contract

```bash
cd /opt/Nemesis && ./tools/test.sh --capacity-contract
```

### Gate 3: Docs + CI drift checks

```bash
cd /opt/Nemesis && rg -n "capacity profile|multi-node|scale-out|rollback|validate readiness|queue-drain" docs/docker_compose.md docs/performance.md docs/troubleshooting.md docs/quickstart.md
cd /opt/Nemesis && rg -n "capacity contract|test_capacity_profile_contracts" .github/workflows/ci-fast.yml tools/test.sh
```

### Gate 4: Compose profile alignment evidence

```bash
cd /opt/Nemesis && rg -n "file-enrichment-1|file-enrichment-2|file-enrichment-3|profiles: \[\"monitoring\"\]|profiles: \[\"llm\"\]" compose.yaml compose.prod.build.yaml
```

---
*Phase research complete: 2026-02-26*
