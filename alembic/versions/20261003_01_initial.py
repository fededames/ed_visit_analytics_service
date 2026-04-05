"""initial schema

Revision ID: 20261003_01
Revises:
Create Date: 2026-10-03
"""

from alembic import op
import sqlalchemy as sa


revision = "20261003_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "raw_arrivals",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("record_id", sa.String(length=128), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_raw_arrivals_record_id", "raw_arrivals", ["record_id"])
    op.create_index("ix_raw_arrivals_payload_hash", "raw_arrivals", ["payload_hash"])

    op.create_table(
        "canonical_records",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("record_id", sa.String(length=128), nullable=False),
        sa.Column("patient_key", sa.String(length=64), nullable=False),
        sa.Column("facility", sa.String(length=128), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("acuity_level", sa.Integer(), nullable=True),
        sa.Column("disposition", sa.String(length=64), nullable=True),
        sa.Column("age_band", sa.String(length=32), nullable=True),
        sa.Column("source_arrival_id", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("record_id", name="uq_canonical_record_record_id"),
    )
    op.create_index("ix_canonical_records_patient_key", "canonical_records", ["patient_key"])
    op.create_index("ix_canonical_records_facility", "canonical_records", ["facility"])
    op.create_index("ix_canonical_records_event_timestamp", "canonical_records", ["event_timestamp"])
    op.create_index("ix_canonical_records_event_type", "canonical_records", ["event_type"])
    op.create_index("ix_canonical_records_acuity_level", "canonical_records", ["acuity_level"])
    op.create_index("ix_canonical_records_disposition", "canonical_records", ["disposition"])
    op.create_index("ix_canonical_records_source_arrival_id", "canonical_records", ["source_arrival_id"])
    op.create_index("ix_canonical_records_payload_hash", "canonical_records", ["payload_hash"])

    op.create_table(
        "merge_conflicts",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("conflict_hash", sa.String(length=64), nullable=False),
        sa.Column("record_id", sa.String(length=128), nullable=False),
        sa.Column("field_name", sa.String(length=128), nullable=False),
        sa.Column("existing_value_json", sa.Text(), nullable=False),
        sa.Column("incoming_value_json", sa.Text(), nullable=False),
        sa.Column("resolved_value_json", sa.Text(), nullable=False),
        sa.Column("resolution_strategy", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("conflict_hash"),
    )
    op.create_index("ix_merge_conflicts_conflict_hash", "merge_conflicts", ["conflict_hash"])
    op.create_index("ix_merge_conflicts_record_id", "merge_conflicts", ["record_id"])
    op.create_index("ix_merge_conflicts_field_name", "merge_conflicts", ["field_name"])

    op.create_table(
        "idempotency_keys",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("endpoint", sa.String(length=255), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("response_status_code", sa.Integer(), nullable=False),
        sa.Column("response_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("endpoint", "idempotency_key", name="uq_idempotency_endpoint_key"),
    )
    op.create_index("ix_idempotency_keys_idempotency_key", "idempotency_keys", ["idempotency_key"])
    op.create_index("ix_idempotency_keys_endpoint", "idempotency_keys", ["endpoint"])
    op.create_index("ix_idempotency_keys_request_hash", "idempotency_keys", ["request_hash"])


def downgrade() -> None:
    op.drop_index("ix_idempotency_keys_request_hash", table_name="idempotency_keys")
    op.drop_index("ix_idempotency_keys_endpoint", table_name="idempotency_keys")
    op.drop_index("ix_idempotency_keys_idempotency_key", table_name="idempotency_keys")
    op.drop_table("idempotency_keys")
    op.drop_index("ix_merge_conflicts_field_name", table_name="merge_conflicts")
    op.drop_index("ix_merge_conflicts_record_id", table_name="merge_conflicts")
    op.drop_index("ix_merge_conflicts_conflict_hash", table_name="merge_conflicts")
    op.drop_table("merge_conflicts")
    op.drop_index("ix_canonical_records_payload_hash", table_name="canonical_records")
    op.drop_index("ix_canonical_records_source_arrival_id", table_name="canonical_records")
    op.drop_index("ix_canonical_records_disposition", table_name="canonical_records")
    op.drop_index("ix_canonical_records_acuity_level", table_name="canonical_records")
    op.drop_index("ix_canonical_records_event_type", table_name="canonical_records")
    op.drop_index("ix_canonical_records_event_timestamp", table_name="canonical_records")
    op.drop_index("ix_canonical_records_facility", table_name="canonical_records")
    op.drop_index("ix_canonical_records_patient_key", table_name="canonical_records")
    op.drop_table("canonical_records")
    op.drop_index("ix_raw_arrivals_payload_hash", table_name="raw_arrivals")
    op.drop_index("ix_raw_arrivals_record_id", table_name="raw_arrivals")
    op.drop_table("raw_arrivals")
