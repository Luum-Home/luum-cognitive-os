# Cognitive OS — Tool Stack Research

> Exhaustive research of open-source tools for Cognitive OS infrastructure components (10 core + 4 extended).
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
| **xpander.ai** | 860 | MIT | Yes | Growing | Multi-agent runtime with MCP + A2A protocol. SDKs in Python, Node.js, C#, Java. **TRIAL** (7.20). Reference architecture, avoid platform lock-in. |

### Notes
- A2A Protocol is an interoperability standard, not a framework — it complements any orchestration choice.
- LangGraph provides the most control with graph-based flows and state persistence.
- CrewAI has the largest community but is more opinionated (role-based paradigm).
- AutoGen has the most stars but the API has been evolving rapidly.
- xpander.ai is interesting as a reference for MCP + A2A integration patterns; avoid platform lock-in by treating it as a reference architecture.

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
| **Cognee** | ~7.5k | Apache 2.0 | Yes | Growing | Knowledge graph memory for AI agents. ECL pipeline (Extract, Cognify, Load). MCP server support. **ADOPT** (8.20). Integration: complement engram with structured knowledge graph. |
| **arscontexta** | ~2.2k | MIT | Yes | Early | Claude Code plugin for individualized knowledge systems. Subagent-per-phase. **ASSESS** (6.65). Reference for cognitive architecture patterns. |

### Notes
- Engram is already integrated and working well for our dev-time workflow.
- Cognee scores highest among new additions (8.20 ADOPT) — its knowledge graph ECL pipeline complements engram's session-based memory with structured relationships.
- Mem0 could complement Engram for production multi-agent scenarios (graph relationships, user memory).
- Letta's self-editing memory is compelling for long-running agents that need to manage their own context.
- arscontexta is worth studying for its cognitive architecture patterns (subagent-per-phase), even if not directly integrated.
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
| **Opik** | 18.3k | Apache 2.0 | Yes | Production | LLM observability, tracing, evaluation, monitoring. Scales to 40M+ traces/day. Python SDK + Java backend. MCP server. **ADOPT** (8.95). Integration: trace all agent LLM calls, feed MAPE-K loop. |
| **error-monitoring-agent** | — | MIT | Yes | Early | Semantic error clustering + context enrichment + auto-triage. Pipeline: cluster → enrich → analyze → act. **TRIAL** (6.80). Integration: self-healing observability layer. |

### Blocked
| Tool | Stars | License | Why Blocked |
|------|-------|---------|-------------|
| **Arize Phoenix** | — | ELv2 | Elastic License v2 — cannot offer as managed service |

### Notes
- Langfuse is the most complete self-hosted option with the largest community.
- Opik scores highest (8.95 ADOPT) with proven scale at 40M+ traces/day and MCP server integration — strong candidate for MAPE-K loop tracing.
- OpenLIT is attractive if we already have OTEL infrastructure (Grafana, Jaeger).
- AgentOps provides unique agent-specific features (session replays) not found in general LLM observability tools.
- error-monitoring-agent provides self-healing capabilities through semantic error clustering and auto-triage.
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
| **Plano** | ~5.9k | Apache 2.0 | Yes | Growing | AI-native proxy on Envoy. LLM routing, safety guardrails, PII detection, observability. Rust + WASM. **TRIAL** (7.80). Integration: data plane for LLM routing. |

### Blocked
| Tool | Stars | License | Why Blocked |
|------|-------|---------|-------------|
| **FalkorDB** | — | SSPL | Server Side Public License blocks SaaS deployment. Graph database — **REJECT** (license). |
| **QueryWeaver** | — | AGPL | Copyleft — Text2SQL by FalkorDB. **REJECT** (license). |

### Notes
- NeMo Guardrails and LLM Guard are complementary: NeMo for conversational policy, LLM Guard for content scanning.
- Invariant Guardrails is unique in being MCP-aware — it can enforce policies on tool invocations, not just text.
- LlamaFirewall brings Meta's PromptGuard 2 model which is specifically trained for injection detection.
- Guardrails AI focuses more on structured output validation than security per se.
- A layered approach (NeMo + LLM Guard + Invariant) provides defense-in-depth.
- Plano overlaps with Observability (section 8) but its guardrail and PII detection capabilities place it primarily here.
- Teleport RFD 0238 (gravitational/teleport) is a useful reference design document on delegating access to AI workloads — relevant for agent identity and access control patterns.

