import pytest

from app.db.models import MergeConflictRecord


@pytest.mark.integration
def test_conflicts_are_persisted_for_corrected_record(client, db_session):
    original = {
        "record_id": "R-9001",
        "patient_id": "P-9001",
        "patient_name": "Patient",
        "date_of_birth": "1980-01-01",
        "facility": "Lakeview Main",
        "timestamp": "2024-04-01T10:00:00Z",
        "event_type": "TRIAGE",
        "acuity_level": 4,
        "chief_complaint": "pain",
        "diagnosis_codes": ["A01"],
    }
    corrected = {
        **original,
        "timestamp": "2024-04-01T10:05:00Z",
        "acuity_level": 2,
        "chief_complaint": "chest pain radiating to left arm",
        "diagnosis_codes": ["A01", "R07.9"],
    }

    client.post('/records', json=original)
    client.post('/records', json=corrected)

    conflicts = db_session.query(MergeConflictRecord).all()
    assert len(conflicts) >= 3
    fields = {conflict.field_name for conflict in conflicts}
    assert 'acuity_level' in fields
    assert 'timestamp' in fields
    assert 'chief_complaint' in fields
