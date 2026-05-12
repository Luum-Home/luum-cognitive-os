# Cross-Session Agent Teams: Protocol Catalog and COS Contract Recommendation

**Date**: 2026-05-06  
**Author**: Research session — Cognitive OS  
**Status**: Complete first pass  
**Word count**: ~3 200  
**Related**: `orchestration-coverage-gap-analysis-2026-05-06.md`, ADR-211 (service-mode readiness gate)  
**Scope**: Cross-session multi-agent coordination — protocol catalog, comparative analysis, and recommendation for COS's first cross-session contract.

---

## 1. Motivation and Scope

Cognitive OS distinguishes two classes of parallelism:

- **Subagents** — agents that live inside a single Claude Code session, spawned via the `Agent` tool and reporting back to the parent context window. These are well-understood and partially covered by ADR-203.
- **Agent teams** — N independent sessions (N ≥ 2) whose processes are coordinated across process boundaries without sharing a context window. No clean contract exists in COS for this class.

The `orchestration-coverage-gap-analysis-2026-05-06.md` document rated this gap as "partial coverage / not catastrophic but real." ADR-211 (service-mode readiness gate) addresses when COS can claim headless operation, but it does not specify *how* sessions should talk to each other. This document fills that gap by cataloging every credible cross-session coordination pattern in use across the 2026 ecosystem, then recommending the first COS contract.

---

## 2. Taxonomy of Coordination Protocols

### 2.1 Tier 1 — In-Process (Single Session Boundary)

These mechanisms keep all agents inside one process. They are the baseline and the easiest to reason about.

**Subagent-as-tool (Anthropic SDK / Claude Code)**  
The SDK's native pattern: an orchestrator spawns subagents as tool invocations. Each subagent runs in its own isolated context window and returns a summary result to the parent. Communication is strictly parent→child→parent (no peer-to-peer). The orchestrator is the sole information hub. This is COS's current model for multi-agent work. Its limit is that the orchestrator's context window becomes a bottleneck when subagents need to share intermediate findings [source: Anthropic multi-agent coordination patterns blog].

**Parallel tool calls (SDK-native)**  
The Anthropic SDK supports parallel tool invocations within a single turn. This is useful for fan-out/gather patterns (spawn N checks, wait for all) but does not survive a context-window compaction event. It is not a cross-session primitive.

**LangGraph in-process graph**  
LangGraph's `StateGraph` compiles all agents and supervisors into a single Python process. State flows through a typed graph with checkpointer-based persistence. Supervisor routing happens in-process via Python function calls. This is powerful for single-machine sequential workflows but does not distribute across processes by default [source: LangGraph supervisor documentation, AWS Bedrock integration guide].

---

### 2.2 Tier 2 — IPC / File-Based (Same Machine, Separate Processes)

These mechanisms allow separate OS processes to coordinate without a network stack.

**Shared task list with file locking (Claude Code Agent Teams)**  
Claude Code v2.1.32 ships an experimental `agent teams` feature enabled via `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`. The architecture:

- One session is the **team lead**; it creates a `~/.claude/tasks/{team-name}/` directory containing a structured task list (status: `pending` / `in_progress` / `completed` / `blocked`).
- Each **teammate** is a full independent Claude Code session with its own context window. It does not inherit the lead's conversation history.
- Coordination happens through **file locking** (`fcntl`-style) on the task list to prevent race conditions when multiple teammates attempt to claim the same task simultaneously.
- A **mailbox** system delivers messages between sessions. Messages are delivered automatically; the lead does not need to poll.
- Team config is stored at `~/.claude/teams/{team-name}/config.json` and contains `members[]` with session IDs and tmux pane IDs.
- Sessions communicate via **`SendMessage`** (peer-to-peer by name) and idle notifications (a teammate signals the lead when it stops).
- Hooks can gate coordination events: `TeammateIdle`, `TaskCreated`, `TaskCompleted`.
- **Known limitations**: no session resumption for in-process teammates (after `/resume`, the lead may message non-existent sessions); no nested teams; one team per lead session; task status can lag [source: code.claude.com/docs/en/agent-teams].

