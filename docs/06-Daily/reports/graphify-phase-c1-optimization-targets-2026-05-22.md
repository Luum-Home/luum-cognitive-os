# Graphify Phase C.1 Optimization Targets Report — 2026-05-22

## Scope

This report executes the recommended Phase C Graphify commands for the first
code-slice candidates and turns the graph output into operator guidance:

- files to preload before working in the area;
- graph paths to inspect;
- tests to run before trusting any optimization;
- extracted evidence kept separate from inference.

Raw command outputs were captured under:

`/tmp/cos-graphify-phase-c1-20260522/`

## Command Syntax Correction

The executable Graphify command form is:

```bash
graphify explain NODE --graph GRAPH
graphify affected NODE --depth 2 --graph GRAPH
graphify path NODE_A NODE_B --graph GRAPH
```

The Phase C report generator was corrected to emit this form before this Phase C.1
run. Earlier placeholder commands that placed the graph path before `--node` were
not executable with the installed Graphify CLI.

## Target Summary

| Slice | Target | Extracted evidence | Preload files | Confirmation tests |
|---|---|---|---|---|
| `lib` | `CanonicalEvent` / `harness_adapter/base.py` | `CanonicalEvent` has degree 43; affected output points to harness adapters and `sprint_orchestrator.py`. | `lib/harness_adapter/base.py`, `lib/harness_adapter/codex.py`, `lib/harness_adapter/aider.py`, `lib/harness_adapter/aider_streaming.py`, `lib/harness_adapter/bare_cli.py`, `lib/harness_adapter/dispatch.py`, `lib/sprint_orchestrator.py` | `tests/unit/test_harness_adapter_base.py`, `tests/unit/test_sprint_orchestrator.py`, `tests/integration/test_preamble_v2_wave1.py` |
| `lib` | `history_sanitization.py` | degree 50; no affected reverse nodes; path to `claude_executor.py` traverses generic exception/enum nodes, so the relation is weak. | `lib/history_sanitization.py`, `lib/history_rewrite_ledger.py`, `scripts/cos-history-sanitization`, `scripts/cos-filter-repo-wrap.sh` | `tests/unit/test_history_sanitization.py`, `tests/behavior/test_history_sanitization_cli.py`, `tests/behavior/test_history_sanitization_execute.py`, `tests/contracts/test_history_rewrite_ledger_append_only.py` |
| `hooks` | `destructive-git-blocker.sh` | degree 23; no affected reverse nodes; internal function fan-out is high. | `hooks/destructive-git-blocker.sh`, `hooks/_lib/common.sh`, `hooks/_lib/killswitch_check.sh`, `hooks/_lib/bypass-resolver.sh`, `hooks/_lib/governance_phase_policy.sh`, `hooks/_lib/registration-allowlist.txt` | `tests/chaos/test_reset_cascade_detector.py`, `tests/chaos/test_safety_drill.py`, `tests/chaos/test_multi_ide_swarm_safety.py` |
| `scripts` | `cos_work_inventory.py` | degree 51; no affected reverse nodes; internal function fan-out is high. | `scripts/cos_work_inventory.py`, `scripts/cos-doctor-work-inventory.sh`, `scripts/cos-doctor-concurrency.sh`, `hooks/agent-prelaunch.sh` | `tests/unit/test_cos_work_inventory.py`, `tests/audit/test_cos_work_inventory_refinements.py`, `tests/behavior/test_agent_prelaunch_read_only.py`, `tests/red_team/portability/test_cos_work_inventory.py` |
| `packages/agent-service` | `BaseModel` consumers | degree 36; affected output identifies `StoredSession` in `agent_service/store.py`. | `packages/agent-service/src/agent_service/models/session.py`, `packages/agent-service/src/agent_service/store.py`, `packages/agent-service/src/agent_service/models/__init__.py`, `packages/agent-service/src/agent_service/routers/sessions.py` | `packages/agent-service/tests/test_contract.py`, `packages/agent-service/tests/test_sessions.py`, `packages/agent-service/tests/test_health.py` |

## Extracted Evidence

### `lib` — `CanonicalEvent`

Command:

```bash
/tmp/graphify-venv/bin/graphify explain 'CanonicalEvent' --graph /tmp/cos-graphify-phase-b-20260522/lib/graphify-out/graph.json
/tmp/graphify-venv/bin/graphify affected 'CanonicalEvent' --depth 2 --graph /tmp/cos-graphify-phase-b-20260522/lib/graphify-out/graph.json
```

Observed:

