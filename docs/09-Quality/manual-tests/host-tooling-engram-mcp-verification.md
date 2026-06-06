# Host Tooling and Engram MCP Verification

> Manual proof path for verifying that Cognitive OS is projected into the
> active host (IDE/CLI), that declared tools are visible, and that Engram MCP
> registrations use upgrade-safe command paths. The filename is historical from
> the first Codex proof; the check is now multi-host.

## Purpose

This check answers a concrete question:

**Can this host actually see the Cognitive OS driver, declared dependencies,
MCP tooling, and Engram memory surface the OS claims to use?**

It is not enough for files to exist in the repository. A durable portability
claim requires a command that proves the active host can resolve the driver,
read the dependency manifest, start optional MCP services, and report missing
or stale tools without hiding them.

## Covered Hosts and Config Surfaces

`scripts/check_mcp_servers.py` inspects user-global and project-local MCP
surfaces, including duplicate registrations. Duplicates are intentional: one
healthy Engram registration must not hide a stale one.

| Host/surface | MCP config inspected | Shape |
|---|---|---|
| Claude Code user settings | `~/.claude/settings.json` | JSON `mcpServers.engram` |
| Claude Code standalone MCP | `~/.claude/mcp/*.json` | JSON single-server or `mcpServers` |
| Claude plugin cache | `~/.claude/plugins/cache/**/.mcp.json` | JSON `mcpServers` |
| Codex user config | `~/.codex/config.toml` or `$CODEX_HOME/config.toml` | TOML `[mcp_servers.engram]` |
| Claude project projection | `.claude/settings.json` | JSON `mcpServers` when present |
| Codex project projection | `.codex/config.toml` | TOML `mcp_servers` when present |
| Cursor | `.cursor/mcp.json` | JSON `mcpServers` |
| Devin | `.devin/mcp_config.json` | JSON `mcpServers` |
| VS Code / Copilot | `.vscode/mcp.json` | JSON `mcpServers` |
| Qoder-style project MCP | `.mcp.json` | JSON `mcpServers` |
| Factory Droid | `.factory/mcp.json` | JSON `mcpServers` |
| Augment | `.augment/mcp.json` | JSON `mcpServers` |
| Kimi | `.kimi/mcp.json` | JSON `mcpServers` |

## Upgrade-Safe Engram Command Contract

Engram MCP registrations must point to a command that survives package upgrades.

Safe examples:

```toml
[mcp_servers.engram]
command = "engram"
args = ["mcp", "--tools=agent"]
```

```toml
[mcp_servers.engram]
command = "/opt/homebrew/bin/engram"
args = ["mcp", "--tools=agent"]
```

```json
{
  "mcpServers": {
    "engram": {
      "command": "/opt/homebrew/bin/engram",
      "args": ["mcp", "--tools=agent"]
    }
  }
}
```

Blocked/brittle pattern:

```text
/opt/homebrew/Cellar/engram/<version>/bin/engram
```

Homebrew removes old Cellar versions during upgrades. A version-pinned Engram
MCP command can leave new host sessions without `mem_save`, `mem_context`,
`mem_search`, or `mem_session_summary`, even when `engram serve` is healthy.

## Prerequisites

- The project is trusted by the active host.
- The project has been initialized with the intended harness, for example
  `--harness=codex`, `--harness=claude`, `--harness=cursor`, or another
  structural projection.
- `engram` is installed when memory/MCP checks are expected.
- The host has been restarted after MCP configuration changes. MCP tools are
  normally loaded at host/session startup, not injected into existing sessions.

## Active-Host Verification

Run the doctor with the active harness environment. Examples:

```bash
COGNITIVE_OS_HARNESS=codex CODEX_PROJECT_DIR="$PWD" \
  bash scripts/cos-doctor-tools.sh --profile default --strict
```

```bash
COGNITIVE_OS_HARNESS=claude CLAUDE_PROJECT_DIR="$PWD" \
  bash scripts/cos-doctor-tools.sh --profile default --strict
```

```bash
COGNITIVE_OS_HARNESS=cursor COGNITIVE_OS_PROJECT_DIR="$PWD" \
  bash scripts/cos-doctor-tools.sh --profile default
```

Expected evidence for hosts with Engram configured:

```text
PASS active harness is supported: <harness>
PASS settings driver exists: <driver path>
PASS dependency manifest loaded for profile: default
PASS required tools present
PASS recommended tools present
PASS recommended MCP server dependencies present
PASS engram CLI found
PASS engram CLI search works
PASS engram MCP stdio starts
PASS Engram MCP host configs use upgrade-safe command paths
Result: PASS (0 warning(s))
```

