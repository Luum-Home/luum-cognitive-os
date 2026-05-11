---
title: "holaOS Annex A — Memory subsystem comparison"
date: 2026-05-10
annex: A
parent: holaos-comparison-2026-05-10.md
scope: research-only
license_constraint: "BSL-like — pattern-only adoption, clean-room rewrite required"
---

# Annex A — Memory: holaOS vs luum-agent-os

Deep code-to-code comparison of the memory subsystem. Three feature areas were
selected from the top-10 in the parent comparison:

1. **Typed memory governance** (freshness/verification policy by memory type)
2. **Turn-memory writeback extractor** (proactive durable-memory extraction
   from conversation turns)
3. **Embedding-based recall** (vector index over durable memories with
   scope-bucketed backfill worker)

Source roots (anonymised):

- holaOS: `<external-snapshot>/runtime/api-server/src/`
- luum:   `<repo-root>/` (this repository)

License framing (per parent doc and the task brief): all holaOS quotes below are
inspected as *ideas / patterns*, not as code to be copied. Any adoption plan in
this annex specifies a clean-room rewrite owned by luum, with new file paths and
new identifiers.

---

## Surface map

### holaOS memory files (raw LOC)

```
memory-governance.ts                144
memory-recall-index.ts              305
memory-recall-manifest.ts         1,176
memory-writeback-extractor.ts       173
turn-memory-writeback.ts          1,453
memory-capture-views.ts             145
memory-embedding-index.ts           208
memory-model-client.ts              732
recall-embedding-backfill-worker.ts 486
recall-embedding-model.ts           226
memory-recall.ts                    149
memory.ts                           647
user-memory-proposals.ts            263
─────────────────────────────────
total                            ~6,107
```

A relatively compact, well-typed surface. Storage is `RuntimeStateStore`
(SQLite + optional vector index via `sqlite-vec`-like API surface).

### luum memory surface

Python-first, dual-layer (Engram CLI + SQLite FTS5 + lifecycle wrapper):

| File | LOC | Role |
|---|---:|---|
| `lib/engram_client.py` | 198 | Trusted internal CRUD wrapper around the Engram CLI/HTTP. |
| `lib/safe_engram.py` | 216 | Untrusted-content write path (MemoryScanner gate). |
| `lib/engram_http_client.py` | — | Local engramd HTTP client. |
| `lib/engram_lifecycle.py` | 758 | Confidence / Ebbinghaus decay / reinforcement trailer (ADR-071). |
| `lib/engram_wave2_schema.py` | 166 | Additive bitemporal columns (`valid_from`, `valid_to`, `memory_class`, `source_episode`). |
| `lib/engram_crystallizer.py` | 438 | Session-end summarisation of working memory into long-term observations. |
| `lib/engram_graph_walker.py` | 507 | Relation traversal (`supersedes`, `related`, …). |
| `lib/memory_manager.py` | 626 | High-level memory provider for hooks / orchestrator. |
| `lib/memory_retriever.py` | 264 | Hybrid FTS5 + Jaccard reranking. |
| `lib/memory_decay.py` | 147 | Decay computations. |
| `lib/memory_first.py` | 96 | "Check cache before searching" enforcement. |
| `lib/memory.py` | 87 | Thin orchestrator-facing facade. |
| `lib/memory_scanner.py` | — | PII / secrets / confidentiality scanner. |
| `lib/memory_retrieval_benchmark.py` | — | Benchmark harness. |
| `lib/prompt_classifier.py` | (excerpted) | Decides which user prompts to persist. |
| `hooks/user-prompt-capture.sh` | — | UserPromptSubmit -> `mem_save_prompt` (via `prompt_classifier`). |
| `hooks/conversation-capture.sh` | — | Session-end transcript capture. |
| `hooks/skill-post-execution-analysis.sh` | 242 | PostToolUse Agent — propose-only skill evolution (no proactive `mem_save`). |
| `hooks/engram-reinforce-on-access.sh` | 163 | Reinforcement counter on observation access. |
| `hooks/engram-crystallize-on-session-end.sh` | 59 | Trigger crystalliser at Stop. |
| `hooks/memory-prefetch.sh` | 67 | Pre-warm cache for agent launches. |
| `packages/recall-search/lib/cognee_client.py` | — | Optional Cognee KG semantic search (off by default). |

