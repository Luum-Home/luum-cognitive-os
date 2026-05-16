# Run Cognitive OS in Docker

> Operator runbook for the ADR-140 cloud-worker container surface.
> If you want to evaluate Cognitive OS without installing anything beyond
> Docker, this is the entry point.

## When to use this

- You want to **evaluate Cognitive OS** without installing it onto your shell profile.
- You need a **headless / cloud / CI worker** that runs the same hooks the maintainer's machine runs.
- You need a **cross-OS** path (Linux / macOS / Windows + WSL2) without shell-profile assumptions.
- You need a **compliance-evaluable surface** (BYOK credentials, audit trail with `audit_class` / `tenant_id` per ADR-142).

This is **not** the path for installing Cognitive OS as your daily Claude Code / Codex governance layer on your own laptop. For that, see [`getting-started.md`](../getting-started.md).

## Prerequisites

- Docker ≥ 24
- Docker Compose v2
- A clone of this repo (or a git worktree pointing at it)

Confirmed working on:

```bash
docker --version          # 29.4.0
docker compose version    # v2.x
```

Windows-native Docker without WSL2 is **not** a supported target (per ADR-140).

## Quick Start (90 seconds)

```bash
git clone https://github.com/Luum-Home/luum-cognitive-os
cd luum-cognitive-os
bash scripts/cos-cloud-worker-bootstrap.sh self-test
```

Expected output:

```text
cos-worker self-test passed; audit=/workspace/.cognitive-os/runtime/agent-audit-trail.jsonl
```

What just happened:

1. Built the `luum-cognitive-os-worker:local` image (~10 seconds cold, cached after).
2. Ran the worker entrypoint with `--self-test`.
3. Exercised `hooks/git-commit-scope-guard.sh` against a harmless `Bash` event to prove the hook layer works inside the container.
4. Wrote two audit-trail entries to `.cognitive-os/runtime/agent-audit-trail.jsonl`.

## Bootstrap script subcommands

```bash
bash scripts/cos-cloud-worker-bootstrap.sh <subcommand>

  config             validate the compose file without starting anything
  self-test          build + run --self-test (smoke test for hook layer + audit)
  up                 start the worker container only (no engram-cloud profile)
  up-full            start the full stack including engram-cloud profile
  down               stop and remove all containers (including engram-cloud)
  path               print the absolute path of the compose file
```

`up-full` activates the `engram-cloud` Compose profile, bringing up the
postgres+pgvector database and the engram-cloud server alongside the worker.

## Environment variables

All credentials are caller-supplied per ADR-139. The worker does **not** read your shell's environment unless you pass it explicitly through the wrapper.

```bash
COS_WORKSPACE=/path/to/repo            # default: this repo's root
COGNITIVE_OS_SESSION_ID=my-session      # default: cos-worker
LLM_PRIMARY_API_KEY=sk-...             # optional, BYOK primary provider
LLM_FALLBACK_API_KEY=sk-...            # optional, BYOK fallback provider
ENGRAM_CLOUD_PORT=8080                 # default: 8080
ENGRAM_CLOUD_DB=engram                 # default: engram
ENGRAM_CLOUD_DB_USER=engram            # default: engram
ENGRAM_CLOUD_DB_PASSWORD=engram-local  # default: engram-local
ENGRAM_CLOUD_INSECURE_NO_AUTH=1        # for local testing only; never in prod
ENGRAM_CLOUD_ALLOWED_PROJECTS=p1,p2    # tenant isolation per ADR-141
TENANT_ID=cos-worker                   # appears in audit trail per ADR-142
AUDIT_CLASS=change_management          # SOC 2 / ISO 27001 / GDPR mapping per ADR-142
CREDENTIAL_SOURCE=byok-project         # billing posture per ADR-139
BILLING_IDENTITY=cos-worker-local      # billing identity per ADR-139
```

## Run COS over a different project (consumer mode)

The worker exists to operate over **your** project, not over the COS repo itself. To do that, point `COS_WORKSPACE` at your project:

```bash
COS_WORKSPACE=/path/to/your-project \
  bash scripts/cos-cloud-worker-bootstrap.sh self-test
```

Inside the container, `/workspace` is bound to your project. The worker runs the configured hooks against it without touching your host shell environment.

## Full stack with engram-cloud (ADR-141)

```bash
bash scripts/cos-cloud-worker-bootstrap.sh up-full

# Verify services are up:
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep cos-

# You should see:
#   cos-worker-cos-engram-cloud-1      Up X seconds   0.0.0.0:8080->8080/tcp
#   cos-worker-cos-engram-cloud-db-1   Up Y seconds (healthy)   5432/tcp
#   cos-worker-cos-worker-1            Up
#   cos-worker-cos-engram-proxy-1      Up
```

