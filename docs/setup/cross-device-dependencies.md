# Cross-Device Dependency Installation

**Purpose**: define how Cognitive OS dependencies should be installed and
verified across developer devices without copying credentials or pretending every
tool is equally portable.

This document backs ADR-168.

## Acceptance criteria

1. Inventory current dependency declarations, docs, scripts, and tool-specific
   installers.
2. Identify which dependency state travels across devices and which state is
   host-local.
3. Define the target `manifests/dependencies.yaml` schema extension.
4. Define the target `scripts/cos-deps-install.sh` behavior.
5. Preserve the no-credentials-copy invariant.

---

## Current repo surfaces audited

| Surface | Current role | Cross-device gap |
|---|---|---|
| `manifests/dependencies.yaml` | Declares Python groups, tools, MCP servers, and profiles for checks. | Does not yet encode `scope`, `syncable`, `auth_bound`, or full platform install targets. |
| `lib/manifest_loader.py` | Validates current manifest keys and profile references. | Rejects unknown fields, so schema v2 needs coordinated loader/test updates. |
| `scripts/manifest-check.sh` | Reports required/recommended dependency status after install. | Check/report only; does not install. |
| `scripts/cos-doctor-tools.sh` | Doctor around manifest-declared tools and MCP registrations. | Needs richer fields to distinguish missing portable deps from manual/auth-bound deps. |
| `scripts/setup.sh` | Imperative development setup using brew/apt/curl/uv/go/pip/npm. | Hardcoded commands; not a manifest-driven cross-device installer. |
| `scripts/cos-bootstrap.sh` | Starts optional Docker services and performs self-install sync. | Docker part is portable; host prerequisites are assumed. |
| `scripts/install-*.sh` | One-off installers for specific tools. | Useful helpers, but drift without manifest ownership. |
| `docs/setup/dependencies.md` | Human dependency guide. | Claims single source of truth but still mixes install commands in prose. |
| `docs/setup/obsidian-local.md` | macOS/Homebrew Obsidian install guide. | Explicitly not cross-platform yet. |
| `docs/manual-tests/codex-host-tooling-verification.md` | Host-tooling proof path for Codex. | Verifies local host, not cross-device installation. |

---

## What travels across devices

| State | Travels? | Mechanism | Notes |
|---|---:|---|---|
| Source code | Yes | Git | Includes manifests, docs, scripts, tests. |
| Python dependency intent | Yes | `pyproject.toml`, lock files when present | Actual venv is per-device. |
| Go dependency intent | Yes | `go.mod`, `.go-version` | Toolchain install is per-device. |
| Docker service definitions | Yes | Compose files / Dockerfiles | Images/volumes are per-device unless pushed/pulled. |
| Engram memories | Partial | Engram sync/cloud/export | Replicates memory data, not installed binaries or host auth. |
| Obsidian vault content | Optional | User-chosen sync/git/cloud storage | Vault path and app install are per-device. |
| MCP server declarations | Partial | Project/user config projection | User auth/config remains per-device. |
| Provider credentials | No | Must be re-authenticated per device | Never copy Keychain, browser cookies, `~/.codex`, `~/.claude`, `.env`, keys, or token stores. |
| Desktop apps | No | Package manager or manual install per device | Obsidian, Docker Desktop, IDEs. |
| Global CLIs | No | Package manager per device | `jq`, `gh`, `semgrep`, `engram`, etc. |

---

## Current dependency classes

### Portable by manifest/package manager

| Dependency | Current declaration | Desired install owner |
|---|---|---|
| Python runtime + packages | `pyproject.toml`, `manifests/dependencies.yaml` Python groups | `uv` + manifest profile. |
| Go version | `.go-version`, `go.mod` | manifest points to `goenv`, asdf, or manual platform path. |
| Docker services | Dockerfiles/compose + docs | Docker prerequisite in manifest; service startup remains `cos-bootstrap.sh`. |

### Host CLI dependencies

| Tool | Current install source | Cross-device note |
|---|---|---|
| `jq` | brew / apt | Portable command, per-device install. |
| `git` | system / brew / apt | Portable command, per-device install. |
| `uv` | brew / curl installer | Portable command, per-device install. |
| `gh` | brew / apt | Auth-bound after install; do not copy `gh` auth state. |
| `engram` | docs currently mention npm/upstream; local machine uses Homebrew binary | Install is portable; memory DB/sync state is separate. |
| `semgrep` | brew / pip | Optional, per-device install. |
| `aguara`, `mcp-aguara` | `go install` | Optional, per-device install. |
| `mcp-scan` | pip | Optional, per-device install. |
| `promptfoo` | npm global | Optional, per-device install. |
| `garak` | pip | Heavy optional dependency; should remain opt-in. |
| `parry-guard` | brew tap | macOS path only in current docs. |

