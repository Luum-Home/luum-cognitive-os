# Consumer SDD Lane Manual Proof

> Five-minute proof that a consumer project can move one feature through a local, durable SDD lane without external task systems or dashboards.

## Goal

Prove that Cognitive OS now has a concrete workflow answer for consumer projects:

```text
find task -> generate spec -> approve -> implement -> review against spec -> save evidence
```

The proof uses the local filesystem store only. Linear, Jira, GitHub Issues, dashboards, and remote services are not required.

## Executable Demo

Run from the Cognitive OS source repository:

```bash
bash scripts/demo-consumer-sdd-lane.sh
```

Expected result:

```text
CONSUMER_SDD_DEMO: PASS project=<temp project>
```

## What The Demo Proves

The demo builds the `cos` CLI, creates a disposable consumer project, and runs:

```bash
cos sdd next --feature cli_recent --title "CLI recent" --work-class medium
cos sdd approve cli_recent
cos sdd apply cli_recent
cos sdd review cli_recent
cos sdd status --json
```

It writes and verifies these artifacts:

```text
.cognitive-os/workflows/sdd/state.json
.cognitive-os/workflows/sdd/cli_recent/requirements.md
.cognitive-os/workflows/sdd/cli_recent/design.md
.cognitive-os/workflows/sdd/cli_recent/tasks.md
.cognitive-os/workflows/sdd/cli_recent/traceability.md
.cognitive-os/workflows/sdd/cli_recent/review.md
.cognitive-os/workflows/sdd/progress/current.md
.cognitive-os/workflows/sdd/progress/history.md
```

## Acceptance Criteria

- `cos sdd next` creates a `spec_ready` feature and durable artifacts.
- `cos sdd approve` is required before `cos sdd apply`.
- `cos sdd review` fails unless every requirement maps to a test or accepted proof.
- Placeholder design or traceability evidence does not pass review.
- A passing review transitions the feature to `done` and appends `progress/history.md`.
- The demo does not call external services.

## What This Does Not Claim

This proof does not claim Linear, Jira, or GitHub Issues adapters exist. Those remain later phases after the local contract is stable.

This proof does not claim every harness has native lifecycle enforcement for the lane. Structural harnesses receive instruction projection; runtime parity remains bounded by each harness capability map.
