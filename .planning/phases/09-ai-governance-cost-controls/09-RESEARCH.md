# Phase 9 Research: AI Governance & Cost Controls

**Phase:** 09 AI Governance & Cost Controls  
**Researched:** 2026-02-26  
**Status:** Complete  
**Requirement IDs:** AI-01, AI-02

## User Constraints

- No `09-CONTEXT.md` exists; planning proceeds from roadmap, requirements, and repository evidence only.
- Scope is limited to Phase 9 requirements (`AI-01`, `AI-02`) and must preserve current operator workflows.
- Changes must remain secret-safe and fail closed when AI dependencies are unavailable.

## Objective

Produce implementation-ready planning input that makes AI analysis decisions auditable/controllable and exposes budget-oriented AI governance signals in operational surfaces.

## Source Surfaces Reviewed

- `.planning/ROADMAP.md`
- `.planning/REQUIREMENTS.md`
- `.planning/PROJECT.md`
- `.planning/STATE.md`
- `projects/web_api/web_api/main.py`
- `projects/web_api/web_api/models/responses.py`
- `projects/web_api/tests/test_llm_auth_status.py`
- `projects/web_api/tests/test_workflow_observability.py`
- `projects/agents/agents/main.py`
- `projects/agents/agents/tasks/reporting_agent.py`
- `projects/agents/agents/tasks/validate.py`
- `projects/agents/agents/schemas.py`
- `projects/agents/tests/test_model_manager_modes.py`
- `projects/frontend/src/components/Dashboard/StatsOverview.jsx`
- `projects/frontend/src/components/Reporting/SourceReportPage.jsx`
- `projects/frontend/src/components/Reporting/SystemReportPage.jsx`
- `projects/frontend/src/components/Agents/AgentsPage.jsx`
- `projects/frontend/src/components/Chatbot/ChatbotPage.jsx`
- `projects/frontend/src/components/Settings/SettingsPage.jsx`
- `tools/test.sh`
- `docs/agents.md`
- `docs/usage_guide.md`
- `docs/troubleshooting.md`
- `docs/api.md`

## Baseline Findings

1. AI synthesis routes (`/reports/source/synthesize`, `/reports/system/synthesize`) currently return `risk_level`, `key_findings`, and `token_usage` but do not expose confidence-aware policy context or override metadata.
2. Validation/triage logic already emits confidence (`projects/agents/agents/tasks/validate.py`) and persists triage values, but policy-mode semantics and explicit operator override traces are not represented in a stable contract.
3. LLM spend telemetry exists (`/agents/spend-data` proxying agents service) with totals and request/token counts, but no budget threshold interpretation or severity-state contract.
4. Observability summary (`/workflows/observability/summary`) only reports queue/workflow/service-health signals; AI governance/cost signals are absent from this operational surface.
5. Dashboard operational panel (`StatsOverview.jsx`) renders observability severity cards and triage links, providing a natural integration point for AI governance status.
6. Existing fail-safe patterns already exist in health/auth and throughput-policy paths (fallback payloads, degraded readiness, telemetry-stale conservative mode) and should be reused for AI governance.
7. Regression coverage is strong for health/auth/observability, but there are no dedicated tests for AI governance contracts (policy-mode exposure, override path, budget warning states).

## AI-01: Confidence-Aware Policy Context and Operator Override Controls

### Current Contract Gaps

- `LLMSynthesisResponse` has no fields for policy mode, confidence band, or override source.
- Synthesis endpoints accept only reporting-focused inputs (`source`, `max_tokens`, etc.) with no explicit policy/override control surface.
- Triaging outputs include confidence but no standardized mapping to operator-facing policy mode (`strict_review`, `balanced`, etc.).

### Recommended Direction

1. Add a stable AI policy context object to synthesis/triage-facing response contracts:
   - policy mode
   - confidence score/band
   - operator override metadata (requested/applied/reason/source)
2. Preserve backward compatibility for existing response keys consumed by frontend/reporting views.
3. Apply fail-safe behavior:
   - when model/auth is unavailable, return explicit governance metadata with safe defaults instead of silent omission.
4. Add deterministic regression tests that lock:
   - override propagation
   - confidence-to-policy mapping behavior
   - non-breaking legacy keys.

## AI-02: Budget-Oriented Governance Signals in Operational Summary Surfaces

