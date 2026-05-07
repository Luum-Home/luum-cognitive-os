# MCP as Orchestration Bus: COS Positioning Research

**Date:** 2026-05-06
**Author:** Research agent (Claude Sonnet 4.6)
**Scope:** MCP ecosystem state, May 2026; COS positioning decision
**Status:** Final draft — no code changes recommended

---

## 1. Executive Summary

The Model Context Protocol has, in 18 months, transformed from a niche Anthropic tool-calling standard into the de-facto interoperability layer of the agentic AI ecosystem. As of May 2026, the protocol is governed by the Linux Foundation's Agentic AI Foundation (AAIF), has over 10,000 public servers, 97 million SDK downloads per month, and is supported natively by ChatGPT, Gemini, VS Code, Cursor, Cline, and Claude Code. The protocol is no longer Anthropic's property; it is an open standard.

For Cognitive OS, this creates a concrete architectural decision that can no longer be deferred: MCP is the bus. The question is not whether COS should connect to it, but how.

**The verdict:** COS should be **both** an MCP server and an MCP client, but in that priority order. COS's governance, quality gate, and memory primitives are unique and high-value tools that any MCP client can consume. COS as a client (consuming GitHub MCP, Linear MCP, etc.) is also valuable but is lower priority because shell-out parity already works today. The first concrete MCP server to ship is the `@luum/mcp-server` package, which already has a skeleton with 8 tools defined — it needs implementation, not design.

**Top 3 takeaways:**
1. MCP is now a Linux Foundation standard with multi-vendor governance; betting against it is betting against the industry.
2. A governance-layer MCP server (COS as policy gateway + quality gate) fills a gap no existing server fills — it is differentiated.
3. The MCP gateway/aggregator market (17+ tools surveyed in Q1 2026) confirms that operator-layer governance above raw MCP servers is the unsolved problem COS is positioned to address.

---

## 2. The MCP Specification in Depth

### 2.1 Protocol History

MCP launched with Anthropic's Claude integrations in late 2024 as a JSON-RPC 2.0 protocol over stdio. Three specification revisions have followed:

| Revision | Key Changes |
|----------|-------------|
| 2025-03-26 | Introduced Streamable HTTP transport (replacing SSE-only), added JSON-RPC batching |
| 2025-06-18 | Removed JSON-RPC batching (breaking), added OAuth 2.1 authorization, structured tool outputs, server-initiated user interactions |
| 2025-11-25 | Added Client ID Metadata Documents (CIMD) for registration, made PKCE mandatory, added `Elicitation` primitive (server can request user input), added `Roots` (server can query filesystem boundaries) |

The removal of JSON-RPC batching in June 2025 is the only hard breaking change in the protocol's history. Teams that relied on batch requests had to refactor to sequential calls.

### 2.2 Current Primitives (November 2025 Revision)

**Server → Client capabilities:**
- **Tools** — Functions the AI model can execute. This is the primary integration surface.
- **Resources** — Context/data exposed to the user or model (files, database records, API responses).
- **Prompts** — Templated messages and reusable workflow fragments.

**Client → Server capabilities:**
- **Sampling** — Server-initiated LLM interactions (server can ask the host model to generate text).
- **Roots** — Server can query the client's accessible filesystem boundaries.
- **Elicitation** — Server can request additional information from the user (added November 2025).

**Utility primitives:** Progress tracking, cancellation, error reporting, logging, configuration.

### 2.3 The Tasks Primitive (SEP-1686)

The `Tasks` primitive shipped as experimental in late 2025 and addresses long-running agent workflows. It introduces lifecycle management for async operations: pending, running, completed, failed states with retry semantics. Production use has surfaced gaps in retry behavior on transient failures and result expiry policies. The 2026 roadmap treats closing these gaps as priority work before Tasks graduates from experimental.

