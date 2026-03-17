# M001: Copilot LLM Auth Migration

**Gathered:** 2026-03-17
**Status:** Ready for planning

## Project Description

Replace the LLM authentication layer in Nemesis with GitHub Copilot as the sole model provider via LiteLLM's built-in `github_copilot/` provider. Remove all Codex and Gemini tooling artifacts. Verify end-to-end on a local OrbStack deployment.

## Why This Milestone

The project previously used OpenAI Codex OAuth for LLM access (agent triage, summarization, credential analysis). Codex is no longer in use, and the operator has a GitHub Copilot subscription with `gh auth` already configured. LiteLLM v1.81.12 (already in compose) has a built-in `github_copilot/` provider that handles OAuth device flow automatically. This migration eliminates dead code, removes the AWS Bedrock dependency, and uses existing GitHub credentials.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Run `nemesis-ctl.sh start prod --llm` on OrbStack and have the LLM subsystem authenticate via GitHub Copilot
- See the agents health endpoint report `healthy: true` with `mode: copilot`
- Submit files and see LLM-powered triage/summarization working with GPT-5.4

### Entry point / environment

- Entry point: `./tools/nemesis-ctl.sh start prod --llm`
- Environment: Local Docker via OrbStack
- Live dependencies involved: GitHub Copilot API (via LiteLLM OAuth device flow), PostgreSQL, RabbitMQ, Minio

## Completion Class

- Contract complete means: all Codex code removed, Copilot auth wired, tests pass, compose/env updated
- Integration complete means: LiteLLM container authenticates with Copilot, agents service initializes with Copilot model
- Operational complete means: full stack runs on OrbStack, OAuth token persists across restarts, LLM call succeeds

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- `nemesis-ctl.sh start prod --llm` starts all services including LiteLLM with Copilot auth
- The agents `/llm/auth/status` endpoint returns healthy with Copilot mode
- An actual LLM call (triage or summarization request) succeeds against GPT-5.4 through the Copilot provider

## Risks and Unknowns

- **OAuth device flow in Docker** — LiteLLM prints a URL+code to stdout during first auth. Operator must watch `docker compose logs litellm` and visit the URL. Token persists after that, but first-run UX is interactive.
- **GPT-5.4 availability via LiteLLM Copilot provider** — confirmed the provider exists in v1.81.12 with chat/responses/embedding support, but `gpt-5.4` specifically hasn't been tested through this path yet.
- **LiteLLM healthcheck** — current healthcheck has a `codex_oauth`-specific branch. Needs updating for Copilot.

## Existing Codebase / Prior Art

- `projects/agents/agents/auth_provider.py` — current auth resolution, has Codex OAuth path with `DEFAULT_CODEX_*` constants
- `projects/agents/agents/auth_modes.py` — `LLMAuthMode` enum with `OFFICIAL_KEY` and `CODEX_OAUTH`
- `projects/agents/agents/model_manager.py` — creates model instance, branches on `codex_oauth` for `CodexOAuthResponsesModel`
- `projects/agents/agents/codex_oauth_model.py` — custom OpenAI Responses model for Codex backend constraints (to be deleted)
- `projects/agents/agents/litellm_startup.py` — LiteLLM token provisioning via admin API + Dapr state store
- `projects/agents/agents/main.py` — lifespan handler that calls `resolve_llm_auth()` and initializes `ModelManager`
- `infra/litellm/config.yml` — current model config pointing at Bedrock `claude-sonnet-4-5`
- `infra/litellm/codex-auth-profile.placeholder.json` — Codex placeholder (to be deleted)
- `compose.yaml` lines ~1095-1107 — Codex env vars and volume mount in agents service
- `compose.yaml` line ~1198 — LiteLLM healthcheck with `codex_oauth` branch

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions — it is an append-only register; read it during planning, append to it during execution.

## Relevant Requirements

- R001-R010 — all active requirements are owned by this milestone's slices
- R003, R004 — core: Copilot provider + gpt-5.4 default
- R005 — constraint: single auth mode, no fallbacks
- R008 — integration: OrbStack deployment proves it

## Scope

### In Scope

- Remove `.codex/`, `AGENTS.md`, `codex_oauth_model.py`, Codex tests, Codex env vars
- Remove Gemini project-level configs
- Configure LiteLLM `github_copilot/gpt-5.4` provider
- Mount token persistence volume for OAuth credentials
- Rewrite auth_modes, auth_provider, model_manager for Copilot-only
- Update compose.yaml, env.example, LiteLLM healthcheck
- Update all affected tests
- Deploy on OrbStack and verify end-to-end

### Out of Scope / Non-Goals

- Kubernetes/EKS deployment
- AWS Bedrock integration
- Multi-provider LLM fallback
- LiteLLM version upgrade (v1.81.12 confirmed sufficient)
- Dependabot vulnerability fixes (separate effort)
- NoseyParker→Titus rename audit (separate from LLM auth)

## Technical Constraints

- LiteLLM's Copilot OAuth device flow requires interactive first-run (visit URL, enter code)
- Token stored at `GITHUB_COPILOT_TOKEN_DIR` (default `~/.config/litellm/github_copilot/`) — must be a mounted volume
- LiteLLM Copilot provider simulates VS Code headers (`editor-version`, `user-agent`) — this is how GitHub identifies the client
- GitHub Copilot subscription required (operator must have active plan)

## Integration Points

- **GitHub Copilot API** — LiteLLM authenticates via OAuth device flow, then routes chat completions through `api.github.com/copilot_internal/v2/token`
- **LiteLLM proxy** — runs inside Docker on port 4000, agents service talks to it via `http://litellm:4000/`
- **Dapr state store** — existing `litellm_startup.py` stores provisioned tokens in Dapr. May need adjustment since Copilot auth is handled by LiteLLM internally now.
- **Docker volumes** — new volume mount for Copilot token persistence

## Open Questions

- **Dapr token provisioning overlap** — `litellm_startup.py` provisions a LiteLLM user/key via admin API. With Copilot provider, LiteLLM handles auth internally. Need to determine if the startup provisioning flow still applies or can be simplified.
- **Model name format** — confirm `github_copilot/gpt-5.4` is the correct model string for the LiteLLM provider (vs `github_copilot/gpt-5.4-codex` or similar).
