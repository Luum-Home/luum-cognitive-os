---
type: adr-synthesis
source: docs/02-Decisions/adrs/ADR-080-hermes-cross-harness-adoption.md
adr: ADR-080
status: accepted
reality_level: PARTIAL
provenance: Prior ADRs (074-078) evaluated the Hermes plugin against Claude-Code-as-only-harness and dismissed the remainder as "Claude Code-specific" — a dismissal later judged wrong once re-evaluated through the cross-harness lens established by ADR-057/064, since features Claude Code provides for free (auto context compaction, native prompt caching, unified rate-limit governance) are absent in every other harness.
---

## Decision

Umbrella ADR grouping remaining MIT-licensed Hermes plugin pieces into four tiers by cross-harness necessity: Tier 1 (critical parity — multi-provider adapters, portable prompt caching, context/trajectory compressors, rate-limit instrumentation, sequentially dependency-ordered with adapters first), Tier 2 (COS feature parity outside Claude Code — batch runner/cron, error classifier+insights), a parking lot (skill_commands.py, ACP adapter — needs further investigation before a porting decision), and explicit discards (memory plugins like byterover/mem0/supermemory — rejected as duplicate storage paths competing with Engram; tinker-atropos RL training — out of operational scope). A piece qualifies as load-bearing only if non-Claude harnesses have no native equivalent AND its absence degrades correctness/reliability/cost-predictability.

## Why

ADR-057 and ADR-064 establish COS must run identically across Claude Code, Cursor, Devin, VS Code Agent, Cline, and future harnesses executing the same SKILLS+RULES surface — but runtime conveniences the Claude Code harness provides natively (context compaction, prompt caching, rate-limit governance) simply don't exist elsewhere, so features previously dismissed as "Claude-Code-specific wrappers" during the ADR-074/078 review were in fact the only portable implementation of infrastructure those other harnesses fundamentally lack. Hermes (MIT-licensed, cleared for copy-verbatim porting since the ADR-078 adoption note) had already solved provider normalization, prompt-cache abstraction, and error taxonomy in a battle-tested implementation — reinventing this from scratch was rejected as duplicate work with no advantage.

## Consequences

Positive: any non-Claude harness becomes a first-class COS target once Tier 1 lands, with the same reliability guarantees Claude Code gets natively; the `resource-governor` skill gains real consumption data instead of estimates once rate-limit instrumentation ships; `/schedule` and `/loop` stop being Claude-Code-only once the batch/cron primitives land; error deduplication becomes semantic rather than string-matching once the classifier+insights layer ships.

Negative/trade-offs: Tier 1 is sequentially coupled — multi-provider adapters (item 1, tied to the separate ADR-081 Codex adapter work) must land before items 2-4 can be fully wired to a provider surface, though harness-independent items (like a decoupled prompt-caching layer) may proceed in parallel if explicitly marked as such; the provider adapter matrix (gemini x bedrock x copilot x codex) grows mock-maintenance burden in tests; leaving the parking-lot items (skill_commands.py, ACP) unresolved means the skill-invocation and multi-agent-communication surfaces stay partially undefined, with a recommended 2-sprint triage deadline after Tier 1 item 1 lands.

## Status & current state

Accepted 2026-04-30, implementation_status "implemented," but the frontmatter classification reflects only the umbrella acceptance — the body's own status table shows real partial completion. Shipped: Tier 1 #2 portable prompt caching (`lib/prompt_cache.py`, 73 tests), Tier 1 #3 context/trajectory compressors (`lib/context_compressor.py`, activated via `COS_CONTEXT_COMPRESS=1`, explicitly must NOT be set by Claude Code harnesses since native PreCompact already handles it), Tier 1 #4 rate-limit instrumentation (`lib/rate_limit_tracker.py`, off by default via `COS_RATE_TRACKER=1`, complementary to but distinct from the existing bash `hooks/rate-limiter.sh` which governs COS tool-call rate rather than provider API quota), Tier 2 #5 batch runner/cron (`lib/cos_batch_runner.py`, `lib/cos_cron.py`, jobs default `enabled=false`, daemon opt-in only), Tier 2 #6 error classifier+insights (`lib/error_classifier.py` JSONL layer, `lib/error_insights.py`, `bin/cos-errors`, 90 new tests) — Tier 2 is explicitly marked closed. Tier 1 item #1 (multi-provider adapters, the dependency-order blocker for the rest of Tier 1) is not confirmed shipped in this document and is tracked under the separate ADR-081. Parking-lot items #7/#8 remain uninvestigated.

## Key links

ADR-057 (harness-agnostic core), ADR-064 (cross-harness authoring guide, still Proposed pending a second real harness proving the ADR-033 canonical event schema), ADR-033 (harness-agnostic event capture schema), ADR-074 (Tier-0 learning loop), ADR-076 (skill-tier frontmatter, Hermes tier model), ADR-077 (peer-card user-memory model), ADR-078 (mid-task memory tool, prior Hermes port and MIT license clearance precedent), ADR-081 (Codex harness adapter — the Tier 1 sequencing prerequisite), `.cognitive-os/adoption-registry.yaml`, `.claude/plugins/hermes-agent/`.
