from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CanonicalRecord, MergeConflictRecord, RawArrival
from app.domain.conflicts import MergeConflict
from app.services.hashing import payload_hash


class IngestionRepository:
    """Write-oriented repository for raw arrivals, canonical records, and merge conflicts."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def append_raw_arrival(self, record_id: str, payload_json: str, payload_hash_value: str) -> RawArrival:
        row = RawArrival(
            record_id=record_id,
            payload_json=payload_json,
            payload_hash=payload_hash_value,
        )
        self._session.add(row)
        self._session.flush()
        return row

    def get_canonical_by_record_id(self, record_id: str) -> CanonicalRecord | None:
        stmt = select(CanonicalRecord).where(CanonicalRecord.record_id == record_id)
        return self._session.execute(stmt).scalar_one_or_none()

    def upsert_canonical(
        self,
        *,
        record_id: str,
        patient_key: str,
        facility: str,
        event_timestamp: datetime,
        event_type: str,
        acuity_level: int | None,
        disposition: str | None,
        age_band: str | None,
        source_arrival_id: int,
        payload_json: str,
        payload_hash_value: str,
    ) -> None:
        row = self.get_canonical_by_record_id(record_id)
        if row is None:
            self._session.add(
                CanonicalRecord(
                    record_id=record_id,
                    patient_key=patient_key,
                    facility=facility,
                    event_timestamp=event_timestamp,
                    event_type=event_type,
                    acuity_level=acuity_level,
                    disposition=disposition,
                    age_band=age_band,
                    source_arrival_id=source_arrival_id,
                    payload_json=payload_json,
                    payload_hash=payload_hash_value,
                )
            )
            return

        row.patient_key = patient_key
        row.facility = facility
        row.event_timestamp = event_timestamp
        row.event_type = event_type
        row.acuity_level = acuity_level
        row.disposition = disposition
        row.age_band = age_band
        row.source_arrival_id = source_arrival_id
        row.payload_json = payload_json
        row.payload_hash = payload_hash_value

    def append_merge_conflicts(self, conflicts: list[MergeConflict]) -> None:
        for conflict in conflicts:
            fingerprint_payload = {
                "record_id": conflict.record_id,
                "field": conflict.field,
                "existing_value": conflict.existing_value,
                "incoming_value": conflict.incoming_value,
                "resolved_value": conflict.resolved_value,
                "resolution_strategy": conflict.resolution_strategy,
            }
            conflict_hash = payload_hash(fingerprint_payload)
            stmt = select(MergeConflictRecord).where(MergeConflictRecord.conflict_hash == conflict_hash)
            if self._session.execute(stmt).scalar_one_or_none() is not None:
                continue

            self._session.add(
                MergeConflictRecord(
                    conflict_hash=conflict_hash,
                    record_id=conflict.record_id,
                    field_name=conflict.field,
                    existing_value_json=json.dumps(conflict.existing_value, default=str),
                    incoming_value_json=json.dumps(conflict.incoming_value, default=str),
                    resolved_value_json=json.dumps(conflict.resolved_value, default=str),
                    resolution_strategy=conflict.resolution_strategy,
                )
            )
