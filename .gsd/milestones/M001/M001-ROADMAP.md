# M001: Copilot LLM Auth Migration

**Vision:** Replace the LLM authentication layer in Nemesis with GitHub Copilot as the sole model provider via LiteLLM, remove all Codex/Gemini dead code, and verify end-to-end on a local OrbStack deployment.

## Success Criteria

- No Codex or Gemini artifacts remain in the repository
- LiteLLM routes all LLM requests through `github_copilot/gpt-5.4`
- Agents service has a single Copilot auth mode — no `official_key` or `codex_oauth`
- `nemesis-ctl.sh start prod --llm` on OrbStack brings up a healthy LLM subsystem
- An actual LLM call (triage or summarization) succeeds through the Copilot provider

## Key Risks / Unknowns

- **OAuth device flow in Docker** — first-run requires interactive auth via browser. Operator must watch logs. Risk: confusing UX if not documented.
- **GPT-5.4 model string** — need to confirm exact model name string for LiteLLM's Copilot provider.
- **Dapr token provisioning overlap** — `litellm_startup.py` provisions LiteLLM keys via admin API. Copilot auth is handled internally by LiteLLM. These may conflict or one may be unnecessary.

## Proof Strategy

- OAuth device flow in Docker → retire in S02 by proving LiteLLM container authenticates with mounted token dir
- GPT-5.4 model string → retire in S02 by confirming model resolves in LiteLLM config
- Dapr token provisioning overlap → retire in S03 by proving agents service initializes cleanly with Copilot auth

## Verification Classes

- Contract verification: ruff lint clean, pytest passes for all modified projects, no Codex references in repo
- Integration verification: LiteLLM Copilot provider authenticates, agents health endpoint healthy
- Operational verification: full stack on OrbStack, OAuth token persists across restart
- UAT / human verification: operator completes OAuth device flow, submits a file, sees LLM triage result

## Milestone Definition of Done

This milestone is complete only when all are true:

- All Codex/Gemini artifacts removed, confirmed by grep
- LiteLLM config uses `github_copilot/gpt-5.4`, model resolves
- Auth modes, auth provider, model manager rewritten for Copilot-only path
- compose.yaml and env.example reflect Copilot configuration
- All agent tests pass with new auth implementation
- OrbStack deployment: `nemesis-ctl.sh start prod --llm` starts, OAuth completes, health healthy, LLM call succeeds

## Requirement Coverage

- Covers: R001, R002, R003, R004, R005, R006, R007, R008, R009, R010
- Partially covers: none
- Leaves for later: none
- Orphan risks: none

## Slices

- [ ] **S01: Dead Code Removal** `risk:low` `depends:[]`
  > After this: `.codex/`, `AGENTS.md`, `codex_oauth_model.py`, Codex tests, Gemini configs all gone. `ruff check` and build pass clean.

- [ ] **S02: LiteLLM GitHub Copilot Provider** `risk:high` `depends:[]`
  > After this: `infra/litellm/config.yml` uses `github_copilot/gpt-5.4`, OAuth token dir mounted in compose, placeholder JSON removed. LiteLLM container starts and Copilot provider is configured (proven by config inspection, not yet by live auth).

- [ ] **S03: Auth Mode Replacement** `risk:medium` `depends:[S01,S02]`
  > After this: `auth_modes.py` has single Copilot mode, `auth_provider.py` resolves Copilot credentials via LiteLLM, `model_manager.py` has no Codex/official_key branching, `compose.yaml`/`env.example` updated, LiteLLM healthcheck fixed, all agent tests pass.

- [ ] **S04: Local Deployment Verification** `risk:high` `depends:[S03]`
  > After this: `nemesis-ctl.sh start prod --llm` on OrbStack, OAuth device flow completes, agents health endpoint reports healthy with Copilot mode, LLM triage/summarization call succeeds against GPT-5.4.

## Boundary Map

### S01 → S03

Produces:
- Clean repo with no Codex/Gemini artifacts — `codex_oauth_model.py` deleted, `CODEX_OAUTH` removed from all code paths
- No `codex_oauth` references in tests — S03 can write new Copilot tests without conflicting with old ones

Consumes:
- nothing (first slice, independent)

### S02 → S03

Produces:
- `infra/litellm/config.yml` with `github_copilot/gpt-5.4` model entry
- `compose.yaml` volume mount for `GITHUB_COPILOT_TOKEN_DIR` on the LiteLLM service
- Knowledge of correct model name string and LiteLLM Copilot provider behavior

Consumes:
- nothing (independent of S01)

### S02 → S04

Produces:
- LiteLLM config that S04 deploys and tests live

Consumes:
- nothing

### S03 → S04

Produces:
- Simplified `auth_modes.py` with single Copilot mode
- `auth_provider.py` that resolves Copilot auth via LiteLLM (token from LiteLLM startup, model from config)
- `model_manager.py` that creates `OpenAIModel` for Copilot (no `CodexOAuthResponsesModel` branching)
- Updated `compose.yaml` with Copilot env vars and no Codex env vars
- Updated `env.example` documenting Copilot configuration
- Updated LiteLLM healthcheck (no `codex_oauth` branch)
- All passing agent tests covering Copilot auth path

Consumes from S01:
- Clean repo without Codex artifacts (no import conflicts, no dead test files)

Consumes from S02:
- LiteLLM config with `github_copilot/gpt-5.4` model
- Volume mount for token persistence
