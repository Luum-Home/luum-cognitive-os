---
adr: 77
title: Peer-Card Local User-Memory Model (Replaces Honcho)
status: accepted
implementation_status: partial
date: '2026-04-30'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: implementation evidence plus partial/deferred/future signal
partial_remaining: Deferred until a concrete retrieval gap is observed.
remaining_in_scope: true
partial_remaining_basis: explicit body remaining signal
---

# ADR-077: Peer-Card Local User-Memory Model (Replaces Honcho)

**Status**: Accepted
**Date**: 2026-04-30
**Engram topic**: `cos/tier2-hermes-alignment`

---

## Status

Accepted on 2026-05-01. Phase 1 is explicitly **no-embeddings v1 / FTS5-only**. Update cadence and `/peer-card` UX are also resolved below, so implementation is unblocked.

## Context

Hermes uses the Honcho service for AI-native user modeling. Honcho exposes four
capabilities through its `MemoryProvider` interface (source:
`.claude/plugins/hermes-agent/plugins/memory/honcho/__init__.py`, MIT):

| Honcho Tool | Purpose |
|---|---|
| `honcho_profile` | Read/write a **peer card** — a curated list of facts about a user (name, role, preferences, communication style, patterns) |
| `honcho_search` | Semantic search over stored context about a peer; returns raw ranked excerpts |
| `honcho_reasoning` | Dialectic Q&A — asks Honcho's LLM to synthesize an answer from stored memory |
| `honcho_conclude` | Store a durable conclusion derived from a conversation |

COS cannot depend on an external Honcho service because:

1. **No service dependency** — COS is a local-first agent OS. All state must
   survive without internet access and without a running external service.
2. **No Honcho SDK in the COS dependency tree** — adding it would violate the
   project's minimal-dependency philosophy and introduce a managed service
   credential (Honcho API key).
3. **MIT-clean replacement** — the peer-card concept itself (Honcho's `profile`
   tool) is straightforwardly implementable on top of Engram, which COS already
   uses as its persistent memory layer.

Engram topic reference: `hermes-learning-loop-source-map` documents the
broader Hermes alignment strategy. ADR-076 handles SKILL.md alignment. This ADR
covers the user-memory replacement for the subset of Honcho features that COS
needs in the short term (peer cards and search), deferring dialectic reasoning.

## Decision

Implement a **local peer-card model** stored in Engram. The design is:

### Schema

A peer card is an Engram observation of type `peer-card`, scope `personal`,
with a structured JSON body:

```json
{
  "name": "string — display name of the user",
  "role": "string — primary role (e.g., 'solo developer', 'tech lead')",
  "preferences": {
    "key": "value — arbitrary user preferences (e.g., language: 'es', verbosity: 'low')"
  },
  "communication_patterns": [
    "list of strings — observed communication style notes (e.g., 'prefers bullet points')"
  ],
  "domain_expertise": [
    "list of strings — topics the user works with frequently (e.g., 'Go', 'Kafka', 'DDD')"
  ],
  "recent_topics": [
    "rolling window of recent conversation themes — capped at N entries (default 20)"
  ]
}
```

One peer card per user. Topic key: `user/peer-card`. Upserted on update.

### Storage

Engram observation via `mem_save` with:
- `type: peer-card`
- `scope: personal`
- `topic_key: user/peer-card`

Retrieval via `mem_search(query="user/peer-card")` followed by
`mem_get_observation(id)` for full content.

### Retrieval

**Phase 1 (this ADR scope):** FTS5 keyword search via `mem_search`. This covers
`honcho_search` and `honcho_profile` use cases at low cost.

**Phase 2 (deferred):** Embedding-based semantic search for `honcho_reasoning`-
equivalent queries. Deferred until a concrete retrieval gap is observed. If that
gap appears, `sqlite-vec` is the preferred candidate for evaluation because it
aligns with Engram's SQLite substrate without adding a Python ML runtime.

### Update Triggers

The peer card is written by the `user-prompt-capture` hook on one of:
- User explicitly states a preference ("from now on speak in Spanish",
  "I prefer shorter answers").
- A feedback signal is detected (strong positive/negative response to agent
  output style).
- Session-end summary includes new domain expertise or communication pattern
  observations.

Update cadence is event-driven, not per-prompt, to avoid Engram write floods.

### Mapping from Honcho API

| Honcho | Local equivalent |
|---|---|
| `honcho_profile` (read) | `mem_search("user/peer-card")` → `mem_get_observation` |
| `honcho_profile` (write) | `mem_save` with `topic_key: user/peer-card` (upsert) |
| `honcho_search` | `mem_search(query)` scoped to peer-card observations |
| `honcho_reasoning` | **Not implemented in Phase 1** — requires embedding stack |
| `honcho_conclude` | `mem_save` with `type: conclusion`, `scope: personal` |

## Resolved Questions

1. **Embedding model choice for Phase 2 semantic search.**
   Decision: **no-embeddings v1 / FTS5-only**. Phase 1 peer-card retrieval uses
   Engram's existing FTS5-backed `mem_search` only. `sentence-transformers` is
   rejected for v1 because it adds a heavyweight Python ML dependency and model
   download path that weakens local-first portability. `sqlite-vec` remains the
   preferred Phase 2 evaluation candidate if a concrete peer-card retrieval gap
   is demonstrated, because it fits the SQLite-backed Engram storage model better
   than a separate embedding runtime.

