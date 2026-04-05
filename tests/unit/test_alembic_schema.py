from pathlib import Path
from tempfile import TemporaryDirectory

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_alembic_upgrade_creates_source_arrival_id_and_endpoint_scoped_idempotency_constraint():
    project_root = Path(__file__).resolve().parents[2]
    with TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "alembic_test.db"
        database_url = f"sqlite+pysqlite:///{db_path}"

        config = Config(str(project_root / "alembic.ini"))
        config.set_main_option("script_location", str(project_root / "alembic"))
        config.set_main_option("sqlalchemy.url", database_url)

        command.upgrade(config, "head")

        engine = create_engine(database_url, future=True)
        inspector = inspect(engine)

        canonical_columns = {column["name"] for column in inspector.get_columns("canonical_records")}
        assert "source_arrival_id" in canonical_columns

        unique_constraints = inspector.get_unique_constraints("idempotency_keys")
        endpoint_scoped = [c for c in unique_constraints if set(c["column_names"]) == {"endpoint", "idempotency_key"}]
        assert endpoint_scoped
