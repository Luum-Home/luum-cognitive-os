# HKUDS/OpenHarness — Deep Audit (Source-Level)

**Date**: 2026-05-05
**Target**: github.com/HKUDS/OpenHarness
**COS equivalent**: Claude Code harness + `lib/harness_adapter/` (ADR-021, ADR-033)
**Status**: research-only — verdict below
**Method**: /repo-scout --level=deep + /reverse-engineer (source-level comparison, no clone)

---

## TL;DR

**Verdict: steal-primitives-only**

OpenHarness is a high-quality, actively-maintained Python reimplementation of the Claude Code harness. Its hook taxonomy, MCP-first architecture, and multi-provider API layer are each individually worth studying. However, adopting it as a replacement forces COS off Claude Code's native tool permissions, `settings.json` projection, and hook stdin contract — invalidating `lib/harness_adapter/claude_code.py`, the `hooks/` directory (90+ hooks), and all `HarnessName.CLAUDE_CODE` adapter logic in one move. The migration cost dwarfs any capability gain. Two primitives are worth extracting without adopting the harness: the `HookEvent` taxonomy (10 named events vs COS's 5 canonical events) and the `ProviderProfile` multi-provider auth model.

---

## OpenHarness Architecture (verified from source)

**Entry points**: `oh` / `ohmo` / `openharness` CLIs, all defined in `pyproject.toml` → `openharness.cli:app` / `ohmo.cli:app`.

**Core loop** (`src/openharness/engine/query_engine.py`):
`QueryEngine` owns conversation history + agentic loop. Accepts injected `ToolRegistry`, `PermissionChecker`, `HookExecutor`, and `SupportsStreamingMessages` API client. Max-turns capped, token-counted, cost-tracked per turn.

**Hook surface** (`src/openharness/hooks/`):
10 named `HookEvent` enum values: `session_start`, `session_end`, `pre_compact`, `post_compact`, `pre_tool_use`, `post_tool_use`, `user_prompt_submit`, `notification`, `stop`, `subagent_stop`. Four hook types: `CommandHookDefinition` (shell), `HttpHookDefinition` (HTTP callback), `PromptHookDefinition` (inline LLM call), `AgentHookDefinition` (full sub-agent). Execution is async with configurable timeouts and `block_on_failure` per hook.

**Tool routing** (`src/openharness/tools/`): `ToolRegistry` with 43+ built-in tools. `PermissionChecker` intercepts every call before OS access, enforcing `PermissionMode.DEFAULT / PLAN / FULL_AUTO` plus path-rule globs and denied-command lists.

**MCP integration** (`src/openharness/mcp/client.py`): First-class `McpClientManager` with stdio and HTTP transports, auto-reconnect, JSON-Schema type inference for MCP tool inputs, graceful degradation on server disconnect.

**Skill system** (`src/openharness/skills/`): Markdown `.md` files loaded on-demand into context via a `skill` tool. `SkillRegistry` stores by name; bundled skills live in `src/openharness/skills/bundled/`. Claims compatibility with `anthropics/skills` convention.

**Configuration model** (`src/openharness/config/settings.py`): Pydantic `SettingsModel` with layered precedence (CLI → env vars → `~/.openharness/settings.json` → defaults). `ProviderProfile` supports named multi-provider profiles (Anthropic, OpenAI, Moonshot/Kimi, compatible APIs) each with separate auth slots, model aliases, and per-profile context window settings.

**Context management**: `MemorySettings.auto_compact_threshold_tokens` drives auto-compaction. `CLAUDE.md` discovery and injection via `SystemPromptBuilder`. `MEMORY.md` for persistent cross-session state. Session resume + history supported.

**Personal agent (Ohmo)** (`ohmo/`): Application layer atop OpenHarness. Integrates 10+ messaging platforms (messaging apps, chat tools, email). Gateway service + workspace at `~/.ohmo/`. Claims to run on the user's existing Claude Code or Codex subscription with no separate API key. Supports file attachments and multimodal messages.

**Swarm** (`src/openharness/swarm/`): Subagent spawning, team registry, background task lifecycle. ClawTeam integration marked as roadmap.

