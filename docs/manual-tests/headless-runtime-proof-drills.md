# Headless Runtime Proof Drills

Manual proof drills are the heavy validation path for ADR-091 / ADR-137 /
ADR-140. They are deliberately separate from the normal test taxonomy.

## Operator prerequisites

- Clean git state or an isolated worktree.
- Docker available for P1/P2.
- No real provider API keys required for P1/P2.
- Explicit confirmation before any cloud-costing drill.

## P1 — Compose worker self-test

Purpose: prove the COS worker can boot in Docker and run a harmless hook.

```bash
bash scripts/cos-cloud-worker-bootstrap.sh config
bash scripts/cos-cloud-worker-bootstrap.sh self-test
```

Expected evidence:

- Compose config renders.
- Worker exits successfully.
- `.cognitive-os/runtime/agent-audit-trail.jsonl` receives a container boot or
  hook smoke row.

What it does not prove:

- task admission;
- crash recovery;
- Kubernetes;
- cloud-provider deployment.

## P2 — Engram Cloud Docker sync

Purpose: prove local central memory replication across two project scopes.

```bash
scripts/cos-engram-cloud-docker-smoke --json
```

Expected evidence:

```json
{
  "status": "pass",
  "cloud_chunks": [
    {"project": "cos-consumer-e2e-drill", "chunks": 1, "observations": 1},
    {"project": "luum-agent-os", "chunks": 1, "observations": 1}
  ]
}
```

What it does not prove:

- authenticated production token rotation;
- multi-maintainer federation;
- conflict resolution;
- Kubernetes.

## P3 — Headless task execution drill

Status: planned.

Purpose: prove a worker can complete a bounded task without an IDE harness.

Target future command:

```bash
scripts/cos-proof-drill --scenario headless-task-execution --json
```

Required manual procedure until the command exists:

1. Create a temporary repository.
2. Start the COS worker with the temporary repo bind-mounted.
3. Provide a single task file, for example: "append one line to README and run a
   grep-based assertion."
4. Worker claims the task.
5. Worker edits only the temp repo.
6. Worker runs validation.
7. Worker emits `proof.json`, `patch.diff`, and `audit.jsonl`.
8. Human reviews the patch. No auto-push.

Pass condition:

- one task claimed;
- one patch produced;
- validation passes;
- audit trail records claim, edit, validation, and stop;
- no publication without human approval.

## P4 — Crash/resume drill

Status: planned.

Purpose: prove an unattended worker can fail safely.

Target future command:

```bash
scripts/cos-proof-drill --scenario headless-crash-resume --json
```

Required behavior:

1. Start worker on temp task.
2. Kill worker after it claims the task and creates WIP.
3. Restart worker.
4. Runtime detects prior lease/workspace.
5. Runtime either resumes safely or emits a safe failure bundle.
6. No WIP is lost.
7. No direct push to `main`.

Pass condition:

- stale lease is visible;
- WIP is preserved or explicitly archived;
- recovery outcome is auditable;
- no silent cleanup.

## P5 — Single VM drill

Status: future.

Purpose: prove the runtime is independent from the maintainer laptop.

Manual target:

1. Start a disposable VM with Docker only.
2. Clone the repo.
3. Run P1.
4. Run P2 if network policy allows local Docker images.
5. Export `.cognitive-os/proofs/<run>/` back to the maintainer machine.

Pass condition:

- no Homebrew dependency;
- no `~/.claude` dependency;
- no local Engram dependency;
- evidence bundle returns.

## P6 — Local Kubernetes drill

Status: future; do not claim Kubernetes support before this passes.

Manual target:

```bash
kind create cluster --name cos-proof
# future:
scripts/cos-proof-drill --scenario k8s-kind-worker --json
```

Required behavior:

- worker runs as Job or Deployment;
- ConfigMap/Secret boundary exists;
- readiness/liveness probes exist;
- temporary workspace volume exists;
- evidence artifact is collected;
- two workers do not execute the same task.

Pass condition:

- scale 1→2 does not duplicate task execution;
- failed pod leaves evidence;
- cleanup removes cluster resources.

## P7 — Cloud-provider overlay drill

Status: future; only after P6.

Targets:

- EKS;
- GKE;
- AKS;
- other only when a real flow requires it.

Rules:

- Provider overlays are adapters.
- Provider overlays must not redefine the runtime contract.
- Every overlay needs cost estimate, cleanup command, and resource TTL.

## Evidence bundle contract

Every proof drill should eventually emit:

```json
{
  "scenario": "headless-compose-single-worker",
  "status": "pass|fail",
  "started_at": "2026-05-04T00:00:00Z",
  "finished_at": "2026-05-04T00:05:00Z",
  "runtime_surface": "docker-compose",
  "cost_class": "free_local",
  "artifacts": {
    "audit": "audit.jsonl",
    "logs": "logs/",
    "patch": "patch.diff"
  },
  "claims_proven": [],
  "claims_not_proven": []
}
```

The `claims_not_proven` field is mandatory. It prevents local Docker proof from
being accidentally marketed as Kubernetes or provider-cloud readiness.
