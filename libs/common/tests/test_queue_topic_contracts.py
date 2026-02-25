"""Contract metadata tests for shared queue/topic definitions."""

from common.queues import (
    ALERTING_NEW_ALERT_TOPIC,
    ALERTING_PUBSUB,
    FILES_NEW_FILE_TOPIC,
    FILES_PUBSUB,
    get_queue_contract,
    get_queue_name,
    get_topic_to_queue_name_mapping,
    list_queue_contracts,
)


def test_get_queue_name_builds_dapr_queue_convention():
    assert get_queue_name("files", "new_file") == "files-new_file"


def test_queue_contract_lookup_returns_expected_contract():
    contract = get_queue_contract(FILES_PUBSUB, FILES_NEW_FILE_TOPIC)
    assert contract is not None
    assert contract.pubsub == FILES_PUBSUB
    assert contract.topic == FILES_NEW_FILE_TOPIC
    assert contract.queue_name == "files-new_file"


def test_topic_to_queue_mapping_contains_core_topics():
    mapping = get_topic_to_queue_name_mapping()
    assert mapping[FILES_NEW_FILE_TOPIC] == "files-new_file"
    assert mapping[ALERTING_NEW_ALERT_TOPIC] == "alerting-new_alert"


def test_contract_inventory_is_non_empty_and_structured():
    contracts = list_queue_contracts()
    assert contracts
    for contract in contracts:
        assert contract.pubsub
        assert contract.topic
        assert contract.required_payload_keys
