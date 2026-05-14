# Standalone Agent Runtime Adapter Options

This note captures the current boundary between Cognitive OS as a harness
projection layer and Cognitive OS as a standalone service that runs on its own
instance. It focuses on the missing runtime-adapter layer and on whether Pi,
Goose, OpenCode, Hermes, holaOS-style patterns, or a native Go/Rust runtime
should supply it.

## Current conclusion

Cognitive OS already has service-shaped infrastructure, but it does **not** yet
have a complete autonomous agent runtime.

Implemented or partially implemented service tracks:

- `scripts/cos_daemon.py` / `cosd`: guarded daemon and control-plane/task API.
- `packages/agent-service/`: ADR-291 HTTP + SSE contract skeleton for
  harness-independent clients.
- Docker/Engram service surfaces described in
  [`cos-service-runtime-boundary.md`](cos-service-runtime-boundary.md).

The missing layer is the runtime piece that owns the model/tool loop:

```text
client / UI / scheduler / webhook
  -> agent-service HTTP + SSE contract
  -> cosd control plane / queue / task admission
  -> runtime adapter                 # missing or not yet productized
  -> model loop + tool loop          # missing or not yet productized
  -> filesystem/git/shell/MCP/browser tools
  -> COS gates, audit, memory, cost, trust evidence
```

`cosd` is therefore closer to a **control-plane / task API / operational
daemon** than to a full autonomous coding-agent runtime. The runtime adapter is
what would turn the service skeleton into a self-running agent instance.

## What "runtime adapter" means

A runtime adapter is the boundary that lets Cognitive OS execute a turn without
assuming Claude Code, Codex, Cursor, or another IDE harness owns the loop.

A minimal interface should cover:

```python
class RuntimeAdapter:
    def start_session(...): ...
    def run_turn(...): ...
    def stream_events(...): ...
    def abort(...): ...
    def list_tools(...): ...
    def get_state(...): ...
```

The adapter must expose enough lifecycle surface for COS to run primitives
before and after model/provider/tool activity:

- context construction;
- provider request/response;
- tool-call preflight;
- tool-result postflight;
- session start/end;
- compaction/checkpoint boundaries;
- streaming events;
- abort/retry/failure events.

## Pi / pi-mono

Pi is not just another instruction-file harness. It is closer to a runtime for
building and running an agent: agent loop, typed tools, session state,
compaction, settings, provider abstraction, TUI/web surfaces, and extension
events.

Observed Pi surfaces relevant to COS:

- `AgentLoopConfig.beforeToolCall` and `afterToolCall` can block or rewrite tool
  execution/results.
- Extension events include `session_start`, `context`, `before_provider_request`,
  `after_provider_response`, `before_agent_start`, `agent_start`, `agent_end`,
  `turn_start`, `turn_end`, `message_*`, `tool_call`, `tool_result`,
  `tool_execution_*`, `session_before_compact`, and `session_compact`.
- Tools are first-class typed objects with name, label, description, TypeBox
  parameter schema, execution mode, execute handler, prompt snippets/guidelines,
  and optional renderers.
- Resources can be discovered through extension-provided `skillPaths`,
  `promptPaths`, and `themePaths`.
- The provider layer can use API keys and OAuth/subscription logins. For
  Anthropic, Pi supports `ANTHROPIC_API_KEY` and an OAuth login flow for Claude
  Pro/Max. It does not need to shell out to the Claude Code CLI to run, but its
  Anthropic OAuth path includes Claude Code compatibility headers/tool naming.

Pi's primitive model is not the same as COS's. Pi primitives are runtime pieces:
tools, events, extensions, resources, settings, session state, compaction, and
streams. COS primitives are governed agentic constructs with lifecycle, scope,
evidence, projection, and audit contracts. A COS-on-Pi integration should
therefore compile COS primitives into a Pi extension rather than pretending the
systems have a one-to-one primitive taxonomy.


### Is Pi's strong side harnessing?

Yes, if "harness" means the runtime harness around an autonomous agent loop:
model calls, typed tools, pre/post tool interception, extension events, streaming,
session state, provider/auth handling, and compaction boundaries. Pi is strong in
that layer because COS can map many lifecycle primitives directly onto Pi runtime
surfaces such as `beforeToolCall`, `afterToolCall`, tool execution events,
session events, and compaction events.

No, if "harness" means universal cross-IDE projection of the same primitive into
Claude Code, Codex, OpenCode, Cursor, Copilot, Goose, shell CI, and future IDEs.
Pi does not replace COS's portability/control-plane layer. It is one strong
runtime backend that COS can target, not the source of truth for COS primitive
semantics.

The safe integration claim is therefore:

```text
COS primitive contract
  -> Pi extension / Pi tools / Pi event handlers
  -> Pi runtime execution
  -> normalized COS evidence and fidelity report
```

The unsafe claim is:

```text
Pi primitive = COS primitive
```

Pi can be the execution harness for COS, but COS must still own primitive
contracts, projection fidelity, evidence ledgers, stale projection policy, and
cross-target truth claims.

### COS primitive mapping to Pi

| COS primitive/surface | Pi adapter target |
|---|---|
| `skills/*/SKILL.md` | `resources_discover.skillPaths` and optional slash commands/context instructions |
| `rules/RULES-COMPACT.md` | `context` injection or `before_agent_start.systemPrompt` augmentation |
| `SessionStart` hooks | `session_start` |
| `PreToolUse` hooks | `tool_call` or `beforeToolCall` |
| `PostToolUse` hooks | `tool_result` or `afterToolCall` |
| `Stop` hooks | `agent_end` / `session_shutdown` |
| Provider policy | `before_provider_request` / `after_provider_response` |
| Compaction checkpoints | `session_before_compact` / `session_compact` |
| Audit and metrics | event subscribers plus COS JSONL/Engram writers |
| Engram retrieval | `context` / `before_agent_start` memory injection |

A Pi adapter MVP should be a Pi extension that:

1. exposes selected COS skills as resources;
2. injects compact COS rules/context;
3. blocks one representative unsafe tool call before execution;
4. records one representative tool result/error after execution;
5. persists a session-end summary/audit row.

## OpenCode

OpenCode is currently modeled as a harness/projection target rather than a
runtime library replacement for Pi. The COS manifest already records its
structural projection and future native enforcement path:

- `opencode.json` structural projection exists.
- Native runtime enforcement should use OpenCode's plugin/permission surfaces,
  especially `tool.execute.before` and `tool.execute.after`.
- COS must not claim OpenCode runtime enforcement until a plugin adapter and
  runtime smoke are signed.

For standalone service architecture, OpenCode is best treated as another
`RuntimeAdapter` candidate or harness target, not as the default internal COS
runtime unless its server/plugin API becomes the chosen execution backend.

## Hermes Agent

Hermes Agent appears to be a separate Python runtime rather than a Pi-based
runtime. COS has adopted or studied Hermes patterns for skills, memory,
feedback/review, context compression, gateways, and self-improvement, but Hermes
should not be described as "using Pi" without a source-backed dependency.

Hermes is useful as a reference for the **native runtime** path: build and own
the agent loop, gateways, tools, memory, and service behavior directly instead
of embedding Pi.

## OpenClaw

OpenClaw is the clearest example of the "product/gateway on top of Pi" pattern.
It demonstrates the opposite path from Hermes: use Pi as the execution runtime
and build product/channel/gateway layers around it.

For COS, OpenClaw is evidence that Pi can serve as a real product runtime, but
it does not prove that COS should migrate to Pi. COS's value remains the
governance/evidence/memory plane; Pi would be one possible runtime backend.

## holaOS

holaOS is tracked under ADR-259 as a **patterns-only** reference. The local ADRs
characterize it as an Electron + TypeScript agent-computer platform with
Fastify/SQLite and a persistent inspectable workspace shared by humans and
agents.

Important boundary:

- holaOS source, identifiers, comments, fixtures, documentation text, and
  directory structure are blocked for adoption.
- Ideas, policies, state machines, algorithms, and observable behaviors may be
  reimplemented only through the clean-room process in ADR-259.

Existing ADRs mention a `pi` harness in the holaOS research context, but that is
not sufficient to claim that holaOS is wholly built on `pi-mono`. Treat holaOS
as a pattern reference for service/runtime design, not as a dependency option.

Patterns already adopted or planned through clean-room ADRs include grant-signed
API access, memory governance, tool-replay budgeting, and tool-result envelopes.

## Go and Rust alternatives to Pi

There are alternatives, but they have different maturity and fit.

### Rust candidates

| Candidate | Fit | Notes |
|---|---|---|
| Goose | Strong runtime-adapter candidate | Rust agent runtime with MCP/sandbox/permissions direction; useful as a runtime backend or adapter target. |
| aictl | Lightweight single-binary reference | Good reference for local single-binary multi-provider/MCP ergonomics; less complete as a coding-agent platform. |
| Aether | Strong Rust harness/library candidate | Cloned repo shows Rust workspace, ACP, headless mode, MCP-only tools, provider traits, TUI, and Rust library mode; good Goose comparator. |
| thClaws | Strong product/workspace candidate, watch for base | Cloned repo shows Rust workspace with GUI/CLI/non-interactive/web serve surfaces, MCP, skills, plugins, permissions, sandbox, sessions, subagents, teams, and Claude Code auth via Agent SDK; product-shaped and broad. |

