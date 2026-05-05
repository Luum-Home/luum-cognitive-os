# Harness docs currentness audit — 2026-05-05

## Purpose

Contrast every Cognitive OS harness projection claim with current official vendor documentation. This audit verifies **structural projection shape**, not account-backed runtime behavior.

## Method

- Read `manifests/harness-projection.yaml` and `manifests/ai-agent-harness-landscape.yaml`.
- Checked current official documentation for implemented and planned harnesses.
- Ran temp-project structural projection tests after corrections.
- Kept hosted/provider surfaces separate from local project-file projection.

## Summary

| Result | Count | Meaning |
|---|---:|---|
| Aligned | 21 | Current generated files match official project-local surfaces or explicit CLI-file inputs. |
| Corrected in this audit | 3 | Generated or documented files were adjusted to avoid unsupported path claims. |
| Planned / no projection | 5 | Kept out of implementation because docs do not yet sign a safe local projection or the surface is provider/hosted. |

## Corrected findings

| Harness | Previous COS projection | Current official-doc contrast | Correction |
|---|---|---|---|
| Kilo Code | Generated `.kilocode/mcp.json` plus `.kilo/kilo.jsonc`. | Kilo docs sign project-level `kilo.jsonc` or `.kilo/kilo.jsonc`, with MCP under the `mcp` key. | Removed `.kilocode/mcp.json`; kept MCP placeholder inside `.kilo/kilo.jsonc`. |
| Goose | Generated `.goose/config.json`. | Goose docs sign `.goosehints` for local context and YAML/config/CLI extension flows, not `.goose/config.json` as a project MCP file. | Removed `.goose/config.json`; kept `.goosehints` only. |
| Augment/Auggie | Generated `.augment/settings.json` as if it were auto-loaded workspace settings. | Augment CLI docs sign `--rules` and `--mcp-config` inputs; workspace MCP settings require explicit trust/approval. | Switched to `.augment/rules/cognitive-os.md`, `.augment/mcp.json`, and `.augment/README.md` with explicit `auggie --rules ... --mcp-config ...` invocation. |

## Implemented harness audit matrix

