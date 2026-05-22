# Graphify Phase C Hotspot and Impact Report

## Scope

Source summary: `/private/tmp/cos-graphify-phase-b-20260522/cos-graphify-slices-summary.json`

This report reads Graphify slice graphs from Phase B and separates extracted graph evidence from maintainer inference. It is a context-selection report, not a correctness proof.

## Slice Overview

| Slice | Status | Duration seconds | Nodes | Edges | Graph |
|---|---|---|---|---|---|
| lib | 0 | 15.203 | 7956 | 12984 | /private/tmp/cos-graphify-phase-b-20260522/lib/graphify-out/graph.json |
| hooks | 0 | 2.286 | 753 | 619 | /private/tmp/cos-graphify-phase-b-20260522/hooks/graphify-out/graph.json |
| scripts | 0 | 8.232 | 4112 | 7254 | /private/tmp/cos-graphify-phase-b-20260522/scripts/graphify-out/graph.json |
| skills | skipped-empty | 1.27 | n/a | n/a | /private/tmp/cos-graphify-phase-b-20260522/skills/graphify-out/graph.json |
| rules | skipped-empty | 0.756 | n/a | n/a | /private/tmp/cos-graphify-phase-b-20260522/rules/graphify-out/graph.json |
| packages/agent-service | 0 | 1.526 | 201 | 343 | /private/tmp/cos-graphify-phase-b-20260522/packages__agent-service/graphify-out/graph.json |

## Context Optimization Candidates

| Slice | First candidate | Inference |
|---|---|---|
| lib | harness_adapter/base.py | Start with `history_sanitization.py` and confirm with source/tests. |
| hooks | agent-working-dir-inject.sh | Start with `destructive-git-blocker.sh` and confirm with source/tests. |
| scripts | primitive-behavior-audit.py | Start with `cos_work_inventory.py` and confirm with source/tests. |
| skills | semantic Phase D | No code graph in code-only mode; needs explicit semantic budget approval. |
| rules | semantic Phase D | No code graph in code-only mode; needs explicit semantic budget approval. |
| packages/agent-service | src/agent_service/models/session.py | Start with `BaseModel` and confirm with source/tests. |

## Slice `lib`

### Extracted Evidence

Graph: `/private/tmp/cos-graphify-phase-b-20260522/lib/graphify-out/graph.json`
Built-at commit: `9621d8eab85fe1d95bdd28b3dfc932ddfbf6758a`
Nodes: 7956
Edges: 12984

Top relation counts:

| Relation | Edges |
|---|---|
| calls | 4892 |
| contains | 3276 |
| rationale_for | 2949 |
| method | 1349 |
| uses | 281 |
| inherits | 117 |
| imports | 81 |
| imports_from | 34 |

Confidence counts:

| Confidence | Edges |
|---|---|
| EXTRACTED | 12478 |
| INFERRED | 506 |

### Hotspots by Degree

| Node | File | Location | In | Out | Total | Community |
|---|---|---|---|---|---|---|
| history_sanitization.py | history_sanitization.py | L1 | 1 | 49 | 50 | 59 |
| claude_executor.py | claude_executor.py | L1 | 21 | 24 | 45 | 64 |
| Enum | <unknown> |  | 44 | 0 | 44 | 155 |
| CanonicalEvent | harness_adapter/base.py | L49 | 40 | 3 | 43 | 21 |
| engram_lifecycle.py | engram_lifecycle.py | L1 | 9 | 32 | 41 | 16 |
| rate_limiter.py | rate_limiter.py | L1 | 1 | 39 | 40 | 82 |
| prelaunch_audit.py | prelaunch_audit.py | L1 | 1 | 39 | 40 | 20 |
| skill_router.py | skill_router.py | L1 | 2 | 37 | 39 | 112 |

### Cross-File Dependency Surfaces

