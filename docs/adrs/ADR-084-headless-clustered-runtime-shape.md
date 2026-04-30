# ADR-084 — Headless and Clustered Runtime Shape

<!-- SCOPE: OS -->

**Status**: Proposed (retroactive backfill 2026-04-30)
**Date**: 2026-04-30
**Author**: Maintainer
**Related**: ADR-027 (performance monitoring SLOs), ADR-033 (harness-agnostic event capture), ADR-064 (cross-harness authoring)
**Implementation-plan**: .cognitive-os/plans/architecture/headless-clustered-runtime-plan.md

---

## Status

Proposed (retroactive backfill 2026-04-30).

---

## Context

Cognitive OS currently runs only in interactive local harness mode (Claude Code,
Codex). There is no defined contract for running it without an IDE, in a
container, or as part of a worker pool. ADR-027 introduced performance SLOs that
implicitly assume a future headless and distributed runtime, but left its shape
undefined.

Three deployment needs are emerging:

1. CI/CD pipelines need to run COS workflows headlessly on VMs or containers.
2. Multi-task repair jobs benefit from parallel workers rather than a single
   interactive session.
3. Kubernetes or similar orchestrators are a natural long-term target for
   queue-backed autonomous repair.

Without a deliberate shape decision, each of these needs would be solved ad hoc,
producing incompatible deployment models.

---

## Decision

Cognitive OS supports three runtime modes under a single product contract:

1. **Local harness mode** — interactive use on a developer machine via Claude Code
   or Codex. Current baseline; all existing behavior applies.
2. **Headless single-node mode** — CLI-driven execution in CI, a VM, or a
   container without an interactive harness. Entry point: `cos run-task` and
   `cos repair`.
3. **Queue-backed worker mode** — multiple headless workers consuming tasks from
   a shared queue. Entry point: `cos worker` and `cos queue-drain`, backed by
   Valkey or a filesystem queue.

All three modes share the same governance contract: hooks, quality gates, memory
lifecycle, and path portability rules apply equally. Headless mode is not a
reduced version of the OS.

### Non-negotiable constraints

- Cluster services (Valkey, Kubernetes) are never mandatory for local default use.
- Headless routing must reuse capability profiles; no duplicate routing logic.
- Provider names are not architecture boundaries.
- Developer-specific absolute paths must not appear in tracked files.
- Autonomous repair must have a testable proof path before it is claimed.
- Existing quality gates are not bypassed in headless mode.

### Phased delivery

The runtime shape is delivered in phases to avoid overclaiming readiness:

| Phase | Mode reached | Key deliverables |
|---|---|---|
| 0 | Local harness (current) | Doctor checks, harness normalization |
| 1 | Headless single-node | `cos run-task`, `cos repair`, isolated worktrees, local queue |
| 2 | Queue-backed workers | `cos worker`, `cos queue-drain`, Valkey option, durable leasing |
| 3 | Container | Container image, non-root execution, artifact volume contract |
| 4 | Kubernetes | Worker Deployment, liveness/readiness probes, horizontal scaling |
| 5 | Autonomous repair factory | Issue ingestion, PR publication, outcome learning loop |

Phases 4 and 5 are future work with no committed timeline. The system must not
claim Kubernetes or cluster superiority until Phase 4 passes a real smoke test.

---

## Consequences

### Positive

- A clear three-mode model prevents deployment decisions from being made ad hoc
  for each new use case.
- The phased approach lets local and headless modes ship and be validated before
  cluster complexity is added.
- Sharing governance across all modes means headless workloads produce the same
  audit trail and memory artifacts as interactive sessions.

### Negative / Trade-offs

- The constraint that cluster services are never mandatory for local use means the
  local queue implementation (filesystem or SQLite) must support all the same
  task lifecycle semantics as Valkey. This is more work than a single queue
  backend.
- Phases 4 and 5 are deliberately deferred. Teams that need Kubernetes support
  today have no path other than manual deployment.
- The `cos run-task` command design must be finalized before Phase 1 can be
  implemented, adding an upfront API-design cost.

### Risks

- If the local queue and Valkey queue are not interface-compatible, switching
  between them in Phase 2 will require rework at the call sites.
  Mitigation: define a queue interface in Phase 1 and implement both backends
  against it.
- Container path portability (Phase 3) depends on the path-sanitization rules
  already enforced for local mode. Any path portability regressions before
  Phase 3 begins will surface as container failures.

---

## Alternatives rejected

- **Headless-only; deprecate interactive mode**: Rejected because interactive
  local development is the primary usage mode and the primary dogfood surface.
- **Single monolithic deployment model (Kubernetes only)**: Rejected because it
  makes local development dependent on cluster infrastructure and breaks the
  no-mandatory-cluster-services constraint.
- **Separate codebases for local and headless**: Rejected because it would
  immediately create governance drift between modes and make quality gate
  enforcement inconsistent.

---

## Open questions

1. What is the exact task payload schema for `cos run-task`? Phase 1 cannot
   begin without it.
2. Should the filesystem queue in Phase 1 use SQLite or plain JSON files?
   SQLite offers atomic operations but adds a dependency; JSON is simpler but
   requires file-locking discipline.
3. What is the minimum container base image that satisfies the non-root and
   no-host-path constraints?

---

## Cross-references

- ADR-027: Performance monitoring SLOs (headless runtime is a prerequisite for
  meaningful SLO measurement beyond developer workstations)
- ADR-033: Harness-agnostic event capture (canonical events must be emitted in
  headless mode through the same adapter interface)
- ADR-064: Cross-harness authoring guide
- docs/manual-tests/local-connected-systems-validation.md (Phase 0 exit criteria)

## Verification

```bash
# Phase 0 exit criteria
cos doctor
# Phase 1 (once implemented)
cos run-task --help
cos repair --help
```