The relevance to COS: COS primitives like `worktree-audit` and `secret-audit` are inherently long-running. Exposing them as MCP Tools today works for synchronous quick checks; exposing them as MCP Tasks (when stable) would enable richer async execution patterns.

### 2.4 Agent-to-Agent (A2A)

A2A is not an MCP extension — it is a separate, parallel protocol from Google, announced April 2025, targeted at agent-to-agent coordination rather than agent-to-tool access. The distinction is architectural:

- **MCP:** Agent calls an external tool/API/resource (vertical integration)
- **A2A:** Agent delegates to another agent (horizontal coordination)

A2A v1.0 stable is projected mid-2026. The MCP maintainers are "actively exploring how agent-to-agent communication overlaps with their protocol's future," and the 2026 roadmap's Tasks primitive is the closest current approximation of A2A within MCP. No formal convergence plan exists as of May 2026.

**COS implication:** COS's multi-agent orchestration model (spawning sub-agents via the harness) currently has no MCP representation. If A2A stabilizes, COS could expose sub-agent delegation as either an MCP Tool (simple) or an A2A endpoint (richer). This is a 2027 decision, not 2026.

### 2.5 Authorization Evolution

The June 2025 revision formalized OAuth 2.1 as the authorization standard for remote MCP servers. The November 2025 revision added:
- Client ID Metadata Documents (CIMD) as the standard client registration mechanism
- PKCE as mandatory for all clients (not optional)
- Scope-based 403 responses when a token lacks required permissions

For local/stdio MCP servers (the pattern COS currently uses via `@luum/advisor-mcp`), OAuth is not required — process-level isolation is the security boundary. For any COS-hosted remote MCP server, OAuth 2.1 with PKCE is now the spec-mandated path.

### 2.6 Transport Landscape

Two transports remain official after the March 2025 revision sunset SSE:

| Transport | Use Case | Latency | Scale |
|-----------|----------|---------|-------|
| **stdio** | Local integrations; one client per process | <1ms | Single client |
| **Streamable HTTP** | Remote/cloud servers; production | 10-50ms | Unlimited clients |

The 2026 roadmap's transport working group is addressing Streamable HTTP's horizontal scaling gap: sticky sessions fight load balancers because state is bound to a specific server instance. Planned fixes include stateless-by-default sessions, explicit session tokens in headers (not just bodies), and `/.well-known/mcp.json` Server Cards for pre-connection capability discovery.

**COS implication:** The current `@luum/advisor-mcp` package uses stdio (spawned as a child process). This is correct for a developer-local OS tool. If COS ever exposes primitives to remote clients or multi-user teams, Streamable HTTP with the upcoming stateless improvements is the migration path.

---

## 3. Server Ecosystem Map

### 3.1 Official Reference Servers

The `modelcontextprotocol/servers` GitHub repository maintains a reduced set of reference implementations after a mid-2025 archival pass:

**Active reference servers (steering group maintained):**
- `everything` — Reference/test server demonstrating all primitive types
- `fetch` — Web content fetching with LLM-friendly conversion
- `filesystem` — Secure file operations with configurable access controls
- `git` — Read, search, manipulate Git repositories
- `memory` — Knowledge graph-based persistent memory (note: overlaps with Engram)
- `sequential-thinking` — Dynamic problem-solving through thought sequences
- `time` — Time and timezone utilities

**Archived (moved to `servers-archived`):** GitHub, Slack, PostgreSQL. These were reference implementations, not production products; the ecosystem has moved to vendor-owned servers.

### 3.2 Major Production Servers

