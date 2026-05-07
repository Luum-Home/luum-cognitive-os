# Dynamic Tool Registration: MCP-Based Runtime Discovery Architectures

**Research type**: Architecture gap analysis  
**Date**: 2026-05-06  
**Author**: Research agent (Sonnet 4.6)  
**Scope**: MCP server discovery, runtime tool list refresh, deferred loading, and recommendations for evolving COS `/tool-discovery` from skill-based to runtime-MCP-based registration  
**Word count**: ~3,100  
**Sources**: 18 (7 web searches, 11 web fetches)

---

## 1. Problem Statement

Cognitive OS currently implements tool discovery through a weekly-run skill (`skills/tool-discovery/skill.md`, ADR-216). This skill scans GitHub and web sources for new open-source tools, classifies them against a Tech Radar, and persists findings to Engram. It is a **search-and-classify** primitive — it discovers tools as ecosystem artifacts for future integration consideration, not as live callable primitives available within a running session.

What COS lacks is what Codex and Claude Code now provide in different degrees: **runtime, mid-session, MCP-based dynamic tool registration** — the ability for tools to appear, disappear, or become searchable within an already-running agent session without restart, reconfiguration, or skill invocation.

This document surveys the landscape of dynamic registration architectures, analyzes the lifecycle they implement, identifies permission and security implications, and concludes with recommendations for evolving COS.

---

## 2. Foundational Layer: MCP Protocol Mechanisms

### 2.1 The `tools/list` + `listChanged` Contract

The MCP specification (2025-06-18 and 2025-11-25) defines the primitive that everything else builds on. Servers that support tools declare a capability:

```json
{
  "capabilities": {
    "tools": {
      "listChanged": true
    }
  }
}
```

The `listChanged` flag signals that this server will emit `notifications/tools/list_changed` whenever its tool roster changes. The client's obligation upon receiving this notification is to re-issue `tools/list` and refresh its local tool map. No session restart, no reconnection, no re-initialization.

The notification payload is intentionally minimal:

```json
{
  "jsonrpc": "2.0",
  "method": "notifications/tools/list_changed"
}
```

This is a pull-trigger, not a push of tool definitions. The client always fetches the authoritative list from the server. This design ensures the client cannot have a stale copy of a tool definition once it re-fetches.

The `tools/list` endpoint also supports pagination via cursor, which becomes important at scale (registries with thousands of tools).

### 2.2 The Two-State Model

The Speakeasy analysis of MCP dynamic tool discovery describes a two-state model that servers use in practice:

- **Enabled state**: Tool is present in `tools/list` response, callable by the model.
- **Disabled state**: Tool is absent from `tools/list`, typically due to expired credentials, unavailable external service, or a permission change.

State transitions trigger `notifications/tools/list_changed`. The client re-fetches and its local view updates. From the model's perspective, the tool simply materializes or vanishes — no error, no graceful degradation, just clean presence/absence.

This is not true *registration* in the sense of new code being loaded; it is **conditional visibility** over a pre-defined catalog. True runtime registration (adding net-new tool handlers not compiled into the server) requires a different architecture (see Section 4).

---

## 3. Survey of Implementations

### 3.1 Claude Code: Deferred Loading via ToolSearch (January 2026)

Claude Code's approach does not implement server-side registration. Instead it solves the **context pollution** problem that arises when many MCP servers are connected: all tool definitions load at startup, consuming massive context.

The solution, announced January 14, 2026, is the Tool Search Tool (`tool_search_tool_regex_20251119` and `tool_search_tool_bm25_20251119`). The mechanism:

1. All tool definitions are provided in the API call, but marked `defer_loading: true` for tools that should not load immediately.
2. Claude sees only the Tool Search Tool plus any non-deferred tools at session start.
3. When Claude needs a capability, it issues a search (regex or BM25 natural language) against the deferred catalog.
4. The API returns `tool_reference` blocks pointing to 3-5 matching tools.
5. Those references expand into full definitions inline in the conversation — appended as `tool_reference` blocks, not modifying the system prompt prefix (preserving prompt caching).

Performance impact measured by Anthropic:

| Metric | Full Upfront Loading | With Tool Search |
|--------|---------------------|------------------|
| Token cost (50+ tools) | ~77K tokens | ~8.7K tokens |
| Token reduction | baseline | 85% |
| Tool selection accuracy (Opus 4.5) | 79.5% | 88.1% |
| Maximum catalog size | — | 10,000 tools |

