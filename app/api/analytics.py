from __future__ import annotations

import logging
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.domain.analytics import AcuityMixRow, DispositionMixRow, StageLatencyRow, VisitVolumeRow
from app.domain.enums import EventType
from app.services.analytics_service import AnalyticsService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["analytics"])


def _normalize_facility(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None


def _log_request(endpoint: str, facility: str | None, start_date: date | None, end_date: date | None) -> None:
    logger.info(
        "api_analytics_request",
        extra={"event": "api", "endpoint": endpoint, "facility": facility, "start_date": start_date, "end_date": end_date},
    )


def _log_response(endpoint: str, result_count: int) -> None:
    logger.info("api_analytics_response", extra={"event": "api", "endpoint": endpoint, "result_count": result_count})


@router.get(
    "/analytics/visit-volume",
    response_model=list[VisitVolumeRow],
    summary="Visit starts by day and facility",
    description="Counts current canonical REGISTRATION records by day and facility as a lightweight proxy for visit starts.",
)
def visit_volume(
    facility: str | None = Query(default=None, description="Optional facility filter."),
    start_date: date | None = Query(default=None, description="Inclusive lower bound in YYYY-MM-DD format."),
    end_date: date | None = Query(default=None, description="Inclusive upper bound in YYYY-MM-DD format."),
    session: Session = Depends(get_db),
) -> list[VisitVolumeRow]:
    facility = _normalize_facility(facility)
    _log_request("visit-volume", facility, start_date, end_date)
    result = AnalyticsService(session, get_settings()).visit_volume(facility, start_date, end_date)
    _log_response("visit-volume", len(result))
    return result


@router.get(
    "/analytics/acuity-mix",
    response_model=list[AcuityMixRow],
    summary="Triage acuity mix by facility",
    description="Counts current canonical TRIAGE records with non-null acuity levels.",
)
def acuity_mix(
    facility: str | None = Query(default=None, description="Optional facility filter."),
    start_date: date | None = Query(default=None, description="Inclusive lower bound in YYYY-MM-DD format."),
    end_date: date | None = Query(default=None, description="Inclusive upper bound in YYYY-MM-DD format."),
    session: Session = Depends(get_db),
) -> list[AcuityMixRow]:
    facility = _normalize_facility(facility)
    _log_request("acuity-mix", facility, start_date, end_date)
    result = AnalyticsService(session, get_settings()).acuity_mix(facility, start_date, end_date)
    _log_response("acuity-mix", len(result))
    return result


@router.get(
    "/analytics/disposition-mix",
    response_model=list[DispositionMixRow],
    summary="Disposition mix by facility",
    description="Counts current canonical DISPOSITION records with non-null outcome values.",
)
def disposition_mix(
    facility: str | None = Query(default=None, description="Optional facility filter."),
    start_date: date | None = Query(default=None, description="Inclusive lower bound in YYYY-MM-DD format."),
    end_date: date | None = Query(default=None, description="Inclusive upper bound in YYYY-MM-DD format."),
    session: Session = Depends(get_db),
) -> list[DispositionMixRow]:
    facility = _normalize_facility(facility)
    _log_request("disposition-mix", facility, start_date, end_date)
    result = AnalyticsService(session, get_settings()).disposition_mix(facility, start_date, end_date)
    _log_response("disposition-mix", len(result))
    return result


@router.get(
    "/analytics/stage-latency",
    response_model=list[StageLatencyRow],
    summary="Average latency between two ED lifecycle stages",
    description="Heuristically reconstructs visits from canonical events using patient, facility, rolling time windows, and visit-closing stages, then computes average minutes between two lifecycle stages.",
)
def stage_latency(
    facility: str | None = Query(default=None, description="Optional facility filter."),
    start_date: date | None = Query(default=None, description="Inclusive lower bound in YYYY-MM-DD format."),
    end_date: date | None = Query(default=None, description="Inclusive upper bound in YYYY-MM-DD format."),
    from_event: EventType = Query(default=EventType.REGISTRATION, description="Lifecycle stage used as the starting timestamp."),
    to_event: EventType = Query(default=EventType.TRIAGE, description="Lifecycle stage used as the ending timestamp."),
    session: Session = Depends(get_db),
) -> list[StageLatencyRow]:
    facility = _normalize_facility(facility)
    _log_request("stage-latency", facility, start_date, end_date)
    result = AnalyticsService(session, get_settings()).stage_latency(facility, start_date, end_date, from_event, to_event)
    _log_response("stage-latency", len(result))
    return result
