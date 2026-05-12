---
adr: 36
title: Sprint orchestration primitives
status: proposed
implementation_status: partial
date: '2026-04-20'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: explicit prose status migration for previously prose-only ADR
---

# ADR-036: Sprint orchestration primitives

## Status
Proposed — MVP implemented 2026-04-20 (CLI skeleton + manifest + canonical events + example spec). Wave 1 test aggregation shipped 2026-04-21. Dispatch wiring via `cos sprint run --dispatch` shipped 2026-05-01. TUI, `SprintTestSummary` event emission, and consolidated-commit execution remain deferred to follow-up waves.

## Context

Claude Code ships a multi-agent task panel that makes a batch of sub-agents feel like a coherent "sprint": one view shows #, task title, tools used, tokens spent, elapsed, status. That panel is powerful but harness-proprietary — it cannot be reproduced for OpenCode, Aider, Cursor, or Continue, and it is not reproducible (the spec is ephemeral chat text, not a file).

COS already has the plumbing to make this harness-agnostic:
- ADR-033 defines a canonical event schema (`AgentStart`, `AgentEnd`, `TokenUsage`, ...) that every adapter emits.
- ADR-034 streams those events live to `canonical-live.jsonl`.
- `cos-watch.py` already tails live events for a single agent.

What is missing is the **sprint** as a first-class artifact: a declarative YAML that names a batch of tasks, a durable manifest that records their state, canonical events that describe sprint lifecycle, and a CLI that drives them. Without these primitives, "run 5 agents together" is a chat-only workflow that never survives a session.

This ADR introduces the primitives. The MVP ships the manifest + CLI + events; the richer UX (TUI, aggregator, consolidated commit) layers on top without changing the contract.

## Decision

Introduce `cos sprint` as a first-class concept with four primitives:

1. **Sprint YAML spec** — declarative batch definition (see schema below).
2. **Sprint manifest** — durable JSON record under `.cognitive-os/sprints/<id>.json`.
3. **Canonical sprint events** — extend ADR-033 registry with `SprintStarted`, `SprintTaskLaunched`, `SprintTaskCompleted`, `SprintCancelled`, `SprintCompleted`.
4. **CLI `cos sprint {run,status,list,cancel}`** — operator surface, harness-agnostic.

### Sprint YAML spec format

```yaml
name: "example-mvp-sprint"              # required
id: sprint-xxxx                         # optional — auto-generated if absent
commit_strategy: per_task               # per_task | squash | none  (default: per_task)
notes: "free-form"                      # optional
tasks:                                  # required, non-empty
  - id: fix-login-bug                   # optional — auto t1, t2, ...
    title: "Fix null-pointer in login handler"   # required
    prompt: "Investigate the NPE ..."   # required — full prompt body
    file_scope:                         # optional — list of files/dirs
      - src/auth/login.py
    model: sonnet                       # opus | sonnet | haiku (default: sonnet)
```

Validation rules (enforced by `load_spec`):
- root must be a mapping with `name` (str) and non-empty `tasks` list;
- each task must have `title` and `prompt`;
- `commit_strategy` ∈ `{per_task, squash, none}`;
- `file_scope` is optional but if present must be a list of strings;
- unknown keys are preserved only where the dataclass accepts them (forward-compat reserved for follow-up waves).

### Sprint manifest schema

Persisted as JSON under `.cognitive-os/sprints/<sprint_id>.json`:

```json
{
  "id": "sprint-abc12345",
  "name": "example-mvp-sprint",
  "commit_strategy": "per_task",
  "status": "pending",
  "created_at": 1745179200.0,
  "started_at": null,
  "ended_at": null,
  "spec_path": ".cognitive-os/sprints/example-sprint.yaml",
  "notes": "Demonstrates the ADR-036 sprint YAML schema.",
  "tasks": [
    {
      "id": "fix-login-bug",
      "title": "Fix null-pointer in login handler",
      "prompt": "Investigate ...",
      "file_scope": ["src/auth/login.py"],
      "model": "sonnet",
      "status": "pending",
      "started_at": null,
      "ended_at": null,
      "agent_id": null
    }
  ]
}
```

Sprint status machine:

```
pending ──► running ──► completed
   │           ├──────► failed
   └───────────┴──────► cancelled
```

Terminal states (`completed`, `failed`, `cancelled`) do not transition further. `transition()` in `lib.sprint_orchestrator` is the single write path and raises `ValueError` on illegal moves.

### Canonical sprint events (extends ADR-033)

All events subclass `CanonicalEvent`, auto-register under `CanonicalEvent._registry`, and round-trip via `to_dict` / `from_dict`. They MUST be importable via `lib.harness_adapter.base` after `sprint_orchestrator` is imported (the subclass `__init_subclass__` wires the registry).