### Go candidates

| Candidate | Fit | Notes |
|---|---|---|
| Hector | Framework candidate | Go agent runtime/framework with tools/MCP/A2A-style direction; may require COS to build coding-agent/session pieces. |
| trpc-agent-go | Framework candidate | Useful for a native Go implementation, not a drop-in coding-agent runtime. |
| LangDAG | Conversation-runtime/reference candidate | Cloned repo shows Go library/CLI/API with SQLite DAG persistence, SSE streaming, tool-use flows, and multi-provider support; stronger than a pure graph library, but still not a full coding-agent workspace. |
| Gollem / Fugue Labs | Strong embedded runtime candidate | Go-first agent runtime/framework with durable execution, streaming, structured output, tool approval, event bus, provider support, and codetool direction. Stronger than a mere reference, but still needs a COS-owned coding-agent product layer. |

The Go path likely means building more COS-native runtime code. The Rust path
has stronger ready-made runtime candidates, especially Goose, but still requires
adapter proof.


### Can Gollem / Fugue become a mature coding-agent runtime?

Yes, but the maturity path is different from Pi.

Pi already looks like a coding-agent runtime: it has a model/tool loop, explicit
pre/post tool hooks, sessions, compaction, extension resources, streams, and
provider/auth surfaces. Gollem / Fugue looks more like a Go-first production
agent runtime substrate: durable execution, structured output, multi-provider
streaming, tool approval, event bus, middleware/guardrails, orchestration, and a
single-binary deployment shape. Its public examples and docs point toward a
coding-agent use case through codetools, approval callbacks, and editor-facing
event buses, but COS should still treat the full coding-agent product as
something to assemble and verify.

What Gollem / Fugue would need to be "coding-agent mature" for COS:

1. complete filesystem/code tool suite: read, write, edit, multi-edit, grep,
   search, bash, git, LSP/diagnostics, test runner, and patch application;
2. coding-agent session model: stable run/session ids, transcripts, event log,
   resumability, compaction checkpoints, replay, and audit;
3. permission and approval policy: allow/ask/deny by tool, path policies,
   destructive-operation gates, and user approval UX;
4. headless and IDE surfaces: CLI/TUI or HTTP/SSE, cancellation, progress events,
   editor bridge, and reconnectable streams;
5. COS adapter compiler: `manifests/primitive-contracts.yaml` to Go values,
   middleware, tool approval, event subscribers, and normalized COS JSONL
   evidence.

The minimum spike acceptance test should be:

```text
clone a repo
load context
make a safe edit
run tests
block one destructive tool call before execution
stream progress/events
resume or recover after a forced interruption
emit `.cognitive-os/metrics/primitive-interventions.jsonl`
produce a primitive projection fidelity row
```

If that spike passes, Gollem / Fugue can be treated as a serious Go coding-agent
runtime candidate. Until then, describe it as a strong embedded runtime substrate,
not as a turnkey Claude Code/Codex/Pi replacement.

Comparison against Pi:

| Dimension | Pi | Gollem / Fugue |
|---|---|---|
| Coding-agent shape out of the box | More direct | Needs assembly around codetools/runtime primitives |
| Runtime durability / service fit | Good | Very strong direction |
| Language/runtime fit for COS service | TypeScript/Node | Go single-binary shape |
| Pre/post tool mapping | Very direct: `beforeToolCall` / `afterToolCall` | Direct through approval, middleware, hooks, event bus |
| Editor/product layer | More product/runtime shaped | Needs COS-owned or adapter-owned surface |
| Primitive contract compiler | Still required | Still required |

Recommended use:

```text
Short-term runtime mapping baseline: Pi
Medium-term COS service/daemon backend candidate: Gollem / Fugue
```


## Primitive ontology mismatch

Each candidate runtime has primitives, but those primitives do not mean the same
thing as Cognitive OS agentic primitives.

Cognitive OS primitives are governed, evidence-producing, projectable agentic
constructs. Runtime primitives in Pi, Goose, Aether, Gollem, Hector, LangDAG,
OpenCode, Hermes, OpenClaw, or thClaws are primarily execution constructs.

```text
COS primitive
  -> compile / project / adapt
runtime primitive
  -> execute
runtime event / result
  -> normalize back into COS evidence
```

The integration goal is therefore **translation**, not migration. COS should keep
its canonical primitive model and adapt it into the runtime's ontology through a
stable `RuntimeAdapter` or future primitive IR.

| System | Main primitive ontology | COS implication |
|---|---|---|
| Cognitive OS | Skills, hooks, rules, agents, memory, MCP, metrics, policies, audit evidence | Canonical governance/evidence layer with lifecycle, scope, projection, and acceptance criteria. |
| Pi | Typed tools, extension events, resources, settings, sessions, compaction, streams | Compile COS skills/rules/hooks into Pi resources and event handlers; do not claim one-to-one primitive parity. |
| Goose | Extensions, MCP tools, permissions, providers, sessions, recipes/config | Strong runtime/MCP/permission model; COS governance must wrap or project into those runtime surfaces. |
| Aether | MCP servers/tools, prompt files, providers, ACP sessions, headless logs, TUI/IDE surfaces | Project COS tools through MCP and COS rules/skills through prompt/config resources; normalize headless/ACP logs into COS evidence. |
| thClaws | Skills, plugins, MCP servers, agents/subagents, permissions, sessions, memory/KMS, teams | Vocabulary overlaps with COS, but it is product/workspace-shaped; treat as adapter target, not canonical primitive source. |
| Gollem / Fugue Labs | `Agent[T]`, typed tools, middleware, guardrails, event bus, streams, orchestrators, teams, memory | Best library-shaped mapping: COS hooks become middleware/guardrails/event subscribers; COS audit owns resulting evidence. |
| Hector | Apps, agents, tools, tasks, sessions, checkpoints, MCP/A2A, Studio/Admin API | Service/platform ontology; wrap tasks/sessions/checkpoints behind COS task and evidence contracts. |
| LangDAG | Conversation nodes/edges, branches, tool-use/tool-result records, sessions, SSE events | Useful as conversation/session substrate; COS still supplies coding-agent tools, permissions, and governance. |
| OpenCode | Providers, agents, commands, plugins, permissions, tool hooks, sessions | Treat as harness/plugin projection target; map COS pre/post tool hooks to plugin hooks. |
| Hermes Agent | Agents, skills, tools, gateways, memory, review/feedback loops | Product/runtime ontology overlaps with COS; use as reference unless an ADR chooses dependency integration. |
| OpenClaw | Channels, tools, sessions, gateway/product layer, Pi runtime surfaces | Evidence for product-on-runtime architecture; not a canonical COS primitive model. |
| aictl | CLI agents, sessions, hooks, MCP, provider proxy/server, local secrets | Reference for single-binary ergonomics only; license blocks default adoption and server ontology is provider-proxy-first. |

### Adapter examples

| COS primitive/surface | Runtime examples | Normalized COS evidence |
|---|---|---|
| `PreToolUse` hook | Pi `beforeToolCall`; OpenCode `tool.execute.before`; Gollem middleware/tool validator; Goose/Aether permission or MCP elicitation; Hector guardrail/task policy | Block/allow decision, policy version, input summary, redaction status, audit row. |
| `PostToolUse` hook | Pi `afterToolCall`; OpenCode `tool.execute.after`; Gollem tool-result validator/event subscriber; LangDAG tool-result node; Hector trace/checkpoint | Tool result envelope, validation outcome, cost/timing, error class, evidence pointer. |
| Skill | Pi `skillPaths`; Aether skill MCP/prompt config; thClaws `SKILL.md`; trpc-agent-go SKILL.md tools; Gollem typed tool/prompt package | Skill identity, version, trigger reason, inputs/outputs, acceptance criteria result. |
| Rule | Prompt/context injection, middleware policy, guardrail, provider/request interceptor | Rule version, enforcement point, applied/not-applicable reason. |
| Memory | Engram context injection, runtime memory store, LangDAG conversation branch, thClaws KMS | Retrieval query, selected facts, citations/evidence, write approval status. |
| Session / compaction | Pi compaction events, Hector checkpoints, LangDAG branch snapshots, Gollem snapshots/traces | Session id, checkpoint id, compacted summary, replay/recovery metadata. |
| Streaming | ADR-291 SSE, Pi streams, Gollem stream events, Aether headless JSON, LangDAG SSE, Hector streaming API | Normalized event type, sequence id, run id, payload hash, terminal status. |

### Design rule

Do not let any runtime redefine the COS primitive taxonomy.

Allowed:

> COS projects its canonical agentic primitives into `<runtime>` primitives and
> normalizes runtime events back into COS evidence.

Not allowed:

> COS primitives are Pi tools.

> COS primitives are Gollem middleware.

> COS primitives are Hector tasks.

Those statements collapse governance primitives into execution primitives and
make portability harder. The portable contract is the adapter/IR boundary, not
any single runtime's ontology.


## Primitive construction mechanics

The more important risk is not only that runtimes name primitives differently;
it is that they **construct** primitives through different mechanisms. COS should
therefore compare candidates by construction mechanics before choosing an
adapter.

