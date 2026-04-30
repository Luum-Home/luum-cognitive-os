# ADR-040 — Query-Tailored Context Injection

**Status**: Accepted  
**Date**: 2026-04-30  
**Deciders**: Matias Amendola  
**Dependencies**: ADR-037 (self-knowledge base), ADR-029b/039 (embeddings index)

---

## Context

`additionalContext` injected into sub-agents via the `SubagentStart` hook and the existing `PreToolUse:Agent` hooks is **fixed**: it injects generic preambles, BLAST RADIUS warnings, and working-dir directives regardless of the agent's actual task.

The result is that:
- A "refactor rate limiter" task receives boilerplate settings.json traps but NOT a reference to ADR-028 or `lib/rate_limiter.py`.
- A "fix UI bug" task may receive rate-limiter warnings that add noise and consume token budget.
- ADRs documenting relevant decisions are never surfaced to sub-agents unless the orchestrator manually hunts for them.

ADR-037 shipped `.cognitive-os/self-knowledge/api-surface.json`, `glossary.md`, and `dep-graph.json`. ADR-029b/039 shipped `lib/reinvention_semantic.py` with `SemanticIndex` (Jaccard, stdlib-only) and `EmbeddingsIndex` (cosine, sentence-transformers optional). These two assets unlock semantic matching at query time.

## Decision

Add a `PreToolUse:Agent` hook — `hooks/query-tailored-context-inject.sh` — that:

1. Extracts the task description from the agent's prompt (first paragraph or first 500 chars).
2. Attempts cosine embedding search via `EmbeddingsIndex`; falls back to Jaccard `SemanticIndex` if `sentence-transformers` is absent.
3. Also searches the ADR index (all `.md` files under `docs/adrs/`) and recent `debt-register.jsonl` entries.
4. Returns the **top-3** relevant snippets, capped at ~1 000 tokens of injected text.
5. Caches results by `hash(task_text)` — repeated identical tasks skip re-embedding.
6. Exits `0` silently (with empty output) when the self-knowledge index is missing.

The actual search and formatting logic lives in `lib/context_injector.py`, callable standalone (`uv run python3 lib/context_injector.py "task description"`). The hook is a thin shell wrapper that delegates to the Python helper.

## Consequences

**Positive**
- Sub-agents receive semantically relevant ADRs, lib modules, and debt notes instead of noise.
- Latency budget: p95 < 300 ms (5× slack vs the 50 ms cwd-inject target; corpus larger).
- Cache hit p95 < 50 ms.
- No regression when index absent (graceful skip).
- Jaccard fallback ensures the feature works on machines without `sentence-transformers`.

**Negative / Trade-offs**
- First cold call pays index-load cost (~50–200 ms depending on corpus size).
- Jaccard fallback has lower recall than embeddings; acceptable for bootstrapping.
- Adds ~1 000 tokens to agent context per call; offset by relevance (removes generic noise).

## Alternatives Considered

| Alternative | Reason Rejected |
|---|---|
| Keyword matching in bash | No semantic coverage; "throttle" misses "rate limiter" |
| Always inject all ADRs | Token budget exceeded; ~96 ADRs × ~500 tokens each = 48 K tokens |
| Orchestrator-manual curation | Requires human attention per task; defeats automation goal |

## Implementation

- `lib/context_injector.py` — Python helper (symlinked from packages)
- `hooks/query-tailored-context-inject.sh` — PreToolUse:Agent hook
- Registered in `scripts/apply-efficiency-profile.sh` PreToolUse:Agent group
- Tests: `tests/integration/test_query_tailored_context.py` (5 scenarios)

## Metrics

Logged to `.cognitive-os/metrics/query-tailored-inject.jsonl`:
- `task_hash`, `match_count`, `top_score`, `fallback_used`, `cache_hit`, `latency_ms`
