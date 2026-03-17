# Requirements

This file is the explicit capability and coverage contract for the project.

## Active

### R001 — Remove all Codex tooling and code
- Class: constraint
- Status: active
- Description: Delete `.codex/` directory, `AGENTS.md`, `codex_oauth_model.py`, all Codex-specific environment variables, tests, and config files from the repository
- Why it matters: Dead code and config for a discontinued tool creates confusion and maintenance burden
- Source: user
- Primary owning slice: M001/S01
- Supporting slices: none
- Validation: unmapped
- Notes: Includes `infra/litellm/codex-auth-profile.placeholder.json`, Codex env vars in `compose.yaml` and `env.example`

### R002 — Remove Gemini tooling references
- Class: constraint
- Status: active
- Description: Remove any Gemini-related configuration files or references from the project
- Why it matters: No longer using Gemini — stale config creates confusion
- Source: user
- Primary owning slice: M001/S01
- Supporting slices: none
- Validation: unmapped
- Notes: Check for `.gemini/` or Gemini-specific project-level files

### R003 — GitHub Copilot as sole LLM provider via LiteLLM
- Class: core-capability
- Status: active
- Description: Configure LiteLLM to use the `github_copilot/` provider with OAuth device flow authentication as the only LLM provider
- Why it matters: Replaces discontinued Codex OAuth and removes AWS Bedrock dependency — uses existing GitHub Copilot subscription
- Source: user
- Primary owning slice: M001/S02
- Supporting slices: M001/S03
- Validation: unmapped
- Notes: LiteLLM v1.81.12 confirmed to have `github_copilot` provider with chat, embedding, and responses support

### R004 — Default to highest available GPT model
- Class: core-capability
- Status: active
- Description: Default model configuration should target the highest available GPT model via GitHub Copilot (currently `github_copilot/gpt-5.4`), easily updated via config
- Why it matters: Ensures best available model quality for triage, summarization, and credential analysis tasks
- Source: user
- Primary owning slice: M001/S02
- Supporting slices: none
- Validation: unmapped
- Notes: Model name lives in `infra/litellm/config.yml` — single place to bump

### R005 — Single auth mode — Copilot only
- Class: constraint
- Status: active
- Description: Remove `official_key` and `codex_oauth` auth modes. The agents service should have a single Copilot auth path with no fallback modes
- Why it matters: Simplifies auth logic — no dead code paths, no mode confusion for operators
- Source: user
- Primary owning slice: M001/S03
- Supporting slices: none
- Validation: unmapped
- Notes: `LLMAuthMode` enum, `auth_provider.py`, `model_manager.py` all simplified

### R006 — OAuth token persistence across container restarts
- Class: operability
- Status: active
- Description: Mount LiteLLM's GitHub Copilot token directory (`~/.config/litellm/github_copilot/`) as a Docker volume so OAuth tokens survive container restarts
- Why it matters: Without persistence, operator must re-authenticate via device flow on every container restart
- Source: inferred
- Primary owning slice: M001/S02
- Supporting slices: M001/S04
- Validation: unmapped
- Notes: LiteLLM stores `access-token` and `api-key.json` in configurable `GITHUB_COPILOT_TOKEN_DIR`

### R007 — Compose/env config reflects Copilot-only auth
- Class: operability
- Status: active
- Description: `compose.yaml` and `env.example` updated to remove all Codex/Bedrock env vars and document Copilot-specific configuration
- Why it matters: Operators need clear, accurate configuration guidance
- Source: user
- Primary owning slice: M001/S03
- Supporting slices: none
- Validation: unmapped
- Notes: Includes LiteLLM healthcheck update (currently has codex_oauth-specific health path)

### R008 — Local OrbStack deployment proves end-to-end LLM flow
- Class: integration
- Status: active
- Description: `nemesis-ctl.sh start prod --llm` on OrbStack completes successfully, OAuth device flow authenticates, and an LLM call (triage or summarization) succeeds
- Why it matters: Code changes without deployment verification are unproven — this is the real proof
- Source: user
- Primary owning slice: M001/S04
- Supporting slices: none
- Validation: unmapped
- Notes: First run requires interactive OAuth device flow (visit URL, enter code)

### R009 — Agent health endpoint reports healthy with Copilot auth
- Class: failure-visibility
- Status: active
- Description: The agents service `/llm/auth/status` endpoint reports `healthy: true` and `mode: copilot` when Copilot auth is configured and working
- Why it matters: Operators need observable health status for the LLM subsystem
- Source: inferred
- Primary owning slice: M001/S04
- Supporting slices: M001/S03
- Validation: unmapped
- Notes: Existing health endpoint infrastructure stays — just the mode/source values change

### R010 — All existing agent tests updated for new auth
- Class: quality-attribute
- Status: active
- Description: Codex-specific tests replaced or updated to cover Copilot auth path. No test regressions.
- Why it matters: Test coverage must reflect the actual auth implementation
- Source: inferred
- Primary owning slice: M001/S03
- Supporting slices: none
- Validation: unmapped
- Notes: `test_codex_oauth_model_defaults.py` deleted; `test_auth_modes.py`, `test_model_manager_modes.py`, `test_auth_provider_*.py` updated

## Validated

(none yet)

## Deferred

(none)

## Out of Scope

### R011 — Kubernetes/EKS deployment
- Class: constraint
- Status: out-of-scope
- Description: No Kubernetes, EKS, k3d, or k3s deployment support in this milestone
- Why it matters: Prevents scope creep — upstream added K8s manifests but we're Docker-only
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: n/a
- Notes: Upstream has `EKS`, `k8s-k3d-keda-support` branches — not adopting

### R012 — AWS Bedrock LLM integration
- Class: anti-feature
- Status: out-of-scope
- Description: AWS Bedrock / direct API key LLM integration explicitly removed
- Why it matters: Prevents confusion about supported auth paths
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: n/a
- Notes: Current `official_key` mode targeting Bedrock is being replaced entirely

### R013 — Multi-provider LLM fallback
- Class: anti-feature
- Status: out-of-scope
- Description: No fallback between multiple LLM providers — Copilot is the single path
- Why it matters: Simplicity over resilience for this use case
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: n/a
- Notes: If Copilot is unavailable, agents degrade gracefully (existing behavior)

## Traceability

| ID | Class | Status | Primary owner | Supporting | Proof |
|---|---|---|---|---|---|
| R001 | constraint | active | M001/S01 | none | unmapped |
| R002 | constraint | active | M001/S01 | none | unmapped |
| R003 | core-capability | active | M001/S02 | M001/S03 | unmapped |
| R004 | core-capability | active | M001/S02 | none | unmapped |
| R005 | constraint | active | M001/S03 | none | unmapped |
| R006 | operability | active | M001/S02 | M001/S04 | unmapped |
| R007 | operability | active | M001/S03 | none | unmapped |
| R008 | integration | active | M001/S04 | none | unmapped |
| R009 | failure-visibility | active | M001/S04 | M001/S03 | unmapped |
| R010 | quality-attribute | active | M001/S03 | none | unmapped |
| R011 | constraint | out-of-scope | none | none | n/a |
| R012 | anti-feature | out-of-scope | none | none | n/a |
| R013 | anti-feature | out-of-scope | none | none | n/a |

## Coverage Summary

- Active requirements: 10
- Mapped to slices: 10
- Validated: 0
- Unmapped active requirements: 0