| `event_type`              | Fields                                                                        | Emitted when                         |
|---------------------------|-------------------------------------------------------------------------------|--------------------------------------|
| `sprint_started`          | `sprint_id, sprint_name, task_count, started_at, commit_strategy, session_id` | `cos sprint run` persists manifest   |
| `sprint_task_launched`    | `sprint_id, task_id, agent_id, model, launched_at, session_id`                | Orchestrator dispatches a task-agent |
| `sprint_task_completed`   | `sprint_id, task_id, agent_id, exit_status, ended_at, duration_ms, session_id`| Task-agent reaches `AgentEnd`        |
| `sprint_cancelled`        | `sprint_id, cancelled_at, reason, session_id`                                 | `cos sprint cancel`                  |
| `sprint_completed`        | `sprint_id, ended_at, tasks_succeeded, tasks_failed, duration_ms, session_id` | All tasks reached a terminal state   |

`agent_id` on launch/complete events MUST equal the `agent_id` on the paired ADR-033 `AgentStart` / `AgentEnd` so downstream consumers can join across streams.

### CLI contract

```
cos sprint run <spec.yaml>         # validate spec, write manifest + launch.md, emit SprintStarted
cos sprint status <sprint_id>      # render manifest + tail of canonical-live.jsonl
cos sprint list                    # table of all manifests under .cognitive-os/sprints/
cos sprint cancel <sprint_id>      # transition → cancelled, emit SprintCancelled
```

Exit codes:
- `0` success
- `1` user error (missing file, bad args)
- `2` spec validation error
- `3` state error (manifest missing, illegal transition)

`--json` flag on `status` and `list` yields machine-readable output.

Both `status` and `list` read the manifest + `canonical-live.jsonl` only — no network, no agent launch.

### `cos watch --sprint` UX mockup (follow-up)

```
┌ Sprint: example-mvp-sprint (sprint-abc12345)      status: running  ────────────┐
│  #  TASK                                   MODEL    TOOLS  TOK   ELAPSED  STATUS│
│  1  fix-login-bug                          sonnet   14     8.2k  01:12    running│
│  2  refactor-cache-layer                   opus     27     21.4k 03:40    running│
│  3  update-docs-rate-limits                haiku    5      1.1k  00:18    done   │
├──────────────────────────────────────────────────────────────────────────────────┤
│ Totals: 3 tasks · 1 done · 2 running · tokens 30.7k · cost $0.41                 │
│ Press [c] cancel · [s] show last event · [q] quit                                │
└──────────────────────────────────────────────────────────────────────────────────┘
```

Implementation sketch: extend `scripts/cos_watch.py` to accept `--sprint <id>`, group events by `sprint_id` + `task_id`, render with the existing rich/textual stack. The data feeding the table is already emitted by MVP events — only the rendering is deferred.

### Test aggregation algorithm (follow-up)

```
inputs:
  sprint_id
  per-task test output (stdout+stderr captured to metrics/task-<agent_id>.log)
algorithm:
  1. For each task: detect runner (pytest, go test, jest, vitest) by regex on log.
  2. Parse runner-specific summary line (e.g. "5 passed, 1 failed" for pytest).
  3. Sum across tasks → {passed, failed, skipped, error}.
  4. Emit SprintTestSummary canonical event (to be added in follow-up).
  5. If any task has failed > 0 → sprint transitions to failed on SprintCompleted.
```

MVP provides `aggregate_test_results_stub()` as a placeholder signature so callers can wire the interface now.

### Consolidated commit strategy (follow-up)

Three strategies declared in the spec:
- `per_task` (MVP default): each task commits as it finishes. Fast feedback; history = one commit per task.
- `squash` (follow-up impl): on `SprintCompleted`, orchestrator runs `git reset --soft <base>` then a single commit with the sprint name as subject and a body listing each task. If any task failed, squash is skipped and strategy degrades to `per_task` for successes.
- `none`: never commit — the caller (e.g. a CI driver) handles git.

Safety rules for `squash`:
- base ref captured at sprint start (`git rev-parse HEAD` → `manifest.base_ref`); squash refuses if HEAD has moved beyond the expected task commits.
- all affected files must be in at least one task's `file_scope`, or the squash is aborted with a structured error.
- on any git failure, keep the per-task commits intact and emit `SprintCompleted` with a `squash_failed` note.

MVP provides `consolidate_commits_stub()` so callers can import a stable symbol.

## Rollout waves

