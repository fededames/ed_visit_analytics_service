from __future__ import annotations

import logging
from datetime import date, datetime
from time import perf_counter
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.analytics import AcuityMixRow, DispositionMixRow, StageLatencyRow, VisitVolumeRow
from app.domain.enums import EventType
from app.domain.errors import InvalidAnalyticsRequest
from app.repositories.analytics_repository import AnalyticsRepository
from app.services.stage_latency import StageLatencyAnalyzer, StageLatencyRequest
from app.services.visit_reconstruction import CanonicalEvent, VisitReconstructor

logger = logging.getLogger(__name__)


def _coerce_to_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise TypeError(f"Unsupported date value type: {type(value)!r}")


def validate_date_range(start_date: date | None, end_date: date | None) -> None:
    if start_date and end_date and start_date > end_date:
        raise InvalidAnalyticsRequest("start_date must be less than or equal to end_date.")


class AnalyticsService:
    def __init__(self, session: Session, settings: Settings) -> None:
        self.repo = AnalyticsRepository(session)
        self.settings = settings
        self.stage_latency_analyzer = StageLatencyAnalyzer(settings)

    def visit_volume(self, facility: str | None, start_date: date | None, end_date: date | None) -> list[VisitVolumeRow]:
        validate_date_range(start_date, end_date)
        started = perf_counter()
        rows = self.repo.visit_volume_rows(facility=facility, start_date=start_date, end_date=end_date)
        result = [VisitVolumeRow(facility=row.facility, day=_coerce_to_date(row.day), visit_count=row.visit_count) for row in rows]
        self._log("visit-volume", facility, len(result), started)
        return result

    def acuity_mix(self, facility: str | None, start_date: date | None, end_date: date | None) -> list[AcuityMixRow]:
        validate_date_range(start_date, end_date)
        started = perf_counter()
        rows = self.repo.acuity_mix_rows(facility=facility, start_date=start_date, end_date=end_date)
        result = [AcuityMixRow(facility=row.facility, acuity_level=int(row.acuity_level), triage_count=row.triage_count) for row in rows]
        self._log("acuity-mix", facility, len(result), started)
        return result

    def disposition_mix(self, facility: str | None, start_date: date | None, end_date: date | None) -> list[DispositionMixRow]:
        validate_date_range(start_date, end_date)
        started = perf_counter()
        rows = self.repo.disposition_mix_rows(facility=facility, start_date=start_date, end_date=end_date)
        result = [DispositionMixRow(facility=row.facility, disposition=row.disposition, disposition_count=row.disposition_count) for row in rows]
        self._log("disposition-mix", facility, len(result), started)
        return result

    def stage_latency(
        self,
        facility: str | None,
        start_date: date | None,
        end_date: date | None,
        from_event: EventType,
        to_event: EventType,
    ) -> list[StageLatencyRow]:
        validate_date_range(start_date, end_date)
        if from_event == to_event:
            raise InvalidAnalyticsRequest("from_event and to_event must be different.")

        started = perf_counter()
        request = StageLatencyRequest(
            facility=facility,
            start_date=start_date,
            end_date=end_date,
            from_event=from_event,
            to_event=to_event,
        )
        reconstructed_visits = self._reconstruct_visits(facility=facility)
        analyzer = getattr(self, "stage_latency_analyzer", StageLatencyAnalyzer(self.settings))
        result = analyzer.analyze(reconstructed_visits, request)
        self._log("stage-latency", facility, len(result), started)
        return result

    def _reconstruct_visits(self, facility: str | None) -> list:
        rows = self.repo.canonical_events()
        events = []
        for row in rows:
            row_facility = row.facility if hasattr(row, "facility") else row["facility"]
            if facility and row_facility != facility:
                continue
            events.append(
                CanonicalEvent(
                    record_id=row.record_id if hasattr(row, "record_id") else row["record_id"],
                    patient_key=row.patient_key if hasattr(row, "patient_key") else row["patient_key"],
                    facility=row_facility,
                    timestamp=row.timestamp if hasattr(row, "timestamp") else row["timestamp"],
                    event_type=row.event_type if hasattr(row, "event_type") else row["event_type"],
                    acuity_level=row.acuity_level if hasattr(row, "acuity_level") else row.get("acuity_level"),
                )
            )
        return VisitReconstructor(self.settings).reconstruct(events)

    def _log(self, endpoint: str, facility: str | None, result_count: int, started: float) -> None:
        logger.info(
            "analytics_query_completed",
            extra={
                "event": "analytics",
                "endpoint": endpoint,
                "facility": facility,
                "result_count": result_count,
                "duration_ms": int((perf_counter() - started) * 1000),
            },
        )
