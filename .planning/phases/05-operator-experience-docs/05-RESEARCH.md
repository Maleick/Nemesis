# Phase 5 Research: Operator Experience & Docs

**Phase:** 05 Operator Experience & Docs
**Researched:** 2026-02-25
**Status:** Complete
**Requirement IDs:** OPS-01, OPS-02

## Objective

Define implementation-ready planning input that makes operator runbooks and profile documentation executable, while aligning dashboard/help triage affordances with the platform's current health/observability behavior.

## Context and Constraints

- `05-CONTEXT.md` is intentionally absent for this pass; planning proceeds with roadmap, requirements, and codebase evidence.
- Phase 4 is complete and adds production-relevant quality gates (`--smoke-backend`, profile smoke, queue contract gate) that should now be reflected in operator documentation.
- `workflow.auto_advance=false`; this planning run must stop after validated planning docs and commit.

## Source Surfaces Reviewed

- `docs/quickstart.md`
- `docs/troubleshooting.md`
- `docs/docker_compose.md`
- `docs/usage_guide.md`
- `docs/agents.md`
- `tools/nemesis-ctl.sh`
- `tools/tests/test_nemesis_ctl_profiles.sh`
- `projects/frontend/src/components/Dashboard/StatsOverview.jsx`
- `projects/frontend/src/components/Help/HelpPage.jsx`
- `projects/web_api/web_api/main.py` (`/system/available-services`, `/system/health`, `/workflows/observability/summary`)

## Current Operator Journey

1. Operator follows `docs/quickstart.md` to create `.env` and run `./tools/nemesis-ctl.sh start <dev|prod> [flags]`.
2. Operator opens dashboard and uses `/files`, `/findings`, and `/help` for initial triage.
3. During issues, operator uses `docs/troubleshooting.md`, then pivots to logs, queue metrics, and observability APIs.
4. Profile-specific operations (`--monitoring`, `--jupyter`, `--llm`) are interpreted via a mix of `quickstart.md`, `docker_compose.md`, `agents.md`, and runtime behavior of `nemesis-ctl.sh status`.

## Confusion Point Inventory

| ID | Confusion Point | Concrete Evidence | Operator Impact |
|----|-----------------|-------------------|-----------------|
| CP-01 | Startup docs do not strongly enforce immediate readiness validation after startup | `docs/quickstart.md` starts services but does not provide a canonical post-start `status` validation flow tied to pass/fail remediation loop | Operators can move to UI before required services are healthy, causing noisy false failures |
| CP-02 | Incident triage guidance is split and partially redundant | `docs/troubleshooting.md` and `docs/usage_guide.md` both cover operations triage but with different emphasis and no single ordered runbook | Slower triage, inconsistent first response behavior |
| CP-03 | Compose profile docs and wrapper behavior are not fully aligned in narrative priority | `docs/docker_compose.md` recommends manual compose patterns while `tools/nemesis-ctl.sh` is the operational source of truth for profile-aware startup/status | Operators mix raw compose and wrapper commands, increasing profile mismatch risk |
| CP-04 | Dashboard observability cards link to generic `/help` rather than role-specific triage destinations | In `StatsOverview.jsx`, “Queue triage links”, “Failure triage links”, and “Service triage links” all navigate to `/help` | Extra clicks and ambiguity during active incidents |
| CP-05 | Help page does not provide an explicit fast triage sequence for startup/queue/workflow/service incidents | `HelpPage.jsx` lists service links but lacks a concrete incident sequence and profile-aware startup checklist | Operators rely on memory instead of guided flow |
| CP-06 | Phase 4 quality-gate commands are not surfaced as operator-facing validation checkpoints | New commands exist in `tools/test.sh` and `tools/tests/test_nemesis_ctl_profiles.sh`, but docs do not consistently present them as pre-change validation checkpoints | Regression checks underused outside CI |

## Doc/UX Drift Matrix

