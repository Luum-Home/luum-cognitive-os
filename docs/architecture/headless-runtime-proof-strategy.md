# Headless Runtime Proof Strategy

This analysis documents how to prove the ADR-091 / ADR-137 / ADR-140 runtime
trajectory without pretending that heavy cloud/runtime validation belongs in the
existing local test lanes.

## Current position

The SO already has three different levels of commitment:

| Level | Source | Current status |
|---|---|---|
| Direction | ADR-091, ADR-137 | Accepted. COS should evolve from a local governance layer into an embedded/headless runtime. |
| Local container worker | ADR-140 | Implemented for Docker Compose worker surfaces. |
| Cross-instance memory | ADR-141 | Implemented for local Docker Engram Cloud proof and scoped sync. |
| Kubernetes / cloud-provider packaging | ADR-091 | Direction only. Not implemented and not claimable yet. |

The important distinction: **Docker Compose worker proof is implemented; full
headless/Kubernetes/cloud-provider runtime is not.**

For the service-boundary version of this distinction, see
[`cos-service-runtime-boundary.md`](cos-service-runtime-boundary.md).
For the future scheduler/queue/worker control-plane plan, see
[`service-control-plane-implementation-plan.md`](service-control-plane-implementation-plan.md).

## Why this must not be a normal test lane

The existing lanes (`unit`, `audit`, `contract`, `integration`, `make
test-laptop`) are designed for local developer feedback. Headless runtime proof
is different:

- It starts containers or remote workers.
- It may create queues, volumes, worktrees, branches, and artifacts.
- It may need cloud credentials or provider secrets.
- It may run for minutes or hours.
- It may intentionally crash workers to prove recovery.
- It may mutate temporary repositories.
- It may cost money.

Putting these checks into existing lanes would make the SO feel unstable and
would recreate the DX problem the recent ADRs are trying to solve.

## New validation class: proof drills

Use a separate class named **proof drills**.

Proof drills are not normal tests. They are opt-in runtime qualifications that
produce evidence bundles. They can be manual, semi-automated, or fully
automated, but they must never run by default in local test commands.

### Properties

Every proof drill must declare:

```yaml
id: headless-compose-single-worker
runtime_surface: docker-compose|vm|kubernetes|provider-overlay
cost_class: free_local|local_heavy|cloud_cost
destructive_scope: temp_repo|worktree|remote_ephemeral|remote_persistent
requires_credentials: false
expected_duration_minutes: 5
human_approval_required: true
produces:
  - proof.json
  - audit.jsonl
  - logs/
  - patch.diff
```

### Rules

1. A proof drill may be automated, but it must be launched explicitly.
2. A proof drill must write machine-readable evidence.
3. A proof drill must clean up by default.
4. A proof drill must support `--keep` for debugging.
5. A proof drill must not push, publish, or merge without human approval.
6. A proof drill must record what it proves and what it does not prove.
7. A failed proof drill is evidence, not a flaky test to hide.

## Proof ladder

### P0 — Static readiness

Purpose: prove the repo contains the declared surfaces.

Examples:

- ADR contract says ADR-140 exists and references Docker Compose.
- `docker/cos-worker/docker-compose.yml` renders.
- `scripts/cos-cloud-worker-bootstrap.sh config` works.

This can remain in audit/contract because it does not start heavy runtime.

### P1 — Local Compose single-worker proof

Purpose: prove COS can run inside a container without local IDE assumptions.

Required proof:

- Build/start `cos-worker`.
- Run one harmless hook inside the container.
- Write `agent-audit-trail.jsonl` from inside the bind-mounted workspace.
- Exit cleanly.

This already exists in ADR-140 shape via `scripts/cos-cloud-worker-bootstrap.sh
self-test`, but should also be represented as a proof drill artifact.

### P2 — Local Compose memory replication proof

Purpose: prove a local cloud worker can sync memory to a central Engram Cloud.

Required proof:

- Start `cos-engram-cloud-db`.
- Start `cos-engram-cloud`.
- Enroll at least two project scopes.
- Save one observation per project using a temporary Engram home.
- Run `engram sync --cloud --project` for each project.
- Verify scoped rows in Postgres.

This is now covered by `scripts/cos-engram-cloud-docker-smoke`.

### P3 — Headless task execution proof

