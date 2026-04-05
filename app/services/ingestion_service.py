from __future__ import annotations

import json
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.records import EDVisitRecordIn, IngestionResponse
from app.repositories.ingestion_repository import IngestionRepository
from app.services.hashing import canonical_json, payload_hash
from app.services.record_merger import RecordMerger
from app.services.sanitization import sanitize_record

logger = logging.getLogger(__name__)


class IngestionService:
    """Coordinates record sanitization, deduplication, merge, conflict capture, and persistence."""

    def __init__(self, session: Session, settings: Settings) -> None:
        self._repository = IngestionRepository(session)
        self._settings = settings
        self._merger = RecordMerger()

    def ingest(self, record: EDVisitRecordIn) -> IngestionResponse:
        sanitized = sanitize_record(record, self._settings)
        incoming_payload = sanitized.canonical_dict()
        incoming_hash = payload_hash(incoming_payload)
        incoming_json = canonical_json(incoming_payload)

        raw_arrival = self._repository.append_raw_arrival(record.record_id, incoming_json, incoming_hash)

        existing_row = self._repository.get_canonical_by_record_id(record.record_id)
        existing_payload = json.loads(existing_row.payload_json) if existing_row else None
        existing_hash = existing_row.payload_hash if existing_row else None
        existing_arrival_id = existing_row.source_arrival_id if existing_row else None

        if existing_hash == incoming_hash:
            response = IngestionResponse(
                status="duplicate_ignored",
                record_id=record.record_id,
                canonical_changed=False,
            )
            logger.info(
                "record_ingested",
                extra={
                    "event": "ingestion",
                    "record_id": record.record_id,
                    "facility": record.facility,
                    "status": response.status,
                    "canonical_changed": response.canonical_changed,
                    "conflict_count": 0,
                },
            )
            return response

        decision = self._merger.merge(
            existing_payload,
            incoming_payload,
            existing_arrival_id=existing_arrival_id,
            incoming_arrival_id=raw_arrival.id,
        )
        merged_hash = payload_hash(decision.payload)
        merged_json = canonical_json(decision.payload)
        canonical_changed = existing_hash != merged_hash

        if decision.conflicts:
            self._repository.append_merge_conflicts(decision.conflicts)
            for conflict in decision.conflicts:
                logger.info(
                    "merge_conflict_resolved",
                    extra={
                        "event": "merge_conflict",
                        "record_id": conflict.record_id,
                        "field": conflict.field,
                        "resolution_strategy": conflict.resolution_strategy,
                    },
                )

        if canonical_changed:
            merged_timestamp = datetime.fromisoformat(decision.payload["timestamp"].replace("Z", "+00:00"))
            self._repository.upsert_canonical(
                record_id=decision.payload["record_id"],
                patient_key=decision.payload["patient_key"],
                facility=decision.payload["facility"],
                event_timestamp=merged_timestamp,
                event_type=decision.payload["event_type"],
                acuity_level=decision.payload.get("acuity_level"),
                disposition=decision.payload.get("disposition"),
                age_band=decision.payload.get("age_band"),
                source_arrival_id=raw_arrival.id,
                payload_json=merged_json,
                payload_hash_value=merged_hash,
            )

        response = IngestionResponse(
            status=decision.reason,
            record_id=record.record_id,
            canonical_changed=canonical_changed,
        )
        logger.info(
            "record_ingested",
            extra={
                "event": "ingestion",
                "record_id": record.record_id,
                "facility": record.facility,
                "status": response.status,
                "canonical_changed": response.canonical_changed,
                "conflict_count": len(decision.conflicts),
            },
        )
        return response
