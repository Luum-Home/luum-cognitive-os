---
adr: 261
title: 'Memory Governance v2: Typed Memory with Verification & Staleness Policies'
status: accepted
implementation_status: implemented
date: '2026-05-11'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: memory governance module, retriever/lifecycle integration, and
  unit tests implement typed memory policy
verification:
  level: strong
  commands:
  - python3 -m pytest tests/unit/test_memory_governance.py tests/red_team/portability/test_engram_lifecycle.py
    -q
  proves:
  - behavior_contract
---

# ADR-261 — Memory Governance v2: Typed Memory with Verification & Staleness Policies

## Status

Accepted

**Date:** 2026-05-11
**Owner:** orchestrator (Opus 4.7)
**Tier:** core
**Authors:** orchestrator (Claude Opus 4.7)
**Implements:** ADR-259 (holaOS Adoption Posture — patterns only)
**Source-pattern:** Internal compliance dossier §Typed memory governance (AnnexA::Feature 1)
**Related:** ADR-078 (Mid-Task Memory Tool — Hermes port), ADR-071 (Ebbinghaus lifecycle
decay), ADR-259 (holaOS Adoption Posture)

---

## Context

### Current state of Engram type handling

luum-agent-os stores observations in Engram with a free-form `type` string field. The
convention (`bugfix | discovery | decision | architecture | pattern | config | preference |
manual | …`) is established by RULES-COMPACT §11 but carries no enforcement mechanism and no
per-type policy. The type field is consumed in exactly one place: `lib/engram_lifecycle.py`
maps it to a decay class via `_TYPE_TO_DECAY_CLASS`, which feeds the Ebbinghaus half-life
calculation (`0.7 * relevance + 0.3 * (confidence * exp(-age/τ))`).

No other component in the recall pipeline consults the type. `lib/memory_retriever.py` ranks
results on FTS5 + Jaccard with weights 0.6/0.4; it does not call into `engram_lifecycle` and
has no awareness of what type an observation carries. The lifecycle and retrieval layers are
independent code paths that happen to share the same underlying records.

### The gap

This design creates three concrete problems:

1. **Stale memory surfaces with high confidence.** A `preference` observation written six months
   ago (e.g., "user prefers verbose output") will continue to score well on relevance and
   confidence if it has been reinforced, even if the preference was overridden in a later
   session. There is no mechanism to detect or signal that it may be outdated.

2. **No verification differentiation.** A `fact` about a public API endpoint has a completely
   different trust lifecycle than a `decision` made within the project. Both are retrieved
   identically. Callers have no signal that a given memory type warrants re-confirmation before
   use.

3. **No intent-aware boost.** When a query is procedural ("how do I release a new version?"),
   `procedure`-type memories should score higher than `discovery` or `bugfix` entries of equal
   lexical similarity. The retriever has no mechanism to apply type-specific score multipliers.

### Research finding

The research annex [private clean-room research dossier] §Typed memory governance documents that the
reference system addresses these three problems with a static rule table keyed on memory type.
Each entry in the table carries a verification policy, a staleness policy, a staleness
threshold in seconds, and a recall score multiplier. The freshness state is computed at query
time and passed forward to the prompt as a human-readable cue ("verify before use", "stale —
reconfirm"). The ranking layer multiplies the base score by the recall boost and applies a
stale penalty. The design is approximately 150 LOC of pure logic in the reference system.

The research annex also identifies two memory types — `procedure` and `blocker` — that are
present in the reference system but absent from luum's vocabulary. `procedure` (how to
perform an operation or release) maps directly to content already maintained in
`docs/05-Methodology/runbooks/`. `blocker` (known issue that prevents a class of actions) is a useful
category for tracking hard constraints across sessions. Both are worth adopting regardless of
the broader feature.

This ADR adopts the pattern under the clean-room protocol established by ADR-259: the
implementation is a Python rewrite guided exclusively by the abstract specification in the
annex. No source code from the reference system is copied or consulted. Identifiers, module
structure, and policy constants are independently derived.

