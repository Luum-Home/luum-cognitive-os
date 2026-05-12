---

adr: 163
title: Cognitive OS Instance Installer
status: accepted
implementation_status: partial
classification_basis: 'first implementation slice supports local/docker-headless profiles; future profiles remain planned/write-blocked'
date: 2026-05-05
supersedes: []
superseded_by: null
implementation_files:
  - manifests/cos-instance-profiles.yaml
  - scripts/cos-instance-init
  - scripts/cos_instance_init.py
  - docs/04-Concepts/architecture/cos-instance-installer.md
  - docs/09-Quality/manual-tests/cos-instance-installer.md
  - tests/contracts/test_cos_instance_profiles.py
tier: maintainer
tags: [instance-installer, headless-runtime, docker, cosd, service-control-plane, portability]
partial_remaining: first implementation slice supports local/docker-headless profiles; future profiles remain planned/write-blocked
partial_remaining_basis: specific classification_basis
---

# ADR-163: Cognitive OS Instance Installer

## Status

**Accepted** — 2026-05-05

## Context

Cognitive OS already has a consumer-project installer/projection path through
`scripts/cos_init.py`. That installer projects hooks, rules, skills, and harness
configuration into repositories that consume the SO.

The headless/runtime work exposed a second installation need: constructing an
**operational COS instance**. This is not the same as installing COS primitives
into a consumer project. An instance may run locally, in Docker/headless mode,
through a future host CLI bridge, on a VM/EC2 host, or as Kubernetes worker pods.

The idea was already distributed across ADR-091, ADR-139, ADR-140, ADR-161,
ADR-162, and the service-control-plane architecture docs: Cognitive OS is not an
IDE plugin. It is an agent governance/runtime layer with multiple frontends:
IDE, CLI local, shell/CI, Docker service, remote ingress, VM, and pod workers.

## Decision

Add a dedicated COS instance installer contract and first implementation slice:

- `manifests/cos-instance-profiles.yaml` declares instance profiles and proof
  levels;
- `scripts/cos-instance-init` is the operator-facing command;
- `scripts/cos_instance_init.py` implements dry-run and safe write behavior;
- `docs/04-Concepts/architecture/cos-instance-installer.md` explains the boundary;
- `docs/09-Quality/manual-tests/cos-instance-installer.md` records the manual proof path;
- `tests/contracts/test_cos_instance_profiles.py` verifies the manifest and
  installer behavior.

The installer starts with two implemented profiles:

| Profile | Purpose | Proof boundary |
|---|---|---|
| `local` | Maintainer-host COS instance for IDE/CLI/shell use. | Contract/write proof, host auth probes optional. |
| `docker-headless` | Local Docker worker instance for non-IDE queue/lease/artifact execution. | Docker smoke proof through `scripts/cos-headless-service-drill`. |

Future profiles are declared but write-blocked until proof exists:

- `host-cli-bridge`
- `vm`
- `k8s`

The instance installer must not copy or read provider credential stores. It may
prepare metadata, directories, commands, and smoke instructions. Provider calls
remain disabled unless an explicit auth probe, cost/approval gate, and runtime
proof permit them.

## Consequences

### Positive

- Consumer-project projection and SO-instance provisioning no longer compete in
  the same installer.
- The Docker/headless proof becomes repeatable from a named instance profile.
- Future VM/pod/host-bridge work has a stable profile taxonomy before code is
  added.
- Existing IDE workflows remain valid because `local` is one profile, not a
  deprecated path.

### Negative

- There is another operator command to document and maintain.
- The first implementation writes metadata and commands, not a full daemon.
- Planned profiles may look real unless their `planned`/write-blocked status is
  enforced by tests.

## Operational Guide

### What changes for the operator

Before this ADR, `scripts/cos_init.py` handled both consumer-project projection and any ad-hoc SO instance setup, with no governed distinction between the two. After this ADR:

- `scripts/cos-instance-init` is the dedicated operator-facing command for provisioning a COS operational instance (separate from consumer-project projection via `cos_init.py`).
- `manifests/cos-instance-profiles.yaml` is the source of truth for instance profiles, proof levels, and write-blocked status.
- Two profiles are implemented: `local` (maintainer-host IDE/CLI/shell instance) and `docker-headless` (Docker worker instance).
- Three future profiles (`host-cli-bridge`, `vm`, `k8s`) are declared but write-blocked until proof exists — the contract tests enforce this.
- Instance metadata is written into `.cognitive-os/instances/<profile>/`.
- The installer never copies or reads provider credential stores.

### What this answers (and what it doesn't)

**Answers:**
- "How do I set up a local COS instance?" — `scripts/cos-instance-init --profile local --write --json`.
- "How do I set up a Docker/headless worker instance?" — `scripts/cos-instance-init --profile docker-headless --write --json`; the Docker smoke is accessible via `scripts/cos-headless-service-drill`.
- "Are planned profiles safe to run?" — `--dry-run` shows what would be written but blocks writes for planned/write-blocked profiles.

**Does not answer:**
- Whether provider calls are available in an instance — provider calls remain disabled unless an explicit auth probe, cost/approval gate, and runtime proof permit them. The installer prepares metadata and commands only.
- Whether `host-cli-bridge`, `vm`, or `k8s` instances are ready to use — those profiles are write-blocked pending proof.

### Daily operational pattern

1. New maintainer or CI environment: `scripts/cos-instance-init --profile local --dry-run --json` to preview.
2. If preview looks correct: `scripts/cos-instance-init --profile local --write --json`.
3. For Docker/headless work: use `--profile docker-headless`; validate with `scripts/cos-headless-service-drill`.
4. Check `manifests/cos-instance-profiles.yaml` before adding a new profile — any new profile needs proof level documentation and tests before gaining write access.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Extend `cos_init.py` to also provision SO instances | Blurs consumer-project projection with operational runtime provisioning. |
| Make Docker/headless the only supported path | Would break or devalue the current IDE/CLI workflow. |
| Wait until Kubernetes exists before defining profiles | Delays local/Docker proof and lets ad-hoc installation semantics spread. |
| Mount host Codex/Claude credential stores into Docker by default | Violates ADR-161 no-credential-scraping boundary. |
| Treat provider smoke as part of default instance init | Provider calls are cost-bearing/account-backed and must stay explicit. |

## Verification

```bash
python3 -m pytest tests/contracts/test_cos_instance_profiles.py -q
scripts/cos-instance-init --profile local --dry-run --json
scripts/cos-instance-init --profile docker-headless --dry-run --json
```

## Implementation Evidence

- `manifests/cos-instance-profiles.yaml` separates `scripts/cos_init.py` from
  `scripts/cos-instance-init` ownership.
- `scripts/cos-instance-init --profile local --write --json` writes local
  instance metadata into `.cognitive-os/instances/local/`.
- `scripts/cos-instance-init --profile docker-headless --write --json` writes
  Docker/headless instance metadata into `.cognitive-os/instances/docker-headless/`.
- Planned profiles are dry-run visible but write-blocked.
