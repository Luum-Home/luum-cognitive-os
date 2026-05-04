# Harness Implementation Roadmap

Generated: 2026-05-04

## Purpose

Track planned IDE/provider harnesses without overclaiming support. A harness becomes `implemented` in `manifests/harness-projection.yaml` only after a projection driver and temp-project proof exist.

## Current implemented projection proof

| Harness | Status | Proof |
|---|---|---|
| Claude Code | implemented | ACC temp project runs `cos_init.py --default/--full --harness claude`. |
| OpenAI Codex | implemented | ACC temp project runs `cos_init.py --default/--full --harness codex`. |
| Shell/CI | projected command layer | `scripts/project_shell_ci.py` projects signed CLI commands/workflow inside those temp projects. |

## Planned harness backlog

| Harness/provider | Current source signal | COS next step | Promotion gate |
|---|---|---|---|
| Qwen Code | Official docs describe MCP, TypeScript SDK, terminal/IDE/CI-style usage. | Define `.qwen`/settings projection, skills/tools/MCP mapping, and temp-project proof. | Add driver, contract test, manual test, ACC adapter count. |
| Kimi Code | Official docs describe CLI, VS Code extension, OpenAI/Anthropic-compatible coding API, and third-party agent usage. | Decide whether COS integrates Kimi as native CLI/VS Code harness or provider behind existing harnesses. | Add config projection or provider adapter; do not mark implemented until local project proof exists. |
| OpenCode | Official docs expose `opencode.json`, agents, prompts, tools, and MCP config. | Implement `opencode.json` projection for instructions/tools/MCP. | Temp project validates config schema and ACC projected surface. |
| Cursor | Planned IDE rules/MCP projection. | Define `.cursor/rules` and `.cursor/mcp.json` projection. | Temp project structural proof. |
| Windsurf | Planned IDE rules/MCP projection. | Define `.windsurf/rules` and `.windsurf/mcp.json` projection. | Temp project structural proof. |
| VS Code Copilot | Planned instructions/tasks/MCP projection. | Generate `.github/copilot-instructions.md`, `.vscode/tasks.json`, and settings. | Temp project validates files and task syntax. |
| Google Antigravity | Local project config is not signed in this repo. | Research supported local config/tool format. | Add driver only after source-supported projection surface is known. |
| MiniMax MaxClaw / MiniMax Agent | Current evidence points to hosted-agent/OpenClaw style surfaces. | Treat as hosted/provider surface unless a local IDE/project config exists. | Provider/openclaw adapter proof, not IDE projection by default. |
| DeepSeek provider | Official docs are provider/API oriented. | Keep as provider compatibility through existing harnesses until a first-party IDE harness exists. | Provider smoke/config proof. |

## Promotion checklist

1. Add or update `manifests/harness-projection.yaml` entry with `status: planned` first.
2. Implement a driver or projection script with no source-repo absolute paths in generated files.
3. Add temp-project contract tests.
4. Add manual test documentation.
5. Run `python3 scripts/acc_pipeline.py --project-dir . --refresh`.
6. Only then change status to `implemented`.

## Baseline discipline

ACC can report 1.0 for the current declared scope. New harnesses must not inherit that status. Planned harness rows remain unverified until their own proof exists.