**OpenCode JSONL inbox + session injection**  
OpenCode implements a two-layer IPC system. Messages are appended to per-agent JSONL files at `team_inbox/<projectId>/<teamName>/<agentName>.jsonl`. Each entry carries: ID, sender, text, timestamp, read flag. When Agent A messages Agent B, the system injects a synthetic user message into B's active session and triggers `autoWake` to restart B's idle prompt loop. Writes are O(1) append-only, avoiding read-modify-write races. State machines are separated: member status (5 coarse states) vs. execution status (10 fine-grained states) — this separation enables responsive UI updates without polluting recovery logic [source: OpenCode inter-session analysis].

**Progress-file pattern (Anthropic harness recipe)**  
Anthropic's long-running agent harness guide separates work into an **Initializer** (runs once, writes `claude-progress.txt`, a `feature_list.json`, an `init.sh`, and a baseline git commit) and a **Coding Agent** (subsequent sessions read `claude-progress.txt` to understand prior state, select the highest-priority incomplete feature, run `init.sh`, and verify before adding new work). Git commits with descriptive messages serve as recoverable checkpoints. This is an implicit coordination protocol: sequential sessions communicate through the filesystem rather than through any live message channel. It is the lowest-complexity cross-session pattern available and the right choice when sessions are strictly sequential [source: Anthropic effective harnesses for long-running agents].

**CrewAI Flows (event-driven state machine)**  
CrewAI Flows implement structured, event-driven workflows that coordinate tasks and Crews. State is managed per-flow run, with `@start`, `@listen`, and `@router` decorators controlling execution order. Flows run 12M+ executions/day in production across finance and government verticals. Cross-process communication is brokered by the Flow runtime rather than raw IPC; individual agents receive task context via the Flow's shared state dict. The system emphasizes sequential or parallel task routing through the orchestration layer, not peer-to-peer agent messaging [source: CrewAI Flows product page, CrewAI documentation].

---

### 2.3 Tier 3 — Network Bus (Cross-Machine, Distributed)

These mechanisms decouple agents from the machine boundary entirely.

**AutoGen Distributed Runtime (gRPC)**  
AutoGen 0.4 (released January 2025) introduces a production-grade distributed runtime. Architecture:

- A **gRPC host** (`GrpcWorkerAgentRuntimeHost`) manages connections from all worker runtimes and routes `CloudEvent`-formatted messages.
- **Worker runtimes** (`GrpcWorkerAgentRuntime`) register their agents with the host, advertise supported agent types, and receive messages through a bidirectional streaming channel.
- Agents are **location-transparent**: they publish to `DefaultTopicId()` and subscribe to topics; the host delivers messages to all subscribers regardless of which worker hosts them.
- Agents remain **unaware of the distributed nature** — they interact with a local `AgentRuntime` interface, and cross-process routing is invisible.
- Each worker runtime manages agent state locally; the host is stateless regarding agent logic.
- Cross-language interop is possible via shared Protobuf schemas (`agentworker.proto`, `cloudevent.proto`) [source: AutoGen distributed runtime documentation, prasanna.dev deep-dive].

**Google A2A (Agent-to-Agent Protocol)**  
Launched April 2025 with 50+ founding partners, now under the Linux Foundation's Agentic AI Foundation (AAIF) alongside MCP. A2A enables peer-to-peer task delegation between agents:

- **Agent Cards**: capability advertisement documents served at `/.well-known/agent.json`; consuming agents discover peer capabilities before delegating.
- **Task objects + Artifacts**: the message envelope is JSON-RPC 2.0; tasks can be dispatched synchronously (HTTPS), polled, or streamed via Server-Sent Events.
- A2A is session-aware: task execution state persists across multiple interactions, unlike MCP's stateless tool calls.
- A2A covers what MCP explicitly leaves out of scope: task delegation, capability discovery, and result streaming between peer agents [source: arxiv 2505.02279, onereach.ai MCP vs A2A guide, getstream.io agent protocols].

**MCP as coordination bus (stdio / Streamable HTTP)**  
MCP's primary purpose is agent↔tool integration (97M monthly SDK downloads by February 2026, adopted by every major AI provider). However, MCP can serve as a lightweight A2A transport:

- `stdio` transport is the default for local MCP servers and handles same-machine IPC without a network stack.
- The November 2025 spec's **Streamable HTTP** transport enables remote MCP servers and bidirectional event streaming.
- An agent can expose itself as an MCP server, making its capabilities available to any other MCP client — including another agent session. This is the emerging "MCP as A2A" pattern.
- MCP does not natively handle capability discovery, task state, or session continuity; these must be layered on top [source: arxiv 2505.02279, DEV.to MCP vs A2A 2026, Camunda blog on MCP/ACP/A2A].