The luum design is type-tag-light but lifecycle-heavy: a single observation
record with a JSON trailer for lifecycle metadata, decay classes derived from
the engram `type` field, and lifecycle wrapper that reranks results.

---

## Feature 1 — Typed memory governance

### holaOS pattern

`memory-governance.ts:25-68` defines a closed enum of memory types with
explicit per-type policy:

> `MEMORY_GOVERNANCE_RULES: Record<MemoryEntryType, MemoryGovernanceRule>`
> — six types: `preference`, `identity`, `fact`, `procedure`, `blocker`,
> `reference`. Each carries `verificationPolicy` (`none | check_before_use |
> must_reconfirm`), `stalenessPolicy` (`stable | workspace_sensitive |
> time_sensitive`), `staleAfterSeconds`, and a `recallBoost` integer.

`memory-governance.ts:83-118` derives a runtime freshness state at query time:

> `assessMemoryFreshness(entry, nowIso)` -> `{ state: "stable"|"fresh"|"stale",
> note: string|null }`. Stable types short-circuit. Others compare
> `nowMs - updatedAtMs >= staleAfterSeconds * 1000` and emit a human-readable
> "verify before use" / "stale, reconfirm" note that travels back to the
> prompt as a UI cue.

`memory-recall-index.ts:171-285` then *uses* the governance rules during
ranking — `governance.recallBoost` is the base score, the freshness state
applies penalties (`stale` → `-3`, stale `reference` → filtered), and intent
cues (`hasProcedureCue`, `hasBlockerCue`, …) gate type-specific score
multipliers. The ranking trace is recorded per-result for explainability:

> `reasons: ["base_recall_boost:2", "user_scope_priority",
> "query_intent_boost:6", "title_match:approval", "stale_penalty"]`.

### luum equivalent

luum does **not** type memories at write time. The engram `type` field is a
free-form string (`bugfix | discovery | decision | architecture | pattern |
config | preference | manual | …`) defined by convention — see RULES-COMPACT
#11. It carries no policy.

The closest analogue is `lib/engram_lifecycle.py:63-80`:

> `_DECAY_TAU` (days per class) and `_TYPE_TO_DECAY_CLASS` map the type-string
> to a half-life. Used only inside the lifecycle wrapper, not surfaced at
> query time. Score formula: `0.7 * relevance + 0.3 * (confidence *
> exp(-age/τ))`. There is no `verificationPolicy`, no `stalenessPolicy`, no
> notion of "stale reference filtered", and no per-result `reasons` trace.

`lib/memory_retriever.py:65-145` ranks purely on FTS5+Jaccard with no
type-awareness:

> `combined = fts5_weight * fts5 + jaccard_weight * jaccard` with weights
> 0.6 / 0.4. The retriever does not consult `engram_lifecycle`; the two layers
> are independent code paths.

### Delta

| Aspect | holaOS | luum | Gap |
|---|---|---|---|
| Type-as-policy carrier | Yes (6 enum + rule table) | No (free-form string) | LARGE |
| Freshness state at query time | Yes (`stable/fresh/stale`) | Indirect (decay multiplier) | MEDIUM |
| Verification policy | Yes (3 levels) | None | LARGE |
| Reasons trace per result | Yes (10+ reason strings) | None | MEDIUM |
| Intent cues drive boost | Yes (procedure/blocker/etc.) | No | MEDIUM |
| Stale-reference auto-filter | Yes | No | SMALL |

luum advantages: temporal-graph support via Wave2 schema (`valid_from`/
`valid_to`/`memory_class`/`source_episode`) plus a relation table
(`memory_relations`) and graph walker — holaOS has nothing equivalent.