| File | Nodes | Internal edges | Incoming cross-file | Outgoing cross-file | Total cross-file |
|---|---|---|---|---|---|
| harness_adapter/base.py | 56 | 72 | 158 | 9 | 167 |
| <unknown> | 12 | 0 | 127 | 0 | 127 |
| claude_executor.py | 43 | 60 | 27 | 22 | 49 |
| harness_adapter/codex.py | 24 | 61 | 7 | 34 | 41 |
| learning_pipeline.py | 25 | 39 | 2 | 32 | 34 |
| dispatch_gate.py | 20 | 29 | 9 | 25 | 34 |
| harness_adapter/aider.py | 17 | 23 | 6 | 28 | 34 |
| metric_event.py | 15 | 19 | 33 | 1 | 34 |

### Recommended Graphify Commands

| Use | Target | Command |
|---|---|---|
| explain | history_sanitization.py | graphify explain 'history_sanitization.py' --graph '/private/tmp/cos-graphify-phase-b-20260522/lib/graphify-out/graph.json' |
| affected | history_sanitization.py | graphify affected 'history_sanitization.py' --depth 2 --graph '/private/tmp/cos-graphify-phase-b-20260522/lib/graphify-out/graph.json' |
| explain | claude_executor.py | graphify explain 'claude_executor.py' --graph '/private/tmp/cos-graphify-phase-b-20260522/lib/graphify-out/graph.json' |
| affected | claude_executor.py | graphify affected 'claude_executor.py' --depth 2 --graph '/private/tmp/cos-graphify-phase-b-20260522/lib/graphify-out/graph.json' |
| explain | CanonicalEvent | graphify explain 'CanonicalEvent' --graph '/private/tmp/cos-graphify-phase-b-20260522/lib/graphify-out/graph.json' |
| affected | CanonicalEvent | graphify affected 'CanonicalEvent' --depth 2 --graph '/private/tmp/cos-graphify-phase-b-20260522/lib/graphify-out/graph.json' |
| path | history_sanitization.py → claude_executor.py | graphify path 'history_sanitization.py' 'claude_executor.py' --graph '/private/tmp/cos-graphify-phase-b-20260522/lib/graphify-out/graph.json' |

### Inference

`harness_adapter/base.py` is the first context-optimization candidate for this slice because it has the highest observed cross-file edge count (167).
`history_sanitization.py` is the first symbol-centered inspection candidate because it has the highest observed total degree (50).
These are navigation candidates only. Confirm any optimization with source inspection and tests before changing behavior.

## Slice `hooks`

### Extracted Evidence

Graph: `/private/tmp/cos-graphify-phase-b-20260522/hooks/graphify-out/graph.json`
Built-at commit: `9621d8eab85fe1d95bdd28b3dfc932ddfbf6758a`
Nodes: 753
Edges: 619

Top relation counts:

| Relation | Edges |
|---|---|
| defines | 249 |
| calls | 203 |
| contains | 149 |
| rationale_for | 18 |

Confidence counts:

| Confidence | Edges |
|---|---|
| EXTRACTED | 619 |

### Hotspots by Degree

| Node | File | Location | In | Out | Total | Community |
|---|---|---|---|---|---|---|
| destructive-git-blocker.sh | destructive-git-blocker.sh | L1 | 0 | 23 | 23 | 0 |
| remediation.sh | _lib/remediation.sh | L1 | 0 | 15 | 15 | 4 |
| execute-repair.sh | _lib/execute-repair.sh | L1 | 0 | 15 | 15 | 3 |
| stash-lock.sh | _lib/stash-lock.sh | L1 | 0 | 13 | 13 | 5 |
| circuit-breaker.sh | _lib/circuit-breaker.sh | L1 | 0 | 11 | 11 | 7 |
| bash-hot-path-dispatcher.sh | bash-hot-path-dispatcher.sh | L1 | 0 | 10 | 10 | 8 |
| build_recap_context() | _lib/recap_adapter.py | L184 | 3 | 6 | 9 | 1 |
| task_bridge.py | _lib/task_bridge.py | L1 | 0 | 9 | 9 | 6 |

### Cross-File Dependency Surfaces

