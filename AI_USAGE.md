# AI Usage

## Tools used and how

I used ChatGPT as an interactive development assistant during the take-home.

I used it for:
- pressure-testing the architecture against the wording of the prompt
- identifying missing edge cases in ingestion and analytics
- improving the markdown deliverables so they better explain assumptions and tradeoffs
- challenging whether the analytics were too simplistic for an ED operations use case
- reviewing where the solution might look overengineered for a 2-hour exercise

I did **not** treat AI output as final truth. I reviewed and edited the implementation and documentation manually.

## Example prompts

### Prompt 1
> Review this ED visit analytics take-home critically. Based on the prompt, what is under-explained, what looks overengineered, and what interview questions am I likely to get about messy data handling?

**What I was trying to accomplish:**
Stress-test whether the project matched the assignment well enough and whether the reasoning would hold up in discussion.

### Prompt 2
> I have deduplication by record_id, out-of-order arrivals, and no visit_id in the feed. Suggest a simple but defensible visit reconstruction strategy for analytics like registration-to-triage latency, and list the tradeoffs clearly.

**What I was trying to accomplish:**
Add a lifecycle-oriented metric without pretending the source data was cleaner than it is.

## What worked well

AI was genuinely helpful for:
- surfacing the difference between feed-record identity and visit identity
- suggesting that the project should include at least one wait-time / throughput style metric, not only simple counts
- improving the clarity of the documentation around assumptions
- pointing out where the project risked becoming too "production architecture" heavy for a take-home
- helping me frame limitations honestly instead of hiding them

## Example where AI output was wrong, incomplete, or misleading

One line of AI suggestions pushed toward a much larger design:
- separate ingestion workers
- extra projection tables for every metric
- queue-based processing
- more event-pipeline infrastructure

That advice was not wrong in the abstract, but it was wrong **for this exercise**.

Why it was misleading here:
- the prompt explicitly says no external streaming systems are required
- the exercise is time-boxed to about 2 hours
- adding that much infrastructure would make the submission harder to finish and harder to justify
- it would risk signaling poor scope control

## What I changed or verified myself

I manually decided or verified the following:
- which analytics to expose
- the exact deduplication/correction semantics around `record_id`
- the validation rules that should be strict versus tolerant
- the visit reconstruction behavior and its limits
- which fields should remain in the sanitized analytical model
- the final shape of the markdown explanations
- the sample scenarios used to exercise duplicates, corrections, partial records, and out-of-order data

## How AI influenced the final result

AI influenced the project mostly as:
- a reviewer
- a design challenger
- a documentation editor

The final result is still based on my own implementation choices, manual review, and explicit tradeoffs rather than copy-pasting raw AI output.
