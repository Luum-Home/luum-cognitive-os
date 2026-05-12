---

adr: 163
title: Cognitive OS Instance Installer
status: accepted
implementation_status: partial
date: 2026-05-05
supersedes: []
superseded_by: null
implementation_files:
  - manifests/cos-instance-profiles.yaml
  - scripts/cos-instance-init
  - scripts/cos_instance_init.py
  - docs/architecture/cos-instance-installer.md
  - docs/manual-tests/cos-instance-installer.md
  - tests/contracts/test_cos_instance_profiles.py
tier: maintainer
tags: [instance-installer, headless-runtime, docker, cosd, service-control-plane, portability]
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
- `docs/architecture/cos-instance-installer.md` explains the boundary;
- `docs/manual-tests/cos-instance-installer.md` records the manual proof path;
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
