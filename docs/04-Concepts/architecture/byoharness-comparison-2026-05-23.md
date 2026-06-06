# BYO Harness Comparison — 2026-05-23

## Source Evidence

- External repo: `betta-tech/byo-coding-agent`, cloned locally at `/tmp/byo-coding-agent`.
- Inspected commit: `77aa4db3fa3f606e6605b4b3275852129e93be6f`.
- Public tutorial site: `https://www.byoharness.dev/es/`.
- User-provided transcript: "Construí un agente de IA... y te enseño cómo".
- Local verification: `go test ./...` passed in the clone.

## Executive Verdict

`byo-coding-agent` is a compact educational implementation of a full coding-agent harness. It owns the REPL, agent loop, LLM provider calls, tools, permission prompts, subagent delegation, MCP registration, compaction, token accounting, debug UI, and file-backed memory.

Cognitive OS is a different product layer: it governs existing harnesses and projects portable agentic primitives into Claude Code, Codex, Cursor, Devin, and service/headless surfaces. The external repo should not replace Cognitive OS hook governance. It is most useful as a reference implementation for the still-partial COS-owned runtime path: ADR-291 `agent-service`, `cosd`, Surface 5 TUI, and optional local runtime labs.

## Architecture Comparison

| Area | BYO Harness | Cognitive OS Today | Reusable Direction |
|---|---|---|---|
| Product role | Full standalone agent harness. | Governance/projection OS above existing harnesses. | Use BYO as runtime-lab inspiration, not as core product repositioning. |
| Agent loop | `internal/agent.Agent.Send` runs the inner provider/tool loop with `MaxTurns`. | No canonical standalone model/tool loop in core; hooks intercept host lifecycle events. | Add a small COS-native runner only behind ADR-291/headless surfaces. |
| Provider seam | `internal/provider.Provider` abstracts Anthropic/OpenAI message APIs. | `internal/provider.Provider` abstracts harness hook payloads/responses. | Keep names conceptually separate: LLM provider vs harness driver. A COS runtime runner needs a distinct `llm.Provider` package. |
| Tool seam | `internal/tool.Tool` plus deterministic registry and one file per tool. | Agentic primitives are skills/hooks/rules/scripts, projected via installers and drivers. | Add a typed tool contract for service/headless runtime tools; do not conflate with project governance hooks. |
| Permission gate | Human approval before each tool call; write calls show unified diff. | Shell hooks and policies block/warn around host tool calls. | Strong candidate: diff-first write approvals for agent-service/headless mode. |
| Subagents | Delegation is just another tool wrapping a fresh `Agent`. | Squads/subagents exist as governance/organization concepts; runtime spawn depends on host. | Useful mental model for a future COS runner: subagent spawn should be a governed tool with isolated context and restricted tools. |
| MCP | Reads `mcp.json`, connects stdio/http servers, registers remote tools into the local registry. | MCP mostly lives in host/user setup plus Engram integration and doctors. | Reuse wrapper pattern for optional runtime service MCP tools; keep host MCP separate. |
| Memory | File-backed session summaries under `.harness`, recall by substring, startup preamble. | Engram plus local metrics/changelogs/session learning, with protection and portability doctors. | BYO validates the store interface shape; COS should retain stronger safe-write and evidence-grounded memory. |
| Compaction | Pluggable strategies: none, sliding window, model summary, safe split around tool results. | Context budgets and memory lifecycle docs exist; hook support varies by harness. | Adopt the safe split invariant and strategy interface in any COS-native runner. |
| Debug UX | Bubble Tea debug panel shows provider calls, tool dispatch, compacted context, token usage. | Surface 5/cosd exist but no equivalent turn-by-turn agent-loop visualizer. | High-value operator UX pattern for explaining governance and runtime decisions. |

## High-Value Patterns to Port

1. **Small agent-loop reference implementation**
   - Create an optional, non-product-center sample under a lab or `packages/agent-runtime` path.
   - Purpose: prove ADR-291 runtime semantics without requiring Claude Code/Codex.
   - Boundary: governance hooks remain authoritative for installed projects.

2. **Distinct LLM provider abstraction**
   - BYO cleanly isolates SDK-specific message formats from agent-loop code.
   - COS already has harness provider adapters; a runtime runner should not overload that package.
   - Recommended name: `internal/llm` or `packages/agent-runtime/.../llm`.

3. **Typed tool registry with deterministic definitions**
   - BYO sorts tool definitions, which helps prompt caching and reproducibility.
   - COS can reuse the pattern for service/headless tools: `read_file`, `write_file`, `bash`, `memory_recall`, `memory_save`, `delegate_*`, MCP wrappers.

4. **Write diff approval before mutation**
   - BYO computes a unified diff before `write_file` and shows it in the approval modal.
   - COS has safety hooks, but a standalone runtime needs a first-class mutation approval envelope before disk writes.

5. **Safe compaction split around tool pairs**
   - BYO's `SafeSplitPoint` avoids cutting between `tool_use` and `tool_result` messages.
   - This is a portable invariant for all future COS context reducers.

6. **Debug transcript/event panel**
   - BYO's `/debug on` makes hidden harness internals visible.
   - COS should expose a similar event stream in ADR-291 SSE and Surface 5: provider call, tool request, policy decision, memory access, compaction, cost.

