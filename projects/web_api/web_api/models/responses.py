from datetime import datetime

from pydantic import BaseModel, Field


class EnrichmentResponse(BaseModel):
    status: str
    message: str
    instance_id: str
    object_id: str


class BulkEnrichmentResponse(BaseModel):
    status: str
    message: str
    total_files: int
    enrichment_name: str


class BulkEnrichmentStatusResponse(BaseModel):
    status: str
    start_time: str | None = None
    end_time: str | None = None
    total_files: int
    processed: int
    skipped: int
    failed: int
    current_file: str | None = None
    cancelled: bool
    error: str | None = None
    progress_percentage: float
    enrichment_name: str


class BulkEnrichmentStopResponse(BaseModel):
    status: str
    message: str
    enrichment_name: str


class EnrichmentsListResponse(BaseModel):
    modules: list[str]


class WorkflowProcessingStats(BaseModel):
    avg_seconds: float | None = None
    min_seconds: float | None = None
    max_seconds: float | None = None
    p50_seconds: float | None = None
    p90_seconds: float | None = None
    p95_seconds: float | None = None
    p99_seconds: float | None = None
    samples_count: int | None = None


class WorkflowMetrics(BaseModel):
    completed_count: int
    failed_count: int
    total_processed: int
    success_rate: float | None = None
    processing_times: WorkflowProcessingStats | None = None


class ActiveWorkflowDetail(BaseModel):
    id: str
    workflow_id: str | None = None
    status: str
    filename: str | None = None
    object_id: str | None = None
    timestamp: datetime | None = None
    started_at: datetime | None = None
    runtime_seconds: float | None = None
    error: str | None = None
    success_modules: list[str] = Field(default_factory=list)
    failure_modules: list[str] = Field(default_factory=list)


class WorkflowStatusResponse(BaseModel):
    active_workflows: int
    status_counts: dict[str, int] | None = None
    active_details: list[ActiveWorkflowDetail] = Field(default_factory=list)
    metrics: WorkflowMetrics
    timestamp: str
    error: str | None = None


class FailedWorkflowsResponse(BaseModel):
    failed_count: int
    workflows: list[ActiveWorkflowDetail] = Field(default_factory=list)
    timestamp: str


class ContainerSubmissionResponse(BaseModel):
    container_id: str
    message: str
    estimated_files: int
    estimated_size: int
    filter_config: dict | None = None


class ContainerStatusResponse(BaseModel):
    container_id: str
    status: str
    progress_percent_files: float | None = None
    progress_percent_bytes: float | None = None
    processed_files: int
    total_files: int
    processed_bytes: int
    total_bytes: int
    current_file: str | None = None
    started_at: str | None = None
    error: str | None = None
    filter_stats: dict | None = None


class QueueMetrics(BaseModel):
    total_messages: int
    ready_messages: int
    processing_messages: int
    consumers: int
    queue_exists: bool
    memory_bytes: int
    state: str
    message_stats: dict
    error: str | None = None


class QueueSummary(BaseModel):
    total_queued_messages: int
    total_processing_messages: int
    total_consumers: int
    healthy_queues: int
    total_queues_checked: int
    bottleneck_queues: list[str]
    bottleneck_threshold: int | None = None
    queues_without_consumers: list[str]
    total_memory_bytes: int


class QueuesResponse(BaseModel):
    queue_details: dict[str, QueueMetrics]
    summary: QueueSummary
    timestamp: str


class SingleQueueResponse(BaseModel):
    topic: str
    metrics: QueueMetrics
    timestamp: str


# Reporting Models


class SourceSummary(BaseModel):
    source: str
    file_count: int
    finding_count: int
    verified_findings: int
    last_activity: datetime | None = None


class RiskIndicators(BaseModel):
    credentials: dict[str, int]
    sensitive_data: dict[str, int]


class TimelineEntry(BaseModel):
    date: str
    files_submitted: int
    findings_created: int


class TopFinding(BaseModel):
    finding_id: int
    finding_name: str
    category: str
    severity: int
    triage_state: str | None = None
    file_path: str | None = None
    created_at: datetime


class SourceReport(BaseModel):
    report_type: str
    source: str
    generated_at: datetime
    summary: dict
    risk_indicators: RiskIndicators
    findings_detail: dict
    timeline: dict
    enrichment_performance: dict
    top_findings: list[TopFinding]


class SystemReport(BaseModel):
    report_type: str
    generated_at: datetime
    time_range: dict
    summary: dict
    sources: list[SourceSummary]
    findings_by_category: dict[str, int]
    findings_by_severity: dict[str, int]
    timeline: dict
    enrichment_stats: dict


class AIPolicyOverride(BaseModel):
    requested: bool = False
    requested_mode: str | None = None
    applied_mode: str | None = None
    reason: str | None = None
    source: str | None = None


