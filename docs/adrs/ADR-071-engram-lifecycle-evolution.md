---
adr: 71
title: Engram Lifecycle Evolution via Wrapper Layer
status: accepted
implementation_status: partial
date: '2026-04-27'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: implementation evidence plus partial/deferred/future signal
partial_remaining: Phases 2–4 are scoped and planned but not implemented until Phase 1 is verified.
remaining_in_scope: true
partial_remaining_basis: explicit body remaining signal
---

# ADR-071 — Engram Lifecycle Evolution via Wrapper Layer

## Status

**Accepted** — 2026-04-27

**Implementation-plan**: `.cognitive-os/plans/features/engram-lifecycle-evolution.md`

## Context

Engram (v1.14.5, third-party Go binary at `<engram-bin>`, exposed via MCP) is the project's persistent memory backend. It provides `mem_save`, `mem_search`, `mem_get_observation`, `mem_judge` (with typed edges: supersedes, conflicts\_with, related, compatible, scoped, not\_conflict), `mem_session_summary`, and `mem_update`. Its observation schema stores `title`, `content`, `type_`, `topic_key`, `project`, and `created_at`.

The schema has no native fields for confidence, decay rate, reinforcement count, or last-reinforced timestamp. As a result, all observations are retrieved with equal weight regardless of age, confirmation count, or whether newer observations have superseded them. A one-year-old ADR about a deprecated dependency competes on equal footing with a two-week-old bugfix about the same module. Observations confirming the same pattern twelve times do not surface before observations seen once.

The LLM Wiki v2 gist (2026) [1] — written by the author of agentmemory and extending Karpathy's original LLM Wiki [2] — crystallizes the industry learning on this failure mode: **the bottleneck for AI memory is not visualization but memory lifecycle**. Specifically: confidence scoring with Ebbinghaus decay, supersession, consolidation tiers (working → episodic → semantic → procedural), and graph traversal as a query strategy. A 38-source research survey conducted 2026-04-27 confirms this diagnosis across the major AI memory frameworks (Mem0, Zep/Graphiti, Cognee, Letta/MemGPT, GraphRAG, HippoRAG, LightRAG).

Full analysis: [`docs/research/llm-wiki-v2-engram-evolution-2026-04-27.md`](../research/llm-wiki-v2-engram-evolution-2026-04-27.md).

The project is in `reconstruction` phase. Patching is not acceptable; the wrapper layer must be complete and test-covered in the same session it is introduced.

## Decision

Extend engram's behavior via a Python wrapper layer (`lib/engram_lifecycle.py`) that encodes lifecycle metadata as a structured trailer in the observation `content` body — a format engram passes through unchanged — and post-processes retrieval results to apply confidence-weighted re-ranking.

Implementation proceeds in four phases. **Phase 1 (this sprint)** covers confidence scoring and Ebbinghaus decay. Phases 2–4 are scoped and planned but not implemented until Phase 1 is verified.

### Schema: lifecycle trailer

Lifecycle metadata is stored as a fenced block at the end of every observation's `content` field:

```
<engram-lifecycle>
{"confidence": 0.5, "last_reinforced": "2026-04-27T15:30:00Z", "reinforcement_count": 0, "decay_class": "decision"}
</engram-lifecycle>
```

Fields:
- `confidence` — float [0.0, 1.0]. Initial value 0.5 for new observations. Increases asymptotically toward 1.0 with each reinforcement.
- `last_reinforced` — ISO-8601 UTC timestamp. Set on save, updated on every access.
- `reinforcement_count` — integer. Incremented on `mem_search` hit and `mem_get_observation` call.
- `decay_class` — string. Determines the retention half-life τ used in the decay function.

The trailer is invisible to humans reading the observation in prose but machine-readable by the wrapper layer.

### Decay classes

| Class | τ (days) | Rationale |
|---|---|---|
| architecture | 365 | Architecture decisions are durable; slow decay preserves them |
| decision | 180 | ADRs and design choices; moderate decay |
| pattern | 180 | Established conventions; same durability as decisions |
| discovery | 90 | Codebase findings and gotchas; moderate decay, still actionable |
| bugfix | 60 | Specific incident reports; decay faster as fixes become stale |
| manual | 90 | Default catch-all for observations not matching above types |

