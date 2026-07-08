---
type: concept-synthesis
source: docs/04-Concepts/architecture/headless-runtime-proof-strategy.md
provenance: "Need to prove the ADR-091/ADR-137/ADR-140 headless-runtime trajectory without pretending heavy cloud/runtime validation belongs in existing local pytest lanes (unit/audit/contract/integration)."
---

## What it is
Defines a separate validation class, "proof drills" — opt-in runtime qualifications (not normal tests) that produce evidence bundles for progressively heavier runtime claims (Docker Compose → headless task execution → crash/resume → Kubernetes → cloud-provider overlays), explicitly kept out of default test lanes.

## Key mechanics
- Current commitment levels: Direction (ADR-091, ADR-137, Accepted); Local container worker (ADR-140, Implemented for Docker Compose); Cross-instance memory (ADR-141, Implemented for local Docker Engram Cloud); Kubernetes/cloud packaging (ADR-091, direction only, not implemented/not claimable).
- Why not a normal test lane: proof drills start containers/remote workers, may need cloud credentials, may run minutes-to-hours, may intentionally crash workers, may cost money.
- Every proof drill declares a YAML contract: `id`, `runtime_surface` (docker-compose|vm|kubernetes|provider-overlay), `cost_class` (free_local|local_heavy|cloud_cost), `destructive_scope`, `requires_credentials`, `expected_duration_minutes`, `human_approval_required`, `produces` (proof.json, audit.jsonl, logs/, patch.diff).
- 6 rules: must be launched explicitly, write machine-readable evidence, clean up by default (support `--keep`), never push/publish/merge without human approval, record what it proves/doesn't, treat failure as evidence not a flaky test to hide.
- Proof ladder P0-P7: P0 static readiness (stays in audit/contract, no heavy runtime); P1 local Compose single-worker (covered by `scripts/cos-cloud-worker-bootstrap.sh self-test`); P2 Compose memory-replication proof (covered by `scripts/cos-engram-cloud-docker-smoke`); P3 headless task execution (create temp repo, claim task, patch, stop before publication — first real ADR-091 exercise); P4 crash/resume proof; P5 single-VM proof; P6 local Kubernetes (kind/minikube/k3d, future work); P7 cloud-provider overlay (EKS/GKE/AKS, thin adapters only).
- Proposed artifact layout: `proof-drills/*.sh`, `manifests/headless-proof-scenarios.yaml`, `.cognitive-os/proofs/<timestamp>-<scenario>/{proof.json,audit.jsonl,logs/,patch.diff,README.md}`; future launcher `scripts/cos-proof-drill --scenario ... --json` — must not hide behind `make test-laptop` or normal CI gates.
- Manual proof acceptable when: paid cloud resources, needs human approval, validates operator UX, run rarely. Do not automate when: requires persistent cloud credentials, failed cleanup could leave billable resources, creates public branches/PRs without review, or the drill is still changing weekly.

## Relations & where used
References ADR-091, ADR-137, ADR-140, ADR-141; see also `cos-service-runtime-boundary.md` (service-boundary framing) and `service-control-plane-implementation-plan.md` (future scheduler/queue/worker plan).

## Status / caveats
Claim discipline explicit: allowed now — "COS has a Docker Compose worker surface and local Engram Cloud replication proof." Not allowed yet — "COS is Kubernetes-native," "production autonomous repair cluster," "supports all cloud providers." Next sequence: convert ADR-140/141 self-tests into first-class `.cognitive-os/proofs/` outputs, add the manifest + `cos-proof-drill` launcher, implement P3 then P4, only then design P6/P7.