| Harness | COS files | Current official-doc status | Audit result |
|---|---|---|---|
| Claude Code | `.claude/settings.json` | Official docs sign project settings and lifecycle hooks. | Aligned. |
| OpenAI Codex | `.codex/hooks.json` | Current Codex docs emphasize AGENTS.md/config/MCP/notify. Repo still treats Codex as native lifecycle based on existing internal projection contract; keep under watch. | Needs periodic Codex-specific review, no change in this audit. |
| Cursor | `.cursor/rules/cognitive-os.mdc`, `.cursor/mcp.json` | Official docs expose project rules/MCP surfaces, though current docs are consolidated under cursor.com/docs. | Aligned structurally; runtime untested. |
| VS Code Copilot | `.github/copilot-instructions.md`, `.vscode/mcp.json` | VS Code docs sign custom instructions and workspace MCP. | Aligned structurally. |
| OpenCode | `opencode.json` | Official docs sign project `opencode.json`, instructions, permissions, and `mcp` config key. | Aligned structurally. |
| Qwen Code | `.qwen/settings.json`, `QWEN.md` | Official docs sign project `.qwen/settings.json`, `context.fileName`, `includeDirectories`, and `mcpServers`. | Aligned structurally. |
| Kimi Code CLI | `AGENTS.md`, `.kimi/mcp.json`, `.kimi/README.md` | Official CLI docs sign work-dir and MCP config file flags; Help Center signs AGENTS.md customization. | Aligned as explicit CLI-file projection. |
| Shell / CI | shell projection manifest/workflow/scripts | COS-owned harness, not vendor-documented. | Aligned by local tests. |
| Gemini CLI | `.gemini/settings.json`, `GEMINI.md` | Official docs sign project `.gemini/settings.json`, `contextFileName`, `includeDirectories`, `loadMemoryFromIncludeDirectories`, and `mcpServers`. | Aligned structurally. |
| Warp | `AGENTS.md`, `.warp/README.md` | Official docs sign root/subdirectory `AGENTS.md`; `WARP.md` is backward-compatible and takes precedence if both exist. | Aligned; intentionally avoids generating `WARP.md`. |
| Amp | `AGENTS.md`, `.amp/settings.json` | Official docs sign `AGENTS.md` and workspace `.amp/settings.json` with explicit MCP trust. | Aligned structurally. |
| JetBrains Junie | `.junie/AGENTS.md` | Official docs sign `.junie/AGENTS.md` as preferred guidelines location. | Aligned structurally. |
| Qoder | `AGENTS.md`, `.mcp.json`, `.qoder/settings.json` | Official docs sign project AGENTS.md, project `.mcp.json`, and project `.qoder/settings.json`. | Aligned structurally. |
| Factory Droid | `AGENTS.md`, `.factory/mcp.json`, `.factory/settings.json`, `.factory/skills/cognitive-os/SKILL.md` | Official docs sign AGENTS.md, project MCP config, project hooks settings, and project skills. | Aligned structurally; hook parity not claimed. |
| Cline | `.clinerules/cognitive-os.md` | Official docs sign `.clinerules/` workspace rules and AGENTS.md compatibility. | Aligned structurally. |
| Continue.dev | `.continue/rules/cognitive-os.md`, `.continue/mcpServers/cognitive-os.json` | Official docs sign `.continue/rules` and `.continue/mcpServers`. | Aligned structurally. |
| Kilo Code | `AGENTS.md`, `.kilocode/rules/cognitive-os.md`, `.kilo/kilo.jsonc` | Official docs sign `.kilo/kilo.jsonc` as project config and MCP under `mcp`; rules path remains structural/contextual. | Corrected; aligned for MCP after change. |
| Zed AI | `.rules`, `.zed/settings.json` | Official docs sign `.rules` and `context_servers` in settings. | Aligned structurally. |
| Augment/Auggie | `.augment/rules/cognitive-os.md`, `.augment/mcp.json`, `.augment/README.md` | Official CLI docs sign `--rules`/`--mcp-config` invocation rather than implicit auto-loading. | Corrected; aligned as explicit CLI-file projection. |
| Goose | `.goosehints` | Official docs sign `.goosehints` and AGENTS.md as default context files. | Corrected; aligned. |
| Aider | `CONVENTIONS.md`, `.aider.conf.yml` | Official docs sign conventions file via `.aider.conf.yml` `read`. | Aligned structurally. |

## Planned / non-projected surfaces

| Harness | Current stance | Why not promoted |
|---|---|---|
| Kiro | lifecycle investigation | Official hooks are promising, but COS still needs event adapter, generated config, and runtime smoke. |
| Windsurf | planned | Official docs sign `.windsurf/rules/*.md` and MCP config, but projection driver was not part of this audit slice. |
| Google Antigravity | planned | Could not confirm a stable official project-local projection contract from Google docs in this audit. |
| MiniMax / MaxClaw | planned/provider-tooling | Current evidence is provider/tooling, not a signed local coding harness projection. |
| DeepSeek | provider-only | Official DeepSeek coding-agent docs route through existing coding agents/providers, not a first-party project-local harness. |

## Verification run

```bash
python3 -m py_compile scripts/cos_init.py scripts/acc_pipeline.py
python3 -m pytest tests/behavior/test_consumer_project_projection.py -q
python3 -m pytest tests/contracts/test_harness_implementation_phases.py tests/contracts/test_ai_agent_harness_landscape.py -q
```

ACC refresh is run after this report to regenerate current projection evidence.

## Follow-up backlog

1. Add a Windsurf structural driver from current `.windsurf/rules/*.md` + MCP docs if desired.
2. Perform a focused Codex docs review against the latest OpenAI Codex app/CLI config and decide whether `.codex/hooks.json` remains a `native-lifecycle` claim or should be reframed.
3. Implement Kiro event adapter only after config path/syntax and runtime smoke are available.
4. Add a periodic harness-docs-currentness audit script that checks every implemented harness has a current official source and a manual/runtime proof level.