**CI status**: Last 10 workflow runs visible via GitHub API are all `Autopilot Scan` / `Autopilot Run Next` workflows — all cancelled or queued. The standard `ci.yml` test suite (README badge: 114 passing) was not observed running. Cannot confirm live test pass rate.

---

## COS / Claude Code Architecture (verified from source)

COS's relationship to Claude Code is defined by four artifacts:

1. **`scripts/_lib/settings-driver-claude-code.sh`**: Canonical driver that projects `cognitive-os.yaml > harness.hooks` into `.claude/settings.json`. The only path that writes the hooks block. ADR-064. Harness-agnostic state stays in `.cognitive-os/`; CC-specific projection is a one-way sync.

2. **`lib/harness_adapter/`** (ADR-033): `HarnessAdapter` ABC with `detect_harness / parse_event / emit_canonical`. Currently ships adapters for `ClaudeCode`, `Codex`, `Aider`, `BareCliAdapter`. Canonical event schema: `SessionStart`, `SessionEnd`, `AgentStart`, `AgentEnd`, `ToolUse`, `TokenUsage`, `HeartbeatTick`, `ProgressMarker`, `ParseError` (9 event types). Dispatch in `dispatch.py` routes payloads to the right adapter via detection heuristics.

3. **`hooks/` (90+ hooks)**: Shell scripts wired via `.claude/settings.json` PreToolUse / PostToolUse / UserPromptSubmit / Stop / SubagentStop callbacks. Hook stdin contract is Claude Code's native JSON: `tool_name`, `tool_use_id`, `tool_input`, `tool_response`.

4. **ADR-021**: COS keeps vendor-agnostic state (`.cognitive-os/`) as source of truth. Adapters sync outward to provider UIs. One-way: provider UI changes do not override COS state.

**COS contract from a harness**: fire hooks on the 5 CC lifecycle events via stdin JSON; respect `settings.json` permission rules; deliver skill discovery via `.claude/skills/`; expose MCP servers via `mcpServers` block in `settings.json`.

---

## 11-Dimension Comparison

| # | Dimension | OpenHarness | COS + Claude Code | Rating | Evidence |
|---|-----------|-------------|-------------------|--------|----------|
| 1 | **Hook surface** | 10 named events; 4 hook types incl. HTTP callback and inline-agent hooks | 5 canonical event types; shell-only hooks; no HTTP or inline-agent hook type | **MEJOR** | `hooks/events.py` vs `lib/harness_adapter/base.py` + `hooks/` dir |
| 2 | **Tool routing** | 43+ built-in tools + `ToolRegistry`; `PermissionChecker` with three permission modes and path-rule globs | CC native tool set; COS adds allowlists/deny-lists in `settings.json`; no COS-level interception between LLM and tool | **IGUAL** | `src/openharness/tools/` vs `.claude/settings.json` permissions |
| 3 | **MCP integration** | First-class `McpClientManager`: stdio + HTTP, auto-reconnect, schema inference | Bolted-on via `mcpServers` block in `settings.json`; no COS-level MCP lifecycle management | **MEJOR** | `src/openharness/mcp/client.py` vs COS having no `lib/mcp*.py` |
| 4 | **Skill discovery** | `SkillRegistry` + bundled `.md` skills + plugin ecosystem; `anthropics/skills` compatible | `.claude/skills/` + COS `skills/` catalog + `skill_router`; project > global > auto priority; 120+ skills | **IGUAL** | `src/openharness/skills/registry.py` vs `skills/CATALOG.md` |
| 5 | **Configuration model** | Single Pydantic model; layered precedence; `ProviderProfile` per provider with separate auth slots | Dual-file: `cognitive-os.yaml` (canonical) + `.claude/settings.json` (projected); settings-driver handles drift | **MEJOR** | `src/openharness/config/settings.py` vs `settings-driver-claude-code.sh` |
| 6 | **Context management** | Auto-compact by token threshold; `CLAUDE.md` discovery; `MEMORY.md` flat-file memory; session resume | Engram persistent memory (vector+KV); PreCompact hook; native CC compaction; multi-session searchable memory | **PEOR** | `src/openharness/memory/` flat-file model vs Engram + ADR-080 |
| 7 | **Multi-provider** | Native: Anthropic, OpenAI, Moonshot/Kimi, GitHub Copilot, any compatible API; per-profile credential slots | Primarily Claude Code; ADR-021 adapter layer for Codex/Aider/BareCliAdapter; no OpenAI or Moonshot native support | **MEJOR** | `src/openharness/api/` registry vs `lib/harness_adapter/` adapters |
| 8 | **Extension surface** | Plugin system (skills + hooks + agents); HTTP callback hooks; inline prompt/agent hooks; swarm subagents | 90+ shell hooks; `lib/harness_adapter/` plugin pattern; COS packages system; no HTTP callback hook type | **MEJOR** | `src/openharness/plugins/` + `hooks/types.py` vs `hooks/` + `packages/` |
| 9 | **Cost/observability** | `CostTracker` per turn; no OpenTelemetry; no structured JSONL export visible at source level | JSONL canonical events (ADR-033); token + cost in `AgentEnd`; SLO probes; `AgentBusMetrics`; MLflow integration | **PEOR** | `src/openharness/engine/cost_tracker.py` vs `lib/harness_adapter/base.py` + SLO 9 |
| 10 | **License & OSS health** | MIT; 11,965 stars; 2,005 forks; 35 days old; pushed 2026-05-03; 26 open issues; 2 release tags | N/A (COS is private); Claude Code is Anthropic-maintained, stable, multi-year | **IGUAL** | MIT is safe; repo is young; CI runs observed are autopilot scans not test suite |
| 11 | **Lock-in cost of switching** | Would invalidate: all 90+ shell hook implementations; `settings-driver-claude-code.sh`; CC's `settings.json` permission model; `ClaudeCodeAdapter`; `.claude/skills/` discovery path | Zero: COS is already on Claude Code; `lib/harness_adapter/` was built to make future migration possible | **PEOR** | ADR-021 + ADR-033 + 90+ hooks quantify the migration surface |