### Current Contract Gaps

- `/agents/spend-data` has raw counters but no policy thresholds, severity, budget window, or actionability.
- `/workflows/observability/summary` cannot be used to triage AI governance drift/spend pressure because it lacks AI signal block.
- Dashboard operational summary currently omits AI usage/cost state, forcing operators into page-by-page investigation.

### Recommended Direction

1. Define an `ai_governance` observability signal model with:
   - spend totals and token/request counters
   - budget threshold values and utilization ratio
   - severity state (`normal|warning|critical`)
   - dependency/fail-safe status when spend telemetry is unavailable.
2. Embed `ai_governance` in `/workflows/observability/summary` while preserving existing fields.
3. Render AI governance severity and key metrics in dashboard operational cards with triage links to docs/runbooks.
4. Add deterministic docs/contract checks in `tools/tests/` plus `tools/test.sh` gate wiring for CI/local parity.

## Contract Drift Matrix

| Surface | Current State | Drift/Risk | Planning Direction |
|---|---|---|---|
| `projects/web_api/web_api/models/responses.py` | Synthesis + observability models lack AI governance block | Operators cannot see policy/cost status in one contract | Extend typed response models for policy context + budget signal |
| `projects/web_api/web_api/main.py` | Synthesis and spend routes return minimal data | No explicit override/policy path; no budget severity | Add policy-context propagation + observability AI signal assembly |
| `projects/agents/agents/tasks/validate.py` | Confidence exists, no policy mode contract | Confidence not translated into controllable policy semantics | Add deterministic confidence-to-policy mapping and override hooks |
| `projects/frontend/src/components/Dashboard/StatsOverview.jsx` | Queue/failure/service cards only | AI governance risk invisible in main operational view | Add AI governance operational card(s) and triage links |
| `tools/test.sh` | readiness/smoke/queue/capacity gates | No deterministic AI governance contract gate | Add `--ai-governance-contract` mode with dedicated script |
| `docs/usage_guide.md`, `docs/troubleshooting.md`, `docs/agents.md` | AI usage discussed across pages but no unified governance triage sequence | Runbook drift and operator ambiguity | Align one AI governance evidence/rollback workflow |

## Recommended Plan Split

### Plan 09-01 (Wave 1, AI-01)

Focus: establish confidence-aware policy and explicit operator override contracts for synthesis/triage outputs.

- Extend response models and synthesis route contract fields.
- Implement deterministic confidence-policy mapping and override preservation in agents/web_api paths.
- Add regression coverage for policy context and override behavior.

### Plan 09-02 (Wave 2, AI-02, depends on 09-01)

Focus: add budget-aware AI governance signal to observability + operator surfaces.

- Extend observability summary with `ai_governance` signal (thresholds, severity, fail-safe).
- Add dashboard/operator docs + deterministic contract gate script.
- Add regression tests for summary fallback/degraded behavior and UI contract rendering assumptions.

## Validation Architecture

### Gate 1: AI policy context contract (AI-01)

```bash
cd /opt/Nemesis/projects/agents && uv run pytest tests/test_ai_policy_modes.py tests/test_model_manager_modes.py -q
cd /opt/Nemesis/projects/web_api && uv run pytest tests/test_ai_policy_contracts.py tests/test_llm_auth_status.py -q
cd /opt/Nemesis && rg -n "policy_mode|confidence|override|operator" projects/web_api/web_api/main.py projects/web_api/web_api/models/responses.py projects/agents/agents/tasks/validate.py projects/agents/agents/tasks/reporting_agent.py
```

### Gate 2: AI governance summary and budget severity (AI-02)

```bash
cd /opt/Nemesis/projects/web_api && uv run pytest tests/test_workflow_observability.py tests/test_ai_governance_summary.py -q
cd /opt/Nemesis/projects/frontend && npm run test:smoke && npm run build
cd /opt/Nemesis && bash tools/tests/test_ai_governance_contracts.sh
```

### Gate 3: Docs/runbook and local gate parity

```bash
cd /opt/Nemesis && ./tools/test.sh --ai-governance-contract
cd /opt/Nemesis && rg -n "ai governance|budget|spend|override|policy mode|llm-auth-status|agents/spend-data" docs/agents.md docs/usage_guide.md docs/troubleshooting.md
```

---
*Phase research complete: 2026-02-26*
