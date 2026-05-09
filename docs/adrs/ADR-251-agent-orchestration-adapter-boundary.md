---
adr: 251
title: Agent Orchestration Adapter Boundary
status: accepted
relationship_chain_exempt: true
date: 2026-05-08
supersedes: []
superseded_by: null
extends: [ADR-057, ADR-081, ADR-190, ADR-223, ADR-226, ADR-228, ADR-230, ADR-233, ADR-235, ADR-246, ADR-248, ADR-250]
implementation_files:
  - manifests/agent-orchestration-adapters.yaml
  - scripts/agent-orchestration-boundary-audit.py
  - scripts/agent-orchestration-benchmark.py
  - tests/unit/test_agent_orchestration_boundary_audit.py
  - tests/unit/test_agent_orchestration_benchmark.py
tier: maintainer
tags: [orchestration, adapters, multi-agent, cross-harness, governance, anti-reinvention, benchmark]
---

<!-- ADR_RELATION_CHAIN_EXEMPT: part of the 2026-05-08 implementation-ledger ADR burst; relationship depth is tracked by control-plane audits rather than new transitive ADR scope. -->

# ADR-251: Agent Orchestration Adapter Boundary

## Status

Accepted — Slice A implemented.

## Context

The operator raised the same concern for multi-agent orchestration that ADR-250
raised for skill routing: COS has accumulated local primitives for agent
lifecycle, handoff, dispatch, release freeze, worktree ownership, file-IPC,
background daemons, and cross-harness projection. The risk is not that these
primitives are useless. The risk is that COS slowly grows into a bespoke
orchestration framework while the ecosystem already has mature agent
orchestration concepts.

The recent dogfood incidents prove that this boundary matters:

- agents committed on a different branch than the operator expected;
- auto-stash lifecycle hid WIP and created ghosts;
- concurrent agents wrote while release/history operations were being prepared;
- handoff and receiver failures needed receipts/idempotency rather than verbal
  success claims;
- multiple harnesses and IDEs can launch agents, each with different native
  semantics.

Repo-local prior art already exists but was spread across multiple ADRs:

- ADR-057/081 define cross-harness projection and Codex adaptation;
- ADR-190 records harness action receipts;
- ADR-223 reconstructs agent lifecycle around worktree-per-write-agent;
- ADR-226 defines event-sourced session state;
- ADR-228 defines retry, budget, circuit-breaker, and dispatch gates;
- ADR-230 defines handoff envelopes and cycle deduplication;
- ADR-233 defines file-IPC for cross-session teams;
- ADR-235 defines the detached daemon path;
- ADR-246 defines release freeze;
- ADR-248 defines the control-plane audit loop.

External prior art confirms that multi-agent orchestration is a mature category,
not a blank sheet:

- OpenAI Agents SDK documents agents, handoffs, guardrails, sessions, tracing,
  and multi-agent orchestration.
- LangGraph/LangChain documents graph/state based multi-agent supervisors and
  handoffs.
- AutoGen documents multi-agent conversations and group chat orchestration.
- CrewAI documents crews, tasks, flows, and process orchestration.

The correct posture is therefore similar to ADR-250:

> COS owns governance and control-plane semantics. External orchestration
> frameworks are adapter candidates, not the source of truth for safety,
> ownership, release freeze, receipts, budgets, or telemetry.

## Decision

Define an explicit agent-orchestration adapter boundary.

COS owns these semantics:

1. policy and safety gates;
2. work ownership, liveness, and branch/worktree boundaries;
3. release freeze and destructive-operation preconditions;
4. evidence receipts and event-log state;
5. budget, retry, circuit-breaker, and idempotency contracts;
6. telemetry, remediation queues, and postmortem regression findings;
7. cross-harness normalization.

Orchestration engines are adapters. They may schedule, graph, coordinate, or run
agents, but they do not get to bypass COS governance semantics.

Introduce:

```text
manifests/agent-orchestration-adapters.yaml
scripts/agent-orchestration-boundary-audit.py
scripts/agent-orchestration-benchmark.py
```

Hard rules:

1. Core COS hot-path orchestration files must not import optional orchestration
   frameworks directly (`langgraph`, `autogen`, `crewai`, OpenAI Agents SDK,
   Semantic Kernel, etc.). Use declared adapters instead.