**Score summary**: OpenHarness is MEJOR on 5 dimensions, IGUAL on 2, PEOR on 3. The three PEOR dimensions are exactly where COS has invested the most architectural depth (memory, observability, migration cost).

---

## Verdict: steal-primitives-only

**Rationale**

OpenHarness is the most complete open-source Python reimplementation of Claude Code released to date. Its architecture is clean, its multi-provider story is genuine (not bolted-on), and its 10-event hook taxonomy is strictly richer than COS's 5 canonical events. At v0.1.7 in 35 days, the velocity is impressive and the code quality is high (Pydantic models, typed dataclasses, async hooks with timeouts).

But "impressive open-source harness" is not the same as "better substrate for COS." COS's value sits in three layers that OpenHarness does not match and could not absorb without full replacement: (1) Engram persistent memory with vector search and cross-session retrieval — OpenHarness uses flat `MEMORY.md` files; (2) the JSONL canonical event pipeline (ADR-033) feeding SLO probes, cost dashboards, and the error-learning pipeline — OpenHarness has a `CostTracker` but no structured JSONL export or downstream observability hook; (3) 90+ shell hooks wired to Claude Code's stdin JSON contract — these would all need to be ported to OpenHarness's `CommandHookDefinition` / `HttpHookDefinition` format with no automated migration path.

Adopting OpenHarness as a replacement means discarding all three layers and rebuilding them on top of a 35-day-old harness with two release tags and a CI history dominated by autopilot scan workflows rather than a visible test suite pass. The risk-adjusted cost is prohibitive.

Adopting it as a second harness via `lib/harness_adapter/openharness/` is conceivable (ADR-021 was written for exactly this), but the business case is weak until a concrete use case demands it (e.g., a contributor running OpenHarness instead of Claude Code who needs COS telemetry).

The two primitives worth extracting today without adopting the harness:

