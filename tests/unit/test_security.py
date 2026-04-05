import pytest

from app.core.config import get_settings
from app.domain.records import EDVisitRecordIn
from app.services.sanitization import derive_age_band, patient_key, sanitize_record


@pytest.mark.unit
def test_patient_key_is_stable():
    settings = get_settings()
    assert patient_key("P-1", settings) == patient_key("P-1", settings)


@pytest.mark.unit
def test_age_band_is_derived():
    record = EDVisitRecordIn(
        record_id="1",
        patient_id="P-1",
        patient_name="Alice",
        date_of_birth="1958-04-12",
        facility="Lakeview Main",
        timestamp="2024-04-01T14:22:00Z",
        event_type="REGISTRATION",
        diagnosis_codes=[],
    )
    assert derive_age_band(record) == "65+"


@pytest.mark.unit
def test_sanitize_record_removes_pii():
    settings = get_settings()
    record = EDVisitRecordIn(
        record_id="1",
        patient_id="P-1",
        patient_name="Alice",
        date_of_birth="1958-04-12",
        ssn_last4="1234",
        contact_phone="555",
        facility="Lakeview Main",
        timestamp="2024-04-01T14:22:00Z",
        event_type="REGISTRATION",
        chief_complaint="pain",
        diagnosis_codes=[],
    )
    payload = sanitize_record(record, settings).canonical_dict()
    assert "patient_name" not in payload
    assert "ssn_last4" not in payload
    assert "contact_phone" not in payload
