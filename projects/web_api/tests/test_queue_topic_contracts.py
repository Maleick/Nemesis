"""Queue/topic contract tests for web_api producer and monitor boundaries."""

import asyncio
import json
from datetime import UTC, datetime

from common.models import File as FileModel
from common.queues import (
    ALERTING_NEW_ALERT_TOPIC,
    ALERTING_PUBSUB,
    FILES_NEW_FILE_TOPIC,
    FILES_PUBSUB,
    get_queue_contract,
    get_topic_to_queue_name_mapping,
)
from web_api.queue_monitor import WorkflowQueueMonitor

import web_api.main as web_main


def test_queue_monitor_mapping_matches_canonical_topic_contracts():
    canonical = get_topic_to_queue_name_mapping(WorkflowQueueMonitor.DEFAULT_TOPICS)
    assert canonical, "Expected canonical topic mapping to include monitor topics"

    for topic in WorkflowQueueMonitor.DEFAULT_TOPICS:
        assert WorkflowQueueMonitor.TOPIC_TO_QUEUE_MAPPING[topic] == canonical[topic]


def test_submit_file_publishes_files_new_file_contract(monkeypatch, mock_storage):
    published = {}

    class _FakeDaprClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def publish_event(self, **kwargs):
            published.update(kwargs)

    monkeypatch.setattr(web_main, "DaprClient", _FakeDaprClient)

    file_data = FileModel(
        object_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        agent_id="agent-contract",
        project="project-contract",
        timestamp=datetime(2026, 2, 25, 0, 0, tzinfo=UTC),
        expiration=datetime(2026, 3, 1, 0, 0, tzinfo=UTC),
        path="/tmp/contract.txt",
    )

    submission_id = asyncio.run(web_main.submit_file(file_data))
    assert submission_id is not None
    assert published["pubsub_name"] == FILES_PUBSUB
    assert published["topic_name"] == FILES_NEW_FILE_TOPIC

    payload = json.loads(published["data"])
    contract = get_queue_contract(FILES_PUBSUB, FILES_NEW_FILE_TOPIC)
    assert contract is not None
    for required_key in contract.required_payload_keys:
        assert required_key in payload


def test_operational_alert_publish_uses_alerting_contract(monkeypatch):
    published = {}

    class _FakeDaprClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def publish_event(self, **kwargs):
            published.update(kwargs)

    monkeypatch.setattr(web_main, "DaprClient", _FakeDaprClient)

    emitted = asyncio.run(
        web_main._publish_operational_alert(
            condition="queue_backlog",
            severity="critical",
            message="Queue backlog exceeded threshold",
        )
    )

    assert emitted is True
    assert published["pubsub_name"] == ALERTING_PUBSUB
    assert published["topic_name"] == ALERTING_NEW_ALERT_TOPIC

    payload = json.loads(published["data"])
    contract = get_queue_contract(ALERTING_PUBSUB, ALERTING_NEW_ALERT_TOPIC)
    assert contract is not None
    for required_key in contract.required_payload_keys:
        assert required_key in payload
    assert payload["severity"] >= 1
