---
type: quality-synthesis
source: docs/09-Quality/manual-tests/host-tooling-engram-mcp-verification.md
provenance: "Manual proof path verifying that a projected host (IDE/CLI) can actually see the Cognitive OS driver, declared dependencies, MCP tooling, and Engram memory surface — not just that files exist in the repository."
---

## What it is
A multi-host verification proof (filename is historical from the first Codex proof, but now covers Claude Code, Cursor, Devin, VS Code/Copilot, Qoder-style, Factory Droid, Augment, and Kimi) that a host can resolve the COS driver, read the dependency manifest, start optional MCP services, and report missing/stale tools — with special emphasis on catching upgrade-brittle Engram MCP command paths.

## Key mechanics
- `scripts/check_mcp_servers.py` inspects user-global and project-local MCP config surfaces across 12 listed host/surface combinations (e.g. `~/.claude/settings.json`, `~/.codex/config.toml`, `.cursor/mcp.json`, `.kimi/mcp.json`); duplicate registrations are intentional to detect — one healthy Engram entry must not hide a stale one.
- Upgrade-safe Engram command contract: safe patterns use a bare `engram` command or a stable path like `/opt/homebrew/bin/engram`; the blocked/brittle pattern is a Homebrew Cellar version-pinned path (e.g. `/opt/homebrew/Cellar/engram/<version>/bin/engram`), which breaks silently after `brew upgrade` removes the old Cellar version, leaving new sessions without `mem_save`/`mem_context`/`mem_search`/`mem_session_summary` even though `engram serve` is healthy.
- Prerequisites: project trusted by the active host, project initialized with the intended harness, `engram` installed, and — critically — the host must be **restarted** after MCP config changes since MCP tools load at session startup, not injected mid-session.
- Active-host verification: `scripts/cos-doctor-tools.sh --profile default --strict` run with harness-specific env vars (`COGNITIVE_OS_HARNESS=codex|claude|cursor` + project dir var); expected evidence is a 9-line PASS block culminating in `Result: PASS (0 warning(s))`.
- Direct MCP config drift check: `scripts/check_mcp_servers.py --json` surfaces duplicate Engram rows as `engram`, `engram#2`, etc.; any Cellar-pinned row should be repaired even if another row is healthy.
- Automatic SessionStart hook: `hooks/host-tool-doctor.sh` runs `cos-doctor-tools.sh` with the default profile, writes results to `.cognitive-os/reports/host-tools/latest.txt` and `.cognitive-os/runtime/host-tool-doctor.state.json`; advisory and cached 24h by default (override with `COS_HOST_TOOL_DOCTOR_FORCE=1`). It does not install tools or mutate MCP config.
- Memory lifecycle verification via `scripts/cos-doctor-memory-lifecycle.sh --harness <codex|claude>` checks 8 PASS conditions spanning session-resume, prompt capture, session-learning, git-context-capture, session-changelog, crystallization, and pre-compaction flush.
- Full profile (`--profile full`) adds optional/recommended tool checks; `--strict` should only be used when the machine is expected to have every recommended extension.
- Explicit non-claims: does not prove every optional Docker/reference service is running; does not prove an already-open session picked up new MCP config (restart required); does not prove every structural IDE can execute hooks natively (structural projections may lack a hook lifecycle); the SessionStart hook does not run pytest.

## Relations & where used
Depends on `scripts/check_mcp_servers.py`, `scripts/cos-doctor-tools.sh`, `scripts/cos-doctor-memory-lifecycle.sh`, `hooks/host-tool-doctor.sh`, `manifests/dependencies.yaml`. Related automated tests: `tests/behavior/test_cos_doctor_tools.py`, `tests/behavior/test_host_tool_doctor_hook.py`, `tests/integration/test_manifest_e2e.py`, `tests/unit/test_check_mcp_servers.py`, `tests/unit/test_safe_engram_contract.py`, `tests/unit/test_cos_mcp_server.py`, `tests/behavior/test_security_integrations.py`.

## Status / caveats
No dated snapshot or internal inconsistency; the doc explicitly separates "what this proves" from "what this does not prove," which is itself the load-bearing content for avoiding false portability claims.