**Redis pub/sub and NATS JetStream**  
For systems that need fire-and-forget fan-out (Redis pub/sub) or durable, exactly-once delivery with replay (NATS JetStream):

- Redis pub/sub delivers messages only to currently-connected subscribers; messages are lost if no one is listening. Suitable for low-latency event notification where durability is not required.
- NATS JetStream adds persistence, consumer groups, replay, and exactly-once semantics on top of NATS's core pub/sub. This is suitable for auditable agent action logs and durable task queues.
- The AI-specific pattern with NATS is: every agent action published to `agent.{agent-id}.actions` creates a replayable history stream. Multiple agent instances with the same queue group share messages (competing consumers), enabling horizontal scaling.
- Redis requires extra work for competing-consumer coordination (list + keyspace notifications + distributed lock); NATS handles this natively through queue groups [source: dev.to pub/sub patterns, sparkco.ai Redis+NATS for AI event streaming].

---

## 3. Comparative Table

| Protocol | Transport | State model | Peer-to-peer | Cross-machine | Durability | Complexity |
|---|---|---|---|---|---|---|
| SDK subagent-as-tool | In-process call | Parent context | No | No | None | Low |
| CC Agent Teams (file + lock) | Local filesystem | Shared task file | Yes (mailbox) | No | File | Medium |
| OpenCode JSONL inbox | Append-only file | JSONL per agent | Yes | No | File | Medium |
| Progress-file pattern | Filesystem | Flat text/JSON | No (sequential) | No | File | Low |
| LangGraph supervisor | In-process graph | Typed state + checkpoint | Via supervisor | No | Checkpointer | Medium |
| CrewAI Flows | In-process event | Flow state dict | Via router | No (single machine) | Flow persistence | Medium |
| AutoGen gRPC | gRPC+CloudEvents | Local per worker | Yes (via host) | Yes | None (workers) | High |
| A2A (Google) | HTTPS + SSE | Session-aware task | Yes (P2P) | Yes | Task objects | Medium-high |
| MCP (stdio/HTTP) | stdio or HTTP | Stateless + optional | Via MCP server | Yes (HTTP) | None native | Medium |
| Redis pub/sub | TCP | Fire-and-forget | Yes | Yes | None | Low-medium |
| NATS JetStream | TCP | Durable streams | Yes | Yes | Persistent | Medium-high |

---

## 4. What the Anthropic Agent SDK Leaves to You

The SDK ships: agent loop, parallel tool calls, streaming, prompt caching, permission routing, subagent spawning, and MCP integration. It explicitly does **not** ship: cross-session state persistence, multi-process synchronization, structured agent handoffs, observability/tracing APIs, durable execution with checkpoint resumption, or prompt injection defenses outside Claude Code. The estimated engineering cost to build these layers from scratch is 2 200–4 500 engineer-hours [source: augmentcode.com SDK gap analysis].

This gap is the COS opportunity: ADR-203 has defined the subagent capability contract; the missing piece is the cross-session layer above it.

---

## 5. COS Gap in Context

The gap-analysis document scores COS cross-session coordination as "partial." Specifically:

- COS has `session_bus.py` as an event log, but it is not end-to-end event-sourced (partial credit).
- COS has subagents within a session (ADR-203) — covered.
- COS lacks: a clean contract distinguishing subagents (1 session) from agent teams (N sessions); peer-to-peer messaging between sessions; a shared task list with file locking; and idle/completion notification across process boundaries.

ADR-211's service-mode readiness gate explicitly includes "mutation authorization boundary" as a requirement before service-mode claims are valid. A cross-session coordination contract is a prerequisite to that boundary being meaningful.

---

## 6. Protocol Catalog Summary

Three natural tiers emerge from the research:

**Tier 1 — In-process**: subagent-as-tool (Anthropic SDK), LangGraph in-process graph. Zero IPC cost, but the orchestrator context window is the bottleneck. Appropriate when agents produce clear, summarizable outputs and don't need to share intermediate findings.

**Tier 2 — File-based IPC**: CC Agent Teams (task file + `fcntl` lock + mailbox), OpenCode JSONL inbox + session injection, progress-file pattern. Appropriate for same-machine orchestration where simplicity and auditability matter. The CC Agent Teams model is the most feature-complete implementation in this tier: it adds peer-to-peer messaging, dependency-aware task unblocking, and hook integration (`TeammateIdle`, `TaskCreated`, `TaskCompleted`).