The `decay_class` is derived automatically from the observation's `type_` field on save:
- `type_=architecture` → `decay_class=architecture`
- `type_=decision` → `decay_class=decision`
- `type_=pattern` → `decay_class=pattern`
- `type_=discovery` or `type_=config` → `decay_class=discovery`
- `type_=bugfix` → `decay_class=bugfix`
- all others → `decay_class=manual`

### Ranking formula

When `lib/engram_lifecycle.py` wraps a `mem_search` call, it applies a lifecycle-adjusted score:

```
adjusted_score = base_score × (1 − α) + confidence × R(t) × α
```

Where:
- `base_score` is engram's native relevance score (BM25+vector), normalized to [0, 1]
- `α = 0.3` — lifecycle weight; engram's relevance signal dominates (70%) to preserve recall quality
- `confidence` — the observation's current confidence value
- `R(t) = exp(−t / τ)` — Ebbinghaus retention function; `t` is days since `last_reinforced`, `τ` is the decay class half-life

The formula is bounded: `adjusted_score ∈ [0, 1]` always, because base\_score ∈ [0,1], R(t) ∈ (0,1], confidence ∈ [0,1], and α ∈ [0,1].

### Reinforcement

Every successful `mem_search` hit and every `mem_get_observation` call triggers reinforcement on the accessed observation:

1. `reinforcement_count += 1`
2. `last_reinforced = now()` (resets the decay clock)
3. `confidence_new = confidence_old + (1 − confidence_old) × β` where `β = 0.15`

The asymptotic formula ensures confidence never reaches exactly 1.0 (no observation becomes "perfectly certain"), and converges toward ~0.98 after 20+ reinforcements.

Reinforcement is implemented via hook `hooks/engram-reinforce-on-access.sh` (PostToolUse, matching `mem_search` and `mem_get_observation` tool events). The hook calls `lib/engram_lifecycle.py reinforce <observation_id>`.

### Phase roadmap

| Phase | Scope | Status |
|---|---|---|
| 1 | Confidence + decay (`lib/engram_lifecycle.py`, trailer schema, ranking, reinforcement hook) | **Done** (Wave 3a) |
| 2 | Crystallization pipeline (auto-promote N+ observations on same topic\_key → digest → `type=pattern`) | **Done** (Wave 3b) |
| 3 | Graph traversal in queries (walk `memory_relations` SQLite table, 2-hop max, merge into ranked results) | **Done** (Wave 3b) |
| 4 | Obsidian export as human-readable layer (read-only; no writes from Obsidian to engram) | **Manual slice done** (2026-05-05); automation deferred |

Feature plan: [`.cognitive-os/plans/features/engram-lifecycle-evolution.md`](../../.cognitive-os/plans/features/engram-lifecycle-evolution.md).

## Consequences

### Positive

- Search ranking reflects actual epistemic state: frequently confirmed, recently accessed observations surface above stale ones with equal text relevance.
- Agents can report calibrated confidence ("I'm fairly confident about X — reinforcement count 8, last confirmed 3 days ago") instead of treating all memory as equally reliable.
- Reinforcement on access creates a self-reinforcing signal: observations the system actually uses become more visible over time.
- The trailer is engram-transparent: no engram binary modification required, no upstream dependency pinning.
- Fully reversible: removing the wrapper layer reverts to current behavior with no data loss. Trailers are inert prose to engram.

### Negative

