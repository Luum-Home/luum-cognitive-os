# Headless and Clustered Runtime Plan

This plan implements ADR-027 in phases. It is intentionally staged so Cognitive
OS does not overclaim cluster readiness before the runtime is real.

## Success Condition

A new operator can use Cognitive OS in one of three ways without changing the
product philosophy:

1. local harness mode on a developer machine;
2. headless single-node mode in CI, a VM, or a container;
3. queue-backed worker mode in a future cluster.

In every mode, the runtime should remain governable, verifiable, portable, and
capability-centric.

## Phase 0 — Current Local Harness Runtime

**Status**: active.

Current behavior:

- lifecycle hooks run through local harness drivers;
- `.cognitive-os/` holds runtime state;
- `.claude/` and `.codex/` are projections;
- memory, metrics, tasks, doctors, install/update, and quality checks exist;
- provider adapters are being normalized through canonical context.

Exit criteria:

- local Codex and Claude Code installs pass host doctor checks;
- self-install/update does not re-center the runtime on `.claude/`;
- temporary test/canary installs do not pollute the production registry.
- local connected-system validation proves dependency readiness, MCP wiring, optional service boundaries, and persistent test summaries through [Local Connected Systems Validation](../../manual-tests/local-connected-systems-validation.md).

## Phase 1 — Headless Single-Node Runtime

**Goal**: run Cognitive OS without an interactive IDE/harness.

Deliverables:

- `cos run-task` command that accepts a task payload;
- `cos repair` command that starts from a failing test or bug report;
- explicit workspace creation using git worktrees or temp directories;
- local queue mode backed by filesystem or SQLite;
- local artifact directory for logs, patches, and test summaries;
- doctor check for headless prerequisites.

Proof paths:

- run a synthetic failing test in an isolated worktree;
- generate a patch;
- run quality gates;
- write a task outcome record;
- cleanly resume or fail after interruption.

## Phase 2 — Queue-Backed Worker Runtime

**Goal**: support multiple headless workers on one host or across VMs.

Deliverables:

- `cos worker` command;
- `cos queue-drain` command;
- Valkey-backed queue option;
- durable task leasing and heartbeat;
- retry/backoff/dead-letter queue;
- per-task cost and capability limits;
- worker crash recovery.

Proof paths:

- enqueue N tasks;
- run two workers;
- prove no duplicate task execution;
- kill one worker mid-task;
- verify task recovery or dead-letter behavior;
- record outcome metrics.

## Phase 3 — Container Runtime

**Goal**: make a worker runnable in a container without local-machine assumptions.

Deliverables:

- container image definition;
- non-root execution where possible;
- mounted workspace contract;
- environment/secret contract;
- artifact volume contract;
- no developer-home absolute paths in generated assets.

Proof paths:

- run `cos run-task` inside a container;
- mount a repository read/write;
- emit artifacts outside the container;
- verify no host-specific paths are written into repo-managed files.

## Phase 4 — Kubernetes Runtime

**Goal**: run Cognitive OS as a scalable worker pool.

Deliverables:

- Kubernetes manifests or Helm chart;
- worker Deployment;
- queue/shared-state configuration;
- ConfigMap/Secret split;
- liveness/readiness probes;
- resource requests/limits;
- horizontal scaling behavior.

Proof paths:

- deploy local kind/minikube profile;
- enqueue tasks;
- scale workers from 1 to N;
- verify leasing and no duplicate execution;
- collect traces/metrics;
- tear down cleanly.

## Phase 5 — Autonomous Repair / Product Factory

**Goal**: orchestrate bug repair and feature-building workflows end-to-end.

Deliverables:

- ticket/issue ingestion adapter;
- failing-test ingestion adapter;
- planning/router stage;
- isolated patch generation;
- quality-gate stage;
- PR/patch publication adapter;
- human approval gates;
- outcome learning loop.

Proof paths:

- ingest a synthetic issue;
- reproduce failure;
- repair in isolated workspace;
- pass tests;
- open or produce a PR/patch;
- save memory and outcome metrics.

## Non-Negotiable Constraints

- Do not make cluster services mandatory for local default use.
- Do not duplicate routing logic; headless routing must reuse capability profiles.
- Do not make provider names the architecture boundary.
- Do not write developer-specific absolute paths into tracked files.
- Do not claim autonomous repair without a testable proof path.
- Do not bypass existing quality gates in headless mode.

## Tracking Checklist

- [ ] Phase 1 command design documented.
- [ ] Phase 1 local task payload schema created.
- [ ] Phase 1 isolated workspace proof implemented.
- [ ] Phase 2 queue/worker contract documented.
- [ ] Phase 2 worker lease tests implemented.
- [ ] Phase 3 container contract documented.
- [ ] Phase 3 no-host-path proof implemented.
- [ ] Phase 4 Kubernetes manifests drafted.
- [ ] Phase 4 local cluster smoke test implemented.
- [ ] Phase 5 repair/product-factory workflow proof implemented.

- [Runtime Comparison Benchmark Plan](runtime-comparison-benchmark-plan.md) — compares COS against vanilla Claude/Codex and prior-art tools across workstation, VM, container, pod, and cluster surfaces.
- [Local Connected Systems Validation](../../manual-tests/local-connected-systems-validation.md) — proves local dependency and service readiness before extending the runtime to VM/container/cluster surfaces.
