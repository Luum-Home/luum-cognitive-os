# ADR-091: Headless and Clustered Runtime Direction

<!-- Renumbered-from: ADR-027 (docs/architecture/adrs/027-headless-clustered-runtime-direction.md) -->
<!-- Renumbered-to: ADR-091 (ADR-087 migration, 2026-04-30) -->
<!-- Note: ADR-027 in docs/adrs/ is a different decision (SO Slimming — Test Strategy). -->

- **Status**: Accepted as direction, not yet implemented as a production cluster
- **Date**: 2026-04-28
- **Decision owner**: Cognitive OS maintainers
- **Related**:
  - `docs/business/durable-product-master-plan.md`
  - `docs/architecture/bootstrap-portability.md`
  - `docs/architecture/capability-centric-runtime-enforcement.md`
  - `docs/architecture/runtime-hardcoding-discipline.md`
  - `.cognitive-os/plans/architecture/headless-clustered-runtime-plan.md`

## Status

Accepted.

## Relationship to ADR-084

ADR-091 supersedes ADR-084 for the headless and clustered runtime contract. ADR-084 remains useful as historical design input, but its three-mode taxonomy is not canonical. The accepted taxonomy is two runtime modes: local harness runtime and headless runtime. Clustered/Kubernetes operation is a future deployment surface under headless runtime and must not be claimed until the requirements in this ADR are implemented and verified.

## Context

Cognitive OS started as a local operating layer for AI coding agents, with
lifecycle hooks, rules, skills, memory, metrics, and driver projections for
harnesses such as Claude Code and Codex. That local mode remains valuable, but
it should not be the final architectural boundary.

The durable product direction is broader:

> Cognitive OS can run locally as a developer assistant, or headlessly as an
> operational runtime for AI engineering workers.

This means the same governance, verification, portability, and memory contracts
that help local coding agents should eventually govern AI workers running in CI,
VMs, containers, Kubernetes pods, and clustered repair/build systems.


The solo maintainer swarm persona from ADR-124/ADR-125 strengthens this
direction. A single operator may deliberately run Cognitive OS on cloud VMs or
containers so work can continue when the laptop/IDE is closed, fan out across
projects, or isolate long-running agents from local interactive sessions. In
that mode the SO is no longer just an IDE enhancement; it is an unattended
runtime boundary. The same primitives that feel heavy for a one-session laptop
workflow become required controls for cloud execution: leases, idempotency,
protected landing, symmetric WIP recovery, eventing, audit trails, repair-first
blocks, and explicit human-approval gates for publication.

## Decision

Cognitive OS will evolve toward a portable engineering-agent runtime with two
explicit modes:

1. **Local harness runtime** — the current mode, driven by local tool harnesses
   such as Codex, Claude Code, OpenCode, Cursor, Windsurf, and similar hosts.
2. **Headless runtime** — a future mode where Cognitive OS runs without an
   interactive developer harness and can accept tasks from queues, CI, tickets,
   bug reports, or product-building workflows.

The headless direction is accepted, but Cognitive OS must not claim to be
cluster-ready until the required runtime surfaces are implemented and tested.

## Scope

The target deployment surfaces are:

- laptop / developer workstation;
- EC2 or another VM;
- container;
- Kubernetes pod;
- clustered worker pool;
- CI/CD pipeline;
- automatic bug-repair system;
- feature/product factory;
- solo-maintainer cloud worker that continues governed tasks without an
  interactive IDE attached.

## Current Enablers

The repository already contains pieces that support this direction:

- lifecycle hooks;
- Engram-backed memory and local fallback evidence;
- JSONL metrics;
- task and session state;
- queues and rate limiting;
- repair loops;
- dispatcher and provider layer;
- doctor scripts;
- install/update flows;
- self-hosting tests;
- increasing separation between `.cognitive-os/` runtime state and driver
  projections such as `.claude/` and `.codex/`.

These are necessary foundations, but they are not sufficient to claim a
clustered runtime.

## Target Flow

```mermaid
flowchart TD
  A["Bug report / ticket / failing test"] --> B["Cognitive OS Runtime"]
  B --> C["Planner / Router"]
  C --> D["Worker pod / EC2 agent"]
  D --> E["Sandboxed repo checkout"]
  E --> F["Patch + tests"]
  F --> G["Quality gates"]
  G --> H["PR / patch / auto-fix"]
  B --> I["Memory / traces / metrics"]
```

## Requirements Before Cluster-Ready Claims

