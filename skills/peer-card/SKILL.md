<!-- SCOPE: os-only -->
---
name: peer-card
description: 'Use when you need this Cognitive OS skill: Local user-memory peer card (read/edit/forget/explain) backed by
  Engram FTS5. ADR-077 Phase 1.; do not use when a narrower skill directly matches the task.'
version: 0.1.0
audience: os
tags:
- memory
- user-model
- engram
- adr-077
platforms:
- claude-code
prerequisites: []
routing_patterns:
- pattern: \bpeer[- ]?card\b
  confidence: 0.95
- pattern: \buser\s+memory\s+card\b
  confidence: 0.8
- pattern: \bpeer\s+(read|edit|forget|explain)\b
  confidence: 0.75
summary_line: Local user-memory peer card (read/edit/forget/explain) backed by Engram FTS5. ADR-077 Phase 1.
routing_intents:
- intent: peer_card_request
  description: User asks to local user-memory peer card (read/edit/forget/explain) backed by Engram FTS5. ADR-077 Phase 1.
  confidence: 0.85
---

# Peer Card

> Local replacement for Honcho's `honcho_profile`. A **single Engram observation
> per user** holding curated facts. Phase 1 is FTS5-only — no embeddings.

## Trigger

Use this skill when the user runs `/peer-card …` or asks to read, edit,
forget, or explain stored personal facts. The skill is also driven indirectly
by `hooks/user-prompt-capture.sh`, which writes high-confidence durable
signals automatically.

## Schema

```json
{
  "name": "string",
  "role": "string",
  "preferences": { "key": "value" },
  "communication_patterns": ["string", ...],
  "domain_expertise": ["string", ...],
  "recent_topics": ["string", ...]
}
```

- **Storage**: Engram observation, `type=peer-card`, `scope=personal`,
  `topic_key=user/peer-card` (upsert).
- **`recent_topics` cap**: **20** entries. Older topics drop FIFO. The cap
  keeps the card bounded and search-relevant; old conversations rarely help
  retrieval and inflate the JSON body.
- **Retrieval**: `mem_search("user/peer-card")` → `mem_get_observation(id)`.
  No embeddings — Phase 1 is FTS5-only (ADR-077 §Resolved Q1).

## Operations

### `read`

Print the current peer card. The agent surfaces a human-readable summary;
on request, also dumps the raw JSON.

```python
from lib.peer_card import read, EngramStore
card = read(EngramStore())
```

### `edit <instruction>`

Translate the user's free-text instruction into a partial JSON patch, **show
the proposed patch**, and only on confirmation apply it via
`lib.peer_card.update(...)`. The update preserves unrelated fields,
deduplicates list entries, caps `recent_topics`, and **rejects any patch that
contains secrets, tokens, private keys, or regulated PII** (the entire patch
is dropped — no partial writes).

```python
from lib.peer_card import update, EngramStore
result = update(EngramStore(), {"preferences": {"language": "es"}})
if result.rejected:
    raise SystemExit(f"refused: {result.rejected}")
```

### `forget <field-or-fact>`

Clear a schema field, drop a single preference key, or remove a literal
string from any list field. If ambiguous, the agent asks one concise
clarification before calling `lib.peer_card.forget(...)`.

### `explain`

Summarize the card and explicitly note that **Phase 1 does not store
provenance**: facts come from explicit user statements or session-end
consolidation. The agent must not fabricate justifications.

## Update cadence (ADR-077 §Resolved Q2)

- **High-confidence (immediate write):** explicit durable preference
  commands (`from now on`, `always`, `never`, `I prefer`, `call me`),
  direct memory corrections (`remember that`, `update my preference`),
  stable identity facts (name, role, locale, primary domain).
- **Medium-confidence (buffered):** recurring style/format feedback,
  repeated language choice. Consolidated at session end, not per-prompt.
- **Never written:** one-off task constraints, transient mood, secrets,
  credentials, regulated identifiers, project-specific facts.

## Implementation pointers

- Library: `lib/peer_card.py` (see module docstring).
- Hook integration: `hooks/user-prompt-capture.sh` calls
  `python3 -m lib.peer_card hook` with the prompt on stdin.
- Tests: `tests/unit/test_peer_card.py`.
- ADR: `docs/02-Decisions/adrs/ADR-077-peer-card-local-model.md`.
