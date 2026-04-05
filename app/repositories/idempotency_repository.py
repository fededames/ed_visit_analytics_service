from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import IdempotencyKeyRecord


class IdempotencyRepository:
    """Repository for request-level idempotency records."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_key(self, *, idempotency_key: str, endpoint: str) -> IdempotencyKeyRecord | None:
        stmt = select(IdempotencyKeyRecord).where(
            IdempotencyKeyRecord.idempotency_key == idempotency_key,
            IdempotencyKeyRecord.endpoint == endpoint,
        )
        return self._session.execute(stmt).scalar_one_or_none()

    def save_response(
        self,
        *,
        idempotency_key: str,
        endpoint: str,
        request_hash: str,
        response_status_code: int,
        response_json: str,
    ) -> None:
        self._session.add(
            IdempotencyKeyRecord(
                idempotency_key=idempotency_key,
                endpoint=endpoint,
                request_hash=request_hash,
                response_status_code=response_status_code,
                response_json=response_json,
            )
        )
