from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from app.core.config import get_settings
from app.domain.enums import EventType
from app.domain.errors import InvalidAnalyticsRequest
from app.services.analytics_service import AnalyticsService, _coerce_to_date


def test_coerce_to_date_handles_datetime_before_date_subclass_trap():
    value = datetime(2024, 4, 1, 10, 30)
    assert _coerce_to_date(value) == date(2024, 4, 1)


@pytest.mark.unit
def test_visit_volume_maps_rows_and_logs():
    service = AnalyticsService.__new__(AnalyticsService)
    service.repo = Mock()
    service.settings = get_settings()
    service.repo.visit_volume_rows.return_value = [SimpleNamespace(facility="Lakeview Main", day="2024-04-01", visit_count=2)]

    with patch("app.services.analytics_service.logger") as mocked_logger:
        result = AnalyticsService.visit_volume(service, "Lakeview Main", date(2024, 4, 1), date(2024, 4, 1))

    assert result[0].facility == "Lakeview Main"
    assert result[0].day == date(2024, 4, 1)
    assert result[0].visit_count == 2
    mocked_logger.info.assert_called_once()
    assert mocked_logger.info.call_args.kwargs["extra"]["endpoint"] == "visit-volume"


@pytest.mark.unit
def test_stage_latency_reconstructs_cross_midnight_visits_from_canonical_events_and_reports_quality_counts():
    service = AnalyticsService.__new__(AnalyticsService)
    service.repo = Mock()
    service.settings = get_settings()
    service.repo.canonical_events.return_value = [
        {
            "record_id": "r1",
            "patient_key": "pk-1",
            "facility": "Lakeview Main",
            "timestamp": datetime(2024, 4, 1, 23, 55, tzinfo=timezone.utc),
            "event_type": "REGISTRATION",
            "acuity_level": None,
        },
        {
            "record_id": "r2",
            "patient_key": "pk-1",
            "facility": "Lakeview Main",
            "timestamp": datetime(2024, 4, 2, 0, 5, tzinfo=timezone.utc),
            "event_type": "TRIAGE",
            "acuity_level": 2,
        },
        {
            "record_id": "r3",
            "patient_key": "pk-2",
            "facility": "Lakeview Main",
            "timestamp": datetime(2024, 4, 1, 12, 0, tzinfo=timezone.utc),
            "event_type": "REGISTRATION",
            "acuity_level": None,
        },
    ]

    result = AnalyticsService.stage_latency(
        service,
        facility="Lakeview Main",
        start_date=date(2024, 4, 1),
        end_date=date(2024, 4, 1),
        from_event=EventType.REGISTRATION,
        to_event=EventType.TRIAGE,
    )

    assert [row.model_dump() for row in result] == [
        {
            "facility": "Lakeview Main",
            "day": date(2024, 4, 1),
            "from_event": "REGISTRATION",
            "to_event": "TRIAGE",
            "acuity_level": 2,
            "visit_count_used": 1,
            "visit_count_excluded": 0,
            "missing_stage_count": 0,
            "missing_from_stage_count": 0,
            "missing_to_stage_count": 0,
            "invalid_sequence_count": 0,
            "coverage_ratio": 1.0,
            "average_minutes": 10.0,
            "heuristic_version": "v1",
            "total_visits_considered": 1,
        },
        {
            "facility": "Lakeview Main",
            "day": date(2024, 4, 1),
            "from_event": "REGISTRATION",
            "to_event": "TRIAGE",
            "acuity_level": None,
            "visit_count_used": 0,
            "visit_count_excluded": 1,
            "missing_stage_count": 1,
            "missing_from_stage_count": 0,
            "missing_to_stage_count": 1,
            "invalid_sequence_count": 0,
            "coverage_ratio": 0.0,
            "average_minutes": None,
            "heuristic_version": "v1",
            "total_visits_considered": 1,
        },
    ]


