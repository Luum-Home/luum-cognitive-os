# Memory Governance v2 — Typed Memory Policies

**Trigger:** `[memory-governance]`
**ADR:** [ADR-261](../docs/adrs/ADR-261-memory-governance-v2.md)
**Related:** ADR-071 (Ebbinghaus lifecycle decay), ADR-078 (Mid-Task Memory Tool)
**Single source of truth for policy values:** `lib/memory_governance.py` — `_POLICY_TABLE`

---

## Overview

Every Engram observation carries a `type` string field.  Six types are
**governed**: each carries a verification policy, a staleness policy, a
staleness threshold in seconds, and a recall score multiplier.  All other
types fall through to a **no-op default** (no boost, no staleness, no
verification note) so existing observations are completely unaffected.

---

## Governed Types — Policy Table

| `type_name`  | `verification`     | `staleness` | `stale_after_seconds` | `recall_boost` |
|:-------------|:-------------------|:------------|----------------------:|---------------:|
| `preference` | `corroborate`      | `soft`      | 7 776 000 (90 d)      | 1.4            |
| `identity`   | `verify_before_use`| `soft`      | 15 552 000 (180 d)    | 1.2            |
| `fact`       | `corroborate`      | `hard`      | 2 592 000 (30 d)      | 1.0            |
| `procedure`  | `verify_before_use`| `soft`      | 5 184 000 (60 d)      | 1.6            |
| `blocker`    | `verify_before_use`| `hard`      | 864 000 (10 d)        | 1.8            |
| `decision`   | `none`             | `never`     | —                     | 1.1            |

---

## Verification Tiers

| Tier                | Semantics |
|:--------------------|:----------|
| `none`              | No special handling at recall time; accepted as-is. |
| `corroborate`       | When stale or aging, the `FreshnessResult.note` instructs the assistant to seek a second source before driving a consequential action. |
| `verify_before_use` | Note is **always emitted** (even when fresh) instructing the assistant to confirm with the user or a live source before acting. |

---

## Staleness Tiers

| Tier    | Semantics |
|:--------|:----------|
| `never` | Observation is considered stable regardless of age.  `is_stale()` always returns `False`. |
| `soft`  | Age >= `stale_after_seconds` emits a warning note but does NOT suppress the result. |
| `hard`  | Age >= `stale_after_seconds` sets `state="stale"`; callers (retriever integration) suppress the result from the ranked output. |

### Freshness States

| State    | Condition |
|:---------|:----------|
| `stable` | `staleness="never"` or unknown type. |
| `fresh`  | Age < 75% of threshold. |
| `aging`  | Age >= 75% of threshold but < threshold. |
| `stale`  | Age >= threshold. |

---

## Recall Boost

The `recall_boost` field is a multiplier applied to the raw retrieval score
at ranking time: `adjusted = raw_score * recall_boost`.

- `blocker` has the highest boost (1.8x) — known hard constraints should
  surface prominently in any relevant query.
- `procedure` (1.6x) — operational how-to content should rank above generic
  entries of equal lexical similarity.
- `preference` (1.4x) — user preferences should surface above technically
  higher-scoring but less personalized entries.
- `decision` (1.1x) — slight lift for project decisions.
- `fact` (1.0x) — neutral; external facts compete on their own merit.

---

## No-Op Default (Backward Compatibility)

Types **not listed** in the table (e.g. `bugfix`, `discovery`, `architecture`,
`config`, `pattern`, `manual`) receive:

```python
MemoryTypePolicy(
    type_name=type_name,
    verification="none",
    staleness="never",
    stale_after_seconds=None,
    recall_boost=1.0,
)
```

This means: no suppression, no boost, no verification note, no change to
existing recall behaviour.

---

## Adding a New Governed Type

To add a new type to the governance table:

1. Open `lib/memory_governance.py` and add an entry to `_POLICY_TABLE`.
2. Update the table in this file (`rules/memory-governance.md`) to match.
3. Add unit tests in `tests/unit/test_memory_governance.py` covering:
   - `get_policy` returns the correct policy values.
   - `is_stale` returns the expected result at boundary ages.
   - `assess_freshness` returns the correct state and note.
4. Open a PR; changes to `_POLICY_TABLE` require a PR review (no YAML
   override path in v1 -- see ADR-261 §Alternatives for rationale).

NEVER hard-code type strings in implementation code.  Always use
`get_policy(type_name)` from `lib/memory_governance.py` as the single
source of truth.

---

## Integration Points

### `lib/memory_retriever.py` -- Recall-time scoring

When the optional `governance` parameter is passed to `MemoryRetriever.search()`:

1. `boosted_score(raw_score, result.type)` adjusts the combined score.
2. `assess_freshness(age_seconds, result.type)` computes the freshness state.
3. Hard-stale results (`state="stale"` + `staleness="hard"`) are suppressed.
4. `freshness_note` and `governance_reasons` are attached to each `RetrievalResult`.

### `lib/engram_lifecycle.py` -- Write-time decay

After computing `decay_class`, `get_policy(type)` is called:

- If `policy.stale_after_seconds` is not None, it overrides the Ebbinghaus tau
  for that type, keeping decay consistent with the governance threshold.
- `governance_freshness_state` is written into the JSON lifecycle trailer for
  governed types.  Field is absent for unrecognized types (no-op).

---

## Cross-References

- ADR-261 -- full specification, identifier divergence table, backward
  compatibility guarantee, and open questions.
- ADR-071 -- Ebbinghaus lifecycle decay model extended by §4 of ADR-261.
- ADR-078 -- Mid-Task Memory Tool (governs write-time decisions, orthogonal
  to this recall-time governance layer).
- `rules/RULES-COMPACT.md` §11 -- type string conventions (extended by this file).