### Adoption plan — clean-room

**New files** (do not exist today):

- `lib/memory_governance.py` — pure-Python rule table + `assess_freshness()`
  function. Public API:
  ```
  governance_rule_for(memory_type: str) -> GovernanceRule
  assess_freshness(record: dict, now_iso: str | None = None) -> FreshnessAssessment
  ```
  `GovernanceRule` is a frozen dataclass (no inheritance from anything
  holaOS-shaped). Enum names should match luum conventions (`bugfix`,
  `discovery`, … remain; new `preference` and `procedure` types are
  *added*, not renamed).
- `rules/memory-governance.md` — rule documentation (load on
  `[memory-governance]` trigger).
- `tests/unit/test_memory_governance.py` — table-driven test suite.

**Modifications**:

- `lib/memory_retriever.py` — accept an optional `governance` injector; when
  present, multiply by `recall_boost`, subtract stale penalty, attach
  `reasons` to `RetrievalResult`. Add new field `reasons: list[str]`. Default
  `governance=None` keeps current behaviour (backwards compatible).
- `lib/engram_lifecycle.py` — emit `governance.freshness_state` into the JSON
  trailer alongside `confidence`/`decay_class` so downstream callers can read
  it without recomputing.
- `lib/memory.py` — expose freshness note in the orchestrator-facing search
  result so the assistant can surface "verify before use" cues to the user.

**Interface — new public**:

```python
# lib/memory_governance.py (sketch — NOT final code)
@dataclass(frozen=True)
class GovernanceRule:
    memory_type: str
    verification_policy: str          # "none" | "check_before_use" | "must_reconfirm"
    staleness_policy: str             # "stable" | "workspace_sensitive" | "time_sensitive"
    stale_after_seconds: int | None
    recall_boost: int

@dataclass(frozen=True)
class FreshnessAssessment:
    state: str                        # "stable" | "fresh" | "stale"
    note: str | None
```

**License-risk check**: the rule *idea* (enum × policy table) is not
copyrightable; constants and policy strings will use luum vocabulary (e.g.
`workspace_sensitive` may be renamed `project_scoped` to fit luum's
`workspace`→`project` terminology). The freshness algorithm is a one-liner
(`age >= stale_after_seconds * 1000`) — restated, not copied.

**Effort**: ~250 LOC new + ~80 LOC modifications + ~200 LOC tests.
Estimated **1–1.5 person-days**.

---

## Feature 2 — Turn-memory writeback extractor

### holaOS pattern

The system runs a *model-driven* extraction of durable memories every N turns.

`turn-memory-writeback.ts:83-90`:

> Constants: `MODEL_EXTRACTION_INTERVAL_TURNS = 5`,
> `MODEL_EXTRACTION_MIN_CONFIDENCE = 0.82`,
> `MODEL_EXTRACTION_MIN_CONFIDENCE_CORROBORATED = 0.6`,
> `MODEL_EXTRACTION_MIN_EVIDENCE_CHARS = 36`. Extraction triggers on
> `completedTurnCount % 5 === 0`.

`memory-writeback-extractor.ts:109-172` is the worker. It prompts a JSON-mode
LLM with the user instruction, recent user messages, recent turn summaries,
and the latest assistant text, and demands a strict-JSON shape:

> ```
> {"memories":[{"scope":"workspace|user", "memory_type":"...",
>   "subject_key":"string", "title":"string", "summary":"string",
>   "tags":["string"], "evidence":"string", "confidence":0.0}]}
> ```
> Then filters: drops items without scope/type/title/summary, normalises
> `subject_key` to a kebab-cased slug, caps at 8 candidates, clips `evidence`
> to 260 chars.

The full `turn-memory-writeback.ts` (1,453 LOC) is the persistence
orchestrator: it picks file paths
(`workspace/{ws}/knowledge/{type}/{slug}.md`), upserts the markdown leaf
with YAML frontmatter, updates the per-scope `MEMORY.md` index, and emits a
side-effect log of `changedIndexedScopes`.

