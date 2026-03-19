# Nemesis Idea

Date: 2026-02-25
Status: Draft

## Problem

Nemesis already ingests, enriches, and exposes offensive-security artifacts, but day-to-day operation can still be fragile in three places:

- startup and readiness behavior across profiles (`base`, `monitoring`, `llm`)
- cross-service observability when workflows stall
- confidence and safety around auth/secrets/logging and release quality gates

Operators need predictable health signals and fast, actionable diagnostics without changing the existing Docker-first deployment model.

## Idea

Evolve Nemesis as a reliability-first, brownfield platform upgrade:

- keep the current architecture (Docker Compose + Dapr + Python services)
- standardize readiness contracts and failure signaling across core services
- improve observability, security hardening, and automated quality gates in phases
- raise operator leverage with clearer troubleshooting and extension guidance

The goal is not a rewrite. The goal is to make the current platform safer, clearer, and easier to run.

## Who This Helps

- operators running Nemesis in varied environments
- analysts depending on stable enrichment and workflow throughput
- maintainers who need faster, lower-risk change cycles

## Success Criteria

- health/readiness outputs are consistent and dependency-aware across profiles
- workflow issues are diagnosable from logs/status without deep source spelunking
- secret-handling and auth-mode drift risks are reduced
- CI catches meaningful cross-service regressions earlier
- operator docs support repeatable startup and troubleshooting flows

## Scope (Current Milestone)

1. Service health contracts
2. Workflow observability baseline
3. Security/auth hardening
4. End-to-end quality gates
5. Operator experience docs
6. Extension contracts and performance follow-through

## Non-Goals

- Kubernetes migration
- multi-tenant SaaS control plane redesign
- full architecture rewrite away from the current Dapr/Python stack

## Constraints

- preserve backward compatibility for existing operator workflows
- avoid secret values in code, logs, docs, prompts, and memory payloads
- prefer incremental, verifiable, phase-based delivery
