import json
from pathlib import Path

import pytest

from app.db.models import CanonicalRecord, RawArrival


@pytest.mark.integration
def test_post_record_creates_raw_and_canonical(client, db_session, sample_record):
    response = client.post("/records", json=sample_record)
    assert response.status_code == 200
    assert response.json()["status"] == "created"
    assert db_session.query(RawArrival).count() == 1
    assert db_session.query(CanonicalRecord).count() == 1


@pytest.mark.integration
def test_duplicate_record_is_ignored(client, db_session, sample_record):
    client.post("/records", json=sample_record)
    response = client.post("/records", json=sample_record)
    assert response.status_code == 200
    assert response.json()["status"] == "duplicate_ignored"
    assert db_session.query(CanonicalRecord).count() == 1
    assert db_session.query(RawArrival).count() == 2


@pytest.mark.integration
def test_canonical_storage_is_sanitized(client, db_session, sample_record):
    client.post("/records", json=sample_record)
    row = db_session.query(CanonicalRecord).one()
    payload = json.loads(row.payload_json)
    assert "patient_name" not in payload
    assert "contact_phone" not in payload
    assert "ssn_last4" not in payload
    assert "patient_key" in payload
    assert row.patient_key is not None


@pytest.mark.integration
def test_triage_requires_acuity_level(client, sample_record):
    payload = dict(sample_record)
    payload["record_id"] = "R-1002"
    payload["event_type"] = "TRIAGE"
    payload["acuity_level"] = None
    response = client.post("/records", json=payload)
    assert response.status_code == 422


@pytest.mark.integration
def test_batch_ingestion(client, db_session, sample_record):
    second = dict(sample_record)
    second["record_id"] = "R-1002"
    second["event_type"] = "TRIAGE"
    second["acuity_level"] = 2
    second["timestamp"] = "2024-04-01T14:35:00Z"

    response = client.post("/records/batch", json=[sample_record, second])
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert db_session.query(CanonicalRecord).count() == 2


@pytest.mark.integration
def test_canonical_timestamp_matches_merged_payload_when_correction_is_newer(client, db_session, sample_record):
    original = dict(sample_record)
    original["event_type"] = "TRIAGE"
    original["acuity_level"] = 4
    original["timestamp"] = "2024-04-01T10:00:00Z"

    corrected = dict(original)
    corrected["timestamp"] = "2024-04-01T10:05:00Z"
    corrected["acuity_level"] = 2

    assert client.post("/records", json=original).status_code == 200
    assert client.post("/records", json=corrected).status_code == 200

    row = db_session.query(CanonicalRecord).filter_by(record_id=original["record_id"]).one()
    payload = json.loads(row.payload_json)
    assert payload["timestamp"] == "2024-04-01T10:05:00Z"
    assert row.event_timestamp.isoformat().startswith("2024-04-01T10:05:00")


@pytest.mark.integration
def test_same_timestamp_later_arrival_wins_for_correction_fields(client, db_session, sample_record):
    original = dict(sample_record)
    original["event_type"] = "TRIAGE"
    original["acuity_level"] = 4
    original["timestamp"] = "2024-04-01T10:00:00Z"

    corrected = dict(original)
    corrected["acuity_level"] = 2
    corrected["chief_complaint"] = "shortness of breath"

    assert client.post("/records", json=original).status_code == 200
    assert client.post("/records", json=corrected).status_code == 200

    row = db_session.query(CanonicalRecord).filter_by(record_id=original["record_id"]).one()
    payload = json.loads(row.payload_json)
    assert payload["acuity_level"] == 2
    assert payload["chief_complaint"] == "shortness of breath"


@pytest.mark.integration
def test_batch_sample_payload_end_to_end(client, db_session):
    payload_path = Path(__file__).resolve().parents[2] / "sample_data" / "batch_payload.json"
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    response = client.post("/records/batch", json=payload)
    assert response.status_code == 200
    assert len(response.json()) == len(payload)
    assert db_session.query(CanonicalRecord).count() > 0