| Server | Owner | Auth | Transport | Maturity | Notes |
|--------|-------|------|-----------|----------|-------|
| **GitHub MCP** | GitHub/Microsoft | OAuth 2.1 + PKCE | HTTP | GA (Sept 2025) | Integrated in VS Code Copilot, Cursor, JetBrains; Lockdown mode for public repo safety |
| **Slack MCP** | Community/Slack | OAuth | HTTP | Community stable | Used for channel ops, message search |
| **Notion MCP** | Community | OAuth | HTTP | Community stable | Page/database CRUD |
| **Linear MCP** | Linear | OAuth | HTTP | Production | Issue tracking, sprint management; used by Firecrawl blog as production example |
| **Sentry MCP** | Sentry | OAuth | HTTP | Production | Full error context access |
| **Vercel MCP** | Vercel | OAuth | HTTP | Production | Deployment management |
| **Composio MCP** | Composio | OAuth | HTTP | Production | Aggregates 250+ integrations in one server |
| **Firecrawl MCP** | Firecrawl | API key | HTTP | Production | 13+ web scraping tools |
| **Context7 MCP** | Context7 | API key | HTTP | Production | Version-accurate library documentation |
| **E2B MCP** | E2B | API key | HTTP | Production | Secure cloud sandbox code execution |
| **Playwright MCP** | Community | None | stdio | Stable | Browser automation via accessibility tree |

The ecosystem is large but not evenly mature. The GitHub MCP server is the most battle-tested: GA status, Lockdown mode for prompt injection protection, `X-MCP-Tools` header for context-window optimization, and broad IDE integration.

### 3.3 Registry Scale

As of May 2026:
- **Official registry** (registry.modelcontextprotocol.io): Maintained by AAIF, community-curated
- **PulseMCP**: 14,000+ servers tracked, updated daily
- **Smithery / Composio**: Aggregator registries with security scanning, ratings, enterprise features
- **Claude connectors**: 75+ connectors in the Claude app, powered by MCP

The registry itself is becoming a governance challenge — no centralized security scanning requirement exists across the 10,000+ public servers. This is the same supply-chain problem npm faced; it is unresolved.

---

## 4. Client Ecosystem Map

### 4.1 MCP Client Maturity Matrix

| Client | MCP Support | Strengths | Target User |
|--------|-------------|-----------|-------------|
| **Claude Code** | Deep (tool search, scoped config, hook integration) | 1M context, SWE-bench 80.9%, hook system, Sonnet/Opus routing | COS native |
| **Cursor** | Native, mature | Polished IDE UX, 360K paying users, Agents Window | Teams wanting IDE experience |
| **Cline** | Most mature community marketplace | Open-source, BYOK, human-in-loop approvals | Budget-conscious devs |
| **Continue.dev** | Present but lightweight | Works with any LLM, VS Code + JetBrains | Devs wanting minimal autonomy |
| **Windsurf** | Native | Parallel multi-agent sessions, Cascade Hooks | Teams needing parallel workstreams |
| **Codex (OpenAI)** | TOML config, clean scoping | Cloud sandbox execution, PR delivery | GPT-native teams |
| **ChatGPT** | Apps SDK (announced 2025) | Widest consumer reach | Consumer/non-dev workflows |

Claude Code is the only client with a hook system that can intercept tool calls before/after execution — this is the COS governance integration point that no other client exposes.

### 4.2 Client-Side Governance Gap

None of the clients above implements operator-layer governance by default. They all trust the MCP server's tool descriptions. The November 2025 spec notes that "descriptions of tool behavior such as annotations should be considered untrusted, unless obtained from a trusted server." The responsibility for validation falls to the client or an intermediary layer. This is the gap COS can fill.

---

## 5. Orchestration Patterns Built on MCP

### 5.1 Three Core Orchestration Patterns

**Handoffs (Delegation):** A primary agent delegates to a specialized sub-agent exposed as an MCP Tool. The parent treats the sub-agent as a callable microservice. This is how COS's `consult_advisor` in `@luum/advisor-mcp` works today — executor agents call the advisor tool without caring what model is behind it.

**Chaining (Sequential Pipelines):** Agents form linear sequences where each stage transforms data. MCP provides the standardized interface so stages can be swapped without redesigning the pipeline.

