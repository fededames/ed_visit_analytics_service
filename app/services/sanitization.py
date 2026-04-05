import hashlib
import hmac

from app.core.config import Settings
from app.domain.records import EDVisitRecordIn, SanitizedRecord


def derive_age_band(record: EDVisitRecordIn) -> str | None:
    if record.date_of_birth is None:
        return None

    event_date = record.timestamp.date()
    years = max(
        0,
        event_date.year - record.date_of_birth.year - (
            (event_date.month, event_date.day) < (record.date_of_birth.month, record.date_of_birth.day)
        ),
    )
    if years < 18:
        return "0-17"
    if years < 35:
        return "18-34"
    if years < 50:
        return "35-49"
    if years < 65:
        return "50-64"
    return "65+"


def patient_key(patient_id: str, settings: Settings) -> str:
    return hmac.new(
        settings.patient_key_secret.encode(),
        patient_id.encode(),
        hashlib.sha256,
    ).hexdigest()


def sanitize_record(record: EDVisitRecordIn, settings: Settings) -> SanitizedRecord:
    return SanitizedRecord(
        record_id=record.record_id,
        patient_key=patient_key(record.patient_id, settings),
        facility=record.facility,
        timestamp=record.timestamp,
        event_type=record.event_type,
        acuity_level=record.acuity_level,
        chief_complaint=record.chief_complaint,
        disposition=record.disposition,
        diagnosis_codes=record.diagnosis_codes,
        age_band=derive_age_band(record),
    )