@pytest.mark.unit
def test_stage_latency_splits_two_same_day_visits_for_same_patient_after_departure_and_new_registration():
    service = AnalyticsService.__new__(AnalyticsService)
    service.repo = Mock()
    service.settings = get_settings()
    service.repo.canonical_events.return_value = [
        {"record_id": "r1", "patient_key": "pk-1", "facility": "Lakeview Main", "timestamp": datetime(2024, 4, 1, 8, 0, tzinfo=timezone.utc), "event_type": "REGISTRATION", "acuity_level": None},
        {"record_id": "r2", "patient_key": "pk-1", "facility": "Lakeview Main", "timestamp": datetime(2024, 4, 1, 8, 15, tzinfo=timezone.utc), "event_type": "TRIAGE", "acuity_level": 4},
        {"record_id": "r3", "patient_key": "pk-1", "facility": "Lakeview Main", "timestamp": datetime(2024, 4, 1, 10, 0, tzinfo=timezone.utc), "event_type": "DEPARTURE", "acuity_level": None},
        {"record_id": "r4", "patient_key": "pk-1", "facility": "Lakeview Main", "timestamp": datetime(2024, 4, 1, 15, 0, tzinfo=timezone.utc), "event_type": "REGISTRATION", "acuity_level": None},
        {"record_id": "r5", "patient_key": "pk-1", "facility": "Lakeview Main", "timestamp": datetime(2024, 4, 1, 15, 20, tzinfo=timezone.utc), "event_type": "TRIAGE", "acuity_level": 2},
    ]

    result = AnalyticsService.stage_latency(
        service,
        facility="Lakeview Main",
        start_date=date(2024, 4, 1),
        end_date=date(2024, 4, 1),
        from_event=EventType.REGISTRATION,
        to_event=EventType.TRIAGE,
    )

    assert [row.model_dump() for row in result] == [
        {
            "facility": "Lakeview Main",
            "day": date(2024, 4, 1),
            "from_event": "REGISTRATION",
            "to_event": "TRIAGE",
            "acuity_level": 2,
            "visit_count_used": 1,
            "visit_count_excluded": 0,
            "missing_stage_count": 0,
            "missing_from_stage_count": 0,
            "missing_to_stage_count": 0,
            "invalid_sequence_count": 0,
            "coverage_ratio": 1.0,
            "average_minutes": 20.0,
            "heuristic_version": "v1",
            "total_visits_considered": 1,
        },
        {
            "facility": "Lakeview Main",
            "day": date(2024, 4, 1),
            "from_event": "REGISTRATION",
            "to_event": "TRIAGE",
            "acuity_level": 4,
            "visit_count_used": 1,
            "visit_count_excluded": 0,
            "missing_stage_count": 0,
            "missing_from_stage_count": 0,
            "missing_to_stage_count": 0,
            "invalid_sequence_count": 0,
            "coverage_ratio": 1.0,
            "average_minutes": 15.0,
            "heuristic_version": "v1",
            "total_visits_considered": 1,
        },
    ]


@pytest.mark.unit
def test_analytics_service_rejects_inverted_ranges():
    service = AnalyticsService.__new__(AnalyticsService)
    service.repo = Mock()
    service.settings = get_settings()

    with pytest.raises(InvalidAnalyticsRequest):
        AnalyticsService.visit_volume(service, None, date(2024, 4, 2), date(2024, 4, 1))


@pytest.mark.unit
def test_stage_latency_rejects_same_start_and_end_event():
    service = AnalyticsService.__new__(AnalyticsService)
    service.repo = Mock()
    service.settings = get_settings()

    with pytest.raises(InvalidAnalyticsRequest):
        AnalyticsService.stage_latency(service, None, None, None, EventType.TRIAGE, EventType.TRIAGE)


@pytest.mark.unit
def test_stage_latency_uses_first_valid_to_event_after_from_event():
    service = AnalyticsService.__new__(AnalyticsService)
    service.repo = Mock()
    service.settings = get_settings()
    service.repo.canonical_events.return_value = [
        {
            "record_id": "r1",
            "patient_key": "pk-1",
            "facility": "Lakeview Main",
            "timestamp": datetime(2024, 4, 1, 10, 0, tzinfo=timezone.utc),
            "event_type": "TRIAGE",
            "acuity_level": 4,
        },
        {
            "record_id": "r2",
            "patient_key": "pk-1",
            "facility": "Lakeview Main",
            "timestamp": datetime(2024, 4, 1, 10, 5, tzinfo=timezone.utc),
            "event_type": "REGISTRATION",
            "acuity_level": None,
        },
        {
            "record_id": "r3",
            "patient_key": "pk-1",
            "facility": "Lakeview Main",
            "timestamp": datetime(2024, 4, 1, 10, 20, tzinfo=timezone.utc),
            "event_type": "TRIAGE",
            "acuity_level": 2,
        },
    ]

    result = AnalyticsService.stage_latency(
        service,
        facility="Lakeview Main",
        start_date=date(2024, 4, 1),
        end_date=date(2024, 4, 1),
        from_event=EventType.REGISTRATION,
        to_event=EventType.TRIAGE,
    )

    assert [row.model_dump() for row in result] == [
        {
            "facility": "Lakeview Main",
            "day": date(2024, 4, 1),
            "from_event": "REGISTRATION",
            "to_event": "TRIAGE",
            "acuity_level": 4,
            "visit_count_used": 1,
            "visit_count_excluded": 0,
            "missing_stage_count": 0,
            "missing_from_stage_count": 0,
            "missing_to_stage_count": 0,
            "invalid_sequence_count": 0,
            "coverage_ratio": 1.0,
            "average_minutes": 15.0,
            "heuristic_version": "v1",
            "total_visits_considered": 1,
        }
    ]
