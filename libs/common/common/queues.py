"""Canonical queue/topic contracts used by producer and consumer services."""

from dataclasses import dataclass

# The *_PUBSUB variables correspond with the metadata.name field in the
# Dapr pubsub yaml files in infra/dapr/components/pubsub.

ALERTING_PUBSUB = "alerting"
ALERTING_NEW_ALERT_TOPIC = "new_alert"

DOCUMENT_CONVERSION_PUBSUB = "document_conversion"
DOCUMENT_CONVERSION_INPUT_TOPIC = "document_conversion_input"
DOCUMENT_CONVERSION_OUTPUT_TOPIC = "document_conversion_output"

DOTNET_PUBSUB = "dotnet"
DOTNET_INPUT_TOPIC = "dotnet_input"
DOTNET_OUTPUT_TOPIC = "dotnet_output"

DPAPI_PUBSUB = "dpapi"
DPAPI_EVENTS_TOPIC = "dpapi_events"

FILES_PUBSUB = "files"
FILES_NEW_FILE_TOPIC = "new_file"  # Emitted when a new file is uploaded.
FILES_FILE_ENRICHED_TOPIC = "file_enriched"  # Emitted when a file is finished being enriched.
FILES_BULK_ENRICHMENT_TASK_TOPIC = "bulk_enrichment_task"

NOSEYPARKER_PUBSUB = "noseyparker"
NOSEYPARKER_INPUT_TOPIC = "noseyparker_input"
NOSEYPARKER_OUTPUT_TOPIC = "noseyparker_output"

WORKFLOW_MONITOR_PUBSUB = "workflow_monitor"
WORKFLOW_MONITOR_COMPLETED_TOPIC = "workflow_completed"


@dataclass(frozen=True)
class QueueTopicContract:
    pubsub: str
    topic: str
    producers: tuple[str, ...]
    consumers: tuple[str, ...]
    required_payload_keys: tuple[str, ...]

    @property
    def queue_name(self) -> str:
        return f"{self.pubsub}-{self.topic}"


# Keep these contracts focused on cross-service boundaries and queue-monitor topics.
QUEUE_TOPIC_CONTRACTS: tuple[QueueTopicContract, ...] = (
    QueueTopicContract(
        pubsub=FILES_PUBSUB,
        topic=FILES_NEW_FILE_TOPIC,
        producers=(
            "web_api.main.submit_file",
            "web_api.large_containers.ContainerFileProcessor.publish_file_message",
            "document_conversion.activities.publish_file.publish_file_message",
            "file_enrichment.subscriptions.dotnet.process_dotnet_output",
        ),
        consumers=("file_enrichment.controller.file_subscription_handler",),
        required_payload_keys=("object_id", "agent_id", "project", "timestamp", "expiration", "path"),
    ),
    QueueTopicContract(
        pubsub=FILES_PUBSUB,
        topic=FILES_BULK_ENRICHMENT_TASK_TOPIC,
        producers=("web_api.main.start_bulk_enrichment",),
        consumers=("file_enrichment.controller.bulk_enrichment_subscription_handler",),
        required_payload_keys=("enrichment_name", "object_id"),
    ),
    QueueTopicContract(
        pubsub=FILES_PUBSUB,
        topic=FILES_FILE_ENRICHED_TOPIC,
        producers=("file_enrichment.activities.publish_enriched.publish_enriched_file",),
        consumers=("document_conversion.subscriptions.file_enriched.file_enriched_subscription_handler",),
        required_payload_keys=("object_id",),
    ),
    QueueTopicContract(
        pubsub=DOCUMENT_CONVERSION_PUBSUB,
        topic=DOCUMENT_CONVERSION_INPUT_TOPIC,
        producers=("file_enrichment.activities.publish_enriched.publish_enriched_file",),
        consumers=("document_conversion.main.file_enriched_subscription_handler",),
        required_payload_keys=("object_id",),
    ),
    QueueTopicContract(
        pubsub=DOCUMENT_CONVERSION_PUBSUB,
        topic=DOCUMENT_CONVERSION_OUTPUT_TOPIC,
        producers=("document_conversion.workflow",),
        consumers=("external",),
        required_payload_keys=("object_id",),
    ),
    QueueTopicContract(
        pubsub=WORKFLOW_MONITOR_PUBSUB,
        topic=WORKFLOW_MONITOR_COMPLETED_TOPIC,
        producers=("file_enrichment.workflow_completion.publish_workflow_completion",),
        consumers=("web_api.main.process_workflow_completion",),
        required_payload_keys=(
            "object_id",
            "originating_container_id",
            "workflow_id",
            "completed",
            "file_size",
            "timestamp",
        ),
    ),
    QueueTopicContract(
        pubsub=ALERTING_PUBSUB,
        topic=ALERTING_NEW_ALERT_TOPIC,
        producers=(
            "file_enrichment.activities.publish_findings.publish_alerts_for_findings",
            "web_api.main._publish_operational_alert",
        ),
        consumers=("alerting.main.handle_alert",),
        required_payload_keys=("title", "body", "category", "severity"),
    ),
    QueueTopicContract(
        pubsub=DOTNET_PUBSUB,
        topic=DOTNET_INPUT_TOPIC,
        producers=("file_enrichment.workflow",),
        consumers=("external.dotnet_service",),
        required_payload_keys=("object_id",),
    ),
    QueueTopicContract(
        pubsub=DOTNET_PUBSUB,
        topic=DOTNET_OUTPUT_TOPIC,
        producers=("external.dotnet_service",),
        consumers=("file_enrichment.controller.dotnet_subscription_handler",),
        required_payload_keys=("object_id",),
    ),
    QueueTopicContract(
        pubsub=NOSEYPARKER_PUBSUB,
        topic=NOSEYPARKER_INPUT_TOPIC,
        producers=("file_enrichment.activities.plaintext_handler.handle_file_if_plaintext",),
        consumers=("external.noseyparker",),
        required_payload_keys=("object_id", "workflow_id"),
    ),
    QueueTopicContract(
        pubsub=NOSEYPARKER_PUBSUB,
        topic=NOSEYPARKER_OUTPUT_TOPIC,
        producers=("external.noseyparker",),
        consumers=("file_enrichment.controller.noseyparker_subscription_handler",),
        required_payload_keys=("object_id",),
    ),
)

QUEUE_TOPIC_CONTRACT_INDEX: dict[tuple[str, str], QueueTopicContract] = {
    (contract.pubsub, contract.topic): contract for contract in QUEUE_TOPIC_CONTRACTS
}

# This is intentionally topic-keyed for direct consumption by queue monitoring.
TOPIC_TO_QUEUE_NAME: dict[str, str] = {
    contract.topic: contract.queue_name for contract in QUEUE_TOPIC_CONTRACTS
}


def get_queue_name(pubsub: str, topic: str) -> str:
    return f"{pubsub}-{topic}"


def get_queue_contract(pubsub: str, topic: str) -> QueueTopicContract | None:
    return QUEUE_TOPIC_CONTRACT_INDEX.get((pubsub, topic))


def list_queue_contracts() -> tuple[QueueTopicContract, ...]:
    return QUEUE_TOPIC_CONTRACTS


def get_topic_to_queue_name_mapping(topics: list[str] | tuple[str, ...] | None = None) -> dict[str, str]:
    if topics is None:
        return dict(TOPIC_TO_QUEUE_NAME)
    return {topic: TOPIC_TO_QUEUE_NAME[topic] for topic in topics if topic in TOPIC_TO_QUEUE_NAME}
