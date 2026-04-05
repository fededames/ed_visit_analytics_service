from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RawArrival(Base):
    __tablename__ = "raw_arrivals"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    record_id: Mapped[str] = mapped_column(String(128), index=True)
    payload_hash: Mapped[str] = mapped_column(String(64), index=True)
    payload_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CanonicalRecord(Base):
    __tablename__ = "canonical_records"
    __table_args__ = (UniqueConstraint("record_id", name="uq_canonical_record_record_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    record_id: Mapped[str] = mapped_column(String(128), nullable=False)
    patient_key: Mapped[str] = mapped_column(String(64), index=True)
    facility: Mapped[str] = mapped_column(String(128), index=True)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    acuity_level: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    disposition: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    age_band: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_arrival_id: Mapped[int] = mapped_column(Integer, index=True, default=0)
    payload_hash: Mapped[str] = mapped_column(String(64), index=True)
    payload_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class MergeConflictRecord(Base):
    __tablename__ = "merge_conflicts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    conflict_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    record_id: Mapped[str] = mapped_column(String(128), index=True)
    field_name: Mapped[str] = mapped_column(String(128), index=True)
    existing_value_json: Mapped[str] = mapped_column(Text)
    incoming_value_json: Mapped[str] = mapped_column(Text)
    resolved_value_json: Mapped[str] = mapped_column(Text)
    resolution_strategy: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IdempotencyKeyRecord(Base):
    __tablename__ = "idempotency_keys"
    __table_args__ = (UniqueConstraint("endpoint", "idempotency_key", name="uq_idempotency_endpoint_key"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    idempotency_key: Mapped[str] = mapped_column(String(255), index=True)
    endpoint: Mapped[str] = mapped_column(String(255), index=True)
    request_hash: Mapped[str] = mapped_column(String(64), index=True)
    response_status_code: Mapped[int] = mapped_column(Integer)
    response_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
