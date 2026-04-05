"""add source_arrival_id and endpoint-scoped idempotency key

Revision ID: 20261003_02
Revises: 20261003_01
Create Date: 2026-10-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20261003_02"
down_revision = "20261003_01"
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _unique_constraints(table_name: str) -> list[dict]:
    bind = op.get_bind()
    inspector = inspect(bind)
    return inspector.get_unique_constraints(table_name)


def upgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    if not _has_column("canonical_records", "source_arrival_id"):
        op.add_column(
            "canonical_records",
            sa.Column("source_arrival_id", sa.Integer(), nullable=False, server_default="0"),
        )
        op.create_index("ix_canonical_records_source_arrival_id", "canonical_records", ["source_arrival_id"])

    uniques = _unique_constraints("idempotency_keys")
    desired = {"endpoint", "idempotency_key"}
    if any(set(constraint.get("column_names") or []) == desired for constraint in uniques):
        return

    old_constraint_names = [
        constraint["name"]
        for constraint in uniques
        if set(constraint.get("column_names") or []) == {"idempotency_key"} and constraint.get("name")
    ]

    if dialect_name == "sqlite":
        with op.batch_alter_table("idempotency_keys", recreate="always") as batch_op:
            for name in old_constraint_names:
                batch_op.drop_constraint(name, type_="unique")
            batch_op.create_unique_constraint("uq_idempotency_endpoint_key", ["endpoint", "idempotency_key"])
    else:
        for name in old_constraint_names:
            op.drop_constraint(name, "idempotency_keys", type_="unique")
        op.create_unique_constraint(
            "uq_idempotency_endpoint_key",
            "idempotency_keys",
            ["endpoint", "idempotency_key"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    uniques = _unique_constraints("idempotency_keys")
    desired = {"endpoint", "idempotency_key"}
    if any(set(constraint.get("column_names") or []) == desired for constraint in uniques):
        if dialect_name == "sqlite":
            with op.batch_alter_table("idempotency_keys", recreate="always") as batch_op:
                batch_op.drop_constraint("uq_idempotency_endpoint_key", type_="unique")
                batch_op.create_unique_constraint("idempotency_keys_idempotency_key_key", ["idempotency_key"])
        else:
            op.drop_constraint("uq_idempotency_endpoint_key", "idempotency_keys", type_="unique")
            op.create_unique_constraint("idempotency_keys_idempotency_key_key", "idempotency_keys", ["idempotency_key"])

    if _has_column("canonical_records", "source_arrival_id"):
        op.drop_index("ix_canonical_records_source_arrival_id", table_name="canonical_records")
        op.drop_column("canonical_records", "source_arrival_id")
