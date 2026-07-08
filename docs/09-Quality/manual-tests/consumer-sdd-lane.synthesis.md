---
type: quality-synthesis
source: docs/09-Quality/manual-tests/consumer-sdd-lane.md
provenance: "Five-minute executable proof that a consumer project can run one feature through a local, durable SDD lane using only the filesystem store, with no external task systems."
---

## What it is
A manual/executable proof that Cognitive OS gives consumer projects a concrete SDD (spec-driven development) workflow — find task, generate spec, approve, implement, review against spec, save evidence — using only the local filesystem, with no dependency on Linear, Jira, GitHub Issues, or dashboards.

## Key mechanics
- Single command: `bash scripts/demo-consumer-sdd-lane.sh`, expected output `CONSUMER_SDD_DEMO: PASS project=<temp project>`.
- The demo builds the `cos` CLI, creates a disposable consumer project, and runs the lane end to end: `cos sdd next` → `cos sdd approve` → `cos sdd apply` → `cos sdd review` → `cos sdd status --json`.
- Verifies durable artifacts are written: `.cognitive-os/workflows/sdd/state.json`, per-feature `requirements.md`, `design.md`, `tasks.md`, `traceability.md`, `review.md`, plus `progress/current.md` and `progress/history.md`.
- Acceptance criteria: `next` creates a `spec_ready` feature; `approve` is a hard gate before `apply`; `review` fails unless every requirement maps to a test or accepted proof (placeholder design/traceability evidence fails review); a passing review transitions the feature to `done` and appends to `progress/history.md`; no external service calls occur.

## Relations & where used
This is the consumer-facing counterpart to the SO's own SDD pipeline (`sdd-propose`/`sdd-spec`/`sdd-design`/`sdd-tasks`/`sdd-apply`/`sdd-verify`/`sdd-archive`) documented in project rules — proving the same discipline is available to downstream adopters via the `cos` CLI rather than the orchestrator's skill set. Related to `consumer-project-primitive-accessibility.md` for verifying downstream projection more broadly.

## Status / caveats
Explicitly scopes its own claims: does NOT claim Linear/Jira/GitHub Issues adapters exist (future phases), and does NOT claim every harness has native lifecycle enforcement — structural harnesses only get instruction projection, with runtime parity bounded by each harness's capability map. No dated run log embedded; this is the procedure/spec, not a captured execution.
