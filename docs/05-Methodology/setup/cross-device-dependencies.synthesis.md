---
type: methodology-synthesis
source: docs/05-Methodology/setup/cross-device-dependencies.md
provenance: "ADR-168 design/status document defining how Cognitive OS dependencies should be installed and verified across developer devices without copying credentials or claiming every tool is equally portable."
---

## What it is

A design-and-status document (backing ADR-168) that audits current dependency-management surfaces, classifies what installed state can and cannot travel across devices, defines a target `manifests/dependencies.yaml` schema extension, and specifies the target behavior of `scripts/cos-deps-install.sh`.

## Key mechanics

- Audits nine existing surfaces (`manifests/dependencies.yaml`, `lib/manifest_loader.py`, `scripts/manifest-check.sh`, `scripts/cos-doctor-tools.sh`, `scripts/setup.sh`, `scripts/cos-bootstrap.sh`, `scripts/install-*.sh`, and the dependencies/Obsidian setup docs) against their cross-device gaps — e.g. `setup.sh` is a hardcoded imperative installer, not manifest-driven.
- "What travels" table: source code, Python/Go dependency *intent* (lockfiles/`.go-version`), and Docker service definitions travel via git; Engram memories and MCP server declarations travel partially; provider credentials, desktop apps, and global CLIs never travel and must be reinstalled/reauthenticated per device (explicitly: never copy Keychain, browser cookies, `~/.codex`, `~/.claude`, `.env`, keys, or token stores).
- Target schema extends `manifests/dependencies.yaml` entries with `scope` (project/user/system), `syncable` (yes/no/state-only/config-only), `auth_bound` (bool), per-platform `install.<platform>` commands, and `never_copy` paths — illustrated with `jq` (non-auth-bound) and `gh` (auth-bound, `never_copy: ~/.config/gh`) examples.
- Target installer `scripts/cos-deps-install.sh --profile core|standard|full --platform auto [--dry-run|--apply] [--json]`: dry-run by default, auto-detects macOS/Linux/Windows-WSL2, `--apply` only installs safe non-auth-bound rows, auth-bound deps are reported with manual follow-up never auto-installed, `manager: manual` rows are reported only, output buckets are `installed`/`already_present`/`manual`/`auth_bound`/`unsupported_platform`/`failed`, and the installer never reads `.env`, key files, browser stores, Keychain, or provider credential directories.
- Surveys five external tooling patterns for useful backend ideas (Homebrew Bundle, winget export/import, Nix flakes, asdf `.tool-versions`, Docker/devcontainers) without adopting any as mandatory.
- Migration plan lists 7 steps with explicit status markers: 4 marked "Done" (schema tests, `scope`/`syncable`/`auth_bound` metadata for `git`/`jq`/`uv`/`python3`, dry-run-by-default JSON installer, `--apply` restricted to safe rows), 1 "In progress" (optional/security tool metadata), 2 "Pending" (`setup.sh` migration to the new installer, manual Linux/Windows proof paths).
- Non-goals: no promise of one-command installation for everything, no credential/app-state copying, no mandatory Nix/Homebrew, no automatic provider login flows, and heavy/security tools stay out of the core profile.
- An ADR-309 update (dated 2026-05-14) extends the installer to `cos-deps-install.v2` reports with explicit headless/service bootstrap targets (`macos`, `linux`, `windows_wsl`, `windows`, with Linux distro keys like `debian`/`fedora`/`arch`/`alpine`) and six named profiles: `core`/`default`, `dev`, `ci`, `services`, `security`, `headless-instance`, `full`. Git hooks remain advisory-only and must never auto-install tools during push/pull/rebase.

## Relations & where used

Backs ADR-168 and is extended by ADR-309; references `lib/manifest_loader.py`, `scripts/cos-deps-install.sh`, `scripts/cos-doctor-tools.sh`, and the sibling `dependencies.md` and `obsidian-local.md` setup docs.

## Status / caveats

This is a living design document with an explicit progress ledger (Done/In progress/Pending as of the migration-plan section) — read the "Done" claims as accurate for their stated scope only (four core tools), not as full coverage of the dependency inventory. The ADR-309 update section is a dated addendum (2026-05-14) layered onto the original ADR-168 content; treat profile names and v2 report format as the current state superseding the earlier `--profile core|standard|full` framing shown in the "Target installer behavior" section above it.