| File | Nodes | Internal edges | Incoming cross-file | Outgoing cross-file | Total cross-file |
|---|---|---|---|---|---|
| agent-working-dir-inject.sh | 9 | 8 | 0 | 2 | 2 |
| _lib/portable.sh | 8 | 7 | 2 | 0 | 2 |
| destructive-git-blocker.sh | 24 | 25 | 0 | 0 | 0 |
| _lib/recap_adapter.py | 18 | 26 | 0 | 0 | 0 |
| _lib/execute-repair.sh | 16 | 25 | 0 | 0 | 0 |
| _lib/remediation.sh | 16 | 21 | 0 | 0 | 0 |
| _lib/stash-lock.sh | 14 | 22 | 0 | 0 | 0 |
| _lib/task_bridge.py | 13 | 24 | 0 | 0 | 0 |

### Recommended Graphify Commands

| Use | Target | Command |
|---|---|---|
| explain | destructive-git-blocker.sh | graphify explain 'destructive-git-blocker.sh' --graph '/private/tmp/cos-graphify-phase-b-20260522/hooks/graphify-out/graph.json' |
| affected | destructive-git-blocker.sh | graphify affected 'destructive-git-blocker.sh' --depth 2 --graph '/private/tmp/cos-graphify-phase-b-20260522/hooks/graphify-out/graph.json' |
| explain | remediation.sh | graphify explain 'remediation.sh' --graph '/private/tmp/cos-graphify-phase-b-20260522/hooks/graphify-out/graph.json' |
| affected | remediation.sh | graphify affected 'remediation.sh' --depth 2 --graph '/private/tmp/cos-graphify-phase-b-20260522/hooks/graphify-out/graph.json' |
| explain | execute-repair.sh | graphify explain 'execute-repair.sh' --graph '/private/tmp/cos-graphify-phase-b-20260522/hooks/graphify-out/graph.json' |
| affected | execute-repair.sh | graphify affected 'execute-repair.sh' --depth 2 --graph '/private/tmp/cos-graphify-phase-b-20260522/hooks/graphify-out/graph.json' |
| path | destructive-git-blocker.sh → remediation.sh | graphify path 'destructive-git-blocker.sh' 'remediation.sh' --graph '/private/tmp/cos-graphify-phase-b-20260522/hooks/graphify-out/graph.json' |

### Inference

`agent-working-dir-inject.sh` is the first context-optimization candidate for this slice because it has the highest observed cross-file edge count (2).
`destructive-git-blocker.sh` is the first symbol-centered inspection candidate because it has the highest observed total degree (23).
These are navigation candidates only. Confirm any optimization with source inspection and tests before changing behavior.

## Slice `scripts`

### Extracted Evidence

Graph: `/private/tmp/cos-graphify-phase-b-20260522/scripts/graphify-out/graph.json`
Built-at commit: `9621d8eab85fe1d95bdd28b3dfc932ddfbf6758a`
Nodes: 4112
Edges: 7254

Top relation counts:

| Relation | Edges |
|---|---|
| calls | 3570 |
| contains | 2636 |
| rationale_for | 513 |
| defines | 469 |
| method | 59 |
| inherits | 4 |
| imports | 3 |

Confidence counts:

| Confidence | Edges |
|---|---|
| EXTRACTED | 7177 |
| INFERRED | 77 |

### Hotspots by Degree

| Node | File | Location | In | Out | Total | Community |
|---|---|---|---|---|---|---|
| cos_work_inventory.py | cos_work_inventory.py | L1 | 0 | 51 | 51 | 22 |
| acc_pipeline.py | acc_pipeline.py | L1 | 0 | 44 | 44 | 5 |
| cos-ci-local.sh | cos-ci-local.sh | L1 | 0 | 37 | 37 | 29 |
| read_text() | primitive-behavior-audit.py | L87 | 33 | 0 | 33 | 48 |
| state_retention_audit.py | state_retention_audit.py | L1 | 0 | 33 | 33 | 19 |
| security_red_team.py | security_red_team.py | L1 | 0 | 33 | 33 | 10 |
| english_only_content_audit.py | english_only_content_audit.py | L1 | 0 | 33 | 33 | 3 |
| primitive_harness_coverage.py | primitive_harness_coverage.py | L1 | 0 | 32 | 32 | 21 |

