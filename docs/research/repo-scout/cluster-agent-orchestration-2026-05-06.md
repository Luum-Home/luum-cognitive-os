---
cluster: agent-orchestration
date: 2026-05-06
phase: shallow
total: 11
adopt: 0
prototype: 4
monitor: 6
reject: 1
---

# Cluster Scout — agent-orchestration (shallow, 2026-05-06)

Theme: multi-agent orchestration frameworks + LLM gateways/proxies. Evaluated against COS's existing dispatch layer (ADR-049 `lib/dispatch.py`, `scripts/orchestrator.py`) and orchestrator/squad primitives.

## Per-Repo Triage

### 1. BerriAI/litellm
- URL: https://github.com/BerriAI/litellm
- License: MIT (root) — `enterprise/` dir carries separate proprietary license; OSS portion is clean
- Stars: 45,798
- Last commit: 2026-05-06
- Primary language: Python
- Purpose: SDK + AI gateway/proxy translating 100+ LLM APIs into OpenAI format with cost tracking, load balancing, guardrails
- Verdict: **monitor**
- Rationale: ADR-049 + `lib/dispatch.py` already cover Qwen-primary/Claude-fallback routing with kill-switches and metrics. LiteLLM offers broader provider matrix and battle-tested cost/observability hooks, but adoption would invert our routing topology. Worth tracking patterns (provider abstraction, fallback policies) without integrating.

### 2. ComposioHQ/agent-orchestrator
- URL: https://github.com/ComposioHQ/agent-orchestrator
- License: MIT
- Stars: 6,821
- Last commit: 2026-05-06
- Primary language: TypeScript
- Purpose: Agentic orchestrator for parallel coding agents — plans tasks, spawns agents, autonomously fixes CI/merge conflicts/reviews
- Verdict: **prototype**
- Rationale: Direct conceptual overlap with our orchestrator (parallel agents, CI repair, review loops). TS stack is foreign but patterns (DAG planning, autonomous fix loops) could refine SDD apply-verify retry loop. Phase-2 worth deep-reading planning + conflict-resolution logic.

### 3. FoundationAgents/MetaGPT
- URL: https://github.com/FoundationAgents/MetaGPT
- License: MIT
- Stars: 67,714
- Last commit: 2026-01-21 (4 months stale)
- Primary language: Python
- Purpose: Multi-agent framework simulating a software company (PM/architect/engineer roles) for natural-language programming
- Verdict: **monitor**
- Rationale: Role-based collaboration patterns inform squad-protocol/peer-card design, but framework is opinionated and largely orthogonal to COS's stateless agent model. Velocity slowing (4mo since push) reduces urgency. Reverse-engineer SOP/role-handoff patterns only if we revisit squad composition.

### 4. JackChen-me/open-multi-agent
- URL: https://github.com/JackChen-me/open-multi-agent
- License: MIT
- Stars: 6,050
- Last commit: 2026-05-05
- Primary language: TypeScript
- Purpose: Goal-to-task-DAG multi-agent orchestration with MCP integration and live tracing; minimal runtime deps
- Verdict: **prototype**
- Rationale: Task-DAG primitive aligns with our [`task-dag`] rule and SDD dependency graph. MCP-native + live tracing is exactly the surface we want to learn from. Phase-2 deep-read for DAG construction algorithm and tracing schema.

### 5. agentgateway/agentgateway
- URL: https://github.com/agentgateway/agentgateway
- License: Apache-2.0
- Stars: 2,603
- Last commit: 2026-05-05
- Primary language: Rust
- Purpose: Next-gen agentic proxy for AI agents and MCP servers
- Verdict: **monitor**
- Rationale: MCP-aware proxy is novel surface — ADR-049 dispatch is LLM-only, not MCP-server-level. If our MCP server count grows, gateway pattern (auth, observability, multiplexing) becomes interesting. Rust stack raises integration cost; monitor Rust→sidecar feasibility.

