---

adr: 140
title: Cross-OS Containerized Deployment via Docker Compose
status: accepted
implementation_status: implemented
date: 2026-05-04
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: [infrastructure, docker, deployment, portability, cloud-flows, cross-os]
---

# ADR-140: Cross-OS Containerized Deployment via Docker Compose

## Status

**Accepted — Implemented** as the containerised deployment shape for COS cloud
worker surfaces. Local harness installation (pip, direct clone) is unchanged.

## Context

[ADR-137](ADR-137-operational-trajectory-governance-layer-to-embedded-runtime.md) commits to Framing A: a COS runtime that travels with the agent into cloud instances, CI runners, and ephemeral containers. The [`dx-cloud-flow-bootstrap-plan.md`](../architecture/dx-cloud-flow-bootstrap-plan.md) names cross-harness portability and the absence of `~/.claude/`-assumption as prerequisites for the first cloud-worker flow.

The current install path (`pip install cognitive-os`, direct hook wiring) is designed for a developer machine and makes several platform-specific assumptions:

- Shell profiles (`~/.bashrc`, `~/.zshrc`) are present and sourced
- `~/.claude/` directory exists (Claude Code assumption)
- `~/.engram/` directory exists with a running daemon
- System Python ≥ 3.11 is the only required runtime
- Network access to PyPI is available at install time

None of these are safe to assume for ephemeral Linux containers, Windows CI runners, or macOS GitHub Actions hosts. The cloud-worker-runtime research document (`cloud-worker-runtime-tooling-research-2026-05.md`) confirms Phase 1 must not add a broker or orchestration platform — the target is a single-VM / single-container deployment that works without external services.

ADR-048 addressed Docker image freshness for *optional services* (Postgres, Valkey, Engram daemon); it did not address COS itself as a containerised runtime.

## Decision

### 1. Single Compose stack for cloud worker surfaces

Cloud workers that need COS as an embedded runtime MUST be launchable via a Docker Compose stack defined in `docker/cos-worker/docker-compose.yml`. The stack:

- Runs on Linux (primary), macOS (developer testing), and Windows with WSL2 (CI compatibility).
- Contains at minimum: a `cos-worker` service (COS runtime + harness adapter) and, when cloud Engram replication is active, a `cos-engram-proxy` sidecar (see ADR-141).
- Uses bind mounts for workspace and `.cognitive-os/` directories; does not bake project state into the image.
- Accepts all configuration via environment variables; no shell profile sourcing required.

The Compose stack is a **cloud worker surface** only. The maintainer's local install path remains unchanged. No `docker-compose.yml` is added to the repo root or to `packages/` that would replace the local install.

### 2. Platform-native compatibility invariants

The Compose stack MUST satisfy all three:

| Platform | Invariant |
|---|---|
| Linux (Ubuntu 22.04+, Debian 12+) | Stack runs with `docker compose up` from a fresh Docker install; no system Python required outside the container. |
| macOS (12+) | Stack runs with Docker Desktop or OrbStack; no Homebrew dependency outside Docker. |
| Windows + WSL2 | Stack runs from a WSL2 terminal with Docker Desktop WSL2 backend; bind mount paths use WSL2 Linux paths. |

The CI matrix for the Compose stack covers Linux only by default (cheapest). macOS and Windows are manual-verification targets until a flow requires them in CI.

### 3. No shell profile assumption

The `cos-worker` image MUST:

- Configure all hooks via explicit paths in `COGNITIVE_OS_PROJECT_DIR` and companion env vars, not via `~/.claude/settings.json`.
- Start the Engram daemon (when local-only mode) via a container `ENTRYPOINT` or `CMD`, not via a shell profile hook.
- Expose session lifecycle via container start/stop signals, not via shell `EXIT` traps that rely on interactive terminal semantics.

The `cos-cloud-worker-bootstrap.sh` script named in ADR-137 and the bootstrap plan is the entry point that satisfies this: it sets env vars and invokes the container, not a shell profile.