---

## 11. Web Crawling

LLM-ready web content extraction for agent skills and pipelines.

| Tool | Stars | License | Self-Host | Maturity | Description |
|------|-------|---------|-----------|----------|-------------|
| **Crawl4AI** | ~30k | Apache 2.0 | Yes | Production | Headless browser crawling that returns clean markdown. CSS/XPath structured extraction, multi-page crawling, JS rendering. **ADOPT**. Integration: `lib/web_crawler.py` wrapper used by skills. |

### Notes
- Crawl4AI converts web pages to LLM-optimised markdown with boilerplate removed.
- The `lib/web_crawler.py` wrapper provides graceful degradation: when Crawl4AI is not installed, single-page fetch falls back to `urllib` with HTML stripping (no JS rendering).
- Structured extraction and multi-page crawling require Crawl4AI (no fallback).
- Replaces any need for Firecrawl or similar commercial crawling services.

---

## 12. Platforms & Infrastructure

Database layers, search extensions, and foundational infrastructure for agent systems.

| Tool | Stars | License | Self-Host | Maturity | Description |
|------|-------|---------|-----------|----------|-------------|
| **pg_textsearch** | ~3.2k | PostgreSQL License | Yes | Early (Pre-v1.0) | BM25 relevance-ranked full-text search for PostgreSQL. Block-Max WAND optimization. **TRIAL** (7.50). Integration: enhance Postgres-based retrieval. |
| **MindsDB** | 30k+ | Elastic License 2.0 | Yes | Production | AI database layer with 200+ integrations. **ASSESS** (5.50). CAUTION: ELv2 restricts offering as a service. |

### Notes
- pg_textsearch is pre-v1.0 but promising for BM25 search within existing Postgres deployments.
- MindsDB has broad integration support but ELv2 license restricts SaaS use — evaluate for internal/self-hosted scenarios only.

---

## 13. Model Training

Fine-tuning and training infrastructure for custom models.

| Tool | Stars | License | Self-Host | Maturity | Description |
|------|-------|---------|-----------|----------|-------------|
| **Unsloth** | 44.6k | Apache 2.0 (core) / AGPL-3.0 (Studio) | Yes | Production | 2x faster LLM fine-tuning, 70% less memory. **ASSESS** (6.15). CAUTION: only use Apache-licensed core, avoid AGPL Studio component. |

### Notes
- Unsloth's Apache-2.0 core is safe for use; the AGPL-3.0 Studio module must be avoided per license policy.
- Relevant only for separate provider-specific model workflows; the COS harness training contract remains operational learning, not provider-weight fine-tuning (see `docs/04-Concepts/architecture/agent-training-harness.md`).

---

## 14. Inference

Inference optimization, context management, and model serving.

| Tool | Stars | License | Self-Host | Maturity | Description |
|------|-------|---------|-----------|----------|-------------|
| **RLM** | 3.2k | MIT | Yes | Research | Recursive Language Models for near-infinite context. Research from MIT OASYS lab. **ASSESS** (5.80). Research-grade, not production-ready. |

### Notes
- RLM is a research prototype exploring recursive context extension. Monitor for maturity but do not depend on it for production workloads.

---

## 15. Reference & Educational

Tutorial collections and reference implementations. Not integrable software.

| Tool | Stars | License | Description |
|------|-------|---------|-------------|
| **ai-engineering-hub** | 31.1k | MIT | Tutorial collection covering AI engineering patterns. **HOLD** — not integrable software, useful as learning resource only. |

### Notes
- ai-engineering-hub is a curated collection of tutorials and examples. Useful for team onboarding and pattern reference, but not a dependency.

---

## 16. Testing & Evaluation

All tools evaluated against Cognitive OS license policy.

### ADOPT

- **DeepEval** (confident-ai/deepeval) — Apache-2.0, 14k stars, Score: 8.08
  Pytest-native LLM unit testing. 60+ metrics (faithfulness, hallucination, tool correctness). ConversationalTestCase for multi-turn agent trajectory testing. Red teaming with 40+ vulnerability categories. Integration: primary framework for skill quality regression, hook decision testing, SDD phase validation.

