# Project

## What This Is

Nemesis is an open-source, centralized data processing platform (v2.0) that ingests, enriches, and enables collaborative analysis of files collected during offensive security assessments. Built on Docker with Dapr integration, it functions as an "offensive VirusTotal." Recently synced with upstream (SpecterOps/Nemesis) to pick up SeaweedFS, Titus scanner, and other v2.2.2 changes.

## Core Value

Automated file enrichment pipeline that accepts uploaded files, runs 20+ enrichment modules in parallel via Dapr workflows, and surfaces findings through a React UI — with LLM-powered triage and summarization of security findings.

## Current State

- Fork synced with upstream v2.2.2 (merge + lint fixes committed and pushed)
- Docker-first deployment via OrbStack locally
- LLM integration exists but uses stale Codex OAuth auth path (being replaced)
- LiteLLM proxy routes LLM calls, currently configured for AWS Bedrock (being replaced)
- Frontend, file enrichment, alerting, web API all functional
- 16 Dependabot vulnerabilities pending (8 high, 3 moderate, 5 low)

## Architecture / Key Patterns

- **Python 3.13** with uv for dependency management
- **FastAPI** REST services (web_api, agents, file_enrichment, alerting)
- **React 18 + Vite + TypeScript** frontend
- **Dapr** for pub/sub, workflows, secrets, service invocation
- **PostgreSQL** database, **RabbitMQ** message queue, **Minio** object storage
- **LiteLLM** proxy for LLM routing (port 4000 inside Docker)
- **Traefik** reverse proxy with TLS
- Microservice architecture under `projects/`, shared libs under `libs/`

## Capability Contract

See `.gsd/REQUIREMENTS.md` for the explicit capability contract, requirement status, and coverage mapping.

## Milestone Sequence

- [ ] M001: Copilot LLM Auth Migration — Replace Codex/Bedrock auth with GitHub Copilot via LiteLLM, remove dead tooling, verify on OrbStack
