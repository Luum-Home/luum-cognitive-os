# Driver-Specific Script Surfaces

> Classification of user-facing scripts that still touch harness-owned files or tool registration APIs.

## Purpose

Cross-harness portability does not mean every script should immediately write every harness format.

Some scripts operate on Cognitive OS runtime state and should be portable now. Others operate on a specific harness driver, such as Claude Code settings or Claude MCP registration. Those scripts must be explicit instead of silently writing `.claude/` during Codex, OpenCode, Cursor, Windsurf, or other host sessions.

The rule is:

**Do not write a harness-owned file unless the active driver is known and the script has a real driver implementation for that harness.**

## Current Classification

| Script | Classification | Current behavior | Required next step |
|---|---|---|---|
| `scripts/so-emergency-stop.sh` | Cross-harness core with driver-specific projection | Always writes the Cognitive OS kill-switch flag, runs the reaper, and backs up the active settings driver. Applies the minimal security profile only for Claude because that profile is currently a Claude settings projection. | Add a Codex security-profile projection before changing Codex hook settings. |
| `scripts/set-security-profile.sh` | Claude-driver-only | Refuses non-Claude active drivers instead of pretending `.codex/hooks.json` can consume Claude profile JSON. | Introduce a security-profile compiler for Codex hook settings if Codex profile switching becomes a product requirement. |
| `scripts/register-mcps.sh` | Claude-driver-only | Registers via `claude mcp add` or merges `mcpServers` into `~/.claude/settings.json`. Skips non-Claude active drivers without writing Claude user config. | Add a Codex MCP registration driver only after the Codex MCP configuration contract is known. |
| `scripts/install-mcp-scan.sh` | Portable binary install, Claude-driver-only wiring examples | Installs or suggests the scanner, but hook wiring examples are Claude settings examples. | Add harness-specific scanner wiring docs once non-Claude drivers exist. |
| `scripts/install-aguara.sh` | Portable binary install, Claude-driver-only wiring examples | Installs Go binaries, but hook and MCP wiring examples are Claude settings examples. | Add harness-specific Aguara hook/MCP projection only when supported. |

## Why This Matters

The dangerous failure mode is not lack of support.

The dangerous failure mode is fake support: a Codex-hosted project that appears to be portable while a script quietly writes `.claude/settings.json` or `~/.claude/settings.json`.

That would preserve vendor lock-in under a portability label.

## Driver Policy

Scripts should follow these rules:

- Runtime-state scripts should use canonical project-root precedence: `COGNITIVE_OS_PROJECT_DIR -> CODEX_PROJECT_DIR -> CLAUDE_PROJECT_DIR -> cwd`.
- Settings-driver scripts should resolve the active driver through `scripts/_lib/settings-driver.sh`.
- Claude-only scripts should fail or skip explicitly when the active driver is not Claude.
- Emergency safety scripts should keep the core safety action portable even when a secondary driver projection is unavailable.
- New Codex support must be implemented as a real driver, not by copying Claude settings JSON into Codex-owned files.

## Product Interpretation

This is part of making Cognitive OS "sophisticated inside, simple outside."

The user experience should be easy and safe, but the implementation must be honest about what is portable today. A beginner-safe product should not silently mutate the wrong harness because an advanced compatibility layer is unfinished.

## Validation

Current regression coverage checks that:

- `so-emergency-stop.sh` creates the core kill-switch in a Codex-hosted project.
- `so-emergency-stop.sh` backs up `.codex/hooks.json` without invoking the Claude-only security-profile script.
- `set-security-profile.sh` refuses non-Claude active drivers.
- `register-mcps.sh` skips non-Claude active drivers without creating `~/.claude/settings.json`.