This is **just-in-time context expansion**, not dynamic server registration. The tool definitions are all declared at session initialization; what changes is *when* they enter the context window.

Claude Code's `list_changed` handling is separate: when a connected MCP server sends `notifications/tools/list_changed`, Claude Code automatically refreshes available capabilities from that server without requiring disconnect/reconnect. A recent bug fix also addressed ToolSearch missing MCP tools that connected after session start in nonblocking mode.

**Gap**: Claude Code issue #14879 (closed as duplicate) and issue #6638 (closed as "not planned") document the unfulfilled request for *true mid-session MCP server loading* — the ability to launch a new MCP server process after the session has started and make its tools available. This remains unsolved.

### 3.2 OpenAI Codex: Configuration-Driven, Static at Session Start

Codex discovers MCP servers through explicit configuration (`config.toml`, project-scoped `.codex/config.toml`). Supported transports: STDIO (local process) and streamable HTTP.

Tool filtering is available via `enabled_tools` allowlist and `disabled_tools` denylist per server. However, the documentation reveals **no mechanism for runtime tool refresh or mid-session server loading**. Codex's MCP integration is static per session. Recent fixes addressed relative-path STDIO launches and added remote MCP server support in the Responses API, but not runtime registration.

The Codex model is best described as: *configuration registers servers at launch, the session uses whatever was configured*.

### 3.3 Spring AI: First-Class Runtime Registration (May 2025)

Spring AI's MCP integration is the most technically complete runtime registration implementation documented. The `McpSyncServer` class exposes three methods:

```java
server.addTool(SyncToolSpecification)   // register a new tool
server.removeTool(String toolName)       // deactivate by identifier
server.notifyToolsListChanged()          // signal connected clients
```

The framework's `ToolCallbackProvider` pattern means clients always fetch the current tool list on demand — the client implementation is designed around the invariant that `tools/list` always returns the most up-to-date state.

The critical lifecycle constraint Spring AI documents: **tools can only be added or removed after the client/server connection has been initialized**. Pre-initialization registration is handled via `@Tool` annotation and `ToolCallbackProvider` beans; post-initialization changes use the imperative API above.

This is true runtime registration: new `SyncToolSpecification` objects can be constructed programmatically and injected without any restart. The server notifies clients, clients re-fetch, and new tools become callable.

### 3.4 OpenCode: Plugin-Based Tool Registration

OpenCode implements a plugin architecture where TypeScript/JavaScript modules register tools via `ToolRegistry.register()`. Lifecycle:

1. **Load Phase**: OpenCode loads plugin files from four sources (global config, project config, global plugins dir, project plugins dir).
2. **Initialize Phase**: Plugin initializes internal state.
3. **Register Phase**: Plugin calls `ToolRegistry.register()`, optionally overriding built-in tools with the same name.
4. **Event Phase**: Tools fire `tool.execute.before` and `tool.execute.after` hooks.

npm plugins auto-install via Bun into `~/.cache/opencode/node_modules/`. Duplicate npm packages with the same name and version are loaded once. Dependencies are managed via `.opencode/package.json`.

This is **load-time** plugin registration (at session/app start), not mid-session. But the architecture is modular enough that a plugin could theoretically register new tools in response to events — the `ToolRegistry.register()` call replaces or appends, and the session sees the updated registry.

### 3.5 Composio: Per-Session Dynamic Tool Scoping

Composio takes a different angle: rather than registering new tool code, it dynamically **scopes** which tools from its 100+ toolkit catalog are visible to an agent, per session and per user.

The session model:

```python
session = composio.create(user_id)
tools = session.tools()              # provider-compatible tools for this user
mcp_url = session.mcp.url            # or MCP endpoint for any MCP client
```

The `allowed_tools` parameter on MCP server creation creates task-specific tool exposure. The Composio Tool Router dynamically loads tools from its catalog based on the task at hand, all through a single MCP endpoint.

Authentication is per-user-session, not global. This enables multi-tenant architectures where different agents operating simultaneously see different tool subsets.

The dynamic quality here is: **what the model sees is determined at session creation time by user identity and task context**, with the underlying catalog being the full Composio integration set.

### 3.6 Smithery: Registry as Discovery Infrastructure