- **RAGAS** (explodinggradients/ragas) — Apache-2.0, 12.9k stars, Score: 8.30
  RAG quality testing with 40+ metrics. Synthetic test generation from knowledge graphs. MultiTurnSample for agent trajectory evaluation. Integration: memory quality testing (engram + cognee), synthetic scenario generation from 51 skills, ToolCallAccuracy for SDD phases.

### TRIAL

- **Promptfoo** (promptfoo/promptfoo) — MIT, 12.8k stars, Score: 7.80
  YAML-driven prompt regression testing. 50+ red team plugins (prompt injection, jailbreak, PII). CI/CD via GitHub Action. Acquired by OpenAI March 2026, remains MIT. Integration: red teaming gate for skills, prompt regression in CI.

- **Strands Evals** (strands-agents/evals) — Apache-2.0, 75 stars, Score: 7.40
  AWS-backed trace-based agent evaluation. OpenTelemetry instrumentation. TrajectoryEvaluator, ToolSelectionAccuracyEvaluator, GoalSuccessRateEvaluator. Integration: SDD phase trajectory validation via OpenTelemetry traces.

### ASSESS

- **AgentEvals** (langchain-ai/agentevals) — MIT, 253 stars, Score: 5.80
  Trajectory matching evaluators (strict, unordered, subset, superset). LLM-as-Judge. Tightly coupled to LangChain. Stale development (last commit May 2025). Defer unless LangGraph adopted.

### Notes
- No single tool covers all Cognitive OS testing needs (MAPE-K, hook lifecycle, cross-session memory)
- Custom test harness maintained for: MAPE-K loop testing, SDD phase transitions, hook cascade testing
- Recommended stack: DeepEval (unit/trajectory) + RAGAS (memory/synthetic) + Promptfoo (red team) + custom (MAPE-K)

## 17. External Integrations

### AutoMaker (ADOPT — reverse integration)

