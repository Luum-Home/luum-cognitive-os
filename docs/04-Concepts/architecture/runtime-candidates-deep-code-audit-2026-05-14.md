# Runtime Candidates Deep Code Audit — Pi, Gollem/Fugue, Hermes, Goose

Date: 2026-05-14

This audit compares four runtime candidates for improving Cognitive OS harnesses
and/or backing a standalone `cosd` / `agent-service` runtime. It is based on
fresh shallow clones under `/tmp/cos-runtime-candidates-2026-05-14`, plus local
code inspection of each repo's runtime loop, tool lifecycle, permissions,
events, sessions, compaction, providers/auth, and extension surfaces.

## Clone snapshot

| Candidate | Repository | Commit inspected | Latest commit observed |
|---|---|---|---|
| Pi / pi-mono | `https://github.com/badlogic/pi-mono.git` | `0b54c87e24ba94b0a2ac43501959fd35c48deb1b` | 2026-05-14 `fix(release): finalize Windows ARM64 binary support` |
| Gollem / Fugue | `https://github.com/fugue-labs/gollem.git` | `354a9f892d8ea8df95e455783f77607f33cd0224` | 2026-04-20 `Experimenting with running forever` |
| Hermes Agent | `https://github.com/NousResearch/hermes-agent.git` | `cd64bed55ee816536cd0ad0cebf75568af3fca09` | 2026-05-14 `Merge pull request #21012 from stephenschoettler/fix/ci-pr-check-unblock` |
| Goose | `https://github.com/block/goose.git` | `401f8e86ba0092076b43161b8f4693edee67ceec` | 2026-05-14 `Dynamically refresh skill instructions each turn (#9217)` |

## Repo shape observed

| Candidate | Dominant implementation | Approx inspected files | Top-level shape |
|---|---:|---:|---|
| Pi | TypeScript | 837 files, 674 TS files | `packages/agent`, `packages/coding-agent`, `packages/ai`, `packages/tui`, `packages/web-ui` |
| Gollem / Fugue | Go | 453 files, 422 Go files | `core`, `ext`, `cmd`, `provider`, `examples`, `e2e` |
| Hermes Agent | Python + TS UI | 3,409 files, 1,681 Python files | `agent`, `tools`, `gateway`, `cron`, `acp_adapter`, `docs`, `dashboard`-style frontend files |
| Goose | Rust + TS UI/docs | 3,001 files, 421 Rust files, 1,109 TS/TSX files | `crates/goose`, `crates/goose-cli`, `crates/goose-server`, `crates/goose-mcp`, `ui`, `documentation` |

## Executive verdict

| Candidate | Best at | Weak at | COS role |
|---|---|---|---|
| Pi | Direct runtime lifecycle mapping for model/tool loop, pre/post tool hooks, events, compaction, resources, provider auth. | Not a cross-IDE standard; TypeScript runtime; COS primitives must compile into Pi extensions/tools rather than become Pi-native source of truth. | Short-term runtime mapping baseline and lifecycle-harness reference. |
| Gollem / Fugue | Go embeddable runtime substrate: typed agents/tools, hooks, approval, event bus, traces, codetools, streaming, Temporal/durable orchestration. | Small public adoption; less turnkey coding-agent product; COS must assemble CLI/IDE/service UX and tool suite. | Best medium-term Go backend candidate for `cosd` / `agent-service`. |
| Hermes Agent | Full product/gateway: skills, memory, self-improvement, cron, messaging, many tools, ACP bridge, terminal backends. | High overlap with COS memory/skills/governance/product surfaces; large Python product, not clean library substrate. | Product benchmark and selective pattern source, not first runtime dependency. |
| Goose | Mature Rust agent ecosystem: MCP extensions, ACP, permissions, inspectors, security/sandbox direction, server/CLI/desktop. | Integration surface is broad; primitive mapping is less direct than Pi; could become a parallel COS. | Best external runtime/safety/interoperability comparator and possible adapter target. |

## Pi / pi-mono code audit

### What the code shows

Pi has the cleanest explicit mapping to COS hook-style lifecycle primitives.
`packages/agent/src/types.ts` defines `BeforeToolCallResult` with `block` and
`reason`, `AfterToolCallResult` with `content`, `details`, `isError`, and
`terminate`, plus `BeforeToolCallContext` / `AfterToolCallContext` with the
assistant message, raw tool call, validated args, and agent context.

`AgentLoopConfig` then exposes:

