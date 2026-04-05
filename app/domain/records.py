from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.enums import Disposition, EventType


class EDVisitRecordIn(BaseModel):
    record_id: str
    patient_id: str
    patient_name: str | None = None
    date_of_birth: date | None = None
    ssn_last4: str | None = None
    contact_phone: str | None = None
    facility: str
    timestamp: datetime
    event_type: EventType
    acuity_level: int | None = Field(default=None, ge=1, le=5)
    chief_complaint: str | None = None
    disposition: Disposition | None = None
    diagnosis_codes: list[str] = Field(default_factory=list)

    model_config = ConfigDict(use_enum_values=True)

    @field_validator("diagnosis_codes")
    @classmethod
    def normalize_codes(cls, value: list[str]) -> list[str]:
        return sorted({code.strip() for code in value if code and code.strip()})

    @model_validator(mode="after")
    def validate_event_specific_fields(self) -> "EDVisitRecordIn":
        if self.event_type == EventType.TRIAGE and self.acuity_level is None:
            raise ValueError("TRIAGE events require acuity_level")
        return self


class SanitizedRecord(BaseModel):
    record_id: str
    patient_key: str
    facility: str
    timestamp: datetime
    event_type: EventType
    acuity_level: int | None = None
    chief_complaint: str | None = None
    disposition: Disposition | None = None
    diagnosis_codes: list[str] = Field(default_factory=list)
    age_band: str | None = None

    model_config = ConfigDict(use_enum_values=True)

    def canonical_dict(self) -> dict:
        payload = self.model_dump(mode="json")
        payload["diagnosis_codes"] = sorted(set(payload["diagnosis_codes"]))
        return payload


class IngestionResponse(BaseModel):
    status: str
    record_id: str
    canonical_changed: bool