- Each search call through the wrapper incurs ~10ms additional overhead for trailer parsing, decay computation, and re-ranking. Acceptable for interactive use; may accumulate in high-frequency automated hooks.
- Observation `content` bodies have a trailer block appended, which is visible if a human reads the raw observation in the engram CLI. Minor visual noise; does not break engram's display or search.
- Observations saved before Phase 1 ships have no trailer. The wrapper must handle missing-trailer gracefully (treat as confidence=0.5, decay\_class=manual, last\_reinforced=created\_at). This "cold start" period means re-ranking has limited effect until observations are accessed and reinforced.
- `β = 0.15` and `α = 0.3` are initial calibration values. They are not empirically derived from this system's usage patterns. They will need tuning after Phase 1 is in production.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Obsidian as primary memory backend | Markdown breaks at 500+ notes; no project-scoping; untyped wikilinks have no semantic weight; no confidence/decay mechanism; visualization is not the bottleneck (LLM Wiki v2 gist §"The missing layer: memory lifecycle") |
| Migrate to Mem0 | Full migration of all existing observations + rewrite of 145+ skills calling engram tools; 4–8 weeks; marginal benefit over extending engram since engram already provides BM25+vector+typed edges |
| Migrate to Zep/Graphiti | Strong temporal graph memory, but introduces external network dependency on a system designed to run locally via MCP; same migration cost concern |
| Fork engram to add native lifecycle fields | High cost (Go binary, upstream divergence, maintenance burden); blocks upstream updates; engram is a third-party binary not owned by this project |
| Encode metadata in topic\_key suffixes (e.g. `decision/auth!c=0.85`) | Fragile: breaks on rename; requires all callers to parse suffixes; not readable by engram's native search; violates the separation between routing key and payload |

## Verification

The following commands verify Phase 1 is correctly implemented. Run them after `lib/engram_lifecycle.py` and `tests/unit/test_engram_lifecycle.py` are implemented:

```bash
# 1. Unit tests pass
python3 -m pytest tests/unit/test_engram_lifecycle.py -v

# 2. Trailer round-trip: save an observation, read it back, confirm trailer is present and parseable
python3 -c "
from lib.engram_lifecycle import EngramLifecycle
lc = EngramLifecycle()
content_with_trailer = lc.build_content_with_trailer(
    'original content',
    decay_class='decision'
)
trailer = lc._parse_trailer(content_with_trailer)
assert trailer is not None, 'Trailer not found'
assert trailer['confidence'] == 0.5, f'Expected 0.5, got {trailer[\"confidence\"]}'
assert trailer['decay_class'] == 'decision', 'Wrong decay class'
assert trailer['reinforcement_count'] == 0, 'Expected 0'
print('PASS: trailer round-trip')
"

# 3. Decay function is bounded and monotonically decreasing
python3 -c "
import math
from lib.engram_lifecycle import decay_retention

tau_values = {'architecture': 365, 'decision': 180, 'bugfix': 60}
for cls, tau in tau_values.items():
    r0 = decay_retention(0, tau)
    r30 = decay_retention(30, tau)
    r365 = decay_retention(365, tau)
    assert 0.0 < r365 <= r30 <= r0 <= 1.0, f'Bounds violated for {cls}'
    assert abs(r0 - 1.0) < 1e-9, 'R(0) must be 1.0'
print('PASS: decay bounds and monotonicity')
"

# 4. Reinforcement increases confidence asymptotically, never exceeds 1.0
python3 -c "
from lib.engram_lifecycle import reinforce_confidence
c = 0.5
beta = 0.15
prev = c
for i in range(30):
    c = reinforce_confidence(c, beta)
    assert c > prev, 'Confidence must increase'
    assert c < 1.0, 'Confidence must never reach 1.0'
    prev = c
print(f'PASS: confidence after 30 reinforcements = {c:.4f} (< 1.0)')
"

# 5. Adjusted score is always in [0, 1]
python3 -c "
from lib.engram_lifecycle import adjusted_score
import random
random.seed(42)
for _ in range(1000):
    base = random.random()
    confidence = random.random()
    retention = random.random()
    score = adjusted_score(base, confidence, retention, alpha=0.3)
    assert 0.0 <= score <= 1.0, f'Score out of bounds: {score}'
print('PASS: adjusted_score bounded [0,1] over 1000 random samples')
"

# 6. Missing-trailer fallback: observations without trailer get defaults
python3 -c "
from lib.engram_lifecycle import EngramLifecycle
lc = EngramLifecycle()
trailer = lc._parse_trailer('observation content with no lifecycle block')
assert trailer is None or trailer == lc.default_trailer(), 'Expected None or defaults'
print('PASS: missing-trailer returns None (fallback handled by caller)')
"
```

## Addendum — 2026-04-27: HTTP API discovery + Phase 1 caveat correction