### Desktop/manual dependencies

| Tool | Current install source | Cross-device note |
|---|---|---|
| Obsidian | `scripts/install-obsidian-local.sh` via Homebrew Cask | macOS-only helper today; vault path is explicit and per-device. |
| Docker Desktop | vendor install | Manual/app install per device. |
| Claude Code / Codex / IDE agents | vendor/npm/IDE install | Auth-bound and per-device. |

---

## Target manifest schema

`manifests/dependencies.yaml` should remain the source of truth, but evolve from
check inventory into install contract.

Illustrative schema:

```yaml
tools:
  - name: jq
    category: cli
    criticality: required
    profiles: [core, standard, full]
    scope: system
    syncable: no
    auth_bound: false
    check: jq --version
    install:
      macos:
        manager: brew
        command: brew install jq
      linux:
        manager: apt
        command: sudo apt-get install -y jq
      windows_wsl:
        manager: apt
        command: sudo apt-get install -y jq
    consumed_by:
      - hooks/*.sh

  - name: gh
    category: cli
    criticality: recommended
    profiles: [standard, full]
    scope: user
    syncable: config-only
    auth_bound: true
    check: gh --version
    install:
      macos:
        manager: brew
        command: brew install gh
      linux:
        manager: apt
        command: sudo apt-get install -y gh
      windows_wsl:
        manager: manual
        url: https://cli.github.com/
    never_copy:
      - ~/.config/gh
    post_install: authenticate manually with `gh auth login`
```

Required field semantics:

| Field | Meaning |
|---|---|
| `profiles` | Which SO dependency profile includes the tool. |
| `scope` | Where installed state lives: `project`, `user`, or `system`. |
| `syncable` | Whether state can travel: `yes`, `no`, `state-only`, `config-only`. |
| `auth_bound` | Whether use requires per-device login/token material. |
| `install.<platform>` | Platform-specific command or manual URL. |
| `never_copy` | Paths/state that must never be migrated across devices. |

---

## Target installer behavior

Command:

```bash
scripts/cos-deps-install.sh --profile core|standard|full --platform auto [--dry-run|--apply] [--json]
```

Rules:

1. `--dry-run` is default.
2. `--platform auto` detects `macos`, `linux`, or `windows_wsl`.
3. `--apply` installs only dependencies with safe platform commands and
   `auth_bound: false`.
4. Auth-bound dependencies are reported with manual follow-up, never installed
   with copied credentials.
5. Dependencies with `manager: manual` are reported, not installed.
6. The installer emits JSON with `installed`, `already_present`, `manual`,
   `auth_bound`, `unsupported_platform`, and `failed` buckets.
7. It never reads `.env`, key files, browser stores, Keychain, `~/.codex`,
   `~/.claude`, or provider credential directories.

---

## External tooling patterns

| Tooling | Useful pattern | COS implication |
|---|---|---|
| Homebrew Bundle / Brewfile | Declarative desired state plus `brew bundle check`. | Good macOS backend, not universal source of truth. |
| winget export/import | JSON package lists for batch restore. | Useful Windows backend; still needs auth/manual classification. |
| Nix flakes | Reproducible dev environments with pinned inputs. | Possible future optional backend for core dev env, not mandatory now. |
| asdf `.tool-versions` | Project-declared runtime versions. | Useful for Python/Go/Node runtime convergence, but not desktop apps/MCP auth. |
| Docker / devcontainers | Portable services and isolated runtime. | Strong for services, not replacement for host IDE/CLI/auth installation. |

Sources:

- Homebrew Bundle docs: https://docs.brew.sh/Brew-Bundle-and-Brewfile
- winget export docs: https://learn.microsoft.com/en-us/windows/package-manager/winget/export
- Nix flakes docs: https://nix.dev/concepts/flakes.html
- asdf version docs: https://asdf-vm.com/manage/versions.html

---

## Migration plan

1. Add schema v2 tests around `lib/manifest_loader.py` before changing the
   manifest.
2. Add `scope`, `syncable`, `auth_bound`, and platform install metadata for core
   tools first: `git`, `jq`, `uv`, `python3`.
3. Add `scripts/cos-deps-install.sh` as dry-run/report-only.
4. Turn on `--apply` for safe non-auth-bound core tools.
5. Migrate `scripts/setup.sh` to call the new installer or mark it as legacy.
6. Gradually register optional/security/desktop tools.
7. Add manual proof paths for macOS, Linux, and Windows/WSL.

---

## Non-goals

- Do not promise one-command installation of every dependency.
- Do not copy credentials or app state across machines.
- Do not require Nix or Homebrew on every platform.
- Do not make optional heavy/security tools part of the core profile.
- Do not run provider login flows automatically.
