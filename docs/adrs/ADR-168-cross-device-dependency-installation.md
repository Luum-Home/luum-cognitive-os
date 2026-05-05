---
adr: 168
title: Cross-Device Dependency Installation Contract
status: implemented
date: 2026-05-05
supersedes: []
superseded_by: null
implementation_files:
  - manifests/dependencies.yaml
  - docs/setup/cross-device-dependencies.md
  - scripts/cos-deps-install.sh
  - scripts/cos-doctor-tools.sh
  - scripts/manifest-check.sh
tier: maintainer
tags: [dependencies, installation, portability, cross-device, manifests]
---

# ADR-168: Cross-Device Dependency Installation Contract

## Status

**Implemented for the manifest-driven dry-run installer and credential-safe
reporting scope** — 2026-05-05. The current implementation provides
cross-platform dry-run JSON, conservative auth-bound/manual reporting, an apply
path for installable non-auth-bound dependencies, and loader support for
ADR-168 structured install metadata. Doctor convergence and legacy
`scripts/setup.sh` delegation remain incremental follow-up work.

## Context

Cognitive OS already has `manifests/dependencies.yaml`, `scripts/manifest-check.sh`,
`scripts/cos-doctor-tools.sh`, `scripts/setup.sh`, and several one-off installers
(`install-aguara.sh`, `install-mcp-scan.sh`, `install-promptfoo.sh`,
`install-garak.sh`, `install-obsidian-local.sh`). The dependency manifest is a
useful check inventory, but it is not yet a complete cross-device installation
contract.

The current installation surface is mixed:

- Python dependencies are mostly reproducible through `pyproject.toml` + `uv`.
- Docker services are portable when Docker is present.
- Host CLIs are installed through a mix of Homebrew, apt, curl, pip, npm, Go,
  vendor installers, and manual app installers.
- Authentication state and MCP/user configuration are host-local and must not be
  copied across machines.
- The new Obsidian helper is intentionally macOS/Homebrew-only.

External tooling confirms the right direction:

- Homebrew Bundle uses a declarative `Brewfile` state model and supports checks
  before install.
- Windows Package Manager supports JSON export/import for batch install.
- Nix flakes emphasize reproducible development environments through pinned
  inputs and outputs.
- asdf uses `.tool-versions` to make runtime versions project-declarative.

COS should not pick one package manager as the universal answer. It needs a
vendor-neutral dependency contract that can drive platform-specific installers,
doctors, and docs while keeping credentials and auth-bound tools explicit.

## Decision

Evolve `manifests/dependencies.yaml` into the source of truth for cross-device
dependency installation and verification.

The manifest contract must describe each dependency with:

- `name`
- `category` (`runtime`, `package-manager`, `cli`, `ai-cli`, `desktop-app`,
  `container`, `security`, `mcp`, `service`)
- `profiles` (`core`, `standard`, `full`, or maintainer-only profiles)
- `criticality` (`required`, `recommended`, `optional`)
- `scope` (`project`, `user`, `system`)
- `syncable` (`yes`, `no`, `state-only`, `config-only`)
- `auth_bound` boolean
- `check` command
- platform-specific install commands for `macos`, `linux`, and `windows_wsl`
- `manual_url` for dependencies that cannot be safely installed by script
- `never_copy` paths or state notes when credential material is involved

Add one operator-facing installer:

```bash
scripts/cos-deps-install.sh --profile core|standard|full --platform auto [--dry-run|--apply]
```

Required behavior:

1. Detect platform (`macos`, `linux`, `windows_wsl`) when `--platform auto`.
2. Read only `manifests/dependencies.yaml` for dependency metadata.
3. Dry-run by default.
4. Install only dependencies with a platform command and no credential/auth
   boundary.
5. Report manual/auth-bound dependencies with exact docs links.
6. Never copy, read, or infer credentials from another device.
7. Emit a machine-readable JSON report for `cos-status`, `cos-doctor-tools`, and
   future ACC evidence.

Docs must include `docs/setup/cross-device-dependencies.md`, explaining:

- what travels through git, Docker, Engram sync/cloud, or package manifests;
- what must be installed per machine;
- which dependencies are auth-bound/manual;
- how to bootstrap macOS, Linux, and Windows/WSL without pretending all tools are
  equally portable.

## Consequences

### Positive

- Dependency installation becomes auditable instead of scattered across prose and
  ad hoc scripts.