**Tier 3 — Network bus**: AutoGen gRPC (location-transparent, language-agnostic), A2A (enterprise peer-to-peer, capability-advertised), MCP Streamable HTTP (de-facto tool bus, can serve as lightweight A2A), Redis/NATS (pub/sub for event fan-out and durable action logs). Appropriate when agents run on separate machines, require exactly-once delivery, or must be discovered dynamically.

---

## 7. Recommendation for COS's First Cross-Session Contract

### 7.1 Proposed contract: File-IPC with Structured Manifest

Given COS's current architecture (local-first, file-backed Engram, Claude Code harness, no cloud infrastructure), the recommendation is to adopt **Tier 2 — file-based IPC with an explicit manifest contract**, modeled on CC Agent Teams but without the tmux dependency.

The contract has four primitives:

**1. Session registry** (`~/.cognitive-os/teams/{team-name}/members.jsonl`)  
Each session appends a single line on join: `{session_id, role, worktree_path, started_at, status}`. No rewrite needed. The lead reads this file to discover teammates. This is append-only (O(1) write), crash-safe, and auditable.

**2. Task manifest** (`~/.cognitive-os/teams/{team-name}/tasks.jsonl`)  
Tasks are JSONL records with: `{id, title, status, depends_on[], claimed_by, completed_at, output_summary}`. Task claims use POSIX advisory file locking (`fcntl.LOCK_EX | fcntl.LOCK_NB`) on a companion `.lock` file. This avoids race conditions when multiple sessions simultaneously attempt to claim the same task — the pattern Claude Code's agent teams use.

**3. Inbox delivery** (`~/.cognitive-os/teams/{team-name}/inbox/{session_id}.jsonl`)  
Messages are appended (O(1) write) to the recipient's inbox file. The sending session writes; the receiving session polls on its own schedule or is triggered by a filesystem watcher. This mirrors OpenCode's JSONL inbox approach and avoids the read-modify-write hazard of JSON arrays.

**4. Idle / completion notification**  
When a session completes its assigned work or goes idle, it appends a `{type: "idle"|"done", session_id, task_id, timestamp}` event to the team's event log (`events.jsonl`). The lead reads this file to detect when to assign new tasks. No active messaging required from the teammate.

### 7.2 What this contract enables

