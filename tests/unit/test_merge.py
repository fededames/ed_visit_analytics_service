import pytest

from app.services.record_merger import RecordMerger


@pytest.mark.unit
def test_merge_creates_when_missing():
    decision = RecordMerger().merge(None, {"record_id": "1", "diagnosis_codes": [], "disposition": None})
    assert decision.changed is True
    assert decision.reason == "created"


@pytest.mark.unit
def test_merge_ignores_exact_duplicate():
    payload = {"record_id": "1", "diagnosis_codes": ["A"]}
    decision = RecordMerger().merge(payload, payload)
    assert decision.changed is False
    assert decision.reason == "duplicate_ignored"


@pytest.mark.unit
def test_merge_unions_diagnosis_codes():
    existing = {"record_id": "1", "diagnosis_codes": ["A"], "disposition": None}
    incoming = {"record_id": "1", "diagnosis_codes": ["B"], "disposition": None}
    decision = RecordMerger().merge(existing, incoming, existing_arrival_id=1, incoming_arrival_id=2)
    assert decision.payload["diagnosis_codes"] == ["A", "B"]


@pytest.mark.unit
def test_merge_prefers_same_or_newer_timestamp_corrections_for_clinical_fields():
    existing = {
        "record_id": "1",
        "timestamp": "2024-04-01T10:00:00Z",
        "diagnosis_codes": [],
        "disposition": "DISCHARGED",
        "chief_complaint": "pain",
    }
    incoming = {
        "record_id": "1",
        "timestamp": "2024-04-01T10:00:00Z",
        "diagnosis_codes": [],
        "disposition": "ADMITTED",
        "chief_complaint": "shortness of breath",
    }
    decision = RecordMerger().merge(existing, incoming, existing_arrival_id=1, incoming_arrival_id=2)
    assert decision.payload["disposition"] == "ADMITTED"
    assert decision.payload["chief_complaint"] == "shortness of breath"


@pytest.mark.unit
def test_merge_keeps_existing_clinical_fields_when_incoming_event_timestamp_is_older():
    existing = {
        "record_id": "1",
        "timestamp": "2024-04-01T10:10:00Z",
        "diagnosis_codes": [],
        "acuity_level": 2,
        "chief_complaint": "severe chest pain",
    }
    incoming = {
        "record_id": "1",
        "timestamp": "2024-04-01T10:00:00Z",
        "diagnosis_codes": [],
        "acuity_level": 4,
        "chief_complaint": "chest pain",
    }
    decision = RecordMerger().merge(existing, incoming, existing_arrival_id=1, incoming_arrival_id=2)
    assert decision.payload["acuity_level"] == 2
    assert decision.payload["chief_complaint"] == "severe chest pain"


@pytest.mark.unit
def test_merge_prefers_later_arrival_when_event_timestamp_ties():
    existing = {
        "record_id": "1",
        "timestamp": "2024-04-01T10:00:00Z",
        "diagnosis_codes": [],
        "disposition": "DISCHARGED",
    }
    incoming = {
        "record_id": "1",
        "timestamp": "2024-04-01T10:00:00Z",
        "diagnosis_codes": [],
        "disposition": "ADMITTED",
    }
    decision = RecordMerger().merge(existing, incoming, existing_arrival_id=1, incoming_arrival_id=2)
    assert decision.payload["disposition"] == "ADMITTED"