---

## Decision

### 1. New module `lib/memory_governance.py`

A new stdlib-only module (`dataclasses`, `typing`, `time`) implementing the governance rule
table and the freshness assessment function. Public interface:

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True)
class MemoryTypePolicy:
    type_name: str
    verification: Literal["none", "corroborate", "verify_before_use"]
    staleness: Literal["never", "soft", "hard"]
    stale_after_seconds: int | None
    recall_boost: float  # multiplier applied to raw retrieval score; 1.0 = neutral

@dataclass(frozen=True)
class FreshnessResult:
    state: Literal["stable", "fresh", "stale"]
    note: str | None  # human-readable cue for assistant surface; None when state == "stable"

def get_policy(type_name: str) -> MemoryTypePolicy:
    """Return the policy for type_name. Returns a no-op default for unknown types."""

def is_stale(observation_age_seconds: int, type_name: str) -> bool:
    """True if the observation exceeds the policy staleness threshold for its type."""

def assess_freshness(observation_age_seconds: int, type_name: str) -> FreshnessResult:
    """Return a FreshnessResult with state and optional human-readable note."""

def boosted_score(raw_score: float, type_name: str) -> float:
    """Apply the type's recall_boost multiplier to raw_score."""
```

**Static rule table** — six types adapted to luum vocabulary:

| `type_name`   | `verification`     | `staleness` | `stale_after_seconds` | `recall_boost` |
|---------------|--------------------|-------------|----------------------:|---------------:|
| `preference`  | `corroborate`      | `soft`      | 7 776 000 (90 days)   | 1.4            |
| `identity`    | `verify_before_use`| `soft`      | 15 552 000 (180 days) | 1.2            |
| `fact`        | `corroborate`      | `hard`      | 2 592 000 (30 days)   | 1.0            |
| `procedure`   | `verify_before_use`| `soft`      | 5 184 000 (60 days)   | 1.6            |
| `blocker`     | `verify_before_use`| `hard`      | 864 000 (10 days)     | 1.8            |
| `decision`    | `none`             | `never`     | None                  | 1.1            |

Semantics:

- `verification="none"`: no special handling at recall time; accepted as-is.
- `verification="corroborate"`: the FreshnessResult note instructs the assistant to seek a
  second source if the observation is being used to drive a consequential action.
- `verification="verify_before_use"`: the FreshnessResult note is always emitted (even when
  `state="fresh"`) instructing the assistant to confirm with the user or a live source before
  acting.
- `staleness="never"`: the observation is considered stable regardless of age.
- `staleness="soft"`: age >= `stale_after_seconds` emits a note but does not filter the result.
- `staleness="hard"`: age >= `stale_after_seconds` sets `state="stale"`; callers may suppress
  the result from the ranked list (retriever integration described in §3).
- `recall_boost`: a multiplier in the range [0.0, ∞). 1.0 is neutral. `blocker` is boosted
  aggressively because unresolved blockers should surface prominently in any relevant query.

**Default policy for unknown types** — types not listed in the table receive:

```python
MemoryTypePolicy(
    type_name=type_name,
    verification="none",
    staleness="never",
    stale_after_seconds=None,
    recall_boost=1.0,
)
```

This is a complete no-op: existing luum types (`bugfix`, `discovery`, `architecture`, `config`,
`pattern`, `manual`, …) are unaffected until explicitly added to the table.

### 2. New rule file `rules/memory-governance.md`

A new rules file documenting the six defined types, their policies, and the operational
semantics of each verification and staleness tier. The file is loaded on the
`[memory-governance]` trigger. It documents:

- The canonical list of governed types and their policy parameters.
- The convention that implementer agents MUST NOT hard-code type strings; they must use the
  table defined in `lib/memory_governance.py` as the single source of truth.
- Instructions for adding a new type (requires a PR that updates the table in
  `lib/memory_governance.py` and the rule documentation simultaneously).
- A cross-reference to this ADR and to ADR-071 (decay lifecycle).

### 3. Additive integration in `lib/memory_retriever.py`

`memory_retriever.py` currently computes a combined score and returns a list of retrieval
results. The integration is purely additive — the new parameter defaults to `None`, preserving
existing behaviour when not supplied.

Changes:

- Add optional parameter `governance: MemoryGovernanceAdapter | None = None` to the main
  retrieval function.
- When `governance` is not `None`, apply the following after the FTS5+Jaccard score is
  computed for each result:
  1. Call `boosted_score(raw_score, result.type)` to compute the adjusted score.
  2. Call `assess_freshness(age_seconds, result.type)` to compute the freshness state.
  3. If `state == "stale"` and `staleness == "hard"`: suppress the result from the ranked
     output entirely (do not return it to the caller).
  4. Attach `freshness_note: str | None` and `governance_reasons: list[str]` to the result
     record. Example reasons: `["recall_boost:1.8", "stale_penalty:hard", "verify_before_use"]`.
- The returned `RetrievalResult` gains two new optional fields (`freshness_note`,
  `governance_reasons`) that are `None` when governance is not active. This is backwards
  compatible — callers that do not check for these fields are unaffected.
- `lib/memory.py` (orchestrator-facing facade) is updated to pass the `governance` adapter
  when constructing the retriever, and to surface any non-None `freshness_note` in the search
  result returned to the assistant. This allows the assistant to include "verify before use"
  cues in responses where warranted.

### 4. Additive integration in `lib/engram_lifecycle.py`

`engram_lifecycle.py` computes confidence and decay and writes a JSON trailer to each
observation record. Changes:

- After computing `decay_class` from `_TYPE_TO_DECAY_CLASS`, call `get_policy(type)` and use
  `policy.stale_after_seconds` (when not `None`) as an **override** of the Ebbinghaus τ for
  that type. This ensures the lifecycle decay is consistent with the governance staleness
  threshold: a `blocker` observation (10-day threshold) will decay faster than a `decision`
  (no threshold) even if both previously mapped to the same `τ` class.
- Emit `governance_freshness_state` into the JSON trailer alongside `confidence` and
  `decay_class`. This allows downstream callers (including hooks and dashboard tooling) to
  read the pre-computed freshness state without re-computing it.
- If `type` is not in the governance table, the trailer field is omitted (no-op default
  described in §1 means the override has no effect either).

### 5. Backward compatibility guarantee

- Types not in the governance table: `get_policy` returns the no-op default. `is_stale`
  always returns `False`. `assess_freshness` returns `FreshnessResult(state="stable",
  note=None)`. `boosted_score` returns `raw_score` unchanged. No existing retrieval result
  is suppressed. The lifecycle τ override has no effect.
- The `governance` parameter in `memory_retriever.py` defaults to `None`; all callers that
  do not explicitly pass it continue to work without modification.
- The lifecycle trailer change is additive: new field `governance_freshness_state` is written
  only when the type is governed. Readers that do not check for this field are unaffected.

### 6. Identifier divergence (Annex F §2 compliance)

| Reference system identifier (from research annex) | luum identifier       | Rationale                                                      |
|----------------------------------------------------|-----------------------|----------------------------------------------------------------|
| `MemoryGovernanceRule` (type name)                 | `MemoryTypePolicy`    | "Policy" is already the luum convention for rule-carriers; avoids "governance/rule" tautology |
| `verificationPolicy` (field)                       | `verification`        | Snake-case; dropped redundant `-Policy` suffix                 |
| `stalenessPolicy` (field)                          | `staleness`           | Same rationale                                                 |
| `recallBoost` (field, integer in reference)        | `recall_boost` (float)| Snake-case; float allows sub-integer tuning without schema change |
| `workspace_sensitive` (staleness tier)             | `soft`                | luum uses `project` not `workspace`; "soft" is more semantically precise |
| `time_sensitive` (staleness tier)                  | `hard`                | Pairs naturally with `soft`; avoids time/workspace ambiguity   |
| `stable` (staleness tier)                          | `never`               | `staleness="never"` is clearer in the field name context       |
| `check_before_use` (verification tier)             | `corroborate`         | Aligns with luum's Trust Score vocabulary (ADR-certified)      |
| `must_reconfirm` (verification tier)               | `verify_before_use`   | Imperative form consistent with luum rule language             |
| `reference` (memory type)                          | Not adopted           | luum has no `reference` concept; `fact` covers the overlap     |

luum-specific additions not in the research annex: `procedure` and `blocker` types (Annex A
§Hallazgos sorpresa item 3, independently derived); `decision` enrolled from luum's existing
vocabulary; `FreshnessResult.note=None` when `state=="stable"` to reduce noise.

---

## Acceptance Criteria

```
[ ] lib/memory_governance.py exists; importable via
    python3 -c "from lib.memory_governance import get_policy, is_stale, boosted_score, assess_freshness"