### 4. Image build discipline

- Base image: `python:3.11-slim` (Debian-based, audited supply chain, no AGPL runtime in the base layer).
- Image is built from a `Dockerfile` in `docker/cos-worker/`; the image is not published to a public registry as part of this ADR. A flow that needs a pre-built image handles registry publishing in its own skill.
- Image layers follow the existing `packages/infra-lifecycle/` freshness policy (ADR-048): a layer containing `requirements.txt` is invalidated when requirements change.
- The image does not embed provider API keys. Keys are injected at container run time via the `--env-file` flag or the Compose `environment:` block populated from CI secrets.

### 5. Optional services remain optional

The existing optional services (Postgres, Valkey, Engram daemon) continue to operate as defined in ADR-060. The `cos-worker` Compose stack MUST be runnable without any of the optional services active. A flow that requires Postgres or Valkey declares this in its `flow_contract.yaml` `sandboxed_write_paths` or as a named dependency; the Compose stack conditionally includes the relevant sidecar via Compose profiles.

### 6. Windows-specific constraints

Windows-native Docker (without WSL2) is not a supported target. The invariant is WSL2 + Docker Desktop. Rationale: the hook layer uses Bash scripts; a native Windows shell (PowerShell, cmd.exe) would require a separate hook layer implementation that is not warranted before a flow requires it.

## Relationship to existing ADRs

| ADR | Relationship |
|---|---|
| [ADR-048](ADR-048-docker-container-image-freshness.md) | **Extended.** ADR-048 governs optional service images; this ADR adds the `cos-worker` image under the same freshness policy. |
| [ADR-060](ADR-060-local-only-optional-services.md) | **Compatible.** Optional services remain optional; the `cos-worker` stack can run without them. |
| [ADR-064](ADR-064-harness-agnostic-cognitive-os.md) | **Enables.** The Compose stack is the delivery vehicle for ADR-064 coverage on CI-runner and cloud-worker harnesses. |
| [ADR-137](ADR-137-operational-trajectory-governance-layer-to-embedded-runtime.md) | **Implements prerequisite.** `bootstrap-portability.md` enforcement gate requires `cos-init` to work without `~/.claude/`; the Compose stack satisfies that gate for worker surfaces. |
| [ADR-141](ADR-141-engram-cloud-cross-instance-replication.md) | **Composes with.** The `cos-engram-proxy` sidecar described in ADR-141 is a Compose service defined alongside `cos-worker`. |

## Acceptance Criteria

1. `docker/cos-worker/docker-compose.yml` exists and `docker compose up` on a fresh Linux environment (no Python, no `~/.claude/`) starts the worker without error.
2. The worker container can run at least one hook (e.g., `git-commit-scope-guard.sh`) and write to `.cognitive-os/runtime/agent-audit-trail.jsonl` in the bind-mounted workspace.
3. No environment variable in the Compose file contains a vendor brand name (per ADR-139 §5). API keys use `LLM_PRIMARY_API_KEY` / `LLM_FALLBACK_API_KEY`.
4. `docs/architecture/bootstrap-portability.md` is updated to reflect that the Compose stack satisfies the `cos-init` portability gate for worker surfaces.

## Border Cases

- **A flow whose sandbox primitive (`e2b-integration`) provides its own container.** The Compose stack is not used; the flow's E2B container is its deployment unit. The flow contract declares the deploy target. No conflict.
- **The maintainer runs the Compose worker locally for testing.** Allowed; the stack is parameterised by env vars. The maintainer bind-mounts their local workspace. `credential_source: byok-maintainer` is acceptable in `lab` state per ADR-139.
- **macOS with Apple Silicon.** The base image (`python:3.11-slim`) ships multi-arch manifests. No `--platform` override required unless a flow introduces an amd64-only binary dependency.
- **CI runner without Docker.** The flow must declare its deploy target; if Docker is unavailable, the flow cannot use the Compose stack. The flow may fall back to `e2b-integration` or declare itself non-portable.

