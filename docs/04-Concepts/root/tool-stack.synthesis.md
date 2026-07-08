---
type: concept-synthesis
source: docs/04-Concepts/root/tool-stack.md
---

## What it is
Exhaustive vendor/tool research across 18 infrastructure categories (10 core + extended) evaluating open-source options for Cognitive OS against the license policy (AGPL/SSPL/ELv2/BSL blocked).

## Key mechanics
Verdicts and key facts by category:
1. **Control Plane**: Galileo Agent Control, NVIDIA OpenShell, AgentField, kagent (CNCF Sandbox), Microsoft Agent Framework (27k★, MIT, mature) — all Apache-2.0/MIT, no explicit ADOPT yet.
2. **Scheduler**: Temporal (19k★ MIT, gold standard), Hatchet (6.6k★ MIT, Postgres-only), Celery (25k★ BSD-3, Python-only), KAI Scheduler (Apache-2.0). Blocked: Windmill (AGPL), Inngest (SSPL).
3. **Runtime Sandbox**: E2B (11.4k★ Apache-2.0, Firecracker microVM, <200ms cold start, production leader), OpenSandbox/Alibaba (8.3k★), microsandbox (3.3k★, libkrun, MCP-native), Agent Sandbox K8s SIG. Blocked: Daytona (65k★, AGPL).
4. **Multi-Agent Orchestration**: LangGraph (15k★ MIT), CrewAI (44k★ MIT), AutoGen (55k★ MIT), Google ADK (18k★ Apache-2.0), A2A Protocol (Linux Foundation standard, 100+ companies), xpander.ai (860★ MIT, **TRIAL** 7.20, reference-architecture-only to avoid lock-in).
5. **Agent Identity** (least mature space): AIM/OpenA2A (Ed25519+DID, most complete), AgentFacts (MIT), OpenAgents, A2A Agent Cards.
6. **Memory**: Engram (Apache-2.0, **ALREADY IN USE**, FTS5), Mem0 (48k★ Apache-2.0), Letta/MemGPT (15k★ Apache-2.0, tiered memory), MemOS (7.4k★, license TBD), Hindsight (MIT), Cognee (~7.5k★ Apache-2.0, **ADOPT** score 8.20, ECL pipeline, complements engram), arscontexta (~2.2k★ MIT, **ASSESS** 6.65, subagent-per-phase reference).
7. **Tool System**: MCP Protocol (**ALREADY IN USE**, 1200+ servers), Context7 (**ALREADY IN USE**), Portkey Gateway (10k★ MIT), LiteLLM (40k★ MIT, 100+ providers).
8. **Observability**: Langfuse (23k★ MIT, most complete self-hosted), OpenLIT (2.3k★ Apache-2.0), Helicone (5k★ Apache-2.0), AgentOps (5.3k★ MIT), OpenLLMetry (5k★ Apache-2.0), Plano (Apache-2.0), Opik (18.3k★ Apache-2.0, **ADOPT** score 8.95, 40M+ traces/day, MCP server), error-monitoring-agent (MIT, **TRIAL** 6.80, cluster->enrich->analyze->act). Blocked: Arize Phoenix (ELv2).
9. **Cost Control**: LiteLLM, Bifrost (Apache-2.0, 4-tier budget global/org/team/agent, 11us overhead, Go), Portkey, Langfuse, AgentOps.
10. **Security**: NeMo Guardrails (4k★ Apache-2.0, Colang), LLM Guard (2.5k★ MIT, 15 input + 20 output scanners), Guardrails AI (4k★ Apache-2.0, 50+ validators), Invariant Guardrails (Apache-2.0, MCP-aware, Snyk-backed), LlamaFirewall/Meta (3k★ MIT, PromptGuard 2), Plano (~5.9k★ Apache-2.0, **TRIAL** 7.80, Envoy/Rust/WASM). Blocked: FalkorDB (SSPL, **REJECT**), QueryWeaver (AGPL, **REJECT**).
11. **Web Crawling**: Crawl4AI (~30k★ Apache-2.0, **ADOPT**, `lib/web_crawler.py` wrapper; falls back to `urllib` + HTML-stripping when not installed; structured extraction/multi-page crawling require Crawl4AI, no fallback).
12. **Platforms & Infra**: pg_textsearch (~3.2k★, PostgreSQL License, **TRIAL** 7.50, BM25, pre-v1.0), MindsDB (30k+★, ELv2, **ASSESS** 5.50, self-hosted-only caution).
13. **Model Training**: Unsloth (44.6k★, Apache-2.0 core / AGPL Studio, **ASSESS** 6.15 — use Apache core only, avoid AGPL Studio).
14. **Inference**: RLM (3.2k★ MIT, **ASSESS** 5.80, MIT OASYS lab, research-grade only).
15. **Reference**: ai-engineering-hub (31.1k★ MIT, **HOLD**, learning resource only).
16. **Testing & Evaluation**: ADOPT — DeepEval (Apache-2.0, 14k★, score 8.08, pytest-native, 60+ metrics, 40+ vuln red-team categories), RAGAS (Apache-2.0, 12.9k★, score 8.30, 40+ RAG metrics). TRIAL — Promptfoo (MIT, 12.8k★, score 7.80, 50+ red-team plugins, acquired by OpenAI Mar 2026, remains MIT), Strands Evals (Apache-2.0, 75★, score 7.40, AWS-backed OTEL trajectory eval). ASSESS — AgentEvals (MIT, 253★, score 5.80, LangChain-coupled, stale since May 2025). Recommended stack: DeepEval + RAGAS + Promptfoo + custom MAPE-K harness.
17. **External Integrations**: AutoMaker (Apache-2.0, **ADOPT**, reverse integration — consumes COS via `.claude/hooks/`, no API client needed; `docker compose --profile ui up automaker` optional).
18. **Claude Code Ecosystem**: ADOPT ring — agnix (Apache-2.0, 112★, CLAUDE.md/SKILL.md/hooks/MCP linter), claude-code-action (MIT, 6.7K★, official GH Action), Claude Code Usage Monitor (MIT, 7.2K★), hcom (MIT, 170★, cross-terminal hooks), parry (MIT, 27★, Rust DeBERTa/ONNX injection scanner), recall (MIT, session search), Trail of Bits Skills (CC-BY-SA-4.0, 4K★). WATCH ring: 19 tools incl. Compound Engineering, SuperClaude, Everything Claude Code (113.8K★), Ruflo/claude-flow, OpenAI Swarm, Repomix, Context7, cc-sessions, Bifrost, Portkey. Patterns prioritized P0 (Context7 auto-trigger 1h, Repomix MCP 2h, session JSONL parser 4h) through P3 (red-team 3-agent security, memory forgetting curves, dynamic skills, multi-platform adapters).
19. **Developer Quality Gates**: Pyrefly (5.9k★ MIT, **TRIAL**, advisory via `make typecheck-pyrefly`; first COS run found 268 non-import type/API-shape findings in ~2s after cache warm-up).

## Relations & where used
References `rules/license-policy.md` (AGPL/SSPL/ELv2/BSL blocked), `docs/04-Concepts/root/component-sources.md`, `docs/08-References/root/competitive-analysis.md`, `docs/04-Concepts/root/ecosystem-comparison.md`, `docs/05-Methodology/root/blocked-tools.md`, `docs/04-Concepts/architecture/agent-training-harness.md`.

## Status / caveats
Living research doc; verdicts (ADOPT/TRIAL/ASSESS/WATCH/HOLD/REJECT/BLOCKED) vary by tool maturity and license. Several tools already integrated (Engram, MCP, Context7). Note: source doc reuses section number "15" for both "Reference & Educational" and "Developer Quality Gates".
