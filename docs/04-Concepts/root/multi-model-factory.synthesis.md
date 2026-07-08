---
type: concept-synthesis
source: docs/04-Concepts/root/multi-model-factory.md
provenance: "Cognitive OS currently supports 8 models via lib/model_router.py but primarily uses Claude; this document defines the target state where different AI models handle different layers of work instead of one model doing everything."
---

## What it is
The target 3-layer "AI software factory" architecture: Strategic (most capable model, e.g. Opus), Execution (balanced model, e.g. Sonnet), and Worker (cheapest/fastest, e.g. Haiku) layers, each handling different task complexity, orchestrated instead of relying on one "best" model.

## Key mechanics
- Current state (v0.1.0): Claude Opus 4.6 (design/debugging/proposals), Sonnet 4 (implementation/specs/verification), Haiku 3.5 (archiving/docs/formatting) are primary; GPT-4o, Gemini 2.5 Pro, DeepSeek R1 configured but rarely used; Llama 3 70B, Qwen 3 32B local, configured but untested.
- SDD phase -> layer -> model mapping (`rules/model-routing.md`, `lib/model_router.py`): explore/propose/design -> Strategic/opus; spec/tasks/apply/verify -> Execution/sonnet; archive -> Worker/haiku.
- Safety mesh layer -> model mapping: clarification gate/blast radius/assumption tracking use no LLM (bash hooks); cross-verification uses Worker(haiku); adversarial review uses Strategic(opus); planning poker (`lib/planning_poker.py`) uses all 3 layers independently then reconciles via divergence detection/consensus.
- Dynamic selection factors: task complexity, budget remaining, historical performance (`estimation_calibrator.py`), availability/fallback chain.
- Example: mixed-model SDD run ~$2.40 vs all-opus ~$8.50 (3.5x more expensive, marginal quality gain).
- Multi-provider routing via LiteLLM proxy (Docker): `lib/litellm_client.py` handles non-Claude models, `route_and_execute()` auto-falls back to Claude, `lib/rate_limit_protection.py` distributes load across providers.
- Agent definitions declare model preference + fallback per squad/package YAML (e.g. architect: preferred opus, fallback gemini-2.5-pro).
- Cost optimization strategies: layer-appropriate selection, local model offloading ($0 cost for Llama/Qwen), provider arbitrage (DeepSeek R1 ~$0.55/$2.19 vs Opus $15/$75 per 1M tokens; Gemini 2.5 Pro $1.25/$5.00 at 1M context), batch bulk ops to workers, cache SDD artifacts in Engram, model downgrade chain (<80% budget normal, 80-95% force sonnet, 95-100% force haiku, >100% BLOCK).
- Capability levels (`lib/capability_levels.py`): 1 basic/2 good (all safety nets active) -> 3 excellent (disables context-management) -> 4 autonomous (+ disables clarification-gate, assumption-tracking, confidence-gate, model-routing, blast-radius).

## Relations & where used
5-layer architecture alignment: Layer 1 Rules (`rules/model-routing.md`, model-agnostic WHAT), Layer 2 Skills (model-agnostic), Layer 3 Hooks (not model-specific), Layer 4 Libs (`lib/model_router.py`, `lib/litellm_client.py` — replaceable), Layer 5 Externals (LiteLLM proxy, Anthropic/OpenAI/Google APIs, Ollama). Related primitives: `planning_poker.py`, `capability_levels.py`, `cost_predictor.py`, `estimation_calibrator.py`, `agent_bus.py`, `rate_limit_protection.py`.

## Status / caveats
Roadmap: Phase 1 (Q2 2026) LiteLLM routing active + 3+ providers validated + local models via Ollama; Phase 3 (Q4 2026) A/B testing across models; Phase 5 (2027+) fully autonomous self-optimizing selection. Only Claude tiers are in real production use today; other providers are "configured, rarely used" or "configured but untested."
