from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MergeConflict:
    record_id: str
    field: str
    existing_value: Any
    incoming_value: Any
    resolved_value: Any
    resolution_strategy: str