`memory-capture-views.ts:37-145` exposes a "captured memory views" projection
returned to debug callers: `runtime_projections`, `durable_indexes`,
`durable_files`, `durable_catalog` (with `counts_by_scope`, `counts_by_type`).
This is the introspection layer holaOS uses to audit what the writeback
extractor produced.

### luum equivalent

luum has **proactive prompt capture** but **no LLM-based turn extractor**.

`hooks/user-prompt-capture.sh` (UserPromptSubmit, async, non-blocking):

> Reads the prompt, runs `lib.safe_engram.scan_only_check` for threats, then
> hands to `lib.prompt_classifier.classify_prompt`. Captures `TASK_REQUEST |
> DECISION | FEEDBACK | CONTEXT`; skips `STATUS_QUERY | NAVIGATION |
> ACKNOWLEDGMENT`. Calls `mem_save_prompt` on capture, logs to
> `.cognitive-os/metrics/prompt-captures.jsonl` always.

`lib/prompt_classifier.py:19-50` is a regex-based classifier (English +
Spanish patterns) returning `ClassificationResult(category, should_capture,
confidence)`. **No LLM call.** It only decides whether to persist the *raw
prompt*; it does not synthesise typed, subject-keyed durable observations
from the conversation arc.

`hooks/skill-post-execution-analysis.sh:1-242` runs PostToolUse on Agent
completions but only writes propose-only skill-evolution artifacts — it never
calls `mem_save`. RULES-COMPACT #11 and the global CLAUDE.md "PROACTIVE SAVE
TRIGGERS" rule mandate that *the assistant* save decisions/discoveries via
`mem_save`, but there is no hook-side automation forcing it.

`lib/engram_crystallizer.py` (438 LOC, fires at session end via
`hooks/engram-crystallize-on-session-end.sh`) is the closest cousin: it
summarises the session into long-term observations. But it is *session-end*
only, not per-turn, and not subject/scope/type aware in the holaOS sense.

### Delta

| Aspect | holaOS | luum | Gap |
|---|---|---|---|
| Per-turn LLM extraction every N turns | Yes | No | LARGE |
| Schema-validated JSON output | Yes (strict 8-field) | N/A | LARGE |
| Subject-key slug normalisation | Yes | No (topic_key is freeform) | MEDIUM |
| Evidence text required for retention | Yes (≥36 chars) | No | MEDIUM |
| Confidence threshold gating | Yes (0.82 / 0.6 corroborated) | Implicit (none) | MEDIUM |
| Per-scope MEMORY.md auto-index | Yes | No (engram is the only index) | SMALL |
| User-prompt capture | No (assistant-driven) | Yes | luum advantage |
| Session-end crystallisation | No | Yes | luum advantage |
| Threat scanning before persist | No | Yes (MemoryScanner) | luum advantage |

luum's design centre-of-gravity is on **session end** + **prompt capture**;
holaOS's is on **mid-turn extraction**. They are complementary, not
competing.

### Adoption plan — clean-room

**New files**:

- `lib/turn_memory_writer.py` — pure-Python coordinator. Public API:
  ```
  should_run_extraction(completed_turn_count: int) -> bool
  build_extraction_context(turn_payload: dict) -> ExtractionContext
  filter_candidates(raw: list[dict], policy: ExtractionPolicy) -> list[Candidate]
  persist_candidates(candidates: list[Candidate], engram: EngramFacade) -> WritebackReport
  ```
  Cadence default = every 5 user turns (configurable in `cognitive-os.yaml`
  under `memory.turn_writeback.interval_turns`).
- `lib/turn_memory_extractor.py` — LLM call (Qwen primary via
  `lib.dispatch` to preserve Claude Max budget per ADR-049). Returns a list
  of `ExtractedCandidate` dataclasses after schema validation.
