from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import CanonicalRecord, RawArrival


@dataclass(frozen=True)
class CanonicalEventRow:
    record_id: str
    patient_key: str
    facility: str
    timestamp: datetime
    event_type: str
    acuity_level: int | None = None


class AnalyticsRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _apply_filters(self, stmt, *, facility: str | None = None, start_date: date | None = None, end_date: date | None = None):
        day_expr = func.date(CanonicalRecord.event_timestamp)
        if facility:
            stmt = stmt.where(CanonicalRecord.facility == facility)
        if start_date:
            stmt = stmt.where(day_expr >= start_date)
        if end_date:
            stmt = stmt.where(day_expr <= end_date)
        return stmt

    def visit_volume_rows(self, *, facility: str | None = None, start_date: date | None = None, end_date: date | None = None):
        day_expr = func.date(CanonicalRecord.event_timestamp)
        stmt = (
            select(CanonicalRecord.facility, day_expr.label("day"), func.count().label("visit_count"))
            .where(CanonicalRecord.event_type == "REGISTRATION")
            .group_by(CanonicalRecord.facility, day_expr)
            .order_by(day_expr, CanonicalRecord.facility)
        )
        stmt = self._apply_filters(stmt, facility=facility, start_date=start_date, end_date=end_date)
        return self.session.execute(stmt).all()

    def acuity_mix_rows(self, *, facility: str | None = None, start_date: date | None = None, end_date: date | None = None):
        stmt = (
            select(
                CanonicalRecord.facility,
                CanonicalRecord.acuity_level,
                func.count().label("triage_count"),
            )
            .where(CanonicalRecord.event_type == "TRIAGE")
            .where(CanonicalRecord.acuity_level.is_not(None))
            .group_by(CanonicalRecord.facility, CanonicalRecord.acuity_level)
            .order_by(CanonicalRecord.facility, CanonicalRecord.acuity_level)
        )
        stmt = self._apply_filters(stmt, facility=facility, start_date=start_date, end_date=end_date)
        return self.session.execute(stmt).all()

    def disposition_mix_rows(self, *, facility: str | None = None, start_date: date | None = None, end_date: date | None = None):
        stmt = (
            select(
                CanonicalRecord.facility,
                CanonicalRecord.disposition,
                func.count().label("disposition_count"),
            )
            .where(CanonicalRecord.event_type == "DISPOSITION")
            .where(CanonicalRecord.disposition.is_not(None))
            .group_by(CanonicalRecord.facility, CanonicalRecord.disposition)
            .order_by(CanonicalRecord.facility, CanonicalRecord.disposition)
        )
        stmt = self._apply_filters(stmt, facility=facility, start_date=start_date, end_date=end_date)
        return self.session.execute(stmt).all()

    def canonical_events(self) -> list[CanonicalEventRow]:
        stmt = select(
            CanonicalRecord.record_id,
            CanonicalRecord.patient_key,
            CanonicalRecord.facility,
            CanonicalRecord.event_timestamp,
            CanonicalRecord.event_type,
            CanonicalRecord.acuity_level,
        ).order_by(CanonicalRecord.patient_key, CanonicalRecord.facility, CanonicalRecord.event_timestamp, CanonicalRecord.record_id)
        rows = self.session.execute(stmt).all()
        return [
            CanonicalEventRow(
                record_id=row.record_id,
                patient_key=row.patient_key,
                facility=row.facility,
                timestamp=row.event_timestamp,
                event_type=row.event_type,
                acuity_level=row.acuity_level,
            )
            for row in rows
        ]

    def raw_arrival_payloads(self) -> list[dict]:
        stmt = select(RawArrival.payload_hash, RawArrival.payload_json).order_by(RawArrival.id.asc())
        rows = self.session.execute(stmt).all()
        payloads: list[dict] = []
        for payload_hash_value, payload_json in rows:
            payload = json.loads(payload_json)
            payload["_payload_hash"] = payload_hash_value
            payloads.append(payload)
        return payloads
