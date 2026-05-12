# IDE and agent harness compatibility

> Current status of Cognitive OS projection across AI coding IDEs, CLIs, and hosted coding agents.

Last reviewed: 2026-05-04.

## Compatibility language

This document no longer uses `FULL`, `HIGH`, or percentage-based compatibility labels. Those labels implied runtime behavior that was not always manually tested.

Use the proof levels from `docs/04-Concepts/architecture/harness-proof-levels.md` instead:

| Proof level | Meaning |
|---|---|
| `native-lifecycle` | Native lifecycle hooks/events are projected and tested for this harness. |
| `runtime-smoke` | A real account-backed CLI/IDE runtime smoke was executed and recorded. |
| `host-plugin-lifecycle` | Host exposes plugin/tool lifecycle events that can support runtime enforcement, but COS has not signed runtime primitive projection/smoke for that host yet. |
| `structural` | Project-local files/configs are generated and shape-tested from official docs. Runtime execution is not claimed. |
| `none` | The surface is planned, hosted/provider-only, unsupported, or not yet researched enough for projection. |

## Source of truth

- Implemented and planned harness projection metadata: `manifests/harness-projection.yaml`
- Broader candidate backlog: `manifests/ai-agent-harness-landscape.yaml`
- Current landscape review: `docs/06-Daily/reports/ai-agent-harness-landscape-2026-05-04.md`
- Proof-level doctrine: `docs/04-Concepts/architecture/harness-proof-levels.md`

## Current implemented COS projection

| Harness | Proof level | Notes |
|---|---|---|
| Claude Code | `native-lifecycle` | Reference lifecycle harness. |
| OpenAI Codex | `native-lifecycle` | Codex harness projection with current repo contract tests. |
| Cursor | `structural` | Project rules/MCP placeholder only; no account-backed runtime claim. |
| VS Code Copilot | `structural` | Copilot instructions/workspace MCP placeholder only; no account-backed runtime claim. |
| OpenCode | `structural` + `host-plugin-lifecycle` candidate | Current COS proof is `opencode.json` structural projection only; official OpenCode permissions/plugins expose `tool.execute.before` / `tool.execute.after`, so runtime enforcement should use an OpenCode plugin adapter before any parallel COS layer is invented. |
| Qwen Code | `structural` | `.qwen/settings.json` and `QWEN.md` shape-tested only. |
| Kimi Code CLI | `structural` | `AGENTS.md` and `.kimi/mcp.json` shape-tested only. |
| Shell / CI | `structural` | Generated commands/workflow shape-tested only. |

## Candidate classes

| Class | Examples | COS stance |
|---|---|---|
| Next structural CLI/IDE candidates | Gemini CLI, Cline, Continue, Aider, Goose, Kilo, Augment, Junie, Zed, Amp, Warp, Factory Droid, Qodo, Qoder, Tabnine | Add drivers only after official-doc-backed project-local config is captured and temp-project tests exist. |
| Lifecycle-hook investigation candidates | Kiro, Cline, Factory Droid | Investigate whether hook/event semantics can map to COS lifecycle. Do not assume parity. |
| Hosted/remote-agent candidates | GitHub Copilot coding agent, Devin, Replit Agent, Lovable, Bolt.new | Treat separately from local consumer-project projection. Use hosted adapter contracts if implemented later. |
| Provider/tooling candidates | DeepSeek, MiniMax `mmx-cli`/Mini-Agent, Sourcegraph MCP/Cody | Track as provider/tool/MCP surfaces unless first-party repo-local harness projection exists. |
| Deprecated/caution candidates | Roo Code | Official docs announce shutdown on 2026-05-15; keep compatibility notes but avoid new first-class investment until migration target is chosen. |

## Non-goals

- This document does not claim COS works in every listed IDE/CLI.
- This document does not replace account-backed runtime smoke tests.
- This document does not authorize writing user-global config files such as `~/.config/*`, `~/.qwen/*`, `~/.kimi/*`, or IDE profile settings.
