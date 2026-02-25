# Pitfalls Research (v1.1)

**Domain:** Scale tuning and AI governance
**Researched:** 2026-02-25
**Confidence:** HIGH

## Critical Pitfalls

### 1. Benchmark-only tuning claims

- **Risk:** Declaring throughput wins from micro-benchmarks without queue/service validation.
- **Impact:** False confidence; backlog growth still worsens in real workloads.
- **Prevention:** Require baseline/compare plus queue drain and health checks before acceptance.

### 2. Throttling policy ambiguity

- **Risk:** Operators cannot predict which modules are throttled and when.
- **Impact:** Incident triage confusion and perceived data loss.
- **Prevention:** Document explicit policy thresholds, fallbacks, and operator-visible status fields.

### 3. Multi-node guidance drift

- **Risk:** Docs diverge from compose/profile reality.
- **Impact:** Invalid deployment commands and hard-to-reproduce incidents.
- **Prevention:** Add deterministic doc checks and executable runbook verification.

### 4. Opaque AI confidence behavior

- **Risk:** AI recommendations appear authoritative without confidence/override context.
- **Impact:** Trust erosion and unsafe analyst decisions.
- **Prevention:** Surface confidence metadata and preserve explicit operator override controls.

### 5. Missing AI cost guardrails

- **Risk:** Unbounded synthesis usage drives unpredictable spend/latency.
- **Impact:** Operational instability and budget overruns.
- **Prevention:** Add budget-aware counters/thresholds and alertable status summaries.

## Validation Guardrails

- No milestone story is complete without executable verification commands.
- Every docs change with operational impact must be paired with command/test evidence.
- Every governance signal surfaced in UI must have a backend contract test.

---
*Pitfall mapping prepared for v1.1 phase planning*