7. **Subagent-as-tool model**
   - BYO implements delegation as a tool that starts another agent with isolated messages and curated tools.
   - COS should model future subagent delegation as a governed, auditable tool call with resource budgets, not as magic runtime behavior.

## Patterns to Avoid or Strengthen Before Adoption

- **Educational safety is not sufficient for production.** BYO approves tools interactively but does not implement COS-level blast radius, license, credential, claim-validation, or retry-exhaustion policies.
- **Memory recall is intentionally simple.** File summaries and substring recall are good for teaching but weaker than Engram v3 goals: evidence-grounded claims, safe writes, BM25 retrieval, approvals, and bundle portability.
- **No central config contract.** BYO intentionally uses inline code/env decisions. COS should use `cognitive-os.yaml`, manifests, and ADR-backed runtime settings.
- **Tool execution lacks policy layering.** For COS, `Tool.Execute` should be wrapped by policy, sandbox/workspace boundaries, audit ledgers, and rollback evidence.
- **Provider names can confuse.** BYO provider means LLM backend; COS provider currently means host harness adapter. Keep these separate.

## Suggested COS Slices

### Slice A — Runtime Vocabulary and Boundary Doc

Document the separation between:

- harness driver provider: Claude/Codex/Cursor/Devin hook payload adapter;
- LLM provider: Anthropic/OpenAI/local model adapter;
- tool registry: runtime-callable tools;
- agentic primitives: skills/hooks/rules/agents/memory projected into host surfaces.

### Slice B — Minimal COS Agent Runner Lab

Implement a tiny internal runner with:

- `Agent` loop;
- `LLMProvider` interface;
- `Tool` interface;
- mock provider for tests;
- no network service or default install path.

Acceptance criteria:

1. mock provider can request a tool and consume the result;
2. max-turn exhaustion is explicit;
3. tool result errors are returned to the model instead of panicking;
4. no mutation tool exists without an approval interface.

### Slice C — Agent-Service Runtime Adapter

Replace the deterministic local sync responses in `packages/agent-service/src/agent_service/runtime.py` with a bounded runtime adapter after Slice B proves the contract.

Acceptance criteria:

1. `/api/v1/oneshot/query` can run against a mock provider in tests;
2. SSE stubs emit real runtime events for tool requests and final answer;
3. bearer auth and kill switch remain unchanged;
4. all workspace mutations pass through a policy/approval envelope.

### Slice D — Debug/Event Schema

Define a durable event schema for:

- model request/response metadata;
- tool request/result;
- policy decision;
- memory save/recall;
- compaction before/after summaries;
- token/cost accounting.

This should feed both ADR-291 SSE and Surface 5 TUI.

### Slice E — Runtime Tool Policy Contract

Port BYO's simple approval hook into a COS policy chain:

1. static policy checks;
2. workspace/path boundary checks;
3. diff preview for writes;
4. human approval if required;
5. execution;
6. audit event;
7. rollback/checkpoint hook where applicable.

## Recommendation

Adopt BYO's architecture as a **reference lab for COS standalone runtime work**, especially ADR-291, not as a replacement for the existing governance mesh. The immediate value is pedagogical and architectural: it gives COS a concrete, testable way to explain and validate the boundary between OS-level governance and full harness ownership.

## Implemented Slice — 2026-05-23

The first COS runtime-lab slice has been implemented under `packages/agent-service/src/agent_service/runtime_lab/` and connected to ADR-291's local query paths through `packages/agent-service/src/agent_service/runtime.py`.

Implemented patterns:

- distinct LLM provider seam: `runtime_lab.llm.LLMProvider` and `MockLLMProvider`;
- typed deterministic tool registry: `runtime_lab.tools.ToolRegistry`;
- diff-first write approval: `WriteFileTool` emits unified diff approval events before mutation;
- safe compaction invariant: `safe_split_point` and `SafeSlidingWindow`;
- subagent-as-tool: `runtime_lab.subagents.SubagentTool`;
- debug/event stream: `EventRecorder` plus query SSE events (`llm.request`, `llm.response`, `agent.final`);
- MCP wrapper seam: `runtime_lab.mcp.MCPToolWrapper`, explicitly scoped to service/headless runtime use and not a replacement for host/user MCP configuration.

Validation:

```bash
cd packages/agent-service && uv run --extra testing pytest tests/test_runtime_lab.py tests/test_sessions.py tests/test_sse.py tests/test_contract.py -q
# 38 passed
```

## Trust Report

TRUST_REPORT: SCORE=82 STATUS=HIGH EVIDENCE=4 UNCERTAINTIES=2

Evidence:

1. Local clone at commit `77aa4db3fa3f606e6605b4b3275852129e93be6f`.
2. `go test ./...` passed in the BYO clone.
3. Reviewed BYO core files: `main.go`, `internal/agent/agent.go`, `internal/provider/provider.go`, `internal/tool/registry.go`, `internal/compact/strategy.go`, `internal/mcp/register.go`, `internal/memory/store.go`, `delegate.go`.
4. Reviewed COS anchors: `README.md`, `cognitive-os.yaml`, `internal/provider/*`, `packages/agent-service/*`, ADR-291, memory lifecycle documentation.

Uncertainties:

1. The website may have content generated from the repo that was not separately exhaustively crawled.
2. The user-provided transcript is treated as source context; the YouTube video itself was not rewatched.