- Teammates can operate independently without polling the lead.
- Tasks have explicit dependency tracking (blocked tasks unblock automatically when prerequisites complete).
- The event log provides a post-mortem replay trail (no re-execution, but full observability — aligns with Engram's read-only memory model).
- Hook integration is natural: `TaskCreated`, `TaskCompleted`, `TeammateDone` hooks can read the manifest and enforce quality gates (DoD checks, trust scores) before marking tasks done.
- The contract is harness-agnostic: any process that can read/write files and acquire advisory locks can participate, including non-Claude-Code agents.

### 7.3 What this contract does NOT provide (intentional scope limits)

- **Cross-machine coordination** — explicitly out of scope for the first iteration; that path goes through A2A or AutoGen gRPC when COS adds cloud infrastructure.
- **Re-execution / replay** — the event log is observational only; replay semantics require a separate checkpoint primitive (tracked as a missing gap in the coverage analysis).
- **Dynamic agent discovery** — sessions must be named at team creation; no runtime capability advertisement. That is an A2A concern.
- **Exactly-once delivery** — JSONL inbox is at-least-once; idempotent task IDs provide de-duplication.

### 7.4 Migration path to Tier 3

When COS adds cloud infrastructure, the file-based contract maps cleanly onto NATS JetStream:

- Session registry → NATS KV store
- Task manifest → NATS JetStream subject with competing consumers
- Inbox delivery → NATS subject per agent (`agent.{session_id}.inbox`)
- Event log → NATS JetStream audit stream with replay

The same data model survives the transport upgrade. No orchestration semantics need to change.

---

## 8. Top 3 Takeaways

1. **The file-based tier is more mature than it looks.** Claude Code Agent Teams and OpenCode have independently converged on the same primitives: append-only JSONL for messages, POSIX file locking for task claims, and a structured task manifest for dependency tracking. This is enough to build a production cross-session contract without introducing a network service.

2. **MCP and A2A are complementary, not competing.** MCP handles agent↔tool connectivity (tool invocation, data access). A2A handles agent↔agent task delegation (capability discovery, task streaming, session-aware state). A production COS service-mode will eventually need both; the first contract does not. The right progression is: file-IPC → MCP-bus (adds network reach) → A2A (adds capability advertisement and enterprise-grade task delegation).

3. **The SDK leaves the cross-session gap deliberately open.** Anthropic ships the agent loop and subagent spawning; everything above that — state persistence, multi-process sync, structured handoffs, durable execution — is explicitly "what you build." This is COS's differentiation surface. A clean cross-session contract is a defensible proprietary layer, not something available off the shelf.

---

## 9. Top 3 Recommendations for COS

1. **Implement the file-IPC manifest contract as a thin library** (`lib/agent_team.py`): `SessionRegistry`, `TaskManifest`, `Inbox`, `EventLog`. Keep it under 400 LOC. Wire `TeammateIdle`, `TaskCreated`, `TaskCompleted` hooks to the existing hook layer. This closes the "partial" rating in the gap analysis and unblocks ADR-211 level 7 (service-mode mutation authorization boundary).

2. **Document the subagent / agent-team distinction in an ADR** (ADR-222 or next available). The distinction is: subagents share the orchestrator's session and report results back; agent teams are independent sessions coordinating through a shared external contract. Without this written contract, every new operator will re-discover the ambiguity. Claude Code's public documentation for this distinction is the reference model.

3. **Adopt NATS JetStream as the declared Tier 3 upgrade path** (not Redis pub/sub). NATS's competing-consumer queue groups handle the agent fan-out / load-balance pattern that Redis pub/sub cannot. The NATS JetStream data model maps directly from the file-IPC contract: the same task manifest semantics survive the transport upgrade. This gives a clear "when we go multi-machine" answer without prematurely adding infrastructure.

---

## 10. Sources

1. Claude Code Agent Teams official documentation — https://code.claude.com/docs/en/agent-teams
2. Anthropic multi-agent coordination patterns — https://claude.com/blog/multi-agent-coordination-patterns
3. Anthropic — building agents with the Claude Agent SDK — https://claude.com/blog/building-agents-with-the-claude-agent-sdk
4. Anthropic — effective harnesses for long-running agents — https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
5. Augment Code — Anthropic Agent SDK: what it ships vs. what you build — https://www.augmentcode.com/guides/anthropic-agent-sdk-what-ships-vs-what-you-build
6. InfoQ — Anthropic introduces Managed Agents — https://www.infoq.com/news/2026/04/anthropic-managed-agents/
7. OpenCode agent teams IPC architecture (dev.to deep-dive) — https://dev.to/uenyioha/porting-claude-codes-agent-teams-to-opencode-4hol
8. MindStudio — Claude Code Agent Teams shared task list — https://www.mindstudio.ai/blog/claude-code-agent-teams-parallel-shared-task-list
9. AutoGen distributed agent runtime official docs — https://microsoft.github.io/autogen/stable//user-guide/core-user-guide/framework/distributed-agent-runtime.html
10. prasanna.dev — AutoGen distributed runtime deep-dive — https://www.prasanna.dev/posts/distributed-runtime-autogen
11. arxiv 2505.02279 — Survey of Agent Interoperability Protocols (MCP, A2A, ACP, ANP) — https://arxiv.org/html/2505.02279v1
12. onereach.ai — MCP vs A2A protocols guide 2026 — https://onereach.ai/blog/guide-choosing-mcp-vs-a2a-protocols/
13. getstream.io — Top AI agent protocols 2026 — https://getstream.io/blog/ai-agent-protocols/
14. Camunda — MCP, ACP, and A2A: the growing world of inter-agent communication — https://camunda.com/blog/2025/05/mcp-acp-a2a-growing-world-inter-agent-communication/
15. dev.to — Pub/sub messaging patterns: Redis vs NATS 2026 — https://dev.to/young_gao/pubsub-messaging-patterns-redis-nats-and-when-to-use-what-2el2
16. sparkco.ai — Redis pub/sub with NATS for AI event streaming — https://sparkco.ai/blog/automate-redis-pubsub-with-nats-for-ai-event-streaming
17. LangGraph supervisor Python library — https://reference.langchain.com/python/langgraph-supervisor
18. CrewAI Flows product page — https://crewai.com/crewai-flows