- `transformContext` before model conversion;
- dynamic `getApiKey` for OAuth-style providers;
- `shouldStopAfterTurn`;
- `prepareNextTurn`;
- steering and follow-up message queues;
- `toolExecution` sequential/parallel mode;
- `beforeToolCall` and `afterToolCall`.

`packages/agent/src/agent-loop.ts` proves the semantics: arguments are prepared
and validated, `beforeToolCall` can return `{ block: true }` before execution,
tool execution emits updates, and `afterToolCall` can rewrite the result/error or
terminate before final tool result events are emitted.

The coding-agent layer adds a richer extension harness:

- `packages/coding-agent/src/core/extensions/runner.ts` handles extension events
  and `resources_discover`.
- `packages/coding-agent/src/core/extensions/types.ts` includes
  `resources_discover`, `session_before_compact`, and related event contracts.
- `packages/coding-agent/src/core/agent-session.ts` bridges session events,
  compaction, resource discovery, and extension runner emissions.
- `packages/coding-agent/src/core/resource-loader.ts` loads skill paths returned
  by extensions.

Provider/auth strength is also real: `packages/ai` has OAuth flows for Anthropic,
OpenAI Codex, GitHub Copilot, token refresh, and `ANTHROPIC_OAUTH_TOKEN` /
`ANTHROPIC_API_KEY` handling.

### COS mapping

| COS primitive | Pi surface |
|---|---|
| `PreToolUse` | `beforeToolCall` after validation, before execution |
| `PostToolUse` | `afterToolCall` before final result emission |
| Session start/end | extension/session events in coding-agent layer |
| Compaction checkpoint | `session_before_compact` and compaction events |
| Skills | `resources_discover.skillPaths` + resource loader |
| Rules/context | `transformContext`, extension context events, prompt augmentation |
| Provider policy | `getApiKey`, provider adapters, OAuth registry |
| Evidence | event subscribers + COS JSONL writer adapter |

### Strengths

- Strongest direct lifecycle mapping of the four.
- Tool preflight can block before execution with validated args.
- Tool postflight can mutate result/error and terminate.
- Event model is detailed enough for session/turn/message/tool/compaction.
- Resource discovery can carry skills/prompts/themes.
- Provider/auth layer is unusually mature for subscription/OAuth flows.

### Weaknesses / risks

- TypeScript/Node runtime may be a larger technology insertion than a Go worker
  under `cosd`.
- Pi's primitives are runtime primitives, not COS primitive contracts.
- The adapter must avoid making Pi tool/resource definitions the source of truth.
- Cross-IDE projection still belongs to COS; Pi does not solve Cursor/Copilot/
  Goose/OpenCode parity.

### COS recommendation

Use Pi as the **lifecycle-harness reference** and as the fastest candidate for a
runtime mapping proof. The integration should be generated from
`manifests/primitive-contracts.yaml` into a Pi extension/resource bundle.

## Gollem / Fugue code audit

### What the code shows

Gollem is not only a thin SDK. Its `core` package has enough runtime structure to
serve as a serious embedded backend:

- `core/agent.go` defines the central `Agent[T]` and tool loop.
- `core/hooks.go` defines lifecycle hooks: `OnRunStart`, `OnRunEnd`,
  `OnModelRequest`, `OnModelResponse`, `OnToolStart`, `OnToolEnd`, `OnTurnStart`,
  `OnTurnEnd`, guardrail/output validation hooks, and `OnContextCompaction`.
- `core/tool.go` defines typed tools, result validators, max retries, sequential
  vs concurrency-safe tool execution, strict schemas, approval requirement,
  stateful tools, and timeouts.
- `core/agent.go` enforces tool approval before execution when
  `RequiresApproval` is set, publishes approval/run/tool events to `EventBus`,
  fires `OnToolStart`/`OnToolEnd`, traces tool calls/results, applies timeouts,
  and serializes tool result content.
- `core/eventbus.go` gives typed pub/sub; `core/runtime_events.go` defines run
  and tool events with run id / parent run id / timestamps.
- `ext/codetool` provides coding-agent tools and background process management.
- `ext/temporal` provides durable workflow scaffolding and approval signals.
- `ext/mcp` provides stdio/SSE/HTTP MCP integration.
- `cmd/gollem/serve_test.go` shows an HTTP/SSE server path with event bus,
  AG-UI session, and approval bridge wiring.

### COS mapping