**Agent Graphs:** Multiple agents communicate with feedback loops, parallelism, and dynamic routing. MCP handles the execution interface; orchestration logic lives in frameworks like LangGraph or COS's own DAG engine.

### 5.2 Gateway/Aggregator Layer

The 17-tool survey of Q1 2026 reveals that the market has "converged on flat aggregation with RBAC." No single tool satisfies hierarchical federation (nested namespaces, multi-tenant routing). The gap is real and unaddressed by existing tools.

**Tier 1 tools (most capable):**
- **IBM ContextForge** — Broadest transport support (7+ options), virtual server namespaces, mDNS federation; alpha/beta status
- **MetaMCP** — Only tool with explicit Servers/Namespaces/Endpoints hierarchy; limited by 1:1 endpoint mapping

**Notable production options:**
- **agentgateway** — Linux Foundation-backed, v1.0 stable, multi-tenancy
- **TrueFoundry** — Sub-3ms latency, 350+ RPS on 1 vCPU, unified LLM+MCP billing
- **Docker MCP Gateway** — Container isolation, cryptographically signed images
- **Lasso Security** — AI safety guardrails, PII detection, Presidio integration, 2024 Gartner Cool Vendor
- **Cloudflare MCP Portals** — Aggregates all registered servers behind one URL; in open beta for Cloudflare One customers (up to 50 free seats)
- **Microsoft MCP Gateway** — Azure AD + OAuth 2.0, Kubernetes-native, complex management

### 5.3 Security Patterns

The "triple-gate" pattern has emerged as best practice:
1. **AI layer**: Prompt filtering, PII detection, jailbreak detection
2. **MCP layer**: Tool authorization, parameter validation, scope enforcement
3. **API layer**: Rate limiting, authentication, audit trail

OpenTelemetry is emerging as the observability standard for MCP — the Python semantic conventions package ships MCP-specific metrics attributes (`mcp_attributes.py`, `mcp_metrics.py`), which COS's `.venv` already includes. This is not a coincidence; COS can hook into this instrumentation immediately.

### 5.4 Observability Gap

When an MCP tool call fails inside an agent, what does the operator see? Currently: almost nothing by default. The tool returns an error JSON-RPC response; the agent may retry or not; the operator has no cross-session trace.

Gateway-mediated deployments (Lasso, TrueFoundry, agentgateway) provide centralized audit trails queryable by user, operation, time range, and policy decision. stdio-deployed tools have no built-in observability beyond process-level monitoring.

**COS implication:** COS's existing `agent-heartbeat.jsonl` and `error-learning.jsonl` files fill this gap partially, but only for calls within the COS harness. For calls to external MCP servers consumed by COS agents, there is no unified trace today.

---

## 6. Verdict for COS: Server, Client, or Both

### 6.1 The Case for COS as MCP Server (Priority 1)

COS has unique primitives that no existing MCP server provides:

| COS Primitive | MCP Tool Name | What It Does | Why Valuable |
|---------------|---------------|--------------|--------------|
| `secret-audit` | `cos_check_credentials` | Scans staged changes for credential leaks | Blocks a class of security incidents before commit |
| `license-audit` (via `security-audit` skill) | `cos_license_check` | Validates dependency licenses against AGPL/SSPL blocklist | Compliance gate for enterprise operators |
| `worktree-audit` | `cos_worktree_status` | Reports divergence state of all git worktrees | Multi-agent coordination primitive |
| `adoption-truth` | `cos_adoption_report` | Measures actual vs. declared feature adoption | Prevents aspirational architecture drift |
| Quality gate | `cos_check_quality` | Prohibited terms, TODOs, stub detection | Universal code quality gate |
| Engram search | `cos_search_memory` | Retrieves cross-session decisions and discoveries | Context recovery for any agent |
| Rules lookup | `cos_get_rules` | Returns contextually relevant COS rules | Governance for non-COS-native agents |
| Status | `cos_status` | COS installation health: phase, rules, hooks | DevOps visibility |

