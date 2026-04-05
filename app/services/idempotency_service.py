from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException

from app.domain.idempotency import IdempotencyReplay
from app.repositories.idempotency_repository import IdempotencyRepository
from app.services.hashing import canonical_json, payload_hash


class IdempotencyService:
    """Implements request-level idempotency using the Idempotency-Key header."""

    def __init__(self, repository: IdempotencyRepository) -> None:
        self._repository = repository

    @staticmethod
    def request_hash(payload: Any) -> str:
        if isinstance(payload, dict):
            return payload_hash(payload)
        return payload_hash({"items": payload})

    def replay_if_present(
        self,
        *,
        idempotency_key: str,
        endpoint: str,
        request_hash: str,
    ) -> IdempotencyReplay | None:
        existing = self._repository.get_by_key(idempotency_key=idempotency_key, endpoint=endpoint)
        if existing is None:
            return None

        if existing.request_hash != request_hash:
            raise HTTPException(
                status_code=409,
                detail="Idempotency-Key was already used with a different request payload for this endpoint.",
            )

        return IdempotencyReplay(
            status_code=existing.response_status_code,
            response_json=existing.response_json,
            replayed=True,
        )

    def store_response(
        self,
        *,
        idempotency_key: str,
        endpoint: str,
        request_hash: str,
        response_status_code: int,
        response_body: Any,
    ) -> None:
        self._repository.save_response(
            idempotency_key=idempotency_key,
            endpoint=endpoint,
            request_hash=request_hash,
            response_status_code=response_status_code,
            response_json=canonical_json(response_body),
        )

    @staticmethod
    def replay_body(replay: IdempotencyReplay) -> Any:
        return json.loads(replay.response_json)