2. Any new lifecycle, handoff, queue, daemon, dispatch, retry, budget, session,
   or worker primitive must be declared in the manifest as a core surface or
   adapter implementation.
3. Agent launch paths must pass through ADR-223 lifecycle and ADR-246 release
   freeze boundaries.
4. Handoff paths must use ADR-230 envelopes and receipts; external handoff
   frameworks must map into that envelope.
5. Provider/model calls must pass through ADR-228 dispatch gate for budget,
   retry, circuit breaker, and optional sandbox checks.
6. Benchmarks must encode historical failure modes so an adapter can prove it
   preserves behavior before it becomes default.

## Adapter posture

| Adapter | Default | Status | Rationale |
|---|---:|---|---|
| `cos_file_ipc_minimal` | yes | active | Zero extra dependency local-first substrate for session teams and receipts |
| `cos_handoff_envelope` | no | active | First-party typed handoff contract and cycle dedup |
| `cos_dispatch_gate` | no | active | First-party budget/retry/circuit-breaker/idempotency boundary |
| `cos_detached_daemon` | no | opt-in | Local tmux/file-sentinel daemon for detached work |
| `openai_agents_sdk` | no | candidate | Mature agent/handoff/session/tracing concepts; adapter only |
| `langgraph` | no | candidate | Mature state graph/supervisor patterns; adapter only |
| `autogen` | no | lab | Mature group chat/multi-agent patterns; heavy optional lab only |
| `crewai` | no | lab | Crew/task/flow orchestration; heavy optional lab only |

## Benchmark doctrine

The ADR-251 benchmark is intentionally incident-shaped. It is not a generic
unit-test index. It checks that the repo contains executable proof for the
failure modes that hurt us:

- write-agent lifecycle uses worktrees and does not depend on auto-stash;
- branch/worktree divergence is audited before launch;
- handoff cycles are detected;
- receiver death mid-dispatch creates a failure receipt;
- provider dispatch can refuse before provider calls when budget or sandbox
  preconditions fail;
- file-IPC can move tasks/messages across sessions;
- release freeze blocks active agent claims before destructive operations.

Known gaps are allowed only if declared as warnings. Required fixtures block.

## Consequences

Positive:

- Prevents COS from silently becoming a bespoke competitor to LangGraph,
  AutoGen, CrewAI, or provider-native agent frameworks.
- Keeps governance semantics stable while allowing orchestration engines to be
  evaluated/adopted as adapters.
- Extends the ADR-250 pattern from router retrieval to multi-agent runtime
  orchestration.
- Adds a concrete audit and benchmark before more orchestration substrate is
  added.

Negative:

- Adds another manifest/audit/benchmark surface.
- Static audits cannot prove that all runtime launch paths are perfectly wired;
  chaos/cross-harness tests remain necessary.
- Optional framework adapters remain future work until they satisfy license,
  footprint, benchmark, and governance-boundary requirements.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Replace COS orchestration with LangGraph/AutoGen/CrewAI/OpenAI Agents SDK immediately | Violates footprint discipline, weakens local-first/cross-harness portability, and delegates COS-specific safety semantics to generic orchestration frameworks. |
| Keep building first-party orchestration primitives without an adapter boundary | Repeats the reinvention pattern that triggered ADR-250 and makes future adoption harder. |
| Treat every harness native agent runner as authoritative | Reintroduces divergent behavior across Claude Code, Codex, OpenCode, IDE agents, cloud agents, and service-mode workers. |
| Use prompts alone to enforce orchestration policy | The recent branch/stash/freeze incidents show that filesystem/worktree/process boundaries and audits are required; prompt statements are not enough. |

## Verification

```bash
python3 scripts/agent-orchestration-boundary-audit.py --json
python3 scripts/agent-orchestration-benchmark.py --json
python3 -m pytest tests/unit/test_agent_orchestration_boundary_audit.py tests/unit/test_agent_orchestration_benchmark.py -q
scripts/cos-control-plane-audit --lane hook-fast --json
```

Expected current result: the boundary audit passes, the benchmark has zero
required failures, and hook-fast includes the orchestration boundary audit
without findings.