- `CanonicalEvent` source: `harness_adapter/base.py L49`.
- Degree: 43.
- Direct graph neighbors include `codex.py`, `bare_cli.py`, `aider.py`,
  `claude_code.py`, `dispatch.py`, `aider_streaming.py`, event subclasses, and
  adapter classes.
- Affected output includes `singularity.py`, `sprint_orchestrator.py`, harness
  adapter modules, adapter classes, and generic base classes.

### `lib` — `history_sanitization.py`

Command:

```bash
/tmp/graphify-venv/bin/graphify explain 'history_sanitization.py' --graph /tmp/cos-graphify-phase-b-20260522/lib/graphify-out/graph.json
/tmp/graphify-venv/bin/graphify affected 'history_sanitization.py' --depth 2 --graph /tmp/cos-graphify-phase-b-20260522/lib/graphify-out/graph.json
/tmp/graphify-venv/bin/graphify path 'history_sanitization.py' 'claude_executor.py' --graph /tmp/cos-graphify-phase-b-20260522/lib/graphify-out/graph.json
```

Observed:

- `history_sanitization.py` source: `history_sanitization.py L1`.
- Degree: 50.
- It contains many local functions including `execute()`, `scan()`,
  `build_report()`, `_run_filter_repo()`, `_verify_replacements_applied()`, and
  manifest/rule helpers.
- Affected output found no reverse impacted nodes.
- The shortest path to `claude_executor.py` exists but crosses generic nodes:
  `SanitizationError`, `RuntimeError`, `IdempotencyConflict`, `FailureClass`, and
  `Enum`. Treat this path as weak navigation evidence, not a functional coupling.

### `hooks` — `destructive-git-blocker.sh`

Command:

```bash
/tmp/graphify-venv/bin/graphify explain 'destructive-git-blocker.sh' --graph /tmp/cos-graphify-phase-b-20260522/hooks/graphify-out/graph.json
/tmp/graphify-venv/bin/graphify affected 'destructive-git-blocker.sh' --depth 2 --graph /tmp/cos-graphify-phase-b-20260522/hooks/graphify-out/graph.json
```

Observed:

- `destructive-git-blocker.sh` source: `destructive-git-blocker.sh L1`.
- Degree: 23.
- The node defines/calls blocker internals such as `_has_allow_main_branch_flag()`,
  `_has_allow_branch_switch_flag()`, `_is_fetch_reset_chain()`, `_has_wip()`,
  `_semantic_git_match()`, `_git_emit_intervention()`, and bypass helpers.
- Affected output found no reverse impacted nodes.

### `scripts` — `cos_work_inventory.py`

Command:

```bash
/tmp/graphify-venv/bin/graphify explain 'cos_work_inventory.py' --graph /tmp/cos-graphify-phase-b-20260522/scripts/graphify-out/graph.json
/tmp/graphify-venv/bin/graphify affected 'cos_work_inventory.py' --depth 2 --graph /tmp/cos-graphify-phase-b-20260522/scripts/graphify-out/graph.json
```

Observed:

- `cos_work_inventory.py` source: `cos_work_inventory.py L1`.
- Degree: 51.
- The node contains functions for inventory, ownership, worktrees, status,
  branches, stashes, claims, sessions, orphans, and race-risk collection.
- Affected output found no reverse impacted nodes.

### `packages/agent-service` — `BaseModel`

Command:

```bash
/tmp/graphify-venv/bin/graphify explain 'BaseModel' --graph /tmp/cos-graphify-phase-b-20260522/packages__agent-service/graphify-out/graph.json
/tmp/graphify-venv/bin/graphify affected 'BaseModel' --depth 2 --graph /tmp/cos-graphify-phase-b-20260522/packages__agent-service/graphify-out/graph.json
```

Observed:

- `BaseModel` has degree 36 in the agent-service graph.
- Direct inheritors include `SessionEvent`, `SessionDetails`, `StoredSession`,
  `SessionStoreSnapshot`, `SessionSummary`, `SessionLatestEvent`, response models,
  query request/response models, and workspace models.
- Affected output identifies `StoredSession` in `src/agent_service/store.py:L33`.

## Inference — Optimization Targets

### 1. Harness event preload bundle

Use when changing canonical event schema, adapter parsing, streaming, or projection.

Preload:

- `lib/harness_adapter/base.py`
- `lib/harness_adapter/codex.py`
- `lib/harness_adapter/aider.py`
- `lib/harness_adapter/aider_streaming.py`
- `lib/harness_adapter/bare_cli.py`
- `lib/harness_adapter/dispatch.py`
- `lib/sprint_orchestrator.py`

Confirm with:

```bash
.venv/bin/python -m pytest tests/unit/test_harness_adapter_base.py tests/unit/test_sprint_orchestrator.py tests/integration/test_preamble_v2_wave1.py -q
```

Why: `CanonicalEvent` is the strongest cross-adapter hotspot and has both import
and inferred-use edges across harness adapters.

### 2. History rewrite preload bundle

Use when touching history sanitization, filter-repo wrappers, or rewrite ledger
behavior.

Preload:

- `lib/history_sanitization.py`
- `lib/history_rewrite_ledger.py`
- `scripts/cos-history-sanitization`
- `scripts/cos-filter-repo-wrap.sh`

Confirm with:

```bash
.venv/bin/python -m pytest tests/unit/test_history_sanitization.py tests/behavior/test_history_sanitization_cli.py tests/behavior/test_history_sanitization_execute.py tests/contracts/test_history_rewrite_ledger_append_only.py -q
```

Why: Graphify shows high internal fan-out but no meaningful reverse affected nodes,
so optimization should focus on preloading its local toolchain rather than assuming
broad runtime coupling.

### 3. Destructive Git blocker preload bundle

Use when changing destructive Git policy, bypass handling, branch switching, WIP
protection, or git intervention logging.

Preload:

- `hooks/destructive-git-blocker.sh`
- `hooks/_lib/common.sh`
- `hooks/_lib/killswitch_check.sh`
- `hooks/_lib/bypass-resolver.sh`
- `hooks/_lib/governance_phase_policy.sh`
- `hooks/_lib/registration-allowlist.txt`

Confirm with:

```bash
.venv/bin/python -m pytest tests/chaos/test_reset_cascade_detector.py tests/chaos/test_safety_drill.py tests/chaos/test_multi_ide_swarm_safety.py -q
bash -n hooks/destructive-git-blocker.sh hooks/_lib/common.sh hooks/_lib/killswitch_check.sh hooks/_lib/bypass-resolver.sh hooks/_lib/governance_phase_policy.sh
```

Why: Graphify shows internal blocker fan-out but no reverse affected nodes; tests
and shell syntax are the real confidence surface.

### 4. Work inventory preload bundle

Use when changing prelaunch inventory, ownership, sessions, stashes, worktrees, or
coordination status behavior.

Preload:

- `scripts/cos_work_inventory.py`
- `scripts/cos-doctor-work-inventory.sh`
- `scripts/cos-doctor-concurrency.sh`
- `hooks/agent-prelaunch.sh`

Confirm with:

```bash
.venv/bin/python -m pytest tests/unit/test_cos_work_inventory.py tests/audit/test_cos_work_inventory_refinements.py tests/behavior/test_agent_prelaunch_read_only.py tests/red_team/portability/test_cos_work_inventory.py -q
```

Why: Graphify shows high local fan-out. Existing test coverage is broad and should
be preferred over graph inference for behavior claims.

### 5. Agent service model preload bundle

Use when changing agent-service API contracts, session persistence, session event
models, or response schemas.

Preload:

- `packages/agent-service/src/agent_service/models/session.py`
- `packages/agent-service/src/agent_service/store.py`
- `packages/agent-service/src/agent_service/models/__init__.py`
- `packages/agent-service/src/agent_service/routers/sessions.py`

Confirm with:

```bash
cd packages/agent-service && ../../.venv/bin/python -m pytest tests/test_contract.py tests/test_sessions.py tests/test_health.py -q
```

Why: `BaseModel` is a broad library-level node, but its affected output points to
`StoredSession`; target session schema/store tests first.

## Paths to Inspect Next

| Priority | Path | Reason |
|---:|---|---|
| 1 | `lib/harness_adapter/base.py` ↔ harness adapters | Strongest cross-file event contract hotspot. |
| 2 | `hooks/destructive-git-blocker.sh` ↔ hook libs | Safety-critical fan-out with chaos coverage. |
| 3 | `scripts/cos_work_inventory.py` ↔ prelaunch hook | High fan-out preflight/inventory surface. |
| 4 | `packages/agent-service/src/agent_service/models/session.py` ↔ `store.py` | API contract and persistence schema coupling. |
| 5 | `lib/history_sanitization.py` local toolchain | Large local fan-out but weak cross-runtime graph path. |

## Acceptance Criteria

1. Graphify recommended commands were executed with the installed CLI syntax.
2. Each target has preload files, inspection paths, and tests.
3. Extracted evidence is separated from maintainer inference.
4. Generic graph paths, such as enum/exception bridges, are labeled weak.
5. No implementation change is recommended without source inspection and tests.
