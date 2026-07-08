---
type: reference-synthesis
source: docs/08-References/root/recommended-stack.md
provenance: "Best-of-breed component selection for Cognitive OS infrastructure — one recommended tool plus alternative per architectural layer, with selection criteria and rationale."
---

## What it is

A reference stack-selection document naming a primary and alternative tool for each of 10 infrastructure components Cognitive OS could build on (control plane, scheduler, sandbox, multi-agent, identity, memory, tools, observability, cost, security), each gated by an explicit license policy.

## Key mechanics

- **Selection criteria**: license must be MIT/Apache-2.0/BSD (no AGPL/SSPL/ELv2/BSL); self-hostable; production-mature with active community; fits existing stack (K8s, TypeScript/Go, MCP, Engram); composable without vendor lock-in.
- **Recommended stack table** (component / primary / alternative / license / why):
  - Control Plane: **kagent** (Apache 2.0, CNCF Sandbox, K8s-native CRDs) vs AgentField.
  - Scheduler: **Temporal** (MIT, mature durable execution, used by Stripe/Netflix/Snap) vs Hatchet.
  - Sandbox: **E2B** (Apache 2.0, Firecracker microVMs, <200ms cold start, 11.4k stars) vs OpenSandbox.
  - Multi-Agent: **LangGraph + A2A Protocol** (MIT + Apache 2.0; graph-based stateful orchestration + Linux Foundation inter-agent standard, 100+ companies) vs CrewAI.
  - Identity: **AIM (OpenA2A)** (Apache 2.0, Ed25519 crypto + W3C DIDs) — no viable alternative at same maturity.
  - Memory: **Engram + Mem0** (Apache 2.0; Engram for dev-time, Mem0 adds graph relationships + multi-agent shared memory for production) vs Letta.
  - Tools: **MCP + Registry** (Apache 2.0, 1200+ servers, industry standard) — no alternative listed.
  - Observability: **Langfuse** (MIT, 23k stars, traces+prompts+evals+cost in one platform) vs OpenLIT.
  - Cost: **LiteLLM + Bifrost** (MIT + Apache 2.0; LiteLLM for budget caps/virtual keys, Bifrost for 11us-overhead Go routing) vs Portkey.
  - Security: **NeMo Guardrails + LLM Guard** (Apache 2.0 + MIT; NeMo for conversational policy via Colang, LLM Guard for 35-scanner content scanning) vs Invariant.
- **Stack interaction diagram**: Control Plane (kagent) at top, branching to Scheduler (Temporal), Identity (AIM), Observability (Langfuse); Scheduler feeds Sandbox (E2B); all converge into Multi-Agent Orchestration (LangGraph+A2A), which feeds Memory (Engram+Mem0) and Security (NeMo+Guard), which feed Tool System (MCP+C7).
- **"Why these over alternatives" rationale** for each pick: kagent over Microsoft Agent Framework (purpose-built K8s ops vs generic dev framework); Temporal over Hatchet (5+ years production scale vs simpler Postgres-only); E2B over OpenSandbox (docs/community/Firecracker maturity); LangGraph over CrewAI/AutoGen (granular graph control vs opinionated/rapidly-evolving); Langfuse over OpenLIT (complete platform vs OTEL-focused); LiteLLM+Bifrost over Portkey (enforcement + performance combined); NeMo+LLM Guard over single solution (different attack surfaces need different defenses; Invariant flagged as a possible future third layer for MCP-aware policies).

## Relations & where used

- References `../research/license-analysis.md` for the underlying license-policy justification (MIT/Apache 2.0/BSD only), which aligns with `rules/license-policy.md` (BLOCK AGPL/SSPL/BSL; ALLOW MIT/BSD/Apache).
- Complementary to `docs/08-References/root/competitive-landscape.md`'s "AI Infrastructure Concepts" appendix, which maps generic infra concepts (gateway, router, cache, etc.) to what COS *currently implements* — this document instead recommends *what to adopt* for infrastructure COS does not yet have (kagent, Temporal, E2B, LangGraph, AIM, Mem0 are all aspirational/candidate additions, not confirmed-integrated components based on this doc alone).

## Status / caveats

- This reads as a forward-looking recommendation/proposal document rather than a record of what is already integrated — unlike `patterns-adopted.md` (which documents adopted-and-implemented patterns with file paths), this document's component picks (kagent, Temporal, E2B, LangGraph+A2A, AIM, Mem0) are not accompanied by implementation file references, suggesting these are recommended-but-not-yet-wired choices. No explicit "status: proposed/implemented" marker exists in the source to confirm this reading either way — flagged as an ambiguity rather than asserted as fact.
- No internal date on the document; star counts and version claims (E2B 11.4k stars, Langfuse 23k stars) are point-in-time and will drift.