The `@luum/mcp-server` package already has a `cos-package.yaml` declaring exactly these 8 tools. The implementation (`cos_mcp.py`) is referenced but the package directory contains only the manifest. This is a skeleton waiting for code, not a design problem.

**What makes this differentiated:** No current MCP server provides operator-layer governance. Existing security gateways (Lasso, etc.) provide threat detection *between* agents and servers. COS would provide quality gates and policy enforcement *about* what agents are doing to the codebase — a distinct and higher layer.

### 6.2 The Case for COS as MCP Client (Priority 2)

COS agents currently shell out to `gh` CLI, `git`, and other tools. Replacing some shell-outs with MCP tool calls has real advantages:

| Current Pattern | MCP Client Alternative | Gain |
|-----------------|----------------------|------|
| `gh issue list` shell-out | GitHub MCP `list_issues` | Structured JSON response, OAuth-scoped, auditble |
| `git log` shell-out | Git MCP server | Already installed as reference server |
| Ad-hoc web fetch | Firecrawl MCP / Fetch MCP | Unified tool interface, no custom scripting |
| Linear manual check | Linear MCP | Issue/sprint state without context switching |

However: the current shell-out approach works. The marginal benefit of MCP client adoption is real but not urgent. The risk is adding MCP infrastructure complexity before the server-side story is solid.

**Recommendation:** Adopt GitHub MCP as a COS client dependency in a second phase, scoped to agents that specifically need repository-level operations (e.g., `pr-review`, `issue-pipeline`). Do not attempt a wholesale replacement of shell-out patterns.

### 6.3 Should COS Be the Orchestrator that Hosts MCP Servers?

COS is already an orchestrator — it spawns sub-agents, routes by model tier, enforces quality gates, and manages session state. The question is whether it should also run an MCP server process that other orchestrators (Cursor, Claude Code in other projects, remote agents) can call.

The answer is yes, with scope control. COS-as-server should expose its *governance primitives*, not its *orchestration logic*. The distinction matters:

- Exposing `cos_check_quality` (a governance primitive) to Cursor is valuable — Cursor gets COS's quality gates without COS controlling Cursor's workflow.
- Exposing `cos_spawn_agent` (orchestration logic) via MCP creates tight coupling and trust boundary violations — a remote caller could trigger arbitrary sub-agent execution.

**Rule:** COS MCP tools should be read-mostly (audit, check, search, suggest) rather than write-mostly (spawn, apply, commit).

### 6.4 Permission Model

MCP tools from external servers that COS agents consume present a governance risk: COS does not control those servers' implementations, update cadence, or tool descriptions. The November 2025 spec acknowledges this: tool annotations "should be considered untrusted, unless obtained from a trusted server."

COS's `mcp-trust-pins.yaml` manifest (currently empty) is the right mechanism. Before any external MCP server is added to COS's agent configuration, it should be pinned by fingerprint (server name + command + args + env key names — never values). The `scripts/mcp_tofu_audit.py` file suggests this tooling exists or is planned.

The `hooks/mcp-scan.sh` hook is the enforcement point: it should fire on any `tool_use` event from an unpinned or modified MCP server and block or warn.

### 6.5 Concrete First MCP Server Proposal

**Deliverable:** Implement `packages/mcp-server/cos_mcp.py` with the 8 tools already declared in `cos-package.yaml`.

**Priority order for implementation:**

1. `cos_check_quality` — Runs the existing quality gate logic (prohibited terms, credential detection, TODOs, stubs) against a provided code snippet or path. Pure read. No external dependencies. Fast to implement.
2. `cos_search_memory` — Wraps Engram's `mem_search` + `mem_get_observation` as a single MCP tool. Allows any Cursor/Cline/Windsurf user to query COS's cross-session memory without launching a full COS session.
3. `cos_get_rules` — Returns relevant rules from the contextual rule index, given a task description. Allows non-COS agents to check governance rules before acting.
4. `cos_status` — Reports COS installation health. Diagnostic tool; low risk, high visibility.
5. `cos_check_credentials` (new, not yet in cos-package.yaml) — Wraps the `secret-audit` skill's detection logic. The most direct security value.

