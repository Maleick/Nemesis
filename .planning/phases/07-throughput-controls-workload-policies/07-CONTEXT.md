# Phase 7: Throughput Controls & Workload Policies - Context

**Gathered:** 2026-02-25
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase delivers throughput control and workload throttling behavior for high-volume processing paths under queue pressure.

Scope is fixed to `SCALE-01` and `SCALE-02`. This discussion clarifies implementation behavior only and does not add new capabilities.

</domain>

<decisions>
## Implementation Decisions

### Trigger Model
- Primary activation signal is queue pressure first.
- Threshold scope uses profile presets with per-queue defaults.
- Activation/deactivation uses sustained window plus cooldown to avoid flapping.
- If telemetry is unavailable or stale, policy enters fail-safe conservative throttling and emits operator warning.

### Workload Prioritization
- Policy uses tiered workload classes.
- Class membership comes from policy file with curated defaults and operator override capability.
- Under pressure, expensive-class processing is constrained by reducing parallelism and deferring admission.
- A minimum floor capacity for expensive workloads is required to prevent starvation.

### Operator Control Surface
- Control entrypoint is config-backed policy mode plus deterministic `nemesis-ctl` workflows.
- Mode model uses named presets (not raw-only knobs or binary on/off).
- Overrides are time-bounded (TTL-based) and expire back to baseline.
- Status output must include concise summary plus per-class active policy state.

### Acceptance Evidence Contract
- Required evidence bundle: benchmark compare results + queue-drain metrics + operator status snapshots.
- Pass/fail rule: no critical regressions and measurable improvement in at least one declared throughput KPI.
- Evidence must be collected against a repeatable stress profile (not ad-hoc-only runs).
- Rollback contract is mandatory with explicit rollback triggers and revert command path.

### Claude's Discretion
- Exact numeric thresholds, sustained-window durations, cooldown durations, and override TTL values.
- Final preset names and exact operator-facing wording for status output.
- Exact KPI target values chosen per profile/workload baseline.

</decisions>

<specifics>
## Specific Ideas

No additional specific references beyond the locked decisions above.

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within Phase 7 scope.

</deferred>

---

*Phase: 07-throughput-controls-workload-policies*
*Context gathered: 2026-02-25*
