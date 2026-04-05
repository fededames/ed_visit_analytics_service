import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


TEST_DB_FILE = os.path.join(tempfile.gettempdir(), "ed_analytics_test.db")
DEFAULT_TEST_DATABASE_URL = f"sqlite+pysqlite:///{TEST_DB_FILE}"
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL)

if TEST_DATABASE_URL.startswith("sqlite") and os.path.exists(TEST_DB_FILE):
    os.remove(TEST_DB_FILE)

os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["PATIENT_KEY_SECRET"] = "test-secret"

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db, reset_db_state_for_tests
from app.main import app
from app.db import models  # noqa: F401

reset_db_state_for_tests()


def _engine_kwargs(database_url: str) -> dict:
    kwargs: dict = {"future": True}
    if database_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        kwargs["poolclass"] = StaticPool
    return kwargs


engine = create_engine(TEST_DATABASE_URL, **_engine_kwargs(TEST_DATABASE_URL))
SessionForTests = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session, expire_on_commit=False)


@pytest.fixture(autouse=True)
def reset_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture()
def db_session():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = SessionForTests()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def sample_record():
    return {
        "record_id": "R-1001",
        "patient_id": "P-1001",
        "patient_name": "Test Patient Alice",
        "date_of_birth": "1958-04-12",
        "ssn_last4": "1234",
        "contact_phone": "555-0001",
        "facility": "Lakeview Main",
        "timestamp": "2024-04-01T14:22:00Z",
        "event_type": "REGISTRATION",
        "diagnosis_codes": [],
    }