**Transport:** stdio for local development (current pattern, consistent with `@luum/advisor-mcp`). Streamable HTTP as a follow-up when multi-user or CI/CD scenarios arise.

**Auth:** No OAuth needed for stdio. When Streamable HTTP is added, use bearer token validation at the transport layer (single token for local CI/CD use; OAuth 2.1 PKCE for any multi-user deployment).

---

## 7. Comparable Protocols

### MCP vs. OpenAI Function Calling

| Dimension | MCP | OpenAI Function Calling |
|-----------|-----|------------------------|
| Discovery | Runtime (`tools/list` at connect time) | Compile-time (in API request body) |
| Provider lock-in | None | OpenAI only |
| Governance | Gateway-enforced | DIY per application |
| Auth | OAuth 2.1 (standardized) | Application-level |
| Audit trail | Automatic per invocation (via gateway) | Must implement |
| Multi-tenancy | Protocol-native | Application-level |
| Tool catalog changes | No redeploy required | Requires code change + deploy |

OpenAI Function Calling is superior for small, stable tool sets in OpenAI-only environments. MCP wins at scale, multi-provider, and enterprise governance.

### MCP vs. LangChain Tools

LangChain Tools are code-defined framework abstractions. They simulate runtime discovery through registries but don't standardize the wire format. LangChain and MCP are not competitors — LangChain can use MCP servers as tool sources. The common pattern in 2026 is LangChain providing orchestration logic while MCP handles cross-system tool access.

### MCP vs. Google ADK

Google ADK is purpose-built for Gemini and Vertex AI. It supports MCP natively as of late 2025, treating MCP servers as callable tools within ADK workflows. ADK's multimodal capabilities are superior for vision/audio/video tasks. For COS (text, code, governance), ADK is not relevant.

### MCP vs. A2A

As established above, these are orthogonal. MCP = agent-to-tool. A2A = agent-to-agent. They complement each other in a layered architecture. COS would consume both: MCP for tool access, A2A (when stable) for inter-agent coordination.

---

## 8. Cross-Cutting Analysis

### 8.1 COS's Natural MCP-Server Surface

The clearest candidates for immediate MCP exposure are the read/audit primitives:

- **`cos_check_quality`**: No side effects; runs in-process against code; fast.
- **`cos_search_memory`**: Read-only Engram access; cross-session context recovery.
- **`cos_get_rules`**: Read-only rules lookup; governance advisory.
- **`cos_status`**: Read-only health check.
- **`cos_check_credentials`**: Read-only scan; security-critical.
- **`cos_worktree_status`**: Read-only git state; coordination primitive.

Write tools (`cos_save_memory`, `cos_get_tasks`, `cos_suggest_skill`) need more careful permission design because they mutate COS state from an external caller.

### 8.2 COS's Natural MCP-Client Need

The highest-value client adoptions, ordered by friction-to-value ratio:

1. **GitHub MCP** (GA, OAuth 2.1, Lockdown mode): Replace `gh` shell-outs in `pr-review` and `issue-pipeline` skills. The `X-MCP-Tools` header allows selective tool exposure to avoid context window pollution.
2. **Git MCP** (official reference server): Replace git shell-outs in worktree and audit primitives.
3. **Fetch MCP** (official reference server): Replace ad-hoc `curl` in web-research workflows.

### 8.3 Observability When MCP Tool Calls Fail

Current state (COS stdio tools): No MCP-native observability. Errors surface as JSON-RPC error responses. The COS hook system (`PostToolUse` hook) can intercept these but only within the Claude Code harness.