Purpose: prove a headless worker can accept a bounded task without an IDE
harness.

Required proof:

- Create a temporary repository.
- Admit one task from a local task file or queue.
- Claim/lease the task.
- Modify a file.
- Run targeted validation.
- Produce a patch bundle.
- Stop before publication.
- Require human approval for merge/push.

This is the first proof that begins to exercise ADR-091 rather than just
ADR-140.

### P4 — Crash and resume proof

Purpose: prove unattended runtime is recoverable.

Required proof:

- Start a worker on a claimed task.
- Kill the worker mid-task.
- Restart runtime.
- Detect stale lease or recover owned workspace.
- Produce either a resumed patch or a safe failure bundle.
- Prove no WIP disappeared silently.

This is where SO governance becomes materially different from vanilla IDE
agent primitives.

### P5 — Single VM proof

Purpose: prove the runtime is not tied to the maintainer laptop.

Acceptable targets:

- local VM;
- disposable cloud VM;
- CI runner with Docker;
- remote Docker host.

Required proof:

- Fresh machine with Docker only.
- Clone repo.
- Run bootstrap.
- Execute P1 and P2.
- Export evidence bundle back to maintainer machine.

### P6 — Local Kubernetes proof

Purpose: prove Kubernetes packaging without cloud-provider cost.

Acceptable targets:

- kind;
- minikube;
- k3d.

Required proof before any Kubernetes claim:

- Worker Deployment or Job.
- ConfigMap/Secret boundaries.
- Readiness/liveness probes.
- Ephemeral workspace volume.
- Evidence artifact collection.
- Scale from 1 to 2 workers without duplicate task execution.

This is still future work.

### P7 — Cloud-provider overlay proof

Purpose: prove provider-specific packaging.

Targets:

- EKS;
- GKE;
- AKS;
- generic Kubernetes;
- ECS/Fargate or Cloud Run only if a flow requires them.

Provider overlays must be thin. The canonical runtime remains provider-neutral;
provider-specific files are deployment adapters, not the source of truth.

## Manual vs automated proof

### Manual proof is acceptable when:

- the target requires paid cloud resources;
- the proof needs human approval;
- the proof validates operator UX;
- the drill is run rarely.

### Automated proof is appropriate when:

- the drill is local and free;
- cleanup is deterministic;
- runtime is bounded;
- evidence can be parsed mechanically;
- failure is actionable.

### Do not automate yet when:

- the automation would require persistent cloud credentials;
- a failed cleanup would leave billable resources;
- the proof creates public branches or PRs without human review;
- the drill is still changing weekly.

## Proposed artifact layout

Future proof drills should live outside normal pytest lanes:

```text
proof-drills/
  headless-compose-single-worker.sh
  engram-cloud-compose-sync.sh
  headless-task-execution.sh
  headless-crash-resume.sh
  k8s-kind-worker.sh

manifests/headless-proof-scenarios.yaml

.cognitive-os/proofs/
  <timestamp>-<scenario>/
    proof.json
    audit.jsonl
    logs/
    patch.diff
    README.md
```

They may be wrapped later by:

```bash
scripts/cos-proof-drill --scenario headless-compose-single-worker --json
```

But they should not be hidden behind `make test-laptop` or the normal CI gates.

## Claim discipline

Allowed now:

> COS has a Docker Compose worker surface and local Engram Cloud replication
> proof.

Not allowed yet:

> COS is Kubernetes-native.

> COS is a production autonomous repair cluster.

> COS supports all cloud providers.

Allowed future wording after P6:

> COS has a local Kubernetes proof path for headless workers.

Allowed future wording after at least one provider overlay:

> COS has a tested deployment adapter for `<provider>`.

## Next implementation sequence

1. Convert existing ADR-140 self-test and ADR-141 Docker smoke into first-class
   proof drill outputs under `.cognitive-os/proofs/`.
2. Add `manifests/headless-proof-scenarios.yaml`.
3. Add `scripts/cos-proof-drill` as an explicit launcher.
4. Implement P3 headless task execution against a temporary repo.
5. Implement P4 crash/resume proof.
6. Only then design P6 kind/minikube Kubernetes packaging.
7. Only after P6 passes should provider overlays be considered.

This keeps growth controlled: first prove local single-worker semantics, then
prove recovery, then prove orchestration, then prove provider adapters.