| COS primitive | Gollem / Fugue surface |
|---|---|
| `PreToolUse` | `RequiresApproval`, tool approval callback, `OnToolStart`, tool prepare/filter functions |
| `PostToolUse` | `OnToolEnd`, per-tool/global result validators, trace export |
| Session/run start/end | `OnRunStart`, `OnRunEnd`, runtime events |
| Provider request/response | `OnModelRequest`, `OnModelResponse`, middleware/interceptors |
| Compaction | `OnContextCompaction`, deep/context packages |
| Skills/rules | Go prompt/tool packages or generated Go values from COS contracts |
| Streaming | `RunStream`, stream utilities, SSE serve path |
| Durability | `ext/temporal`, `ext/orchestrator`, stateful tools, checkpoints |
| Evidence | EventBus subscribers + trace exporter + COS JSONL adapter |

### Strengths

- Best fit for a Go-first `cosd` / `agent-service` backend.
- Typed Go construction makes adapter boundaries explicit and testable.
- Strong hooks/middleware/event bus story.
- Approval + event bus maps cleanly to COS governed primitives.
- Durable execution and orchestration are closer to a service runtime than Pi's
  local coding-agent emphasis.
- Lower architectural overlap with COS than Hermes or Goose.

### Weaknesses / risks

- Much lower public adoption than Pi/Goose/Hermes.
- Not as turnkey as Pi for coding-agent UX.
- COS must build/verify CLI, IDE bridge, filesystem/code tool completeness,
  session storage, permission UX, and projection compiler.
- Static Go composition can hide stale primitives unless reload/delete semantics
  are designed.

### COS recommendation

Use Gollem / Fugue as the **medium-term embedded backend candidate**. A valid
spike must clone a repo, load context, edit safely, run tests, block a destructive
tool before execution, stream events, recover/resume or expose durable state, and
emit COS primitive intervention rows plus a projection fidelity row.

## Hermes Agent code audit

### What the code shows

Hermes is a full autonomous product, not merely a runtime library. The README
advertises a self-improving agent with persistent memory, autonomous skill
creation, skill self-improvement, FTS5 session search, Honcho user modeling,
cron, subagents, terminal backends, gateway delivery across Telegram/Discord/
Slack/WhatsApp/Signal/Email, and research/batch trajectory flows.

The repo structure matches that product claim:

- `agent/` contains memory, skill, prompt, transport, model adapter, LSP,
  context, compression, curator/self-improvement, credential, and guardrail
  modules.
- `tools/` contains the actual tool suite: terminal, file ops, patching, browser,
  web search/extract, MCP, memory, skills, cron, image/video, process control,
  platform integrations, and more.
- `gateway/` contains multi-channel messaging platforms.
- `cron/` contains scheduler logic.
- `acp_adapter/` maps Hermes tools and sessions into ACP.

The ACP adapter is substantial. `acp_adapter/tools.py` maps Hermes tool names to
ACP `ToolKind` values and gives polished tool-call rendering for `read_file`,
`write_file`, `patch`, `terminal`, `delegate_task`, `session_search`, `memory`,
`skill_manage`, browser, cron, and messaging tools. `acp_adapter/permissions.py`
bridges ACP `request_permission` outcomes to Hermes approval semantics:
`allow_once`, session allow, permanent allow, and deny.

Hermes also has a pure tool-loop guardrail module: `agent/tool_guardrails.py`
classifies idempotent vs mutating tools and tracks repeated/no-progress tool-call
patterns. `agent/shell_hooks.py` implements user-approved shell hook allowlists.

### COS mapping

| COS primitive | Hermes surface |
|---|---|
| Skills | Native skills system and `skill_manage` tool |
| Memory | Native memory/user model/session search |
| Tool safety | Approval callbacks, guardrails, allowlists, ACP permission bridge |
| Product delivery | Gateway platforms + cron |
| ACP | `acp_adapter` session/events/tools/permissions |
| Coding tools | File, patch, terminal, browser, LSP-adjacent and process tools |
| Evidence | Native trajectory/session/tool traces, but not COS JSONL unless adapted |

### Strengths

- Broadest product feature set.
- Strong benchmark for long-running personal/remote agent UX.
- Has first-class memory, skill evolution, cron, messaging, subagents, toolsets.
- ACP adapter work is practical and relevant to COS.
- Existing tool suite is rich.

### Weaknesses / risks

- Highest overlap with COS: memory, skills, self-improvement, governance,
  product personality, gateway, and runtime all exist inside Hermes.
- Large Python product surface makes it hard to embed as a narrow runtime.
- COS would need strict boundaries to avoid becoming a Hermes fork/plugin.
- Evidence/audit semantics are Hermes-native, not COS primitive-fidelity native.

### COS recommendation

