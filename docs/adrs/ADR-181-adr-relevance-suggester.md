---
adr: 181
title: ADR Relevance Suggester — Lightweight Routing for Architecture Decisions
status: accepted
date: 2026-05-05
authors: [luum-agent-os]
supersedes: []
superseded_by: null
cross_references:
  - ADR-174  # auto-derived primitive routing for skills — same declare-in-artifact pattern
  - ADR-179  # rule routing pattern; AdrRouter is analogous
  - rules/RULES-COMPACT.md  # existing manual [ref-key] ADR reference system being augmented
implementation_files:
  - lib/adr_router.py
  - hooks/adr-relevance-suggest.sh
  - manifests/adr-routing-coverage.yaml
  - tests/unit/test_adr_router.py
  - tests/unit/test_adr_relevance_hook.py
tier: maintainer
tags: [adr-routing, suggestion, hooks, user-prompt-submit, relevance, agentic-primitives]
---
# ADR-181: ADR Relevance Suggester

## Status

Accepted — 2026-05-05

## Context

The Cognitive OS has 180+ ADRs in `docs/adrs/`. When the orchestrator begins a
task, it must mentally infer which ADRs are relevant context. The current
mechanism is hand-referencing via `RULES-COMPACT.md` `[ref-key]` syntax and
ADR cross-references in code comments. This is error-prone and relies entirely
on the operator's recall.

ADR-174 introduced auto-derived routing for **skills** (frontmatter
`routing_patterns:` → `lib/skill_router.py` → `hooks/skill-router-prompt-suggest.sh`).
ADR-179 records the analogous rule router (`lib/rule_router.py`). ADRs are
the third primitive surface that benefits from the same pattern, but they have
lower volatility (ADRs change at low frequency vs skills and rules) and a smaller
recall requirement (only high-confidence suggestions are useful — noisy ADR
suggestions are worse than none).

This ADR completes the prevention backlog for ADR-174b by applying the
routing pattern to ADRs with a pragmatic, lower-priority implementation.

## Decision

Implement a lightweight ADR relevance suggester with three components:

### 1. `lib/adr_router.py` — `AdrRouter` class

- Indexes all `docs/adrs/ADR-*.md` files (excluding tombstones, superseded,
  deprecated) on first use (lazy, cached in memory).
- Sources keywords from three tiers per ADR:
  1. **Frontmatter `tags:`** (weight ×3 in scoring) — curated, high-precision.
  2. **Title keywords** (weight ×2) — strong structural signal.
  3. **First paragraph of `## Context`** (weight ×1) — weaker, broad signal.
- Scoring: `min(weighted_hits / sqrt(total_kw_count), 1.0)` — normalised to
  penalise large ADRs less.
- Public API: `top_matches(prompt, n=3, min_confidence=0.85) -> list[AdrMatch]`.
- Higher confidence threshold (0.85) than skill/rule routers (0.80) because
  false-positive ADR suggestions are more disruptive than false-negative ones.
- Standard library only (no PyYAML hard requirement; falls back to a minimal
  inline parser).

### 2. `hooks/adr-relevance-suggest.sh` — `UserPromptSubmit` hook (async)

- Reads prompt from stdin JSON.
- Calls `AdrRouter().top_matches(text, n=3, min_confidence=0.85)`.
- Always logs to `.cognitive-os/metrics/adr-suggestion.jsonl` for calibration.
- If matches found: emits `additionalContext`:
  `"Relevant ADRs for this prompt: ADR-181 (ADR Relevance Suggester, 0.92), ..."`
- Killswitch: `DISABLE_HOOK_ADR_RELEVANCE_SUGGEST=1`.
- Latency budget: <250ms.

### 3. `manifests/adr-routing-coverage.yaml`

- Baseline: 43/180 non-tombstone ADRs have `tags:` (23.9% — below 75% target).
- Target: ≥75% by rolling back-fill (advisory, not enforced).
- Router degrades gracefully for untagged ADRs by using title/context keywords.

## Consequences

**Good:**
- Orchestrator receives passive context hints about relevant ADRs without manual
  [ref-key] lookup.
- Unifies ADR/skill/rule surfaces under the same routing pattern (ADR-174 pattern).
- Low false-positive rate due to 0.85 threshold — only fires on confident matches.
- Async hook — zero latency impact on the user prompt round-trip.

**Accepted trade-offs:**
- Tag-based matching is shallow. ADRs without good tags get poor suggestions.
  Tag quality varies significantly (23.9% current coverage).
- Confidence threshold 0.85 may be too strict in the first 30 days. The metrics
  log enables calibration. If recall is too low, lower to 0.80 after evidence.
- No deduplication across related ADR series (e.g. ADR-043/tombstone and a
  successor may both score well on the same prompt). Operator should read all
  suggested ADRs before concluding one supersedes the other.

## Alternatives rejected

- **Full-text search** — too many false positives and too slow (<250ms budget).
- **LLM-based ADR selector** — too expensive for an async hook on every prompt.
- **No implementation** — accepted status quo is manual [ref-key] lookup; the
  prevention backlog explicitly requested this as a low-priority completion item.

## Verification

```bash
# Router smoke test
python3 -c "
from lib.adr_router import AdrRouter
r = AdrRouter()
print(r.top_matches('research first protocol for high risk changes', n=3, min_confidence=0.0)[:2])
"

# Full unit tests
python3 -m pytest tests/unit/test_adr_router.py tests/unit/test_adr_relevance_hook.py -v

# Coverage baseline
python3 -c "
from lib.adr_router import AdrRouter
print(AdrRouter().coverage_stats())
"

# Hook smoke test (should exit 0 silently — no ADRs match 'hello')
echo '{"prompt": "hello"}' | bash hooks/adr-relevance-suggest.sh
```
