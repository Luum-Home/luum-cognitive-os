# Multi-IDE Harness Implementation Plan

Generated: 2026-05-04

## Purpose

Turn the ACC harness backlog into an evidence-backed rollout path. A harness can be product scope without being runtime-supported. The promotion rule is:

```text
planned → structural projection → optional runtime smoke → native lifecycle parity
```

Only the first implemented slice is in this change: structural projection for OpenCode, VS Code Copilot, and Cursor. These drivers write project-local instruction/config files and prove them in temporary consumer projects. They do not claim native Claude/Codex lifecycle hook parity.

## Source signals used

| Harness | Source signal | COS interpretation |
|---|---|---|
| OpenCode | Official config supports `opencode.json`, `instructions`, `mcp`, plugins, permissions. See https://opencode.ai/docs/config/ and https://opencode.ai/docs/mcp-servers. | Implement structural config projection now. Runtime CLI smoke later. |
| VS Code Copilot | Official VS Code docs auto-detect `.github/copilot-instructions.md`, support `AGENTS.md`, and document workspace/user MCP config. See https://code.visualstudio.com/docs/copilot/customization/custom-instructions and https://code.visualstudio.com/docs/copilot/customization/mcp-servers. | Implement instruction + workspace MCP placeholder projection now. Account-backed extension smoke later. |
| Cursor | Official docs describe project rules under `.cursor/rules`, MDC metadata, `AGENTS.md`, and MCP configuration. See https://docs.cursor.com/en/context and https://docs.cursor.com/advanced/model-context-protocol. | Implement project rule + MCP placeholder projection now. Account-backed Cursor smoke later. |
| Windsurf | Official docs describe Cascade MCP management/admin whitelist, but the repo has not signed a project-local rules/config surface. See https://docs.windsurf.com/windsurf/cascade/mcp. | Keep planned until project-local instruction/rule contract is confirmed. |
| Qwen Code | Official docs describe project `.qwen/settings.json`, `mcpServers`, and hierarchical context files such as `QWEN.md`. See https://qwenlm.github.io/qwen-code-docs/en/users/configuration/settings/ and https://qwenlm.github.io/qwen-code-docs/en/users/features/mcp/. | Implemented structural projection; account-backed runtime smoke later. |
| Kimi Code | Official docs describe Kimi Code CLI, `--work-dir`, `--mcp-config-file`, MCP configuration, and project-level `AGENTS.md`; VS Code extension remains account-backed runtime proof. See https://www.kimi.com/code/docs/en/kimi-code-cli/reference/kimi-command.html and https://www.kimi.com/help/kimi-code/cli-customization. | Implemented structural CLI projection; account-backed runtime smoke later. |
| Google Antigravity | Current local-project config evidence is not signed in this repo from a primary source. | Keep planned; research before projection. |
| MiniMax MaxClaw | Current evidence points to hosted/agent-platform behavior, not local repo harness projection. | Treat as provider/hosted target, not IDE harness, unless local project config emerges. |
| DeepSeek | Provider/API compatibility rather than first-party coding IDE projection. | Keep provider-via-existing-harness. |

## Phase plan

### Phase 0 — Ratchet baseline

Status: done.

- ACC `--fail-new` blocks new capability/finding debt.
- Broad defaults are strict: a new local file aligned only by `scripts/**`, `rules/*.md`, or `skills/**/SKILL.md` is review debt.

### Phase 1 — Structural instruction harnesses

Status: implemented in this slice for OpenCode, VS Code Copilot, and Cursor.

Deliverables:

- `cos_init.py --default/--full --harness opencode` writes `opencode.json`.
- `cos_init.py --default/--full --harness vscode-copilot` writes `.github/copilot-instructions.md` and `.vscode/mcp.json`.
- `cos_init.py --default/--full --harness cursor` writes `.cursor/rules/cognitive-os.mdc` and `.cursor/mcp.json`.
- ACC temp-project projection runs those harnesses for default/full profiles.
- Automated tests verify generated files without requiring accounts.

Non-claims:

- No native lifecycle hook parity.
- No account-backed IDE runtime invocation.
- No guarantee that every MCP server exists or authenticates.

### Phase 2 — Shell/CI formal harness

Status: done.

Deliverables:

- `shell-ci` is promoted from planned to implemented.
- `cos_init.py --default/--full --harness shell-ci` installs the normal `.cognitive-os/` surface and invokes `project_shell_ci.py`.
- ACC records `shell-ci/default` and `shell-ci/full` projection counts.
- Workflow syntax and generated command-driver tests cover the structural baseline.

### Phase 3 — Qwen/Windsurf/Kimi structural candidates

Status: in progress. Qwen Code and Kimi Code CLI are implemented; Windsurf remains planned.

Deliverables:

- Qwen: `cos_init.py --default/--full --harness qwen-code` generates `.qwen/settings.json` and `QWEN.md` with conservative `mcpServers` placeholder and COS context references.
- Windsurf: only generate project-local files after confirming a project-scoped rules/instructions contract from primary docs.
- Kimi: `cos_init.py --default/--full --harness kimi-code` generates a bounded `AGENTS.md` block plus `.kimi/mcp.json` and `.kimi/README.md`; account-backed runtime smoke remains optional.

### Phase 4 — Provider/hosted surfaces

Status: planned.

Deliverables:

- DeepSeek: provider compatibility proof through existing harnesses, not IDE projection.
- MiniMax/MaxClaw: hosted-agent or OpenClaw-compatible proof if a local repo projection surface emerges.
- Google Antigravity: research gate before implementation.

### Phase 5 — Account-backed runtime proof

Status: planned/manual/optional.

Deliverables:

- Optional manual tests for real IDE launches when accounts/licenses exist.
- Runtime smoke logs stored as reports, never required for normal CI.
- Clear split between structural projection support and runtime parity.

## Checklist

- [x] ACC `--fail-new` strict gate exists.
- [x] OpenCode structural projection implemented and tested.
- [x] VS Code Copilot structural projection implemented and tested.
- [x] Cursor structural projection implemented and tested.
- [x] Shell/CI promoted to implemented harness semantics.
- [x] Qwen structural projection researched and implemented.
- [ ] Windsurf project-local projection surface confirmed from primary docs.
- [x] Kimi Code CLI projection mode selected and implemented.
- [ ] DeepSeek provider proof separated from IDE projection.
- [ ] MiniMax/MaxClaw classified as hosted/provider unless local repo config emerges.
- [ ] Google Antigravity researched against primary docs before any projection claim.
- [ ] Account-backed optional runtime smoke tests documented per IDE.

## Acceptance criteria

1. A harness is `implemented` only if `scripts/cos_init.py` can project it into a temp consumer project and automated tests assert generated files.
2. A harness marked `planned` never contributes implemented projection proof in ACC.
3. Account-dependent runtime tests are optional/manual and cannot block local CI by default.
4. Every promotion updates `manifests/harness-projection.yaml`, this plan, ADRs/manual tests, and ACC reports.

## Proof-level boundary

See [Harness Proof Levels](harness-proof-levels.md). `implemented` does not mean universal runtime support. For structural harnesses it means project-local files/configs are generated from official docs and shape-tested; account-backed runtime smoke remains optional.