Evaluation axes:

1. **Definition locus** — file, config, code API, database row, server object, or
   remote MCP server.
2. **Registration** — static registry, runtime plugin discovery, config loader,
   dependency injection, API create call, or workspace scan.
3. **Schema** — typed language schema, JSON Schema, YAML/TOML schema, prompt-only
   convention, or provider-native tool shape.
4. **Activation** — always loaded, contextual trigger, explicit command, route,
   session config, or model-selected tool.
5. **Execution boundary** — in-process function, subprocess, MCP server, HTTP
   service, daemon, or provider-side operation.
6. **Interception points** — before/after model request, before/after tool call,
   guardrails, middleware, permission prompts, checkpoints, or event bus.
7. **Persistence** — none, local files, JSONL, SQLite, task/checkpoint store,
   session transcript, vector/memory store, or external database.
8. **Evidence surface** — trace, stream event, audit row, checkpoint, run result,
   callback, or plugin event.

| System | How primitives are constructed | Adapter risk for COS |
|---|---|---|
| Cognitive OS | Mostly filesystem-first: `skills/*/SKILL.md`, `rules/*.md`, `hooks/*.sh`, YAML manifests, JSONL ledgers, Engram observations, plus Python/Go support libraries. Primitives carry governance metadata and are projected into harnesses. | Canonical source of truth should remain COS-owned. Runtime adapters must preserve lifecycle, scope, acceptance, and evidence metadata. |
| Pi | Code-first TypeScript runtime objects plus extension/resource discovery. Tools are typed objects; hooks are extension events or `beforeToolCall`/`afterToolCall`; skills/prompts/themes are resource paths; sessions/compaction are runtime state. | Good event mapping, but COS shell hooks and docs primitives must be compiled into a Pi extension/resource bundle. Risk: losing COS metadata if projected as plain Pi tools/resources. |
| Goose | Extension/MCP-first runtime. Capabilities are built from MCP servers, built-in extensions, permissions, providers, session state, and recipes/config. | COS would likely project tools/policies as MCP/extension config. Risk: COS pre/post evidence becomes Goose permission/session data unless explicitly normalized. |
| Aether | Config/library/MCP-first. Agents are configured from project files; prompts are markdown arrays; all tools enter through MCP servers; providers implement traits; surfaces include TUI, ACP, headless logs, and Rust library mode. | Clean if COS exposes primitives as MCP servers plus prompt/config resources. Risk: COS hooks/rules need a separate evidence wrapper because Aether intentionally keeps tools external via MCP. |
| thClaws | Product-workspace construction. Skills/plugins/MCP/agents/hooks/permissions/sessions/memory are first-class repo/runtime objects loaded by the app and served through GUI/CLI/web modes. | Vocabulary overlap can mislead. It can absorb many COS ideas, but COS must avoid letting thClaws become the canonical registry unless chosen as a product base. |
| Gollem / Fugue Labs | Code/library-first Go construction. Agents, tools, middleware, guardrails, hooks, event bus subscribers, orchestrators, team tasks, and memory stores are Go values composed at compile/runtime. | Best fit for an embedded adapter, but COS file primitives need code-generated or hand-written Go adapter objects. Risk: static Go composition may hide dynamic COS primitive changes unless reload/projection is designed. |
| Hector | Service/config/API construction. Agents/apps/tools/guardrails/tasks/sessions/checkpoints are created through Go packages, YAML configs, Admin/API surfaces, and SQL-backed runtime state. | Good for external service delegation. Risk: duplicate `cosd`/ADR-291 task/session concepts unless Hector objects are wrapped as backend execution records only. |
| LangDAG | Graph/storage-first construction. Conversation nodes, edges, branches, tool-use/tool-result records, providers, and SSE events are persisted around a SQLite conversation DAG and API/SDK. | Strong for session/conversation substrate. Risk: not enough construction surface for COS skills/hooks/rules unless COS builds those around LangDAG. |
| OpenCode | Harness/plugin construction. Agents, commands, skills, plugins, permissions, providers, tool runtime, and sessions are built through `.opencode/` files, TypeScript plugins, and app/server internals. | Good projection target. Risk: treating OpenCode plugin hooks as equivalent to COS hooks without preserving COS acceptance/evidence metadata. |
| Hermes Agent | Product/runtime construction. Agents, skills, tools, gateways, memory, review and feedback loops are built into a Python runtime/product stack. | Useful reference for native COS runtime. Risk: too much overlap; adopting it could replace COS governance primitives rather than host them. |
| OpenClaw | Product/gateway construction around a runtime. Channels, tools, sessions, gateway behaviors, and product surfaces are constructed as app/gateway objects, with Pi-like runtime backing. | Useful pattern for product-on-runtime. Risk: product concepts become the integration center instead of COS primitive governance. |
| trpc-agent-go | Go framework construction. Agents, graph/chain/cycle agents, callbacks, invocation context, A2A/Claude Code adapters, memory/skills/tools are Go objects and framework modules. | Useful secondary Go adapter candidate. Risk: framework abstractions may compete with COS RuntimeAdapter unless scoped to execution only. |
| aictl | CLI/config construction. Agents/sessions/hooks/MCP/provider proxy/secrets are constructed as CLI/server config and local state. | Reference-only due license. Risk: server is provider-proxy-first, so COS would still need its own full runtime construction. |


### Source-backed construction notes — 2026-05-14

This pass inspected cloned source under `/tmp/cos-runtime-candidates`. The goal
was to identify construction mechanics, not feature marketing.