- `hooks/turn-memory-writeback.sh` — PostToolUse hook (event TBD; likely
  Stop on user turn boundary). Killswitch
  `DISABLE_HOOK_TURN_MEMORY_WRITEBACK=1`. Non-blocking, async, latency
  budget <500ms because the LLM call is dispatched to background.
- `lib/memory_capture_views.py` — projection helper for `/cos-status`-style
  introspection (`durable_catalog` analogue).
- `tests/unit/test_turn_memory_writer.py`,
  `tests/integration/test_turn_memory_writeback.py`.

**Modifications**:

- `cognitive-os.yaml` — add `memory.turn_writeback` block (`enabled`,
  `interval_turns`, `min_confidence`, `min_evidence_chars`, `max_candidates_per_run`).
- `lib/safe_engram.py` — already gates writes; extend `SafeEngramResult` so
  the writeback worker can log scan-rejections without retrying.
- `RULES-COMPACT.md` §11 / `rules/turn-memory-writeback.md` (new) — document
  the new behaviour and the killswitch.

**Interface — new public**:

```python
# lib/turn_memory_writer.py (sketch)
@dataclass(frozen=True)
class ExtractedCandidate:
    scope: str                  # "project" | "user"
    memory_type: str
    subject_key: str            # kebab-cased
    title: str
    summary: str
    tags: tuple[str, ...]
    evidence: str
    confidence: float | None

@dataclass(frozen=True)
class ExtractionPolicy:
    min_confidence: float = 0.82
    min_confidence_corroborated: float = 0.60
    min_evidence_chars: int = 36
    max_candidates: int = 8
```