[ ] pytest tests/unit/test_memory_governance.py passes, covering:
    - get_policy returns correct MemoryTypePolicy for each of the six governed types
    - get_policy returns the no-op default for an unrecognized type string
    - is_stale returns False for age < stale_after_seconds; True for age >= threshold
    - is_stale always returns False for types with staleness="never" (e.g., "decision")
    - boosted_score is idempotent: boosted_score(s, unknown_type) == s
    - assess_freshness returns state="stable" and note=None for staleness="never" types
    - assess_freshness returns state="stale" for hard-staleness types past threshold
    - assess_freshness returns note != None for verify_before_use types regardless of age

[ ] lib/memory_retriever.py ranking is unchanged when governance parameter is None
    (verified by running existing retriever tests without modification)

[ ] lib/engram_lifecycle.py JSON trailer includes governance_freshness_state for governed
    types; field is absent for unrecognized types

[ ] rules/memory-governance.md exists, references ADR-261, and documents the six types
    with their policy parameters

[ ] Compliance F§5 grep verification:
    grep -rF "MemoryGovernanceRule" /tmp/holaOS-investigation 2>/dev/null
    # must return 0 matches in any staged diff (absent /tmp path = WARN, not FAIL)

[ ] Commit message uses Annex F §6 template:
    Source-pattern: [private compliance dossier — see internal records] §Typed memory governance
