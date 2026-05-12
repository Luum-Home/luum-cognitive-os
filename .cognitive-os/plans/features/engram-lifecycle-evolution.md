# Feature Plan: Engram Lifecycle Evolution

**Status**: Phases 1, 2, 3 SHIPPED 2026-04-27. Phase 4 manual Obsidian export implemented 2026-05-05; no automatic Stop hook is registered. See "Honest Limitations" in the ADR before assuming behaviour.
**Date**: 2026-04-27 (created), 2026-04-27 (Phases 1–3 implemented)
**ADR**: [`docs/02-Decisions/adrs/ADR-071-engram-lifecycle-evolution.md`](../../docs/02-Decisions/adrs/ADR-071-engram-lifecycle-evolution.md)
**Research**: [`docs/03-PoCs/research/llm-wiki-v2-engram-evolution-2026-04-27.md`](../../docs/03-PoCs/research/llm-wiki-v2-engram-evolution-2026-04-27.md)

---

## Goal

Extend engram with memory lifecycle — confidence scoring, Ebbinghaus decay, automated crystallization, and graph traversal queries — without modifying the engram binary. All lifecycle state is encoded as a structured trailer in observation `content`; a Python wrapper layer (`lib/engram_lifecycle.py`) parses, applies, and maintains it.

The system's memory must distinguish a pattern confirmed twelve times from one seen once, and a 2-year-old ADR about a deprecated dependency from a 2-week-old bugfix. Without lifecycle, retrieval ranking is a proxy for text relevance alone; with lifecycle, it reflects actual epistemic state.

---

## Phase 1: Confidence + decay (this sprint)

### Scope

Phase 1 introduces the trailer schema, decay functions, ranking formula, and reinforcement-on-access hook. No crystallization, no graph traversal.

### Files to create

| File | Purpose |
|---|---|
| `lib/engram_lifecycle.py` | Core wrapper: `save()`, `search()`, `reinforce()`, `_parse_trailer()`, `_apply_decay()`, `build_content_with_trailer()`, `adjusted_score()` |
| `tests/unit/test_engram_lifecycle.py` | Unit tests (see test list below) |
| `hooks/engram-reinforce-on-access.sh` | PostToolUse hook: bumps reinforcement\_count + updates last\_reinforced on mem\_search and mem\_get\_observation events |

### `lib/engram_lifecycle.py` — interface contract

```python
class EngramLifecycle:
    DECAY_TAU = {
        "architecture": 365,
        "decision": 180,
        "pattern": 180,
        "discovery": 90,
        "bugfix": 60,
        "manual": 90,
    }
    ALPHA = 0.3   # lifecycle weight in ranking formula
    BETA = 0.15   # confidence increment per reinforcement

    def save(self, title, content, type_, topic_key, project, **kwargs) -> dict
    def search(self, query, project=None, limit=10, lifecycle_weight=True) -> list[dict]
    def reinforce(self, observation_id: str) -> bool
    def _parse_trailer(self, content: str) -> dict | None
    def _apply_decay(self, trailer: dict) -> float
    def build_content_with_trailer(self, content: str, decay_class: str) -> str
    def default_trailer(self) -> dict
    def _decay_class_for_type(self, type_: str) -> str

def decay_retention(t_days: float, tau: float) -> float:
    """R(t) = exp(-t / tau). Returns value in (0, 1]."""

def reinforce_confidence(current: float, beta: float = 0.15) -> float:
    """confidence_new = confidence_old + (1 - confidence_old) * beta"""

def adjusted_score(base_score: float, confidence: float, retention: float, alpha: float = 0.3) -> float:
    """adjusted = base * (1 - alpha) + confidence * retention * alpha. Bounded [0, 1]."""
```

### `tests/unit/test_engram_lifecycle.py` — test list

- `test_trailer_round_trip` — `build_content_with_trailer` + `_parse_trailer` returns identical fields
- `test_trailer_missing_returns_none` — content with no `<engram-lifecycle>` block returns `None`
- `test_trailer_malformed_returns_none` — truncated or invalid JSON in trailer returns `None` without raising
- `test_decay_at_zero_days_is_one` — `decay_retention(0, tau)` == 1.0 for all tau values
- `test_decay_monotonically_decreasing` — `R(0) > R(30) > R(90) > R(365)` for every decay class
- `test_decay_bounds_never_negative` — `decay_retention(t, tau) > 0` for t in [0, 3650]
- `test_reinforcement_increases_confidence` — each call to `reinforce_confidence` increases value
- `test_reinforcement_never_reaches_one` — after 50 reinforcements, confidence < 1.0
- `test_reinforcement_starts_from_zero_point_five` — fresh observation converges correctly
- `test_adjusted_score_bounded` — 1000 random inputs always yield score in [0.0, 1.0]
- `test_adjusted_score_alpha_zero_equals_base` — when alpha=0, adjusted\_score == base\_score
- `test_adjusted_score_alpha_one_equals_confidence_times_retention` — when alpha=1
- `test_decay_class_mapping_from_type` — `bugfix` → `bugfix`, `architecture` → `architecture`, `unknown_type` → `manual`
- `test_save_appends_trailer` — `save()` output content contains `<engram-lifecycle>` block
- `test_search_re_ranks_newer_over_older` — two mock results with identical base\_score but different last\_reinforced; newer one ranks higher
- `test_search_without_lifecycle_weight_returns_base_order` — `lifecycle_weight=False` bypasses re-ranking
- `test_reinforce_updates_last_reinforced` — `reinforce()` updates `last_reinforced` and increments count
- `test_reinforce_nonexistent_id_returns_false` — graceful failure, no exception

