# Design Decisions, Assumptions, and Tradeoffs

## 1. Scope and architecture

I chose a small monolithic service:
- FastAPI application
- PostgreSQL database
- synchronous request handling
- query-time analytics for most metrics

### Why
The prompt explicitly says to keep scope reasonable and that a single-process solution is fine. For a take-home, I wanted the design to be easy to run, easy to explain, and still realistic enough to discuss production evolution.

### Tradeoff
This is not optimized for very large reporting workloads or highly bursty ingestion. It is optimized for clarity and correctness within the exercise.

---

## 2. Treat `record_id` as feed-record identity

I treat `record_id` as the identity of an incoming record, not as the identity of a patient visit.

### Why
The prompt says:
- the same visit may be reported more than once
- a corrected record may reuse the same `record_id`

That strongly suggests `record_id` identifies a feed event instance that can be retried or corrected.

### Resulting behavior
- exact replay with same canonical payload → duplicate, ignored
- same `record_id` with changed canonical payload → correction, update canonical record

### Tradeoff
This assumes upstream uses `record_id` consistently. If a real EHR integration violated that assumption, I would need stronger source lineage, versioning, or arrival-sequence handling.

---

## 3. Separate feed ingestion concerns from visit analytics concerns

I separated two different questions:

### A. What is the latest canonical version of this feed event?
Answered by deduplication and correction logic around `record_id`.

### B. Which events probably belong to the same ED visit?
Answered later by a visit reconstruction heuristic.

### Why
Trying to solve both problems in one step usually makes the logic harder to reason about. The prompt's messy-data requirements become easier to defend when these concerns are explicitly separated.

---

## 4. Sanitize data before analytical use

The inbound record includes direct identifiers such as:
- patient name
- date of birth
- SSN fragment
- phone number

For analytics, I derive a pseudonymous `patient_key` using HMAC over `patient_id` and reduce age into an `age_band`.

### Why
The prompt asks for non-sensitive reporting. The analytics do not need direct identifiers.

### Tradeoff
This is privacy-aware, but not a full compliance design. In a production healthcare setting I would expect more explicit data governance, retention rules, key management, and audit controls.

---

## 5. Chosen analytics: mix of simple and lifecycle-aware

I intentionally chose two categories of analytics.

### Direct aggregation metrics
- visit volume from canonical `REGISTRATION` events
- acuity mix from canonical `TRIAGE` events
- disposition mix from canonical `DISPOSITION` events

These are simple, robust, and easy to explain.

### Lifecycle metric
- stage latency between any two ED lifecycle stages

This adds a more interesting operational measure and demonstrates how I handled the absence of a provided `visit_id`.

### Why this mix works well
It gives a balanced answer to the prompt:
- some analytics remain straightforward and stable under messy data
- at least one analytic addresses wait-time/throughput style questions directly

---

## 6. Visit reconstruction is heuristic by design

The feed has no explicit `visit_id`, so I reconstruct analytical visits from canonical events using:
- `patient_key`
- `facility`
- chronological ordering
- a rolling visit window
- an inactivity gap
- visit-closing stages (`DISPOSITION`, `DEPARTURE`)

### Why
Without a visit identifier, some heuristic is necessary for stage-to-stage latency. I preferred a transparent heuristic over pretending the data is cleaner than it is.

### Important assumption
For analytical purposes, events for the same patient and facility that are close in time are likely part of the same ED encounter, unless there is evidence that the earlier visit is already closed.

### Tradeoff
This can misclassify edge cases such as:
- two truly separate same-day visits by the same patient to the same facility
- unusual workflows where a stage arrives very late after closure
- upstream systems that emit sparse or inconsistent stage sequences

That is acceptable here because the output is framed as operational analytics, not billing- or chart-grade truth.

---

## 7. Sort by event time, not arrival order, for lifecycle analytics

For reconstruction and stage latency, I sort canonical events by event timestamp.

### Why
The prompt explicitly calls out delayed and out-of-order arrivals. If lifecycle analytics were based on arrival order, the result would be misleading.

### Tradeoff
This improves analytical correctness, but it means a late correction can change historical analytics. In a production reporting system, I would make this behavior explicit and likely support backfill-aware recomputation.

---

## 8. Query-time computation over precomputed aggregates

Most analytics are calculated when requested.

### Why
This keeps the architecture smaller:
- fewer moving parts
- fewer projection tables
- easier to test in a take-home

### Tradeoff
Query-time computation is fine at the prompt's stated scale, but it would not be my final design if reporting volume or time ranges grew significantly.

### Production change
At larger scale I would likely precompute daily facility aggregates and maintain a separate analytical model for latency metrics.

---

## 9. Make lifecycle metrics explicit about coverage, not falsely precise

`/analytics/stage-latency` returns more than just an average. It also returns counters such as:
- visits used
- visits excluded
- missing-stage counts
- invalid sequence counts
- coverage ratio
- heuristic version

### Why
Averages on messy event data can look more precise than they really are. I wanted the endpoint to expose enough context so a consumer can judge reliability.

### Tradeoff
The response is more verbose, but much more defensible in an interview and more honest for operational use.

---

## 10. Validation choices

I enforce only a few strict domain validations, for example:
- `TRIAGE` requires `acuity_level`
- `acuity_level` must be within 1..5
- `diagnosis_codes` are normalized and deduplicated

### Why
I wanted the API to reject clearly invalid data while still being tolerant of incomplete but plausible records, since the prompt says to handle similar records gracefully.

### Tradeoff
A production integration would probably add source-specific validation, schema versioning, and quarantine paths for malformed payloads.

---

## 11. Why I did not add Kafka, Celery, or streaming infrastructure

### Reason
The prompt explicitly says no external streaming systems are required.

### Decision
I kept ingestion synchronous and transactional.

### Tradeoff
This is simpler and fully appropriate here, but a real system might buffer bursts, separate ingestion from analytics projection, and support replay pipelines.

---

## 12. Things I would change in a production system

If this were moving beyond take-home scope, I would prioritize:

### Data model and lineage
- explicit raw landing table or object storage archive
- event arrival timestamp alongside event timestamp
- correction versioning and audit trail
- source-system metadata

### Performance
- incremental aggregate tables
- background recomputation for historical corrections
- caching for common operational dashboards

### Reliability
- dead-letter or quarantine handling for bad input
- idempotent replay support with stronger operational tooling
- migration and startup health checks in CI/CD

### Security and governance
- secret management outside env defaults
- tighter retention policies
- more aggressive field minimization
- audit logging and access controls

### Analytics quality
- configurable facility time zones
- richer visit-closing logic
- explicit quality score per reconstructed visit
- optional facility-specific heuristics if source feeds differ materially

---

## Bottom line

The core design principle was:

**be honest about messy data, keep the service small, and make the analytical tradeoffs visible rather than hiding them.**
