"""Smoke tests for upload -> workflow lifecycle -> retrieval contracts."""

from datetime import UTC, datetime
import json
from uuid import UUID


def _metadata_payload(path: str, include_time_fields: bool = True) -> str:
    payload = {
        "agent_id": "agent-smoke",
        "project": "project-smoke",
        "path": path,
        "source": "unit-test",
    }
    if include_time_fields:
        payload["timestamp"] = "2026-02-25T00:00:00+00:00"
        payload["expiration"] = "2026-05-01T00:00:00+00:00"
    return json.dumps(payload)


def test_upload_lifecycle_download_smoke_contract(client, mock_storage, monkeypatch):
    object_id = "11111111-1111-1111-1111-111111111111"
    submission_id = "22222222-2222-2222-2222-222222222222"
    mock_storage.upload_uploadfile.return_value = object_id
    mock_storage.download_bytes.return_value = b"hello"

    captured = {}

    async def _mock_submit_file(file_data):
        captured["file_data"] = file_data
        return UUID(submission_id)

    def _mock_lifecycle_payload(_object_id: str):
        assert _object_id == object_id
        return {
            "object_id": object_id,
            "ingestion": {
                "object_id": object_id,
                "agent_id": "agent-smoke",
                "source": "unit-test",
                "project": "project-smoke",
                "path": "/C:/ops/drop/sample.txt",
                "file_name": "sample.txt",
                "ingested_at": datetime(2026, 2, 25, 0, 0, tzinfo=UTC),
                "observed_at": datetime(2026, 2, 25, 0, 1, tzinfo=UTC),
            },
            "workflows": [
                {
                    "workflow_id": f"FileEnrichment.smoke.{object_id}",
                    "status": "COMPLETED",
                    "started_at": datetime(2026, 2, 25, 0, 2, tzinfo=UTC),
                    "runtime_seconds": 1.2,
                    "filename": "sample.txt",
                    "success_modules": ["noseyparker"],
                    "failure_modules": [],
                    "error": None,
                }
            ],
            "publication": {
                "enrichments_count": 1,
                "transforms_count": 0,
                "findings_count": 0,
                "last_enrichment_at": datetime(2026, 2, 25, 0, 3, tzinfo=UTC),
                "last_transform_at": None,
                "last_finding_at": None,
            },
            "summary": {
                "latest_status": "COMPLETED",
                "workflow_count": 1,
                "running_count": 0,
                "completed_count": 1,
                "failed_count": 0,
            },
            "timestamp": "2026-02-25T00:04:00+00:00",
        }

    monkeypatch.setattr("web_api.main.submit_file", _mock_submit_file)
    monkeypatch.setattr("web_api.main._fetch_object_lifecycle_payload", _mock_lifecycle_payload)

    upload_response = client.post(
        "/files",
        files={"file": ("sample.txt", b"hello world", "text/plain")},
        data={"metadata": _metadata_payload(r"C:\ops\drop\sample.txt")},
    )

    assert upload_response.status_code == 200
    assert upload_response.json() == {"object_id": object_id, "submission_id": submission_id}
    assert captured["file_data"].path == "/C:/ops/drop/sample.txt"
    mock_storage.upload_uploadfile.assert_called_once()

    lifecycle_response = client.get(f"/workflows/lifecycle/{object_id}")
    assert lifecycle_response.status_code == 200
    lifecycle_payload = lifecycle_response.json()
    assert lifecycle_payload["summary"]["latest_status"] == "COMPLETED"
    assert lifecycle_payload["ingestion"]["agent_id"] == "agent-smoke"

    download_response = client.get(f"/files/{object_id}?offset=0&length=5")
    assert download_response.status_code == 200
    assert download_response.content == b"hello"
    mock_storage.download_bytes.assert_called_once_with(object_id, 0, 5)


def test_upload_sets_default_timestamp_and_expiration_when_missing(client, mock_storage, monkeypatch):
    object_id = "33333333-3333-3333-3333-333333333333"
    submission_id = UUID("44444444-4444-4444-4444-444444444444")
    mock_storage.upload_uploadfile.return_value = object_id

    captured = {}

    async def _mock_submit_file(file_data):
        captured["file_data"] = file_data
        return submission_id

    monkeypatch.setattr("web_api.main.submit_file", _mock_submit_file)

    response = client.post(
        "/files",
        files={"file": ("defaults.txt", b"defaults", "text/plain")},
        data={"metadata": _metadata_payload("/tmp/defaults.txt", include_time_fields=False)},
    )
    assert response.status_code == 200
    assert response.json()["object_id"] == object_id
    assert response.json()["submission_id"] == str(submission_id)

    file_data = captured["file_data"]
    assert file_data.timestamp is not None
    assert file_data.expiration is not None
    assert file_data.expiration > file_data.timestamp
