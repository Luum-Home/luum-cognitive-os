# ADR-071 — Engram Lifecycle Evolution via Wrapper Layer

## Status

**Accepted** — 2026-04-27

## Context

Engram (v1.14.5, third-party Go binary at `<home>/go/bin/engram`, exposed via MCP) is the project's persistent memory backend. It provides `mem_save`, `mem_search`, `mem_get_observation`, `mem_judge` (with typed edges: supersedes, conflicts\_with, related, compatible, scoped, not\_conflict), `mem_session_summary`, and `mem_update`. Its observation schema stores `title`, `content`, `type_`, `topic_key`, `project`, and `created_at`.

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
| 1 | Confidence + decay (`lib/engram_lifecycle.py`, trailer schema, ranking, reinforcement hook) | **This sprint** |
| 2 | Crystallization pipeline (auto-promote N+ observations on same topic\_key → digest → `type=pattern`) | Planned — see feature plan |
| 3 | Graph traversal in queries (walk `mem_judge` edges, 2-hop max, merge into ranked results) | Planned — see feature plan |
| 4 | Obsidian export as human-readable layer (read-only; no writes from Obsidian to engram) | Deferred — after Phases 1–3 ship |

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

## Related

- `docs/research/llm-wiki-v2-engram-evolution-2026-04-27.md` — full analysis backing this decision
- `.cognitive-os/plans/features/engram-lifecycle-evolution.md` — phased implementation plan
- `lib/engram_client.py` — existing engram wrapper; `lib/engram_lifecycle.py` wraps this
- `hooks/engram-reinforce-on-access.sh` — PostToolUse hook implementing reinforcement (Phase 1)
- `rules/RULES-COMPACT.md` — reinvention-prevention rule that excluded Mem0/Zep/Cognee migration
- `docs/adrs/ADR-070-convention-enforcement-mechanism.md` — adjacent ADR for context on enforcement patterns