| Runtime | Source evidence | Construction flow | Load / activation | Interception / evidence | COS adapter consequence |
|---|---|---|---|---|---|
| Pi | `packages/agent/src/types.ts`, `packages/agent/src/agent-loop.ts` | `AgentLoopConfig` receives model, context converter, `transformContext`, tool execution policy, `beforeToolCall`, `afterToolCall`, steering/follow-up queues, and API-key resolver. Tools are typed runtime objects in `context.tools`; tool calls are extracted from assistant messages and executed sequentially or in parallel. | Constructed in TypeScript at agent-loop setup; context is transformed before each model call; tools are model-selected from `context.tools`. | `beforeToolCall` can block; `afterToolCall` can override content/details/error/terminate; loop emits message/tool/turn/agent events. | Best direct mapping for COS lifecycle hooks, but COS filesystem primitives must be compiled into TypeScript extension/config objects and event subscribers. |
| Goose | `crates/goose/src/builtin_extension.rs`, `crates/goose/src/tool_inspection.rs`, `crates/goose/src/tool_monitor.rs`, `crates/goose-server/src/session_event_bus.rs` | Built-in extensions register spawn functions into a global registry; tool governance is via `ToolInspector` implementations coordinated by `ToolInspectionManager`; session events publish through a replayable bus. | Extensions are registered/discovered; inspectors are added to the manager and run in order for tool requests. | Inspectors return inspection actions; session event bus assigns monotonic sequence IDs and supports replay/live subscription. | COS gates can map to inspectors and event subscribers, but COS must own the evidence normalization because Goose evidence is permission/session-event shaped. |
| Aether | `packages/aether-core/src/agent_spec.rs`, `packages/aether-project/src/agent_config.rs`, `packages/aether-project/src/agent_catalog.rs`, `packages/aether-cli/src/runtime.rs`, `packages/mcp-servers/src/lib.rs`, `packages/llm/src/tools.rs` | Authored agent config resolves into `AgentSpec`; prompts are resolved from text/globs/MCP instructions; MCP config sources are spawned; tools arrive as MCP `ToolDefinition`s and pass through `ToolFilter`; `AgentBuilder::from_spec(...).tools(...)` constructs runtime. | Project config/catalog selects an agent; runtime loads built-in and configured MCP servers; allowed/denied tool patterns filter tool definitions before agent spawn. | Evidence exits through MCP client events, headless/agent events, ACP/TUI surfaces, and provider/tool results; tools are externalized through MCP. | Clean adapter if COS exposes tools/skills/rules as MCP + prompt/config resources. COS pre/post evidence wrapper must sit around MCP calls, not inside arbitrary tool functions. |
| thClaws | `crates/core/src/skills.rs`, `plugins.rs`, `hooks.rs`, `permissions.rs`, `mcp.rs`, `agent.rs`, `session.rs`, `subagent.rs` | Skills are directories with `SKILL.md`, parsed lazily/eagerly into `SkillDef` and held in `SkillStore`; plugins bundle skills/commands/MCP servers through manifests and registries; hooks are shell commands in settings; permissions are dynamic runtime modes/sinks. | Workspace/user/plugin discovery loads stores; GUI/CLI/web modes share the same engine; permission mode is consulted at each tool dispatch; hooks fire from configured lifecycle events. | Hook commands receive environment variables and are timeout-bounded/fire-and-forget; permission sinks produce allow/deny/plan behavior; sessions/subagents/teams emit product events. | Very close vocabulary to COS, but construction is product-owned. Adapter must prevent double-governance and should treat thClaws as an external runtime/product target unless COS intentionally adopts its registry. |
| Gollem / Fugue Labs | `core/tool.go`, `core/hooks.go`, `core/agent_middleware.go`, `core/eventbus.go`, `ext/codetool/*`, `ext/orchestrator/*` | Go code constructs `Agent[T]`, `FuncTool[P]`, `ToolDefinition`, `ToolHandler`, typed `RunContext`, lifecycle `Hook`, request/stream middleware, guardrails, event-bus subscribers, orchestrator tasks, and codetools. | Registered through Go functional options at agent construction; tools can prepare/filter before model requests; model-selected tools execute in-process; orchestrator/team primitives run through Go stores/schedulers. | Hooks cover run/model/tool/turn/guardrail/output/compaction; middleware wraps model requests/streams; tool validators and approval flags gate tool output/execution; event bus publishes typed events. | Best embedded-library construction. COS needs a projection/codegen layer from file primitives into Go values plus reload/deletion semantics so static composition does not make stale COS primitives linger. |
| Hector | `pkg/config/agent.go`, `pkg/config/tool.go`, `pkg/builder/agent.go`, `pkg/builder/toolset.go`, `pkg/checkpoint/*`, `pkg/execution/native/event_queue.go` | YAML/config/API objects define agents, tools, guardrails, server/database settings; builder packages assemble agents/toolsets; runtime stores sessions/tasks/checkpoints in service/database structures. | Loaded from config or API; `hector serve`/server surfaces activate apps/agents/tasks; checkpoints and event queues are service-level runtime records. | Guardrails/toolsets/checkpoints/events are platform objects; persistence is SQL/checkpoint oriented. | Strong external-service adapter. COS must map Hector tasks/sessions/checkpoints to backend execution records only, or it duplicates `cosd` and ADR-291 concepts. |
| LangDAG | `README.md`, `api/openapi.yaml`, `internal/config/*`, `internal/provider/*` | Conversation is constructed as a persisted DAG: nodes, edges, aliases, provider calls, tool-use/tool-result records, branches, and API resources. | API/SDK/CLI creates conversations and nodes; provider/router config chooses model path; SSE/API streams events. | Evidence is graph state, node lineage, tool-result nodes, SQLite history, and SSE stream IDs. | Useful as session/conversation substrate. COS would still construct skills/hooks/rules/tools outside LangDAG and write their outcomes into DAG/evidence records. |
| OpenCode | `packages/core/src/plugin.ts`, `packages/llm/src/tool.ts`, `packages/llm/src/tool-runtime.ts`, `.opencode/*`, `packages/opencode/specs/tui-plugins.md` | Tools are typed Effect schema objects or dynamic JSON Schema objects; plugin `define/add/trigger/remove` registers hook functions; `.opencode/` files define agents/skills/tools/plugins. | Plugins load into manager; hooks trigger with mutable draft output; tool record keys become wire names; app/server/session internals activate runtime. | Plugin hooks can mutate outputs; tool runtime emits tool-call/result stream events; plugin manager rolls back registrations on removal/failure. | Good harness/plugin projection target. COS adapter should generate OpenCode plugin/hooks and preserve COS metadata/evidence externally. |
| trpc-agent-go | `agent/agent.go`, `agent/callbacks.go`, `tool/callbacks.go`, `agent/invocation.go`, `agent/graphagent/*`, `tool/*`, `memory/*` | Agents implement a Go interface with `Run`, `Tools`, `SubAgents`; callbacks register before/after agent hooks; tool callbacks register before/after tool hooks, argument mutation, custom result, and result-message conversion; graph/chain/cycle agents are Go modules. | Go constructors/options compose agents and callbacks; invocation carries session, plugins, run options, model selector, limits, event channels. | Before/after callbacks can skip execution, mutate args, replace results, skip summarization, or return custom responses; events stream through channels. | Strong Go framework construction and direct pre/post tool mapping. Risk is framework breadth and its own invocation/session concepts competing with COS RuntimeAdapter. |
| aictl | `README.md`, local config/session/hook/MCP/server files in clone | CLI/config constructs agents, saved sessions, hooks, MCP, provider proxy, and local secret usage. | Activated from CLI/server commands and local config. | Primarily CLI/proxy traces/hooks, not a full service-side agent loop. | Reference-only under current license; construction pattern useful for single-binary ergonomics, not default adapter base. |

### Construction compatibility scoring

| Runtime | Definition fit | Interception fit | Dynamic reload fit | Evidence fit | Overall construction risk |
|---|---:|---:|---:|---:|---:|
| Gollem / Fugue Labs | ◐ Go code values need projection | ✅ hooks/middleware/event bus | ⚠️ must design reload | ✅ COS can own ledgers | Low-medium |
| Aether | ✅ config/MCP/prompt files | ◐ MCP/permission layer, less direct hooks | ✅ config/server reload plausible | ◐ headless/MCP events need normalization | Low-medium |
| Pi | ◐ TS code/extensions/resources | ✅ direct pre/post tool hooks | ◐ extension reload depends integration | ✅ event streams map well | Medium |
| trpc-agent-go | ◐ Go code values | ✅ callbacks | ◐ needs adapter lifecycle | ✅ event channels/callbacks | Medium |
| Goose | ◐ extensions/MCP/inspectors | ✅ inspectors/permissions | ◐ extension/session dependent | ◐ session events need normalization | Medium |
| Hector | ✅ config/API/service objects | ◐ guardrails/platform hooks | ✅ service/API likely | ✅ checkpoints/tasks | Medium-high due overlap |
| LangDAG | ✅ graph/API/storage | ⚠️ not full tool governance | ✅ API/storage | ✅ graph lineage/SSE | Medium-high due incomplete primitive set |
| OpenCode | ✅ files/plugins/tools | ✅ plugin hooks | ✅ plugin manager removal | ◐ plugin/session events need normalization | Medium as harness, high as core |
| thClaws | ✅ files/product registries | ✅ hooks/permissions | ✅ app registries | ◐ product evidence must be normalized | High due product overlap |
| Hermes/OpenClaw | ✅ product registries | ✅ product runtime hooks | ? | ◐ product evidence | High due overlap |
| aictl | ◐ CLI config | ◐ CLI hooks/proxy | ◐ | ⚠️ not full loop | Blocked/reference-only |

Construction-fit conclusion: **Gollem / Fugue Labs, Aether, Pi, and
trpc-agent-go are the cleanest places to prove primitive construction adapters**.
Hector is the cleanest service delegation proof but must be kept behind the COS
service contract. LangDAG is useful only if the adapter slice is explicitly
conversation/session persistence. thClaws, Hermes, and OpenClaw are too
product-shaped to be first construction backends.

### COS adapter construction contract

A COS runtime adapter should make construction explicit with a manifest that says
how each COS primitive was projected.

```yaml
runtime_adapter: gollem
projection:
  skill:
    source: skills/code-review/SKILL.md
    runtime_object: go.tool.CodeReviewSkill
    activation: contextual-trigger
    evidence: .cognitive-os/metrics/skill-routing.jsonl
  pre_tool_gate:
    source: hooks/pre_tool_use.sh
    runtime_object: middleware.CosPreToolGate
    activation: every-tool-call
    evidence: .cognitive-os/metrics/tool-gates.jsonl
  rule:
    source: rules/RULES-COMPACT.md
    runtime_object: prompt/context fragment + guardrail
    activation: session-start
    evidence: .cognitive-os/metrics/rule-loads.jsonl
```

Minimum adapter proof:

1. list every COS primitive projected into the runtime;
2. name the runtime object it became;
3. name the trigger/activation rule;
4. name the interception point;
5. name the evidence row/event/checkpoint written back to COS;
6. prove deletion/disable semantics so stale runtime objects do not outlive COS
   source-of-truth changes.

This is the real portability test. A runtime is a good COS backend only if its
primitive construction can be made reversible, inspectable, and evidence-backed.



## Standards landscape: what COS should reuse vs own

COS is not wrong for wanting agnostic primitives, but it must not pretend there
is already one complete standard for constructing every primitive across IDEs and
agent runtimes.

As of 2026-05-14, the standards landscape is fragmented:

| Standard / convention | What it standardizes well | What it does not standardize |
|---|---|---|
| `AGENTS.md` | Repository-level instructions for coding agents: project context, commands, conventions, constraints. | Runtime hooks, tool enforcement, skill lifecycle, audit evidence, projection fidelity, or provider/session event semantics. |
| `SKILL.md` / Agent Skills | Filesystem package for reusable workflow knowledge with progressive disclosure: metadata, instructions, scripts/resources. | Cross-runtime enforcement hooks, permission semantics, tool preflight/postflight, audit ledgers, versioned projection manifests. |
| MCP | Tool/resource/prompt protocol shape: tools with names/schemas/results; resources; prompts; client/server interaction. | IDE lifecycle, agent session semantics, governance rules, primitive scope, skill activation policy, audit/evidence ownership. |
| ACP | Agent-client/editor protocol: sessions, prompt turns, updates, permissions, file/terminal capabilities between an agent and client. | Internal primitive authoring, skill/rule/hook construction, governance metadata, cross-runtime primitive IR. |
| OpenCode/Pi/Goose/Aether/Gollem/Hector native models | Practical runtime-specific construction models for tools, plugins, hooks, events, sessions, tasks, checkpoints. | A universal primitive construction contract across all IDEs/runtimes. |

