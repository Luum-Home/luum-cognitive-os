---
type: adr-synthesis
source: docs/02-Decisions/adrs/ADR-049-llm-gateway-selection-and-overflow-providers.md
adr: ADR-049
status: accepted
reality_level: REAL
provenance: The user on Claude Code Max ($200/mo) hit rate limits mid-session ("You're out of extra usage · resets 2pm") after running 4-5 opus-class sub-agents in parallel burned the 5h usage window with no overflow valve, and Claude Code's native Agent tool has no public hook to redirect it to another provider.
---

## Decision

Remove LiteLLM entirely and do not adopt Bifrost as a proxy; implement direct-SDK dispatch in `lib/model_router.py` instead. Build a multi-provider overflow cascade with Alibaba Qwen Coding Plan Pro selected as the primary overflow provider (ahead of Z.AI GLM and MiniMax), reserving Anthropic API direct dispatch as a tier-6 fallback for explicitly critical tasks only. Architecture correction mid-ADR: since Claude Code's main chat cannot be redirected (proprietary app, no interception point), only sub-agents dispatched via `scripts/orchestrator.py` can use the cascade — so Qwen is PRIMARY for sub-agents (preserving Claude Max quota for the main chat) and Claude is FALLBACK, invoked only when Qwen fails.

## Why

LiteLLM was the subject of a March 2026 supply-chain compromise (Trend Micro Research) where a malicious package was injected upstream and propagated via `pip install litellm` — a disqualifying trust-boundary violation for a proxy that also concentrates every provider's API keys in one process. Bifrost (Go binary, 50x lower overhead, no published CVEs, Apache 2.0) is objectively safer but still proxies keys and adds a container to the security perimeter — deemed unjustified for single-operator sub-agent orchestration, not production multi-user service at high RPS. Direct SDK dispatch was chosen because OpenAI-compatible `base_url` override lets one SDK cover four providers (Qwen/DeepSeek/GLM/MiniMax via OpenRouter), keeping the attack surface to only the SDKs actually imported. Qwen Coding Plan Pro won over MiniMax Coding Plan Max on 7 of 9 compared dimensions (quota, model families bundled, context window, SWE-bench score, vendor stability) despite both costing $50/mo, and won over Z.AI GLM on price ($50 vs $64.80), model families bundled, and context size — Z.AI having already doubled prices twice within two months.

## Consequences

Positive: supply-chain attack surface reduced (no proxy holding aggregated keys); predictable ~$220-250/mo cost envelope with effectively unlimited overflow for interactive coding work versus $260-380/mo for Anthropic-direct-as-overflow; provider independence prevents any single vendor holding service hostage via rate limits or price hikes; simpler debugging via standard Python tracebacks instead of a proxy black-box.

Negative/trade-offs: the project now owns and maintains dispatch logic in `lib/model_router.py` (~2-3h initial build, ~30min per new provider); output quality varies across GLM/Qwen/MiniMax versus Claude for non-code tasks, mitigated by routing high-priority tasks to tier-6 Anthropic-direct when budget permits; multiple API keys must be managed across providers. All providers are implemented as always-present stubs gated by per-provider `enabled` feature flags in `cognitive-os.yaml`, so a user can start with a single provider and add more with zero code changes. Qwen Pro's ToS restricts it to interactive use only (no batch/cron/backend) — judged acceptable because the actual overflow target (sub-agents spawned during an interactive session when rate-limited) is exactly that use case.

## Status & current state

Accepted 2026-04-21, implementation_status "implemented." Supersedes ADR-011 entirely and the LLM-gateway portions of ADR-018 (which remains canonical for the broader Docker-to-pip migration). Mega-plan checkpoints C0-C7 all shipped (`--providers` CLI cascade, `lib/dispatch.py` router, `rules/llm-dispatch.md`, `/llm-status` skill, operational runbook, `claude-code-router` research reaching a NO-GO verdict, ADR-051 Phase 1 Qwen agent loop). C8 (ADR-051 Phases 2-4: remaining tools, hooks injection, parity) is explicitly DEFERRED. Reserved future ADR slots (050 per-skill routing, 052 provider benchmark harness, 053 dispatch auto-optimizer) are documented as not required for the current cascade to function.

## Key links

ADR-022 (prior LiteLLM adoption, superseded), ADR-028 (`ORCHESTRATOR_MODE=executor` framework, LiteLLM dependency replaced by direct-SDK dispatch), ADR-042 (Valkey local daemon, precedent for pip-first migration), `rules/model-routing.md`, `rules/resource-governance.md`, `rules/credential-management.md`, `lib/model_router.py`, `lib/cost_predictor.py`, `lib/qwen_agent_loop.py`.
