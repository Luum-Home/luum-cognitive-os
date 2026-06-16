# Artifact Intelligence, Work Graph, Refutation, and Advisor Primitives

Cognitive OS now includes a portable advisory lane for artifact-first agent work.
The lane is generic: it does not assume a programming language, IDE, CLI, or
security workflow. It persists receipts under `.cognitive-os/` so any harness can
inspect progress without relying on hidden conversation state.

## Primitives

| Primitive | Purpose | State |
| --- | --- | --- |
| `scripts/cos-artifact-ingest` | Ingest explicit files or directories into a project-local artifact ledger. | `.cognitive-os/artifacts/ledger.json` |
| `scripts/cos-artifact-watch` | Poll an artifact directory for a bounded number of cycles and ingest changed files. | `.cognitive-os/artifacts/events.jsonl` |
| `scripts/cos-artifact-report` | Summarize artifacts, parse states, signals, and duplicate fingerprints. | stdout JSON/report |
| `scripts/cos-work-graph` | Persist prioritized work tasks with dedupe by fingerprint. | `.cognitive-os/work-graphs/{graph-id}/state.json` |
| `scripts/cos-refutation-review` | Challenge a claim with evidence and optional verification command, then record confidence. | `.cognitive-os/process-loops/{process-id}/refutation-review.jsonl` |
| `scripts/cos-second-pass-advisor` | Run a bounded second-pass advisor command when signals trigger it and store a receipt. | `.cognitive-os/process-loops/{process-id}/advisor-receipts.jsonl` |

All primitives are advisory/candidate maturity. They record evidence and block by
exit code where appropriate, but they do not claim harness-level enforcement.

## Example conversation request

A user or orchestrator can ask:

> Run artifact intelligence and work-graph review for this task, then challenge
> the final claim and run a second-pass advisor if signals justify it.

Equivalent shell flow:

```bash
scripts/cos-artifact-ingest --artifact-dir reports --json
scripts/cos-artifact-report --json
scripts/cos-work-graph add --graph-id task --task-id T1 --title "Review artifact evidence" --priority 5 --json
scripts/cos-refutation-review \
  --process-id task \
  --claim-id final-claim \
  --claim "verification passed" \
  --evidence "pytest output" \
  --verification-command "python3 -m pytest tests/unit/test_example.py -q" \
  --json
scripts/cos-second-pass-advisor \
  --process-id task \
  --signal large-diff \
  --command "python3 scripts/cos-process-loop report --process-id task --json" \
  --timeout-seconds 60 \
  --json
```

## Design contracts

### Artifact Intelligence Plane

- Inputs are files or directories, not hidden conversation state.
- Files are fingerprinted by SHA-256 and tracked with size/mtime metadata.
- Text/YAML/JSON parsing is best-effort. Parse errors are recorded as artifact
  metadata instead of crashing the lane.
- Duplicate fingerprints are reported so agents can avoid re-reading repeated
  evidence.

### Work Graph Ledger

- Tasks have stable ids, priority, status, evidence, and fingerprint.
- Duplicate fingerprints return exit code `2` unless explicitly allowed.
- The next task is selected by highest priority among open tasks.

### Refutation Review Loop

- Claims must have evidence and preferably a verification command.
- The primitive computes an advisory confidence score.
- Unsupported claims are recorded as fresh-review findings under the same
  process loop path used by `cos-fresh-review` and `cos-verify-report`.

### Second-pass Advisor Lane

- Advisors run only when signal thresholds are met or `--force` is passed.
- Every run has a timeout and appends a receipt.
- The receipt marks `read_only_required: true`; callers should use a harness
  sandbox or read-only command policy when available.

## Boundaries

These primitives intentionally avoid domain-specific analysis. Security testing,
web recon, bounty submission, or active verification belongs in optional project
packs, not Cognitive OS core.
