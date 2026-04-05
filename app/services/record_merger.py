from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.domain.conflicts import MergeConflict


def _is_missing(value: Any) -> bool:
    return value is None or value == "" or value == []


def _parse_iso_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


@dataclass(frozen=True)
class MergeDecision:
    payload: dict[str, Any]
    changed: bool
    reason: str
    conflicts: list[MergeConflict]


class BaseFieldResolver:
    strategy_name = "base"

    def resolve(
        self,
        record_id: str,
        field: str,
        existing: Any,
        incoming: Any,
        *,
        existing_payload: dict[str, Any],
        incoming_payload: dict[str, Any],
        existing_arrival_id: int | None,
        incoming_arrival_id: int | None,
    ) -> tuple[Any, MergeConflict | None]:
        if _is_missing(incoming):
            return existing, None
        if _is_missing(existing):
            return incoming, None
        if existing == incoming:
            return existing, None
        return self._resolve_conflict(
            record_id,
            field,
            existing,
            incoming,
            existing_payload=existing_payload,
            incoming_payload=incoming_payload,
            existing_arrival_id=existing_arrival_id,
            incoming_arrival_id=incoming_arrival_id,
        )

    def _resolve_conflict(
        self,
        record_id: str,
        field: str,
        existing: Any,
        incoming: Any,
        *,
        existing_payload: dict[str, Any],
        incoming_payload: dict[str, Any],
        existing_arrival_id: int | None,
        incoming_arrival_id: int | None,
    ) -> tuple[Any, MergeConflict | None]:
        raise NotImplementedError


class KeepExistingResolver(BaseFieldResolver):
    strategy_name = "keep_existing"

    def _resolve_conflict(self, record_id: str, field: str, existing: Any, incoming: Any, **_: Any) -> tuple[Any, MergeConflict]:
        return existing, MergeConflict(
            record_id=record_id,
            field=field,
            existing_value=existing,
            incoming_value=incoming,
            resolved_value=existing,
            resolution_strategy=self.strategy_name,
        )


class StrictIdentityResolver(BaseFieldResolver):
    strategy_name = "strict_keep_existing"

    def _resolve_conflict(self, record_id: str, field: str, existing: Any, incoming: Any, **_: Any) -> tuple[Any, MergeConflict]:
        return existing, MergeConflict(
            record_id=record_id,
            field=field,
            existing_value=existing,
            incoming_value=incoming,
            resolved_value=existing,
            resolution_strategy=self.strategy_name,
        )


class UnionListResolver(BaseFieldResolver):
    strategy_name = "union_list_values"

    def _resolve_conflict(self, record_id: str, field: str, existing: Any, incoming: Any, **_: Any) -> tuple[Any, MergeConflict]:
        resolved = sorted(set(existing) | set(incoming))
        return resolved, MergeConflict(
            record_id=record_id,
            field=field,
            existing_value=existing,
            incoming_value=incoming,
            resolved_value=resolved,
            resolution_strategy=self.strategy_name,
        )


class PreferAuthoritativePayloadResolver(BaseFieldResolver):
    strategy_name = "prefer_authoritative_payload"

    @staticmethod
    def _precedence_key(payload: dict[str, Any], arrival_id: int | None) -> tuple[datetime, int]:
        event_ts = _parse_iso_timestamp(payload.get("timestamp")) or datetime.min.replace(tzinfo=None)
        # normalize to naive UTC-like ordering for safe tuple comparisons
        if event_ts.tzinfo is not None:
            event_ts = event_ts.astimezone(UTC).replace(tzinfo=None)
        return (event_ts, arrival_id or -1)

    def _resolve_conflict(
        self,
        record_id: str,
        field: str,
        existing: Any,
        incoming: Any,
        *,
        existing_payload: dict[str, Any],
        incoming_payload: dict[str, Any],
        existing_arrival_id: int | None,
        incoming_arrival_id: int | None,
    ) -> tuple[Any, MergeConflict]:
        existing_key = self._precedence_key(existing_payload, existing_arrival_id)
        incoming_key = self._precedence_key(incoming_payload, incoming_arrival_id)
        resolved = incoming if incoming_key >= existing_key else existing
        return resolved, MergeConflict(
            record_id=record_id,
            field=field,
            existing_value=existing,
            incoming_value=incoming,
            resolved_value=resolved,
            resolution_strategy=self.strategy_name,
        )


FIELD_RESOLVERS: dict[str, BaseFieldResolver] = {
    "patient_key": StrictIdentityResolver(),
    "facility": StrictIdentityResolver(),
    "event_type": StrictIdentityResolver(),
    "timestamp": PreferAuthoritativePayloadResolver(),
    "acuity_level": PreferAuthoritativePayloadResolver(),
    "chief_complaint": PreferAuthoritativePayloadResolver(),
    "disposition": PreferAuthoritativePayloadResolver(),
    "diagnosis_codes": UnionListResolver(),
    "age_band": KeepExistingResolver(),
}
DEFAULT_RESOLVER = KeepExistingResolver()


class RecordMerger:
    def merge(
        self,
        existing: dict[str, Any] | None,
        incoming: dict[str, Any],
        *,
        existing_arrival_id: int | None = None,
        incoming_arrival_id: int | None = None,
    ) -> MergeDecision:
        record_id = incoming.get("record_id", "<unknown>")

        if existing is None:
            return MergeDecision(payload=incoming, changed=True, reason="created", conflicts=[])

        if existing == incoming:
            return MergeDecision(payload=existing, changed=False, reason="duplicate_ignored", conflicts=[])

        merged: dict[str, Any] = {}
        conflicts: list[MergeConflict] = []

        for field in sorted(set(existing) | set(incoming)):
            resolver = FIELD_RESOLVERS.get(field, DEFAULT_RESOLVER)
            resolved_value, conflict = resolver.resolve(
                record_id,
                field,
                existing.get(field),
                incoming.get(field),
                existing_payload=existing,
                incoming_payload=incoming,
                existing_arrival_id=existing_arrival_id,
                incoming_arrival_id=incoming_arrival_id,
            )
            merged[field] = resolved_value
            if conflict is not None:
                conflicts.append(conflict)

        changed = merged != existing
        return MergeDecision(
            payload=merged,
            changed=changed,
            reason="updated" if changed else "duplicate_ignored",
            conflicts=conflicts,
        )