class AIPolicyContext(BaseModel):
    policy_mode: str
    confidence_score: float | None = None
    confidence_band: str | None = None
    override: AIPolicyOverride = Field(default_factory=AIPolicyOverride)
    fail_safe: bool = False
    fail_safe_reason: str | None = None


class LLMSynthesisResponse(BaseModel):
    success: bool
    report_markdown: str | None = None
    risk_level: str | None = None  # "high", "medium", "low"
    key_findings: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    token_usage: int | None = None
    policy_context: AIPolicyContext | None = None
    error: str | None = None


class WorkflowLifecycleRecord(BaseModel):
    workflow_id: str
    status: str
    started_at: datetime | None = None
    runtime_seconds: float | None = None
    filename: str | None = None
    success_modules: list[str] = Field(default_factory=list)
    failure_modules: list[str] = Field(default_factory=list)
    error: str | None = None


class ObjectIngestionDetails(BaseModel):
    object_id: str
    agent_id: str | None = None
    source: str | None = None
    project: str | None = None
    path: str | None = None
    file_name: str | None = None
    ingested_at: datetime | None = None
    observed_at: datetime | None = None


class ObjectPublicationDetails(BaseModel):
    enrichments_count: int = 0
    transforms_count: int = 0
    findings_count: int = 0
    last_enrichment_at: datetime | None = None
    last_transform_at: datetime | None = None
    last_finding_at: datetime | None = None


class ObjectLifecycleSummary(BaseModel):
    latest_status: str | None = None
    workflow_count: int = 0
    running_count: int = 0
    completed_count: int = 0
    failed_count: int = 0


class ObjectLifecycleResponse(BaseModel):
    object_id: str
    ingestion: ObjectIngestionDetails
    workflows: list[WorkflowLifecycleRecord] = Field(default_factory=list)
    publication: ObjectPublicationDetails
    summary: ObjectLifecycleSummary
    timestamp: str


class QueueBacklogSignal(BaseModel):
    severity: str
    total_queued_messages: int
    total_processing_messages: int
    bottleneck_queues: list[str] = Field(default_factory=list)
    queues_without_consumers: list[str] = Field(default_factory=list)
    warning_threshold: int
    critical_threshold: int


class WorkflowFailureSignal(BaseModel):
    severity: str
    failed_workflows: int
    active_workflows: int
    warning_threshold: int
    critical_threshold: int


class ServiceHealthSignal(BaseModel):
    severity: str
    readiness: str
    unhealthy_dependencies: list[str] = Field(default_factory=list)
    degraded_dependencies: list[str] = Field(default_factory=list)


class AIGovernanceSignal(BaseModel):
    severity: str
    total_spend: float
    total_tokens: int
    total_requests: int
    budget_limit: float
    budget_window: str
    utilization_ratio: float
    warning_threshold_ratio: float
    critical_threshold_ratio: float
    fail_safe: bool
    fail_safe_reason: str | None = None
    auth_mode: str | None = None
    auth_healthy: bool | None = None


class ObservabilitySummaryResponse(BaseModel):
    queue_backlog: QueueBacklogSignal
    workflow_failures: WorkflowFailureSignal
    service_health: ServiceHealthSignal
    ai_governance: AIGovernanceSignal | None = None
    timestamp: str


class OperationalAlertEvent(BaseModel):
    condition: str
    severity: str
    emitted: bool
    message: str
    emitted_at: str | None = None


class ObservabilityConditionState(BaseModel):
    condition: str
    active: bool
    severity: str
    sustained_seconds: int
    cooldown_remaining_seconds: int
    eligible: bool


class ObservabilityAlertEvaluationResponse(BaseModel):
    evaluated_at: str
    sustained_duration_seconds: int
    cooldown_seconds: int
    alerts_emitted: list[OperationalAlertEvent] = Field(default_factory=list)
    condition_states: list[ObservabilityConditionState] = Field(default_factory=list)
    summary: ObservabilitySummaryResponse


class ThroughputPolicyQueueState(BaseModel):
    queue: str
    queued_messages: int
    warning_threshold: int
    critical_threshold: int
    severity: str


class ThroughputPolicyClassState(BaseModel):
    class_name: str
    active_parallelism: int
    minimum_floor: int
    deferred_admission: bool
    reason: str


class ThroughputPolicyStatusResponse(BaseModel):
    requested_preset: str
    active_preset: str
    queue_pressure_level: str
    policy_active: bool
    telemetry_stale: bool
    fail_safe: bool
    fail_safe_reason: str | None = None
    sustained_seconds: int
    sustained_seconds_required: int
    cooldown_seconds: int
    cooldown_remaining_seconds: int
    queue_states: list[ThroughputPolicyQueueState] = Field(default_factory=list)
    class_states: list[ThroughputPolicyClassState] = Field(default_factory=list)
    timestamp: str
