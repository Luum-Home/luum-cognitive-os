---
type: quality-synthesis
source: docs/09-Quality/manual-tests/headless-runtime-proof-drills.md
provenance: "Defines the P1-P7 heavy manual proof-drill ladder for ADR-091/137/140 headless runtime claims, kept deliberately separate from the normal automated test taxonomy."
---

## What it is
A staged ladder of manual proof drills (P1 through P7) that validate increasing levels of headless/unattended runtime capability for Cognitive OS, from a Docker worker self-test up through future Kubernetes and cloud-provider overlays. Serves as the heavy validation path referenced by ADR-091, ADR-137, and ADR-140.

## Key mechanics
- Operator prerequisites: clean git state or isolated worktree, Docker for P1/P2, no real provider API keys needed for P1/P2, explicit confirmation before any cloud-costing drill.
- P1 (Compose worker self-test, implemented): `bash scripts/cos-cloud-worker-bootstrap.sh config` / `self-test`; proves the worker boots in Docker and a harmless hook runs, evidenced by an audit-trail row. Does not prove task admission, crash recovery, Kubernetes, or cloud deployment.
- P2 (Engram Cloud Docker sync, implemented): `scripts/cos-engram-cloud-docker-smoke --json` proves local central-memory replication across two project scopes (example JSON with `cloud_chunks` per project). Does not prove production token rotation, multi-maintainer federation, conflict resolution, or Kubernetes.
- P3 (Headless task execution, status: planned): target command `scripts/cos-proof-drill --scenario headless-task-execution --json` does not exist yet; a 8-step manual procedure (temp repo, bind-mounted worker, single task, claim/edit/validate, emit proof.json/patch.diff/audit.jsonl, human review, no auto-push) stands in until it does.
- P4 (Crash/resume, status: planned): target scenario `headless-crash-resume`; required behavior is kill-after-claim, restart, detect stale lease, resume-or-safe-failure, no WIP loss, no direct push to main.
- P5 (Single VM, status: future): disposable VM with Docker only, clone repo, run P1 then P2 if network policy allows, export `.cognitive-os/proofs/<run>/`. Pass condition explicitly forbids Homebrew, `~/.claude`, or local-Engram dependencies.
- P6 (Local Kubernetes via `kind`, status: future — "do not claim Kubernetes support before this passes"): requires Job/Deployment worker, ConfigMap/Secret boundary, readiness/liveness probes, no duplicate task execution when scaling 1→2.
- P7 (Cloud-provider overlay — EKS/GKE/AKS, status: future, only after P6): overlays are adapters that must not redefine the runtime contract; each needs cost estimate, cleanup command, and resource TTL.
- Every drill should eventually emit a standard evidence-bundle JSON with `scenario`, `status`, timestamps, `runtime_surface`, `cost_class`, `artifacts`, `claims_proven`, and a **mandatory** `claims_not_proven` field — explicitly designed to prevent local Docker proof from being marketed as Kubernetes or provider-cloud readiness.

## Relations & where used
Referenced by ADR-091, ADR-137, ADR-140 (headless runtime decisions). P1/P2 commands (`cos-cloud-worker-bootstrap.sh`, `cos-engram-cloud-docker-smoke`) are implemented; P3-P7 commands (`cos-proof-drill`) are aspirational/planned. Complements the sibling `headless-docker-service-runtime.md` drill, which covers a different (already-implemented) local-command execution path.

## Status / caveats
Mixed maturity by design: P1-P2 are implemented and runnable today; P3-P7 are explicitly marked planned/future and their target commands do not exist yet — this is a roadmap document as much as a test spec, not an inconsistency. The evidence-bundle JSON schema shown is a target contract, not yet universally emitted by all drills.
