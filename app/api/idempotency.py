from __future__ import annotations

from typing import Any

from fastapi import Response
from sqlalchemy.orm import Session

from app.repositories.idempotency_repository import IdempotencyRepository
from app.services.idempotency_service import IdempotencyService


class ApiIdempotencyHandler:
    """Small API-layer helper to keep request-level idempotency logic out of endpoints."""

    def __init__(
        self,
        *,
        session: Session,
        response: Response,
        endpoint: str,
        idempotency_key: str | None,
        payload: Any,
    ) -> None:
        self._response = response
        self._endpoint = endpoint
        self._idempotency_key = idempotency_key
        self._service = IdempotencyService(IdempotencyRepository(session))
        self._request_hash = self._service.request_hash(payload)

    def replay_or_none(self) -> Any | None:
        if not self._idempotency_key:
            return None

        replay = self._service.replay_if_present(
            idempotency_key=self._idempotency_key,
            endpoint=self._endpoint,
            request_hash=self._request_hash,
        )
        if replay is None:
            return None

        self._response.headers["X-Idempotent-Replay"] = "true"
        return self._service.replay_body(replay)

    def store(self, *, response_status_code: int, response_body: Any) -> None:
        if not self._idempotency_key:
            return

        self._service.store_response(
            idempotency_key=self._idempotency_key,
            endpoint=self._endpoint,
            request_hash=self._request_hash,
            response_status_code=response_status_code,
            response_body=response_body,
        )

    @property
    def enabled(self) -> bool:
        return bool(self._idempotency_key)
