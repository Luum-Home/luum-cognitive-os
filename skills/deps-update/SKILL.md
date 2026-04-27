<!-- SCOPE: os-only -->
---
name: deps-update
command: /deps-update
description: Audit and optionally upgrade project dependencies — Python, engram binary, Claude Code plugins, Docker images
version: 0.1.0
audience: os-dev
scope: os-only
tags: [maintenance, dependencies, audit, upgrade]
last-updated: 2026-04-24
effort: haiku
script: scripts/deps-update.sh
---

# Deps Update

## Purpose

Keep all luum-cognitive-os dependencies current between releases. Covers four dimensions:

1. **Python packages** (pyproject.toml / uv) — minor and patch upgrades automated; major bumps require opt-in.
2. **engram binary** — compares installed version against the latest GitHub release; upgrades via `go install` with the GOPATH versioned-bin workaround.
3. **Claude Code plugins** — read-only inventory with upstream version check; actual upgrade is manual via Claude Code UI.
4. **Docker images** — digest freshness check; `docker pull` in apply mode; compose file pinning is never modified automatically.

## Input

```
/deps-update [--audit|--apply|--apply-major]
```

| Flag | Behaviour |
|---|---|
| `--audit` (default) | Read-only report. Exit 0 always. |
| `--apply` | Upgrade Python minor/patch + engram binary if newer. Plugins and Docker are info-only. |
| `--apply-major` | Same as `--apply` but also applies Python major version bumps (`uv sync --upgrade`). |
| `--dry-run` | Print the commands that `--apply` would run without executing them. |

## Output

```
=== Deps Update Summary ===
  Python:   3 upgraded (minor/patch), 2 skipped (major — use --apply --major)
  engram:   dev → 1.13.1  applied
  Plugins:  0 of 4 need upgrade (manual via Claude Code UI)
  Docker:   1 image(s) may have newer digest (manual review)
```

## When to Use

- Before a release to verify nothing is dangerously stale
- After a security advisory mentions a Python or Go dependency
- Weekly maintenance pass (`/deps-update --audit`)
- After `engram` publishes a new release
- User says `/deps-update`

## Process

### Step 1: Run the audit

```bash
bash scripts/deps-update.sh --audit
```

Review the output table. Identify any MAJOR bumps that need manual review.

### Step 2: Apply safe upgrades (optional)

```bash
bash scripts/deps-update.sh --apply
```

This upgrades Python minor/patch packages via `uv sync --upgrade-package <name>` for each non-major bump, and installs the latest engram binary via `go install`.

### Step 3: Apply major bumps (operator opt-in)

```bash
bash scripts/deps-update.sh --apply --major
```

Runs `uv sync --upgrade` which includes major version bumps. Review the changelog for breaking changes before running in production.

### Step 4: Handle plugins and Docker manually

- **Plugins**: Claude Code UI → Settings → Plugins → Update for any flagged plugin.
- **Docker**: Review any digest changes noted by the script. Update digest pins in `docker-compose*.yml` after manual testing.

## Dependencies

The script requires:
- `uv` — Python package manager
- `brew` — Homebrew (preferred for engram upgrade on macOS)
- `gh` — GitHub CLI (for engram + plugin version checks, fallback when brew unavailable)
- `go` — Go toolchain (fallback engram upgrade on Linux CI without Homebrew)
- `docker` — Docker CLI (for image digest checks)
- `python3` — JSON parsing of uv output (present wherever uv is)

Missing tools cause per-dimension SKIP messages; the script does not fail.

## Safety Rules

- NEVER modifies `docker-compose*.yml` files — Docker digest pinning is deliberate.
- NEVER runs `uv sync` (full resolution) in `--audit` mode — read-only.
- NEVER upgrades plugins automatically — Claude Code UI manages plugin lifecycle.
- Major Python bumps require explicit `--major` flag — no surprises.
- `uv.lock` is rewritten only in `--apply` mode (by uv itself, not the script).
- Before any binary swap, the existing binary is backed up to `<path>.v<old-version>.bak`.

## Engram: Brew-First Upgrade Flow

