import json

import pytest

from app.db.models import CanonicalRecord, MergeConflictRecord


@pytest.mark.integration
def test_chief_complaint_latest_non_empty_correction_wins(client, db_session, sample_record):
    first = dict(sample_record)
    first["chief_complaint"] = "pain"

    correction = dict(sample_record)
    correction["chief_complaint"] = "pleuritic chest pain"

    first_response = client.post("/records", json=first)
    correction_response = client.post("/records", json=correction)

    assert first_response.status_code == 200
    assert correction_response.status_code == 200

    row = db_session.query(CanonicalRecord).filter_by(record_id=sample_record["record_id"]).one()
    payload = json.loads(row.payload_json)

    assert payload["chief_complaint"] == "pleuritic chest pain"
    assert db_session.query(MergeConflictRecord).filter_by(
        record_id=sample_record["record_id"],
        field_name="chief_complaint",
    ).count() >= 1
