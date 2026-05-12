# COS Instance Installer

## Purpose

Cognitive OS now has two installation concerns that must remain separate:

| Installer | Command | Owns | Does not own |
|---|---|---|---|
| Consumer-project projection | `scripts/cos_init.py` | Project-local hooks, rules, skills, harness files, profiles | Operational SO runtime, Docker workers, host CLI bridge, VM/pod deployment |
| COS instance provisioning | `scripts/cos-instance-init` | Runtime instance metadata, local/headless directories, Docker worker readiness, future VM/pod/bridge profiles | Consumer project projection or provider credential stores |

The product statement is:

> Cognitive OS is not an IDE plugin. It is an agent governance/runtime layer with
> multiple frontends: IDE, CLI local, shell/CI, Docker service, remote ingress,
> VM, and pod workers.

## Evidence lineage

The idea was already present but distributed:

- `docs/adrs/ADR-091-headless-clustered-runtime-direction.md` — canonical local
  harness runtime vs headless runtime taxonomy.
- `docs/architecture/cos-service-runtime-boundary.md` — separates IDE/harness
  embedded execution from the future `cosd` service boundary.
- `docs/architecture/service-control-plane-research-2026-05-04.md` — asks how
  COS grows from IDE/harness worker surface into a service outside an IDE.
- `docs/architecture/service-control-plane-implementation-plan.md` — phases
  `cosd`, queue, leases, workers, provider adapters, artifacts, propose-only
  output.
- `docs/adrs/ADR-139-account-agnostic-multi-provider-runtime.md` — prevents
  binding runtime to one IDE, provider, or account model.
- `docs/adrs/ADR-140-cross-os-containerized-deployment.md` — container worker
  base.
- `docs/adrs/ADR-161-remote-control-plane-and-provider-adapter-boundary.md` —
  remote ingress vs provider/executor adapters and no credential scraping.
- `docs/adrs/ADR-162-task-lifecycle-interruption-question-worktree-pr-protocol.md`
  — task lifecycle, interruptions, questions, worktrees, branches, PRs.
- `docs/manual-tests/headless-docker-service-runtime.md` — first explicit Docker
  service proof that coexists with IDE workflows.

## Profiles

Profiles live in `manifests/cos-instance-profiles.yaml`.

### `local`

For the current maintainer-host workflow: IDEs, CLI local, shell/CI, optional
host auth probes. This preserves the way COS is used today.

### `docker-headless`

For a local Docker worker that executes queue/lease/artifact tasks without an
IDE. This profile points at `scripts/cos-headless-service-drill` for smoke
proof.

### `host-cli-bridge`

Planned. This is the future bridge where a Docker/service runtime can ask the
host to run official CLIs such as Codex or Claude Code without mounting or
reading credential stores. It needs loopback/socket auth, command allowlists,
redaction, cost gates, and human approval.

### `vm`

Planned. This is the EC2/VPS/single-node deployment shape.

### `k8s`

Planned. This is the worker-pod deployment shape with namespace, external
secrets/provider-cloud auth, queue backend, artifacts, and probes.

## Operator commands

Dry-run is safe and default when `--write` is absent:

```bash
scripts/cos-instance-init --profile local --dry-run --json
scripts/cos-instance-init --profile docker-headless --dry-run --json
```

Write metadata for implemented profiles:

```bash
scripts/cos-instance-init --profile local --write --json
scripts/cos-instance-init --profile docker-headless --write --json
```

Run Docker smoke separately:

```bash
scripts/cos-headless-service-drill --json
```

## Boundary rules

- Do not copy `~/.codex/auth.json`.
- Do not copy `~/.claude`.
- Do not read Keychain or browser cookies.
- Do not mount opaque host credential directories into containers by default.
- Do not direct-push or merge from an instance worker without human/merge-queue
  approval.
- Do not turn provider smoke into default init behavior.
