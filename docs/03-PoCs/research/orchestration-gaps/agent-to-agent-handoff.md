# Agent-to-Agent Handoff Protocols: Research Report

**Date:** 2026-05-06  
**Scope:** Multi-agent handoff protocols across OpenAI Swarm/Agents SDK, AutoGen, CrewAI, LangGraph, Google A2A, Anthropic Agent Teams, ElevenLabs, Microsoft Copilot Studio, Slack, and production case studies.  
**Purpose:** Evaluate options for COS agent handoff protocol (operator-in-loop, local-first, manifest-driven governance posture).

---

## 1. Executive Summary

Agent-to-agent (A2A) handoff is the mechanism by which a running agent transfers task ownership, context, and optionally permissions to another agent. The field has converged on three architectural shapes: **hub-and-spoke** (one orchestrator routes everything), **peer chain** (agents hand off sequentially with no return path), and **swarm** (any agent can hand off to any other based on capability signals).

OpenAI Swarm (2024) established the canonical handoff primitive: a tool call returning an `Agent` object, with full conversation history carried over and the new agent's system prompt replacing the old one. Its production successor, the OpenAI Agents SDK, keeps this shape but adds input filtering, history collapsing, and typed input schemas for handoff metadata. LangGraph adds graph-native `Command` objects that combine routing and state mutation in a single return. Google A2A (April 2025) is the first open, cross-vendor protocol—built on JSON-RPC 2.0 over HTTPS with cryptographically signed Agent Cards.

The cross-cutting finding is that **context passing is the hardest unsolved problem**. Full history is expensive and eventually exceeds context limits. Summarization is lossy. Production systems are moving toward structured, queryable context layers with progressive compression, but no framework ships this out of the box.

The failure mode nobody documents: **infinite handoff loops** (A → B → C → A) combined with context loss cause 41–87% failure rates on state-of-the-art open-source multi-agent systems according to the 2025 MAST taxonomy paper. No production framework has a built-in loop detector.

**COS recommendation:** Adopt a manifest-declared handoff graph with a single `HandoffEnvelope` data structure, operator-gated handoffs above a configurable blast radius, and a bounded-depth call stack enforced at runtime. This maps to LangGraph's Command pattern adapted for local-first operation without a cloud routing layer.

---

## 2. Per-System Deep Dive

### 2.1 OpenAI Swarm (deprecated) → Agents SDK (production)

**Repository:** github.com/openai/swarm (archived); openai.github.io/openai-agents-python  
**Status:** Swarm deprecated October 2024. Agents SDK is the production successor (March 2025).

#### Handoff Mechanism

Swarm's core primitive: an agent function returns an `Agent` object instead of a string. The execution loop detects this and switches active agent. The `Result` dataclass allows combining value return, agent switch, and context variable update in one atomic operation.

In the Agents SDK, handoffs are represented as tools. If the destination agent is named `RefundAgent`, the tool name is `transfer_to_refund_agent`. This makes handoffs first-class LLM tool calls, not magic internal state changes.

```python
# Agents SDK handoff definition
handoff_obj = handoff(
    agent=billing_agent,
    tool_name_override="escalate_to_billing",
    tool_description_override="Use when user has billing questions",
    on_handoff=log_transfer_reason,  # callback fires at handoff time
    input_type=BillingContext,       # typed handoff metadata schema
    input_filter=remove_all_tools,   # filter conversation history
    nest_handoff_history=True        # collapse history into <CONVERSATION HISTORY> block
)
```

#### Context Passing

`context_variables` in Swarm is a shared dict passed to `client.run()`, optionally injected into agent instructions (if instructions is a callable) and tool functions. It persists across agent switches. The Agents SDK replaces this with a typed `RunContextWrapper` passed via dependency injection.

`input_filter` receives a `HandoffInputData` object with three history slices (`input_history`, `pre_handoff_items`, `new_items`) and can return a trimmed version. The `nest_handoff_history` flag collapses the prior transcript into a single assistant message block to keep the receiving agent's context manageable.

#### Permission Model

Handoffs stay within a single `Runner.run()` call. Input guardrails apply only to the first agent; output guardrails only to the final agent. There is no tool scoping per destination agent—the receiving agent inherits whatever tools it was initialized with, not a subset of the caller's tools.

#### Deadlock and Termination

The Agents SDK has a `max_turns` parameter. No documented circular handoff detection. The SDK recommends the `recommended_prompt_prefix` which instructs the model to recognize when it's been handed off and not to re-initiate transfers to the same agent.