### `hooks/engram-reinforce-on-access.sh` — behavior

- Event: `PostToolUse`
- Matcher: tools matching `mem_search` or `mem_get_observation`
- Reads observation IDs from tool output JSON
- Calls `python3 lib/engram_lifecycle.py reinforce <id>` for each hit
- Exits 0 always (advisory; reinforcement failure does not block the tool call)
- Logs to `.cognitive-os/metrics/engram-reinforcement.jsonl`
- Named kebab-case per `rules/bash-naming.md`

### Definition of Done — Phase 1

- [x] `lib/engram_lifecycle.py` exists and implements the full interface contract
- [x] `tests/unit/test_engram_lifecycle.py` contains all 18+ tests (expanded to cover HTTP reinforce path)
- [x] `python3 -m pytest tests/unit/test_engram_lifecycle.py -v` passes with 0 failures
- [x] `hooks/engram-reinforce-on-access.sh` exists and is registered in `.claude/settings.json` under PostToolUse
- [x] No TODO/FIXME/HACK comments in committed code (per `rules/agent-quality.md`)
- [x] No stub implementations (no `pass`, no `raise NotImplementedError`)
- [x] `lib/engram_lifecycle.py` uses snake\_case filename (per `rules/python-naming.md`)
- [x] `hooks/engram-reinforce-on-access.sh` uses kebab-case filename (per `rules/bash-naming.md`)
- [x] ADR-071 Verification commands pass (see `docs/02-Decisions/adrs/ADR-071-engram-lifecycle-evolution.md`)
- [x] **reinforce() works in production** (caveat from Phase 1 commit d48dcb8 corrected — HTTP API at port 7437 discovered and wired in, 2026-04-27)

### Phase 1 Correction — 2026-04-27

The Phase 1 commit (d48dcb8) noted a caveat: "reinforce() returns False in production until engram CLI exposes get/update". This was **false**. The engram daemon exposes a complete HTTP REST API including `GET /observations/<id>` and `PATCH /observations/<id>`. The `reinforce()` method was updated in Wave 3a to use these endpoints via `lib/engram_http_client.py`.

Data access paths as of Wave 3a:
- **Save**: `engram save` CLI → `engram_client.save_observation()` (unchanged)
- **Search**: `engram search` CLI → `engram_client.search_observations()` (unchanged)
- **Fetch by ID**: HTTP `GET /observations/<id>` → `engram_http_client.get_observation()` (new)
- **Update in-place**: HTTP `PATCH /observations/<id>` → `engram_http_client.update_observation()` (new)

The re-save workaround (duplicate observations under new IDs) has been removed from `reinforce()`.

A safety rule was ratified simultaneously: `rules/engram-api-safety.md` — never mutate the production daemon for exploration; use a sandboxed daemon on an alternate port.

---

## Phase 2: Crystallization pipeline (sketch)

### Concept

When N≥5 observations share the same `topic_key`, trigger automatic consolidation: synthesize a digest using an LLM call, save as a new observation with `type=pattern`, elevated confidence (0.85 initial), and trailer field `crystallized: true`. The constituent observations are updated via `mem_judge` with relation `supersedes` pointing to the new digest.

### Files to create (Phase 2, not yet)

| File | Purpose |
|---|---|
| `lib/engram_crystallizer.py` | Count observations per topic\_key; trigger synthesis; call LLM; save digest |
| `hooks/engram-crystallize-on-session-end.sh` | Stop hook: triggers crystallizer on session end |
| `tests/unit/test_engram_crystallizer.py` | Unit tests for count trigger, LLM synthesis stub, digest format, supersession edges |

### Trigger conditions (to be refined)

- N≥5 observations with same `topic_key` within 30 days, OR
- N≥10 total observations on same `topic_key` regardless of age, OR
- Manual: `mem_crystallize <topic_key>` command

### Definition of Done — Phase 2

- [x] `lib/engram_crystallizer.py` exists with full `EngramCrystallizer` API
- [x] `hooks/engram-crystallize-on-session-end.sh` exists (Stop hook, kebab-case)
- [x] Hook registered in `scripts/apply-efficiency-profile.sh` (Stop group, async)
- [x] Hook referenced in `scripts/set-security-profile.sh` (minimal + standard Stop summaries)
- [x] `tests/unit/test_engram_crystallizer.py` — 19 tests, all pass
- [x] `tests/e2e/test_engram_lifecycle_e2e.py` — 4 new Phase 2 e2e tests pass
- [x] `lib/engram_http_client.py` extended with `get_recent()` (GET /observations/recent)
- [x] No LLM call in v1 crystallization — deterministic synthesis only
- [x] Idempotence guard: duplicate digests not created on repeated runs
- [x] No TODO/FIXME/HACK in committed code
- [x] ADR-071 addendum updated to reflect Phase 2 shipped

