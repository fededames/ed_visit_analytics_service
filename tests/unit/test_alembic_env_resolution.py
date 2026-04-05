from app.db.alembic_config import resolve_database_url


def test_resolve_database_url_prefers_explicit_config_over_environment_url():
    assert resolve_database_url("sqlite:///./configured.db", "sqlite:///./settings.db", "postgresql+psycopg://postgres:postgres@localhost:5432/ed_analytics") == "sqlite:///./configured.db"


def test_resolve_database_url_uses_environment_url_when_config_is_placeholder():
    assert resolve_database_url("driver://", "sqlite:///./settings.db", "postgresql+psycopg://postgres:postgres@localhost:5432/ed_analytics") == "postgresql+psycopg://postgres:postgres@localhost:5432/ed_analytics"


def test_resolve_database_url_falls_back_to_settings_for_placeholder_without_environment():
    assert resolve_database_url("driver://", "sqlite:///./settings.db", None) == "sqlite:///./settings.db"
