---
adr: 337
title: Agent Process Loop Contract Layer
status: accepted
implementation_status: implemented
date: '2026-06-13'
supersedes: []
superseded_by: null
implementation_files:
  - templates/process-contract.example.yaml
  - scripts/cos-process-loop
  - scripts/cos-apply-progress
  - scripts/cos-fresh-review
  - scripts/cos-verify-report
  - scripts/cos_process_loop.py
  - tests/unit/test_cos_process_loop.py
  - tests/red_team/portability/test_cos_process_loop_primitives.py
tier: consumer
tags: [agent-loop, process-contract, review, verification, portability]
classification_basis: portable CLI wrappers, project-local process-loop state, apply progress, fresh review findings, verification report, final verdict gating, and consumer-project portability tests
---

# ADR-337: Agent Process Loop Contract Layer

## Status

Accepted — implemented on 2026-06-13.

## Context

ADR-336 introduced low-level loop primitives for bounded iterations, traces, guard checks, replay, and eval export. That was necessary but not sufficient for full agent process engineering. Real coding-agent delivery needs a higher-level contract that survives compaction and handoff: what issue or spec is being implemented, which skills were selected, what apply progress exists, what a fresh review found, whether the fix-review loop is closed, what verification report exists, and what final verdict can honestly be claimed.

Without this process contract, agents can still record loop ticks while losing the delivery state that determines whether implementation is actually complete.

## Decision

Add a portable process-loop layer above the loop runtime:

- `templates/process-contract.example.yaml` defines `cos.process-contract.v1` with source, goal, selected skills, apply progress policy, fresh review policy, verify report policy, fix-review loop policy, and final verdict requirements.
- `scripts/cos-process-loop` initializes, reports, and records final verdict for a process loop.
- `scripts/cos-apply-progress` records task/application progress events.
- `scripts/cos-fresh-review` records independent review findings and resolution state.
- `scripts/cos-verify-report` runs or records verification commands into a project-local verify report.
- `scripts/cos_process_loop.py` is the shared dependency-light engine for those wrappers.

State is project-local under `.cognitive-os/process-loops/{process-id}/`:

- `contract.json`
- `state.json`
- `trace.jsonl`
- `apply-progress.jsonl`
- `review-findings.jsonl`
- `verify-report.json`
- `final-verdict.json`

A passing final verdict is blocked when required verification has not passed, when open blocking review findings remain, or when apply progress contains blocked tasks.

## Consequences

Positive:

- Agent work can be audited as a process, not only as individual loop iterations.
- Review findings and fix-review closure become durable artifacts instead of chat-only context.
- Verification evidence and final verdict are mechanically linked.
- The layer is harness-neutral and works from arbitrary consumer project roots.

Tradeoffs:

- Initial maturity is advisory/candidate. It does not forcibly intercept every IDE/CLI action.
- Fresh review quality depends on the reviewer or reviewing tool supplying meaningful findings.
- Process contracts are project-authored; Cognitive OS supplies the schema and CLI enforcement around evidence and verdicts.

## Alternatives rejected

- **Keep process state only in task lists or chat summaries** — rejected because compaction and cross-CLI handoff lose key evidence and review status.
- **Use only ADR-336 loop traces** — rejected because loop traces answer what happened per iteration, not whether source/spec, selected skills, apply progress, fresh review, verification, and verdict all line up.
- **Make the first version a harness-native orchestrator** — rejected because Codex, Claude, OpenCode, IDEs, and shell-only consumers expose different interception capabilities. A portable CLI/process contract can be validated first.

## Verification

The decision is verified by unit behavior, wrapper portability, syntax, and closure commands:

```bash
python3 -m py_compile scripts/cos_process_loop.py tests/unit/test_cos_process_loop.py tests/red_team/portability/test_cos_process_loop_primitives.py
python3 -m pytest tests/unit/test_cos_process_loop.py tests/red_team/portability/test_cos_process_loop_primitives.py -q
bash -n scripts/cos-process-loop scripts/cos-apply-progress scripts/cos-fresh-review scripts/cos-verify-report
scripts/cos-primitive-closure-check --strict
```

Manual smoke proof for consumer-project portability:

```bash
tmp=$(mktemp -d)
cp templates/process-contract.example.yaml "$tmp/process-contract.yaml"
scripts/cos-process-loop init --project-dir "$tmp" --contract "$tmp/process-contract.yaml" --json
scripts/cos-apply-progress --project-dir "$tmp" --process-id example-process-loop --task-id T1 --title implement --status done --json
scripts/cos-fresh-review --project-dir "$tmp" --process-id example-process-loop --finding-id R1 --severity major --status resolved --summary reviewed --json
scripts/cos-verify-report --project-dir "$tmp" --process-id example-process-loop --command "python3 -c 'raise SystemExit(0)'" --json
scripts/cos-process-loop verdict --project-dir "$tmp" --process-id example-process-loop --status passed --summary done --json
scripts/cos-process-loop report --project-dir "$tmp" --process-id example-process-loop --json
```
