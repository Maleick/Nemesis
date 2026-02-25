"""Queue/topic contract tests for file_enrichment producer-consumer boundaries."""

from pathlib import Path

from common.models import Alert
from common.queues import (
    ALERTING_NEW_ALERT_TOPIC,
    ALERTING_PUBSUB,
    DOTNET_OUTPUT_TOPIC,
    DOTNET_PUBSUB,
    FILES_BULK_ENRICHMENT_TASK_TOPIC,
    FILES_NEW_FILE_TOPIC,
    FILES_PUBSUB,
    NOSEYPARKER_OUTPUT_TOPIC,
    NOSEYPARKER_PUBSUB,
    WORKFLOW_MONITOR_COMPLETED_TOPIC,
    WORKFLOW_MONITOR_PUBSUB,
    get_queue_contract,
)


def _source(path_from_repo_root: str) -> str:
    repo_root = Path(__file__).resolve().parents[3]
    return (repo_root / path_from_repo_root).read_text()


def test_contract_metadata_covers_file_enrichment_queue_boundaries():
    contracts = [
        get_queue_contract(FILES_PUBSUB, FILES_NEW_FILE_TOPIC),
        get_queue_contract(FILES_PUBSUB, FILES_BULK_ENRICHMENT_TASK_TOPIC),
        get_queue_contract(NOSEYPARKER_PUBSUB, NOSEYPARKER_OUTPUT_TOPIC),
        get_queue_contract(DOTNET_PUBSUB, DOTNET_OUTPUT_TOPIC),
        get_queue_contract(WORKFLOW_MONITOR_PUBSUB, WORKFLOW_MONITOR_COMPLETED_TOPIC),
        get_queue_contract(ALERTING_PUBSUB, ALERTING_NEW_ALERT_TOPIC),
    ]

    for contract in contracts:
        assert contract is not None
        assert contract.required_payload_keys


def test_controller_subscriptions_use_canonical_queue_constants():
    source = _source("projects/file_enrichment/file_enrichment/controller.py")

    assert "dapr_app.subscribe(pubsub=FILES_PUBSUB, topic=FILES_NEW_FILE_TOPIC)" in source
    assert "dapr_app.subscribe(pubsub=FILES_PUBSUB, topic=FILES_BULK_ENRICHMENT_TASK_TOPIC)" in source
    assert "dapr_app.subscribe(pubsub=NOSEYPARKER_PUBSUB, topic=NOSEYPARKER_OUTPUT_TOPIC)" in source
    assert "dapr_app.subscribe(pubsub=DOTNET_PUBSUB, topic=DOTNET_OUTPUT_TOPIC)" in source


def test_workflow_completion_payload_includes_required_contract_keys():
    source = _source("projects/file_enrichment/file_enrichment/workflow_completion.py")
    required_keys = (
        '"object_id": str(object_id)',
        '"originating_container_id": str(originating_container_id)',
        '"workflow_id": instance_id',
        '"completed": completed',
        '"file_size": file_size',
        '"timestamp": datetime.now().isoformat()',
    )

    for key in required_keys:
        assert key in source

    assert "pubsub_name=WORKFLOW_MONITOR_PUBSUB" in source
    assert "topic_name=WORKFLOW_MONITOR_COMPLETED_TOPIC" in source


def test_alert_publish_uses_canonical_alert_contract():
    source = _source("projects/file_enrichment/file_enrichment/activities/publish_findings.py")
    assert "pubsub_name=ALERTING_PUBSUB" in source
    assert "topic_name=ALERTING_NEW_ALERT_TOPIC" in source

    alert = Alert(
        title="contract-check",
        body="contract-check-body",
        service="file_enrichment",
        category="operational",
        severity=5,
    )
    payload = alert.model_dump(exclude_unset=True)
    contract = get_queue_contract(ALERTING_PUBSUB, ALERTING_NEW_ALERT_TOPIC)
    assert contract is not None
    for required_key in contract.required_payload_keys:
        assert required_key in payload