- New machines can reproduce the portable part of the SO setup from one command.
- Doctors and installers stop disagreeing because they share the same manifest.
- Auth-bound tools are visible without unsafe credential migration.
- Platform-specific installer work can advance incrementally.

### Negative

- The manifest schema becomes larger and needs validation tests.
- Existing scripts must be migrated or wrapped instead of duplicated.
- Some dependencies remain manual by design, so "one command installs
  everything" remains an invalid claim.
- Windows/WSL support needs explicit proof rather than being inferred from Linux
  commands.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Keep `scripts/setup.sh` as the only installer | It hardcodes commands and cannot express syncability, auth boundaries, or platform-specific/manual states clearly. |
| Add more one-off installers | Increases drift and makes new-device bootstrap harder to reason about. |
| Adopt Homebrew Bundle as the universal source | Good macOS pattern, but it does not cover Linux/WSL, auth-bound CLIs, project Python deps, or Docker services. |
| Adopt Nix flakes for everything now | Strong reproducibility, but high adoption cost and not aligned with existing Homebrew/uv/Docker workflows. Could become an optional backend later. |
| Copy user config and credentials between devices | Violates credential-boundary decisions and risks leaking provider tokens, MCP auth, browser state, or Keychain material. |

## Implementation plan

1. **Audit and docs** — create `docs/setup/cross-device-dependencies.md` with the
   current surface inventory and target contract.
2. **Schema v2** — extend `manifests/dependencies.yaml` and
   `lib/manifest_loader.py` to validate platform install targets, `scope`,
   `syncable`, and `auth_bound`.
3. **Installer** — add `scripts/cos-deps-install.sh` backed by a Python module,
   dry-run by default.
4. **Doctor convergence** — update `scripts/manifest-check.sh` and
   `scripts/cos-doctor-tools.sh` to consume the v2 fields.
5. **Retire wrappers gradually** — keep one-off installers as implementation
   helpers only when the manifest delegates to them.
6. **Proof** — add unit/contract tests for manifest validation, platform
   detection, dry-run output, and no-credential-copy invariants.

## Acceptance criteria

1. `manifests/dependencies.yaml` validates with platform install metadata for all
   required/core dependencies.
2. `scripts/cos-deps-install.sh --profile core --dry-run --json` exits 0 on
   macOS, Linux, and Windows/WSL test hosts or fixtures.
3. `scripts/cos-deps-install.sh --profile core --apply` installs only portable,
   non-auth-bound dependencies for the detected platform.
4. Auth-bound tools report manual instructions and never read/copy credential
   paths.
5. `docs/setup/cross-device-dependencies.md` lists git/Docker/Engram/package
   manifest/manual boundaries.
6. `scripts/setup.sh` either delegates to the new installer or is documented as a
   legacy wrapper.

## Verification

Initial documentation/ADR slice:

```bash
python3 -m pytest tests/unit/test_manifest_loader.py tests/integration/test_install_manifest_integration.py -q
bash scripts/manifest-check.sh --profile default || true
```

Implemented installer slice:

```bash
python3 -m pytest tests/unit/test_manifest_loader.py tests/contracts/test_cross_device_dependencies.py -q
scripts/cos-deps-install.sh --profile core --dry-run --json
```

Implemented schema and automation-adjacent slice:

```bash
python3 -m pytest \
  tests/unit/test_manifest_loader.py \
  tests/contracts/test_cross_device_dependencies.py \
  tests/behavior/test_engram_obsidian_export_hook.py \
  -q
bash -n scripts/cos-deps-install.sh hooks/engram-obsidian-export-on-stop.sh
scripts/cos-deps-install.sh --profile core --platform macos --dry-run --json
```

Current implementation evidence:

- `manifests/dependencies.yaml` carries `category`, `profiles`, `scope`,
  `syncable`, `auth_bound`, platform install metadata, and `never_copy` where
  credential state exists.
- `lib/manifest_loader.py` validates those fields while still accepting legacy
  string install entries during migration.
- `scripts/cos_deps_install.py` emits JSON buckets for `already_present`,
  `installable`, `manual`, `auth_bound`, `unsupported_platform`, `installed`,
  and `failed`.
- `tests/contracts/test_cross_device_dependencies.py` enforces the no-credential
  copy invariant and the presence of cross-platform metadata for core tools.