**License-risk check**: extraction-by-LLM-every-N-turns is a well-known
pattern (cited in the parent doc's prior-art section). The JSON schema names
will use luum vocabulary (`scope=project` not `workspace`). Slug
normalisation is a 5-line regex restated. No literal code transcription.

**Effort**: ~400 LOC new + ~50 LOC modifications + ~300 LOC tests + LLM
prompt iteration. Estimated **3–4 person-days** including prompt tuning
and a small eval harness.

---

## Feature 3 — Embedding-based recall

### holaOS pattern

`memory-embedding-index.ts:13` declares `RECALL_EMBEDDING_DIM = 1536` and
defines `MemoryEmbeddingScopeBucket` = `workspace | preference | identity` —
not all memory types are embedded; only the ones with cross-session relevance.

`memory-embedding-index.ts:99-174` `syncDurableMemoryEmbedding(...)`:

> 1. Skip if no embedding client or store lacks vector index.
> 2. Compute `scopeBucket`; if entry is inactive, delete index row.
> 3. Read markdown leaf, strip frontmatter, build a structured embedding
>    text:
>    ```
>    Title: <t>
>    Type: <t>
>    Summary: <s>
>    Tags: <comma-separated>
>    Excerpt: <first ~480 chars no headings>
>    ```
> 4. Compute SHA-256 fingerprint of that text. If existing row has same
>    fingerprint + model + dim, skip (`skipped_unchanged`).
> 5. Call embedding API (`queryMemoryModelEmbedding`, 7s timeout).
> 6. Upsert `memory_embedding_index` + `replaceMemoryRecallVector` with
>    scope bucket + workspace + memory_type as filterable columns.

`recall-embedding-backfill-worker.ts:16-117`:

> Background worker. Defaults: batch=10, poll=60s, initial delay=30s.
> Won't run while any workspace has an active session run (avoids contention).
> Pages through `listMemoryEntries` 200 at a time, identifies pending
> entries (missing index or stale fingerprint), and processes one batch per
> cycle.

`recall-embedding-model.ts:8-227` is the **provider resolver**: aliases
(`openai_direct`, `holaboss_model_proxy`, `openrouter_direct`, …),
default model per provider (`text-embedding-3-small`,
`openai/text-embedding-3-small`, `null` for anthropic/gemini/ollama —
no embedding endpoint), and openai-compatible-proxy gate.

`memory-recall-manifest.ts:30-34` (1,176 LOC total) drives query-side
recall: `VECTOR_WORKSPACE_LIMIT=12`, `VECTOR_USER_LIMIT=8`,
`VECTOR_PRIMARY_PATHS=8`, `VECTOR_RESERVE_PATHS=4` — separate budgets per
scope bucket. Two-stage plan: (a) plan + candidate selection with 7s
timeout, (b) finalize with 7s timeout, returning `RecallStatus` ∈
`sufficient | expand_once | none`.

### luum equivalent

luum has **no embedding-based recall in active use**. Evidence:

- `lib/memory_retriever.py` uses pure FTS5 + Jaccard (lexical only).
- `lib/engram_wave2_schema.py` adds bitemporal/episode columns but **no
  vector column**.
- `grep -rln "embedding\|vector_search\|similarity" lib/` returns mostly
  `threat_classifier.py`, `context_injector.py`, `reinvention_semantic.py`
  (semantic similarity for *invention prevention*, not memory recall),
  `feedback_consumer.py`.
- `packages/recall-search/lib/cognee_client.py` is an *optional* client to
  an external Cognee KG service (`COGNEE_ENABLED` env-gated, defaults off).
  Not integrated into the default recall pipeline.

luum has **DORMANT/ASPIRATIONAL** capability here — the architecture
(Wave2 schema, lifecycle wrapper, graph walker) is forward-compatible with
vector recall, but no implementation exists.

### Delta

| Aspect | holaOS | luum | Gap |
|---|---|---|---|
| Vector index over durable memories | Yes (sqlite-vec-style, 1536d) | No | LARGE |
| Scope-bucket filtering (workspace/preference/identity) | Yes | No | MEDIUM |
| Fingerprint-based reindex skip | Yes (sha256 of text) | N/A | SMALL (easy add) |
| Backfill worker w/ active-session backoff | Yes | No | MEDIUM |
| Multi-provider embedding selection | Yes (5+ providers) | No | MEDIUM |
| Two-stage recall (plan→finalize) | Yes | No | MEDIUM |
| External KG fallback | No | Yes (Cognee, off-by-default) | luum advantage (latent) |
| Lifecycle decay reranking | No | Yes | luum advantage |

### Adoption plan — clean-room

This is the largest of the three. Recommend splitting into two waves:

#### Wave 1 — schema + sync core

**New files**:

- `lib/memory_embedding_schema.py` — additive engram schema migration
  (analogous to `engram_wave2_schema.py`). Adds:
  - `memory_embedding_index` table: `(memory_id, scope_bucket, memory_type,
    content_fingerprint, model_id, dim, vec_rowid, updated_at)`.
  - Vector storage: either `sqlite-vec` extension table or a separate
    `recall_vectors.db` with `numpy.savez` blobs (decision = ADR; both
    options need a spike).
- `lib/memory_embedding_sync.py` — pure-Python equivalent of
  `syncDurableMemoryEmbedding`. Returns one of `disabled | deleted |
  skipped_unchanged | indexed`.
- `lib/recall_embedding_provider.py` — provider resolver. Reuses
  `lib/dispatch.py` (ADR-049). Defaults: Qwen `text-embedding-v2` (1536d
  compatible) primary, OpenAI `text-embedding-3-small` fallback,
  Voyage/Cohere optional. Anthropic/Gemini/Ollama explicitly disabled.
- `lib/memory_excerpt_builder.py` — markdown-aware excerpt extraction (strip
  frontmatter, drop heading lines, clip to ~480 chars, fingerprint via
  sha256). Reusable for prompt-context building too.
- `tests/unit/test_memory_embedding_sync.py`,
  `tests/integration/test_embedding_backfill.py`.

**Modifications**:

- `scripts/cos-engram-wave2-schema-migrate` — add embedding-schema migration
  call (idempotent, additive, killswitch-protected).
- `cognitive-os.yaml` — `memory.embeddings` block (enabled,
  provider, model, dim, batch_size, poll_seconds, initial_delay_seconds).

#### Wave 2 — backfill worker + recall integration

**New files**:

- `scripts/cos-recall-embedding-backfill` — Python long-running worker (not a
  hook — too heavy). Cron-launched or `make recall-backfill`. Mirrors
  holaOS poll/batch logic with luum's `lib.engram_locks` for coordination.
- `hooks/recall-embedding-on-save.sh` — PostToolUse `mem_save`-style trigger
  (or post-engramd-write event if/when engramd exposes it) to enqueue the
  entry for embedding refresh. Cheap, non-blocking.
- `lib/memory_recall_planner.py` — two-stage planner returning
  `RecallStatus`. Caller is `lib/memory_retriever.py` (extended to accept
  an optional vector-search backend).
- `tests/integration/test_recall_planner.py`.

**Modifications**:

- `lib/memory_retriever.py` — accept optional `vector_search: VectorBackend
  | None = None`. Three-source fusion: FTS5 + Jaccard + vector (RRF-weighted).
- `lib/engram_lifecycle.py` — confirm decay/confidence still rerank *after*
  vector candidates are merged; tests in `tests/unit/test_engram_lifecycle.py`.
- `packages/recall-search/SKILL.md` — document the new default backend and
  retain Cognee as an opt-in alternative.

**Interface — new public**:

```python
# lib/memory_embedding_sync.py (sketch)
SyncStatus = Literal["disabled", "deleted", "skipped_unchanged", "indexed"]

def sync_durable_memory_embedding(
    *,
    observation: dict,
    excerpt_builder: ExcerptBuilder,
    embedding_provider: EmbeddingProvider,
    store: EmbeddingStore,
) -> SyncStatus: ...
```

**License-risk check**: vector recall over scoped buckets with fingerprint
skip is industry-standard (pgvector, sqlite-vec, langchain, llama-index all
do this). Constants like `RECALL_EMBEDDING_DIM=1536` are model-determined,
not authored. Provider-alias table will be rebuilt from public docs
(OpenAI, Voyage, Cohere, Qwen) — no transcription from
`recall-embedding-model.ts`.

**Effort**:

- Wave 1: ~700 LOC new + ~150 LOC modifications + ~500 LOC tests +
  schema-migration smoke test + provider integration. **6–8 person-days.**
- Wave 2: ~500 LOC new + ~200 LOC modifications + ~400 LOC tests + RRF
  weight tuning + benchmark deltas vs FTS5+Jaccard baseline.
  **5–7 person-days.**
- **Total: 11–15 person-days.**

---

## Hallazgos sorpresa

1. **holaOS has no session-end crystallisation.** Despite the per-turn
   writeback, there is no analogue to `lib/engram_crystallizer.py`. The
   architectures pick opposite ends of the conversation timeline. Adopting
   feature 2 should keep the crystalliser; the two are complementary.

2. **holaOS has no relations/graph layer.** `memory_relations` and
   `engram_graph_walker.py` have no holaOS counterpart. luum's
   `supersedes`/`related`/`conflicts_with` model (ADR-071) is strictly more
   expressive than holaOS's flat `memory_entries` table. This is a luum
   moat — preserve it.

3. **holaOS extracts memory types we don't have** (`procedure`, `blocker`).
   `procedure` (workspace-scoped "how to verify/deploy/release") is
   particularly relevant to the operator-runbook content luum already
   maintains in `docs/runbooks/`. Worth considering as a new luum
   memory type even *without* full feature-2 adoption.

4. **`memory-capture-views.ts` is essentially a debug projection.**
   Reverse-engineering it suggests holaOS has an internal "what did the
   memory system actually capture?" diagnostic. luum has nothing equivalent;
   `/cos-status` reports global state but not "what changed in memory this
   session". This is a *small-win* adjacency to feature 2.

5. **Confidence thresholds are dual.** `MIN_CONFIDENCE = 0.82` standalone vs
   `0.60` if corroborated by another signal. The corroboration logic isn't
   visible in the extractor file (lives elsewhere in
   `turn-memory-writeback.ts`), but the *two-tier* gating pattern is worth
   adopting — single thresholds tend to either under- or over-capture.

6. **No vector backend means luum's reinforcement-on-access loop has no
   recall-stage feedback.** `hooks/engram-reinforce-on-access.sh` increments
   reinforcement counters when an observation is *retrieved*. If retrieval
   is lexical-only, semantically-equivalent-but-textually-different queries
   never reinforce the right memory. Adopting feature 3 closes this loop.

7. **MemoryScanner has no holaOS equivalent.** holaOS appears to trust
   memory content blindly. luum's `lib.memory_scanner` + `safe_engram` is
   a security advantage we should not lose when adopting LLM-driven writes
   (feature 2 must route through `safe_engram`).

---

## Recomendación final

| Feature | Decision | Confidence |
|---|---|---|
| 1. Typed memory governance | **Adopt — modified** | High |
| 2. Turn-memory writeback extractor | **Adopt — modified** | Medium |
| 3. Embedding-based recall | **Adopt — modified, phased** | High |

### Rationale

- **Feature 1 (governance)** is the highest leverage:lowest cost item in this
  annex (1–1.5 days). It plugs into existing retrieval and lifecycle code
  without architectural change, and unlocks UI cues ("verify before use")
  that meaningfully improve trust calibration. The "modified" caveats:
  rename `workspace_sensitive` → `project_scoped`, fold our existing
  `bugfix/discovery/decision` types into the rule table rather than
  replacing them.

- **Feature 2 (turn writeback)** delivers proactive durable-memory creation
  but at meaningful complexity cost (3–4 days) and an LLM-cost line item.
  Key modifications: dispatch via `lib.dispatch` (Qwen primary), route writes
  through `safe_engram` (MemoryScanner gate — non-negotiable), make cadence
  configurable, expose killswitch. Confidence is *medium* because the
  marginal value over our existing prompt-capture + session-crystalliser
  needs validation — recommend a 1-sprint A/B (or shadow-mode evaluation
  comparing extractor output vs human-curated `mem_save` calls) before
  committing fully.

- **Feature 3 (embeddings)** is high-value, high-effort. Adopt in two waves:
  ship the schema + sync core first (Wave 1) so future features can rely on
  the index even before recall integration lands. Wave 2 (planner +
  retriever integration) waits on a benchmark showing FTS5+Jaccard+vector
  beats FTS5+Jaccard alone on luum's eval set
  (`lib/memory_retrieval_benchmark.py`). License risk is low — the patterns
  are textbook IR.

### Sequencing recommendation

```
Sprint N+0  : Feature 1 (governance)              [~1.5 d]   ─ standalone
Sprint N+1  : Feature 3 Wave 1 (embedding schema) [~7 d]     ─ unblocks future
Sprint N+2  : Feature 2 (turn writeback)          [~4 d]     ─ depends on safe_engram only
Sprint N+3  : Feature 3 Wave 2 (recall planner)   [~6 d]     ─ benchmark-gated
```

Total budget: ~18–22 person-days across four sprints. None of the work
blocks public-launch readiness (`docs/runbooks/public-launch-day.md`); all
features land behind killswitches and feature-flags so reverting is cheap.

### Out-of-scope (deferred)

- `memory-recall-manifest.ts` (1,176 LOC, two-stage plan/finalize with LLM
  in the loop): re-evaluate after Feature 3 Wave 2 lands.
- `user-memory-proposals.ts` (user-facing memory edit proposals): UX-heavy,
  no luum precedent. Defer until we have a memory-management UI surface.
- `turn-memory-writeback.ts` 1,453-LOC orchestration body: only the
  extractor + cadence are in scope here. The full per-scope-MEMORY.md
  index materialization is *out of scope* because luum delegates indexing
  to engramd / FTS5.

---

*End of Annex A. See parent
[`holaos-comparison-2026-05-10.md`](holaos-comparison-2026-05-10.md) for
cross-feature context and the remaining annexes.*