The OpenTelemetry semantic conventions for MCP (already in COS's `.venv` via `opentelemetry.semconv._incubating.attributes.mcp_attributes`) define standard attributes: `mcp.server.name`, `mcp.tool.name`, `mcp.request.id`, `mcp.response.error_code`. Instrumenting `cos_mcp.py` with these attributes from day one would give COS operators structured traces for free in any OTel-compatible collector.

**Recommendation:** Add OTel instrumentation as a first-class requirement in the `cos_mcp.py` implementation spec, not an afterthought.

### 8.4 The Supply-Chain Risk

With 10,000+ public MCP servers and no mandatory security scanning at the registry level, the supply-chain risk is equivalent to early npm. COS's `mcp-trust-pins.yaml` + `mcp-scan.sh` + `mcp_tofu_audit.py` stack is the right direction. The gap is that `mcp-trust-pins.yaml` is currently empty (no pins) and `mcp_tofu_audit.py` has not been verified as implemented.

Before COS agents consume any external MCP server in production:
1. Pin the server in `mcp-trust-pins.yaml`.
2. Run `mcp_tofu_audit.py` on first use to generate the initial fingerprint.
3. Block tool calls from any server whose fingerprint has changed (via `mcp-scan.sh`).

---

## 9. Key Uncertainties

1. **A2A adoption trajectory**: Google's A2A is pre-v1.0 and has limited non-Google adoption. It could converge with MCP's Tasks primitive, remain parallel, or be absorbed. COS should not architect around A2A until v1.0 ships (projected mid-2026).

2. **MCP Tasks stability**: The Tasks primitive is experimental. Shipping COS's long-running audit primitives as Tasks today would create compatibility risk when the lifecycle semantics change. Wait for Tasks to graduate from experimental.

3. **Streamable HTTP stateless redesign**: The transport working group's planned stateless session model may change how session IDs work. Any Streamable HTTP implementation of `cos_mcp.py` should not depend on the current session ID mechanism.

4. **Registry security scanning**: No timeline exists for mandatory security scanning in the official MCP registry. COS cannot rely on the registry as a trust signal; all external server consumption requires explicit operator pinning.

5. **Claude Code MCP server discovery**: It is not confirmed whether Claude Code automatically discovers and loads MCP servers registered in `settings.json` sub-directories, or only at the project root. The `@luum/advisor-mcp` README assumes manual registration. This should be tested before relying on auto-discovery for `cos_mcp.py`.

---

## 10. Sources

1. [The 2026 MCP Roadmap — Model Context Protocol Blog](https://blog.modelcontextprotocol.io/posts/2026-mcp-roadmap/)
2. [Specification 2025-11-25 — modelcontextprotocol.io](https://modelcontextprotocol.io/specification/2025-11-25)
3. [MCP Spec Updates from June 2025 — Auth0 Blog](https://auth0.com/blog/mcp-specs-update-all-about-auth/)
4. [MCP Transport Future — Model Context Protocol Blog](https://blog.modelcontextprotocol.io/posts/2025-12-19-mcp-transport-future/)
5. [GitHub MCP Server — GA Announcement](https://github.blog/changelog/2025-09-04-remote-github-mcp-server-is-now-generally-available/)
6. [GitHub MCP Server — Tool-Specific Configuration](https://github.blog/changelog/2025-12-10-the-github-mcp-server-adds-support-for-tool-specific-configuration-and-more/)
7. [Official MCP Registry](https://registry.modelcontextprotocol.io/)
8. [Anthropic Donates MCP to Linux Foundation — Agentic AI Foundation](https://www.anthropic.com/news/donating-the-model-context-protocol-and-establishing-of-the-agentic-ai-foundation)
9. [MCP Aggregation, Gateway, and Proxy Tools: State of the Ecosystem (Q1 2026)](https://www.heyitworks.tech/blog/mcp-aggregation-gateway-proxy-tools-q1-2026)
10. [MCP vs OpenAI Function Calling vs LangChain — STOA Docs](https://docs.gostoa.dev/blog/mcp-vs-openai-function-calling-vs-langchain)
11. [MCP vs A2A vs AG-UI: AI Agent Protocols Guide 2026](https://nextpj.net/blog/mcp-a2a-ag-ui-ai-agent-protocols-guide-2026)
12. [Best MCP Clients in 2026 — Nimbalyst](https://nimbalyst.com/blog/best-mcp-clients-2026/)
13. [MCP Agent Orchestration: Chaining, Handoffs, and Multi-Agent Patterns](https://www.getknit.dev/blog/advanced-mcp-agent-orchestration-chaining-and-handoffs)
14. [MCP Gateway & Proxy Patterns — ChatForest](https://chatforest.com/guides/mcp-gateway-proxy-patterns/)
15. [Best MCP Gateways 2026 — TrueFoundry](https://www.truefoundry.com/blog/best-mcp-gateways)
16. [MCP Transport Protocols Comparison — MCPcat](https://mcpcat.io/guides/comparing-stdio-sse-streamablehttp/)
17. [MCP Authentication Guide — TrueFoundry](https://www.truefoundry.com/blog/mcp-authentication-in-cursor-oauth-api-keys-and-secure-configuration)
18. [Cloudflare Agents + MCP Documentation](https://developers.cloudflare.com/agents/model-context-protocol/)
19. [modelcontextprotocol/servers GitHub Repository](https://github.com/modelcontextprotocol/servers)
20. [MCP Release Notes — Speakeasy](https://www.speakeasy.com/mcp/release-notes)
21. [10 Best MCP Servers for Developers 2026 — Firecrawl](https://www.firecrawl.dev/blog/best-mcp-servers-for-developers)
22. [Every AI Coding CLI in 2026 — DEV Community](https://dev.to/soulentheo/every-ai-coding-cli-in-2026-the-complete-map-30-tools-compared-4gob)

---

## Appendix A: COS MCP Server Implementation Checklist

When implementing `packages/mcp-server/cos_mcp.py`, the following checklist applies:

- [ ] Use `fastmcp >= 2.0.0` (already declared in `cos-package.yaml`)
- [ ] Implement all 8 tools from `cos-package.yaml`
- [ ] Add `cos_check_credentials` as a 9th tool (wraps `secret-audit` skill logic)
- [ ] Instrument with OTel MCP semantic conventions from `opentelemetry.semconv._incubating`
- [ ] Expose via stdio transport initially (consistent with `@luum/advisor-mcp` pattern)
- [ ] Write at least one `tests/` unit test per tool (mock filesystem/engram calls)
- [ ] Update `mcp-trust-pins.yaml` with self-pin fingerprint after first install
- [ ] Add server health to `cos_status` output (reports whether MCP server is running)
- [ ] Document tool descriptions defensively — avoid instruction-like text that could be prompt-injected by a malicious caller

## Appendix B: MCP Ecosystem Decision Matrix

| Decision | Recommendation | Rationale |
|----------|---------------|-----------|
| COS as MCP server? | **Yes, Priority 1** | Unique governance primitives; skeleton exists |
| COS as MCP client? | **Yes, Priority 2** | GitHub MCP first; shell-out replacement |
| Remote vs. stdio transport? | **stdio now, HTTP later** | Consistency with advisor-mcp; complexity deferral |
| OAuth 2.1 now? | **No, not for stdio** | Only needed for remote/multi-user deployment |
| A2A integration? | **Wait for v1.0** | Pre-stable; divergence from MCP unclear |
| MCP Tasks for long-running? | **Wait for stable** | Experimental; lifecycle semantics may change |
| External MCP server trust? | **Pin everything** | `mcp-trust-pins.yaml` + `mcp-scan.sh` mandatory |
| Gateway adoption (Lasso, etc.)? | **Evaluate in Phase 2** | Only needed when COS serves remote multi-user |