### 6. agentscope-ai/agentscope
- URL: https://github.com/agentscope-ai/agentscope
- License: Apache-2.0
- Stars: 24,622
- Last commit: 2026-04-30
- Primary language: Python
- Purpose: Multi-agent platform with visualization, observability, and trust focus ("see, understand and trust")
- Verdict: **prototype**
- Rationale: Trust + observability framing matches our Trust Report / agent-dashboard / phoenix-trace work. Apache-2.0 + Python = low integration friction. Phase-2 read trace/observability adapters for potential reuse against our harness-agnostic event capture (ADR-033).

### 7. awslabs/agent-squad
- URL: https://github.com/awslabs/agent-squad (note: org redirected to `2FastLabs/agent-squad` in API response)
- License: Apache-2.0
- Stars: 7,608
- Last commit: 2026-05-04
- Primary language: Python
- Purpose: Framework for managing multiple agents and orchestrating complex conversations
- Verdict: **monitor**
- Rationale: Name collision with our squad-protocol but conceptually thinner (conversation routing, not full orchestrator). AWS-flavored adapters (Bedrock-first) reduce portability. Skim classifier/router patterns; not a high-priority deep-read.

### 8. crewAIInc/crewAI
- URL: https://github.com/crewAIInc/crewAI
- License: MIT
- Stars: 50,719
- Last commit: 2026-05-06
- Primary language: Python
- Purpose: Framework orchestrating role-playing autonomous agents for collaborative tasks
- Verdict: **monitor**
- Rationale: Mature, role-based, opinionated. Overlaps MetaGPT design space; less software-engineering-specific. Useful as comparative reference for squad-manager, but adopting would clash with COS's harness-first philosophy. Ecosystem-watch only.

### 9. maximhq/bifrost
- URL: https://github.com/maximhq/bifrost
- License: Apache-2.0
- Stars: 4,631
- Last commit: 2026-05-06
- Primary language: Go
- Purpose: High-performance enterprise AI gateway (claims 50× faster than LiteLLM, <100µs overhead at 5k RPS)
- Verdict: **monitor**
- Rationale: Same gateway category as litellm; ADR-049 covers our routing needs. Go performance profile is interesting if we ever externalize dispatch as a service, but nothing in COS's volume justifies it now. Track perf claims; do not adopt.

### 10. microsoft/agent-framework
- URL: https://github.com/microsoft/agent-framework
- License: MIT
- Stars: 10,140
- Last commit: 2026-05-06
- Primary language: Python (also .NET)
- Purpose: Framework for building/orchestrating/deploying agents and multi-agent workflows (Python + .NET)
- Verdict: **prototype**
- Rationale: Microsoft-backed successor lineage from Semantic Kernel/AutoGen. Workflow primitives (planner, executors, memory) overlap our SDD pipeline + orchestrator. Active dev, MIT, Python-first → Phase-2 deep-read for workflow-state and planner abstractions.

### 11. multica-ai/multica
- URL: https://github.com/multica-ai/multica
- License: Modified Apache-2.0 (commercial-hosting + LOGO retention clauses)
- Stars: 24,976
- Last commit: 2026-05-06
- Primary language: TypeScript
- Purpose: Open-source managed-agents platform — turn coding agents into teammates with task assignment and skill compounding
- Verdict: **reject**
- Rationale: Modified Apache-2.0 with hosted-service restriction + frontend LOGO retention is BSL-equivalent. Per cluster constraint and `[license-policy]` we cannot adopt code OR patterns from sources whose modifications restrict commercial use. Skip entirely.

## Phase 2 Candidates

Recommended deep-reads (`reverse-engineer` / `repo-forensics`):

1. **ComposioHQ/agent-orchestrator** — autonomous CI-fix + merge-conflict + review loops; cross-pollinate SDD apply-verify retry contract.
2. **JackChen-me/open-multi-agent** — goal→task-DAG construction + MCP-native tracing; map onto `[task-dag]` and harness-agnostic event capture.
3. **agentscope-ai/agentscope** — observability/trust adapters; potential alignment with phoenix-trace-ui and Trust Report evidence pipeline.
4. **microsoft/agent-framework** — workflow planner + state abstractions; comparative baseline against SDD pipeline.

Monitor-tier (no Phase 2, ecosystem watch): litellm, MetaGPT, agentgateway, awslabs/agent-squad, crewAI, bifrost.

Rejected: multica (license).
