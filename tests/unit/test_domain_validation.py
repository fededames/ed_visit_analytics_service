import pytest
from pydantic import ValidationError

from app.domain.records import EDVisitRecordIn


@pytest.mark.unit
def test_triage_requires_acuity():
    with pytest.raises(ValidationError) as exc_info:
        EDVisitRecordIn(
            record_id="1",
            patient_id="p1",
            facility="Lakeview Main",
            timestamp="2024-04-01T10:00:00Z",
            event_type="TRIAGE",
            diagnosis_codes=[],
        )

    assert "TRIAGE events require acuity_level" in str(exc_info.value)
