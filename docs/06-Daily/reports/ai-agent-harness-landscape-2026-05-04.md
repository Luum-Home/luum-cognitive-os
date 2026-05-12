# AI agent harness landscape review — 2026-05-04

## Purpose

This report reconciles Cognitive OS repository documentation with current official/product documentation for agentic coding IDEs, CLIs, and hosted coding agents. It is intentionally a **candidate landscape**, not an implementation claim.

The operating rule is the proof-level doctrine from `docs/04-Concepts/architecture/harness-proof-levels.md`:

- `native-lifecycle`: COS lifecycle hooks/events are projected and tested for that harness.
- `runtime-smoke`: a real account-backed CLI/IDE smoke was executed and recorded.
- `structural`: project-local files/configs are generated and shape-tested from official docs; runtime is not claimed.
- `none`: no local projection proof exists.

## Repository sources reviewed

The old broad list lives mainly in:

- `docs/04-Concepts/root/ide-compatibility.md`
- `docs/08-References/business/portability-plan.md`
- `docs/08-References/business/features.md`
- `docs/04-Concepts/root/component-sources.md`
- `docs/04-Concepts/root/distributed-architecture.md`
- `docs/04-Concepts/architecture/multi-ide-harness-implementation-plan.md`
- `docs/04-Concepts/architecture/harness-implementation-roadmap.md`
- `manifests/harness-projection.yaml`

The important finding is that older docs used compatibility labels such as `FULL` and `HIGH` from documentation analysis alone. That language is now too strong. The maintained contract is proof-level based.

## Current implemented harnesses in this repo

| Harness | Status | Proof level | Current COS surface |
|---|---:|---:|---|
| Claude Code | implemented | native-lifecycle | `.claude/settings.json`, hooks, rules, skills |
| OpenAI Codex | implemented | native-lifecycle | `.codex/hooks.json`, instructions/driver surface |
| Cursor | implemented | structural | `.cursor/rules/cognitive-os.mdc`, `.cursor/mcp.json` |
| VS Code Copilot | implemented | structural | `.github/copilot-instructions.md`, `.vscode/mcp.json` |
| OpenCode | implemented | structural | `opencode.json` |
| Qwen Code | implemented | structural | `.qwen/settings.json`, `QWEN.md` |
| Kimi Code CLI | implemented | structural | `AGENTS.md`, `.kimi/mcp.json`, `.kimi/README.md` |
| Shell / CI | implemented | structural | `.cognitive-os/shell-ci-projection.json`, generated workflow, projected commands |

## Official-doc-backed candidate backlog

These candidates have enough official documentation to justify backlog tracking, but not necessarily enough evidence for implementation or native lifecycle parity.