As of 2026-04-27, the engram section prefers `brew` over `go install`. Rationale: binaries
installed via brew are Gatekeeper-trusted on macOS. Binaries installed via `go install`
into `~/go/bin/` may be SIGKILL'd by macOS Operon sandbox when spawned from Claude Code.

**Apply flow:**
1. `brew update` — refreshes the tap formula index (versions can lag without this)
2. `brew info gentleman-programming/tap/engram` — gets the tap's latest stable version
3. `brew install/upgrade gentleman-programming/tap/engram` — installs it
4. Falls back to `go install` only when `brew` is not available (Linux CI, etc.)

**Fallback (no brew) flow:**
Same as the original flow: `go install github.com/Gentleman-Programming/engram/cmd/engram@vX.Y.Z`
plus the GOPATH versioned-bin workaround (copies `~/go/1.x/bin/engram` → `~/go/bin/engram`).

## Multi-Path Resolution Trap

`which engram` only shows the first match in PATH. If engram exists in multiple locations
(`~/go/bin`, `~/.local/bin`, `/opt/homebrew/bin`), the wrong binary may be active.

**Diagnosis:**
```bash
which -a engram   # show ALL matches, not just the first
```

The script runs `which -a` after any install and warns if more than one path is found.
To eliminate the ambiguity, symlink each location to the brew canonical:
```bash
ln -sf "$(brew --prefix)/bin/engram" ~/.local/bin/engram
ln -sf "$(brew --prefix)/bin/engram" ~/go/bin/engram
```

See `docs/tooling-update-protocol.md` for the full diagnosis + remediation pattern.

## MCP Server Lifecycle

MCP servers (engram, others) are **spawned once at Claude Code startup**. Changing the
binary on disk does NOT affect an already-running Claude Code session. After any engram
binary change you MUST:

1. Quit Claude Code fully (`cmd-Q` on macOS — not just closing the window)
2. Reopen Claude Code
3. Verify the new binary is active: `python3 scripts/check_mcp_servers.py`

The script prints this reminder automatically when it applies an engram upgrade.

## Backup / Rollback

Before replacing any binary the script backs it up:
- brew path: `<binary>.v<old-version>.bak` alongside the current binary
- go path: `~/go/bin/engram.v<old-version>.bak`

To roll back:
```bash
cp ~/.local/bin/engram.v1.10.2.bak ~/.local/bin/engram
# then restart Claude Code
```

## Known Gotchas

**GOPATH versioned-bin issue**: On macOS with `go env GOVERSION` in the path (e.g. `~/go/1.25.6/bin/`), `go install` writes the binary to the versioned subdirectory instead of `~/go/bin/`. The script detects this and copies the freshly built binary to `~/go/bin/engram` so the PATH-resolved binary is updated. This gotcha only applies to the `go install` fallback path; the brew path does not have this issue.

**brew tap formula lag**: `brew info` returns stale data if you haven't run `brew update` recently. Always run `brew update` first — the script does this automatically in `--apply` mode.

## Acceptance Criteria

1. `bash scripts/deps-update.sh --audit` exits 0 in <60s without side effects and prints the summary.
2. `bash scripts/deps-update.sh --dry-run` prints lines containing `would run:` without executing.
3. `bash scripts/deps-update.sh --apply` upgrades Python minor/patch and engram; prints MANUAL for major bumps.
4. Skill passes `uv run pytest tests/audit/test_skills_contracts.py -k deps-update`.
5. `validate-release/SKILL.md` references the audit call as an advisory step.

## Trust Report

```
TRUST_REPORT: SCORE=85 STATUS=HIGH EVIDENCE=4 UNCERTAINTIES=2
---
Score: 85/100
EVIDENCE: Script validated locally with --audit and --dry-run; output format confirmed;
          all four dimensions covered with SKIP guards for missing tools.
CONFIDENT: Python audit path, engram version comparison, plugin inventory, Docker pull logic.
UNSURE: engram version string parsing depends on `engram version` output format (may vary
        across builds). Docker `manifest inspect` requires experimental features enabled
        on some Docker installations — falls back gracefully to "unavailable".
VERIFY: bash scripts/deps-update.sh --audit 2>&1 | tail -15
        bash scripts/deps-update.sh --dry-run 2>&1 | grep "would run:" | head -10
```