Therefore COS should reuse standards at the right layer:

```text
AGENTS.md  -> repository instruction projection
SKILL.md   -> skill packaging / progressive disclosure projection
MCP        -> tools/resources/prompts transport and discovery
ACP        -> agent-client/editor session protocol
RuntimeAdapter / Primitive IR -> COS-owned governance, fidelity, evidence, and projection semantics
```

### Is COS reinventing the wheel?

Partly yes, if COS builds its own versions of things already covered by open
standards:

- custom tool transport instead of MCP;
- custom repo instruction file instead of projecting to/from `AGENTS.md`;
- custom skill package format that ignores `SKILL.md` progressive disclosure;
- custom editor session protocol where ACP is sufficient;
- target-specific hand-written files with no projection manifest.

But COS is **not** merely reinventing the wheel when it owns the missing layer:

- primitive lifecycle and scope taxonomy;
- projection fidelity and drift detection;
- cross-target enforcement-vs-context parity claims;
- evidence/audit ledgers owned by COS;
- policy gates that normalize across runtimes;
- stale projection disable/delete semantics;
- acceptance criteria proving a primitive behaved the same way across targets.

No current standard fully specifies that layer. MCP standardizes tools/resources
and prompts. SKILL.md standardizes skill packaging and progressive disclosure.
AGENTS.md standardizes repo instructions. ACP standardizes agent-client/editor
communication. None of them, alone, defines a canonical governed primitive IR
that can project skills, rules, hooks, policies, sessions, memory, metrics, and
evidence into every IDE/runtime with declared fidelity.

### Design correction for COS

COS should stop treating "agnostic primitive" as a target-neutral Markdown file
that every IDE interprets directly. Instead, COS should treat it as a canonical
spec with explicit projections.

Bad claim:

> This primitive is agnostic because Claude, Codex, OpenCode, and Pi can all read
> a file with roughly similar instructions.

Correct claim:

> This primitive is canonical in COS. It has SKILL.md/AGENTS.md/MCP/ACP/runtime
> projections with declared fidelity, and COS evidence proves which semantics are
> enforced in each target.

### Standard-first rule

When a primitive maps cleanly to an existing standard, COS should use that
standard as the projection format:

| COS primitive need | Prefer existing standard | COS-owned addition |
|---|---|---|
| Repo instructions | `AGENTS.md` | Scope, source pointer, evidence that target loaded it. |
| Reusable workflow knowledge | `SKILL.md` | Version, audience/scope, acceptance criteria, trust/evidence metadata, projection manifest. |
| Callable external capability | MCP tool | COS pre/post gate, permission policy, audit ledger, result normalization. |
| Context/data source | MCP resource | Retrieval policy, provenance, citation/evidence contract. |
| Reusable prompt/workflow template | MCP prompt or SKILL.md | Trigger semantics and acceptance/evidence. |
| Editor/client session | ACP | COS run/task/session id mapping, audit and replay. |
| Runtime event/tool loop | RuntimeAdapter | Canonical lifecycle events and fidelity claims. |

COS should only invent where no standard exists: governed primitive IR,
projection fidelity, evidence normalization, and cross-runtime parity tests.


### Deep standards audit — 2026-05-14

Primary-source review shows there is no single standard for creating governed
agentic primitives once and carrying them to every IDE/runtime with equivalent
semantics. There are mature partial standards, and COS should use each at its
native boundary.

| Standard | Primary-source scope | What COS can rely on | What COS must not assume |
|---|---|---|---|
| `AGENTS.md` | The public format describes a predictable Markdown place for agent context/instructions, with no required fields and nearest-file precedence. | Good universal projection for repo guidance, build/test commands, conventions, and high-level governance reminders. | Not a runtime primitive system. It has no schema for hooks, tools, enforcement, evidence, lifecycle, or projection fidelity. |
| Agent Skills / `SKILL.md` | Anthropic Skills are filesystem directories with YAML metadata, progressive disclosure, instructions, scripts, and resources loaded when relevant. | Good canonical or projection format for reusable procedural knowledge. COS should align skill packaging with this rather than inventing a different package shape. | Not a universal enforcement or runtime-event standard. It does not define pre/post tool gates, audit ledgers, or parity semantics across non-Claude runtimes. |
| MCP | MCP standardizes client/server lifecycle, capability negotiation, tools, resources, prompts, annotations, tool results, list-changed notifications, and security expectations such as user confirmation for tools. | Best projection/transport for callable capabilities, prompt templates, resources, and tool result normalization. | MCP tools are model-controlled capabilities, not governed COS primitives. MCP does not define COS lifecycle states, primitive scope, acceptance criteria, or evidence ownership. |
| ACP | ACP standardizes agent-client/editor interaction: initialize/auth/session, session updates, file/terminal capabilities, permission requests, content blocks, session config, cancellation, and extensibility through `_meta`/custom methods. | Best session/client protocol for a standalone COS service or runtime adapter that talks to IDEs. | ACP does not define how an agent internally authors/loads skills, hooks, policies, rules, memory, or audit evidence. |
| Runtime-native models | Pi, Goose, Aether, Gollem, Hector, OpenCode, thClaws, etc. provide practical construction models for tools, hooks/callbacks, sessions, permissions, event buses, tasks, checkpoints, plugins, and skills. | Best execution backend surfaces for adapters. | None is a neutral universal standard; adopting one as canonical would make COS portable only to runtimes that imitate that ontology. |

#### Current COS behavior against standards

| COS behavior observed | Assessment | Action |
|---|---|---|
| `manifests/harness-projection.yaml` separates `structural`, `host-plugin-lifecycle`, `native-lifecycle`, and runtime-smoke proof levels. | Correct. This already prevents many false parity claims. | Keep and extend it with explicit projection-fidelity fields. |
| `scripts/cos_init.py` projects structural harnesses via `AGENTS.md`, host instruction files, MCP placeholders, and bounded proof-boundary text. | Mostly correct standard reuse. It treats AGENTS.md and host files as instruction/config projections, not runtime proof. | Add generated projection manifests per target so drift and unsupported semantics are machine-readable, not just prose. |
| Claude/Codex are marked `native-lifecycle`, while Cursor/Copilot/OpenCode/etc. are mostly structural. | Correct distinction. | For each non-native target, add a fidelity row saying context-only vs enforcement-capable. |
| `skills/*/SKILL.md` uses the broader Skills convention. | Correct direction. | Ensure COS-only extensions in frontmatter remain additive and do not break portable SKILL.md readers. |
| COS still has docs claiming broad portability percentages or “rules/skills are portable” in aggregate. | Risky. It can sound like semantic parity when much of the proof is structural/context-only. | Qualify claims as packaging portability, context projection, or enforcement projection. |
| `docs/04-Concepts/architecture/skills-rules-portability-gap.md` already identifies `.claude/` gravity and source-of-truth hierarchy. | Correct diagnosis already existed. | Promote this into enforceable manifest/tests: canonical spec first, target artifact generated. |
| `manifests/primitive-authority.yaml` separates visibility/projection from mutation authority. | Correct and valuable. | Connect authority modes to primitive contract/projection manifests so adapters know whether they can enforce, advise, or only observe. |
| `manifests/primitive-contracts.yaml` already exists as a canonical portable primitive contract registry with per-target fidelity levels. | Important correction: COS is not starting from zero. The repo already has the seed of a Primitive IR/fidelity ledger. | Promote this registry to the explicit canonical source for all projectors/adapters instead of letting target files or adapter code duplicate primitive semantics. |
| `scripts/primitive_projection_fidelity.py` and `tests/contracts/test_primitive_projection_fidelity.py` join contracts to observed harness coverage and prevent declared contracts from becoming runtime proof. | Correct proof discipline. A local run on 2026-05-14 reported 340 contracts, 2,040 projection rows, and 0 gaps. | Keep this as the acceptance gate for projection claims; add stale-artifact/delete semantics and adapter-generation checks. |
| `packages/opencode-adapter/plugins/cos-primitive-guard.js` provides an OpenCode `tool.execute.before/after` governed-wrapper smoke path. | Useful runtime proof for an enforcement-capable subset. It writes normalized `primitive-interventions.jsonl` rows. | Reduce duplication: generate the signed primitive list/source map/classifiers from primitive contracts or a narrower adapter spec instead of hand-maintaining hardcoded JavaScript mappings. |

#### Is COS doing something wrong?

COS is doing the right high-level thing by treating governed primitives and
evidence as COS-owned. The architectural risk is **overloading Markdown/files as
if they were semantic portability**. A file can be portable as packaging but not
portable as behavior.

The failure mode to avoid:

```text
same SKILL.md/rule text everywhere
=> claim same primitive behavior everywhere
```

The safer claim:

```text
same canonical primitive spec
+ target projection manifest
+ target-specific artifact
+ runtime evidence
=> measured fidelity for each target
```

#### What COS should standardize internally

COS should not create another public replacement for AGENTS.md, SKILL.md, MCP,
or ACP. COS should make `manifests/primitive-contracts.yaml` the explicit
canonical **Primitive Contract / Primitive IR v1** and have it reference those
standards as projection formats. If a separate `primitive-ir.yaml` is introduced
later, it should be generated from, or losslessly synchronized with, the contract
registry rather than becoming a second source of truth.

