# Cluster A — Root Installers Audit

## Summary

Cluster A contains the two entry-point installers at the repo root level: `install.sh`
(bootstrap for external projects) and `scripts/install-cos.sh` (Go CLI binary installer).
Neither reimplements skill/rule/hook sync logic. `install.sh` delegates ALL sync work to
`scripts/cos-init.sh` (Cluster B), so the ADR-001 fix applies at that delegated layer,
not here. `scripts/install-cos.sh` is out of scope entirely: it downloads and installs
the `cos` Go binary to `/usr/local/bin` or `~/.local/bin` and never touches `.claude/`
or `.cognitive-os/` paths. Both scripts are CLEAN for this bug class and need no
modifications. The real fix for external-project installs lives in `scripts/cos-init.sh`
(Cluster B).

## Findings

### install.sh

- **Synced**: None directly. Script handles arg parsing (`--from`, `--force`, `--help`),
  source-repo detection, conflict warning for existing `.claude/`, preparing a temp
  source copy (via rsync excluding `.venv`, `node_modules`, `reference`, `.git`,
  `__pycache__`), delegates all agentic primitive sync to `cos-init.sh --standard` (line 248),
  then copies `CLAUDE.md` template into `.claude/CLAUDE.md` if not present (line 254-256).
- **Destinations**: The only destination this script writes directly is
  `.claude/CLAUDE.md`. All other destinations (skills, rules, hooks, commands, templates,
  settings.json) are owned by the delegated `cos-init.sh`.
- **Risk**: CLEAN. No sync reimplementation; ADR-001 fix cascades via the delegation
  chain to `cos-init.sh` once that script is fixed.
- **Bug**: No. The advisory echo at lines 266-270 that describes the post-install tree
  mentions only `.cognitive-os/skills/cos/` and not `.claude/skills/cos/`. That copy-paste
  is stale documentation, not a sync bug, and it reflects a real gap in the delegated
  `cos-init.sh` (Cluster B). Fixing that here would be out of scope since it does not
  alter install behavior. Flagging for Cluster B / summary-output refresh after the real
  fix lands.
- **Fix applied**: No. Per scope guard, cross-cluster changes are noted, not touched.
- **Verification**: `grep -n 'skills|\.claude/|\.cognitive-os/' install.sh` shows only
  (a) help text references to source-dir detection, (b) pre-install conflict detection
  reads of `.claude/settings.json`, `.claude/rules`, `.claude/commands`, `.claude/CLAUDE.md`,
  (c) the single `cp .../CLAUDE.md.template .claude/CLAUDE.md` write, and (d) the
  post-install summary echo. No `skills/` write occurs in this script.

### scripts/install-cos.sh

- **Synced**: Nothing related to the COS content layer. The script installs the `cos`
  Go CLI binary via `go install github.com/Luum-Home/luum-cognitive-os/cmd/cos@latest`
  (method 1) or by downloading a pre-built release binary from GitHub (method 2), then
  moves it to `/usr/local/bin/cos` or `~/.local/bin/cos`.
- **Destinations**: `$COS_INSTALL` (defaults to `/usr/local/bin` or `$HOME/.local/bin`).
  No writes to `.claude/` or `.cognitive-os/` — this script does not touch project
  directories at all. It is a pure binary installer.
- **Risk**: CLEAN. Zero overlap with ADR-001 bug class.
- **Bug**: No. The script does not sync any of: skills, rules, hooks, commands, agents,
  templates, plugins. It is the equivalent of `brew install` for the `cos` CLI.
- **Fix applied**: No. Nothing to fix.
- **Verification**: `grep -n 'skills|\.claude|\.cognitive-os'` on this file returns
  "No matches found". The script's only outputs are shell messages and a binary copy to
  `INSTALL_DIR`. Cross-reference: HALT triggers call out `curl | bash` downloads of
  external binaries. This script uses `curl -fsSL ... | bash`-style invocation AS ITS
  DOCUMENTED USE CASE (it IS the `curl | bash` target), and uses `curl` internally to
  fetch a pre-built release binary from `github.com/Luum-Home/luum-cognitive-os`. That is
  the script's purpose (distribute a Go binary), not a suspicious side-channel, so no
  HALT needed. Flagging for awareness only — supply-chain review would examine this
  separately.

## Changes in this commit

- Files modified: none (both scripts clean for the ADR-001 bug class).
- File created: `docs/04-Concepts/architecture/harness-adoption-gap/scripts-audit-A-root-installers.md`
  (this report).

## What I'm confident about

- `install.sh` does NOT reimplement skill sync. It delegates to `cos-init.sh` and only
  writes `.claude/CLAUDE.md` directly. Verified by reading the full 274 lines.
- `scripts/install-cos.sh` is a Go-binary installer with ZERO overlap to the COS content
  sync layer. Verified by grep returning "No matches found" for skills/claude/cognitive-os.
- Neither script needs `SYNC_DIRS`-style modifications.
- The ADR-001 bug class for external-project installs lives in `scripts/cos-init.sh`
  (Cluster B). `cos-init.sh` at line 135 does `mkdir -p .cognitive-os/skills/cos` and at
  line 221 sets `skills_dest=".cognitive-os/skills/cos"`. No `.claude/skills/` write
  exists there either. That is a real bug for external projects and is Cluster B's
  responsibility.

## What I'm unsure about

- Whether `install.sh`'s post-install summary (lines 266-270) should be updated NOW to
  preview the future `.claude/skills/cos/` destination, or only AFTER Cluster B fixes
  `cos-init.sh`. Current decision: leave stale-ish echo untouched to avoid contradicting
  actual install behavior until cos-init.sh is fixed.
- Whether there are OTHER root-level installer scripts I missed beyond the two named in
  the cluster definition. I was given an explicit list of two, and did not search the
  repo more broadly (search permission: no). If something like `bootstrap.sh` or
  `setup.sh` exists at root and also syncs skills, it is not in cluster A by the
  orchestrator's definition.
- Whether the `scripts/install-cos.sh` Go binary, once installed, itself performs a
  skills sync when a user runs `cos init`. That is a Go-code audit, out of scope for
  this cluster (scope guard explicitly prohibits touching Go source).

## What human should verify

- Confirm `cos-init.sh` (Cluster B) is scheduled for audit and fix — it is the actual
  site of the ADR-001 bug class for external project installs. The verification that
  cos-init.sh has the bug: `grep -n 'skills_dest\|\.claude/skills' scripts/cos-init.sh`
  should show `skills_dest=".cognitive-os/skills/cos"` at line 221 and ZERO references
  to `.claude/skills/`.
- Confirm `install.sh`'s line 266-270 summary block does not mislead users. Consider a
  follow-up line refresh after Cluster B's fix ships.
- If the `cos` Go CLI performs a `cos init` operation that bypasses `cos-init.sh` and
  writes skills directly, that code path needs its own audit (likely lives in
  `cmd/cos/init.go` or similar under `cmd/`). Out of scope here.
- The `scripts/install-cos.sh` script uses `curl -fsSL ... | bash` distribution model.
  This is the documented public entry point (per script header). Supply-chain review
  policy applies but is a separate concern from ADR-001.
