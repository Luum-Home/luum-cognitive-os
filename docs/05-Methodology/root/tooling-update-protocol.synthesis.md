---
type: methodology-synthesis
source: docs/05-Methodology/root/tooling-update-protocol.md
provenance: "Distilled from the engram MCP outage of 2026-04-27 to give operators a repeatable procedure for safely updating tools that Claude Code spawns as MCP servers, hooks, or directly-executed binaries."
---

## What it is

An operator guide for updating any tool integrated with Claude Code (MCP servers, hook binaries, plugin executables) without silently breaking it — because updates to these binaries have failure modes that are easy to miss (stale PATH resolution, sandbox kills, non-restarted processes).

## Key mechanics

- **The 3-Paths Trap**: `which <tool>` only reports the first PATH match; if the same binary name exists in multiple locations (e.g. `~/go/bin/`, `~/.local/bin/`, `/opt/homebrew/bin/`), the copy that actually executes inside Claude Code's spawned subprocess can differ from the one resolved in an interactive shell. Diagnosis via `which -a <tool>` plus `python3 scripts/check_mcp_servers.py` (shows resolved path + version per MCP). Remediation: symlink every extra location to one canonical, authoritative install.
- **MCP Server Restart Requirement**: MCP servers spawn once at Claude Code startup — neither editing plugin config nor replacing the binary on disk affects a running session. A full quit (`cmd-Q`, not just closing the window) and reopen is required before the new binary takes effect; this is called out as the single most common reason an upgrade "succeeds" but has no observable effect.
- **Install-method decision table**: prefer `brew install/upgrade` on macOS with Homebrew (Gatekeeper-trusted, survives the macOS Operon sandbox); `go install` only when brew is unavailable; raw release-asset download with checksum verification as last resort. Explicitly warns against mixing `go install` with an existing brew install — it creates a second binary and reintroduces the 3-Paths Trap. Always run `brew update` first since the tap formula can lag upstream.
- **Verification post-update**: 4-step check (`which -a`, version flag, `check_mcp_servers.py`, and for engram specifically a live `mem_search` call) with exit-code semantics (0 = all healthy, 1 = issue detected).
- **Rollback**: `deps-update.sh` backs up the prior binary (`<path>.v<old-version>.bak`) before replacing it; restore by copying the backup back and restarting Claude Code, or reinstalling the pinned version via brew/go install if no local backup exists.
- **Case study (engram, 2026-04-27)**: three physical copies of the `engram` binary existed across PATH; the one resolved by plain `which` (v1.13.1, from `~/go/bin/`) was being SIGKILL'd by the macOS Operon sandbox specifically when spawned from Claude Code's execution context (not predicted by `spctl -a -v` alone); `brew info` was also showing a stale version until `brew update` refreshed the tap. Fix: `brew update` + reinstall to get 1.14.5, back up the old copies, symlink all PATH locations to the canonical brew binary, then quit/reopen Claude Code.

## Relations & where used

Directly informs `scripts/deps-update.sh` (backup/rollback mechanics) and `scripts/check_mcp_servers.py` (verification step). The case study's full observation is cross-referenced in Engram under topic key `tooling/engram-mcp-fix` (ID #13280) rather than duplicated here.

## Status / caveats

Framed as a living, example-driven guide anchored to one specific incident (engram MCP outage, 2026-04-27) — the case study is dated and tool-specific, but the general protocol (3-Paths Trap, restart requirement, brew/go decision table) is timeless operational guidance. No internal inconsistencies found.
