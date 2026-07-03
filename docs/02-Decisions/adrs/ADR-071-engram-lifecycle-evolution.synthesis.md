---
type: adr-synthesis
source: docs/02-Decisions/adrs/ADR-071-engram-lifecycle-evolution.md
adr: ADR-071
status: accepted
reality_level: PARTIAL
provenance: Engram's observation schema has no native fields for confidence, decay, or reinforcement, so all observations retrieve with equal weight regardless of age or confirmation count — a one-year-old ADR about a deprecated dependency competes on equal footing with a two-week-old bugfix on the same module.
---

## Decision

Extend engram's behavior via a Python wrapper layer (`lib/engram_lifecycle.py`) rather than forking or migrating the backend: lifecycle metadata (confidence, last_reinforced, reinforcement_count, decay_class) is encoded as a fenced `<engram-lifecycle>` JSON trailer appended to each observation's `content` field — a format engram passes through unchanged. Search results are re-ranked post-hoc using `adjusted_score = base_score*(1-alpha) + confidence*R(t)*alpha` (alpha=0.3, engram's native relevance dominates), with Ebbinghaus retention decay `R(t)=exp(-t/tau)` keyed to a per-type decay class (architecture=365d down to bugfix=60d). Reinforcement on every access nudges confidence asymptotically toward but never reaching 1.0.

## Why

A 38-source research survey (2026-04-27) into the major AI memory frameworks (Mem0, Zep/Graphiti, Cognee, Letta/MemGPT, GraphRAG, HippoRAG, LightRAG) confirmed the industry-wide diagnosis that the bottleneck for AI memory is not visualization but memory lifecycle: confidence scoring with decay, supersession, and consolidation tiers. Engram itself provides none of this natively. The wrapper approach was chosen over four rejected alternatives specifically because it requires no engram binary modification, no upstream dependency pinning, and is fully reversible (trailers are inert prose if the wrapper is removed) — forking engram was rejected as high-maintenance-burden on a third-party binary not owned by this project, and migrating to Mem0/Zep was rejected as 4-8 week efforts for marginal benefit over extending what already exists.

## Consequences

Positive: search ranking reflects actual epistemic state instead of treating all memory as equally reliable; agents can report calibrated confidence; reinforcement-on-access is self-reinforcing (frequently used observations become more visible over time); zero data loss on rollback.

Negative/trade-offs: ~10ms overhead per wrapped search call; the trailer is visible noise if a human reads the raw observation via engram CLI; observations saved before Phase 1 shipped have no trailer and get cold-start defaults until reinforced; alpha=0.3 and beta=0.15 are uncalibrated initial guesses requiring production tuning. Documented honest limitations (post-implementation): the crystallizer (Phase 2) uses no LLM — deterministic concat/dedup only, capped at 4000 chars; `mem_judge` supersedes edges are not actually written (engram's HTTP API doesn't expose `/relations` writes) — Phase 2 stores `crystallized: true` + `superseded_obs_ids` in the trailer instead, so the graph itself doesn't show the supersedes edge; reinforcement is local-only, not aggregated across devices on cloud sync; the graph walker reads SQLite directly (bypassing the HTTP API), coupling it to engram's schema and risking silent wrong results if that schema changes.

## Status & current state

Accepted 2026-04-27, implementation_status "partial" (Phases 2-4 scoped but gated on Phase 1 verification per the original decision). In practice all four phases shipped per the addenda: Phase 1 (confidence+decay) done in Wave 3a with 89 passing tests (75 unit + 14 e2e); an addendum the same day corrected an incorrect original claim about `reinforce()` needing an unavailable engram CLI feature — the HTTP API at port 7437 was discovered to already support GET/PATCH, making reinforcement fully functional (this discovery also triggered a new safety policy, `rules/engram-api-safety.md`, after an accidental overwrite of a real observation during API exploration). Phase 2 (crystallization) and Phase 3 (graph traversal) shipped the same day in Wave 3b. Phase 4 (Obsidian export) shipped 2026-05-05 as a manual, dry-run-first, opt-in-only slice — the vault stays outside the repo, `docs/` remains the source of truth, and no automatic commit path exists.

## Key links

`docs/03-PoCs/research/llm-wiki-v2-engram-evolution-2026-04-27.md` (research backing), `.cognitive-os/plans/features/engram-lifecycle-evolution.md` (phased plan), `rules/engram-api-safety.md` (production daemon mutation safety policy, added in addendum), ADR-261 (Memory Governance v2, a later complementary layer extending `_TYPE_TO_DECAY_CLASS`), `lib/engram_client.py`, `lib/engram_http_client.py`, `lib/engram_crystallizer.py`, `lib/engram_graph_walker.py`, `lib/engram_obsidian_exporter.py`.
