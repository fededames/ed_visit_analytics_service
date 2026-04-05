import pytest

from app.services.hashing import canonical_json, payload_hash


@pytest.mark.unit
def test_canonical_json_sorts_keys():
    assert canonical_json({"b": 1, "a": 2}) == '{"a":2,"b":1}'


@pytest.mark.unit
def test_payload_hash_is_stable():
    assert payload_hash({"a": 1, "b": 2}) == payload_hash({"b": 2, "a": 1})
