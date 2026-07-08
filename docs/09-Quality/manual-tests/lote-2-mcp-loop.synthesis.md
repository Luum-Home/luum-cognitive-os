---
type: quality-synthesis
source: docs/09-Quality/manual-tests/lote-2-mcp-loop.md
provenance: "Step-by-step manual test checklist for the end-to-end MCP auto-install/registration loop introduced in PR lote-2, verifying install.sh, register-mcps.sh, and cos-update.sh close the loop declared in manifests/dependencies.yaml."
---

## What it is
A 4-step manual checklist (with explicit pass/fail criteria per step) verifying that fresh installs auto-register declared MCP servers, that `cos-update.sh` picks up newly added manifest MCP entries, that repeated runs are no-ops via a SHA cache, and that the tooling degrades gracefully when the `claude` CLI is absent.

## Key mechanics
- Step 1 — Fresh install registers MCPs: back up `~/.claude/settings.json`, delete it, run `bash install.sh --from . --force --install-deps`, then `claude mcp list`. Pass: output contains `engram` and no `ERROR:` lines in stderr. Fail: no entries listed, or install.sh exits 1.
- Step 2 — `cos-update.sh` picks up a new MCP entry: manually append a `test-mcp-manual` (optional, stdio, `echo` command) entry to `manifests/dependencies.yaml` (not committed) and to the `default` profile's recommended list, then run `bash scripts/cos-update.sh --no-verify`. Pass: `claude mcp list` shows `test-mcp-manual` and the update script exits 0. Cleanup: `git checkout manifests/dependencies.yaml` and `claude mcp remove test-mcp-manual`.
- Step 3 — Second run is a no-op (SHA cache): run `cos-update.sh --no-verify` twice; the second run's output must contain `"unchanged"` or `"skipped"` for MCP registration, and `claude mcp add` must not be invoked again.
- Step 4 — Graceful degradation without `claude` CLI: delete `.cognitive-os/state/mcps.sha` (to bypass the short-circuit), run `register-mcps.sh --profile default` with a stripped `PATH=/usr/bin:/bin`. Pass: exit code 0, no unhandled tracebacks, and either `~/.claude/settings.json` gets updated or a `WARN:` explains the skip.
- Each step's commands include explicit destructive-action warnings (deleting real settings, requiring restoration from backup).

## Relations & where used
Exercises `install.sh --install-deps`, `scripts/register-mcps.sh`, `scripts/cos-update.sh`, and `manifests/dependencies.yaml`. Complements `host-tooling-engram-mcp-verification.md`, which verifies the resulting MCP config is actually visible/usable by the host rather than just registered.

## Status / caveats
Named after an internal PR batch ("lote 2" / "PR lote-2") — the doc is tied to a specific historical change rather than a generic capability description; treat as a regression checklist for that MCP auto-install feature rather than a living architecture reference. No other inconsistency found.