Use Hermes as a **product/UX benchmark and pattern mine**, not as the first
runtime base. The safest extraction targets are ACP permission/tool rendering,
cron/gateway UX, self-improving skill lifecycle patterns, and remote/long-running
agent ergonomics.

## Goose code audit

### What the code shows

Goose is a mature Rust agent platform with server, CLI, MCP, ACP, session,
permission, extension, and safety subsystems.

Key surfaces:

- `crates/goose/src/agents/agent.rs` defines the main `Agent`, `AgentConfig`,
  `AgentEvent`, extension manager, prompt manager, tool confirmation router,
  retry manager, tool inspection manager, hook manager, and container field.
- The default inspection manager registers `SecurityInspector`,
  `EgressInspector`, LLM-based `AdversaryInspector`, `PermissionInspector`, and
  `RepetitionInspector`.
- `crates/goose/src/tool_inspection.rs` defines `ToolInspector`,
  `InspectionResult`, and `InspectionAction::{Allow,Deny,RequireApproval}`.
- `crates/goose/src/permission/permission_confirmation.rs` defines permission
  decisions: `AlwaysAllow`, `AllowOnce`, `Cancel`, `DenyOnce`, `AlwaysDeny`.
- `crates/goose/src/agents/tool_execution.rs` handles tool approvals by emitting
  action-required messages, waiting for confirmation, dispatching allowed tools,
  recording always-allow/always-deny choices, and returning declined tool
  responses when denied.
- `crates/goose/src/agents/agent.rs` runs `PreToolUse` and `PostToolUse` hooks
  around `dispatch_tool_call` through its hook manager.
- `crates/goose/src/session/session_manager.rs` and `session/extension_data.rs`
  provide persistent sessions and extension state.
- `crates/goose-mcp` and extension manager code provide strong MCP orientation.
- `crates/goose-server` exposes server routes for config, permissions, sessions,
  tools, replies, action-required, and MCP app proxy/sandbox behavior.

### COS mapping

| COS primitive | Goose surface |
|---|---|
| `PreToolUse` | Goose hook manager around `dispatch_tool_call`; tool inspectors/permissions before execution |
| `PostToolUse` | `with_post_tool_hook` around tool result processing |
| Safety policies | Security/Egress/Adversary/Permission/Repetition inspectors |
| Permission UX | action-required + permission confirmation router |
| MCP tools/resources | Extension manager + Goose MCP crates |
| ACP/session | ACP tests/server/session support and session manager |
| Sessions | SQLite-backed session manager and extension state |
| Streaming/server | `goose-server` reply/session event routes |

### Strengths

- Strongest safety/interoperability harness of the four.
- MCP and extension ecosystem are first-class.
- ACP integration is real enough to test against.
- Permission model is richer than simple allow/block.
- Inspectors are a good pattern for COS primitive validators.
- Public adoption is high and active.

### Weaknesses / risks

- Less direct than Pi for a clean one-to-one COS lifecycle mapping, because the
  core architecture routes through MCP/extension/inspector/permission systems.
- Larger integration surface than Gollem if COS wants to own `agent-service`.
- Could become a parallel platform beside COS rather than a backend adapter.
- Rust server/desktop ecosystem may be more disruptive than a small Go worker if
  COS prioritizes a minimal service runtime.

### COS recommendation

Use Goose as the **safety/interoperability benchmark** and a serious external
adapter candidate. COS should copy/adapt the concepts of tool inspectors,
permission levels, MCP extension state, ACP session behavior, and action-required
UX into its own `RuntimeHarnessContract` instead of replacing COS governance with
Goose wholesale.

## Feature comparison matrix

| Feature | Pi | Gollem / Fugue | Hermes Agent | Goose |
|---|---:|---:|---:|---:|
| Direct pre-tool block | Excellent (`beforeToolCall`) | Good (`RequiresApproval`, prepare/approval path) | Good (approval/guardrails) | Excellent (inspectors + permissions + hooks) |
| Post-tool mutation/validation | Excellent (`afterToolCall`) | Excellent (`OnToolEnd`, validators) | Medium-good (tool result classification/adapters) | Good (`PostToolUse`, result handling) |
| Runtime event bus | Good | Excellent | Medium-good | Good |
| Streaming | Good | Excellent | Good | Good |
| Session persistence | Good | Medium; needs app layer | Excellent product layer | Excellent |
| Compaction hooks | Excellent | Good | Good | Good |
| MCP | Medium | Good | Good | Excellent |
| ACP | Low-medium | Low-medium / AG-UI direction | Good | Excellent |
| Provider/auth/subscription | Excellent | Medium | Good | Good/excellent |
| Tool approval UX | Medium-good | Good, framework-level | Good product-level | Excellent |
| Coding tool suite | Good | Medium-good but needs proof | Excellent | Good |
| Durable execution | Medium | Excellent | Medium-good | Medium-good |
| Embeddable runtime fit | Medium | Excellent | Low-medium | Medium |
| Product completeness | Medium | Low-medium | Excellent | Excellent |
| Risk of replacing COS | Medium | Low | High | Medium-high |
| Public adoption | High | Very low | Very high | High |

