# Feature Research

**Domain:** Offensive-security file processing and triage platform
**Researched:** 2026-02-25
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Artifact ingestion (API + CLI) | Core workflow starts here | MEDIUM | Must preserve metadata fidelity and large-file support |
| Asynchronous enrichment pipeline | Analysts expect automated parsing/enrichment | HIGH | Queue/workflow resilience is more important than raw throughput initially |
| Searchable findings/results surface | Users need rapid pivoting and triage | HIGH | Hasura + web API + frontend path must stay coherent |
| Alerting and feedback loop | Teams expect signal routing to existing channels | MEDIUM | Apprise integrations and filtering controls are operationally critical |
| Authenticated operator access | Security baseline for sensitive artifacts | MEDIUM | Traefik basic auth + service-level role protections |

### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Deep enrichment modules (DPAPI, Chromium, office/pdf, secrets) | High-value context extraction from post-ex artifacts | HIGH | Requires disciplined module contracts and test harness coverage |
| Container and large-file workflows | Handles forensic-scale evidence without manual splitting | HIGH | Ingestion + extraction + metadata inheritance must remain predictable |
| Optional LLM triage/summarization/chatbot | Speeds analyst interpretation and prioritization | HIGH | Strong auth/health controls required to keep it trustworthy |
| Multi-source connector support (Mythic/CobaltStrike/Outflank/Velociraptor) | Fits existing operator ecosystems | MEDIUM | Configuration quality and retry semantics define user trust |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| "Auto-triage everything by default" | Appears to reduce analyst effort | Costly, noisy, and difficult to trust at scale | Targeted triage triggers + confidence thresholds |
| "Real-time everything" | Feels modern | Adds complexity and failure coupling without clear operator value | Event-driven async with explicit status indicators |
| "Single mega-service rewrite" | Promises simplification | High regression blast radius in brownfield platform | Incremental refactors by phase with compatibility gates |

## Feature Dependencies

```text
Artifact ingestion
    └──requires──> Storage + metadata contracts
                        └──requires──> Queue/topic contract stability

Enrichment modules
    └──requires──> Workflow orchestration + retry semantics
                        └──requires──> Observability and failure diagnostics

LLM triage/chatbot
    └──requires──> Reliable findings pipeline + auth health
```

### Dependency Notes

- **Enrichment reliability requires topic and schema contract stability:** drift causes silent dropped processing.
- **LLM capabilities depend on core enrichment fidelity:** weak upstream signals degrade model usefulness.
- **Operational alert quality depends on consistent workflow state tracking:** otherwise responders see stale/noisy alerts.

## MVP Definition

### Launch With (v1)

- [ ] Deterministic startup/readiness and dependency health checks across profiles
- [ ] Workflow observability baseline (queue/workflow status, failure visibility)
- [ ] Security/logging hardening for secrets and auth mode clarity
- [ ] Cross-service smoke validation and CI confidence upgrades

### Add After Validation (v1.x)

- [ ] Operator UX and runbook improvements from real incident feedback
- [ ] Module/connector extension contracts and contributor onboarding acceleration

### Future Consideration (v2+)

- [ ] Large-scale horizontal partitioning of enrichment workloads
- [ ] Deeper policy-driven automation beyond advisory triage
- [ ] Multi-tenant control-plane abstractions

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Startup/readiness hardening | HIGH | MEDIUM | P1 |
| Workflow observability baseline | HIGH | MEDIUM | P1 |
| Secret/logging/auth hardening | HIGH | MEDIUM | P1 |
| Cross-service + frontend smoke gates | HIGH | MEDIUM | P1 |
| Operator docs/runbook polish | MEDIUM | LOW | P2 |
| Extension contract formalization | MEDIUM | MEDIUM | P2 |

**Priority key:**
- P1: Must have for this cycle
- P2: Should have after P1 stabilization
- P3: Future consideration

## Competitor Feature Analysis

| Feature | Competitor A | Competitor B | Our Approach |
|---------|--------------|--------------|--------------|
| Automated artifact analysis | Malware triage platforms | DFIR data lakes | Keep offensive-ops specific enrichment depth with modular parsers |
| Alerting integration | SOC-first SIEM workflows | Generic notification tools | Operator-centric alert routing with customizable filters |
| AI-assisted triage | Inline copilots | Standalone chat tools | Optional profile, bounded by platform health and trust controls |

## Sources

- Existing implementation and docs in this repository (`README.md`, `docs/usage_guide.md`, `docs/alerting.md`, `docs/chatbot.md`)
- Current service contracts in `compose.yaml` and `libs/common/common/queues.py`
- Existing codebase map outputs under `.planning/codebase/`

---
*Feature research for: offensive-security file processing and triage platform*
*Researched: 2026-02-25*
