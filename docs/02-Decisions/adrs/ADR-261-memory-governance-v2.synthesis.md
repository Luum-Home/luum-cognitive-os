---
type: adr-synthesis
source: docs/02-Decisions/adrs/ADR-261-memory-governance-v2.md
adr: ADR-261
status: accepted
reality_level: REAL
provenance: Engram's observation type field was a free-form, unenforced string consulted only by lib/engram_lifecycle.py for decay-class mapping; the retrieval layer (lib/memory_retriever.py) had no awareness of type at all, so a six-month-old preference observation could keep scoring well even after being overridden, and no memory type received an intent-aware boost or "verify before use" signal.
---

## Decision

New stdlib-only module `lib/memory_governance.py` defines a static per-type policy table (`MemoryTypePolicy`: verification tier, staleness tier, stale-after threshold, recall-boost multiplier) covering six types — `preference`, `identity`, `fact`, `procedure`, `blocker`, `decision` — with `blocker` getting the most aggressive recall boost (1.8x) and shortest hard-staleness window (10 days), and `decision` getting no staleness policy at all. Unrecognized types get a complete no-op default (confidence/boost unchanged, never stale). Integration into `lib/memory_retriever.py` and `lib/engram_lifecycle.py` is strictly additive via an optional `governance` parameter defaulting to `None`.

## Why

Three concrete gaps: stale memory could surface with high confidence indefinitely since nothing detected or signaled that a reinforced-but-overridden preference might be outdated; there was no verification differentiation between a `fact` (external, needs re-confirmation) and a `decision` (internal, stable) even though they have completely different trust lifecycles; and there was no intent-aware boost, so a procedural query ("how do I release a version?") couldn't preferentially surface `procedure`-type memories over equally-lexically-similar `bugfix` entries. This ADR adopts the pattern from a private clean-room research annex under the ADR-259 protocol — the annex documents a reference system solving the same three problems with a static rule table, and additionally flags that the reference system itself lacks `procedure` and `blocker` types, which this ADR independently adds since they map directly to existing luum content (`docs/05-Methodology/runbooks/`) and known-issue tracking respectively.

## Consequences

Positive: hard-staleness types (`fact`, `blocker`) past threshold are auto-suppressed from recall, preventing outdated entries from surfacing with misleadingly high confidence; `preference` observations score 40% higher than baseline on equal lexical match; `blocker` observations get the system's highest recall boost, ensuring known hard constraints stay prominent; a `freshness_note` field propagates through `lib/memory.py` so the assistant can include verification cues in replies; a `governance_reasons` list gives a machine-readable audit trail per recall for retrieval-benchmark analysis.

Negative/trade-offs: the policy table is statically hardcoded in v1 — any threshold or boost change requires a code change and PR review, with no YAML override path (explicitly deferred to a phase-2 ADR); the six governed types cover only a minority of existing observation types, so most luum observations (`bugfix`, `discovery`, `architecture`) fall through to the no-op default and pay governance overhead for zero benefit until enrolled; hard suppression of stale results is irreversible at query time — a suppressed 31-day-old `fact` may still be the best available answer with no "suppressed but available on request" fallback in v1 (mitigation path noted: a future `include_stale` parameter).

## Status & current state

Accepted 2026-05-11, implementation_status "implemented" with strong verification (`tests/unit/test_memory_governance.py tests/red_team/portability/test_engram_lifecycle.py`). Two open questions flagged as genuinely unresolved at acceptance: whether the six `stale_after_seconds` thresholds are calibrated correctly for real recall quality (UNSURE, pending benchmark data via `lib/memory_retrieval_benchmark.py`), and whether `assess_freshness` should consult the graph/relation layer (`engram_graph_walker.py`, bitemporal `supersedes` edges) before deciding freshness rather than relying on age alone — deferred to a follow-up ADR, with v1 operating on age alone.

## Key links

ADR-259 (holaOS Adoption Posture — umbrella clean-room policy this implements as its second concrete instance), ADR-071 (Ebbinghaus lifecycle decay — the decay model this ADR's `lib/engram_lifecycle.py` integration extends with a governance override of tau), ADR-078 (Mid-Task Memory Tool — complementary, governs write-time decisions rather than recall-time scoring), `lib/memory_governance.py`, `lib/memory_retriever.py`, `lib/memory.py`, `rules/memory-governance.md`, `rules/RULES-COMPACT.md` §11 (type string conventions).