Smithery functions as a **registry and management platform** — a layer above individual MCP servers. It provides:

- **Human-browsable directory**: 6,000+ community-submitted servers, browsable by category.
- **Machine-readable registry API**: MCP clients can programmatically query `registry.modelcontextprotocol.io` to discover servers.
- **Deployment models**: Local install (via Smithery CLI) or hosted remote (authenticated endpoints).
- **TypeScript SDK**: Programmatic connection to hosted servers, tool listing, and invocation.

Smithery's role in dynamic registration is as **discovery infrastructure** — it lets a client (or orchestrator) programmatically discover *which MCP servers exist and how to connect to them*, without needing to pre-configure them. An agent could query Smithery's registry at runtime, decide to connect to a new server, and integrate its tools.

This is the missing link between "I know a tool exists" and "the tool is callable in my session" — but Smithery does not solve the last-mile problem of injecting a newly discovered server into a running session.

### 3.7 Dynamic MCP Server (scitara-cto): Handler Package Pattern

The `dynamic-mcp-server` OSS framework explicitly solves compile-time vs. runtime tool registration. Its architecture:

- **Handler Packages**: Named collections of related tools with schemas, permissions (`rolesPermitted`), and a dispatch handler function.
- **Session-based Loading**: Tools are populated per-user session via role filtering after API key authentication.
- **Registration call**: `server.registerHandler(packageName)` after server initialization.
- **Template variables**: `config.args` maps using `{{location}}`-style references to tool inputs and environment variables.

This framework enables tools to be defined and registered entirely at runtime — the server can load handler packages from a database, config store, or API call, then expose them as MCP tools to any connected client.

---

## 4. Dynamic Registration Lifecycle

Synthesizing across implementations, three distinct lifecycle patterns emerge:

### Pattern A: Startup-Static with Conditional Visibility
**Used by**: Codex, Claude Code (default), most MCP clients  
**Flow**: All tools declared at session start → conditional `list_changed` removes/restores tools → no new tool code ever loads mid-session.  
**Limitation**: Tool catalog is bounded by what was configured at start.

### Pattern B: Deferred Context Expansion (Just-In-Time)
**Used by**: Claude Code ToolSearch, Anthropic API `defer_loading`  
**Flow**: All tool definitions declared at start → most deferred from context → search query triggers inline expansion of 3-5 relevant definitions → model calls them normally.  
**Limitation**: Catalog is still closed (all tools must be declared upfront). No new server processes can be added.

### Pattern C: True Runtime Registration
**Used by**: Spring AI MCP, dynamic-mcp-server, theoretically Smithery-connected orchestrators  
**Flow**: Server starts → handler packages registered via API → `addTool()` injects new tools → `notifyToolsListChanged()` signals clients → clients re-fetch → new tools callable.  
**Limitation**: Requires server-side support (`listChanged` capability). Client must handle incremental updates. Security surface expands significantly.

---

## 5. Permission and Security Implications

Dynamic registration opens attack surfaces that static registration does not:

**Tool Injection Risk**: If a server can register new tools after session start, a compromised server process could inject tools with names designed to be called preferentially (e.g., a malicious `read_file` that shadows a legitimate one).

**Capability Escalation**: Tools registered mid-session may have permissions never reviewed by the user. MCP spec requires `listChanged` to be declared upfront (capability negotiation at connect time), which limits surprise registrations to servers the client already trusts — but trust granted at session start may not extend to tools added an hour later.

**Deregistration Gaps**: When a tool is removed via `removeTool()` or `list_changed`, any in-flight tool calls referencing it become undefined. Clients must handle `Unknown tool: invalid_tool_name` JSON-RPC errors gracefully.

**Session Scope Leakage**: Per-session tool scoping (Composio model) requires session tokens to be validated per-request, not just at connection time. A leaked session token that grants expanded tool access is more dangerous than a leaked API key with static permissions.

**MCP Spec Guidance**: The specification states clients MUST consider tool annotations to be untrusted unless they come from trusted servers, and clients SHOULD prompt for user confirmation on sensitive operations. These recommendations become harder to enforce when tool definitions are dynamic.

The `dynamic-mcp-server` framework addresses this via `rolesPermitted` arrays that filter tools per session before the model sees them — role-based access control baked into the registration model rather than bolted on.

---

