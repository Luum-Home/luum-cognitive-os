---
name: artifact-workflow
version: 1.0.0
description: Run the portable Cognitive OS artifact intelligence, work graph, refutation review, and second-pass advisor lane for any project or stack.
triggers:
  - /artifact-workflow
  - /artifact-intelligence
  - /work-graph
  - run artifact intelligence
  - challenge final claim
  - second-pass advisor
---

# Artifact Workflow

Use this skill when a task needs durable evidence intake, duplicate-aware work
tracking, claim refutation, or a bounded second-pass review. The workflow is
stack-agnostic and persists state under `.cognitive-os/`.

## Procedure

1. Ingest explicit evidence artifacts or a bounded artifact directory:

   ```bash
   scripts/cos-artifact-ingest --artifact-dir <dir> --json
   ```

2. Review the artifact ledger:

   ```bash
   scripts/cos-artifact-report --json
   ```

3. Add or update the work graph for the task:

   ```bash
   scripts/cos-work-graph add --graph-id <task> --task-id T1 --title "<work item>" --priority 5 --json
   scripts/cos-work-graph report --graph-id <task> --json
   ```

4. Challenge important completion claims before final status:

   ```bash
   scripts/cos-refutation-review \
     --process-id <task> \
     --claim-id final-claim \
     --claim "<claim>" \
     --evidence "<evidence>" \
     --verification-command "<command>" \
     --json
   ```

5. Run a bounded second-pass advisor only when signals justify it:

   ```bash
   scripts/cos-second-pass-advisor \
     --process-id <task> \
     --signal large-diff \
     --command "<read-only review command>" \
     --timeout-seconds 120 \
     --json
   ```

## Rules

- Do not treat the artifact ledger as source of truth; inspect source and run tests before final claims.
- Advisor commands must be read-only in intent and bounded by timeout.
- Unsupported claims should remain open fresh-review findings until resolved.
- Do not add domain-specific scanners or active external actions to the generic core workflow.

## Contextual Trigger

Use when the user asks for artifact intelligence, work graph tracking, evidence
ledger, claim refutation, second-pass review, or durable process receipts.