The original Phase 1 commit (d48dcb8) claimed `reinforce()` would return False in production "until engram CLI exposes get/update". This was incorrect. The engram daemon at port 7437 exposes `GET /observations/<id>`, `PATCH /observations/<id>`, `GET /search`, `GET /stats`, and `GET /health`. Phase 1's `reinforce()` was migrated to use HTTP and is fully functional today.

A safety policy was ratified the same day after an accidental overwrite of observation #13283 during API discovery: see `rules/engram-api-safety.md`. Production daemon mutation is restricted to typed clients (`lib/engram_http_client.py`); ad-hoc curl experiments must target a sandboxed daemon (alternate port + temp `ENGRAM_DATA_DIR`).

New files introduced in this addendum:
- `lib/engram_http_client.py` — HTTP wrapper (`is_available`, `get_observation`, `search_observations`, `update_observation`). Falls back to `urllib` when `requests` is not installed.
- `tests/unit/test_engram_http_client.py` — 12+ unit tests with mocked HTTP transport.
- `tests/e2e/test_engram_lifecycle_e2e.py` — 5 e2e tests against a real sandboxed daemon.
- `rules/engram-api-safety.md` — safety policy for production daemon mutation.

`lib/engram_lifecycle.py` `reinforce()` now: checks `engram_http_client.is_available()`, fetches via `get_observation()`, updates the trailer in-memory, and writes back via `update_observation()`. The re-save workaround (which created duplicate observations under new IDs) has been removed.

## Addendum — 2026-04-27: Phase 2 (Crystallization) + Phase 3 (Graph Traversal) shipped

### Phase 2: Crystallization

`lib/engram_crystallizer.py` implements the consolidation pipeline:
- `candidates()` fetches recent observations via `GET /observations/recent` and groups by `topic_key`, using `revision_count` as a proxy for multi-save count (engram deduplicates topic_keys into a single observation).
- `crystallize()` synthesises a deterministic text digest (no LLM call in v1), saves it as a new observation with `type=pattern`, `topic_key=<original>/crystallized`, and a trailer with `crystallized: true`, `confidence: 0.85`, `decay_class: pattern`, and `superseded_obs_ids`.
- `crystallize_all()` iterates all candidates with short-circuit when empty (target: ≤500ms at session end).
- `hooks/engram-crystallize-on-session-end.sh` fires at the Stop event and calls `crystallize_all()` asynchronously.

**Cloud branch finding**: `lib/engram_http_client.get_recent()` was added (GET `/observations/recent`) to support `_search_all()`. The lifecycle trailer survives cloud sync because it lives in the `content` field, which engram stores and returns unchanged.

**Engram deduplication caveat**: engram deduplicates observations with the same `topic_key` into a single observation, incrementing `revision_count` on each save. The crystallizer uses `revision_count` as the effective observation count for threshold evaluation.

### Phase 3: Graph Traversal

`lib/engram_graph_walker.py` implements BFS over the `memory_relations` SQLite table:
- Opens the DB read-only via `sqlite3.connect(f"file:{path}?mode=ro", uri=True)`.
- `walk()` performs BFS up to `max_depth=2` hops, excluding rejected relations and starting nodes.
- `merge_into_results()` re-ranks base results with `final = original * (1 - alpha_graph)` and adds graph-only neighbors at `graph_boost=0.3`.
- `EngramLifecycle.search()` accepts `graph_walk=True` to trigger traversal after initial search.

**`memory_relations` not in HTTP API**: the table is only accessible via the engram MCP server (`mem_judge` tool), not via the HTTP REST API at port 7437. The graph walker reads SQLite directly for compatibility.


## Addendum — 2026-05-05: Phase 4 manual Obsidian export shipped

`lib/engram_obsidian_exporter.py` implements the one-way Engram → Obsidian export layer requested after the follow-up research in `docs/research/obsidian-doc-graph-ai-agent-memory-2026-05-05.md`:

- Reads observations via `lib.engram_http_client.get_recent()` with optional project, limit, and since filters.
- Reads `memory_relations` from SQLite in read-only mode and exports only non-rejected typed relations between exported observations.
- Renders one Markdown file per observation under `Cognitive OS/Engram/` in an explicit vault path.
- Converts lifecycle trailer fields (`confidence`, `last_reinforced`, `reinforcement_count`, `decay_class`, etc.) into YAML frontmatter and strips the raw trailer from the Markdown body.
- Converts accepted typed relations into Obsidian wikilinks in an `## Engram Relations` section.
- Uses a manifest with content digests for incremental writes; `--force` rewrites planned files.

