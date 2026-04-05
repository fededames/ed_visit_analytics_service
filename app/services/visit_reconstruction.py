from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Iterable

from app.core.config import Settings
from app.domain.enums import EventType

FINAL_STAGE_EVENTS = {EventType.DISPOSITION.value, EventType.DEPARTURE.value}
EARLY_STAGE_EVENTS = {EventType.REGISTRATION.value, EventType.TRIAGE.value}


@dataclass
class CanonicalEvent:
    record_id: str
    patient_key: str
    facility: str
    timestamp: datetime
    event_type: str
    acuity_level: int | None = None


@dataclass
class ReconstructedVisit:
    patient_key: str
    facility: str
    opened_at: datetime
    last_event_at: datetime
    closed_at: datetime | None = None
    event_timestamps: dict[str, datetime] = field(default_factory=dict)
    event_history: dict[str, list[datetime]] = field(default_factory=dict)
    triage_acuity: int | None = None

    def attach(self, event: CanonicalEvent) -> None:
        self.last_event_at = max(self.last_event_at, event.timestamp)
        existing_ts = self.event_timestamps.get(event.event_type)
        if existing_ts is None or event.timestamp < existing_ts:
            self.event_timestamps[event.event_type] = event.timestamp
        self.event_history.setdefault(event.event_type, []).append(event.timestamp)
        if event.event_type == EventType.TRIAGE.value and event.acuity_level is not None:
            triage_ts = self.event_timestamps.get(EventType.TRIAGE.value)
            if triage_ts is None or event.timestamp <= triage_ts:
                self.triage_acuity = int(event.acuity_level)
        if event.event_type in FINAL_STAGE_EVENTS:
            self.closed_at = event.timestamp if self.closed_at is None else max(self.closed_at, event.timestamp)


class VisitReconstructor:
    """Groups canonical events into analytical visits using a rolling time window.

    This intentionally uses soft lifecycle cues rather than a rigid state machine:
    visits can span midnight, multiple same-day visits are less likely to collapse,
    and clearly closed visits are not reopened by later early-stage events.
    """

    def __init__(self, settings: Settings) -> None:
        self._window = timedelta(hours=settings.visit_reconstruction_window_hours)
        self._inactive_gap = timedelta(hours=settings.visit_inactive_gap_hours)
        self._closed_visit_grace = timedelta(minutes=30)

    def reconstruct(self, events: Iterable[CanonicalEvent]) -> list[ReconstructedVisit]:
        grouped: dict[tuple[str, str], list[CanonicalEvent]] = {}
        for event in events:
            grouped.setdefault((event.patient_key, event.facility), []).append(event)

        visits: list[ReconstructedVisit] = []
        for (patient_key, facility), patient_events in grouped.items():
            patient_events.sort(key=lambda item: (item.timestamp, item.record_id))
            patient_visits: list[ReconstructedVisit] = []
            for event in patient_events:
                visit = self._find_candidate_visit(patient_visits, event)
                if visit is None:
                    visit = ReconstructedVisit(
                        patient_key=patient_key,
                        facility=facility,
                        opened_at=event.timestamp,
                        last_event_at=event.timestamp,
                    )
                    patient_visits.append(visit)
                visit.attach(event)
            visits.extend(patient_visits)

        visits.sort(key=lambda item: (item.opened_at, item.facility, item.patient_key))
        return visits

    def _find_candidate_visit(self, visits: list[ReconstructedVisit], event: CanonicalEvent) -> ReconstructedVisit | None:
        for visit in reversed(visits):
            if event.timestamp < visit.opened_at:
                continue
            if event.timestamp - visit.opened_at > self._window:
                continue
            if event.timestamp - visit.last_event_at > self._inactive_gap:
                continue
            if visit.closed_at is not None:
                if event.timestamp - visit.closed_at > self._closed_visit_grace:
                    continue
                if event.event_type in EARLY_STAGE_EVENTS and event.timestamp >= visit.closed_at:
                    continue
            if event.event_type == EventType.REGISTRATION.value:
                if EventType.REGISTRATION.value in visit.event_timestamps:
                    continue
            return visit
        return None