| Wave | Scope | Status |
|------|-------|--------|
| MVP (this ADR) | YAML spec, manifest persistence, 5 canonical events, `cos sprint {run,status,list,cancel}`, example spec, unit+integration tests | Shipped |
| Wave 1 (test aggregator) | `lib/sprint_test_aggregator.py` (pytest/go/jest/vitest parsing + regression detection), `scripts/sprint-test-summary.sh` CLI (text + `--json`), 13 unit tests | **Shipped 2026-04-21** |
| Beta | `cos watch --sprint` TUI, `SprintTestSummary` canonical event emission, orchestrator wiring that actually dispatches agents from `run` | Partial: dispatch shipped 2026-05-01; TUI/event emission pending |
| Full | Consolidated-commit impl (`squash`), notifier on completion, multi-project sprint registry, retry-failed-tasks | Follow-up (pending) |

## Consequences

### Easier
- Sprints become reproducible artifacts (YAML → manifest → events).
- Harness-agnostic: the exact same CLI drives Claude Code, OpenCode, Aider.
- Canonical events already integrate with cost-dashboard, SLO probes, and watchdogs — zero new sinks required.
- Operator UX is consistent with existing `cos` subcommands (`status`, `list`).

### Harder
- Sprint manifests add a new write surface; corruption must be tolerated (`list_manifests` already skips bad JSON).
- Orchestrator dispatch is now available through `cos sprint run --dispatch`; the `launch.md` hand-off remains as a human-readable fallback prompt for harnesses or operators that choose manual launch.
- YAML parsing: we ship a minimal fallback parser for environments without PyYAML. This is intentional (zero-dep stdlib policy for lib/) but limits spec complexity. Users who need richer YAML install PyYAML.

### Risks
- **Skew between manifest and live events**: if the orchestrator fails to call `transition()` after emitting events, status lies. Mitigation: follow-up wave adds a reconciliation pass on `cos sprint status` that derives status from the event stream when manifest looks stale.
- **Launch script drift**: the MVP `launch.md` is a hand-off document; if the orchestrator reinvents the dispatch logic elsewhere, the two will diverge. Mitigation: beta wave replaces `launch.md` with a direct orchestrator hook that reads the manifest.

## Dependencies

- **ADR-033** (canonical event schema) — required. Sprint events subclass `CanonicalEvent` and share the registry.
- **ADR-034** (live streaming) — required for `cos sprint status` tail and for the follow-up TUI.

## Follow-up tasks

1. **TUI — `cos watch --sprint <id>`**: extend `scripts/cos_watch.py` with a sprint-grouping table. Data source: `canonical-live.jsonl` filtered by `sprint_id`. Implement as Textual/rich table; reuse existing cost/token formatters.
2. **Test aggregator — `lib/sprint_aggregator.py`**: implement `aggregate_test_results()` (pytest, go test, jest, vitest parsers), add `SprintTestSummary` canonical event, wire into `SprintCompleted` emission.
3. **Consolidated commits — `lib.sprint_commit`**: implement `squash` strategy with safe rollback, capture base ref at `SprintStarted`, enforce file-scope guardrails.
4. **Notifier**: on `SprintCompleted`, emit a desktop/terminal notification summarizing pass/fail counts and total cost.

## Resolution Log

- **2026-04-21 — Wave 1 (test aggregator) DELIVERED.** Implemented `lib/sprint_test_aggregator.py`
  with the contract from §"Test aggregation algorithm": per-session reader with primary source
  (`.cognitive-os/sessions/<id>/test-results.jsonl`) and fallback (`metrics/task-*.log` regex
  parsing for pytest, go test, jest, vitest). Aggregator returns rolled-up totals, per-suite
  breakdown, per-runner breakdown, and chronological pass→fail regressions. CLI wrapper
  `scripts/sprint-test-summary.sh` supports explicit session IDs, auto-detection of recent
  sessions (`--limit N`), and JSON output (`--json`). Exit code 1 when totals include failures
  or errors. 13 unit tests in `tests/unit/test_sprint_test_aggregator.py` (all green). The
  `SprintTestSummary` canonical event emission is explicitly deferred to the Beta wave per
  the Rollout waves table — aggregator returns a plain dict consumable by whoever wires the
  event next. **Still pending**: TUI (`cos watch --sprint`) and consolidated-commit (`squash`).
  Existing `aggregate_test_results_stub()` in `lib/sprint_orchestrator.py` remains for API
  stability; Beta wave should replace it with a thin shim over `aggregate()`.
- **2026-05-01 — Dispatch wiring DELIVERED.** `scripts/cos_sprint.py run --dispatch` now
  transitions the manifest to running, invokes each task through `bin/cos-agent spawn --json`,
  records `SprintTaskLaunched`, `SprintTaskCompleted`, and `SprintCompleted` events, and
  persists task-level status back to `.cognitive-os/sprints/<id>.json`. The launch Markdown
  remains as a manual fallback, not the primary execution path. Covered by
  `tests/integration/test_cos_sprint_cli.py::test_run_dispatch_updates_manifest_and_events`.