---

## Phase 3: Graph traversal in queries (sketch)

### Concept

Extend `lib/engram_lifecycle.py` search to walk `mem_judge` edges after initial BM25+vector results. For each hit, fetch its outgoing edges (supersedes, related, compatible), add the connected observation IDs to the candidate pool, score them, and merge into the ranked result set. Traversal depth capped at 2 hops to bound combinatorial growth.

### Files to create (Phase 3, not yet)

| File | Purpose |
|---|---|
| `lib/engram_graph_walker.py` | BFS over `mem_judge` edges with depth limit; deduplication; score merging |
| `tests/unit/test_engram_graph_walker.py` | Unit tests for BFS, depth limit, deduplication, graph+lifecycle score fusion |

### Graph contribution weight

```
final_score = lifecycle_score × (1 − α_graph) + graph_boost × α_graph
```

Default `α_graph = 0.2`. Graph-connected observations that did not appear in the initial search get a base boost of 0.3 before lifecycle adjustment.

### Definition of Done — Phase 3

- [x] `lib/engram_graph_walker.py` exists with full `EngramGraphWalker` API
- [x] `tests/unit/test_engram_graph_walker.py` — 13 tests, all pass
- [x] `tests/e2e/test_engram_lifecycle_e2e.py` — 5 new Phase 3 e2e tests pass
- [x] SQLite opened read-only via `file:...?mode=ro` URI — no write attempts
- [x] BFS depth limit enforced; rejected relations excluded
- [x] `EngramLifecycle.search()` accepts `graph_walk=True` kwarg (default OFF)
- [x] `memory_relations` not-in-HTTP-API caveat documented in ADR addendum
- [x] No TODO/FIXME/HACK in committed code
- [x] ADR-071 addendum updated to reflect Phase 3 shipped

---

## Phase 4 (optional): Obsidian export (manual slice shipped)

### Concept

A read-only export layer that renders engram observations as Obsidian Markdown with wikilinks derived from `mem_judge` edges. One `.md` file per observation, named by `topic_key` with `/` replaced by `-`. Wikilinks generated from typed edges: `[[target-note]]` with edge type as link text prefix. No writes from Obsidian back to engram — the vault is a human-readable audit layer only.

**Status**: Manual export slice shipped 2026-05-05 after an explicit operator request. Automation remains deferred until the manual proof path passes against a real vault.

### Files created

| File | Purpose |
|---|---|
| `lib/engram_obsidian_exporter.py` | Lifecycle-aware exporter from Engram observations + typed relations to Obsidian Markdown |
| `scripts/export-engram-to-obsidian.sh` | Manual wrapper; dry-run by default; `--vault` required; `--write` required for mutation |
| `tests/unit/test_engram_obsidian_exporter.py` | Unit coverage for dry-run, write, lifecycle frontmatter, relation wikilinks, rejected-relation skip, since filter, and manifest idempotence |
| `docs/09-Quality/manual-tests/engram-obsidian-export.md` | Human proof path before enabling any automation |

### Definition of Done — Phase 4 manual slice

- [x] `lib/engram_obsidian_exporter.py` exists and never writes to Engram.
- [x] `scripts/export-engram-to-obsidian.sh` requires explicit `--vault`.
- [x] Dry-run is default; `--write` is required before files are created.
- [x] Markdown frontmatter includes Engram identity plus lifecycle trailer fields when present.
- [x] Typed accepted relations become Obsidian wikilinks; rejected relations are excluded.
- [x] Incremental manifest skips unchanged files; `--force` rewrites.
- [x] No Stop hook or automatic export is registered.

---

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Engram upstream binary update breaks trailer-in-content assumption | Low (v1.14.5 stable; content is opaque to engram) | Pin engram version in `cognitive-os.yaml`; add integration test that round-trips content with trailer through engram MCP call |
| Reinforcement hook fires too frequently (automated re-reads create noise) | Medium — automated hooks can read the same observation many times | Add deduplication: skip reinforcement if `last_reinforced` was within the last 60 seconds for the same observation ID |
| α=0.3 and β=0.15 are wrong calibration for this system | Unknown until production | Log pre/post scores to `.cognitive-os/metrics/engram-lifecycle-scores.jsonl`; run `/model-optimizer`-style analysis after 2 weeks |
| Cold-start period: observations without trailer get no lifecycle signal | Certain — all existing observations predate Phase 1 | Fallback to defaults (confidence=0.5, decay\_class=manual); system self-corrects as observations are accessed and reinforced |
| Performance overhead at scale (>1000 observations in search result pool) | Low currently, watch as corpus grows | Profile at 500, 1000, 5000 obs; add `max_rerank_candidates` config option to bypass re-ranking when pool exceeds threshold |
