from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IdempotencyReplay:
    status_code: int
    response_json: str
    replayed: bool = True
