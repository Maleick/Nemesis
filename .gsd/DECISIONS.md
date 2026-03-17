# Decisions Register

<!-- Append-only. Never edit or remove existing rows.
     To reverse a decision, add a new row that supersedes it.
     Read this file at the start of any planning or research phase. -->

| # | When | Scope | Decision | Choice | Rationale | Revisable? |
|---|------|-------|----------|--------|-----------|------------|
| D001 | M001 | arch | LLM provider | GitHub Copilot via LiteLLM `github_copilot/` provider | Operator has active Copilot subscription, `gh auth` already configured, LiteLLM v1.81.12 has built-in provider with OAuth device flow | Yes — if Copilot access changes |
| D002 | M001 | arch | Default LLM model | `github_copilot/gpt-5.4` (highest available GPT) | User wants best available model, GPT-5.4 GA in Copilot as of 2026-03-05 | Yes — bump when newer model available |
| D003 | M001 | arch | Auth mode strategy | Single Copilot mode, no fallbacks | User explicitly chose to replace `official_key` entirely, not keep as fallback. Simplicity over resilience. | Yes — if multi-provider needed later |
| D004 | M001 | arch | Token persistence | Mount `GITHUB_COPILOT_TOKEN_DIR` as Docker volume | LiteLLM stores OAuth tokens at `~/.config/litellm/github_copilot/`. Without mount, re-auth required on every container restart. | No |
| D005 | M001 | scope | Deployment model | Docker via OrbStack, no Kubernetes | User is Docker-first, not adopting upstream K8s work | Yes — if K8s needed later |