Minimum Primitive IR fields:

```yaml
id: rule.no_secret_writes
kind: pre_tool_policy
version: 1
source: rules/no-secret-writes.md
standard_projection:
  repo_instructions: AGENTS.md
  skill_package: null
  tool_transport: MCP
  client_session: ACP
semantics:
  activation_event: pre_tool_use
  required_inputs: [tool_name, path, command, diff]
  decision_type: allow_block_warn
  enforcement_required: true
  evidence_required: true
projection_requirements:
  minimum_fidelity: enforcement
  required_runtime_intercepts: [pre_tool_use]
  unsupported_target_policy: advisory_only_or_disable
```

The generated target projection should then state:

```yaml
target: cursor
artifact: .cursor/rules/cognitive-os.mdc
fidelity: context-only
unsupported:
  - pre_tool_use_blocking
claim_allowed: advisory_context_projection
claim_forbidden: runtime_enforcement
```

This turns the portability question from subjective prose into a testable matrix.

## Agnostic primitive drift problem

The core portability problem is that an "agnostic primitive" can silently stop
being agnostic when each IDE/runtime applies its own construction rules during
implementation.

Bad shape:

```text
COS skill/rule/hook
  -> Claude Code file
  -> Codex skill/plugin shape
  -> OpenCode plugin/command shape
  -> Pi extension/resource shape
  -> Goose/Aether/Gollem/Hector runtime object
```

In that shape, every projection target becomes a co-author of the primitive's
semantics. Over time the primitive drifts: one IDE treats it as prompt context,
another as a command, another as a permission hook, another as a runtime tool.
The name stays portable while the behavior stops being portable.

The safer shape is a canonical primitive IR plus lossy/lossless projections:

```text
COS canonical primitive spec
  -> semantic IR / contract
  -> projection manifest per target
  -> generated target artifact
  -> runtime execution event
  -> normalized COS evidence
```

The IDE/runtime-specific artifact is therefore **not** the primitive. It is a
compiled projection of the primitive.

### Required separation

| Layer | Owned by | Mutable by IDE/runtime? | Purpose |
|---|---|---:|---|
| Canonical primitive spec | COS | No | Human-authored source of truth: intent, scope, lifecycle, acceptance, safety, evidence. |
| Primitive IR | COS | No | Normalized semantic contract consumed by all projectors/adapters. |
| Projection manifest | COS adapter | No without regeneration | Declares what target artifact was generated, what was lost, what is enforced, and where evidence returns. |
| Target artifact | IDE/runtime adapter | Yes, generated/ephemeral | Claude/Codex/OpenCode/Pi/Goose/Aether/Gollem/Hector-specific representation. |
| Runtime event/result | Runtime | Yes | Actual execution observation. |
| Normalized evidence | COS | No | COS-owned proof that behavior matched or failed the canonical contract. |

### Projection manifest must track drift

Every projection should declare fidelity, unsupported semantics, and enforcement
location.

```yaml
primitive_id: skill.code_review
source: skills/code-review/SKILL.md
ir_version: 1
projection:
  target: opencode
  artifact: .opencode/skills/code-review/SKILL.md
  generated_by: cos projector opencode/v1
  fidelity:
    trigger: lossless
    prompt_body: lossless
    pre_tool_gate: unsupported
    post_tool_audit: adapter-required
    acceptance_criteria: advisory-only
  enforcement:
    pre_tool_gate: plugin.tool.execute.before
    post_tool_audit: plugin.tool.execute.after
    evidence: .cognitive-os/metrics/projection-events.jsonl
  drift_policy:
    target_edits: forbidden
    regeneration_required: true
    stale_artifact_action: disable
```

A projection with unsupported semantics is still useful, but it must not be
reported as parity. For example, a target that can inject prompt text but cannot
block tools has a **context projection**, not an **enforcement projection**.

### Canonical primitive fields needed before projection

A portable primitive should carry enough structure that target-specific behavior
is a rendering choice, not an interpretation choice.

```yaml
id: rule.no_secret_writes
kind: pre_tool_policy
scope: both
intent: Block attempts to write credentials or key material.
activation:
  event: pre_tool_use
  applies_to_tools: [write_file, edit_file, bash]
inputs:
  required: [tool_name, path, command, diff]
policy:
  decision: block_if_secret_material
  severity: critical
outputs:
  on_block: structured_error_result
  on_allow: audit_allow_row
acceptance:
  - unsafe write is blocked before execution
  - audit row includes primitive id and matched detector
evidence:
  ledger: .cognitive-os/metrics/tool-gates.jsonl
projection_requirements:
  minimum_fidelity: enforcement
  required_intercepts: [pre_tool_use]
```

The projector can then decide whether a target can implement it:

- Claude Code hook: shell `PreToolUse` hook plus JSONL evidence.
- Codex plugin/skill: adapter-specific pre-tool hook if available, otherwise no
  enforcement parity claim.
- OpenCode: `tool.execute.before` plugin hook.
- Pi: `beforeToolCall` or `tool_call` event handler.
- Gollem: tool approval / middleware / hook.
- Aether: MCP permission or COS-owned MCP wrapper.
- Hector: guardrail/task policy wrapper.

### Rule

Do not author target files as the primitive source of truth.

Allowed:

> `skills/foo/SKILL.md` is the canonical primitive source. `.opencode/...`,
> `.claude/...`, Pi resources, and runtime objects are generated projections with
> declared fidelity.

Not allowed:

> The OpenCode skill is the source of truth for this COS skill.

> The Pi tool definition is the source of truth for this COS hook.

> The Gollem middleware is the source of truth for this COS policy.

Target-specific implementation may be hand-written during a spike, but before it
becomes product behavior it must be backfilled into the canonical primitive spec
and projection manifest.


### Deep code audit correction — 2026-05-14

A deeper code pass changes the earlier gap framing from "missing primitive IR" to
"primitive IR exists but is not yet the sole projector source of truth".

Observed implementation facts:

- `manifests/primitive-contracts.yaml` is already the canonical portable contract
  registry. It records primitive id, family, source, trigger, required host
  capabilities, actions, evidence ledgers, proof tests, and per-harness
  projection fidelity.
- `lib/primitive_contracts.py` exposes read-only helpers to load/index those
  contracts by id or source.
- `scripts/primitive_projection_fidelity.py` builds a report that joins contract
  declarations with observed harness coverage and OpenCode smoke evidence. It
  deliberately says declared contracts are not runtime proof.
- `tests/contracts/test_primitive_projection_fidelity.py` asserts that structural
  advisory projections stay non-enforced and host-plugin-capable projections stay
  pending until runtime smoke exists.
- `scripts/cos_init.py` still writes many target files directly: AGENTS.md
  blocks, host instruction files, MCP placeholders, OpenCode config, and the
  OpenCode primitive guard plugin. It uses good proof-boundary language, but it
  is not yet a pure compiler from primitive contracts.
- `packages/opencode-adapter/plugins/cos-primitive-guard.js` is effective as an
  enforcement smoke adapter, but it hardcodes signed primitive ids, source paths,
  and classifier logic that should eventually be generated or checked against the
  contract registry.

Therefore the current architecture is healthy but mid-transition:

```text
Current:   primitive contracts + hand-written projectors/adapters + fidelity report
Desired:   primitive contracts/IR -> generated projection manifests/artifacts -> adapter smoke -> fidelity report
```

The next hardening step is not inventing a new standard. It is closing the loop
so target artifacts cannot become semantic co-authors of primitives.

## Recommended architecture

Do **not** migrate COS wholesale to Pi, Goose, OpenCode, Hermes, or any single
runtime yet. Define a stable `RuntimeAdapter` boundary below `agent-service` and
`cosd`, then compare candidate backends with the same proof drill.

Recommended candidate set:

1. `native-python` or `native-go` minimal adapter for direct COS ownership;
2. `pi` adapter for Pi runtime integration;
3. `goose` adapter for Rust runtime comparison;
4. `opencode` adapter/plugin if OpenCode's server/plugin surface proves enough
   lifecycle parity;
5. keep Hermes/holaOS as pattern references unless a deliberate integration ADR
   changes their status.

The first proof should be model-light or model-optional where possible:

```text
POST /api/v1/oneshot/query
"Read README, summarize project state, do not modify files."

Expected stream:
- session_started
- context_loaded
- model_called or faux_model_called
- tool_requested: read_file
- tool_result
- answer_delta
- completed

Expected evidence:
- COS pre-tool gate ran
- COS post-tool audit ran
- event log written
- Engram/session summary path exercised or explicitly stubbed
- no write/publish action occurred
```

## Acceptance criteria for the next ADR or implementation slice

Before claiming standalone autonomous runtime support, complete at least one
adapter slice with these criteria:

1. `agent-service` can route one bounded query to a `RuntimeAdapter` instead of
   returning a Phase-1 `501` stub.
2. The adapter emits machine-readable stream events compatible with ADR-291 SSE
   shapes.
3. One read-only tool call passes through COS preflight and postflight gates.
4. One blocked unsafe tool call is proven not to execute.
5. Session/task evidence is written to the COS audit/runtime ledger.
6. The implementation declares what it does **not** prove: long-running autonomy,
   crash recovery, publication, multi-tenant isolation, and provider credential
   storage unless each is explicitly tested.