### Cross-File Dependency Surfaces

| File | Nodes | Internal edges | Incoming cross-file | Outgoing cross-file | Total cross-file |
|---|---|---|---|---|---|
| primitive-behavior-audit.py | 13 | 27 | 30 | 14 | 44 |
| cos_task_claims.py | 33 | 77 | 23 | 9 | 32 |
| cos_worktree_sweeper.py | 18 | 23 | 21 | 0 | 21 |
| cos-worktree-sweeper.sh | 1 | 0 | 0 | 18 | 18 |
| primitive_row_audit.py | 17 | 40 | 2 | 15 | 17 |
| claim_task.py | 8 | 14 | 3 | 13 | 16 |
| claim_enforcer.py | 10 | 17 | 9 | 6 | 15 |
| agentic_tool_license_matrix.py | 16 | 14 | 14 | 0 | 14 |

### Recommended Graphify Commands

| Use | Target | Command |
|---|---|---|
| explain | cos_work_inventory.py | graphify explain 'cos_work_inventory.py' --graph '/private/tmp/cos-graphify-phase-b-20260522/scripts/graphify-out/graph.json' |
| affected | cos_work_inventory.py | graphify affected 'cos_work_inventory.py' --depth 2 --graph '/private/tmp/cos-graphify-phase-b-20260522/scripts/graphify-out/graph.json' |
| explain | acc_pipeline.py | graphify explain 'acc_pipeline.py' --graph '/private/tmp/cos-graphify-phase-b-20260522/scripts/graphify-out/graph.json' |
| affected | acc_pipeline.py | graphify affected 'acc_pipeline.py' --depth 2 --graph '/private/tmp/cos-graphify-phase-b-20260522/scripts/graphify-out/graph.json' |
| explain | cos-ci-local.sh | graphify explain 'cos-ci-local.sh' --graph '/private/tmp/cos-graphify-phase-b-20260522/scripts/graphify-out/graph.json' |
| affected | cos-ci-local.sh | graphify affected 'cos-ci-local.sh' --depth 2 --graph '/private/tmp/cos-graphify-phase-b-20260522/scripts/graphify-out/graph.json' |
| path | cos_work_inventory.py → acc_pipeline.py | graphify path 'cos_work_inventory.py' 'acc_pipeline.py' --graph '/private/tmp/cos-graphify-phase-b-20260522/scripts/graphify-out/graph.json' |

### Inference

`primitive-behavior-audit.py` is the first context-optimization candidate for this slice because it has the highest observed cross-file edge count (44).
`cos_work_inventory.py` is the first symbol-centered inspection candidate because it has the highest observed total degree (51).
These are navigation candidates only. Confirm any optimization with source inspection and tests before changing behavior.

## Slice `skills`

### Extracted Evidence

This slice produced no code graph in code-only mode and was recorded as `skipped-empty`.

### Inference

This is expected for Markdown-heavy governance/procedure surfaces. Evaluate this slice in Phase D only after semantic extraction budget approval.

## Slice `rules`

### Extracted Evidence

This slice produced no code graph in code-only mode and was recorded as `skipped-empty`.

### Inference

This is expected for Markdown-heavy governance/procedure surfaces. Evaluate this slice in Phase D only after semantic extraction budget approval.

## Slice `packages/agent-service`

### Extracted Evidence

Graph: `/private/tmp/cos-graphify-phase-b-20260522/packages__agent-service/graphify-out/graph.json`
Built-at commit: `9621d8eab85fe1d95bdd28b3dfc932ddfbf6758a`
Nodes: 201
Edges: 343

Top relation counts:

| Relation | Edges |
|---|---|
| contains | 120 |
| calls | 102 |
| rationale_for | 43 |
| inherits | 39 |
| uses | 25 |
| method | 14 |

Confidence counts:

