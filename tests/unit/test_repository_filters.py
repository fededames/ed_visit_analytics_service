from datetime import datetime, timezone

import pytest

from app.db.models import CanonicalRecord
from app.repositories.analytics_repository import AnalyticsRepository


def seed(db_session):
    db_session.add_all([
        CanonicalRecord(record_id="r1", patient_key="a", facility="Lakeview Main", event_timestamp=datetime(2024,4,1,10,0,tzinfo=timezone.utc), event_type="REGISTRATION", acuity_level=None, disposition=None, age_band="50-64", source_arrival_id=1, payload_hash="h1", payload_json="{}"),
        CanonicalRecord(record_id="r2", patient_key="b", facility="Lakeview Main", event_timestamp=datetime(2024,4,2,0,5,tzinfo=timezone.utc), event_type="TRIAGE", acuity_level=2, disposition=None, age_band="35-49", source_arrival_id=2, payload_hash="h2", payload_json="{}"),
        CanonicalRecord(record_id="r3", patient_key="c", facility="Harbor Campus", event_timestamp=datetime(2024,4,2,8,0,tzinfo=timezone.utc), event_type="DISPOSITION", acuity_level=None, disposition="ADMITTED", age_band="65+", source_arrival_id=3, payload_hash="h3", payload_json="{}"),
        CanonicalRecord(record_id="r4", patient_key="d", facility="Harbor Campus", event_timestamp=datetime(2024,4,2,9,0,tzinfo=timezone.utc), event_type="TRIAGE", acuity_level=None, disposition=None, age_band="18-34", source_arrival_id=4, payload_hash="h4", payload_json="{}"),
    ])
    db_session.commit()


@pytest.mark.unit
def test_repository_filters_and_exclusions(db_session):
    seed(db_session)
    repo = AnalyticsRepository(db_session)

    visits = repo.visit_volume_rows(start_date=datetime(2024,4,1).date(), end_date=datetime(2024,4,1).date())
    assert len(visits) == 1
    assert visits[0].visit_count == 1

    acuity = repo.acuity_mix_rows(facility="Lakeview Main")
    assert len(acuity) == 1
    assert acuity[0].acuity_level == 2

    disposition = repo.disposition_mix_rows()
    assert len(disposition) == 1
    assert disposition[0].disposition == "ADMITTED"

from datetime import date
from sqlalchemy import select
from sqlalchemy.dialects import postgresql


def test_repository_date_filters_bind_as_sql_dates(db_session):
    repo = AnalyticsRepository(db_session)
    stmt = select(CanonicalRecord.record_id)
    stmt = repo._apply_filters(stmt, facility="Lakeview Main", start_date=date(2024, 4, 1), end_date=date(2024, 4, 3))
    compiled = stmt.compile(dialect=postgresql.dialect())
    date_bind_types = [str(bind.type) for name, bind in compiled.binds.items() if name.startswith("date_")]

    assert sorted(date_bind_types) == ["DATE", "DATE"]
