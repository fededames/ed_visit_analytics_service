import pytest

from app.services.record_merger import RecordMerger


@pytest.mark.unit
def test_merge_collects_conflicts_with_field_specific_strategies():
    existing = {
        "record_id": "1",
        "diagnosis_codes": ["A"],
        "disposition": "DISCHARGED",
        "age_band": "50-64",
        "acuity_level": 4,
        "timestamp": "2024-04-01T10:00:00Z",
        "chief_complaint": "pain",
    }
    incoming = {
        "record_id": "1",
        "diagnosis_codes": ["B"],
        "disposition": "ADMITTED",
        "age_band": "65+",
        "acuity_level": 2,
        "timestamp": "2024-04-01T09:55:00Z",
        "chief_complaint": "shortness of breath",
    }
    decision = RecordMerger().merge(existing, incoming)
    assert len(decision.conflicts) == 6
    strategies = {conflict.field: conflict.resolution_strategy for conflict in decision.conflicts}
    assert strategies["diagnosis_codes"] == "union_list_values"
    assert strategies["disposition"] == "prefer_authoritative_payload"
    assert strategies["age_band"] == "keep_existing"
    assert strategies["acuity_level"] == "prefer_authoritative_payload"
    assert strategies["timestamp"] == "prefer_authoritative_payload"
    assert strategies["chief_complaint"] == "prefer_authoritative_payload"