`scripts/export-engram-to-obsidian.sh` is the manual wrapper. It is dry-run by default and requires `--write` before any vault files are mutated. The first real vault proof ran against `$HOME/.cognitive-os/obsidian-vaults/luum-agent-os`; evidence and structural checks live in `docs/manual-tests/engram-obsidian-export.md`.

`hooks/engram-obsidian-export-on-stop.sh` adds the optional automation slice. It is safe to register only because it is gated by `COS_OBSIDIAN_VAULT`: when the variable is unset, the hook exits 0 without exporting; when set, it performs the same one-way export and logs non-blocking metrics. This does not make Obsidian the source of truth and does not create an automatic git commit path.

The vault remains outside the repository by default. `docs/` is the curated, reviewed documentation source; Obsidian is a generated graph/audit view over Engram and selected links to docs. A future repo-local export must use an explicit generated path, sanitization, and manual promotion.

## Honest Limitations (post-implementation, 2026-04-27)

The implementation works end-to-end (89 tests passing: 75 unit + 14 e2e against a real sandboxed engram daemon). What follows is what does **not** work, what is **partial**, and what is **best-effort** — documented so future readers don't inherit false confidence.

### What is partial

1. **Crystallizer uses no LLM.** Synthesis is deterministic concat + dedup of constituent contents, capped at 4000 chars. The output is browsable as a digest but is not a smart summary. Upgrading to an LLM call (via `scripts/orchestrator.py` per ADR-049) is left for a future revision when the heuristic version produces evidence of insufficient signal density. Not aspirational — the current behaviour is what runs.

2. **`mem_judge` supersedes is not written.** Engram's HTTP API does not expose `/relations` writes; the `mem_judge` MCP tool is the only path, and we do not invoke MCP from Python in this implementation. Phase 2 stores `crystallized: true` and `superseded_obs_ids: [...]` in the digest trailer instead. Downstream consumers must read the trailer to know which observations were folded in. The `memory_relations` graph itself does not show the supersedes edge from constituents to digest.

3. **Reinforcement is local-only.** `engram-reinforce-on-access.sh` updates `last_reinforced` and `reinforcement_count` on the local DB. Engram cloud sync replicates the `content` field (trailer included) but does not aggregate reinforcement counters across devices. Two laptops both accessing the same observation reinforce independently; merging across devices is not implemented.

4. **Graph walker reads SQLite directly.** The walker bypasses the HTTP API by opening `~/.engram/engram.db` in read-only mode. This couples the walker to engram's schema. If engram changes the `memory_relations` schema (column rename, type change, table split) the walker will silently return wrong results until updated. Mitigation: read-only mode prevents corruption; the walker fails closed (returns `{}`) if the DB is missing or the schema mismatch causes a SQL error.

5. **Crystallizer uses `revision_count` as the count proxy.** Engram deduplicates observations sharing a `topic_key` into a single row, incrementing `revision_count` per save instead of inserting new rows. The crystallizer threshold (`N≥5 in 30 days` OR `N≥10 total`) reads `revision_count` to know "how many times has this been saved." This is a proxy: it counts saves, not distinct events. A topic that is saved-then-edited 5 times triggers crystallization the same as one saved 5 times by 5 distinct discoveries.

### What is dormant until activated

6. **Hooks are registered but only fire under matching profiles.** `hooks/engram-reinforce-on-access.sh` and `hooks/engram-crystallize-on-session-end.sh` are listed in `scripts/apply-efficiency-profile.sh` and `scripts/set-security-profile.sh`. They activate when the user runs `bash scripts/apply-efficiency-profile.sh default` (or any of the security profiles). In a fresh checkout that has not re-applied a profile, the hooks exist on disk but `.claude/settings.json` does not yet route events to them.

7. **`reinforce()` requires the engram daemon to be running.** If `engram serve` (port 7437) is not up, `reinforce()` returns `False` silently. The hook logs to `.cognitive-os/metrics/lifecycle-reinforcement.jsonl` regardless, so failures are observable. There is no auto-start; the daemon is the user's responsibility.

