"""Queue/topic contract tests for alerting consumer boundaries."""

from pathlib import Path

from common.models import Alert
from common.queues import ALERTING_NEW_ALERT_TOPIC, ALERTING_PUBSUB, get_queue_contract


def test_alerting_contract_metadata_is_defined():
    contract = get_queue_contract(ALERTING_PUBSUB, ALERTING_NEW_ALERT_TOPIC)
    assert contract is not None
    assert contract.consumers
    assert contract.required_payload_keys


def test_alerting_subscription_uses_canonical_constants():
    repo_root = Path(__file__).resolve().parents[3]
    source = (repo_root / "projects/alerting/alerting/main.py").read_text()

    assert "@dapr_app.subscribe(pubsub=ALERTING_PUBSUB, topic=ALERTING_NEW_ALERT_TOPIC)" in source
    assert "async def handle_alert(event: CloudEvent[Alert]):" in source


def test_alert_payload_shape_matches_contract_requirements():
    payload = Alert(
        title="queue-contract",
        body="contract-message",
        service="web_api",
        category="operational_observability",
        severity=9,
    ).model_dump(exclude_unset=True)

    contract = get_queue_contract(ALERTING_PUBSUB, ALERTING_NEW_ALERT_TOPIC)
    assert contract is not None
    for required_key in contract.required_payload_keys:
        assert required_key in payload
