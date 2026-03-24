# Cognitive OS — Tool Stack Research

> Exhaustive research of open-source tools for each of the 10 Cognitive OS infrastructure components.
> All tools evaluated against [Cognitive OS license policy](../research/license-analysis.md) — AGPL/SSPL/ELv2/BSL are blocked.

---

## 1. Control Plane

The orchestration layer that manages agent lifecycle, policy enforcement, and coordination.

| Tool | Stars | License | Self-Host | Maturity | Description |
|------|-------|---------|-----------|----------|-------------|
| **Galileo Agent Control** | — | Apache 2.0 | Yes | Early | Centralized policy enforcement for agent fleets. Guardrails + monitoring in one layer. |
| **NVIDIA OpenShell** | — | Apache 2.0 | Yes | Early | Secure agent runtime with K3s sandbox + policy engine. Designed for untrusted agent execution. |
| **AgentField** | — | Apache 2.0 | Yes | Early | Agents-as-microservices architecture with W3C DID-based identity. Each agent is a discoverable service. |
| **kagent** | — | Apache 2.0 | Yes (K8s) | Early (CNCF Sandbox) | Kubernetes-native agent management via CRDs. Declarative agent definitions, model configs, tool bindings. |
| **Microsoft Agent Framework** | 27k | MIT | Yes | Mature | Unified framework merging Semantic Kernel + AutoGen. Multi-language (C#, Python, Java). |

### Notes
- kagent entered CNCF Sandbox, signaling strong community backing and K8s ecosystem alignment.
- AgentField's DID approach is forward-looking for agent identity but less battle-tested.
- Microsoft Agent Framework has the largest community but is more of a dev framework than infrastructure control plane.

---

## 2. Scheduler

Durable task execution, retry logic, DAG orchestration, and workflow management.

| Tool | Stars | License | Self-Host | Maturity | Description |
|------|-------|---------|-----------|----------|-------------|
| **Temporal** | 19k | MIT | Yes | Production | Durable execution engine. Auto-handles failures, retries, timeouts. Used by Stripe, Netflix, Snap. |
| **Hatchet** | 6.6k | MIT | Yes | Growing | PostgreSQL-based DAG orchestration. No extra infra needed beyond Postgres. |
| **Celery** | 25k | BSD-3 | Yes | Battle-tested | Python distributed task queue. Massive ecosystem, 15+ years of production use. |
| **KAI Scheduler (NVIDIA)** | — | Apache 2.0 | Yes (K8s) | Early | GPU-aware K8s scheduler. Fair-share, bin-packing, topology-aware for AI workloads. |

### Blocked
| Tool | Stars | License | Why Blocked |
|------|-------|---------|-------------|
| **Windmill** | — | AGPL | Copyleft — must open-source all code if used as SaaS |
| **Inngest** | — | SSPL | Server Side Public License blocks SaaS deployment |

### Notes
- Temporal is the gold standard for durable workflows. MIT license, massive adoption.
- Hatchet is compelling for simpler setups — Postgres-only dependency is attractive.
- Celery is Python-only, which limits use in our polyglot stack but remains viable for Python agents.

---

## 3. Runtime Sandbox

Isolated execution environments for untrusted agent code and tool invocations.

| Tool | Stars | License | Self-Host | Maturity | Description |
|------|-------|---------|-----------|----------|-------------|
| **E2B** | 11.4k | Apache 2.0 | Yes | Production | Firecracker microVM sandboxes. <200ms cold start. Purpose-built for AI agents. |
| **OpenSandbox (Alibaba)** | 8.3k | Apache 2.0 | Yes | Growing | Multi-language sandboxes with Docker + K8s deployment. Originally from Alibaba Cloud. |
| **microsandbox** | 3.3k | Apache 2.0 | Yes | Early | libkrun-based MicroVMs with native MCP integration. Lightweight alternative to E2B. |
| **Agent Sandbox (K8s SIG)** | — | Apache 2.0 | Yes (K8s) | Early | CRD-based sandboxes for K8s. Part of K8s SIG ecosystem. |
| **NVIDIA OpenShell** | — | Apache 2.0 | Yes | Early | K3s-based secure runtime. Overlaps with Control Plane but provides sandbox capabilities. |

### Blocked
| Tool | Stars | License | Why Blocked |
|------|-------|---------|-------------|
| **Daytona** | 65k | AGPL | Best sandbox UX in the market but AGPL copyleft makes it unusable for SaaS |

### Notes
- E2B is the clear leader: best docs, largest community, self-hostable, Firecracker-based security.
- Daytona at 65k stars has the best developer experience but AGPL is a hard blocker.
- microsandbox's MCP integration is interesting for our existing MCP-based tool system.

---

## 4. Multi-Agent Orchestration

Frameworks for coordinating multiple agents working on shared or related tasks.

| Tool | Stars | License | Self-Host | Maturity | Description |
|------|-------|---------|-----------|----------|-------------|
| **LangGraph** | 15k | MIT | Yes | Production | Graph-based stateful agent orchestration. Checkpointing, branching, human-in-the-loop. |
| **CrewAI** | 44k | MIT | Yes | Production | Role-based agent teams. Simple API for defining agent roles, goals, and delegation. |
| **AutoGen** | 55k | MIT | Yes | Production | Microsoft Research. Multi-agent conversations, code execution, tool use. |
| **Google ADK** | 18k | Apache 2.0 | Yes | Growing | Agent Development Kit. Multi-language (Python, Java), built-in tool support. |
| **A2A Protocol** | — | Apache 2.0 | N/A (Protocol) | Early (Linux Foundation) | Agent-to-Agent communication standard. Agent Cards for discovery. 100+ companies backing. |

### Notes
- A2A Protocol is an interoperability standard, not a framework — it complements any orchestration choice.
- LangGraph provides the most control with graph-based flows and state persistence.
- CrewAI has the largest community but is more opinionated (role-based paradigm).
- AutoGen has the most stars but the API has been evolving rapidly.

---

## 5. Agent Identity

Cryptographic identity, authentication, and discovery for autonomous agents.

| Tool | Stars | License | Self-Host | Maturity | Description |
|------|-------|---------|-----------|----------|-------------|
| **AIM (OpenA2A)** | — | Apache 2.0 | Yes | Early | Ed25519 crypto keys + W3C DID-based identity for agents. Most complete agent identity solution. |
| **AgentFacts** | — | MIT | Yes | Early | Verifiable agent identity claims. Lightweight approach to agent credentials. |
| **OpenAgents** | — | Open Source | Yes | Early | DID-based agent networks. Peer-to-peer agent discovery and communication. |
| **A2A Protocol Agent Cards** | — | Apache 2.0 | N/A | Early | Agent Cards provide discovery metadata (capabilities, endpoints, auth requirements). |

### Notes
- Agent identity is the least mature component across the entire stack.
- AIM from OpenA2A is the most complete solution with crypto + DIDs + verification.
- A2A Agent Cards provide discovery but not full cryptographic identity.
- This space will evolve significantly as multi-agent systems mature.

---

## 6. Memory

Persistent memory, context management, and knowledge retrieval for agents across sessions.

| Tool | Stars | License | Self-Host | Maturity | Description |
|------|-------|---------|-----------|----------|-------------|
| **Engram** | — | Apache 2.0 | Yes | Production | **ALREADY IN USE.** Session-aware persistent memory with FTS5 search. MCP-compatible. |
| **Mem0** | 48k | Apache 2.0 | Yes | Production | Universal memory layer. Graph-based relationships, multi-user, multi-agent support. |
| **Letta (MemGPT)** | 15k | Apache 2.0 | Yes | Production | Self-editing memory with tiered storage (core/archival/recall). Auto-manages context window. |
| **MemOS** | 7.4k | Check | Yes | Growing | Memory Operating System concept. Unified memory management across agents. |
| **Hindsight** | — | MIT | Yes | Early | MCP-compatible knowledge graph. Automatic relationship extraction from conversations. |

### Notes
- Engram is already integrated and working well for our dev-time workflow.
- Mem0 could complement Engram for production multi-agent scenarios (graph relationships, user memory).
- Letta's self-editing memory is compelling for long-running agents that need to manage their own context.
- MemOS license needs verification before consideration.

---

## 7. Tool System

Protocols and gateways for agents to discover, authenticate with, and invoke external tools and APIs.

| Tool | Stars | License | Self-Host | Maturity | Description |
|------|-------|---------|-----------|----------|-------------|
| **MCP Protocol** | — | Apache 2.0 | Yes | Production | **ALREADY IN USE.** Model Context Protocol. 1200+ tool servers. Industry standard. |
| **Context7** | — | — | No (SaaS) | Production | **ALREADY IN USE.** Documentation-as-context for LLMs. Library-aware code examples. |
| **Portkey Gateway** | 10k | MIT | Yes | Production | Unified API gateway to 1600+ LLM models. Routing, fallbacks, caching, load balancing. |
| **LiteLLM** | 40k | MIT | Yes | Production | OpenAI-compatible proxy for 100+ LLM providers. Budget management, key rotation. |

### Notes
- MCP is the clear industry standard for tool integration. Already deeply embedded in our workflow.
- Portkey and LiteLLM overlap in LLM gateway functionality but differ in focus: Portkey is more routing-oriented, LiteLLM more budget-oriented.
- Context7 fills a unique niche (docs-as-context) that no other tool covers.

---

## 8. Observability

Tracing, logging, cost tracking, and debugging for LLM-powered agent systems.

| Tool | Stars | License | Self-Host | Maturity | Description |
|------|-------|---------|-----------|----------|-------------|
| **Langfuse** | 23k | MIT | Yes | Production | Full LLM engineering platform. Traces, prompts, evals, cost tracking. Self-hostable. |
| **OpenLIT** | 2.3k | Apache 2.0 | Yes | Growing | OpenTelemetry-native LLM observability. Integrates with existing OTEL infrastructure. |
| **Helicone** | 5k | Apache 2.0 | Yes | Production | LLM proxy with SOC2/GDPR compliance. Request logging, cost tracking, rate limiting. |
| **AgentOps** | 5.3k | MIT | Yes | Growing | Agent-specific observability. Session replays, event graphs, compliance monitoring. |
| **OpenLLMetry** | 5k | Apache 2.0 | Yes | Growing | OpenTelemetry extensions for LLMs. Spans for completions, embeddings, retrievals. |
| **Plano** | — | Apache 2.0 | Yes | Early | AI-native proxy. Transparent observability layer between agents and LLM providers. |

### Blocked
| Tool | Stars | License | Why Blocked |
|------|-------|---------|-------------|
| **Arize Phoenix** | — | ELv2 | Elastic License v2 — cannot offer as managed service |

### Notes
- Langfuse is the most complete self-hosted option with the largest community.
- OpenLIT is attractive if we already have OTEL infrastructure (Grafana, Jaeger).
- AgentOps provides unique agent-specific features (session replays) not found in general LLM observability tools.
- Arize Phoenix is technically excellent but ELv2 blocks SaaS use.

---

## 9. Cost Control

Budget enforcement, usage tracking, model routing for cost optimization, and per-agent attribution.

| Tool | Stars | License | Self-Host | Maturity | Description |
|------|-------|---------|-----------|----------|-------------|
| **LiteLLM** | 40k | MIT | Yes | Production | Per-key/user/team budget caps. Virtual keys, rate limiting, spend tracking. |
| **Bifrost** | — | Apache 2.0 | Yes | Growing | 4-tier budget system (global/org/team/agent). 11 microsecond overhead. Written in Go. |
| **Portkey Gateway** | 10k | MIT | Yes | Production | Cost tracking + intelligent routing. Automatic fallbacks to cheaper models. |
| **Langfuse** | 23k | MIT | Yes | Production | Token and cost tracking per trace/session. Dashboards for spend analysis. |
| **AgentOps** | 5.3k | MIT | Yes | Growing | Per-session cost attribution. Links cost to specific agent actions and outcomes. |

### Notes
- LiteLLM is the most feature-complete for budget enforcement (hard caps, alerts, virtual keys).
- Bifrost's 11us overhead and Go implementation make it ideal for high-throughput scenarios.
- Combining LiteLLM (budget caps) + Langfuse (cost visibility) covers enforcement + analytics.
- Portkey overlaps with LiteLLM but adds intelligent routing (cost-aware model selection).

---

## 10. Security

Input/output scanning, prompt injection defense, policy enforcement, and safety guardrails.

| Tool | Stars | License | Self-Host | Maturity | Description |
|------|-------|---------|-----------|----------|-------------|
| **NeMo Guardrails (NVIDIA)** | 4k | Apache 2.0 | Yes | Production | Colang policy language for defining conversational guardrails. Topical, safety, and security rails. |
| **LLM Guard** | 2.5k | MIT | Yes | Production | 15 input scanners + 20 output scanners. PII detection, prompt injection, toxicity, bias. |
| **Guardrails AI** | 4k | Apache 2.0 | Yes | Production | Validation framework with 50+ validators. Structured output enforcement. |
| **Invariant Guardrails** | — | Apache 2.0 | Yes | Growing | MCP-aware security. Snyk-backed. Policies that understand tool invocations. |
| **LlamaFirewall (Meta)** | 3k | MIT | Yes | Growing | PromptGuard 2 model for injection detection. CodeShield for code scanning. Agent alignment checks. |

### Notes
- NeMo Guardrails and LLM Guard are complementary: NeMo for conversational policy, LLM Guard for content scanning.
- Invariant Guardrails is unique in being MCP-aware — it can enforce policies on tool invocations, not just text.
- LlamaFirewall brings Meta's PromptGuard 2 model which is specifically trained for injection detection.
- Guardrails AI focuses more on structured output validation than security per se.
- A layered approach (NeMo + LLM Guard + Invariant) provides defense-in-depth.
