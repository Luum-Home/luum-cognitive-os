# COS Service Runtime Boundary

This document answers a deliberately narrow question:

> How does Cognitive OS run as a service, given that today it is mostly used
> inside IDEs and coding-agent harnesses?

## Short answer

Cognitive OS does **not** yet have one central long-running service such as
`cosd` that owns scheduling, task admission, workers, leases, and publication.

Today it has three runtime shapes:

1. **Harness-embedded runtime** — the current primary mode.
2. **Docker Compose worker surface** — implemented as a containerized worker
   proof path.
3. **Engram Cloud service** — a real long-running service for cross-instance
   memory replication.

The missing piece is a **COS control-plane service** for autonomous/headless
task execution.

## Runtime shape 1: harness-embedded runtime

This is the current default.

```text
Claude Code / Codex / other harness
  -> projected settings
  -> COS hooks
  -> COS rules
  -> COS skills
  -> COS scripts
  -> JSONL metrics/audit
  -> Engram local/cloud memory
```

In this mode, the IDE or harness owns:

- process lifecycle;
- interactive user turn loop;
- tool invocation;
- sub-agent launch semantics;
- prompt/context assembly.

COS owns:

- governance hooks;
- claim and coordination checks;
- lifecycle manifests;
- audit rows;
- memory wrappers;
- projection readiness;
- proof/control-plane scripts.

This is **not** a standalone service. It is a governed runtime layer inside an
existing host.

## Runtime shape 2: Docker Compose worker surface

Implemented files:

- `docker/cos-worker/docker-compose.yml`
- `docker/cos-worker/Dockerfile`
- `docker/cos-worker/entrypoint.sh`
- `scripts/cos-cloud-worker-bootstrap.sh`

Current commands:

```bash
bash scripts/cos-cloud-worker-bootstrap.sh config
bash scripts/cos-cloud-worker-bootstrap.sh self-test
bash scripts/cos-cloud-worker-bootstrap.sh up
bash scripts/cos-cloud-worker-bootstrap.sh down
```

The `cos-worker` service is a **worker surface**, not a full scheduler.

It proves that COS can run in a container without relying on:

- `~/.claude`;
- shell profile startup;
- Homebrew;
- local Python outside the image;
- an IDE-attached session.

What it can do today:

- boot in Docker;
- receive explicit environment variables;
- bind-mount a workspace;
- run hook smoke checks;
- write audit rows into `.cognitive-os/runtime/agent-audit-trail.jsonl`;
- serve as the deployment unit for future proof drills.

What it does **not** do yet:

- accept tasks from a queue;
- lease tasks;
- schedule multiple workers;
- resume after crash;
- manage branch/worktree lifecycle autonomously;
- publish PRs or patches;
- expose an HTTP API;
- run as a durable `cosd` daemon.

## Runtime shape 3: Engram Cloud service

Implemented files:

- `docker/cos-worker/docker-compose.yml`
- `scripts/cos-engram-cloud-enroll`
- `scripts/engram-sync.sh`
- `scripts/cos-engram-cloud-docker-smoke`
- `docs/manual-tests/engram-cloud-docker-sync.md`

This is a real service:

```text
cos-engram-cloud-db  -> Postgres/pgvector
cos-engram-cloud     -> engram cloud serve
```

It supports cross-instance memory replication through:

```bash
engram cloud config --server URL
engram cloud enroll PROJECT
engram sync --cloud --project PROJECT
```

It was proven locally with:

```bash
scripts/cos-engram-cloud-docker-smoke --json
```

This service solves memory replication. It does **not** solve task scheduling or
worker orchestration.

## The missing service: COS control plane

The future service boundary implied by ADR-091 looks like this:

```text
cosd / COS control plane
  -> task admission
  -> queue / scheduler
  -> worker leases
  -> workspace allocation
  -> cos-worker containers
  -> validation/proof drills
  -> artifact store
  -> propose-only PR/patch output
  -> Engram Cloud
```

The command surface named by ADR-091 but not implemented as production service
yet:

```text
cos worker
cos run-task
cos repair
cos queue-drain
```

Until these exist, COS must not claim to be a full standalone autonomous
service.

## Service-readiness ladder

| Stage | Status | Meaning |
|---|---|---|
| S0 — harness embedded | implemented | COS runs inside IDE/harness lifecycle. |
| S1 — Compose worker self-test | implemented | COS boots in Docker and runs a hook smoke. |
| S2 — Engram Cloud service | implemented | Memory replication runs as a service. |
| S3 — headless task execution | planned | Worker can claim and complete a bounded task without an IDE. |
| S4 — crash/resume | planned | Worker can fail and recover without losing WIP. |
| S5 — single VM | planned | Fresh VM can run worker and return evidence. |
| S6 — local Kubernetes | planned | kind/minikube/k3d worker proof with probes and no duplicate task execution. |
| S7 — provider overlays | planned | EKS/GKE/AKS/etc. adapters after generic K8s proof. |

## Product wording

Allowed today:

> COS has a Docker Compose worker surface and an Engram Cloud service proof.

> COS can run inside IDE harnesses and can boot a containerized worker for
> explicit proof drills.

Not allowed today:

> COS has a full standalone daemon.

> COS is Kubernetes-native.

> COS is a production autonomous repair cluster.

> COS supports every cloud provider.

Allowed future wording after S3/S4:

> COS can execute bounded headless tasks and recover from worker crashes under
> a propose-only contract.

Allowed future wording after S6:

> COS has a local Kubernetes proof path for headless workers.

Allowed future wording after S7:

> COS has a tested deployment adapter for `<provider>`.

## Relationship to ADRs

- ADR-091 defines the headless/clustered direction.
- ADR-137 defines the trajectory from governance layer to embedded runtime.
- ADR-140 implements the Docker Compose worker surface.
- ADR-141 implements Engram Cloud replication.
- `docs/architecture/headless-runtime-proof-strategy.md` defines how to prove
  the future service stages without polluting normal test lanes.
- `docs/architecture/service-control-plane-research-2026-05-04.md` compares
  service-shaped agent runtimes and defines the credential-mode boundary for
  account-backed provider executors.
- `docs/architecture/service-control-plane-implementation-plan.md` stages the
  future `cosd` queue, leases, workers, provider adapters, artifact store, and
  propose-only output.

This document is the boundary statement: it prevents the implemented worker
surface from being overclaimed as a complete COS service.
