# Codex Host Tooling Verification

> Manual proof path for verifying that Cognitive OS is projected into Codex,
> that declared host tools are available, and that Engram is registered as a
> Codex MCP server.

## Purpose

This check answers a concrete question:

**Can this Codex host actually see the Cognitive OS driver, declared
dependencies, and MCP tooling the OS claims to use?**

It is not enough for files to exist in the repository. A durable self-hosting
claim requires a command that proves the active host can resolve the driver,
read the dependency manifest, start optional MCP services, and report missing
tools without hiding them.

## Prerequisites

- The repository is trusted by Codex.
- The repository contains `.codex/hooks.json`.
- `engram` is installed on `PATH` when memory/MCP checks are expected.
- Codex has been restarted after MCP configuration changes.

## One-Time Engram Setup For Codex

Run:

```bash
engram setup codex
```

Expected effect in `~/.codex/config.toml`:

```toml
model_instructions_file = "/Users/matias.nahuel.amendola/.codex/engram-instructions.md"
experimental_compact_prompt_file = "/Users/matias.nahuel.amendola/.codex/engram-compact-prompt.md"

[mcp_servers.engram]
command = "/opt/homebrew/Cellar/engram/1.14.5/bin/engram"
args = ["mcp", "--tools=agent"]
```

The exact `command` path may differ by machine. The important contract is that
Codex config contains an `mcp_servers.engram` entry pointing to an executable
Engram binary with `["mcp", "--tools=agent"]`.

After running setup, restart Codex. Codex loads MCP server definitions at host
startup, so a running conversation can still lack newly configured MCP tools
until the app is restarted.

## Default Profile Verification

Run:

```bash
COGNITIVE_OS_HARNESS=codex CODEX_PROJECT_DIR="$PWD" \
  bash scripts/cos-doctor-tools.sh --profile default --strict
```

Expected result:

```text
PASS active harness is supported: codex
PASS settings driver exists: .codex/hooks.json
PASS settings driver JSON contract is valid
PASS dependency manifest loaded for profile: default
PASS required tools present
PASS recommended tools present
PASS recommended MCP server dependencies present
PASS engram CLI found
PASS engram CLI search works
PASS engram MCP stdio starts
PASS Codex config mentions Engram
PASS memory lifecycle doctor passed
Result: PASS (0 warning(s))
```

This verifies the default host contract declared in
`manifests/dependencies.yaml`.

## Automatic SessionStart Check

`hooks/host-tool-doctor.sh` is registered as a SessionStart hook for both the
Codex and Claude projections. It resolves the installed Cognitive OS source
from `.cognitive-os/install-meta.json`, runs `scripts/cos-doctor-tools.sh` with
the default profile, and records the latest result at:

```text
.cognitive-os/reports/host-tools/latest.txt
.cognitive-os/runtime/host-tool-doctor.state.json
```

The automatic hook is cached for 24 hours by default. Override the cache only
when diagnosing host wiring:

```bash
COS_HOST_TOOL_DOCTOR_FORCE=1 \
COS_HOST_TOOL_DOCTOR_FOREGROUND=1 \
COGNITIVE_OS_HARNESS=codex CODEX_PROJECT_DIR="$PWD" \
  bash hooks/host-tool-doctor.sh
```

The hook is advisory and never installs missing tools or mutates user-level MCP
configuration. Safe project wiring repair remains the job of `self-install.sh`;
tool installation and Codex restart remain explicit operator actions.

`cos-doctor-tools.sh` also invokes the memory lifecycle doctor. For deeper
manual verification, run the memory check directly:

```bash
COGNITIVE_OS_HARNESS=codex \
CODEX_PROJECT_DIR="$PWD" \
  bash scripts/cos-doctor-memory-lifecycle.sh --harness codex
```

Expected evidence:

- `PASS Engram launcher hook can run for a new codex session`
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
COGNITIVE_OS_HARNESS=codex CODEX_PROJECT_DIR="$PWD" \
  bash scripts/cos-doctor-tools.sh --profile full
```

The full profile includes optional/recommended tools. Missing optional tools
should be visible as warnings, not silently ignored.

Example:

```text
WARN recommended tools missing: mcp-scan,parry-guard,promptfoo
Result: PASS (1 warning(s))
```

Use `--strict` with the full profile only when the local machine is expected to
have every recommended extension installed.

## What This Proves

- Codex is selected as the active harness.
- `.codex/hooks.json` exists and uses Codex-native lifecycle keys.
- Required/recommended tools are checked from the declarative manifest, not a
  hand-maintained one-off list.
- Engram CLI can search local memory.
- Engram MCP stdio startup succeeds.
- Codex config contains the Engram MCP registration.

## What This Does Not Prove

- It does not prove every optional Docker/reference service is running.
- It does not prove Codex has already loaded newly added MCP definitions in the
  current conversation if Codex was not restarted.
- It does not prove every future harness driver works; it proves the active
  Codex driver and declared dependency profile on this host.
- The automatic SessionStart hook does not run pytest. Use
  `scripts/pytest-with-summary.sh` explicitly when test inventory is needed.

## Related Automated Tests

```bash
python3 -m pytest \
  tests/behavior/test_cos_doctor_tools.py \
  tests/behavior/test_host_tool_doctor_hook.py \
  tests/integration/test_manifest_e2e.py \
  tests/unit/test_safe_engram_contract.py \
  tests/unit/test_cos_mcp_server.py \
  tests/behavior/test_security_integrations.py \
  -q --tb=short -ra
```

These tests cover the doctor command, dependency manifest integration, Engram
safe-save contracts, COS MCP server behavior, and MCP security integration
degradation paths.
