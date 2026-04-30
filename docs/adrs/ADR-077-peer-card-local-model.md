# ADR-077: Peer-Card Local User-Memory Model (Replaces Honcho)

**Status**: Proposed
**Date**: 2026-04-30
**Engram topic**: `cos/tier2-hermes-alignment`

---

## Status

Proposed.

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
equivalent queries. Deferred until the embedding stack is chosen (see Open
Questions below).

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

## Open Questions (must be answered before implementation)

1. **Embedding model choice for Phase 2 semantic search.**
   Candidates:
   - `sentence-transformers/all-MiniLM-L6-v2` — lightweight, runs locally, 384-dim
   - `sqlite-vec` — vector extension for SQLite; integrates directly with Engram's
     SQLite backend; no Python ML dependency
   - **Skip embeddings in v1** — FTS5-only; simplest; revisit when a concrete
     retrieval failure is observed
   Recommendation: start with FTS5-only, add `sqlite-vec` when a retrieval gap
   is demonstrated. Decision requires a separate RFC.

2. **Update cadence granularity.**
   Options: (a) every prompt where a signal is detected, (b) every N prompts,
   (c) session-end only. Event-driven (option a) is chosen above, but the
   signal detection heuristics need to be specified in the implementation skill.

3. **User readability and editability of the peer card.**
   The peer card holds inferred preferences. Users should be able to inspect and
   correct it. A `/peer-card` slash command should expose `read` and `edit`
   sub-commands. Whether editing is via free-text (agent interprets) or
   structured (field-by-field) is an implementation detail for the follow-up.

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
- **Embedding stack adds a dependency (Phase 2):** `sqlite-vec` or
  `sentence-transformers` must be evaluated before Phase 2 lands. This is
  deferred deliberately.

## Alternatives rejected

- **Depend directly on Honcho**: Rejected because COS must remain local-first
  and cannot require an external service credential for memory continuity.
- **Store peer cards in ad-hoc JSON files only**: Rejected because it would
  bypass Engram search/upsert semantics and duplicate the memory substrate.
- **Implement dialectic reasoning first**: Rejected because peer-card read/write
  and keyword search provide the smallest useful local replacement; reasoning
  should follow only after a concrete retrieval gap is observed.

## Implementation Deferred

This ADR is **Proposed**, not Accepted. Implementation is a follow-up task.
Before implementation:
1. Answer the three open questions above (embed model, cadence, UX).
2. Draft the `user-prompt-capture` hook signal detection spec.
3. Create the `/peer-card` skill skeleton.
4. Accept this ADR.

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
