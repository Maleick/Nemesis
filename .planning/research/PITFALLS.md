# Pitfalls Research

**Domain:** Offensive-security workflow and enrichment platform operations
**Researched:** 2026-02-25
**Confidence:** HIGH

## Critical Pitfalls

### Pitfall 1: Queue/Topic Contract Drift

**What goes wrong:**
Publishers and subscribers disagree on topic names or payload shapes, causing silent workflow drops.

**Why it happens:**
Cross-service edits are made independently without a single source of truth verification step.

**How to avoid:**
Keep queue/topic constants centralized and require contract checks in CI for producer/consumer pairs.

**Warning signs:**
Rising queue backlog with missing downstream events; enrichment status stuck in intermediate states.

**Phase to address:**
Phase 1 (Service Health Contracts)

---

### Pitfall 2: Startup Order Fragility Across Profiles

**What goes wrong:**
Services boot before dependencies are truly ready (especially llm profile), causing intermittent failures.

**Why it happens:**
Health checks and readiness semantics vary by service; profile combinations increase matrix complexity.

**How to avoid:**
Define explicit readiness contracts and dependency health gates per profile.

**Warning signs:**
Transient startup failures, repeated reconnect loops, manual restarts required.

**Phase to address:**
Phase 1 (Service Health Contracts)

---

### Pitfall 3: Secret Leakage Through Logs/Debug Paths

**What goes wrong:**
Sensitive values appear in startup logs or diagnostic output.

**Why it happens:**
Convenience logging during auth/debug implementation; inconsistent redaction standards.

**How to avoid:**
Adopt secret-safe logging policy and automated checks for likely secret patterns.

**Warning signs:**
Credentials visible in logs, bug reports, or copied troubleshooting transcripts.

**Phase to address:**
Phase 3 (Security & Auth Hardening)

---

### Pitfall 4: Weak End-to-End Validation

**What goes wrong:**
Unit tests pass but real ingestion->enrichment->presentation flows regress.

**Why it happens:**
Cross-service behavior is under-tested relative to component-level tests.

**How to avoid:**
Add deterministic smoke tests for critical user/operator journeys and gate merges on them.

**Warning signs:**
Production/runtime issues not caught by CI; repeated manual verification burden.

**Phase to address:**
Phase 4 (End-to-End Quality Gates)

---

### Pitfall 5: Operator Runbook Drift

**What goes wrong:**
Docs and troubleshooting steps stop matching actual runtime behavior.

**Why it happens:**
Frequent compose/service updates without synchronized operational documentation updates.

**How to avoid:**
Treat runbooks as release artifacts and update with each operationally meaningful change.

**Warning signs:**
Repeated Slack/support questions for the same startup/debug procedures.

**Phase to address:**
Phase 5 (Operator Experience & Docs)

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Import-time external initialization | Faster implementation | Test fragility and startup unpredictability | Rarely; only for trivial local constants |
| Duplicated subscriber logic per service | Rapid feature delivery | Contract drift and inconsistent retries | Short-term spike only with explicit follow-up ticket |
| Manual operator checks instead of codified smoke tests | Low initial setup effort | Hidden regressions and slow release confidence | Acceptable only during initial prototyping |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Hasura subscriptions | Assume permanent websocket stability | Implement reconnect/backoff and health observability |
| LiteLLM/auth modes | Treat provider auth as static | Validate mode/token health on startup and surface status endpoints |
| Apprise notifications | Send all events without filtering | Apply severity/triage-aware filtering and tag strategy |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Overly high workflow concurrency | DB contention, queue churn, timeout spikes | Tune per-profile concurrency and pool settings | Moderate/high ingestion bursts |
| Unbounded OCR/heavy enrichment on all files | CPU saturation, long processing latency | Scope heavy modules by policy/feature flags | Any sustained mixed-content intake |
| Excessive log verbosity in steady state | I/O overhead and noisy diagnostics | Structured log levels + targeted debug toggles | Medium/high event throughput |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Logging credential values in startup checks | Secret compromise | Strict redaction helpers and log review gates |
| Keeping default env template secrets in deployed setups | Unauthorized access | Enforce startup checks for non-default secret values |
| Weakly validated auth mode fallbacks | Unintended insecure runtime path | Explicit auth-mode validation and fail-closed behavior |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Ambiguous workflow failure states | Analysts cannot tell whether to retry or wait | Clear workflow status taxonomy and actionable remediation hints |
| Inconsistent naming between CLI/UI/API | Operator confusion and mistakes | Align terminology in docs and UI surfaces |
| Missing health summary at startup | Slow diagnosis of dependency issues | Provide concise profile-specific readiness report |

## "Looks Done But Isn't" Checklist

- [ ] **Startup hardening:** all profile combinations validated, not just base profile
- [ ] **Observability:** queue, workflow, and object-level tracing correlated end-to-end
- [ ] **Security:** no secret-bearing log lines in nominal and error paths
- [ ] **CI quality gate:** smoke tests cover upload->enrich->retrieve critical path
- [ ] **Operator docs:** runbooks updated to current compose/profile behavior

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Topic contract drift | MEDIUM | Roll back publisher change, restore shared constants, replay blocked queue items |
| Startup order fragility | LOW/MEDIUM | Adjust readiness/dependency checks, restart affected profile, validate health matrix |
| Secret logging incident | HIGH | Rotate credentials, scrub logs, patch redaction paths, add regression tests |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Queue/topic contract drift | Phase 1 | Contract check + subscriber smoke test pass |
| Startup order fragility | Phase 1 | Profile startup matrix green |
| Secret leakage | Phase 3 | Secret-scan/lint and log redaction tests pass |
| Weak e2e validation | Phase 4 | CI smoke tests stable across main scenarios |
| Runbook drift | Phase 5 | Runbook steps executed successfully in clean environment |

## Sources

- Operational patterns and concerns from current Nemesis codebase/docs
- Existing `.planning/codebase/CONCERNS.md`
- Runtime/CI definitions in `compose.yaml` and `.github/workflows/*`

---
*Pitfalls research for: offensive-security workflow and enrichment platform operations*
*Researched: 2026-02-25*
