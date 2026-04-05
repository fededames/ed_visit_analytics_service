import json

import pytest

from app.db.models import CanonicalRecord


@pytest.mark.integration
def test_out_of_order_correction_arrival_keeps_canonical_consistent(client, db_session):
    correction = {
        "record_id": "R-7001",
        "patient_id": "P-7001",
        "patient_name": "Late Original",
        "date_of_birth": "1984-04-01",
        "facility": "Lakeview Main",
        "timestamp": "2024-04-01T10:10:00Z",
        "event_type": "TRIAGE",
        "acuity_level": 2,
        "chief_complaint": "severe chest pain radiating to left arm",
        "diagnosis_codes": ["R07.9"],
    }
    original = {
        "record_id": "R-7001",
        "patient_id": "P-7001",
        "patient_name": "Late Original",
        "date_of_birth": "1984-04-01",
        "facility": "Lakeview Main",
        "timestamp": "2024-04-01T10:00:00Z",
        "event_type": "TRIAGE",
        "acuity_level": 4,
        "chief_complaint": "chest pain",
        "diagnosis_codes": [],
    }

    first = client.post("/records", json=correction)
    assert first.status_code == 200
    assert first.json()["status"] == "created"

    second = client.post("/records", json=original)
    assert second.status_code == 200
    assert second.json()["status"] == "duplicate_ignored"

    canonical = db_session.query(CanonicalRecord).filter(CanonicalRecord.record_id == "R-7001").one()
    payload = json.loads(canonical.payload_json)

    assert canonical.event_timestamp.isoformat() == "2024-04-01T10:10:00"
    assert payload["timestamp"] == "2024-04-01T10:10:00Z"
    assert payload["acuity_level"] == 2
    assert payload["chief_complaint"] == "severe chest pain radiating to left arm"
