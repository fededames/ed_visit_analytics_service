from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class VisitVolumeRow(BaseModel):
    facility: str
    day: date
    visit_count: int


class AcuityMixRow(BaseModel):
    facility: str
    acuity_level: int
    triage_count: int


class DispositionMixRow(BaseModel):
    facility: str
    disposition: str
    disposition_count: int


class StageLatencyRow(BaseModel):
    facility: str
    day: date
    from_event: str
    to_event: str
    acuity_level: int | None = None
    visit_count_used: int
    visit_count_excluded: int
    total_visits_considered: int
    missing_stage_count: int
    missing_from_stage_count: int = 0
    missing_to_stage_count: int = 0
    invalid_sequence_count: int = 0
    coverage_ratio: float | None = None
    average_minutes: float | None
    heuristic_version: str