#### Key Limitation

Handoffs are client-side and stateless between calls. No server-side state persistence. The framework "runs almost entirely on the client."

---

### 2.2 AutoGen GroupChat / Microsoft Agent Framework

**Repository:** microsoft.github.io/autogen  
**Status:** AutoGen 0.4+ unified with Semantic Kernel as Microsoft Agent Framework (public preview October 2025, v1.0 late 2025).

#### Speaker Selection Patterns

Three team types:
- `RoundRobinGroupChat`: fixed rotation, no intelligence in selection
- `SelectorGroupChat`: LLM selects next speaker based on conversation history and agent descriptions; by default prevents the same agent from speaking twice in a row
- `Swarm`: handoff-message-only selection—the active agent emits a `HandoffMessage` naming the next agent, or keeps going if no handoff

The `SelectorGroupChat` selection prompt template includes all participant names, their descriptions, and the conversation history. The LLM decision is fully transparent and log-able.

#### Message Envelope

AutoGen uses a typed message protocol:
- `TextMessage`: normal communication
- `ToolCallRequestEvent` / `ToolCallExecutionEvent` / `ToolCallSummaryMessage`: tool use cycle
- `HandoffMessage`: peer-to-peer transfer request (Swarm pattern)
- `UserInputRequestedEvent`: human-in-loop gate

The `BroadcastChannelTopic` pattern (AutoGen core, not agentchat) uses publish-subscribe: agents publish messages to a topic; all subscribers receive them. This is the basis for groupchat—a `GroupChatMessage` topic is subscribed to by all participants plus the manager.

#### Context Passing

Conversation history is "kept within the team and all participants, so the next task can continue from the previous conversation context." All agents see the full shared history unless explicitly filtered. No built-in progressive compression.

#### Termination

Termination conditions are composable operators:
- `TextMentionTermination(text="TERMINATE")`: any agent can signal done
- `MaxMessageTermination(max_messages=25)`: budget cap
- `StopMessageTermination`: specific message type stops the loop
- Conditions combine with `|` (OR) and `&` (AND) operators

Custom selector functions can also filter the candidate agent list each turn, preventing certain transitions and breaking potential loops.

#### Circular Handoff Prevention

No automatic deadlock detection. Custom selector functions return `None` to indicate no valid next speaker, which terminates the loop. The pattern recommendation is to encode graph edges in the selector function rather than relying on LLM routing.

---

### 2.3 CrewAI Hierarchical Process

**Repository:** docs.crewai.com; github.com/crewAIInc/crewAI  
**Status:** Active. Hierarchical mode requires explicit `Process.hierarchical` flag.

#### Delegation Mechanism

The manager agent is an LLM instance (configured via `manager_llm`) with access to two built-in tools:
- `Delegate work to coworker(coworker, task, context)`: dispatches a task
- `Ask question to coworker(coworker, question, context)`: queries without full delegation

These tools accept `coworker` (role name, case-insensitive), `task` (natural language description), and `context` (background information string). The manager LLM decides which worker to invoke and what context to pass.

The 2025 PR #2068 added `allowed_agents` filtering: the manager can only delegate to agents in the explicit allowlist, preventing uncontrolled delegation breadth.

#### Permission and Trust Model

Worker agents that should not further delegate must have `allow_delegation=False`. The recommended pattern is: manager orchestrates, workers execute, tools live on workers. The manager has no tools—it only has delegation tools. This creates a clean trust boundary.

Task outputs flow back to the manager as string results. The manager evaluates quality against expected output format and either accepts or re-delegates. There is no schema validation of worker output—trust is fully delegated to the manager LLM's judgment.

#### Known Production Failures

