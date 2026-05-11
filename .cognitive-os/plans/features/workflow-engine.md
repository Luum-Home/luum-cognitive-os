<!--
RECONCILIATION STATUS: TOMBSTONE — 2026-05-10 (post-v0.28.0)
Reconciled-by: P3 plan triage (see docs/reports/p3-plan-triage-2026-05-10.md)
Decision: TOMBSTONE.
Rationale: The External Tool Adoption Doctrine (docs/architecture/external-tool-adoption-doctrine.md, ratified by ADR-254) explicitly DEFERs "Distributed workflow engines: Temporal, NATS, Firecracker-primary, OPA-by-default" with the rule "Local-first event bus, file-IPC, release freeze, and worktree governance" instead. ADR-036 (sprint orchestration primitives) plus @event_wrap + ADR-226 cover the MVP slice already, and lib/workflow_engine.py / lib/workflow_types.py do not exist nor are they planned. Building this engine would directly contradict accepted doctrine and duplicate mechanisms COS has decided to integrate (FastMCP, agentapi adapter, MCP) rather than reimplement. Move to .cognitive-os/plans/archive/tombstones/ in a future tidy commit (recommendation only; do not move now). If a Shape-B trigger ever fires for federation/cluster runtime per ADR-132, revisit via ADR-254 manifest/audit/research-check path — not by reviving this plan as-is.
Older inline reconciliation history (preserved for audit):
ON ICE — 2026-04-27
Related ADRs: ADR-036 (sprint orchestration primitives — MVP shipped 2026-04-20: CLI + manifest + canonical events + example spec)
Reconciled: 2026-04-21 (initial scope note); re-audited 2026-04-27 (no engineering progress)
Audit 2026-04-27: lib/workflow_engine.py and lib/workflow_types.py do not exist. .cognitive-os/workflows/ contains only bugfix-pipeline.yaml + feature-pipeline.yaml, neither matching the 5 pre-built workflows the plan specifies. tests/unit/test_workflow_engine.py absent. Zero commits in last 60 reference workflow-engine. Marked ON ICE — re-activate when SDD pipeline failure recovery becomes a recurring pain point (signal: ≥3 incidents where a partial pipeline can't resume) or operator prioritizes.
Remaining scope (preserved for unfreezing): DAG-with-dependencies, resumability of failed pipelines, SDD-pipeline-as-data. ADR-036 covers batch launching (sprint YAML → parallel agents) but not these three.
-->

# Workflow Engine — Declarative DAG Execution for Cognitive OS

> Last updated: 2026-04-13
> Status: PLANNING — not yet started
> Phase: 1 of 3

---

## 1. Current State

### 1.1 How Multi-Step Workflows Are Run Today

All multi-step workflows (SDD pipeline, CI checks, release flows) are executed by the
orchestrator manually: it launches agents one at a time, waits for each to complete,
reads the result, decides what to do next, and launches the next agent. This is:

- **Fragile**: If the orchestrator's context is compacted mid-pipeline, the workflow is
  lost. There is no state persistence for in-progress pipelines.
- **Non-resumable**: A failed or interrupted SDD pipeline cannot be resumed. The user
  must restart from the beginning or manually figure out what step was last completed.
- **Hard-coded**: The SDD pipeline logic lives in the orchestrator's rules, not in a
  data file. Changing the pipeline requires editing CLAUDE.md or skills — a code change.
- **Sequential only**: Independent tasks (e.g., `sdd-spec` and `sdd-design`) run
  sequentially even though they could run in parallel, wasting wall-clock time.
- **No visibility**: There is no dashboard showing which task is running, which
  succeeded, and which failed mid-pipeline.

### 1.2 Existing Infrastructure Available

The following components exist and will be integrated:

| Component | Location | Role in Workflow Engine |
|-----------|----------|------------------------|
| Engram memory | `lib/engram_*` | State persistence for cross-session recovery |
| Agent Bus (Valkey) | `lib/agent_bus.py` | Real-time task progress publishing |
| Task Queue | `lib/task_queue.py` | Pending task buffering |
| Agent Monitor | `lib/agent_monitor.py` | Dashboard for agent/task progress |
| Hook system | `hooks/` | Event emission at workflow lifecycle points |
| Session state | `lib/session_state.py` | In-session checkpoint files |
| SDD pipeline logic | `rules/` + `CLAUDE.md` | Existing workflow definitions to migrate |

### 1.3 Gap

There is no runtime that takes a declarative workflow definition and executes it as a
DAG with dependency tracking, parallel execution, retry, and resumability. That is what
this plan builds.

---

## 2. Target State

A declarative workflow engine that:

1. Reads YAML workflow definitions from `.cognitive-os/workflows/`
2. Parses each workflow into a DAG of tasks with typed edges (dependency, condition)
3. Executes tasks in topological order, parallelizing independent tasks
4. Handles failures with configurable strategies: retry, skip, escalate, circuit breaker
5. Persists state to `.cognitive-os/sessions/{id}/workflow-state.json` after every task
6. Resumes interrupted workflows from the last checkpoint
7. Fires hooks at workflow lifecycle events (started, task started, task completed, failed)
8. Publishes real-time progress to the Agent Bus and Agent Monitor dashboard

### 2.1 Workflow Definition Format

Workflows are YAML files stored in `.cognitive-os/workflows/`. Example:

```yaml
name: sdd-pipeline
description: Full SDD pipeline for changes
version: "1.0"
triggers:
  - command: /sdd-ff
  - command: /sdd-new

tasks:
  explore:
    type: agent
    model: sonnet
    skill: sdd-explore
    timeout: 300s

  propose:
    type: agent
    model: opus
    skill: sdd-propose
    depends_on: [explore]

  spec:
    type: agent
    model: sonnet
    skill: sdd-spec
    depends_on: [propose]

  design:
    type: agent
    model: opus
    skill: sdd-design
    depends_on: [propose]

  tasks:
    type: agent
    model: sonnet
    skill: sdd-tasks
    depends_on: [spec, design]

  apply:
    type: agent
    model: sonnet
    skill: sdd-apply
    depends_on: [tasks]
    retry: 3
    on_failure: escalate

  verify:
    type: agent
    model: sonnet
    skill: sdd-verify
    depends_on: [apply]

  archive:
    type: agent
    model: haiku
    skill: sdd-archive
    depends_on: [verify]
    condition: "verify.status == 'pass'"
```

### 2.2 Task Types

| Type | Description | Example |
|------|-------------|---------|
| `agent` | Launches a Claude Code Agent tool sub-agent | `skill: sdd-apply`, `model: sonnet` |
| `bash` | Runs a shell command | `command: "yarn test --coverage"` |
| `skill` | Invokes a skill directly (no full sub-agent) | `skill: dod-check` |
| `workflow` | Nested workflow (composition) | `workflow: ci-check` |
| `gate` | Human approval checkpoint — pauses until user confirms | `message: "Review changes before release?"` |

### 2.3 Failure Strategies

| Strategy | Behavior |
|----------|----------|
| `retry` | Re-run the task up to N times before marking failed |
| `skip` | Mark task as skipped, continue to dependent tasks that allow skipped deps |
| `escalate` | Pause workflow, surface to user with diagnosis |
| `fail_fast` | Mark workflow failed immediately, stop all tasks |
| `circuit_breaker` | After N failures in rolling window, switch to fallback task |

### 2.4 State Persistence Schema

Each in-progress workflow writes to `.cognitive-os/sessions/{session_id}/workflow-state.json`:

```json
{
  "workflow": "sdd-pipeline",
  "run_id": "uuid-v4",
  "session_id": "session-123",
  "started_at": "ISO-8601",
  "last_updated": "ISO-8601",
  "status": "running",
  "tasks": {
    "explore": { "status": "completed", "started_at": "...", "completed_at": "...", "output_ref": "engram:sdd/change/explore" },
    "propose": { "status": "running",   "started_at": "...", "attempt": 1 },
    "spec":    { "status": "pending" },
    "design":  { "status": "pending" }
  },
  "context": {
    "change": "workflow-engine",
    "inputs": {}
  }
}
```

---

## 3. Architecture

### 3.1 Core Components

```
lib/workflow_engine.py
├── WorkflowEngine          — top-level orchestrator, loads + runs workflows
├── WorkflowParser          — YAML → WorkflowDefinition
├── DAGBuilder              — WorkflowDefinition → nx.DiGraph (task nodes + dependency edges)
├── TaskExecutor            — executes a single task by type (agent, bash, skill, gate)
├── ConditionEvaluator      — evaluates condition expressions ("verify.status == 'pass'")
├── RetryPolicy             — applies retry/skip/escalate/fail_fast strategy
├── StateManager            — reads/writes workflow-state.json, saves to Engram
├── WorkflowHookEmitter     — fires WorkflowStarted/TaskStarted/TaskCompleted hooks
└── WorkflowScheduler       — topological sort + parallel task dispatch
```

### 3.2 Execution Model

```
WorkflowEngine.run(workflow_name, context)
    │
    ├── load + parse YAML → WorkflowDefinition
    ├── resume from state if workflow-state.json exists (same run_id in context)
    │
    └── WorkflowScheduler.execute_dag(dag, state)
            │
            ├── topological_sort(dag) → execution layers
            │   Layer 0: [explore]
            │   Layer 1: [propose]          (depends on explore)
            │   Layer 2: [spec, design]     (both depend on propose — PARALLEL)
            │   Layer 3: [tasks]            (depends on spec + design)
            │   Layer 4: [apply]
            │   Layer 5: [verify]
            │   Layer 6: [archive]
            │
            └── for each layer:
                    ├── filter tasks by condition (skip if condition is false)
                    ├── dispatch parallel tasks via asyncio.gather()
                    ├── for each task:
                    │   ├── emit TaskStarted hook
                    │   ├── TaskExecutor.execute(task, context)
                    │   ├── on success: update state, emit TaskCompleted hook
                    │   └── on failure: apply RetryPolicy
                    └── StateManager.checkpoint(state)  ← after every layer
```

### 3.3 Integration Points

| Integration | Mechanism | When |
|-------------|-----------|------|
| Hooks | `WorkflowHookEmitter` writes to `.hook-pipe/workflow-events.jsonl` | WorkflowStarted, TaskStarted, TaskCompleted, WorkflowCompleted, WorkflowFailed |
| Engram | `StateManager.save_to_engram()` after each task completes | Task completion, workflow completion |
| Agent Bus | `lib/agent_bus.py publish()` to `workflow:{run_id}` channel | Task status changes (for real-time dashboard) |
| Agent Monitor | Reads from Agent Bus; workflow run shown as progress tree | Ongoing execution |
| Task Queue | `lib/task_queue.py enqueue()` for pending agent tasks | When agent task is dispatched |
| Session state | `workflow-state.json` written after every layer | After each layer completes |

---

## 4. Pre-Built Workflows to Ship

### 4.1 `sdd-pipeline.yaml` — Full SDD Flow

explore → propose → spec + design (parallel) → tasks → apply → verify → archive

Tasks: 8 (7 agent, 1 conditional on verify.status)
Estimated wall-clock time: 15–25 minutes (with parallel spec+design)

### 4.2 `sdd-fast.yaml` — Fast SDD (Opus skip)

explore → propose → apply → verify → archive

Tasks: 5 agent tasks
Estimated wall-clock: 8–12 minutes
Trigger: `/sdd-ff` when model is opus

### 4.3 `ci-check.yaml` — Lint + Test + Build

```yaml
tasks:
  lint:
    type: bash
    command: "golangci-lint run ./..."
    timeout: 120s
  test:
    type: bash
    command: "go test ./... -short"
    timeout: 300s
    depends_on: [lint]
  build:
    type: bash
    command: "go build ./..."
    timeout: 120s
    depends_on: [test]
```

Tasks: 3 bash (sequential)
Estimated wall-clock: 3–8 minutes

### 4.4 `release.yaml` — Version Bump + Changelog + Tag

version-check → bump-version → update-changelog → gate(review) → git-tag → release-notes

Tasks: 4 bash + 1 gate + 1 agent
Estimated wall-clock: 5 minutes + human review time

### 4.5 `security-audit.yaml` — Security Scan Suite

```yaml
tasks:
  semgrep:
    type: bash
    command: "semgrep scan --config=auto --json > .cognitive-os/metrics/semgrep-results.json"
    timeout: 180s
  aguara:
    type: skill
    skill: aguara-scan
    timeout: 120s
  secret-scan:
    type: bash
    command: "hooks/secret-detector.sh --full-scan"
    timeout: 60s
  report:
    type: agent
    model: sonnet
    skill: audit-report
    depends_on: [semgrep, aguara, secret-scan]
    condition: "semgrep.exit_code != null"
```

Tasks: 3 bash/skill (parallel) + 1 agent report
Estimated wall-clock: 4–6 minutes

---

## 5. Gap Analysis

### 5.1 What Exists vs. What Is Needed

| Component | Exists? | Notes |
|-----------|---------|-------|
| YAML parser for workflows | No | Build with `PyYAML` (already installed) |
| DAG library | No | Use `networkx` (install needed) |
| Async task execution | Partial | `asyncio` available; no workflow-specific wrapper |
| State persistence | Partial | `session_state.py` exists but no workflow schema |
| Retry logic | No | Currently ad-hoc in orchestrator rules |
| Condition evaluation | No | Need safe expression evaluator |
| Hook emitter for workflow events | No | Hook pipe exists, workflow events not defined |
| Agent Bus publishing | Partial | `agent_bus.py` exists; workflow channel not defined |
| Agent Monitor integration | Partial | Monitor exists; no workflow tree view |
| Workflow YAML files | No | 5 files to write |
| Tests | No | Unit + integration test suite needed |

### 5.2 New Dependencies

| Package | Version | Purpose | License |
|---------|---------|---------|---------|
| `networkx` | >=3.0 | DAG construction and topological sort | BSD-3 |
| `PyYAML` | >=6.0 | Already installed | MIT |
| `asyncio` | stdlib | Parallel task execution | PSF |

`networkx` is the only new install. BSD-3 is acceptable under `rules/license-policy.md`.

---

## 6. Implementation Phases

### Phase 1: Engine Core + Sequential Execution (NEXT)

**Goal**: Parse YAML workflow definitions and execute them sequentially with state persistence.
Parallel execution, conditions, and retry come in Phase 2.

**Deliverables**:
- `lib/workflow_engine.py` — `WorkflowParser`, `DAGBuilder`, `TaskExecutor` (agent + bash only), `StateManager`, `WorkflowEngine.run()`
- `lib/workflow_types.py` — `WorkflowDefinition`, `TaskDefinition`, `TaskStatus`, `WorkflowState` dataclasses
- `.cognitive-os/workflows/sdd-pipeline.yaml` — full SDD workflow (sequential for now)
- `.cognitive-os/workflows/ci-check.yaml` — lint/test/build workflow
- `tests/unit/test_workflow_engine.py` — parser tests, DAG construction tests, sequential execution tests
- `docs/workflows.md` — reference for YAML format and task types

**Acceptance Criteria**:
- `python3 -c "from lib.workflow_engine import WorkflowEngine; print('OK')"` exits 0
- `python3 -m pytest tests/unit/test_workflow_engine.py -v` — all tests pass
- `WorkflowEngine.run('ci-check', {})` runs lint→test→build in sequence
- State file written to `.cognitive-os/sessions/test/workflow-state.json` after run
- `python3 -c "import networkx"` exits 0 (networkx installed)

**Estimated cost**: 1 session (sonnet). **Priority**: HIGH.

---

### Phase 2: Parallel Execution + Conditions + Retry + State Recovery

**Goal**: Unlock the full DAG execution model — parallel independent tasks, conditional
task skipping, retry policies, and workflow resume from checkpoint.

**Deliverables**:
- `WorkflowScheduler` — topological layer extraction, `asyncio.gather()` for parallel dispatch
- `ConditionEvaluator` — safe expression evaluation using `ast.literal_eval` + restricted `eval`
- `RetryPolicy` — retry / skip / escalate / fail_fast / circuit_breaker strategies
- `WorkflowHookEmitter` — emits WorkflowStarted, TaskStarted, TaskCompleted, WorkflowCompleted hooks
- `.cognitive-os/workflows/sdd-fast.yaml` — fast SDD with parallel spec+design
- `.cognitive-os/workflows/release.yaml` — release workflow with gate task
- `.cognitive-os/workflows/security-audit.yaml` — security audit with parallel scans
- Resume: `WorkflowEngine.run()` detects existing state file and skips completed tasks
- Tests for: parallel execution, condition evaluation, retry policies, resume

**Acceptance Criteria**:
- `spec` and `design` tasks in `sdd-pipeline.yaml` execute in parallel (both `asyncio` tasks dispatched before either completes)
- A workflow with `condition: "verify.status == 'pass'"` skips `archive` when verify fails
- A task with `retry: 3` is attempted 3 times on failure before the policy fires
- Interrupting a workflow mid-run and re-running with the same `run_id` resumes from the last completed layer
- `python3 -m pytest tests/unit/test_workflow_engine.py tests/integration/test_workflow_execution.py -v` — all tests pass

**Estimated cost**: 1.5 sessions (sonnet). **Priority**: HIGH.

---

### Phase 3: Nested Workflows + Dashboard Integration + External Triggers

**Goal**: Composition, real-time visibility, and trigger wiring.

**Deliverables**:
- `workflow` task type — `TaskExecutor` handles nested workflow invocation recursively
- `skill` task type — invokes a skill directly without full agent context
- `gate` task type — pauses workflow, writes approval request to session state, resumes on `workflow.approve(run_id)`
- Agent Bus publishing — `WorkflowEngine` publishes to `workflow:{run_id}` channel on every state change
- Agent Monitor integration — workflow progress tree view alongside agent progress
- CLI command `cos workflow run <name>` and `cos workflow status <run_id>`
- Trigger wiring — `user-prompt-capture.sh` hook detects `/sdd-ff` and fires `WorkflowEngine.run('sdd-fast', ...)`
- Tests for: nested workflows, gate approval, Agent Bus messages, CLI commands

**Acceptance Criteria**:
- A workflow containing `type: workflow` executes the nested workflow and propagates state
- A `gate` task pauses execution until `cos workflow approve <run_id>` is called
- Agent Monitor shows a workflow progress tree when a workflow is running
- `cos workflow status <run_id>` returns the current state JSON
- All 5 pre-built workflows execute end-to-end without errors (integration test suite)
- `python3 -m pytest tests/` — all tests pass, including integration suite

**Estimated cost**: 1.5 sessions (sonnet). **Priority**: MEDIUM.

---

## 7. File Map

### New Files

```
lib/
  workflow_engine.py         — engine core (WorkflowEngine, WorkflowParser, DAGBuilder,
                               TaskExecutor, StateManager, WorkflowScheduler,
                               ConditionEvaluator, RetryPolicy, WorkflowHookEmitter)
  workflow_types.py          — dataclasses: WorkflowDefinition, TaskDefinition,
                               TaskStatus, WorkflowRunState

.cognitive-os/
  workflows/
    sdd-pipeline.yaml        — full SDD (8 tasks, spec+design parallel)
    sdd-fast.yaml            — fast SDD (5 tasks)
    ci-check.yaml            — lint + test + build (3 bash tasks)
    release.yaml             — version bump + gate + tag (4 tasks)
    security-audit.yaml      — semgrep + aguara + secret-scan + report (4 tasks)

tests/
  unit/
    test_workflow_engine.py  — parser, DAGBuilder, ConditionEvaluator, RetryPolicy
  integration/
    test_workflow_execution.py — end-to-end workflow runs (ci-check, sdd-fast)

docs/
  workflows.md               — YAML format reference, task types, failure strategies
```

### Modified Files

```
lib/agent_monitor.py         — add workflow progress tree view (Phase 3)
lib/agent_bus.py             — add workflow channel constants (Phase 3)
hooks/task-started.sh        — handle WorkflowTaskStarted event (Phase 2)
hooks/task-completed.sh      — handle WorkflowTaskCompleted event (Phase 2)
requirements.txt             — add networkx>=3.0 (Phase 1)
docs/skills-catalog.md       — add workflow-engine entry
```

---

## 8. Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| `networkx` topological sort does not handle conditional edges | LOW | MEDIUM | Pre-filter tasks before building graph; conditions are checked at execution time, not in the DAG |
| Async parallel agents saturate the `max_parallel_agents` limit from `resource-governance.md` | MEDIUM | MEDIUM | `WorkflowScheduler` reads `max_parallel_agents` from `cognitive-os.yaml` before dispatching each layer |
| Resumed workflow uses stale Engram state from a different change | MEDIUM | HIGH | `run_id` (uuid4) is stored in both `workflow-state.json` and Engram; resume validates `run_id` match |
| Condition expression evaluation opens code injection risk | MEDIUM | HIGH | Use `ast.literal_eval` for simple literals; allow only field access (`task.status`) via a whitelist parser; no `eval()` |
| Nested workflow depth causes stack overflow or infinite loops | LOW | HIGH | Maximum nesting depth = 3 (enforced in `WorkflowParser`); circular dependency detection in `DAGBuilder` |
| Pre-built workflows become outdated as skills evolve | MEDIUM | MEDIUM | Workflow YAML is data — updating skill names requires only a YAML edit, no code change |
| Gate task blocks session indefinitely if user never approves | LOW | LOW | Gate has a configurable `timeout`; on timeout fires `on_failure` strategy |

---

## 9. Test Plan

### Phase 1 Tests

| Test | What it checks |
|------|----------------|
| `test_parse_valid_workflow_yaml` | WorkflowParser loads a YAML file into WorkflowDefinition |
| `test_parse_missing_task_type_raises` | Parser raises `WorkflowValidationError` for unknown task types |
| `test_dag_builder_creates_correct_edges` | `sdd-pipeline.yaml` → DAG has edge `explore→propose`, `propose→spec`, `propose→design` |
| `test_dag_builder_detects_cycle` | A YAML with circular `depends_on` raises `CyclicDependencyError` |
| `test_sequential_execution_order` | `ci-check.yaml` executes lint before test before build |
| `test_state_written_after_each_task` | After `explore` completes, `workflow-state.json` has `explore.status = completed` |
| `test_bash_task_executor_captures_exit_code` | Bash task with `exit 0` marks task completed; `exit 1` marks failed |

### Phase 2 Tests

| Test | What it checks |
|------|----------------|
| `test_parallel_tasks_dispatched_concurrently` | `spec` and `design` are both dispatched before either resolves |
| `test_condition_true_task_executes` | Task with `condition: "verify.status == 'pass'"` runs when verify is passed |
| `test_condition_false_task_skipped` | Same condition skips task when verify is failed |
| `test_retry_policy_retries_n_times` | A failing task with `retry: 3` is attempted 3 times |
| `test_retry_policy_escalate_pauses_workflow` | After 3 failures with `on_failure: escalate`, workflow status is `paused` |
| `test_resume_skips_completed_tasks` | Resuming a workflow with `explore: completed` in state does not re-run `explore` |
| `test_hook_emitter_fires_workflow_started` | `WorkflowHookEmitter` writes WorkflowStarted event to hook pipe |

### Phase 3 Tests

| Test | What it checks |
|------|----------------|
| `test_nested_workflow_executes_child` | Task of type `workflow: ci-check` runs ci-check and propagates state |
| `test_nested_workflow_max_depth` | Depth-4 nesting raises `WorkflowNestingDepthError` |
| `test_gate_task_pauses_execution` | Workflow with a gate task pauses at gate; subsequent tasks not started |
| `test_gate_task_resumes_on_approve` | `WorkflowEngine.approve(run_id)` resumes execution after gate |
| `test_agent_bus_publishes_on_task_start` | Agent Bus receives `workflow:{run_id}:task:explore:started` message |
| `test_cli_workflow_status_returns_json` | `cos workflow status <run_id>` prints valid JSON with current state |
| `test_all_prebuilt_workflows_parse` | All 5 YAML files in `.cognitive-os/workflows/` parse without error |

---

## 10. Definition of Done

### Phase 1

- [ ] `lib/workflow_engine.py` and `lib/workflow_types.py` exist and import without errors
- [ ] `networkx` added to `requirements.txt` and importable
- [ ] `sdd-pipeline.yaml` and `ci-check.yaml` exist in `.cognitive-os/workflows/`
- [ ] All Phase 1 unit tests pass: `python3 -m pytest tests/unit/test_workflow_engine.py -v`
- [ ] `WorkflowEngine.run('ci-check', {})` executes lint→test→build (or mocked equivalents) sequentially
- [ ] State file written after each task completion
- [ ] `docs/workflows.md` written with YAML format reference

### Phase 2

- [ ] Parallel task dispatch verified by test (asyncio.gather, not sequential)
- [ ] Condition evaluation safe (no eval(), whitelist parser only)
- [ ] Retry policy covers all 5 strategies
- [ ] Resume from checkpoint tested and working
- [ ] WorkflowHookEmitter fires all 5 lifecycle events
- [ ] All Phase 2 tests pass
- [ ] `sdd-fast.yaml`, `release.yaml`, `security-audit.yaml` exist

### Phase 3

- [ ] Nested workflows execute correctly (max depth=3 enforced)
- [ ] Gate task pauses and resumes workflow correctly
- [ ] Agent Bus publishing verified by integration test
- [ ] `cos workflow status <run_id>` CLI command works
- [ ] All 5 pre-built workflows parse and execute end-to-end (integration suite)
- [ ] Agent Monitor shows workflow progress tree
- [ ] All tests pass: `python3 -m pytest tests/ -v`