| Surface | Source of Truth | Current Drift | Planned Correction Direction |
|---------|-----------------|---------------|------------------------------|
| Startup validation flow | `tools/nemesis-ctl.sh status` readiness matrix + remediation semantics | Quickstart does not strongly anchor to status-first gating after start | Add explicit startup validation runbook with copy/paste commands and expected states |
| Profile behavior (`base`, `monitoring`, `llm`) | `tools/nemesis-ctl.sh` + `tools/tests/test_nemesis_ctl_profiles.sh` | Profile outcomes documented inconsistently across quickstart/docker_compose/troubleshooting | Normalize profile command matrix and expected outcomes in one consistent vocabulary |
| Observability triage UX | `StatsOverview.jsx` severity cards + `HelpPage.jsx` resources + `/api/workflows/observability/summary` | Triage buttons are generic and not mapped to specific next actions | Add explicit deep-link routing and help-page triage anchors |
| Compose profile documentation | `nemesis-ctl` wrapper behavior and supported flags | Manual compose examples can appear equally preferred for routine ops | Clarify primary/secondary paths: wrapper-first, compose-for-advanced scenarios |
| Operator validation checkpoints | Phase 4 quality gates (`--smoke-backend`, profile smoke, queue contract) | Mentioned partially, not structured as standard operator validation routine | Add deterministic validation sequence in runbooks |

## Requirement Mapping

- `OPS-01` (runbooks up to date and executable): primarily addressed by Phase 5 Plan `05-01` through startup and incident runbook normalization and command verification.
- `OPS-02` (compose profile docs match current commands/outcomes): primarily addressed by Phase 5 Plan `05-02` through profile-documentation alignment and operator UX clarifications.

## Recommended Plan Split

### Plan 05-01 (Wave 1, OPS-01)

- Update startup validation and incident triage runbooks in `quickstart.md`, `troubleshooting.md`, and `usage_guide.md`.
- Add deterministic command consistency checks for operator docs under `tools/tests/`.
- Provide executable command ordering and expected outcomes for healthy/degraded/unhealthy paths.

### Plan 05-02 (Wave 2, OPS-02, depends on 05-01)

- Align `docker_compose.md` with wrapper-first operational guidance and profile outcome expectations.
- Update `StatsOverview.jsx` triage affordances and `HelpPage.jsx` triage guidance to reduce incident response ambiguity.
- Add frontend smoke coverage for health-summary triage-link behavior.

## Risks and Mitigations

- **Risk:** Docs become stale again after future command changes.
  - **Mitigation:** add deterministic docs-check script with required command signatures and include it in verification routines.
- **Risk:** UX triage-link updates introduce route regressions.
  - **Mitigation:** add focused frontend smoke tests and keep existing `test:smoke` gate green.
- **Risk:** Overcorrection toward docs-only changes misses operational UI confusion.
  - **Mitigation:** include explicit `StatsOverview` + `HelpPage` UX alignment in Plan 05-02.

## Validation Architecture

### Gate 1: Operator runbook consistency

- `bash tools/tests/test_operator_docs_commands.sh`
- `rg -n "nemesis-ctl.sh status|healthy|degraded|unhealthy|workflows/observability/summary" docs/quickstart.md docs/troubleshooting.md docs/usage_guide.md`

### Gate 2: Compose/profile alignment

- `rg -n "nemesis-ctl.sh start|nemesis-ctl.sh status|--monitoring|--jupyter|--llm" docs/docker_compose.md docs/quickstart.md docs/agents.md`
- `bash tools/tests/test_nemesis_ctl_profiles.sh`

### Gate 3: Dashboard/help triage UX

- `cd projects/frontend && npm run test:smoke && npm run build`
- `rg -n "Queue triage|Failure triage|Service triage|troubleshooting" projects/frontend/src/components/Dashboard/StatsOverview.jsx projects/frontend/src/components/Help/HelpPage.jsx`

## Planning Notes for Executor Compatibility

- Plans must be consumable by `$gsd-execute-phase` with explicit `wave` and `depends_on` frontmatter.
- Plan verification commands should be command-complete and copy/paste ready.
- `05-02` should remain dependency-locked on `05-01` because UX messaging should reference finalized runbook language.

---
*Phase research complete: 2026-02-25*
