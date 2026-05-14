---
status: Accepted
date: 2026-05-14
deciders: Cognitive OS maintainers
tags:
  - dependencies
  - installer
  - portability
  - headless
  - standalone
implementation_status: Implemented
---

# ADR-310: Cross-Platform and Headless Dependency Bootstrap

## Status

Accepted


## Context

ADR-168 created the dependency installation contract and ADR-308 made dependency drift visible during install, update, push, and pull. That still left a product gap: Cognitive OS is not only used on one maintainer Mac. It must be bootstrapable on multiple developer machines and in standalone/headless instances such as CI runners, service workers, Docker hosts, VM instances, or future `cosd` deployments.

The previous state was partial:

- `scripts/cos-deps-install.sh` could report/install a small core/default set.
- `scripts/setup.sh` still installed many tools imperatively and only reported dependency drift.
- `scripts/cos-update.sh` reported dependency drift but did not attempt portable dependency convergence.
- `manifests/dependencies.yaml` did not model the full high-signal tool classes found by the dependency coverage audit: toolchains, quality/CI tools, SBOM/security tools, service tools, harness tools, and OS primitives.
- Windows native, Linux distro variance, WSL, and headless/service instances were not first-class in the installer contract.

## Decision

Promote dependency bootstrap from a macOS-biased partial installer into a manifest-driven cross-platform/headless contract.

The installer contract is now `cos-deps-install.v2` and supports:

- platform reports for `macos`, `linux`, `windows_wsl`, and `windows`;
- runtime context metadata for container/headless/root/sudo/package-manager detection;
- profiles for `dev`, `ci`, `services`, `security`, `headless-instance`, `full`, and `rust-transpiler-lab` in addition to `default/core`;
- Python group planning for selected profiles;
- platform-builtin classification for OS primitives such as `flock`, `pgrep`, `timeout`, checksums, and terminal helpers;
- auth-bound/manual reporting for tools that require per-device login or cannot be safely scripted;
- explicit `git_hook_policy: advisory-only-no-auto-install` in reports.

Explicit install/update commands may install portable, non-auth-bound tools:

- `scripts/setup.sh` delegates to `scripts/cos-deps-install.sh --apply` using a profile mapped from `--minimal|--standard|--full`.
- `scripts/cos-update.sh` runs the same installer during explicit updates, with `COS_DEPS_UPDATE_PROFILE` and `COS_DEPS_UPDATE_INSTALL=0` as operator controls.

Git-triggered flows remain advisory-only:

- `pre-push`, `post-merge`, and `post-rewrite` run dependency maintenance reports but do not install tools.
- This prevents a `git pull` or `git push` from mutating an operator machine without explicit setup/update intent.

## Profiles

| Profile | Purpose |
|---|---|
| `core` / `default` | Minimal portable tools required for COS scripts. |
| `dev` | Developer workstation: core + toolchains + quality tools + auth-bound AI CLIs as manual/login-bound. |
| `ci` | Non-interactive validation runner: toolchains, shellcheck, pytest, link/style tools, OS primitives. |
| `services` | Local services and integration dependencies: Docker, Redis/Valkey/Postgres helpers, tmux. |
| `security` | SBOM/scanner/sandbox tools: Semgrep, Syft, Grype, Trivy, bubblewrap/sandbox primitives. |
| `headless-instance` | Standalone SO instance profile for CI/VM/service hosts without desktop/auth-bound requirements. |
| `full` | Superset for maintainers/lab machines. |
| `rust-transpiler-lab` | Lab-only Rust transpiler tooling. |

## Safety invariants

1. The installer never reads or copies credentials, `.env`, key files, browser stores, Keychain, `~/.codex`, `~/.claude`, `gh` auth, or provider token stores.
2. Auth-bound tools can be installed only as binaries when safe, but login state is always manual per device.
3. Desktop/manual tools remain reported, not silently installed.
4. Git hooks are advisory-only and must not invoke `--apply`.
5. Explicit setup/update commands may install only manifest-declared, non-auth-bound, non-manual dependencies for the selected platform/profile.
6. Headless instances use `headless-instance` instead of inheriting desktop or AI-login tooling from developer machines.

## Consequences

- The decision is now part of the governed Cognitive OS primitive surface and must stay aligned with implementation, tests, and runtime projection metadata.

## Alternatives rejected

- **Leave the behavior as implicit agent instruction only.** Rejected because this ADR records a runtime/authoring contract that needs durable tests or audits rather than conversation-only memory.

## Verification

- `bash -n scripts/setup.sh scripts/cos-update.sh scripts/cos-deps-install.sh`
- `python3 scripts/cos_deps_install.py --profile headless-instance --platform linux --dry-run --json`
- `.venv/bin/python -m pytest tests/contracts/test_cross_device_dependencies.py tests/unit/test_manifest_loader.py -q`



```bash
python3 -m pytest tests/unit -q
```
## Coverage result

After the manifest/profile expansion and coverage-audit parser fixes, `scripts/cos-deps-maintain --mode doctor --no-install-plan --json` reports no `missing_from_manifest` and no `optional_lane_needed` findings. The only remaining actionable finding is the intentional `blocked_or_removed_by_policy` row for `litellm`, which is governed by the external-tool adoption policy rather than installed by the bootstrapper.
