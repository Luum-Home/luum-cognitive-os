---
title: External Tool Adoption Doctrine
date: 2026-05-08
status: proposed-doctrine
source_index: docs/reports/external-tools-radar-INDEX.md
source_reports:
  - docs/reports/external-tools-radar-2026-05-08.md
  - docs/reports/cross-check-A-memory-2026-05-08.md
  - docs/reports/cross-check-B-sandbox-mcp-2026-05-08.md
  - docs/reports/cross-check-C-orchestration-2026-05-08.md
  - docs/reports/cross-check-D-codegen-skills-tui-2026-05-08.md
  - docs/reports/cross-check-E-observability-debt-2026-05-08.md
related_adrs: [ADR-058, ADR-065, ADR-192, ADR-212, ADR-247, ADR-250, ADR-251, ADR-252, ADR-253]
---

# External Tool Adoption Doctrine

## Why this exists

The tech-radar corpus shows a recurring risk: Cognitive OS can drift from
"govern and compose the agentic ecosystem" into "rebuild every interesting
agentic subsystem". That is the wrong product shape. The durable wedge is not
being another LangGraph, AutoGen, CrewAI, RAG framework, TUI framework, or
observability product. The durable wedge is a **governance/control plane for
coding agents** that can adopt mature tools while preserving COS semantics:
ownership, safety gates, receipts, claims, budgets, release freeze, and
cross-harness portability.

This doctrine turns the radar into a decision rule before new implementation
work starts.

## Decision vocabulary

| Verdict | Meaning | COS default action |
|---|---|---|
| ADOPT | External primitive should be the selected implementation/default for that layer. | Depend on it or call it directly, behind a version/license contract and rollback path. |
| INTEGRATE | External tool is valuable, but must remain behind a COS adapter/provider boundary. | Build adapter + policy wrapper; do not let it become COS source of truth. |
| BUILD | COS must own this behavior because it is governance, policy, evidence, or product semantics. | Implement in COS; use external ideas only as references. |
| DEFER | Tool/pattern is interesting but too heavy, immature, or outside local-first scope. | Track in radar; do not add default dependency or roadmap commitment. |
| REJECT | Tool/pattern conflicts with license, footprint, or product boundary. | Add to blocked/rejected ledger with rationale. |

## Core rule

> Adopt commodity mechanisms; build governance semantics.

COS should adopt or integrate the mechanism when the external ecosystem is
better at it, but COS must build the layer that answers:

- Is this action allowed now?
- Who owns this file/task/surface?
- What evidence proves the claim?
- What is the budget/cost blast radius?
- Is the tool active, opt-in, blueprint, or rejected?
- Can this behavior travel across Claude Code, Codex, Cursor, OpenCode, CLI,
  service mode, and future containers?

## Domain matrix