## Consequences

**Positive.**

- Cloud workers become launchable on any platform that runs Docker without assuming developer tooling. The `cos-cloud-worker-bootstrap.sh` entry point becomes a thin wrapper around `docker compose up`.
- The Compose stack is a natural test surface for ADR-064 (harness-agnostic) coverage: a container that boots COS and runs hooks verifies portability mechanically.
- Optional services remain optional; the flow's Compose profile declares what it needs.

**Negative / risk.**

- Docker is an additional operational dependency for cloud worker surfaces. Operators who cannot run Docker (some locked-down CI environments) cannot use the Compose path; they need a direct pip install in the container image.
- Windows WSL2 bind mounts have known latency characteristics on large workspaces. A flow with heavy file I/O should benchmark before committing to the Compose stack on Windows.

**Of not making this commitment.**

- Every cloud worker flow invents its own container setup. The first flow's container assumptions become the de-facto standard without being explicit. `bootstrap-portability.md` remains aspirational rather than gate-enforced.

## Cross-references

- [ADR-048](ADR-048-docker-container-image-freshness.md) — image freshness policy, extended here to `cos-worker`.
- [ADR-060](ADR-060-local-only-optional-services.md) — optional services; unchanged.
- [ADR-064](ADR-064-harness-agnostic-cognitive-os.md) — harness-agnostic implementation; Compose stack enables CI-runner coverage.
- [ADR-137](ADR-137-operational-trajectory-governance-layer-to-embedded-runtime.md) — trajectory commitment; Compose stack is the portability vehicle for Framing A worker surfaces.
- [ADR-139](ADR-139-account-agnostic-multi-provider-runtime.md) — credential posture; env var naming conventions apply to the Compose file.
- [ADR-141](ADR-141-engram-cloud-cross-instance-replication.md) — Engram cloud sidecar defined as a Compose service.
- [`dx-cloud-flow-bootstrap-plan.md`](../architecture/dx-cloud-flow-bootstrap-plan.md) — the plan whose `cos-cloud-worker-bootstrap.sh` entry point this ADR specifies.
- [`bootstrap-portability.md`](../architecture/bootstrap-portability.md) — portability gate; the Compose stack satisfies it for worker surfaces.
- [`cloud-worker-runtime-tooling-research-2026-05.md`](../architecture/cloud-worker-runtime-tooling-research-2026-05.md) — research baseline for Phase 1 no-broker constraint.

## Alternatives rejected

- Leave the ADR without an alternatives section — rejected because ADR-067+ audit contracts require a falsifiable record of considered options.

## Verification

```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
python3 -m pytest tests/audit/test_adr_140_cos_worker_compose.py -q
bash scripts/cos-cloud-worker-bootstrap.sh config
bash scripts/cos-cloud-worker-bootstrap.sh self-test
```

The `self-test` command requires Docker. It builds/runs the `cos-worker`
service, executes a harmless hook smoke through `hooks/git-commit-scope-guard.sh`,
and writes `.cognitive-os/runtime/agent-audit-trail.jsonl` in the bind-mounted
workspace.

## Implementation Evidence

- Implemented in `docker/cos-worker/docker-compose.yml`: the `cos-worker`
  service, account-agnostic provider key environment names, workspace bind
  mount, and optional `cos-engram-proxy` profile.
- Implemented in `docker/cos-worker/Dockerfile`: `python:3.11-slim` worker image
  with Bash/Git and no shell-profile dependency.
- Implemented in `docker/cos-worker/entrypoint.sh`: self-test boot path that
  runs a hook smoke and writes `agent-audit-trail.jsonl`.
- Implemented in `scripts/cos-cloud-worker-bootstrap.sh`: thin wrapper around
  Docker Compose for `config`, `self-test`, `up`, and `down`.
- Reflected in `docs/architecture/bootstrap-portability.md`: the Compose worker
  is the container-surface portability proof for ADR-140.
- Validated by `tests/audit/test_adr_140_cos_worker_compose.py`.