| Confidence | Edges |
|---|---|
| EXTRACTED | 276 |
| INFERRED | 67 |

### Hotspots by Degree

| Node | File | Location | In | Out | Total | Community |
|---|---|---|---|---|---|---|
| BaseModel | <unknown> |  | 36 | 0 | 36 | 3 |
| JsonSessionStore | src/agent_service/store.py | L52 | 3 | 19 | 22 | 1 |
| session.py | src/agent_service/models/session.py | L1 | 1 | 19 | 20 | 3 |
| sessions.py | src/agent_service/routers/sessions.py | L1 | 1 | 16 | 17 | 4 |
| SessionEvent | src/agent_service/models/session.py | L76 | 11 | 3 | 14 | 1 |
| ._read() | src/agent_service/store.py | L204 | 10 | 2 | 12 | 1 |
| SessionDetails | src/agent_service/models/session.py | L66 | 8 | 3 | 11 | 1 |
| _store() | src/agent_service/routers/sessions.py | L44 | 10 | 0 | 10 | 4 |

### Cross-File Dependency Surfaces

| File | Nodes | Internal edges | Incoming cross-file | Outgoing cross-file | Total cross-file |
|---|---|---|---|---|---|
| src/agent_service/models/session.py | 21 | 20 | 37 | 23 | 60 |
| <unknown> | 4 | 0 | 41 | 0 | 41 |
| src/agent_service/store.py | 27 | 54 | 1 | 38 | 39 |
| src/agent_service/routers/sessions.py | 16 | 29 | 4 | 10 | 14 |
| src/agent_service/sse.py | 11 | 12 | 10 | 0 | 10 |
| src/agent_service/models/health.py | 7 | 6 | 4 | 4 | 8 |
| src/agent_service/app.py | 4 | 3 | 5 | 3 | 8 |
| src/agent_service/models/query.py | 7 | 6 | 2 | 5 | 7 |

### Recommended Graphify Commands

| Use | Target | Command |
|---|---|---|
| explain | JsonSessionStore | graphify explain 'JsonSessionStore' --graph '/private/tmp/cos-graphify-phase-b-20260522/packages__agent-service/graphify-out/graph.json' |
| affected | JsonSessionStore | graphify affected 'JsonSessionStore' --depth 2 --graph '/private/tmp/cos-graphify-phase-b-20260522/packages__agent-service/graphify-out/graph.json' |
| explain | session.py | graphify explain 'session.py' --graph '/private/tmp/cos-graphify-phase-b-20260522/packages__agent-service/graphify-out/graph.json' |
| affected | session.py | graphify affected 'session.py' --depth 2 --graph '/private/tmp/cos-graphify-phase-b-20260522/packages__agent-service/graphify-out/graph.json' |
| explain | sessions.py | graphify explain 'sessions.py' --graph '/private/tmp/cos-graphify-phase-b-20260522/packages__agent-service/graphify-out/graph.json' |
| affected | sessions.py | graphify affected 'sessions.py' --depth 2 --graph '/private/tmp/cos-graphify-phase-b-20260522/packages__agent-service/graphify-out/graph.json' |
| path | JsonSessionStore → session.py | graphify path 'JsonSessionStore' 'session.py' --graph '/private/tmp/cos-graphify-phase-b-20260522/packages__agent-service/graphify-out/graph.json' |

### Inference

`src/agent_service/models/session.py` is the first context-optimization candidate for this slice because it has the highest observed cross-file edge count (60).
`BaseModel` is the first symbol-centered inspection candidate because it has the highest observed total degree (36).
These are navigation candidates only. Confirm any optimization with source inspection and tests before changing behavior.

## Acceptance Criteria

1. Hotspots are computed from graph node degree and listed per slice.
2. Incoming/outgoing cross-file dependency surfaces are listed per slice.
3. Context optimization candidates are labeled as inference, not proof.
4. Recommended `graphify explain`, `graphify affected`, and `graphify path` commands are emitted for built slices.
5. Skipped governance/procedure slices are routed to Phase D semantic extraction instead of treated as Phase B failures.