```

---

## Consequences

### Positive

- **Stale memory auto-suppressed.** Hard-staleness types (`fact`, `blocker`) past their
  threshold are filtered from recall results, preventing outdated entries from surfacing with
  misleadingly high confidence scores.
- **Preference boost reduces noise.** `preference` observations score 40% higher than baseline
  on the same lexical match, reducing the chance that a user preference is buried behind a
  technically-higher-scoring `bugfix` entry.
- **Blockers surface in critical queries.** `blocker` observations have the highest recall
  boost (1.8×), ensuring that known hard constraints are prominent whenever a related query
  arrives — a meaningful safety improvement for agent execution loops.
- **Verify-before-use cue reaches the assistant.** The `freshness_note` field propagated
  through `lib/memory.py` gives the orchestrator-facing assistant a structured signal to
  include verification prompts in replies when a sensitive memory type is retrieved. This
  improves trust calibration without requiring any orchestrator-side changes.
- **Audit trace per recall.** The `governance_reasons` list in `RetrievalResult` provides a
  machine-readable explanation of why a given result ranked where it did — directly useful
  for retrieval benchmark analysis in `lib/memory_retrieval_benchmark.py`.

### Negative

- **Policy table is statically hardcoded.** Changing a type's `stale_after_seconds` or
  `recall_boost` requires a code change and PR review. There is no YAML-driven override path
  in v1. For an agentic system where staleness thresholds may need per-project tuning,
  this means a full release cycle for each adjustment.
- **Six governed types covers a minority of existing observations.** Most luum observations
  use types like `bugfix`, `discovery`, or `architecture` that fall through to the no-op
  default. The governance layer adds overhead (function calls, freshness computation) for
  records that receive no policy benefit until those types are added to the table.
- **Hard suppression of stale results is irreversible at query time.** A `fact` observation
  suppressed because it is 31 days old may still be the best available answer if no fresher
  record exists. There is currently no fallback mode ("suppressed but available on request").

### Mitigations

- The no-op default (§1) ensures the negative impact on unrecognized types is exactly zero;
  the "minority coverage" problem is a day-1 reality that improves organically as new types
  are enrolled.
- If YAML-driven policy overrides are needed (per-project tuning), a follow-up ADR may
  introduce a `cognitive-os.yaml` block `memory.governance.overrides` that merges with the
  static table at startup. This is explicitly deferred to a phase-2 ADR to keep this change
  reviewable and reversible.
- Hard suppression can be mitigated by a future `include_stale: bool = False` parameter in
  the retriever call-site; the retrieval logic is structured to make this a one-line addition.

---

## Implementation Plan

**Day 0.5 — Core governance module and unit tests**

- Write `lib/memory_governance.py`: `MemoryTypePolicy`, `FreshnessResult`, `_POLICY_TABLE`
  (static dict), `get_policy`, `is_stale`, `assess_freshness`, `boosted_score`.
- Write `tests/unit/test_memory_governance.py`: table-driven test suite covering all
  acceptance criteria test cases above.
- Verify: `python3 -m pytest tests/unit/test_memory_governance.py -q` passes with 0 failures.

**Day 0.5 — Retriever and memory facade integration**

- Modify `lib/memory_retriever.py`: add `governance` parameter, apply `boosted_score`,
  `assess_freshness`, hard-suppression logic, attach `freshness_note` and `governance_reasons`
  to `RetrievalResult`.
- Modify `lib/memory.py`: pass governance adapter, surface `freshness_note` in the search
  result returned to the orchestrator.
- Verify: existing retriever tests pass unchanged (no regression). Add integration test for
  boosted and suppressed result scenarios.

**Day 0.5 — Lifecycle integration and rule file**

- Modify `lib/engram_lifecycle.py`: add `stale_after_seconds` override of τ, emit
  `governance_freshness_state` into JSON trailer for governed types.
- Write `rules/memory-governance.md`: type table, operational semantics, cross-references.
- Run full acceptance criteria checklist.
- Run Annex F §5 compliance grep commands, record results.
- Save Engram observation under `compliance/holaos-adoption/memory-governance`.

---

## Alternatives rejected

| Alternative | Decision | Rationale |
|-------------|----------|-----------|
| Policy table in YAML (`cognitive-os.yaml`) | Rejected (v1) | Adds YAML parsing, schema validation, and hot-reload complexity. The benefit (per-project tuning without PR) is real but not required for the initial delivery. Parked as explicit phase-2 option; see Mitigations. |
| Per-observation policy record (one policy row per memory entry) | Rejected | Overkill. Policy is a property of the type, not of the individual observation. Per-entry overrides would require a new DB column and a write-time governance decision that adds latency to every `mem_save` call. |
| Reuse of ADR-078 Hermes mid-task memory | Rejected (complementary) | ADR-078 addresses *when* to write a memory during task execution. This ADR addresses *how retrieved memories are scored and filtered*. The two are orthogonal and complementary; neither replaces the other. |
| Extend `_TYPE_TO_DECAY_CLASS` in `engram_lifecycle.py` directly | Rejected | Would conflate the decay (time-to-forget) concern with the retrieval (boost/suppress/verify) concern. The two concerns have different consumers and different rate-of-change. A dedicated module with a clean interface is preferable. |

---

## Compliance Certification

This ADR adopts a pattern from [private clean-room research dossier] §Typed memory governance under the
clean-room protocol defined in [private compliance dossier — see internal records].

Compliance declarations per Annex F §4.2:

```yaml
pattern_source: "holaos-comparison-2026-05-10.md::AnnexA::§Feature1 (Typed memory governance)"
holaos_files_read_by_research: []
holaos_files_blocked_for_impl: ["ALL"]
```

See §Decision 6 above for the full identifier divergence table.

luum-specific additions not present in the reference system:

- `procedure` and `blocker` types added based on Annex A §Hallazgos sorpresa (gap analysis),
  independently derived for luum.
- `decision` type enrolled with a no-staleness policy (luum's existing vocabulary; not present
  in the reference system's six-type table).
- `FreshnessResult.note` suppressed when `state == "stable"` (reduces note noise vs.
  reference system which may emit a note for any verification policy tier).
- `governance_reasons` list for explainability in retrieval benchmarks (no analogue in
  reference system).

Implementer agents operating under this ADR MUST NOT read `/tmp/holaOS*` or any path
identified as a mirror of the reference source. Any prompt containing such paths or literal
source fragments requires immediate execution halt and emission of:
`NEEDS_CLARIFICATION: prompt contains holaOS source references; resend with only the abstract
spec ([private clean-room research dossier] §Typed memory governance).`

Commit messages for all implementation commits MUST include:

```
Pattern adopted from holaOS (clean-room rewrite).
Refs: [private clean-room research dossier]
Source-pattern: AnnexA::§Feature1.typed-memory-governance
License: Apache-2.0 modified (BSL-like). No source code copied.
```

---

## Open Questions

1. **Exact `stale_after_seconds` calibration per type.** The thresholds in the §1 table
   (90 days for `preference`, 10 days for `blocker`, etc.) are reasonable defaults derived
   from general domain knowledge about how quickly these memory categories become outdated in
   an agent-OS context. However, luum has not yet run a retrieval benchmark comparing
   threshold choices against real recall quality. **UNSURE** whether the chosen thresholds
   will produce net-positive recall outcomes in practice; calibration against
   `lib/memory_retrieval_benchmark.py` output after a few weeks of production use is required
   before declaring the defaults stable.

2. **Interaction with the relation/graph layer.** luum's `engram_graph_walker.py` and the
   Wave2 bitemporal schema (`valid_to`, `supersedes` relation) provide a richer freshness
   signal than age alone: if a `preference` observation has been explicitly superseded via a
   `supersedes` relation edge, the governance staleness threshold is redundant — the
   observation should be suppressed regardless of age. Conversely, if an aging `fact`
   observation has a recent `related` edge to a newly written observation, that graph
   proximity may indicate that the `fact` is still current. **UNSURE** whether the
   `assess_freshness` function should consult the graph layer (via `engram_graph_walker`)
   before deciding on the freshness state, or whether the two systems should remain
   independent for now. The interaction design is deferred to a follow-up ADR; v1 governance
   operates on age alone.

---

## References

- [private clean-room research dossier] §Typed memory governance — abstract specification source for
  the typed memory governance pattern
- [private compliance dossier — see internal records] — clean-room protocol and compliance
  checklist
- ADR-259 — holaOS Adoption Posture (umbrella patterns-only policy; this ADR is its second
  concrete implementation)
- ADR-071 — Ebbinghaus lifecycle decay (the decay model extended by §4 of this ADR)
- ADR-078 — Mid-Task Memory Tool / Hermes port (complementary; governs write-time decisions,
  not recall-time scoring)
- `lib/engram_lifecycle.py:63-80` — `_DECAY_TAU` and `_TYPE_TO_DECAY_CLASS` (extended by §4)
- `lib/memory_retriever.py:65-145` — FTS5+Jaccard ranking (extended by §3)
- `lib/memory.py` — orchestrator-facing memory facade (extended by §3)
- `rules/RULES-COMPACT.md` §11 — type string conventions (extended by new rule file)

---
*This ADR references a private clean-room research dossier whose specific
file paths and section headings are intentionally redacted from this public
record per ADR-267 §Layer 4 and the privatize-research migration (commit e961fd3b).*

## Verification

```bash
python3 -m py_compile lib/memory_governance.py lib/memory_retriever.py lib/engram_lifecycle.py
python3 -m pytest tests/unit/test_memory_governance.py tests/red_team/portability/test_engram_lifecycle.py -q
```

