# ED Visit Analytics Service

A small FastAPI backend for ingesting Emergency Department lifecycle events and exposing operational analytics from messy, real-world ED feed data.

The service is intentionally scoped to fit the take-home:
- single process
- no external streaming system
- PostgreSQL persistence
- analytics that are useful to operations but avoid directly exposing sensitive patient data

It is designed around the quirks called out in the prompt:
- duplicate deliveries
- late-arriving corrections
- out-of-order events
- partial records and missing demographics

## What the service does

1. Accepts ED event records over HTTP.
2. Sanitizes inbound records before storing a canonical analytical representation.
3. Uses `record_id` as the feed-level identity for deduplication and correction handling.
4. Reconstructs likely visits from canonical events when a metric needs visit-level lifecycle reasoning.
5. Exposes lightweight analytics endpoints for operational reporting.

## Chosen analytics

The service exposes four analytics endpoints. The assignment only asked for at least two, but I included two direct aggregations and two lifecycle-oriented views because that better matches the ED use case.

### 1. `GET /analytics/visit-volume`
Counts canonical `REGISTRATION` events by day and facility.

Why it is useful:
- gives operations a quick volume trend
- works well even when later stages are delayed
- stays simple and explainable

### 2. `GET /analytics/acuity-mix`
Counts canonical `TRIAGE` events by facility and acuity level.

Why it is useful:
- shows whether a site is seeing more urgent cases
- is closer to staffing and load-balancing decisions than raw volume alone

### 3. `GET /analytics/disposition-mix`
Counts canonical `DISPOSITION` outcomes by facility.

Why it is useful:
- shows admission vs discharge vs transfer vs LWOT patterns
- gives a simple outcome-oriented view without exposing patient-level data

### 4. `GET /analytics/stage-latency`
Reconstructs visits heuristically and computes average elapsed minutes between two lifecycle stages, for example:
- registration → triage
- registration → disposition
- triage → disposition

Why it is useful:
- gives a wait/throughput metric directly aligned with the prompt
- makes the reconstruction tradeoffs discussable in the interview
- includes coverage/exclusion counters so the metric is transparent about data quality

## API surface

### Ingestion
- `POST /records` — ingest one record
- `POST /records/batch` — ingest a list of records

### Analytics
- `GET /analytics/visit-volume`
- `GET /analytics/acuity-mix`
- `GET /analytics/disposition-mix`
- `GET /analytics/stage-latency`

### Utility
- `GET /health`

## Privacy and analytical storage

The input payload contains PHI/PII, but the analytical representation is intentionally reduced.

The service derives and stores a sanitized canonical form for analytics, including:
- `patient_key`: HMAC-derived pseudonymous key from `patient_id`
- `facility`
- `timestamp`
- `event_type`
- `acuity_level`
- `chief_complaint`
- `disposition`
- `diagnosis_codes`
- `age_band`

This keeps the data useful for analytics while avoiding direct patient identifiers in the main analytical flow.

## High-level design

### 1. Raw ingestion + canonical analytical record
Each incoming event is validated and sanitized. The canonical representation is what analytics rely on.

### 2. Deduplication and correction handling
`record_id` is treated as the identity of a feed record.
- same `record_id` + same canonical payload → duplicate, ignored
- same `record_id` + different canonical payload → correction, canonical row updated

That matches the prompt's statement that corrections may reuse the same record ID.

### 3. Visit reconstruction
The feed does not provide a stable `visit_id`, so lifecycle metrics use a heuristic reconstructor based on:
- patient key
- facility
- timestamp ordering
- rolling visit window
- inactivity gap
- visit-closing stages such as `DISPOSITION` or `DEPARTURE`

This is deliberately a pragmatic analytical heuristic, not a claim of clinical-grade visit identity.

## Project structure

```text
app/
  api/            HTTP endpoints
  core/           settings and logging
  db/             SQLAlchemy models and session setup
  domain/         enums and schemas
  repositories/   database access
  services/       ingestion, merge, reconstruction, analytics
alembic/          schema migrations
sample_data/      example payloads
tests/            unit and integration tests
```

## Local setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[dev]"
cp .env.example .env
make db-up
make db-migrate
make run-local
```

Open the API docs at:

```text
http://localhost:8000/docs
```

## Quick start with sample data

Ingest the sample batch:

```bash
curl -X POST http://localhost:8000/records/batch \
  -H "Content-Type: application/json" \
  --data @sample_data/batch_payload.json
```

Example analytics calls:

```bash
curl "http://localhost:8000/analytics/visit-volume"
curl "http://localhost:8000/analytics/acuity-mix"
curl "http://localhost:8000/analytics/disposition-mix"
curl "http://localhost:8000/analytics/stage-latency?from_event=REGISTRATION&to_event=TRIAGE"
```

## Testing

```bash
make test
```

There are both unit and integration tests covering:
- validation rules
- deduplication and correction handling
- out-of-order behavior
- API responses
- analytics logic
- migration wiring

## Production-oriented changes I would make next

Given more time or a real deployment context, I would likely add:
- asynchronous ingestion pipeline or queue buffering
- precomputed aggregates for larger reporting ranges
- stronger data lineage and auditability around corrections
- richer observability and SLO-oriented metrics
- clearer separation between raw landing data and curated analytical projections
- facility time-zone handling and more explicit event-time vs arrival-time reporting

More detail is in `DECISIONS.md`, `INSTRUCTIONS.md`, and `AI_USAGE.md`.