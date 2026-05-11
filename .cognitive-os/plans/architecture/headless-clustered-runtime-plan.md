---
related-adr: ADR-084
---

<!--
RECONCILIATION STATUS: PARTIAL — 2026-05-10 (post-v0.28.0)
Reconciled-by: P2 plan reconciliation (see docs/reports/p2-plan-reconciliation-2026-05-10.md)
Phase status:
- Phase 0 (current local harness): ACTIVE as designed.
- Phase 1 (headless single-node): MOSTLY DONE — `cos run-task` contract documented (docs/architecture/cos-run-task-contract.md cited); 5 of 8 tracking items checked; unattended safe-mode/kill-switch + protected-publication + VM-restart idempotency proofs not yet shipped (some implicitly covered by ADR-246 release-transaction freeze for publication paths).
- Phase 2 (queue-backed worker): PARTIAL — research documented (cloud-worker-runtime-tooling-research-2026-05.md); worker-lease tests pending; queue worker referenced as default push path in foundation-hardening-program.md Phase 2.
- Phase 3 (container): DOCUMENTED — Docker worker bootstrap shipped in v0.26.0 (`scripts/cos-cloud-worker-bootstrap.sh` + `docs/runbooks/run-cos-in-docker.md`); container contract document item still unchecked.
- Phase 4 (Kubernetes): NOT STARTED. Per External Tool Adoption Doctrine, distributed workflow engines and multi-machine orchestration are explicitly DEFER/REJECT. This phase remains aspirational until a Shape-B trigger fires per ADR-132.
- Phase 5 (autonomous repair): NOT STARTED — guarded by non-negotiable constraint "Do not claim autonomous repair without testable proof path".
Recommendation: keep ACTIVE for Phases 1-2 follow-through; treat Phases 4-5 as DEFER per doctrine. Do NOT archive.

OPUS REFINEMENT — 2026-05-11 (post-v0.28.0):
Opus AGREES with Sonnet's PARTIAL framing. Concrete cross-check against unchecked items at lines 195-205:
- Phase 1 acceptance lines 195-197 (unattended safe-mode/kill-switch, protected-publication, VM-restart idempotency proofs): ADR-246 release transaction freeze + ADR-241 cos-bypass allowlist + branch-ownership-lock cover the publication path implicitly; explicit kill-switch and VM-restart idempotency single-contract proofs not yet shipped. Stay open.
- Phase 2 acceptance lines 198-200 (queue/worker contract + lease tests): docs/runbooks/run-cos-in-docker.md exists but queue/worker contract document + lease tests pending.
- Phase 3 acceptance lines 201-202: docs/runbooks/run-cos-in-docker.md serves as partial container contract; no-host-path proof still open.
- Phases 4-5 (Kubernetes + autonomous repair): explicit DEFER per External Tool Adoption Doctrine (ADR-132) — no Shape-B trigger has fired.
Opus confirms: PARTIAL. Recommendation stands.
-->

# Headless and Clustered Runtime Plan

This plan implements ADR-027 in phases. It is intentionally staged so Cognitive
OS does not overclaim cluster readiness before the runtime is real.

## Success Condition

A new operator can use Cognitive OS in one of four ways without changing the
product philosophy:

1. local harness mode on a developer machine;
2. headless single-node mode in CI, a VM, or a container;
3. solo-maintainer cloud worker mode for unattended but governed work across
   multiple projects;
4. queue-backed worker mode in a future cluster.

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
- local connected-system validation proves dependency readiness, MCP wiring, optional service boundaries, and persistent test summaries through [Local Connected Systems Validation](../../../docs/manual-tests/local-connected-systems-validation.md).

## Phase 1 — Headless Single-Node Runtime

**Goal**: run Cognitive OS without an interactive IDE/harness. This includes the
solo-maintainer cloud worker case: one operator intentionally leaves a governed
agent runtime running on a VM/container while local IDE sessions may also exist.

Deliverables:

- `cos run-task` command that accepts a task payload;
- `cos repair` command that starts from a failing test or bug report;
- explicit workspace creation using git worktrees or temp directories;
- local queue mode backed by filesystem or SQLite;
- local artifact directory for logs, patches, and test summaries;
- doctor check for headless prerequisites;
- unattended safe-mode / kill-switch command;
- protected-publication policy: no unattended worker may push to `main` without
  merge queue or human approval;
- crash-safe task outcome ledger so a restarted VM cannot double-publish or lose
  evidence.

Proof paths:

- run a synthetic failing test in an isolated worktree;
- generate a patch;
- run quality gates;
- write a task outcome record;
- cleanly resume or fail after interruption;
- simulate VM restart during a task and prove idempotent resume/dead-letter;
- attempt unattended direct-main publication and prove it is blocked or routed
  through protected landing.

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
- Do not claim unattended cloud operation until crash recovery, safe-mode,
  artifact persistence, and protected-publication proof paths pass.
- Do not bypass existing quality gates in headless mode.

## Tracking Checklist

- [x] Phase 1 command design documented.
- [x] Phase 1 local task payload schema created.
- [x] Phase 1 isolated workspace proof implemented.
- [x] Phase 1 provider/agent command execution implemented.
- [x] Phase 1 acceptance execution and outcome artifacts implemented.
- [ ] Phase 1 unattended safe-mode / kill-switch proof implemented.
- [ ] Phase 1 protected-publication proof implemented.
- [ ] Phase 1 VM-restart idempotency proof implemented.
- [ ] Phase 2 queue/worker contract documented.
- [x] Phase 2 queue/workflow tooling research documented.
- [ ] Phase 2 worker lease tests implemented.
- [ ] Phase 3 container contract documented.
- [ ] Phase 3 no-host-path proof implemented.
- [ ] Phase 4 Kubernetes manifests drafted.
- [ ] Phase 4 local cluster smoke test implemented.
- [ ] Phase 5 repair/product-factory workflow proof implemented.

- [Runtime Comparison Benchmark Plan](runtime-comparison-benchmark-plan.md) — compares COS against vanilla Claude/Codex and prior-art tools across workstation, VM, container, pod, and cluster surfaces.
- [Local Connected Systems Validation](../../../docs/manual-tests/local-connected-systems-validation.md) — proves local dependency and service readiness before extending the runtime to VM/container/cluster surfaces.
- [`cos run-task` Contract](../../../docs/architecture/cos-run-task-contract.md) — defines the Phase 1 payload, provider/agent command, artifact, exit-code, and security contract.
- [Cloud Worker Runtime Tooling Research — 2026-05](../../../docs/architecture/cloud-worker-runtime-tooling-research-2026-05.md) — evaluates queue/workflow options for later phases.