The engram-cloud server listens on `localhost:8080`. It supports the live-sync replication path documented in ADR-141. The local SQLite remains authoritative; the cloud server is a replication-only complement to the existing `git-jsonl` path, not a replacement.

To bring everything down:

```bash
bash scripts/cos-cloud-worker-bootstrap.sh down
```

## Compliance evidence written by construction (ADR-142)

Every worker boot writes structured audit entries to `.cognitive-os/runtime/agent-audit-trail.jsonl`:

```json
{
    "timestamp": "2026-05-05T21:19:37Z",
    "event": "cos-worker-self-test-passed",
    "harness": "barecli",
    "tenant_id": "cos-worker",
    "audit_class": "change_management",
    "credential_source": "byok-project",
    "billing_identity": "cos-worker-local",
    "engram_project_scope": "luum-agent-os"
}
```

The five compliance fields (`tenant_id`, `audit_class`, `credential_source`, `billing_identity`, `engram_project_scope`) map to SOC 2 / ISO 27001 / GDPR controls per ADR-142. They are written **by construction**, not by an explicit logging call from your code.

The full enumeration of `audit_class` values (seven classes covering access control, change management, data access, etc.) is in ADR-142.

## Architecture inside the container

```text
docker/cos-worker/
├── Dockerfile        python:3.11-slim + bash + git + ca-certificates
├── docker-compose.yml
│   ├── cos-worker            (always)              the hook + governance runtime
│   ├── cos-engram-proxy      (engram-cloud profile) optional engram CLI proxy
│   ├── cos-engram-cloud-db   (engram-cloud profile) postgres + pgvector
│   └── cos-engram-cloud      (engram-cloud profile) engram cloud server :8080
└── entrypoint.sh             self-test + audit-trail writer
```

The entrypoint is intentionally thin. ADR-140 explicitly chose Compose configuration over shell-profile bootstrap magic so the deployment surface is observable and reproducible.

## What is NOT supported (be honest in the pitch)

- **Windows-native Docker without WSL2.** ADR-140 declares this out of scope. The invariant is WSL2 + Docker Desktop.
- **Auto credential pickup from your host shell.** The worker does not read your `~/.zshrc` or shell profile. Pass `LLM_*_API_KEY` explicitly or it stays unset.
- **Daily Claude Code / Codex usage.** This is a worker container, not your IDE governance layer. For day-to-day use, install on your laptop directly per [`getting-started.md`](../getting-started.md).

## Troubleshooting

### `docker: command not found`

Install Docker Desktop (macOS / Windows + WSL2) or Docker Engine + Compose v2 (Linux). Then re-run the self-test.

### `Cannot connect to the Docker daemon`

Ensure Docker Desktop is running. On Linux, ensure your user is in the `docker` group (`sudo usermod -aG docker $USER`, then re-login).

### Engram cloud server returns 404 on `/healthz`

Engram cloud does not expose `/healthz`. The server is up if you see `[engram-cloud] listening on 0.0.0.0:8080` in `docker logs cos-worker-cos-engram-cloud-1`. The 404 response itself is evidence the server is responding.

### Self-test passes but no audit-trail entry

Check the file path:

```bash
cat .cognitive-os/runtime/agent-audit-trail.jsonl | tail -3
```

If the file is empty, your `COS_WORKSPACE` may be pointing at a different directory than the host expects. Re-run with explicit path:

```bash
COS_WORKSPACE="$PWD" bash scripts/cos-cloud-worker-bootstrap.sh self-test
```

## Related ADRs and documents

- [ADR-140](../adrs/ADR-140-cross-os-containerized-deployment.md) — the architectural decision that defines this surface
- [ADR-141](../adrs/ADR-141-engram-cloud-cross-instance-replication.md) — engram cloud replication
- [ADR-142](../adrs/ADR-142-compliance-audit-air-gapped-surface.md) — audit trail compliance surface
- [ADR-139](../adrs/ADR-139-account-agnostic-multi-provider-runtime.md) — BYOK credential posture
- [ADR-137](../adrs/ADR-137-operational-trajectory-governance-layer-to-embedded-runtime.md) — why this surface exists at all
- [`docs/04-Concepts/architecture/bootstrap-portability.md`](../architecture/bootstrap-portability.md) — the portability gate this stack satisfies
- [`docs/04-Concepts/architecture/cloud-worker-runtime-tooling-research-2026-05.md`](../architecture/cloud-worker-runtime-tooling-research-2026-05.md) — research that informed ADR-140
- [`docs/09-Quality/manual-tests/headless-docker-service-runtime.md`](../manual-tests/headless-docker-service-runtime.md) — manual test of the worker surface
- [`docs/09-Quality/manual-tests/engram-cloud-docker-sync.md`](../manual-tests/engram-cloud-docker-sync.md) — manual test of the engram-cloud profile
