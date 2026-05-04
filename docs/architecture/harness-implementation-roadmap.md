# Harness Implementation Roadmap

Generated: 2026-05-04

## Purpose

Track planned IDE/provider harnesses without overclaiming support. A harness becomes `implemented` in `manifests/harness-projection.yaml` only after a projection driver and temp-project proof exist.

## Current implemented projection proof

| Harness | Status | Proof |
|---|---|---|
| Claude Code | implemented | ACC temp project runs `cos_init.py --default/--full --harness claude`. |
| OpenAI Codex | implemented | ACC temp project runs `cos_init.py --default/--full --harness codex`. |
| OpenCode | implemented structural | ACC temp project runs `cos_init.py --default/--full --harness opencode` and verifies `opencode.json`. |
| VS Code Copilot | implemented structural | ACC temp project runs `cos_init.py --default/--full --harness vscode-copilot` and verifies `.github/copilot-instructions.md` plus `.vscode/mcp.json`. |
| Cursor | implemented structural | ACC temp project runs `cos_init.py --default/--full --harness cursor` and verifies `.cursor/rules/cognitive-os.mdc` plus `.cursor/mcp.json`. |
| Shell/CI | implemented structural | `cos_init.py --default/--full --harness shell-ci` invokes `scripts/project_shell_ci.py` and ACC records shell-ci default/full projection counts. |

## Planned harness backlog

| Harness/provider | Current source signal | COS next step | Promotion gate |
|---|---|---|---|
| Qwen Code | Official docs describe `.qwen/settings.json`, `mcpServers`, and context files such as `QWEN.md`. | Implemented structural projection. Next: optional account-backed CLI/runtime smoke. | Temp project validates `.qwen/settings.json`, `QWEN.md`, and ACC default/full counts. |
| Kimi Code | Official docs describe Kimi Code CLI, `--work-dir`, `--mcp-config-file`, MCP config, and project-level `AGENTS.md`; VS Code extension remains account-backed. | Implemented structural CLI projection. Next: optional account-backed CLI smoke. | Temp project validates `AGENTS.md`, `.kimi/mcp.json`, `.kimi/README.md`, and ACC default/full counts. |
| OpenCode | Official docs expose `opencode.json`, instructions, permissions, and MCP config. | Implemented structural projection. Next: optional account-backed CLI smoke. | Temp project validates `opencode.json`; runtime smoke remains optional. |
| Cursor | Official docs expose `.cursor/rules`, MDC metadata, AGENTS.md, and MCP config. | Implemented structural projection. Next: optional account-backed Cursor smoke. | Temp project validates `.cursor/rules/cognitive-os.mdc` and `.cursor/mcp.json`; runtime smoke remains optional. |
| Windsurf | Planned IDE rules/MCP projection. | Define `.windsurf/rules` and `.windsurf/mcp.json` projection. | Temp project structural proof. |
| VS Code Copilot | Official docs expose `.github/copilot-instructions.md`, AGENTS.md, and MCP configuration. | Implemented structural projection. Next: optional account-backed extension smoke. | Temp project validates `.github/copilot-instructions.md` and `.vscode/mcp.json`; runtime smoke remains optional. |
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

ACC can report 1.0 for the current declared scope. New harnesses must not inherit that status. Planned harness rows remain unverified until their own proof exists. Implemented structural harnesses prove project-local config/instruction/context or command/workflow projection, not native lifecycle hook parity or stack-specific runtime command success.

Run the ACC ratchet before promoting any harness work:

```bash
python3 scripts/acc_pipeline.py --project-dir . --brief --fail-new
```

`--fail-new` must stay strict by default: a new file that only matches a broad local default is review debt until it gets an exact availability row, lifecycle metadata, or projection proof. This keeps planned harness work from being hidden by existing local-surface defaults.