## Product wording

Allowed today:

> Cognitive OS has `cosd` control-plane work and an ADR-291 HTTP/SSE service
> skeleton, but its full autonomous agent runtime adapter is still a planned
> bridge.

> Pi, Goose, OpenCode, Hermes, and holaOS-style systems are runtime references or
> adapter candidates, not default COS runtime dependencies.

Not allowed today:

> COS already runs as a complete standalone autonomous coding agent service.

> COS is built on Pi.

> COS has runtime parity across Pi, Goose, OpenCode, Claude Code, and Codex.

Allowed after a signed adapter proof:

> COS can route bounded service-mode tasks through `<adapter>` while preserving
> selected COS pre-tool, post-tool, streaming, and audit guarantees.

## Local clone scan — 2026-05-14

A shallow clone scan was run in `/tmp/cos-runtime-candidates` for the candidates
that came up in the runtime discussion:

| Candidate | Repo cloned | Language / shape | License signal | Service-agent fit | COS fit |
|---|---|---|---|---|---|
| Hector | `verikod/hector` | Go single-binary service with embedded Studio, SQL state, A2A/MCP, Admin API, tasks/sessions/checkpoints | MIT | Very high: `hector serve`, HTTP API, app/agent runtimes, SQL-backed durability | Best off-the-shelf service shape; may duplicate `cosd`/ADR-291 unless used behind adapter only |
| Gollem / Fugue Labs | `fugue-labs/gollem` | Go library/framework with agent runtime, codetools, event bus, MCP, Temporal/durable orchestration | MIT | High as embedded runtime library, lower as turnkey service | Best structural fit if COS wants to own `agent-service`/`cosd` and embed a Go runtime below it |
| Pi | `badlogic/pi-mono` | TypeScript runtime + coding agent + provider layer + extensions | MIT | High as agent runtime, lower as service/control-plane | Strong runtime adapter candidate but adds TS runtime and Pi extension model |
| Goose | `block/goose` | Rust agent/runtime ecosystem with server, SDK, MCP, UI | Apache-2.0 | High as external runtime/service candidate | Strong Rust candidate; larger integration surface than Gollem/Hector |
| OpenCode current | `anomalyco/opencode` | TypeScript product/harness with server/specs/plugins/permissions | MIT | Medium-high as harness/server, less as embeddable library | Good plugin adapter target; not the cleanest internal COS runtime |
| OpenCode archived Go | `opencode-ai/opencode` | Historical Go implementation | MIT | Low for new work | Reference-only; current line is not this repo |
| Hermes Agent | `NousResearch/hermes-agent` | Python full agent product/gateway/runtime | MIT | Very high product capability | Too much overlap with COS; good reference, risky as dependency/runtime base |
| OpenClaw | `openclaw/openclaw` | Node/TypeScript product/gateway on/around Pi, local-first gateway, channels/tools/sessions | MIT | Very high product/gateway capability | Too broad and product-shaped; evidence for Pi/product pattern, not minimal COS backend |
| trpc-agent-go | `trpc-group/trpc-agent-go` | Go framework: multi-agent, memory, SKILL.md tools, A2A/AG-UI/gateway server | Apache-2.0 | Medium-high framework fit | Good Go framework candidate, but broader/more opinionated than Gollem for COS runtime core |
| aictl | `pwittchen/aictl` | Rust CLI/desktop/server proxy; saved agents/sessions/hooks/MCP | PolyForm Noncommercial | Technically interesting but server is proxy-only for LLM provider, not full agent loop | Blocked for commercial/default adoption by license; reference-only unless license changes |
| Aether | `contextbridge/aether` | Rust monorepo with CLI/TUI/headless/ACP/library, MCP-only tools, provider trait, first-party MCP servers | MIT | High as Rust harness/runtime adapter candidate, medium as standalone service | Strong Goose comparator; less disruptive than product-shaped systems if used as library/headless adapter |
| thClaws | `thClaws/thClaws` | Rust workspace/product with desktop GUI, CLI, non-interactive mode, WebSocket/HTTP serve, skills/plugins/MCP, permissions/sandbox, sessions/subagents/teams | MIT OR Apache-2.0 | Very high product/workspace capability | Too broad to be least-disruptive base; strong watch/reference or external adapter candidate |
| LangDAG | `aduermael/langdag` | Go library/CLI/API for persistent LLM conversation DAGs with SQLite, SSE, tool-use flows, multi-provider support | MIT | Medium-high as conversation service/runtime, lower as coding workspace | Useful if COS wants Go-native conversation/session persistence below ADR-291; not enough alone for coding-agent filesystem/tool governance |

### Fit ranking for "service with agents" while preserving COS structure

1. **Gollem / Fugue Labs as embedded runtime library** — best if COS keeps `agent-service` and
   `cosd` as the public/control-plane surfaces and only imports a runtime loop,
   tool approval, event bus, codetools, MCP, and durable orchestrator underneath.
2. **Hector as external service backend** — best if the goal is to run a complete
   agent service quickly. It is already a single-binary service with Studio,
   Admin API, apps/agents, sessions, tasks, checkpoints, and SQL durability. The
   risk is structural overlap: it may replace rather than fill the missing COS
   runtime layer unless strictly wrapped as an adapter.
3. **Pi as runtime adapter** — best proven coding-agent loop and extension/event
   surface, but it brings a TypeScript runtime into a COS codebase whose service
   path is currently Python/Go.
4. **Goose as Rust runtime adapter** — strong runtime ecosystem and MCP/server
   story, but more adapter work is needed to avoid a parallel product surface.
5. **OpenCode plugin/server adapter** — useful for harness/runtime projection,
   not the cleanest standalone service core.
6. **Aether as Rust library/headless adapter** — now ranks beside Goose for a Rust proof because it explicitly supports ACP, MCP-only tools, headless structured logs, and library mode.
7. **LangDAG as Go conversation/session substrate** — useful if the first missing slice is persistent conversation DAG + SSE + tool-use flows, but it is not enough alone as a coding-agent workspace.
8. **trpc-agent-go** — promising Go framework with SKILL.md and gateway concepts; evaluate after Gollem/Hector because it appears broader and more framework-y.
9. **thClaws** — strong product/workspace candidate with many COS-like primitives, but broad enough that it risks replacing COS structure unless wrapped externally.
10. **Hermes/OpenClaw** — reference systems for product/runtime breadth; not the least disruptive base for COS.
11. **aictl** — reference-only because of PolyForm Noncommercial and because its server path is provider proxy rather than full agent-service loop.

### Recommended next proof

Build two tiny adapters behind ADR-291 instead of choosing a product first:

- `runtime=gollem`: embedded Go runtime adapter that runs one read-only task and
  emits ADR-291-compatible events.
- `runtime=hector`: external-service adapter that delegates one task to a local
  Hector instance and records the same COS evidence.

The one that preserves these invariants with less glue should win the first
runtime slice:

1. `agent-service` remains the HTTP/SSE contract.
2. `cosd` remains the control-plane/task-admission surface.
3. COS gates still run before/after tools.
4. Engram/audit/event ledgers remain COS-owned.
5. The backend can be swapped without changing product-facing APIs.

## Feature comparison matrix — 2026-05-14 clone scan

Legend: ✅ observed first-class surface, ◐ partial/available but not central,
⚠️ mismatch/risk, ❌ not suitable for this criterion, ? needs deeper proof.