## 6. Current COS Tool Discovery Architecture

COS `/tool-discovery` (ADR-216) is an **ecosystem scanning skill**, not a runtime registration system. It:

- Runs weekly via the `skill.md` protocol, searching GitHub topics and web sources.
- Classifies findings against a Tech Radar (ADOPT/TRIAL/ASSESS/HOLD) with weighted scoring.
- Persists to Engram at `tool-discovery/{date}`.
- Does not touch the live tool registry or MCP configuration.

The `manifests/tool-discovery-preuse.yaml` adds a complementary **pre-use gate** that blocks ad-hoc tool invocations when COS already has a canonical primitive — preventing tool reinvention during execution rather than managing the live registry.

`lib/tool_discovery_preuse.py` implements the enforcement: pattern-matching against `command_patterns`, bypass via `allow_if_contains` or `COS_ALLOW_TOOL_DISCOVERY_BYPASS=1`.

The gap is that COS has no mechanism to:
1. Discover a new MCP server at runtime and make its tools available mid-session.
2. Defer loading of known-but-rarely-needed tools until they are searched for.
3. Respond to `notifications/tools/list_changed` from COS-internal servers with session-level tool refresh.

---

## 7. Recommendations for Evolving COS

### Recommendation 1: Implement Deferred Loading for MCP Toolsets (Pattern B)

**Priority**: High. **Effort**: S.

COS agents should adopt Anthropic's `defer_loading: true` + ToolSearch pattern for any session that connects to MCP servers with more than ~10 tools. The token savings (85% reduction) and accuracy improvement (from 79.5% to 88.1%) are proven at production scale.

Implementation path:
- The `add-mcp` skill and session initialization code should emit tool definitions with `defer_loading: true` by default for all but 3-5 frequently-used core tools.
- Sub-agent prompts should include the `tool_search_tool_bm25_20251119` tool in their tool list when launching with large MCP toolsets.
- The `lib/dispatch.py` LLM dispatch layer (ADR-049) should be updated to insert the ToolSearch tool when estimated tool token count exceeds 10K.

This is the lowest-friction path: no changes to MCP server code, no protocol extensions, no security surface expansion. It is a pure client-side optimization using an already-shipped Anthropic API feature.

### Recommendation 2: Add `listChanged` Response to COS MCP Client Layer

**Priority**: Medium. **Effort**: M.