For Codex specifically, the doctor also verifies the native lifecycle-key shape
of `.codex/hooks.json` and reports whether the Codex user config mentions
Engram. For Claude specifically, it verifies the Claude `hooks` object shape.
For structural IDE/CLI projections, the settings-driver presence check proves
the projection artifact exists, while the MCP scanner independently checks the
known MCP files listed above.

## Direct MCP Config Drift Check

Use this when debugging a host where agents report missing `mem_*` tools:

```bash
COGNITIVE_OS_PROJECT_DIR="$PWD" python3 scripts/check_mcp_servers.py --json
```

Look for Engram rows. Duplicate registrations appear as `engram`, `engram#2`,
`engram#3`, etc. Any row with a Cellar-pinned command should be repaired even
if another Engram row is healthy.

Common operator checks:

```bash
command -v engram
type -a engram
which -a engram
ls -l /opt/homebrew/bin/engram
realpath /opt/homebrew/bin/engram
engram --version
```

## Automatic SessionStart Check

`hooks/host-tool-doctor.sh` is registered as a SessionStart hook for projected
hook-capable hosts. It resolves the installed Cognitive OS source from
`.cognitive-os/install-meta.json`, runs `scripts/cos-doctor-tools.sh` with the
default profile, and writes the latest result at:

```text
.cognitive-os/reports/host-tools/latest.txt
.cognitive-os/runtime/host-tool-doctor.state.json
```

The hook is advisory and cached for 24 hours by default. Override the cache only
when diagnosing host wiring:

```bash
COS_HOST_TOOL_DOCTOR_FORCE=1 \
COS_HOST_TOOL_DOCTOR_FOREGROUND=1 \
COGNITIVE_OS_HARNESS=codex CODEX_PROJECT_DIR="$PWD" \
  bash hooks/host-tool-doctor.sh
```

The hook does not install missing tools or mutate user-level MCP configuration.
Tool installation, MCP config repair, and host restart remain explicit operator
actions.

## Memory Lifecycle Verification

`cos-doctor-tools.sh` invokes the memory lifecycle doctor when Engram is
available. For direct verification:

```bash
COGNITIVE_OS_HARNESS=codex CODEX_PROJECT_DIR="$PWD" \
  bash scripts/cos-doctor-memory-lifecycle.sh --harness codex
```

```bash
COGNITIVE_OS_HARNESS=claude CLAUDE_PROJECT_DIR="$PWD" \
  bash scripts/cos-doctor-memory-lifecycle.sh --harness claude
```

Expected evidence includes:

- `PASS Engram launcher hook can run for a new <harness> session`
- `PASS session-resume detects and recovers pending tasks`
- `PASS user prompt capture writes lifecycle metrics`
- `PASS session-learning saves session summary metrics`
- `PASS git-context-capture saves session git context`
- `PASS session-changelog saves resumable changelog`
- `PASS Engram crystallization records session-end lifecycle event`
- `PASS pre-compaction flush emits durable memory reminder`

## Full Profile Verification

Run:

```bash
COGNITIVE_OS_HARNESS=<harness> COGNITIVE_OS_PROJECT_DIR="$PWD" \
  bash scripts/cos-doctor-tools.sh --profile full
```

The full profile includes optional/recommended tools. Missing optional tools
should be visible as warnings, not silently ignored. Use `--strict` only when
the local machine is expected to have every recommended extension installed.

## What This Proves

- Active harness detection works for the selected host.
- The selected settings driver exists and has the expected shape for hook-capable
  Codex/Claude projections.
- Required/recommended tools are checked from `manifests/dependencies.yaml`.
- Recommended MCP server dependencies are visible.
- Engram CLI can search local memory when installed.
- Engram MCP stdio startup succeeds when installed.
- Engram MCP host configs use upgrade-safe command paths across scanned
  user-global and project-local IDE/CLI surfaces.

## What This Does Not Prove

- It does not prove every optional Docker/reference service is running.
- It does not prove an already-open host session has reloaded newly changed MCP
  definitions; restart the host after MCP config changes.
- It does not prove every structural IDE can execute hooks natively. Structural
  projections may provide instructions/rules plus MCP config files without a
  hook lifecycle equivalent.
- The automatic SessionStart hook does not run pytest. Use
  `scripts/pytest-with-summary.sh` explicitly when test inventory is needed.

## Related Automated Tests

```bash
uv run pytest \
  tests/behavior/test_cos_doctor_tools.py \
  tests/behavior/test_host_tool_doctor_hook.py \
  tests/integration/test_manifest_e2e.py \
  tests/unit/test_check_mcp_servers.py \
  tests/unit/test_safe_engram_contract.py \
  tests/unit/test_cos_mcp_server.py \
  tests/behavior/test_security_integrations.py \
  -q --tb=short -ra
```

These tests cover the doctor command, dependency manifest integration, MCP
config/path drift diagnostics, Engram safe-save contracts, COS MCP server
behavior, and MCP security integration degradation paths.