Cognitive OS must implement and verify the following before using language such
as "Kubernetes-native autonomous repair cluster".

### Runtime Server / Worker Mode

Required commands or equivalents:

- `cos worker`
- `cos run-task`
- `cos repair`
- `cos queue-drain`

### Shared State

The runtime must support durable state outside a single local filesystem:

- Valkey for queue/cache use cases;
- Postgres or SQLite for durable coordination state;
- object storage or artifact storage for patches, logs, and test outputs;
- explicit degradation rules when a shared dependency is absent.

### Workspace Isolation

Each bug, ticket, or feature must run in an isolated workspace:

- git worktree;
- container workspace;
- ephemeral volume;
- rollback path with audit evidence.


### Unattended Solo-Cloud Controls

A headless single-node VM used by one operator must still satisfy team-scale
coordination controls because the missing human-in-the-loop increases blast
radius:

- task leasing and heartbeat even when there is only one worker;
- crash-safe resume with idempotent task outcomes;
- explicit ownership of branch/worktree/stash/session artifacts;
- no direct publication to `main` from unattended workers;
- human approval or protected merge queue before pushing public results;
- persistent artifacts for every task, including prompts, commands, diffs, test
  summaries, and failure taxonomy;
- remote kill switch / safe mode that can stop new task admission without
  destroying in-flight evidence.

### Queue and Scheduler

Headless execution must include:

- task admission;
- worker leasing;
- retry/backoff;
- dead-letter queue;
- cost/model/capability limits;
- idempotent recovery after worker crash.

### Provider and Capability Routing

The runtime must remain capability-centric:

- task asks for execution profile/capabilities;
- provider/model selection happens behind adapters;
- no local harness or vendor is the implicit center.

### Security Model

Required controls:

- per-task permissions;
- filesystem/network isolation;
- secrets only via environment or secret manager;
- audit trail for every privileged action;
- policy checks before patch publication.

### Observability

The runtime must expose:

- traces;
- quality gates;
- outcome metrics;
- repair success rate;
- cost and latency metrics;
- failure taxonomy.

### Kubernetes Packaging

Before claiming Kubernetes readiness, provide:

- worker deployment manifests or Helm chart;
- scheduler/queue deployment;
- shared-service configuration;
- ConfigMap/Secret boundaries;
- readiness/liveness checks;
- scale-up/down behavior tests.

## Non-Goals For Now

- Cognitive OS is not yet a production Kubernetes-native autonomous repair
  cluster.
- Cognitive OS is not yet a fully unattended cloud operator until Phase 1/2
  crash recovery, lease, safe-mode, artifact, and publication gates are proven.
  UI/control-plane service mandatory for local default use.
- Cognitive OS should not move non-core subsystems into central runtime paths
  merely because they are useful in the future clustered architecture.

## Product Positioning

Approved positioning:

> Cognitive OS is evolving from a local agent operating layer into a portable
> engineering runtime that can run on developer machines, CI, VMs, and eventually
> clustered worker environments.

Future promise:

> The same operational contracts that govern local coding agents should also
> govern headless repair workers and product-building agents in cloud
> infrastructure.

Disallowed until implemented and tested:

> Cognitive OS is a Kubernetes-native autonomous repair cluster.

## Alternatives rejected

- Keep the previous behavior unchanged — rejected because the audit or runtime failure would remain deterministic and would continue masking real regressions.

## Consequences

### Positive

- Provides a clear growth path beyond Claude/Codex local hooks.
- Aligns with the master plan: governable, verifiable, portable coding agents
  in real repositories.
- Prevents early vendor lock-in by requiring capability-centric routing.
- Makes EC2/container/pod execution a planned runtime target rather than an
  accidental script side effect.

### Negative / Risks

- The architecture can become over-engineered if headless features invade the
  local default path.
- Shared-state and cluster features introduce operational complexity.
- Security expectations rise sharply once the runtime can mutate repositories
  without an interactive developer.
- Product messaging must stay honest while the runtime is still local-first.

## Guardrails

- Local default remains lightweight.
- Headless/clustered features are opt-in until mature.
- `.cognitive-os/` remains the canonical runtime state center.
- Driver projections (`.claude/`, `.codex/`, etc.) remain adapters, not the
  source of truth.
- Every new headless claim needs a runnable proof path or a test.

## Verification

Run the focused contract for this decision:

```bash
python3 -m pytest tests/contracts/test_headless_runtime_direction_docs.py -q
```