Community issues (2025-2026) document:
- Manager delegating to wrong agent when role descriptions are ambiguous
- `allowed_agents` not respected in some edge cases (Issue #4783)
- No built-in retry budget enforcement; a confused manager can loop indefinitely

---

### 2.4 LangGraph Supervisor Pattern

**Repository:** github.com/langchain-ai/langgraph-supervisor-py  
**Status:** Active. langgraph-supervisor v0.0.x, Python and JS implementations.

#### Supervisor Architecture

The supervisor is a dedicated LLM node whose only job is routing. It takes the current state (messages, task context) and returns a `Command(goto=target_agent_name)`. Workers are subgraphs; the supervisor is a node in the parent graph.

```python
# Simplified supervisor pattern
supervisor_node = create_supervisor(
    agents=[research_agent, write_agent],
    model=model,
    prompt="Route user requests to the appropriate specialist."
)
graph = StateGraph(State)
graph.add_node("supervisor", supervisor_node)
graph.add_node("researcher", research_agent)
graph.add_node("writer", write_agent)
```

The `Command` object is the LangGraph primitive for combined routing + state update:
```python
Command(
    goto="writer",
    update={"messages": [output_message], "active_agent": "writer"},
    graph=Command.PARENT  # route to parent graph node, not within subgraph
)
```

#### State Management

All agent state flows through a centralized `messages` list with an `add_messages` reducer. Each agent can use private state keys (e.g., `alice_messages`) internally, with wrapper functions translating between private and shared state at handoff boundaries.

The `Command.PARENT` routing enables hierarchical graphs: a subgraph agent can hand off to a sibling subgraph by routing to the parent graph's node. This is the mechanism for peer-to-peer handoffs within a structured hierarchy.

#### Deadlock Prevention

No built-in circular handoff detection. The recommended pattern is `max_iterations` on the graph executor. Type annotations on node return types enable static analysis of possible routing paths (graph visualization preserves these hints), but runtime loop detection is left to the application layer.

---

### 2.5 LangGraph Swarm Pattern

**Repository:** github.com/langchain-ai/langgraph-swarm-py

#### Handoff Tools

`create_handoff_tool(agent_name, description)` generates a tool for each possible transfer target. The active agent calls this tool when it determines another agent should handle the next step. No central supervisor is involved.

By default, the handoff tool passes:
- Full message history from the swarm's shared `messages` list
- A `ToolMessage` confirming successful handoff
- The `active_agent` field updates to the new agent name

The `Command` return from a handoff tool:
```python
return Command(
    goto=target_agent_name,
    graph=Command.PARENT,
    update={"messages": [tool_message], "active_agent": target_agent_name}
)
```

Custom handoff tools can trim history, inject task summaries, or add structured metadata before transfer.

#### Swarm vs Supervisor Tradeoffs

| Dimension | Supervisor | Swarm |
|-----------|-----------|-------|
| Routing control | Centralized, one LLM call per turn | Distributed, each agent decides |
| Debuggability | High—one routing node, all decisions logged | Low—emergent routing |
| Latency | Higher—extra LLM call per routing step | Lower—direct handoffs |
| Deadlock risk | Low—supervisor holds global view | High—agents lack global state |
| Best for | Complex routing logic, auditability needed | Known handoff graph, latency-critical |

---

### 2.6 Google Agent2Agent (A2A) Protocol

**Specification:** a2a-protocol.org/latest/specification  
**Status:** Open standard, Apache 2.0, Linux Foundation governance (June 2025). 150+ partner organizations by April 2026.

#### Protocol Stack

A2A sits above transport (HTTPS) using JSON-RPC 2.0. Agents communicate by:
1. Fetching the remote agent's `/.well-known/agent-card.json` for capability discovery
2. Calling `tasks/send` with a `Message` payload to initiate work
3. Polling `tasks/get` or subscribing to SSE stream for task status
4. Receiving `Artifact` objects on completion

#### Task State Machine (8 states)

```
SUBMITTED → WORKING → COMPLETED (terminal)
                    ↘ FAILED    (terminal)
                    ↘ CANCELED  (terminal)
                    ↘ REJECTED  (terminal)
                    ↘ INPUT_REQUIRED (interrupted, awaits input)
                    ↘ AUTH_REQUIRED  (interrupted, awaits auth)
```

Terminal states close all active streams. `INPUT_REQUIRED` and `AUTH_REQUIRED` suspend processing until the initiating agent provides additional input.

#### Message Envelope

```json
{
  "messageId": "uuid",
  "role": "USER | AGENT",
  "parts": [
    {"text": "string content"},
    {"data": {"key": "value"}},
    {"url": "https://...", "mediaType": "application/pdf"},
    {"raw": "base64-encoded-bytes"}
  ],
  "contextId": "grouping-key",
  "taskId": "task-uuid",
  "referenceTaskIds": ["prior-task-uuid"],
  "metadata": {},
  "extensions": {}
}
```

`referenceTaskIds` is the key mechanism for chaining context across agent calls without passing full history—the receiving agent can fetch prior tasks if needed.

#### Agent Card Schema

The Agent Card is a signed JSON document at `/.well-known/agent-card.json`:
```json
{
  "name": "BillingAgent",
  "version": "1.2.0",
  "capabilities": {
    "streaming": true,
    "pushNotifications": true,
    "extendedAgentCard": false
  },
  "skills": [{"name": "process-refund", "inputSchema": {...}}],
  "securitySchemes": {"bearer": {"type": "http", "scheme": "bearer"}},
  "signature": "base64-cryptographic-sig"
}
```

Capability flags are explicit—a client does not attempt streaming if the card does not declare support.

#### Trust and Authentication

Five supported auth schemes: API key, HTTP bearer, OAuth2 (authorization code, client credentials, device code), OpenID Connect, mutual TLS. The protocol requires explicit credential negotiation per agent pair. Trust is not inherited—each A2A relationship is independently authenticated.

The cryptographic signature on Agent Cards enables authenticity verification, preventing impersonation of legitimate agents.

#### Deadlock Notes

The spec addresses concurrent stream termination but does not define circular task detection. The asynchronous, event-driven architecture means agents do not block on responses—they submit tasks and receive callbacks—which reduces blocking deadlocks but not logical infinite loops.

---

### 2.7 Anthropic Claude Code Agent Teams

**Documentation:** code.claude.com/docs/en/agent-teams  
**Status:** Experimental, disabled by default as of May 2026. Requires Claude Code v2.1.32+.

#### Architecture

```
Team Lead (main session)
  ├── Shared Task List (~/.claude/tasks/{team-name}/)
  ├── Mailbox (inter-agent messaging)
  └── Teammates (independent Claude Code sessions)
       ├── Teammate A (own context window)
       ├── Teammate B (own context window)
       └── Teammate C (own context window)
```

Key distinction from subagents: **teammates communicate directly with each other**. Subagents are fire-and-forget workers that report only to the orchestrator. Teammates share a task list, claim work autonomously, and message each other by name.

#### Communication Protocol

- **Mailbox delivery**: messages delivered automatically, lead does not poll
- **Task file locking**: prevents race conditions when multiple teammates claim the same task simultaneously
- **Idle notifications**: automatic—a teammate notifies the lead on completion without explicit polling
- **Teammate discovery**: teammates read `~/.claude/teams/{team-name}/config.json` to get peer session IDs

#### Permission Model

Teammates start with the lead's permission settings. If the lead runs `--dangerously-skip-permissions`, all teammates inherit that setting. Per-teammate modes can be changed after spawning but not at spawn time. This is a **flat inheritance model with no per-task scoping**.

Subagent definitions (`.claude/agents/*.md` files) can be referenced when spawning teammates to constrain tool access via the `tools` frontmatter field. However, `skills` and `mcpServers` from subagent definitions are NOT applied to teammates—those load from project and user settings.

#### Context Passing

Teammates load the same project context as a regular session (CLAUDE.md, MCP servers, skills) but do NOT inherit the lead's conversation history. The spawn prompt is the sole mechanism for passing task context at initialization. The shared filesystem is the primary coordination layer—agents write files that other agents read.

#### Hooks for Quality Gates

Three hook points specific to agent teams:
- `TeammateIdle`: can veto idle state (exit code 2 = keep working with feedback)
- `TaskCreated`: can veto task creation
- `TaskCompleted`: can veto task completion

These are the COS-native governance controls—operator-defined quality gates enforced at task boundaries.

#### Documented Limitations (as of May 2026)

- No session resumption with in-process teammates
- Task status can lag (a done task might not be marked complete)
- No nested teams (teammates cannot spawn their own teams)
- Lead is fixed for team lifetime (no leadership transfer)
- One team per session

---

### 2.8 ElevenLabs Agent Transfer

**Documentation:** elevenlabs.io/docs/eleven-agents/customization/tools/system-tools/agent-transfer  
**Status:** Production, enterprise feature.

#### Transfer Mechanism

ElevenLabs implements a voice-first handoff optimized for real-time audio pipelines. Transfer conditions are expressed in natural language (e.g., "User asks about billing details"). The parent agent's LLM evaluates these conditions and invokes a `transfer_to_agent` tool call.

Configuration parameters overwritten on the child agent:
- Client events (which audio events to accept)
- TTS output format (pcm_16000, ulaw_8000, etc.)
- ASR input format

Everything else resets to the child's own definition (prompt, voice, knowledge base, tools). This is a **capability reset with history preservation**—the child gets the full conversation transcript but operates within its own context.

#### History Handling

The full transcript persists across the entire conversation. However, `transfer_to_agent` tool calls are stripped from the LLM-visible history so the child agent does not reference the mechanism. Post-call evaluators receive the unfiltered transcript with transfer tool calls as boundary markers.

#### Key Architectural Note

ElevenLabs' model is **stateless configuration plus stateful transcript**. The receiving agent's behavior is entirely determined by its own definition—there is no capability injection from the caller. This prevents privilege escalation (the child cannot use tools the parent has) but also means capability customization requires pre-defining agents.

---

### 2.9 Microsoft Copilot Studio / Microsoft Agent Framework

**Documentation:** microsoft.com/en-us/microsoft-copilot/blog/copilot-studio; devblogs.microsoft.com/agent-framework  
**Status:** Microsoft Agent Framework v1.0 (October 2025) merges AutoGen + Semantic Kernel.

#### Copilot Studio Multi-Agent

Copilot Studio uses A2A protocol for cross-runtime agent collaboration. Agents built with Microsoft 365 agent builder, Azure AI Agents Service, and Microsoft Fabric can coordinate via A2A. Full conversation context is carried over during handoffs. Maker controls require explicit consent before agents are shared.

The orchestration patterns supported:
- **Sequential**: chain agents in fixed order
- **Concurrent**: run agents in parallel, merge results
- **Handoff**: transfer and release (like Swarm)
- **Group Chat**: collaborative discussion (like AutoGen GroupChat)
- **Magentic-One**: complex task decomposition with a generalist orchestrator

All patterns support streaming, checkpointing, human-in-the-loop approvals, and pause/resume.

#### Trust Between Agents

Copilot Studio requires explicit agent registration and consent gates before sharing. The A2A Agent Card authentication model applies. No automatic trust inheritance—each agent relationship is explicitly configured by the maker.

---

### 2.10 Slack Agent Platform

**Documentation:** slack.com/blog/news/powering-agentic-collaboration; slack.dev  
**Status:** Slack Agent Platform GA 2025; Slackbot MCP client in preview.

#### Handoff Architecture

Slack's model uses **Slackbot as the routing front door**. Slackbot can hand off to specialized agents when conditions match. The Embedded AI Handoff feature enables seamless transfers between Slackbot and third-party agents (including Salesforce Agentforce, custom agents via MCP) without disrupting the conversation thread.

Block Kit serves as the inter-agent UI scaffolding: agents use cards, carousels, and work objects to exchange structured data visible to the user.

The Slackbot MCP client bridges external agents directly into Slack channels—any MCP-compliant agent can be registered and invoked from a conversation.

#### Context Passing

Slack conversations are the shared state. All messages are in the thread, visible to all participants including agents. There is no proprietary context envelope—the thread history IS the context. This means context grows unboundedly with conversation length; there is no automatic compaction.

---

## 3. Cross-Cutting Analysis

### 3.1 Protocol Shape Taxonomy

Six recurring shapes across all systems surveyed:

| Shape | Topology | Control Return | Representative System |
|-------|----------|---------------|----------------------|
| **Hub-Spoke** | Orchestrator ↔ Workers | Always returns to hub | AutoGen SelectorGroupChat, CrewAI Hierarchical |
| **Chain/Sequential** | A → B → C (no return) | One-way, terminal hands off | OpenAI Swarm, CrewAI Sequential |
| **Peer Swarm** | Any → Any | One-way or termination | LangGraph Swarm, AutoGen Swarm |
| **Hierarchical Graph** | Tree with selective inheritance | Returns to parent or terminates | Google ADK, LangGraph Supervisor |
| **Protocol Interop** | Cross-vendor over HTTP | Async, callback-based | Google A2A, MCP |
| **Broadcast** | One → All | Not applicable | AutoGen BroadcastChannelTopic |

### 3.2 Context Passing: The Unsolved Problem

Every system makes the same fundamental tradeoff:

- **Full history** (Swarm default, AutoGen GroupChat, Slack): Safe but expensive. Fails when history exceeds context window. Token cost scales linearly with conversation depth.
- **Filtered history** (OpenAI Agents SDK `input_filter`): Requires application-defined filter logic. Common presets: `remove_all_tools` (strips tool call artifacts), keep-last-N.
- **Collapsed history** (OpenAI `nest_handoff_history`): Collapses prior transcript into a single `<CONVERSATION HISTORY>` block. Reduces tokens 70-90% but introduces lossy summarization.
- **References only** (Google A2A `referenceTaskIds`): Passes task IDs, not content. Receiving agent fetches prior work on demand. Most token-efficient; requires additional round-trips.
- **Structured state** (Google ADK `include_contents` parameter, external Artifacts): Passes task outputs as typed artifacts to storage; agents receive lightweight references. Best for large payloads.

The emerging production pattern (2025) is **progressive compression**: recent turns verbatim, older turns hierarchically summarized, very old turns as external artifacts with references. No production framework ships this out of the box.

### 3.3 Trust and Permission Models

Four distinct trust models:

1. **Flat inheritance** (OpenAI Swarm, Anthropic Agent Teams): Delegated agent inherits caller's permissions. Simple but permits privilege creep. If the lead has dangerous permissions, all teammates do too.
2. **Definition-bounded** (ElevenLabs, Anthropic subagent definitions): The receiving agent's capability set is fixed at definition time, not determined by caller. No privilege escalation possible but no capability injection either.
3. **Explicit scoping** (OAuth 2.1 / OBO / delegated tokens): Caller generates an attenuated token for the delegated agent. Most secure, highest complexity. Production OAuth2 patterns from Stytch/WorkOS research.
4. **Protocol-level auth** (Google A2A): Each agent relationship is independently authenticated. No inherited trust. Trust is established per-pair, not per-chain.

The security research literature (2025) strongly recommends against flat inheritance for production systems—it violates the principle of least privilege and makes the blast radius of a compromised sub-agent equal to the blast radius of the orchestrator.

### 3.4 Handoff vs. Delegation

A critical distinction that most frameworks conflate:

- **Handoff**: Control transfers and does NOT return. The originating agent is done. (OpenAI Swarm, LangGraph Swarm, ElevenLabs)
- **Delegation**: Control transfers temporarily; the originating agent waits for result and resumes. (CrewAI `delegate_work`, AutoGen SelectorGroupChat, Google ADK agents-as-tools)

Most systems support both patterns but use different names. Mixing them in a single system is the primary source of deadlocks—an agent that expects a result back from a handoff (not delegation) will wait forever.

### 3.5 Deadlock and Infinite Loop

No production framework ships a built-in circular handoff detector as of May 2026. The research literature (MAST paper, 2025) identifies infinite handoff loops as the #1 production failure mode.

Observed mitigations (applied by practitioners, not shipped by frameworks):
- `max_turns` / `max_iterations` hard cap
- Custom selector functions that encode the valid handoff graph as an allowlist
- Call stack depth tracking (application layer)
- Handoff history stored as a set; block re-entry of a node already in the current call chain
- Timeout-based termination (not ideal—masks bugs)

### 3.6 Termination: Who Decides Done?

| Pattern | Termination Owner | Mechanism |
|---------|------------------|-----------|
| Hub-Spoke | Orchestrator | Explicit `TERMINATE` signal or task completion check |
| Chain | Last agent in chain | No output from last agent = done |
| Swarm | Any agent, or budget cap | `TextMentionTermination`, `MaxMessageTermination` |
| A2A | Task state machine | `COMPLETED` / `FAILED` / `CANCELED` states |
| Agent Teams | Team lead + hooks | `TeammateIdle` notification, lead synthesizes |

The safest pattern for production is **dual termination**: the task itself has a state machine with explicit terminal states (like A2A), AND the orchestrator has a budget cap as a backstop.

---

## 4. Comparative Table

| System | Shape | Context Passing | Permission Model | Deadlock Guard | Termination Owner | Open Protocol |
|--------|-------|----------------|-----------------|----------------|-------------------|---------------|
| OpenAI Swarm (deprecated) | Chain | Full history | Flat inherit | max_turns only | Last agent | No |
| OpenAI Agents SDK | Chain / Hub | Filtered/collapsed | Definition-bounded | max_turns | Last agent | No |
| AutoGen SelectorGroupChat | Hub-Spoke | Full shared | N/A (same process) | Custom selector | Any + budget | No |
| AutoGen Swarm | Peer | Full shared | N/A | None built-in | HandoffMessage or budget | No |
| CrewAI Hierarchical | Hub-Spoke | String context param | allow_delegation flag | None built-in | Manager LLM | No |
| LangGraph Supervisor | Hub-Spoke | State reducers | None (tool-level) | max_iterations | Supervisor | No |
| LangGraph Swarm | Peer | Full or custom | None built-in | None built-in | Any agent | No |
| Google A2A | Protocol Interop | Task references + parts | Per-pair auth | None in spec | Task state machine | Yes (Apache 2.0) |
| Google ADK | Hierarchical Graph | include_contents + Artifacts | Not specified | Not specified | Orchestrator | No |
| Anthropic Agent Teams | Hub-Spoke + Peer | Spawn prompt + filesystem | Flat inherit | None built-in | Team Lead + hooks | No |
| ElevenLabs Agent Transfer | Chain | Full transcript, strip tool calls | Definition-bounded | None | Last agent / human | No |
| MS Copilot Studio | Hub-Spoke + A2A | Full context | Consent gates | Not documented | Orchestrator | Via A2A |
| Slack | Broadcast / Hub | Thread history | Explicit registration | None | Not specified | Via MCP/A2A |

---

## 5. Verdict for COS: Handoff Protocol Proposal

### 5.1 COS Governance Posture

COS operates with three non-negotiable constraints:
- **Operator-in-loop**: human approval gates for high-blast-radius actions
- **Local-first**: no cloud routing layer; agents run in local worktrees or local processes
- **Manifest-driven**: capabilities declared in frontmatter/settings.json, not inferred at runtime

This rules out:
- Pure swarm (no global visibility, undeclared routing)
- A2A over HTTPS (requires network, external auth infrastructure)
- AutoGen BroadcastChannelTopic (no per-agent scoping)

The best-fit starting point is **LangGraph's Command pattern** (explicit routing + state update) adapted for local-first operation, combined with **Anthropic Agent Teams' hook system** for operator gates.

### 5.2 Proposed COS HandoffEnvelope

A single data structure for all COS agent handoffs:

```python
@dataclass
class HandoffEnvelope:
    # Routing
    from_agent: str           # Sender agent ID
    to_agent: str             # Destination agent ID  
    handoff_id: str           # UUID for this handoff event
    
    # Context
    task_id: str              # Task being transferred
    context_mode: Literal["full", "summary", "reference", "none"]
    context_summary: str | None     # If mode == "summary"
    context_reference: str | None   # If mode == "reference", engram key
    
    # Permission scope (attenuated from caller)
    granted_tools: list[str] | None  # None = inherit; list = restrict
    max_blast_radius: int            # 0-100 scale; >threshold requires operator gate
    
    # Governance
    depth: int                # Current call stack depth
    max_depth: int            # Hard cap (default: 5)
    call_chain: list[str]     # All agents visited in this call chain (deadlock detection)
    requires_approval: bool   # Set to True if blast_radius > threshold
    approval_token: str | None  # Set by operator gate if approved
    
    # Result contract
    return_control: bool      # True = delegation (result returns); False = handoff (transfer)
    expected_output_schema: dict | None  # JSON schema for output validation
```

### 5.3 Concrete Protocol Rules

**Rule 1: Manifest-declared graph.** All valid handoff edges must be declared in the agent's frontmatter:
```yaml
# .claude/agents/researcher.md
---
name: researcher
handoffs_allowed:
  - writer
  - reviewer
handoffs_blocked:
  - self  # explicit no-op guard
max_depth: 3
---
```

**Rule 2: Depth limit enforced at runtime.** Before executing any handoff, the COS harness checks `envelope.depth < envelope.max_depth`. Violation raises `HandoffDepthExceeded` and terminates the call chain cleanly.

**Rule 3: Call chain deduplication.** Before executing any handoff, check `envelope.to_agent not in envelope.call_chain`. Violation raises `HandoffCycleDetected`. This is O(depth) and adds negligible overhead.

**Rule 4: Blast radius gating.** If the receiving agent's declared `blast_radius` exceeds the operator-configured threshold (default: 40), set `requires_approval=True` and pause until the operator provides an approval token via the `TeammateIdle` hook or the interactive UI.

**Rule 5: Tool scoping on delegation.** When `return_control=True` (delegation), the receiving agent's tool set is the intersection of `granted_tools` and its own `tools` definition. The caller cannot grant tools the receiving agent does not already have—preventing privilege escalation in both directions.

**Rule 6: Context mode per edge.** Each declared handoff edge can specify a default `context_mode`. High-context edges use `"full"` for correctness; latency-sensitive edges use `"summary"` or `"reference"`. Default: `"summary"`.

**Rule 7: Dual termination.** Every handoff graph has a `max_total_turns` budget set at team creation. Individual agents also have `max_turns`. The `TeammateIdle` hook fires when a teammate completes; the team lead synthesizes and declares the team done. This provides both bottom-up (agent) and top-down (lead) termination signals.

**Rule 8: Append-only audit trail.** Every `HandoffEnvelope` is written to `~/.claude/teams/{team-name}/handoff-log.jsonl` before dispatch. This provides full replay capability for debugging infinite loops.

### 5.4 Implementation Path

Phase 1 (immediate, low risk): Add `call_chain` tracking and depth limit check to COS orchestrator. No changes to agent definitions. Catches the #1 production failure mode.

Phase 2 (near term): Introduce `HandoffEnvelope` as the structured handoff context carrier. Implement `context_mode` selection per edge. Replace ad-hoc context string passing with typed envelopes.

Phase 3 (governance maturity): Add blast radius gating and `requires_approval` flow through existing `TeammateIdle` / `TaskCompleted` hooks. Introduce manifest-declared handoff graphs in agent frontmatter.

Phase 4 (optional): Consider A2A compatibility layer if COS needs to interoperate with third-party agents. A2A's task state machine maps cleanly onto COS's task lifecycle.

---

## 6. Sources

1. OpenAI Swarm GitHub repository — https://github.com/openai/swarm
2. OpenAI Agents SDK: Handoffs documentation — https://openai.github.io/openai-agents-python/handoffs/
3. OpenAI Cookbook: Orchestrating Agents — https://developers.openai.com/cookbook/examples/orchestrating_agents
4. AutoGen: Selector Group Chat documentation — https://microsoft.github.io/autogen/stable//user-guide/agentchat-user-guide/selector-group-chat.html
5. AutoGen: Group Chat design pattern — https://microsoft.github.io/autogen/stable//user-guide/core-user-guide/design-patterns/group-chat.html
6. CrewAI: Hierarchical Process — https://docs.crewai.com/en/learn/hierarchical-process
7. CrewAI: allowed_agents PR #2068 — https://github.com/crewAIInc/crewAI/pull/2068
8. LangGraph Command blog post — https://www.langchain.com/blog/command-a-new-tool-for-multi-agent-architectures-in-langgraph
9. LangGraph Swarm repository — https://github.com/langchain-ai/langgraph-swarm-py
10. LangGraph Supervisor repository — https://github.com/langchain-ai/langgraph-supervisor-py
11. Google A2A announcement — https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/
12. Google A2A protocol specification — https://a2a-protocol.org/latest/specification/
13. Auth0: MCP vs A2A — https://auth0.com/blog/mcp-vs-a2a/
14. Google ADK: Multi-agent systems documentation — https://google.github.io/adk-docs/agents/multi-agents/
15. Google Developers Blog: Context-aware multi-agent framework — https://developers.googleblog.com/architecting-efficient-context-aware-multi-agent-framework-for-production/
16. Anthropic Claude Code: Agent Teams documentation — https://code.claude.com/docs/en/agent-teams
17. ElevenLabs: Agent Transfer documentation — https://elevenlabs.io/docs/eleven-agents/customization/tools/system-tools/agent-transfer
18. Microsoft Copilot Studio: Multi-agent orchestration (Build 2025) — https://www.microsoft.com/en-us/microsoft-copilot/blog/copilot-studio/multi-agent-orchestration-maker-controls-and-more-microsoft-copilot-studio-announcements-at-microsoft-build-2025/
19. Microsoft Agent Framework v1.0 announcement — https://devblogs.microsoft.com/agent-framework/microsoft-agent-framework-version-1-0/
20. Slack: Powering agentic collaboration — https://slack.com/blog/news/powering-agentic-collaboration
21. Augment Code: Multi-Agent AI Systems Architecture and Failure Modes — https://www.augmentcode.com/guides/multi-agent-ai-systems
22. MAST paper: Why Do Multi-Agent LLM Systems Fail? — https://arxiv.org/pdf/2503.13657
23. Xtrace: AI Agent Handoff context loss — https://xtrace.ai/blog/ai-agent-handoff-why-context-gets-lost-between-agents-and-how-to-fix-it
24. OSO: Setting Permissions for AI Agents — https://www.osohq.com/learn/ai-agent-permissions-delegated-access
25. Galileo: 7 AI Agent Failure Modes — https://galileo.ai/blog/agent-failure-modes-guide
26. TechAhead: Multi-Agent Reality Check failure modes in production — https://www.techaheadcorp.com/blog/ways-multi-agent-ai-fails-in-production/
