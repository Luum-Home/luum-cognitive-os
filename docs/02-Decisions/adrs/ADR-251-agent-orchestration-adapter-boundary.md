---

adr: 251
title: Agent Orchestration Adapter Boundary
status: accepted
implementation_status: implemented
classification_basis: 'boundary manifest, audit, benchmark fixtures, and tests implement the orchestration adapter boundary scope'
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

## Operational Guide

### What changes for the operator

Before this ADR, COS had accumulated first-party primitives for agent lifecycle,
handoff, dispatch, release freeze, worktree ownership, file-IPC, and background
daemons across multiple ADRs (ADR-057, 081, 190, 223, 226, 228, 230, 233, 235,
246, 248) with no single boundary declaration. Community orchestration frameworks
(LangGraph, AutoGen, CrewAI, OpenAI Agents SDK) could only be considered by
importing them directly into COS core — mixing governance policy with optional
dependency.

After this ADR:

- COS owns: policy/safety gates, work ownership, branch/worktree boundaries,
  release freeze preconditions, evidence receipts, budget/retry/circuit-breaker,
  telemetry, remediation queues, cross-harness normalization.
- External orchestration engines (LangGraph, AutoGen, CrewAI, OpenAI Agents SDK)
  are **adapter candidates only**. They schedule and coordinate; they do not
  bypass COS governance.
- Core COS hot-path files must NOT import optional orchestration frameworks
  directly (`langgraph`, `autogen`, `crewai`, etc.). Declared adapters in
  `manifests/agent-orchestration-adapters.yaml` are the only permitted path.
- Any new lifecycle, handoff, queue, daemon, dispatch, or worker primitive
  must be declared in the manifest as a core surface or adapter.

### What this answers (and what it doesn't)

**Answers:**
- "Can I use LangGraph to coordinate agents?" — Yes, as a declared adapter with
  `status: candidate`. The adapter must prove it maps handoffs into ADR-230
  envelopes and passes the ADR-251 benchmark.
- "How do I know if the boundary is respected?" — Run
  `python3 scripts/agent-orchestration-boundary-audit.py --json`. It checks
  that core hot-path files do not import undeclared frameworks.
- "What failure modes must an adapter prove before it becomes default?" — See
  §Benchmark doctrine: write-agent lifecycle, branch divergence, handoff cycle
  detection, receiver-death receipt, budget refusal before provider calls,
  file-IPC cross-session, release freeze blocking.

**Does not answer:**
- Whether the currently active adapters (`cos_file_ipc_minimal`,
  `cos_handoff_envelope`, `cos_dispatch_gate`) are free of race conditions.
  That requires chaos/cross-harness tests beyond the static boundary audit.
- Whether a candidate adapter satisfies the license and footprint requirements
  without checking `manifests/agent-orchestration-adapters.yaml`.

### Daily operational pattern

1. Verify the orchestration boundary on any change to agent launch or handoff paths:
   ```bash
   python3 scripts/agent-orchestration-boundary-audit.py --json
   python3 scripts/agent-orchestration-benchmark.py --json
   ```
2. To propose a new orchestration engine as an adapter:
   - Add an entry to `manifests/agent-orchestration-adapters.yaml` with
     `status: candidate` and the full declaration fields.
   - Write benchmark fixtures that cover the incident-shaped failure modes in §Benchmark doctrine.
   - Keep core COS imports unchanged until the adapter satisfies license,
     footprint, benchmark, and governance boundary review.
3. Full verification:
   ```bash
   python3 -m pytest tests/unit/test_agent_orchestration_boundary_audit.py tests/unit/test_agent_orchestration_benchmark.py -q
   scripts/cos-control-plane-audit --lane hook-fast --json
   ```

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
