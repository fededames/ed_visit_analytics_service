import pytest


def ingest(client, payload):
    response = client.post("/records", json=payload)
    assert response.status_code == 200


@pytest.mark.integration
def test_healthcheck(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


@pytest.mark.integration
def test_analytics_endpoints_apply_filters_and_return_empty_lists(client):
    ingest(client, {
        "record_id": "R-1001", "patient_id": "P-1001", "patient_name": "Patient", "date_of_birth": "1980-01-01",
        "facility": "Lakeview Main", "timestamp": "2024-04-01T10:00:00Z", "event_type": "REGISTRATION", "diagnosis_codes": []
    })
    ingest(client, {
        "record_id": "R-2001", "patient_id": "P-2001", "patient_name": "Patient", "date_of_birth": "1980-01-01",
        "facility": "Lakeview Main", "timestamp": "2024-04-01T10:10:00Z", "event_type": "TRIAGE", "acuity_level": 3, "diagnosis_codes": []
    })
    ingest(client, {
        "record_id": "R-3001", "patient_id": "P-3001", "patient_name": "Patient",
        "facility": "Harbor Campus", "timestamp": "2024-04-01T21:00:00Z", "event_type": "DISPOSITION", "disposition": "LEFT_WITHOUT_TREATMENT", "diagnosis_codes": []
    })

    response = client.get("/analytics/visit-volume", params={"facility": "   Lakeview Main   ", "start_date": "2024-04-01", "end_date": "2024-04-01"})
    assert response.status_code == 200
    assert response.json() == [{"facility": "Lakeview Main", "day": "2024-04-01", "visit_count": 1}]

    response = client.get("/analytics/acuity-mix")
    assert response.status_code == 200
    assert response.json() == [{"facility": "Lakeview Main", "acuity_level": 3, "triage_count": 1}]

    response = client.get("/analytics/disposition-mix", params={"facility": "Unknown"})
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.integration
def test_stage_latency_endpoint_reconstructs_visits_from_canonical_events_and_reports_quality_counts(client):
    ingest(client, {
        "record_id": "R-1001", "patient_id": "P-1001", "patient_name": "Alice", "date_of_birth": "1980-01-01",
        "facility": "Lakeview Main", "timestamp": "2024-04-01T10:00:00Z", "event_type": "REGISTRATION", "diagnosis_codes": []
    })
    ingest(client, {
        "record_id": "R-1002", "patient_id": "P-1001", "patient_name": "Alice", "date_of_birth": "1980-01-01",
        "facility": "Lakeview Main", "timestamp": "2024-04-01T10:08:00Z", "event_type": "TRIAGE", "acuity_level": 2, "diagnosis_codes": []
    })
    ingest(client, {
        "record_id": "R-2001", "patient_id": "P-2001", "patient_name": "Bob", "date_of_birth": "1990-02-01",
        "facility": "Lakeview Main", "timestamp": "2024-04-01T23:55:00Z", "event_type": "REGISTRATION", "diagnosis_codes": []
    })
    ingest(client, {
        "record_id": "R-2002", "patient_id": "P-2001", "patient_name": "Bob", "date_of_birth": "1990-02-01",
        "facility": "Lakeview Main", "timestamp": "2024-04-02T00:05:00Z", "event_type": "TRIAGE", "acuity_level": 2, "diagnosis_codes": []
    })
    ingest(client, {
        "record_id": "R-3001", "patient_id": "P-3001", "patient_name": "Cara", "date_of_birth": "1988-03-01",
        "facility": "Lakeview Main", "timestamp": "2024-04-01T12:00:00Z", "event_type": "REGISTRATION", "diagnosis_codes": []
    })

    response = client.get(
        "/analytics/stage-latency",
        params={"facility": "Lakeview Main", "start_date": "2024-04-01", "end_date": "2024-04-01"},
    )
    assert response.status_code == 200
    assert response.json() == [
        {
            "facility": "Lakeview Main",
            "day": "2024-04-01",
            "from_event": "REGISTRATION",
            "to_event": "TRIAGE",
            "acuity_level": 2,
            "visit_count_used": 2,
            "visit_count_excluded": 0,
            "missing_stage_count": 0,
            "missing_from_stage_count": 0,
            "missing_to_stage_count": 0,
            "invalid_sequence_count": 0,
            "coverage_ratio": 1.0,
            "average_minutes": 9.0,
            "heuristic_version": "v1",
            "total_visits_considered": 2,
        },
        {
            "facility": "Lakeview Main",
            "day": "2024-04-01",
            "from_event": "REGISTRATION",
            "to_event": "TRIAGE",
            "acuity_level": None,
            "visit_count_used": 0,
            "visit_count_excluded": 1,
            "missing_stage_count": 1,
            "missing_from_stage_count": 0,
            "missing_to_stage_count": 1,
            "invalid_sequence_count": 0,
            "coverage_ratio": 0.0,
            "average_minutes": None,
            "heuristic_version": "v1",
            "total_visits_considered": 1,
        },
    ]


@pytest.mark.integration
def test_analytics_invalid_range_returns_422(client):
    response = client.get("/analytics/visit-volume", params={"start_date": "2024-04-02", "end_date": "2024-04-01"})
    assert response.status_code == 422
    assert "start_date" in response.json()["detail"]


@pytest.mark.integration
def test_stage_latency_same_event_returns_422(client):
    response = client.get("/analytics/stage-latency", params={"from_event": "TRIAGE", "to_event": "TRIAGE"})
    assert response.status_code == 422


@pytest.mark.integration
def test_analytics_invalid_date_format_returns_422(client):
    response = client.get("/analytics/visit-volume", params={"start_date": "04-01-2024"})
    assert response.status_code == 422


@pytest.mark.integration
def test_api_adds_request_id_header(client, sample_record):
    response = client.post("/records", json=sample_record)
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers



@pytest.mark.integration
def test_stage_latency_splits_two_same_day_visits_for_same_patient(client):
    ingest(client, {
        "record_id": "R-4001", "patient_id": "P-4001", "patient_name": "Dan", "date_of_birth": "1970-01-01",
        "facility": "Lakeview Main", "timestamp": "2024-04-01T08:00:00Z", "event_type": "REGISTRATION", "diagnosis_codes": []
    })
    ingest(client, {
        "record_id": "R-4002", "patient_id": "P-4001", "patient_name": "Dan", "date_of_birth": "1970-01-01",
        "facility": "Lakeview Main", "timestamp": "2024-04-01T08:12:00Z", "event_type": "TRIAGE", "acuity_level": 4, "diagnosis_codes": []
    })
    ingest(client, {
        "record_id": "R-4003", "patient_id": "P-4001", "patient_name": "Dan", "date_of_birth": "1970-01-01",
        "facility": "Lakeview Main", "timestamp": "2024-04-01T10:00:00Z", "event_type": "DEPARTURE", "diagnosis_codes": []
    })
    ingest(client, {
        "record_id": "R-4004", "patient_id": "P-4001", "patient_name": "Dan", "date_of_birth": "1970-01-01",
        "facility": "Lakeview Main", "timestamp": "2024-04-01T15:00:00Z", "event_type": "REGISTRATION", "diagnosis_codes": []
    })
    ingest(client, {
        "record_id": "R-4005", "patient_id": "P-4001", "patient_name": "Dan", "date_of_birth": "1970-01-01",
        "facility": "Lakeview Main", "timestamp": "2024-04-01T15:20:00Z", "event_type": "TRIAGE", "acuity_level": 2, "diagnosis_codes": []
    })

    response = client.get("/analytics/stage-latency", params={"facility": "Lakeview Main", "start_date": "2024-04-01", "end_date": "2024-04-01"})
    assert response.status_code == 200
    payload = response.json()
    assert any(row["acuity_level"] == 4 and row["average_minutes"] == 12.0 for row in payload)
    assert any(row["acuity_level"] == 2 and row["average_minutes"] == 20.0 for row in payload)


@pytest.mark.integration
def test_stage_latency_ignores_triage_events_that_occur_before_registration(client):
    ingest(client, {
        "record_id": "R-5001", "patient_id": "P-5001", "patient_name": "Eli", "date_of_birth": "1980-01-01",
        "facility": "Lakeview Main", "timestamp": "2024-04-01T10:00:00Z", "event_type": "TRIAGE", "acuity_level": 4, "diagnosis_codes": []
    })
    ingest(client, {
        "record_id": "R-5002", "patient_id": "P-5001", "patient_name": "Eli", "date_of_birth": "1980-01-01",
        "facility": "Lakeview Main", "timestamp": "2024-04-01T10:05:00Z", "event_type": "REGISTRATION", "diagnosis_codes": []
    })
    ingest(client, {
        "record_id": "R-5003", "patient_id": "P-5001", "patient_name": "Eli", "date_of_birth": "1980-01-01",
        "facility": "Lakeview Main", "timestamp": "2024-04-01T10:20:00Z", "event_type": "TRIAGE", "acuity_level": 2, "diagnosis_codes": []
    })

    response = client.get("/analytics/stage-latency", params={"facility": "Lakeview Main", "start_date": "2024-04-01", "end_date": "2024-04-01"})
    assert response.status_code == 200
    payload = response.json()
    assert any(row["average_minutes"] == 15.0 for row in payload)


@pytest.mark.integration
def test_stage_latency_reports_invalid_sequence_exclusions(client):
    ingest(client, {
        "record_id": "R-8001", "patient_id": "P-8001", "patient_name": "Fran", "date_of_birth": "1980-01-01",
        "facility": "Lakeview Main", "timestamp": "2024-04-01T10:00:00Z", "event_type": "TRIAGE", "acuity_level": 3, "diagnosis_codes": []
    })
    ingest(client, {
        "record_id": "R-8002", "patient_id": "P-8001", "patient_name": "Fran", "date_of_birth": "1980-01-01",
        "facility": "Lakeview Main", "timestamp": "2024-04-01T10:05:00Z", "event_type": "REGISTRATION", "diagnosis_codes": []
    })

    response = client.get("/analytics/stage-latency", params={"facility": "Lakeview Main", "start_date": "2024-04-01", "end_date": "2024-04-01"})
    assert response.status_code == 200
    payload = response.json()
    assert any(row["invalid_sequence_count"] == 1 and row["visit_count_excluded"] == 1 for row in payload)


@pytest.mark.integration
def test_visit_volume_endpoint_supports_date_query_params_regression(client):
    ingest(client, {
        "record_id": "R-9001", "patient_id": "P-9001", "patient_name": "Ivy", "date_of_birth": "1980-01-01",
        "facility": "Lakeview Main", "timestamp": "2024-04-01T09:00:00Z", "event_type": "REGISTRATION", "diagnosis_codes": []
    })
    ingest(client, {
        "record_id": "R-9002", "patient_id": "P-9002", "patient_name": "Jax", "date_of_birth": "1980-01-01",
        "facility": "Lakeview Main", "timestamp": "2024-04-03T11:00:00Z", "event_type": "REGISTRATION", "diagnosis_codes": []
    })

    response = client.get(
        "/analytics/visit-volume",
        params={"facility": "Lakeview Main", "start_date": "2024-04-01", "end_date": "2024-04-03"},
    )
    assert response.status_code == 200
    assert response.json() == [
        {"facility": "Lakeview Main", "day": "2024-04-01", "visit_count": 1},
        {"facility": "Lakeview Main", "day": "2024-04-03", "visit_count": 1},
    ]