### What is unvalidated

8. **Threshold tuning is a starting heuristic.** `N≥5 in 30 days` and `N≥10 total` for crystallization, and τ values per decay class (`architecture=365d, decision=180d, pattern=180d, discovery=90d, bugfix=60d, manual=90d`), are defensible defaults but not empirically calibrated. Phase 2 logging should accumulate data to retune these.

9. **Cloud sync compat is structurally sound but not e2e-tested.** The trailer lives in `content` which engram cloud sync round-trips unchanged (verified by reading engram's source). No e2e test exercises a sync chunk through the lifecycle wrapper.

10. **Trailer parse is best-effort.** If a user manually edits an observation and corrupts the `<engram-lifecycle>{...}</engram-lifecycle>` JSON, `_parse_trailer()` returns `None` and the wrapper falls back to default-trailer behaviour (confidence=0.5, retention=1.0). The corrupted observation is not penalised but its lifecycle state is silently lost. There is no repair tool.

### Scope decisions, deliberately

11. **Obsidian export is opt-in and one-way.** Phase 4 now has a one-way exporter and an optional Stop hook. The hook does nothing unless `COS_OBSIDIAN_VAULT` is set, the vault path remains explicit, the manual command is dry-run by default, and Obsidian remains a human-readable graph/audit layer rather than the source of truth. No automatic commit path is allowed.

12. **No fork of engram.** The integration uses engram as-is. If a future need requires `mem_judge` write access from Python, the path is to (a) spawn engram in MCP mode and pipe stdin, or (b) propose an HTTP endpoint upstream — not to fork the binary.

## Future Work — Conditional, Concrete

These are not "someday" items. Each has a **trigger** (the observable signal that justifies the work), an **action** (concrete first step), and an **estimated cost**. None of them block the v0.20.0 release; all of them have a defensible reason to be deferred today.

### F1. Crystallizer LLM upgrade (heuristic → real synthesis)
- **Trigger**: heuristic digests in `.cognitive-os/metrics/crystallization-events.jsonl` are reviewed and judged "low signal" by the operator (e.g. constituent contents are paraphrases of each other, dedup leaves a list rather than a paragraph). Expected at 30+ crystallized digests.
- **Action**: route `EngramCrystallizer.synthesize_content()` through `scripts/orchestrator.py` per ADR-049 (LLM dispatch). Use Sonnet (cheap, sufficient for summarization). Keep heuristic path as fallback when LLM is unavailable.
- **Cost**: 2–4 hours. Single-file change in `lib/engram_crystallizer.py` plus a fixture in unit tests.
- **Risk**: cost + latency at session-end. Mitigate by gating on N≥20 constituents (the threshold where heuristic visibly fails).

### F2. `mem_judge` supersedes writes
- **Trigger**: engram exposes `POST /relations` over HTTP, OR a downstream consumer (other than the trailer-aware crystallizer) needs the supersedes edge to be queryable through `mem_judge`.
- **Action (option A — preferred)**: replace the trailer-only flag with an actual relation row by calling the new HTTP endpoint after crystallize() saves the digest. **Action (option B — fallback)**: spawn `engram mcp --tools=admin` in subprocess, pipe a `mem_judge` JSON-RPC request via stdin. B is doable today but adds 200ms per crystallize call and a long-lived subprocess.
- **Cost**: 1 hour for option A (when endpoint exists), 4 hours for option B (subprocess management).
- **Risk**: option B couples to engram's MCP protocol version.

### F3. Cross-device reinforcement aggregation
- **Trigger**: two operators (or two laptops of the same operator) both reading the same `topic_key` and the in-cloud `reinforcement_count` not summing. Observable when comparing `lifecycle-reinforcement.jsonl` across devices and the trailer in cloud-synced obs.
- **Action**: extend `reinforce()` to PATCH the trailer with `reinforcement_count = max(local, remote) + 1` instead of `local + 1`. Requires a fetch-then-update pattern (already what `reinforce()` does — small change to the merge math).
- **Cost**: 1–2 hours, plus an e2e test that simulates two HTTP clients hitting the same observation.
- **Risk**: lost-update race if two devices reinforce simultaneously. Mitigation: engram's PATCH is last-write-wins; idempotency key based on `(observation_id, device_id, timestamp)` is overkill for the dev case.

### F4. Threshold calibration with real data
- **Trigger**: ≥4 weeks of `crystallization-events.jsonl` and `lifecycle-reinforcement.jsonl` accumulated, or ≥100 crystallized digests, whichever comes first.
- **Action**: write a one-off analysis script (`scripts/calibrate_engram_lifecycle.py`) that reads the JSONL logs and answers: (a) what fraction of crystallized digests get queried in the next 30 days? (signal that the threshold is right), (b) what is the half-life of "discovery"-type observations measured by access? (validates τ=90d), (c) histogram of `revision_count` distribution per topic_key (validates N≥5/N≥10). Re-tune the `DECAY_TAU` and `THRESHOLD_*` constants in `lib/engram_lifecycle.py` and `lib/engram_crystallizer.py` based on findings. Open a follow-up ADR if the changes are significant.
- **Cost**: 4–6 hours including the analysis + retune + tests.
- **Risk**: re-tuning silently changes ranking for everyone — must be a tracked ADR change with the empirical justification.

### F5. Obsidian export automation
- **Trigger**: `docs/manual-tests/engram-obsidian-export.md` passes against a real vault and the operator wants recurring export.
- **Action**: add an opt-in Stop hook or scheduled wrapper around `scripts/export-engram-to-obsidian.sh` that only runs when `COS_OBSIDIAN_VAULT` is set. Keep dry-run/manual mode as the default operator path.
- **Cost**: 2–3 hours after manual proof, mostly hook registration and metrics.
- **Risk**: vault path discovery and unwanted local file churn. Mitigate with explicit env var, project filter, incremental manifest, and no default automation.

### F6. Cloud sync e2e test
- **Trigger**: any cross-device feature (F3) lands, OR a sync-related bug is reported.
- **Action**: extend `tests/e2e/test_engram_lifecycle_e2e.py` with a fixture that runs `engram cloud serve` on a temp port (auth disabled via `ENGRAM_CLOUD_INSECURE_NO_AUTH=1`), enrolls a project, saves obs on instance A, runs `engram sync --import` on instance B, asserts the trailer round-trips intact.
- **Cost**: 3–4 hours. The fixture machinery is the bulk of the work; the assertion is one line.
- **Risk**: cloud serve has more env-var prerequisites than the regular daemon — the test may be skipped in CI if those aren't satisfied. Acceptable; it would still cover the local two-instance case.

### What is explicitly NOT future work

- **Forking engram**. Already rejected (Honest Limitations §12).
- **Migrating to Mem0/Zep/Cognee**. Already rejected (research doc §"Why NOT migrate").
- **Replacing the trailer with a separate metadata table**. Engram doesn't expose user metadata; the trailer is the only path until upstream changes. Adding our own SQLite for lifecycle state would split the source of truth.
- **Adaptive thresholds (ML-tuned)**. Premature without F4 calibration data.
- **Building our own graph view**. F5 (Obsidian export) covers the human-readable graph need; building one would be reinvention.

## Related

- `docs/research/llm-wiki-v2-engram-evolution-2026-04-27.md` — full analysis backing this decision
- `.cognitive-os/plans/features/engram-lifecycle-evolution.md` — phased implementation plan
- `lib/engram_client.py` — existing engram wrapper; `lib/engram_lifecycle.py` wraps this
- `lib/engram_http_client.py` — HTTP REST API wrapper (added in addendum 2026-04-27)
- `hooks/engram-reinforce-on-access.sh` — PostToolUse hook implementing reinforcement (Phase 1)
- `lib/engram_obsidian_exporter.py` — Phase 4 one-way Obsidian Markdown export
- `scripts/export-engram-to-obsidian.sh` — manual dry-run-first export wrapper
- `docs/manual-tests/engram-obsidian-export.md` — manual proof path before automation
- `rules/engram-api-safety.md` — safety policy for production daemon mutation (added in addendum)
- `rules/RULES-COMPACT.md` — reinvention-prevention rule that excluded Mem0/Zep/Cognee migration
- `docs/adrs/ADR-070-convention-enforcement-mechanism.md` — adjacent ADR for context on enforcement patterns
