import pytest


@pytest.mark.integration
def test_idempotency_key_replays_same_request(client, sample_record):
    response_1 = client.post(
        "/records",
        json=sample_record,
        headers={"Idempotency-Key": "key-1"},
    )
    response_2 = client.post(
        "/records",
        json=sample_record,
        headers={"Idempotency-Key": "key-1"},
    )

    assert response_1.status_code == 200
    assert response_2.status_code == 200
    assert response_2.headers["X-Idempotent-Replay"] == "true"
    assert response_1.json() == response_2.json()


@pytest.mark.integration
def test_idempotency_key_rejects_different_payload_on_same_endpoint(client, sample_record):
    client.post(
        "/records",
        json=sample_record,
        headers={"Idempotency-Key": "key-2"},
    )
    changed = dict(sample_record)
    changed["record_id"] = "R-1002"

    response = client.post(
        "/records",
        json=changed,
        headers={"Idempotency-Key": "key-2"},
    )

    assert response.status_code == 409


@pytest.mark.integration
def test_idempotency_key_is_scoped_per_endpoint(client, sample_record):
    first = client.post(
        "/records",
        json=sample_record,
        headers={"Idempotency-Key": "shared-key"},
    )
    second = client.post(
        "/records/batch",
        json=[sample_record],
        headers={"Idempotency-Key": "shared-key"},
    )

    assert first.status_code == 200
    assert second.status_code == 200