| Domain | External candidates | Verdict | What to adopt/integrate | What COS must keep custom |
|---|---|---:|---|---|
| Temporal memory / knowledge graph | Graphiti | INTEGRATE -> possible ADOPT after benchmark | Bi-temporal temporal-graph schema and optional backend adapter. Graphiti is a temporal context graph engine with validity windows, provenance, hybrid search, and incremental updates. | Engram lifecycle, privacy classes, portability boundaries, project scoping, memory governance, decay rules, and receipts. |
| Graph RAG retrieval | LightRAG | INTEGRATE / DEFER core | Dual-level retrieval idea and benchmark corpus; possibly provider adapter for docs/corpus retrieval. | Canonical agent memory. LightRAG is better treated as document/corpus RAG, not the only COS memory substrate. |
| Multi-hop graph retrieval | HippoRAG | DEFER runtime / ADOPT benchmark idea | Personalized PageRank and multi-hop benchmark reference. | Runtime default until local benchmark proves superiority over existing graph walk. |
| LM program optimization | DSPy | INTEGRATE | Prompt/skill optimization for structured-I/O skills and eval-backed prompt compilation. DSPy optimizers tune programs when final output can be evaluated. | Skill routing, dangerous-skill rejection, negative-context guards, and governance gates. DSPy is not a router replacement. |
| Repo context selection | Aider repo-map | ADOPT concept / BUILD COS layer | Graph-ranked symbol map with token budget. Aider’s repo map sends concise classes/functions/signatures and ranks relevant portions. | COS projection must include agentic primitives: hooks, rules, skills, ADRs, tests, metrics, and governance state. |
| Multi-agent control adapter | agentapi | INTEGRATE | Optional HTTP adapter/test fixture source for multiple coding agents. | COS ownership/liveness, branch/worktree policy, claims, receipts, release freeze, and handoff governance. |
| Skills methodology | Superpowers | INTEGRATE selectively | Skill-description conventions and importable methodology patterns where evidence supports them. | COS skill lifecycle, policy routing, ADR provenance, and capability matrix. |
| TUI | Bubble Tea | ADOPT | Go TUI framework. Bubble Tea is Elm-architecture based and production-proven. | COS command semantics, safety UX, and release flows. |
| MCP server/client | FastMCP + official MCP SDK | ADOPT | Python MCP server/client framework, stdio/HTTP transports, schema generation. FastMCP explicitly targets MCP apps and tool/resource/prompt surfaces. | COS tool exposure policy, trust pinning, permission envelopes, and audit. |
| Sandbox mechanism | Bubblewrap / Seatbelt / E2B opt-in | INTEGRATE | Low-level sandbox backend. Bubblewrap exposes namespaces and seccomp arguments; Seatbelt covers macOS profile enforcement. | Threat model, profile policy, deny/allow rules, fallback behavior, and audit. |
| Observability UI/evals | Phoenix, MLflow, OpenTelemetry | ADOPT standards / INTEGRATE backends | OTel/OpenInference traces, Phoenix for LLM debugging/evals, MLflow for outcome tracking. | COS receipts, control-plane findings, remediation queues, and claim closure. |
| Capability reality / claims | n/a | BUILD | External tools can inform, not own. | ADR-252 capability matrix, claim gates, public-feature reality ledger. |
| Approval policy | YAML + future OPA only if needed | BUILD now / DEFER OPA | Borrow policy-as-code patterns. | Local-first policy evaluator and projection to hooks/settings. |
| Distributed workflow engines | Temporal, NATS, Firecracker-primary, OPA-by-default | DEFER | Study patterns only. | Local-first event bus, file-IPC, release freeze, and worktree governance. |

## Anti-reinvention guardrail

Before adding a new custom subsystem, the proposal must answer:

1. Which existing tool/framework already solves the mechanism?
2. Is the missing value actually COS governance semantics?
3. Can the external tool sit behind an adapter without becoming source of
   truth?
4. What is the license, footprint, default-install impact, and fallback?
5. What audit proves the tool is active rather than blueprint?

If answers 1-3 point to a mature external tool, build only the adapter and
policy wrapper.

## Source-backed external observations

- Graphiti frames itself as temporal context graphs for agents, with facts that
  track validity windows, provenance episodes, and hybrid semantic/keyword/graph
  retrieval: [getzep/graphiti](https://github.com/getzep/graphiti).
- LightRAG’s paper describes graph-structured indexing plus dual-level retrieval
  over low-level and high-level knowledge: [LightRAG arXiv](https://arxiv.org/abs/2410.05779).
- HippoRAG combines knowledge graphs with Personalized PageRank for long-term
  memory retrieval: [HippoRAG arXiv](https://arxiv.org/abs/2405.14831).
- DSPy positions optimizers around measurable outputs and typed signatures,
  which fits skill optimization but not routing: [DSPy](https://dspy.ai/).
- Aider documents repo maps with classes/functions/signatures and graph ranking
  under a token budget: [Aider repo map](https://aider.chat/docs/repomap.html).
- FastMCP is the Pythonic framework for MCP servers/clients/apps; COS should
  not reimplement MCP transport: [FastMCP docs](https://gofastmcp.com/getting-started/welcome).
- OpenTelemetry now has MCP semantic conventions, but they are still marked
  development; COS should version its own mapping defensively:
  [OTel MCP SemConv](https://opentelemetry.io/docs/specs/semconv/gen-ai/mcp/).

## Acceptance criteria for future implementations

- Every new external-tool adoption has an explicit type: dependency,
  cli-adapter, schema-port, algorithm-port, testdata-vendor, operator-installed,
  or pattern-only.
- Every adoption has license posture, footprint posture, default-install impact,
  owner, tests, and rollback/deprecation path.
- Every custom feature proposal includes an anti-reinvention answer.
- COS remains local-first by default; heavy infra must be opt-in or deferred.