## What COS should take from each

### From Pi

- Canonical `before_tool_call` / `after_tool_call` contract shape.
- Validated-args preflight before execution.
- Result override semantics after execution.
- Session/turn/message/tool/compaction event vocabulary.
- Extension resource discovery for skills/prompts/themes.
- OAuth/subscription provider resolver pattern.

### From Gollem / Fugue

- Go `RuntimeAdapter` backend shape.
- Typed tools and strict schema generation.
- Tool approval callback and approval lifecycle events.
- Event bus with run id / parent run id lineage.
- Durable orchestration and long-running task store patterns.
- Trace exporter and stateful tool checkpoint patterns.

### From Hermes

- Product-level skills/memory/self-improvement lifecycle.
- ACP tool rendering and permission bridge ergonomics.
- Cron/scheduled automations with platform delivery.
- Gateway/multi-channel UX patterns.
- Tool-loop guardrail taxonomy: idempotent vs mutating vs no-progress loops.

### From Goose

- Tool inspector interface with composable security, egress, adversary,
  permission, and repetition checks.
- Rich permission outcomes: allow once, always allow, deny once, always deny.
- Action-required UX and confirmation routing.
- MCP extension/session-state management.
- ACP/session/server patterns.
- Sandbox/proxy separation for MCP app UI.

## Recommended COS harness strategy

Do not choose one winner as the new source of truth. Treat each as a benchmark
for a different layer:

```text
Pi              -> lifecycle harness contract
Gollem / Fugue  -> embedded Go backend runtime
Goose           -> safety / interoperability / MCP / ACP harness
Hermes          -> product UX / skills / memory / long-running agent benchmark
```

The next COS artifact should be a `RuntimeHarnessContract` backed by
`manifests/primitive-contracts.yaml`:

```yaml
runtime_harness_contract:
  lifecycle:
    before_tool_call: required
    after_tool_call: required
    on_model_request: recommended
    on_model_response: recommended
    on_session_start: required
    on_session_end: required
    on_compaction: recommended
  permissions:
    outcomes: [allow_once, allow_always, deny_once, deny_always, ask]
    evidence_required: true
  events:
    run_id: required
    parent_run_id: recommended
    tool_call_id: required
    timestamp: required
  projection:
    generated_from: manifests/primitive-contracts.yaml
    target_artifacts_are_source_of_truth: false
```

Then run four separate proofs:

1. **Pi proof**: generate a Pi extension from one COS primitive contract and
   block a destructive command with `beforeToolCall`.
2. **Gollem proof**: embed a Go worker under a COS adapter, run a repo edit/test,
   block one destructive tool, stream events, and emit COS evidence.
3. **Goose proof**: express one COS primitive as a Goose inspector/permission/hook
   adapter and compare emitted evidence to COS fidelity rows.
4. **Hermes proof**: port one COS skill/memory/product workflow as a UX benchmark,
   not as a runtime dependency.

## Decision guidance

| If the goal is... | Choose first |
|---|---|
| Fastest lifecycle mapping proof | Pi |
| Least structural break for a Go service backend | Gollem / Fugue |
| Best safety/interoperability model | Goose |
| Best product UX benchmark | Hermes |
| Broadest community/adoption confidence | Goose or Pi |
| Most complete autonomous product | Hermes |
| Lowest risk of replacing COS semantics | Gollem / Fugue |

## Bottom line

Pi, Gollem/Fugue, Hermes, and Goose are all useful, but at different layers.
For COS harness improvement, the right move is not migration. The right move is
extracting a unified harness contract:

```text
COS primitive contracts
  -> RuntimeHarnessContract
  -> candidate-specific adapter/projection
  -> runtime smoke/evidence
  -> primitive projection fidelity report
```

Pi gives the clearest lifecycle vocabulary. Gollem gives the cleanest embedded Go
runtime substrate. Goose gives the strongest safety/interoperability model.
Hermes gives the richest product and long-running-agent benchmark.