Any COS component that acts as an MCP client (Claude Code harness, the `mcp-builder` skill's output, orchestrator-managed sub-agents) should implement `toolsChangeConsumer` / `notifications/tools/list_changed` handling. When a COS-internal MCP server changes its tool roster (e.g., because credentials refreshed, a dependent service came back online, or a new integration was activated), the session should automatically see the updated list without restart.

Concretely: the COS MCP server infrastructure (`packages/`, any server managed by `add-mcp`) should declare `"tools": { "listChanged": true }` in their capability response, and implement `addTool`/`removeTool` to handle conditional visibility based on auth state. The Spring AI and `dynamic-mcp-server` patterns are the reference implementations.

This primarily benefits scenarios where COS tools become unavailable mid-session (expired OAuth tokens, downed services) and should gracefully re-appear once restored.

### Recommendation 3: Build a Session-Scoped Tool Router Primitive

**Priority**: Medium-Low. **Effort**: L.

Longer term, COS should implement a **session-scoped tool router** inspired by Composio's per-session model and the `dynamic-mcp-server` handler package pattern. The design:

- At session creation, the orchestrator queries Engram for the task context and derives a `tool_profile` (which MCP servers / tool categories are relevant).
- The COS MCP aggregator server exposes only the tools matching that profile to the session's model.
- If the task evolves (new subtask identified), the orchestrator can call an internal API to update the session's `tool_profile`, triggering `notifications/tools/list_changed` and a re-fetch.
- Role-based filtering (`rolesPermitted` per the `dynamic-mcp-server` pattern) ensures tools requiring elevated permissions are only visible to sessions authorized for them.

This addresses the core complaint from Claude Code issue #14879: agents currently have no way to declare "I now need postgres tools" and have them materialize. With a session-scoped router, the orchestrator (which has that semantic awareness) bridges the gap — it translates the agent's intent into a tool profile update and the server makes new tools visible.

The `skill-invocation-mandatory` rule in `RULES-COMPACT.md` (Section 11) already establishes that high-confidence skill suggestions are mandatory — this primitive would give that rule runtime enforcement by making tools discoverable rather than requiring the agent to know their names upfront.

---

## 8. Gap Summary Table

| Capability | Claude Code | Codex | OpenCode | COS (current) |
|-----------|-------------|-------|----------|---------------|
| Static MCP at start | Yes | Yes | Via plugins | Via add-mcp |
| `list_changed` refresh | Yes (auto) | No docs | No | No |
| Deferred context loading | Yes (ToolSearch) | No | No | No |
| Mid-session server add | No (requested) | No | No | No |
| True runtime registration | Via MCP protocol | No | Via ToolRegistry | No |
| Per-session scoping | No | Via filter lists | Via project plugins | Via preuse gate |
| Registry-backed discovery | Via Smithery | Via Smithery | No | Skill-based only |

---

## 9. Conclusion

The gap between COS's current `/tool-discovery` skill and the runtime registration capabilities of peer systems is real but bridgeable in stages. The Anthropic `defer_loading` + ToolSearch pattern (Pattern B) is the highest ROI immediate improvement — it requires no server changes and delivers measurable accuracy and token benefits. Adding `listChanged` response handling closes the reliability gap when COS services cycle. The session-scoped tool router is the longer-term architectural investment that would give COS genuine runtime extensibility comparable to Spring AI's model.

The existing `tool-discovery-preuse` gate and skill remain valuable as complementary primitives: one governs what tools enter the session context (pre-use enforcement), the other governs how developers discover new tools for future integration (weekly ecosystem scan). Neither should be removed in favor of runtime registration — they serve different layers of the tool lifecycle.

---

## Sources

1. [Dynamic Tool Updates in Spring AI's Model Context Protocol](https://spring.io/blog/2025/05/04/spring-ai-dynamic-tool-updates-with-mcp/) — Spring.io, May 2025
2. [Tool search tool — Claude API Docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool) — Anthropic, 2026
3. [Tools — Model Context Protocol Specification 2025-06-18](https://modelcontextprotocol.io/specification/2025-06-18/server/tools) — MCP Spec
4. [One Year of MCP: November 2025 Spec Release](https://blog.modelcontextprotocol.io/posts/2025-11-25-first-mcp-anniversary/) — MCP Blog
5. [Dynamic tool discovery in MCP](https://www.speakeasy.com/mcp/tool-design/dynamic-tool-discovery) — Speakeasy
6. [Scaling MCP Tools with Anthropic's Defer Loading](https://unified.to/blog/scaling_mcp_tools_with_anthropic_defer_loading) — Unified.to
7. [dynamic-mcp-server — GitHub](https://github.com/scitara-cto/dynamic-mcp-server) — scitara-cto
8. [What is MCP Tool Search? — Claude Code feature guide](https://www.atcyrus.com/stories/mcp-tool-search-claude-code-context-pollution-guide) — atcyrus.com
9. [FEATURE: Dynamic MCP Server Loading During Sessions — Issue #14879](https://github.com/anthropics/claude-code/issues/14879) — anthropics/claude-code
10. [Add dynamic loading/unloading of MCP servers — Issue #6638](https://github.com/anthropics/claude-code/issues/6638) — anthropics/claude-code
11. [Model Context Protocol — Codex Docs](https://developers.openai.com/codex/mcp) — OpenAI
12. [Plugins — OpenCode Docs](https://opencode.ai/docs/plugins/) — opencode.ai
13. [Smithery AI: A central hub for MCP servers](https://workos.com/blog/smithery-ai) — WorkOS
14. [Single Toolkit MCP — Composio Docs](https://docs.composio.dev/docs/single-toolkit-mcp) — Composio
15. [Add defer tool loading — Issue #762](https://github.com/modelcontextprotocol/go-sdk/issues/762) — modelcontextprotocol/go-sdk
16. [Support deferred loading — Issue #3590](https://github.com/pydantic/pydantic-ai/issues/3590) — pydantic/pydantic-ai
17. [Using notifications/tools/list_changed — Discussion #76](https://github.com/orgs/modelcontextprotocol/discussions/76) — MCP GitHub
18. [Add support for MCP dynamic tool update — Gemini CLI Issue #13850](https://github.com/google-gemini/gemini-cli/issues/13850) — google-gemini/gemini-cli