| Candidate | Surface type | Officially documented signals | COS next classification |
|---|---|---|---|
| Gemini CLI | CLI | `GEMINI.md` memory/context, MCP commands, skills commands, non-interactive mode | high-priority structural candidate |
| Kiro IDE/CLI | IDE + CLI | steering files, custom agents, MCP, lifecycle/tool hooks | high-priority native-lifecycle investigation |
| Cline | VS Code extension + CLI/headless | `.clinerules/`, `AGENTS.md`, MCP, skills, hooks docs | high-priority structural/native investigation |
| Roo Code | VS Code extension | `.roo/mcp.json`, rules, MCP, but official docs announce shutdown on 2026-05-15 | archive/compatibility-only unless successor is chosen |
| Continue.dev | IDE extension/agent config | local configs for models, rules, tools, `.continue/mcpServers` | structural candidate |
| Aider | CLI | `CONVENTIONS.md` via `--read` or `.aider.conf.yml` | structural CLI candidate, likely rules-only |
| Goose | CLI/Desktop/API | local agent, MCP, `--instructions`, CLI sessions | structural CLI candidate |
| Kilo Code | VS Code/CLI | project-level `.kilo/kilo.jsonc`, MCP | structural candidate |
| Augment/Auggie | CLI/IDE agent | CLI flags for `--rules`, MCP settings, permissions | structural candidate |
| JetBrains Junie | IDE + CLI | `.junie/AGENTS.md`, root `AGENTS.md` fallback, MCP, terminal interface | structural candidate |
| Zed AI | IDE/ACP | `.rules`, `AGENTS.md`, `CLAUDE.md`, MCP context servers | structural candidate |
| Amp Code | CLI/editor integration | `AGENTS.md`, agents-md tools, MCP config | structural candidate |
| Warp | Terminal agent | `AGENTS.md`/`WARP.md` project rules, global rules, MCP/permissions docs | structural candidate |
| Factory Droid | CLI/Desktop/CI | `droid`, `droid exec`, AGENTS.md, skills, MCP, hooks, plugins | high-priority structural candidate |
| Qodo Gen CLI | CLI/IDE | custom agents and per-agent MCP TOML | structural candidate |
| Qoder | IDE + CLI | CLI uses `AGENTS.md`; IDE/CLI MCP support; subagents | structural candidate |
| Tabnine Agent | IDE agent | autonomous agent, `.tabnine/mcp_servers.json` | structural candidate if instructions surface is found |
| OpenHands | CLI/SDK/server | CLI mode, `.openhands/microagents/repo.md`, config | structural/adapter candidate |
| SWE-agent | benchmark/CLI agent | YAML configs via `--config` | lab/benchmark adapter candidate |
| GitHub Copilot coding agent | hosted GitHub agent | repository custom instructions, `AGENTS.md` support in GitHub-hosted coding agent, MCP | hosted structural candidate distinct from VS Code Copilot |
| Sourcegraph Cody | IDE/enterprise assistant | Cody agentic context and MCP integration | structural/enterprise candidate |
| Devin | hosted agent + MCP server | official Devin MCP server for other agents; hosted execution | hosted/remote-agent candidate, not local projection by default |
| Replit Agent | hosted workspace agent | Replit Agent + MCP connectors | hosted/no local projection candidate |
| Lovable | hosted/desktop app agent | Agent mode; MCP personal connectors/local MCP in desktop app | hosted/no repo-local projection unless docs expose project instruction files |
| Bolt.new | hosted web agent | release/docs surface and connector/MCP claims; no repo-local projection signed here | hosted/no repo-local projection |
| MiniMax Mini-Agent / mmx-cli | provider tools + agent sample | `mmx-cli`, Mini-Agent, MCP/skills signals | provider/tooling candidate, not yet coding-harness projection |
| DeepSeek | provider | official guide integrates DeepSeek into existing coding agents | provider-only until first-party coding harness appears |
| Google Antigravity | IDE/agent | already tracked as planned, but local projection remains unsigned here | keep planned/none |
| Windsurf | IDE agent | already tracked as planned; needs current official rules/MCP verification before implementation | planned structural candidate |
| Trae | IDE agent | MCP and `.rules` signals exist, but official syntax maturity is uncertain | research candidate |

## Gaps found versus the previous repo list

New or under-modeled surfaces to add to the backlog:

- Qoder (IDE + CLI, Qwen/Alibaba-adjacent surface)
- JetBrains Junie, not just generic JetBrains AI
- Amp Code
- Goose
- Factory Droid as a CLI/CI-capable harness, not only a hosted platform
- Kilo Code
- GitHub Copilot coding agent as a hosted GitHub workflow, separate from VS Code Copilot
- MiniMax `mmx-cli` / Mini-Agent as provider/tooling surface separate from MaxClaw
- Tabnine Agent with MCP settings
- Replit/Lovable/Bolt hosted MCP surfaces, but not as local projection claims

## Deprecated or caution surfaces

- Roo Code is still useful for understanding `.roo/mcp.json` and VS Code extension patterns, but official docs state a shutdown date of 2026-05-15. COS should not invest in a new first-class driver unless there is a successor/migration decision.
- “DeepSeek support” should stay provider-level. Their official docs route users through existing coding agents rather than a first-party project-local coding harness.
- Hosted builders such as Replit Agent, Lovable, Bolt.new, and Devin may be important ecosystem surfaces, but they are not the same problem as projecting COS files into a consumer Git working tree.

## Recommended priority order

1. Add this backlog to a machine-readable manifest and enforce proof-level metadata.
2. Update stale compatibility docs to remove `FULL`/`HIGH` claims based only on doc reading.
3. Implement Gemini CLI structural projection next: project-local `GEMINI.md` plus `.gemini/settings.json`/MCP placeholder if official settings docs confirm scope.
4. Investigate Kiro lifecycle hooks as the first non-Claude/Codex candidate that may legitimately approach `native-lifecycle`.
5. Implement AGENTS.md-native structural harnesses in batches: Warp, Amp, Junie, Qoder, Factory Droid.
6. Implement rules/MCP-directory harnesses in batches: Cline, Continue, Kilo, Zed, Augment, Goose, Aider.
7. Keep hosted/provider candidates out of default ACC projection until they expose project-local, testable config or an explicit hosted adapter contract.

## Manual review checklist

- [ ] Confirm every candidate URL still resolves to official docs before implementation.
- [ ] Do not promote any candidate from `none` to `structural` without an automated temp-project projection test.
- [ ] Do not promote any candidate to `runtime-smoke` without recorded CLI/IDE/account-backed execution evidence.
- [ ] Do not promote any candidate to `native-lifecycle` without hook/event semantics and a contract test for event mapping.
- [ ] Keep hosted/provider surfaces separate from local consumer-project projection.
