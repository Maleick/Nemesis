# Feature Research (v1.1)

**Domain:** Scale controls and AI governance
**Researched:** 2026-02-25
**Confidence:** HIGH

## Candidate Feature Set

### Table Stakes for This Milestone

| Feature | Requirement Link | Notes |
|---------|------------------|-------|
| Throughput targets and partition controls | SCALE-01 | Must define measurable queue/latency targets by profile/workload class. |
| Policy-based throttling for expensive enrichments | SCALE-02 | Must prevent heavy modules from starving normal processing paths. |
| Multi-node deployment and capacity playbook | SCALE-03 | Must provide reproducible operator guidance beyond single-node defaults. |
| Confidence-aware AI triage modes | AI-01 | Must preserve analyst override and transparency over auto-generated assessments. |
| AI usage/cost governance signals | AI-02 | Must expose budget-related metrics and warning states in operator surfaces. |

### Differentiators

| Feature | Why It Matters |
|---------|----------------|
| Operator-overridable AI policies | Keeps trust high while enabling optional automation. |
| Baseline-driven throughput governance | Avoids anecdotal tuning and regression loops. |
| Runtime profile-aware scale guidance | Matches existing deployment reality and lowers outage risk. |

### Deferred (Not in v1.1)

| Feature | Defer Reason |
|---------|--------------|
| Fully automatic triage actions that mutate findings | Safety/trust risk without stronger policy engine maturity. |
| Kubernetes-native autoscaling implementation | Out of scope for Docker-first operator baseline. |
| Provider-level AI cost optimization marketplace logic | Too broad for current operational milestone. |

## Feature Dependencies

```text
Queue pressure observability
  -> throughput policy controls
      -> safe workload partitioning

AI synthesis endpoints
  -> confidence/policy contracts
      -> operator override UI/UX
          -> budget/cost governance signals
```

## Validation Architecture

- Throughput controls: benchmark + queue-level evidence and profile checks.
- AI policies: API contract tests for policy mode, confidence metadata, and override behavior.
- Cost signals: dashboard/service summary checks with deterministic fallback behavior.

---
*Feature focus: actionable milestone scope, not long-term roadmap expansion*