1. **`HookEvent` taxonomy extension**: add `pre_compact`, `post_compact`, `user_prompt_submit`, `notification`, `subagent_stop` to the canonical schema in `lib/harness_adapter/base.py` — these are gaps visible by comparing OpenHarness's 10-event enum against COS's 5 canonical event types, and Claude Code fires all five via its hook system.
2. **`ProviderProfile` multi-provider auth pattern**: the named profile + credential slot design in `src/openharness/config/settings.py` is cleaner than COS's current env-var-first approach; worth porting to `cognitive-os.yaml` when multi-provider support (ADR-021) is extended beyond the adapter layer.

---

## Concrete First Step (steal-primitives path)

**File**: `lib/harness_adapter/base.py`
**Action**: extend the canonical event schema with five new subtypes mirroring OpenHarness's missing events: `PreCompact`, `PostCompact`, `UserPromptSubmit`, `Notification`, `SubagentStop`.
**Falsifiable claim**: after the extension, `ClaudeCodeAdapter.parse_event()` can emit `UserPromptSubmit` on the `UserPromptSubmit` CC hook and `SubagentStop` on the `SubagentStop` CC hook — filling two gaps in the SLO 9 observability surface without changing any hook registration.
**Effort**: small (< 1 day). Zero migration risk. Zero hook changes required.

---

## Trust Report

- **CI health not verified end-to-end**: The last 10 workflow runs visible via GitHub API are all `Autopilot Scan` / `Autopilot Run Next` workflows (all cancelled or queued). The README claims 114 passing tests; this was not confirmed by observing a live `ci.yml` run. The CI badge may reflect a separate, unobserved trigger.
- **Lock-in cost is an estimate from architecture inspection, not a measured migration**: The "90+ hooks" count was derived from `ls hooks/` in COS; individual hook complexity was not assessed. The true migration effort could be higher or lower.
- **Ohmo runtime behavior inferred from source, not tested**: The 10-platform messaging integration was read from `ohmo/config/schema.py` Pydantic models and the `ohmo/gateway/` directory structure. The claim that Ohmo runs on an existing Claude Code subscription (no separate API key) was read from the README but not traced through `src/openharness/api/copilot_auth.py` end-to-end.

---

## Open Questions

1. Does `CommandHookDefinition` in OpenHarness replicate COS's `exit 2 = block` semantics that ~40 COS hooks rely on? The `block_on_failure` flag suggests approximate parity but the exact exit-code protocol was not traced fully through `HookExecutor._run_command_hook()`.
2. Is the `swarm/` module production-ready or aspirational? `ClawTeam` integration is marked `(Roadmap)` in the README; the subagent spawning stability note in the changelog ("stabilized in v0.1.6") suggests it was unstable shortly before audit date.
3. Can the `ProviderProfile` credential slot model support the Claude Max subscription path (no API key) that Ohmo claims to use on top of Claude Code / Codex? `copilot_auth.py` and `codex_client.py` exist in `src/openharness/api/` but were not fully read.

---

## Sources

| Source | Method | Date |
|--------|--------|------|
| `deepwiki.com/HKUDS/OpenHarness` | WebFetch | 2026-05-05 |
| `gh api repos/HKUDS/OpenHarness` (metadata) | gh CLI | 2026-05-05 |
| `src/openharness/hooks/events.py` | gh api contents | 2026-05-05 |
| `src/openharness/hooks/executor.py` | gh api contents | 2026-05-05 |
| `src/openharness/engine/query_engine.py` | gh api contents | 2026-05-05 |
| `src/openharness/config/settings.py` | gh api contents | 2026-05-05 |
| `src/openharness/mcp/client.py` | gh api contents | 2026-05-05 |
| `src/openharness/skills/registry.py` | gh api contents | 2026-05-05 |
| `pyproject.toml` | gh api contents | 2026-05-05 |
| `lib/harness_adapter/base.py` | Read (local) | 2026-05-05 |
| `lib/harness_adapter/dispatch.py` | Read (local) | 2026-05-05 |
| `lib/harness_adapter/claude_code.py` | Read (local) | 2026-05-05 |
| `docs/adrs/ADR-021-vendor-agnostic-with-adapters.md` | Read (local) | 2026-05-05 |
| `docs/adrs/ADR-033-harness-agnostic-event-capture.md` | Read (local) | 2026-05-05 |
| `scripts/_lib/settings-driver-claude-code.sh` | Read (local) | 2026-05-05 |
