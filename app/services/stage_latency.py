from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable

from app.core.config import Settings
from app.domain.analytics import StageLatencyRow
from app.domain.enums import EventType
from app.services.visit_reconstruction import ReconstructedVisit


@dataclass(frozen=True)
class StageLatencyRequest:
    facility: str | None
    start_date: date | None
    end_date: date | None
    from_event: EventType
    to_event: EventType


@dataclass
class StageLatencyAccumulator:
    total_minutes: float = 0.0
    visit_count_used: int = 0
    visit_count_excluded: int = 0
    missing_stage_count: int = 0
    missing_from_stage_count: int = 0
    missing_to_stage_count: int = 0
    invalid_sequence_count: int = 0

    @property
    def total_visits_considered(self) -> int:
        return self.visit_count_used + self.visit_count_excluded

    @property
    def coverage_ratio(self) -> float | None:
        if self.total_visits_considered == 0:
            return None
        return round(self.visit_count_used / self.total_visits_considered, 3)

    @property
    def average_minutes(self) -> float | None:
        if self.visit_count_used == 0:
            return None
        return round(self.total_minutes / self.visit_count_used, 1)


class StageLatencyAnalyzer:
    def __init__(self, settings: Settings) -> None:
        self._heuristic_version = settings.stage_latency_heuristic_version

    def analyze(self, visits: Iterable[ReconstructedVisit], request: StageLatencyRequest) -> list[StageLatencyRow]:
        aggregates: dict[tuple[str, date, int | None], StageLatencyAccumulator] = defaultdict(StageLatencyAccumulator)

        for visit in visits:
            from_ts = self._first_event_timestamp(visit, request.from_event.value)
            to_ts = self._first_event_at_or_after(visit, request.to_event.value, from_ts) if from_ts is not None else None
            has_any_to_event = bool(visit.event_history.get(request.to_event.value))
            day = from_ts.date() if from_ts is not None else visit.opened_at.date()

            if request.start_date and day < request.start_date:
                continue
            if request.end_date and day > request.end_date:
                continue

            aggregate = aggregates[(visit.facility, day, visit.triage_acuity)]

            if from_ts is None:
                aggregate.visit_count_excluded += 1
                aggregate.missing_stage_count += 1
                aggregate.missing_from_stage_count += 1
                continue

            if to_ts is None:
                aggregate.visit_count_excluded += 1
                aggregate.missing_stage_count += 1
                if has_any_to_event:
                    aggregate.invalid_sequence_count += 1
                else:
                    aggregate.missing_to_stage_count += 1
                continue

            aggregate.total_minutes += (to_ts - from_ts).total_seconds() / 60.0
            aggregate.visit_count_used += 1

        return [
            StageLatencyRow(
                facility=payload_facility,
                day=day,
                from_event=request.from_event.value,
                to_event=request.to_event.value,
                acuity_level=acuity_level,
                visit_count_used=values.visit_count_used,
                visit_count_excluded=values.visit_count_excluded,
                total_visits_considered=values.total_visits_considered,
                missing_stage_count=values.missing_stage_count,
                missing_from_stage_count=values.missing_from_stage_count,
                missing_to_stage_count=values.missing_to_stage_count,
                invalid_sequence_count=values.invalid_sequence_count,
                coverage_ratio=values.coverage_ratio,
                average_minutes=values.average_minutes,
                heuristic_version=self._heuristic_version,
            )
            for (payload_facility, day, acuity_level), values in sorted(
                aggregates.items(), key=lambda item: (item[0][1], item[0][0], item[0][2] if item[0][2] is not None else 99)
            )
        ]

    @staticmethod
    def _first_event_timestamp(visit: ReconstructedVisit, event_type: str) -> datetime | None:
        history = visit.event_history.get(event_type, [])
        return history[0] if history else None

    @staticmethod
    def _first_event_at_or_after(visit: ReconstructedVisit, event_type: str, reference_ts: datetime | None) -> datetime | None:
        if reference_ts is None:
            return None
        for candidate in visit.event_history.get(event_type, []):
            if candidate >= reference_ts:
                return candidate
        return None