| Feature / Candidate | Gollem / Fugue Labs | Hector | LangDAG | Pi | Goose | Aether | thClaws | OpenCode current | trpc-agent-go | Hermes | OpenClaw | aictl |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Permissive license for COS default adoption | ✅ MIT | ✅ MIT | ✅ MIT | ✅ MIT | ✅ Apache-2.0 | ✅ MIT | ✅ MIT OR Apache-2.0 | ✅ MIT | ✅ Apache-2.0 | ✅ MIT | ✅ MIT | ❌ PolyForm NC |
| Primary implementation language aligns with COS service path | ✅ Go | ✅ Go | ✅ Go | ⚠️ TS/Node | ◐ Rust | ◐ Rust | ◐ Rust | ⚠️ TS/Node | ✅ Go | ◐ Python | ⚠️ TS/Node | ◐ Rust |
| Turnkey long-running service | ◐ `cmd/gollem serve`, library-first | ✅ `hector serve` | ✅ API/SSE server surface | ◐ CLI/runtime, not service-first | ✅ server crate/ecosystem | ◐ headless/ACP, not service-first | ✅ WebSocket/HTTP serve + daemon | ✅ server/product | ◐ gateway/server framework | ✅ product/gateway | ✅ gateway daemon/product | ◐ server is provider proxy |
| Embeddable runtime library | ✅ strong | ◐ possible, service-shaped | ✅ Go package | ✅ TS packages | ◐ SDK/server crates | ✅ Rust library | ◐ core crate but product-shaped | ◐ package internals | ✅ framework | ⚠️ product-shaped | ⚠️ product-shaped | ◐ CLI/core crates |
| Agent model/tool loop | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ CLI, ❌ server |
| Coding tools out of the box | ✅ codetool | ◐ tools configurable | ◐ tool-use flows, not workspace-first | ✅ read/write/edit/bash | ✅ | ✅ first-party MCPs | ✅ built-in tools/doc tools | ✅ | ◐ broad tools/skills | ✅ 40+ tools | ✅ first-class tools | ◐ general tools |
| Tool preflight / approval hooks | ✅ `WithToolApproval`, middleware | ✅ guardrails/sandbox/HITL claims | ◐ tool flow, approval not central | ✅ `beforeToolCall`, `tool_call` | ✅ permissions/approval direction | ◐ permissions/elicitation via MCP | ✅ permissions/sandbox/approval | ✅ plugin `tool.execute.before/after` | ✅ guardrail/plugins likely | ✅ approval tools | ✅ approval/sandbox | ✅ CLI HITL/hooks |
| Tool postflight/event hooks | ✅ event bus/runtime events | ✅ events/server traces | ✅ DAG events/tool results | ✅ `afterToolCall`, `tool_result` | ✅ events | ✅ structured events/logs | ✅ events/hooks/docs | ✅ plugin/event surfaces | ✅ events/plugins | ✅ tool result storage/hooks | ✅ gateway/events | ✅ audit/hooks |
| Streaming events | ✅ `RunStream` | ✅ streaming chat/API | ✅ SSE | ✅ event streams | ✅ | ✅ headless JSON/streams | ✅ WebSocket/HTTP | ✅ | ✅ | ✅ | ✅ | ✅ CLI/proxy |
| HTTP API/server surface | ◐ present but not central | ✅ strong | ✅ API/OpenAPI | ⚠️ not primary | ✅ strong | ◐ ACP/headless, not API-first | ✅ serve mode | ✅ strong | ✅ gateway | ✅ strong | ✅ strong | ✅ proxy only |
| Session persistence | ◐ framework/state support | ✅ SQL-backed sessions | ✅ SQLite DAG | ✅ session manager | ✅ sessions | ◐ project/session support | ✅ sessions/memory | ✅ sessions | ✅ sessions/memory | ✅ sessions/memory | ✅ sessions | ✅ saved sessions |
| Durable tasks / leases / recovery | ✅ orchestrator + SQLite/Temporal | ✅ tasks/checkpoints/retry | ◐ persistent DAG, not task queue | ❌/◐ not central | ? | ◐ session/log oriented | ✅ schedule/loop/goal/daemon claims | ◐ product queue/session | ◐ framework workflows | ◐ product/runtime | ✅ gateway/product | ❌ server, ◐ CLI |
| MCP support | ✅ client/server/ext | ✅ MCP | ❌/◐ not central in clone | ⚠️ minimal in clone scan | ✅ strong | ✅ MCP-only tools | ✅ stdio/HTTP MCP + OAuth | ✅ | ✅ | ✅ | ◐ tools/channels | ✅ |
| Skills / SKILL.md support | ⚠️ no direct COS SKILL.md observed | ◐ agent skills in config/A2A | ❌ not central | ◐ resources/skillPaths | ? | ✅ first-party skills MCP | ✅ SKILL.md + plugins | ◐ agents/commands/plugins | ✅ SKILL.md tools | ✅ strong | ✅ strong | ✅ saved skills |
| Provider abstraction | ✅ | ✅ | ✅ | ✅ strong | ✅ | ✅ strong trait | ✅ | ✅ | ✅ | ✅ strong | ✅ | ✅ |
| OAuth/subscription provider support | ? | ? | ◐ cloud/provider deps | ✅ Anthropic/OpenAI Codex/Copilot | ? | ✅ OAuth/keyring deps | ✅ Claude Code auth + OAuth MCP | ? | ? | ✅ many account flows | ✅ likely via gateway | ◐ server/proxy features |
| Built-in UI/admin | ❌/◐ examples | ✅ embedded Studio | ◐ CLI/API docs | ✅ TUI/web-ui packages | ✅ desktop/UI | ✅ TUI/IDE/ACP | ✅ GUI/CLI/webapp | ✅ TUI/web/server | ◐ demos | ✅ TUI/gateways | ✅ UI/gateway | ✅ CLI/desktop |
| Multi-agent orchestration | ✅ team/orchestrator | ✅ apps/agents | ◐ DAG branching, not teams | ◐ sessions/follow-ups | ? | ✅ sub-agent MCP | ✅ subagents/teams | ✅ agents/sessions | ✅ strong | ✅ delegates/subagents | ✅ routing/sessions | ◐ saved agents |
| COS structure preservation | ✅ best | ◐ good if wrapped, overlap risk | ✅ good substrate, incomplete tools | ◐ good runtime, stack shift | ◐ good, larger Rust surface | ✅ good if library/headless | ⚠️ overlaps too much | ◐ adapter target, not core | ◐ framework, broad | ⚠️ overlaps too much | ⚠️ overlaps too much | ❌ license + proxy-only server |
| Fastest path to a visible service demo | ◐ requires adapter code | ✅ best | ✅ if conversation API is enough | ◐ requires Node adapter | ◐ requires Rust adapter | ◐ requires Rust adapter | ✅ product already works | ✅ if adopting product semantics | ◐ requires framework assembly | ✅ product already works | ✅ product already works | ◐ proxy demo only |
| Best first experiment role | Embedded runtime adapter | External service backend adapter | Conversation/session substrate | Runtime adapter baseline | Rust adapter candidate | Rust library/headless adapter | Product/workspace watch | Plugin/server adapter | Secondary Go framework compare | Reference only | Reference only / Pi proof | Reference only |


### Supplemental clone scan — Aether, thClaws, LangDAG

After the initial matrix, a supplemental shallow clone added three candidates the
first pass had underweighted:

- **Aether (`contextbridge/aether`, MIT)**: stronger than a generic watch item.
  The clone shows a Rust workspace with CLI/TUI, ACP support, headless structured
  logs, Rust library mode, provider traits, OAuth/keyring dependencies, MCP
  client/server utilities, first-party MCP servers, and a deliberate "tools via
  MCP" design. For COS, Aether is a good Rust library/headless adapter proof,
  especially if we want less product overlap than thClaws.
- **thClaws (`thClaws/thClaws`, MIT OR Apache-2.0)**: much more complete than a
  simple watch repo. It has desktop GUI, CLI, non-interactive mode, WebSocket/HTTP
  serve mode, MCP, skills, plugins, permissions, sandboxing, sessions, subagents,
  agent teams, scheduling/loops/goals, memory/KMS, and Claude Code auth via
  Agent SDK. The issue is fit, not capability: it is product/workspace-shaped and
  could replace COS service structure unless wrapped as an external adapter.
- **LangDAG (`aduermael/langdag`, MIT)**: stronger than a pure DAG reference. The
  clone shows a Go package/CLI/API surface with SQLite-backed persistent
  conversation DAGs, SSE streaming, tool-use/tool-result flows, branching, retry,
  and multi-provider support. It is useful as a Go-native conversation/session
  substrate below ADR-291, but it does not by itself supply the full coding-agent
  workspace, permissions, sandbox, and project-governance layer.

Updated shortlist after the supplemental scan:

1. **Gollem / Fugue Labs** for least-disruptive embedded Go runtime proof.
2. **Hector** for quickest off-the-shelf service-with-agents proof, with overlap
   risk.
3. **Aether** for Rust library/headless adapter proof.
4. **Goose** for Rust runtime/server comparator.
5. **LangDAG** if the first missing slice is persistent conversation DAG + SSE +
   tool flow rather than full coding-agent workspace.
6. **Pi** for mature coding-agent runtime/event baseline, accepting TS/Node.
7. **thClaws** as product/workspace watch or external adapter, not least
   disruptive base.

### Feature-matrix interpretation

- **Gollem / Fugue Labs** wins on preserving COS structure because it can sit below
  `agent-service`/`cosd` as an embedded Go runtime while giving COS tool
  approval, event bus, codetools, MCP, and durable orchestration hooks.
- **Hector** wins on turnkey service features: service command, embedded UI,
  Admin API, SQL-backed sessions/tasks/checkpoints, app/agent runtime cache, and
  multi-tenant posture. The integration risk is overlap with the COS surfaces we
  already built.
- **Pi** remains the strongest coding-agent-runtime baseline and has the cleanest
  direct mapping for COS pre/post tool gates through `beforeToolCall` and
  `afterToolCall`, but it moves the runtime slice into TypeScript/Node.
- **Aether** and **Goose** are now the strongest Rust adapter candidates from the cloned set. Aether is attractive for library/headless/ACP/MCP-first embedding; Goose remains attractive as a broader runtime/server ecosystem.
- **LangDAG** is a credible Go-native substrate for conversation persistence and streaming, but it would need COS-owned coding tools, permissions, and governance around it.
- **OpenCode current** should be treated as a native plugin/harness adapter, not
  the internal standalone runtime, unless its server/plugin API is deliberately
  selected as the execution backend.
- **thClaws**, **Hermes**, and **OpenClaw** are too product-shaped to be the least disruptive COS runtime base. They are valuable reference systems and external adapter/comparison targets.
- **aictl** is blocked for default adoption by PolyForm Noncommercial and its
  server is primarily a provider proxy; keep it as a pattern/reference only.