| Tool | License | Stars | Status |
|------|---------|-------|--------|
| [AutoMaker](https://github.com/AutoMaker-Org/automaker) | Apache-2.0 | — | ADOPT |

AutoMaker is a Kanban-based dev studio that launches Claude Code sessions in git worktrees. Unlike other tools in this stack, AutoMaker is a **consumer** of Cognitive OS, not a dependency.

**Integration model**: AutoMaker → launches Claude Code → Cognitive OS hooks fire automatically (because `.claude/hooks/` exists in the project). No API client needed from our side.

**What happens when AutoMaker runs a task**:
- SessionStart hooks fire: health check, session init, metrics rotation
- PreToolUse hooks fire: completeness check, phase context, safety mesh
- PostToolUse hooks fire: error learning, auto-repair, trust score, completion gate

**Docker**: Available via `docker compose --profile ui up automaker` but is optional. AutoMaker can also run standalone.

**Skill**: `skills/automaker-bridge/SKILL.md` — configures a project for AutoMaker compatibility.

### Notes
- AutoMaker is the only tool with a "reverse" integration pattern — it consumes us, we don't consume it
- No `lib/` client needed — the integration is via hooks, not API
- The bridge skill ensures the project has the right `.claude/` structure for AutoMaker to discover

---

## 18. Claude Code Ecosystem

Tools, extensions, and frameworks built around Claude Code. Evaluated for integration into Cognitive OS infrastructure.

### ADOPT

| Tool | License | Stars | What it does | Integration plan |
|------|---------|-------|--------------|------------------|
| **agnix** | Apache-2.0 | 112 | Linter for CLAUDE.md, SKILL.md, hooks, MCP configs | Add as pre-commit validator for our 72 skills and 55 rules |
| **claude-code-action** | MIT | 6.7K | Anthropic's official GitHub Action for Claude Code in CI/CD | Integrate into our GitHub Actions for PR review + issue triage |
| **Claude Code Usage Monitor** | MIT | 7.2K | Real-time terminal token monitor with ML predictions | Complement our cost-tracking with visual terminal UI |
| **hcom (claude-hook-comms)** | MIT | 170 | Cross-terminal agent communication via hooks | Alternative to Valkey bus for simpler multi-session coordination |
| **parry** | MIT | 27 | Rust prompt injection scanner (DeBERTa/ONNX) | Strengthen content-policy hook and agent-security defenses |
| **recall** | MIT | — | Full-text search and resume for Claude Code sessions | Fill Engram gap — searchable raw conversation history |
| **Trail of Bits Skills** | CC-BY-SA-4.0 | 4K | Security audit skills from top security firm | Complement security-scanning and pentesting-readiness |

### WATCH

| Tool | License | Stars | What it does | What to learn | Extractable patterns |
|------|---------|-------|--------------|---------------|---------------------|
| **Compound Engineering** | MIT | 11.3K | Brainstorm/plan/work/review/compound workflow | "Compounding" concept, ideate/brainstorm phases | Retrospect/compound phase after archive; learning extraction loop |
| **SuperClaude** | MIT | 22K | Configuration framework with cognitive personas | Persona system, command structure patterns | Behavioral modes (`/mode`), wave-checkpoint-wave parallelism, pre-execution confidence scoring |
| **Everything Claude Code** | MIT | 113.8K | Complete agent harness with skills, memory, security | Battle-tested patterns from 10+ months daily use | Instinct extraction (`/evolve`), 3-agent red-team security, memory consolidation |
| **Ruflo/claude-flow** | MIT | 27.7K | Multi-agent swarm orchestration | Swarm patterns, AgentDB controllers | Task claiming protocol for active-tasks.json, memory forgetting curves |
| **OpenAI Swarm** | MIT | 21K | Educational multi-agent framework | Agent handoff architecture reference | Agent-to-agent handoff via return value, dynamic/callable skills |
| **Repomix** | MIT | 22.7K | Pack repo into single AI-friendly file | Context packing for repo-scout/deep-research | MCP server integration for repo-scout context packing |
| **Context7** | MIT | 50.9K | Library docs via MCP | Deeper MCP integration (already referenced) | Auto-trigger rule: check library docs before implementation |
| **cc-sessions** | MIT | 1.6K | Session management with todo validation | Scope creep prevention patterns | PostToolUse hook: detect edits outside approved scope |
| **Claude Code System Prompts** | MIT | 6.9K | Internal system prompt documentation | Claude Code internals reference | Active cross-session knowledge synthesis patterns |
| **tweakcc** | MIT | 1.5K | Customize system prompts and toolsets | Deeper customization layer ideas | Runtime prompt injection layer for behavioral overrides |
| **SPARC** | Apache-2.0 | 442 | Spec-driven AI development framework | Alternative spec methodology to study | Specification-pseudocode-architecture-refinement phasing |
| **AgentSys** | MIT | 662 | Modular runtime: 19 plugins, 47 agents | Plugin marketplace architecture | Config linter auto-fix, multi-platform adapter directories |
| **cc-devops-skills** | Apache-2.0 | 141 | DevOps skill pack (CI/CD, infra, monitoring) | Cherry-pick DevOps skills we lack | Generator+Validator pair template for infrastructure skills |
| **claude-esp** | MIT | — | Stream Claude Code hidden output to terminal | Debugging/observability patterns | Session JSONL parser for real metrics extraction |
| **Crystal** | MIT | — | Desktop app for parallel Claude Code sessions | Parallel worktree management UX | Worktree lifecycle management patterns |
| **RIPER Workflow** | MIT | — | Research/Innovate/Plan/Execute/Review workflow | Simplified workflow for adaptive-bypass | Branch-aware topic keys with `@branch` suffix |
| **Vibe-Log** | MIT | — | Session analysis and logging CLI | Session analytics patterns | Prompt quality scoring (not just ambiguity) |
| **MyCoder** | MIT | 565 | CLI-based multi-agent coding system | CLI patterns for agent orchestration | Hierarchical agent spawning with token budget caps |
| **Continue** | Apache-2.0 | — | Source-controlled AI checks for CI | CI-enforcement of AI rules | `checks/` directory + CI runner as GitHub status checks |
| **Bifrost** | Apache-2.0 | — | High-performance AI gateway in Go, 4-tier budget hierarchy | LLM routing performance, budget hierarchy patterns |
| **Portkey** | MIT | 11K | Lightweight AI gateway (200+ providers, 122KB, <1ms) | Provider routing, guardrails, virtual keys |

### Patterns to Extract (Prioritized)

Actionable patterns identified from deep analysis of WATCH repos.

#### P0 — Immediate (high impact, low effort)

| Pattern | Source | What | Effort |
|---|---|---|---|
| Context7 auto-trigger | Context7 (50.9K⭐) | Rule: check library docs before implementation | 1h |
| Repomix MCP for repo-scout | Repomix (22.7K⭐) | Add as MCP server for repo context packing | 2h |
| Session JSONL parser | claude-esp | `lib/session_parser.py` — real metrics from Claude Code sessions | 4h |

#### P1 — Next sprint (good ROI)

| Pattern | Source | What | Effort |
|---|---|---|---|
| Scope-creep detection | cc-sessions (1.6K⭐) | PostToolUse hook: detect edits outside approved scope | 1d |
| Compound/retrospect phase | Compound Engineering (11.3K⭐) | `/sdd-compound` skill: extract learnings post-archive | 1d |
| CI checks as markdown | Continue (32K⭐) | `checks/` directory + CI runner as GitHub status checks | 2d |
| Handoff pattern | OpenAI Swarm (21K⭐) | Agent-to-agent control transfer via return value | 1d |
| Task claiming protocol | Ruflo (27.7K⭐) | Agents claim tasks in active-tasks.json, prevent duplicates | 4h |
| Branch-aware Engram | RIPER Workflow | Topic keys with `@branch` suffix for feature branch scoping | 4h |
| Prompt quality scoring | Vibe-Log | PreToolUse hook: score quality (not just ambiguity) | 4h |
| Generator+Validator pairs | cc-devops-skills | Template pattern for infrastructure skills | 2h |

#### P2 — Backlog (requires design)

| Pattern | Source | What | Effort |
|---|---|---|---|
| Behavioral modes (`/mode`) | SuperClaude (22K⭐) | Switch cognitive style (brainstorm, efficiency, deep research) | 3d |
| Instinct extraction (`/evolve`) | Everything Claude Code (113.8K⭐) | Auto-detect RECURRING patterns → crystallize into skills | 5d |
| Wave-Checkpoint-Wave | SuperClaude | [parallel reads] → analyze → [parallel edits], 3.5x speedup | 3d |
| Pre-execution confidence | SuperClaude | Confidence scoring BEFORE execution, not after | 2d |
| Memory consolidation | System Prompts | Active cross-session knowledge synthesis | 2d |
| Config linter auto-fix | AgentSys (662⭐) | Validate + auto-fix rules, hooks, skills misconfigurations | 3d |

#### P3 — Future

| Pattern | Source | What |
|---|---|---|
| Red-team 3-agent security | Everything Claude Code | 3 Opus agents: red-team/blue-team/auditor |
| Memory forgetting curves | Ruflo | Temporal decay in Engram observations |
| Dynamic/callable skills | OpenAI Swarm | Skills generated dynamically from context |
| Multi-platform adapters | AgentSys | adapters/codex, adapters/opencode directories |

### Notes
- 7 tools in ADOPT ring have clear integration paths with existing Cognitive OS infrastructure.
- 19 tools in WATCH ring are monitored for patterns and ideas, not direct integration.
- 5 additional tools were evaluated but blocked by license policy (AGPL/GPL) — see `docs/05-Methodology/root/blocked-tools.md`.
- agnix is the only linter purpose-built for Claude Code configuration files.
- parry fills a gap in our prompt injection defenses with a dedicated ML-based scanner.
- Trail of Bits Skills bring professional security audit expertise as reusable skills.
---

## 15. Developer Quality Gates

Static and dynamic checks that improve agent-produced code before broader test
lanes run.

| Tool | Stars | License | Self-Host | Maturity | Description |
|------|-------|---------|-----------|----------|-------------|
| **Pyrefly** | 5.9k | MIT | Yes | Stable | Fast Python type checker and language server. **TRIAL** as an advisory CLI gate via `make typecheck-pyrefly`; first COS run found 268 non-import type/API-shape findings in about two seconds after cache warm-up. |

### Notes
- Pyrefly complements Ruff and pytest rather than replacing either.
- Keep it advisory until the historical baseline is triaged and a ratchet target
  exists for newly introduced findings.

