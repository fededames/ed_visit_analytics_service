from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Header, Response
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.api.idempotency import ApiIdempotencyHandler
from app.domain.records import EDVisitRecordIn, IngestionResponse
from app.services.ingestion_service import IngestionService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["records"])


@router.post("/records", response_model=IngestionResponse, summary="Ingest a single ED event record")
def ingest_record(
    record: EDVisitRecordIn,
    response: Response,
    session: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> IngestionResponse:
    logger.info(
        "api_records_request",
        extra={
            "event": "api",
            "endpoint": "records",
            "record_id": record.record_id,
            "facility": record.facility,
            "has_idempotency_key": bool(idempotency_key),
        },
    )

    idempotency = ApiIdempotencyHandler(
        session=session,
        response=response,
        endpoint="records",
        idempotency_key=idempotency_key,
        payload=record.model_dump(mode="json"),
    )
    replayed = idempotency.replay_or_none()
    if replayed is not None:
        replayed_response = IngestionResponse.model_validate(replayed)
        logger.info("api_records_replay", extra={"event": "api", "endpoint": "records", "record_id": record.record_id})
        return replayed_response

    try:
        result = IngestionService(session, get_settings()).ingest(record)
        idempotency.store(response_status_code=200, response_body=result.model_dump(mode="json"))
        session.commit()
    except Exception:
        session.rollback()
        raise

    logger.info(
        "api_records_response",
        extra={
            "event": "api",
            "endpoint": "records",
            "record_id": record.record_id,
            "status": result.status,
            "canonical_changed": result.canonical_changed,
        },
    )
    return result


@router.post("/records/batch", response_model=list[IngestionResponse], summary="Ingest a batch of ED event records")
def ingest_batch(
    records: list[EDVisitRecordIn],
    response: Response,
    session: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> list[IngestionResponse]:
    logger.info(
        "api_records_batch_request",
        extra={
            "event": "api",
            "endpoint": "records-batch",
            "batch_size": len(records),
            "has_idempotency_key": bool(idempotency_key),
        },
    )

    idempotency = ApiIdempotencyHandler(
        session=session,
        response=response,
        endpoint="records-batch",
        idempotency_key=idempotency_key,
        payload=[record.model_dump(mode="json") for record in records],
    )
    replayed = idempotency.replay_or_none()
    if replayed is not None:
        replayed_results = [IngestionResponse.model_validate(item) for item in replayed]
        logger.info("api_records_batch_replay", extra={"event": "api", "endpoint": "records-batch", "batch_size": len(records)})
        return replayed_results

    try:
        ingestion_service = IngestionService(session, get_settings())
        results = [ingestion_service.ingest(record) for record in records]
        idempotency.store(
            response_status_code=200,
            response_body=[result.model_dump(mode="json") for result in results],
        )
        session.commit()
    except Exception:
        session.rollback()
        raise

    logger.info(
        "api_records_batch_response",
        extra={
            "event": "api",
            "endpoint": "records-batch",
            "batch_size": len(records),
            "result_count": len(results),
            "updated_count": sum(1 for result in results if result.status == "updated"),
            "duplicate_count": sum(1 for result in results if result.status == "duplicate_ignored"),
        },
    )
    return results
