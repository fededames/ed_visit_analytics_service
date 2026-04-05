# INSTRUCTIONS

This document is written for Lakeview Health Network's engineering team. It explains how to run, test, and integrate the service, plus the main behavioral assumptions behind the API.

## 1. What this service is

This service ingests Emergency Department event records and exposes operational analytics over a sanitized analytical model.

It is intended as a backend building block for non-sensitive reporting, not as a system of record for patient charts.

## 2. Supported endpoints

### Health
- `GET /health`

Checks API and database connectivity.

### Ingestion
- `POST /records`
- `POST /records/batch`

### Analytics
- `GET /analytics/visit-volume`
- `GET /analytics/acuity-mix`
- `GET /analytics/disposition-mix`
- `GET /analytics/stage-latency`

## 3. Runtime requirements

- Python 3.11+ (tested with 3.12 locally)
- Docker and Docker Compose for the local PostgreSQL dependency

## 4. Local setup

From the repository root:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[dev]"
cp .env.example .env
```

## 5. Environment variables

The main settings are:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:55432/ed_analytics
PATIENT_KEY_SECRET=dev-secret-change-me
ENVIRONMENT=development
LOG_LEVEL=INFO
```

### Notes
- `DATABASE_URL` defaults to a local debug PostgreSQL URL if not set.
- `PATIENT_KEY_SECRET` must be changed outside development.
- in non-development environments, the app rejects the default secret.

## 6. Start the database

```bash
make db-up
```

This starts the PostgreSQL container defined in `docker-compose.yml`.

If you want a clean local database:

```bash
make db-reset
```

## 7. Run migrations

```bash
make db-migrate
```

### Important
This command uses the `alembic` executable installed in the virtual environment. If you see an error like:

```text
make: alembic: No such file or directory
```

it usually means dependencies were not installed in the active virtual environment yet. Activate the venv and run:

```bash
python -m pip install -e ".[dev]"
```

then retry `make db-migrate`.

## 8. Start the API

```bash
make run-local
```

The service runs on:

```text
http://localhost:8000
```

Swagger UI is available at:

```text
http://localhost:8000/docs
```

## 9. Ingesting data

### Single-record ingestion

```bash
curl -X POST http://localhost:8000/records \
  -H "Content-Type: application/json" \
  -d '{
    "record_id": "R-1001",
    "patient_id": "P-1001",
    "patient_name": "Test Patient Alice",
    "date_of_birth": "1958-04-12",
    "ssn_last4": "1234",
    "contact_phone": "555-0001",
    "facility": "Lakeview Main",
    "timestamp": "2024-04-01T14:22:00Z",
    "event_type": "REGISTRATION",
    "chief_complaint": "chest pain",
    "diagnosis_codes": []
  }'
```

### Batch ingestion

```bash
curl -X POST http://localhost:8000/records/batch \
  -H "Content-Type: application/json" \
  --data @sample_data/batch_payload.json
```

### Optional API idempotency key

Both ingestion endpoints accept:

```text
Idempotency-Key: <client-generated-key>
```

This protects clients from accidentally replaying the same HTTP request body.

### Ingestion response shape

```json
{
  "status": "created | updated | duplicate_ignored",
  "record_id": "R-1001",
  "canonical_changed": true
}
```

## 10. Analytics usage

### A. Visit volume

Counts canonical registrations by day and facility.

```bash
curl "http://localhost:8000/analytics/visit-volume"
curl "http://localhost:8000/analytics/visit-volume?facility=Lakeview%20Main"
curl "http://localhost:8000/analytics/visit-volume?start_date=2024-04-01&end_date=2024-04-03"
```

Example response:

```json
[
  {
    "facility": "Lakeview Main",
    "day": "2024-04-01",
    "visit_count": 2
  }
]
```

### B. Acuity mix

Counts canonical triage records by facility and acuity level.

```bash
curl "http://localhost:8000/analytics/acuity-mix"
```

Example response:

```json
[
  {
    "facility": "Lakeview Main",
    "acuity_level": 2,
    "triage_count": 2
  }
]
```

### C. Disposition mix

Counts canonical dispositions by facility.

```bash
curl "http://localhost:8000/analytics/disposition-mix"
```

Example response:

```json
[
  {
    "facility": "Lakeview Main",
    "disposition": "ADMITTED",
    "disposition_count": 1
  }
]
```

### D. Stage latency

Computes average minutes between two lifecycle stages over reconstructed visits.

```bash
curl "http://localhost:8000/analytics/stage-latency?from_event=REGISTRATION&to_event=TRIAGE"
curl "http://localhost:8000/analytics/stage-latency?facility=Lakeview%20Main&from_event=TRIAGE&to_event=DISPOSITION"
```

Example response:

```json
[
  {
    "facility": "Lakeview Main",
    "day": "2024-04-01",
    "from_event": "REGISTRATION",
    "to_event": "TRIAGE",
    "acuity_level": 2,
    "visit_count_used": 1,
    "visit_count_excluded": 0,
    "total_visits_considered": 1,
    "missing_stage_count": 0,
    "missing_from_stage_count": 0,
    "missing_to_stage_count": 0,
    "invalid_sequence_count": 0,
    "coverage_ratio": 1.0,
    "average_minutes": 13.0,
    "heuristic_version": "v1"
  }
]
```

## 11. Behavioral assumptions

### Deduplication and corrections
`record_id` is treated as the identity of an upstream feed record.

- same `record_id` + same canonical content → duplicate
- same `record_id` + changed canonical content → correction/update

This is how the service handles retries and corrected records that reuse the same ID.

### Out-of-order arrival
Lifecycle analytics use event timestamps, not arrival order.

This means late events and corrections can affect previously computed metrics, which is expected and intentional.

### Visit reconstruction
The feed does not provide a `visit_id`, so visit-level metrics are heuristic.

Current logic groups events by:
- pseudonymous patient key
- facility
- temporal proximity
- evidence that a prior visit is already closed

This is suitable for operational reporting, but should not be interpreted as a clinical source of truth.

## 12. Data minimization

The analytics path intentionally avoids storing direct identifiers in the canonical analytical representation.

Key examples:
- `patient_id` becomes HMAC-derived `patient_key`
- age is reduced to `age_band`
- analytics endpoints return only aggregated results

## 13. Testing

Run all tests:

```bash
make test
```

Run only unit tests:

```bash
make test-unit
```

Run only integration tests:

```bash
make test-integration
```

The test suite covers:
- domain validation
- deduplication and correction semantics
- out-of-order updates
- analytics API behavior
- schema migration wiring

## 14. Integration guidance for upstream teams

### Recommended client behavior
- send one event per EHR stage change
- preserve `record_id` when sending a correction to the same feed event
- provide a client-generated `Idempotency-Key` when retrying HTTP requests
- prefer UTC timestamps with explicit offsets

### Recommended expectations
- duplicates are safely ignored
- corrections can change historical aggregate outputs
- stage latency is an analytical approximation when no explicit visit identifier exists

## 15. Known limitations

- no authentication or authorization layer is included
- no background workers or streaming pipeline
- no full raw-event archival strategy beyond the relational persistence used here
- no dashboard UI
- no facility-specific timezone normalization logic
- visit reconstruction is intentionally heuristic

## 16. Production evolution

If Lakeview wanted to push this toward production, the next likely steps would be:
- separate raw landing from curated analytical projections
- add stronger auditability for corrections
- precompute common aggregates
- add security controls and secret management
- add monitoring, tracing, and alerting
- introduce backfill/rebuild workflows for historical corrections