2. **Update cadence granularity.**
   Decision: **event-driven writes with session-end consolidation**. The
   `user-prompt-capture` hook may update the peer card immediately only when a
   high-confidence durable signal is present. Session end may consolidate
   repeated medium-confidence signals into one update. The implementation must
   avoid per-prompt writes for ambiguous signals.

   High-confidence immediate-write signals are:
   - Explicit durable user preference commands, such as "from now on",
     "always", "never", "I prefer", or "call me".
   - Direct correction of the peer card or memory, such as "remember that",
     "don't remember that", "that's wrong about me", or "update my
     preference".
   - Stable identity or role facts volunteered by the user, such as name, role,
     organization context, locale, or primary technology/domain focus.

   Medium-confidence signals are buffered for session-end consolidation when
   repeated or reinforced in the same session. Examples: recurring language
   choice, formatting feedback, repeated domain focus, or repeated positive or
   negative feedback about answer style.

   Signals that must not update the peer card are one-off task constraints,
   transient mood, secrets, credentials, regulated identifiers, private keys,
   tokens, or project-specific facts that belong in project memory instead of
   the personal peer card.

3. **User readability and editability of the peer card.**
   Decision: `/peer-card` exposes **read**, **edit**, **forget**, and **explain**
   operations. The UX is free-text first, with the agent translating user intent
   into the structured peer-card JSON schema and showing the proposed patch
   before write. Field-by-field structured editing may be added later, but v1
   should optimize for fast correction and user trust.

   Required behavior:
   - `/peer-card read` prints the current peer card in a human-readable summary
     plus the raw JSON when requested.
   - `/peer-card edit <instruction>` proposes a minimal JSON patch, asks for
     confirmation unless the user explicitly requested immediate update, then
     upserts with `topic_key: user/peer-card`.
   - `/peer-card forget <field-or-fact>` removes a fact or clears a field; if the
     target is ambiguous, the command must ask one concise clarification.
   - `/peer-card explain` shows why each stored preference/fact is believed,
     using provenance when available; if provenance is absent, it must say so.
   - Every write preserves unrelated fields, caps `recent_topics`, and avoids
     storing secrets or project-only details.

## Consequences

**Positive:**
- No external service dependency; peer card persists offline.
- MIT-clean: the concept is generic; implementation is entirely in COS/Engram.
- Reuses the existing Engram API — no new infrastructure.
- FTS5 keyword search covers the majority of `honcho_search` use cases without
  an embedding stack.

**Negative / trade-offs:**
- **No dialectic reasoning (Phase 1):** `honcho_reasoning` synthesizes answers
  from stored memory using an LLM. The local equivalent requires an agent call
  (higher latency, token cost). This is acceptable at Phase 1 scale.
- **No cross-session semantic drift detection:** Honcho tracks how user
  preferences change over time with ML-based drift detection. The local model
  relies on the agent's judgment during updates — less systematic.
- **No semantic embeddings in v1:** FTS5-only retrieval may miss paraphrased or
  conceptually related memories. This is accepted until a concrete peer-card
  retrieval gap justifies Phase 2. If Phase 2 is needed, `sqlite-vec` is the
  preferred candidate for evaluation; `sentence-transformers` remains out of v1
  due to dependency weight and portability risk.
- **Event-driven writes require careful filtering:** High-confidence durable
  signals can be written immediately, but ambiguous behavior is consolidated at
  session end to avoid noisy or creepy memory updates.
- **Free-text editing needs confirmation discipline:** `/peer-card edit` is
  user-friendly, but the agent must show a minimal patch before writing unless
  the user explicitly asks for immediate update.

## Alternatives rejected

- **Depend directly on Honcho**: Rejected because COS must remain local-first
  and cannot require an external service credential for memory continuity.
- **Store peer cards in ad-hoc JSON files only**: Rejected because it would
  bypass Engram search/upsert semantics and duplicate the memory substrate.
- **Implement dialectic reasoning first**: Rejected because peer-card read/write
  and keyword search provide the smallest useful local replacement; reasoning
  should follow only after a concrete retrieval gap is observed.

## Implementation Ready

This ADR is **Accepted** for the Phase 1 architecture. The embedding stack,
update cadence, and `/peer-card` UX decisions are resolved. Implementation can
proceed with:
1. Draft the `user-prompt-capture` hook signal detection spec from the cadence
   rules above.
2. Create the `/peer-card` skill skeleton with `read`, `edit`, `forget`, and
   `explain` operations.
3. Add tests that prove peer-card writes preserve unrelated fields, cap
   `recent_topics`, reject secrets, and use FTS5-only retrieval.

The follow-up should reference this ADR by number.

## Verification

```bash
python3 -m pytest tests/unit/test_safe_engram.py tests/unit/test_memory_retriever.py -q --tb=short
python3 -m pytest tests/audit/test_adr_contracts.py -q --tb=short
```

## References

- Honcho memory plugin source: `.claude/plugins/hermes-agent/plugins/memory/honcho/__init__.py`
- Honcho plugin license: MIT
- Engram memory layer: `lib/engram.py` (or equivalent)
- Engram topic: `cos/tier2-hermes-alignment`
- Broader alignment context: Engram topic `hermes-learning-loop-source-map`
- Related ADR: ADR-076 (SKILL.md frontmatter alignment)
