---
adr: 302
title: Language-Agnostic Primitive Routing Authoring Contract
status: accepted
implementation_status: implemented
date: '2026-05-13'
supersedes: []
superseded_by: null
extends:
  - ADR-296
  - ADR-297
  - ADR-298
  - ADR-299
  - ADR-300
  - ADR-301
implementation_files:
  - lib/language_dependence_audit.py
  - scripts/cos-language-dependence-audit
  - skills/primitive-authoring/SKILL.md
  - skills/add-skill/SKILL.md
  - tests/unit/test_language_dependence_audit.py
tier: core
tags:
  - skill-router
  - primitives
  - multilingual
  - authoring
  - audit
verification_level: medium
classification_basis: |
  Converts the language-dependence discussion into an enforceable authoring
  contract: explicit command/identifier regexes remain allowed; natural-language
  routing must move to semantic metadata (`summary_line` + `routing_intents`)
  and be validated through the ADR-298/300 benchmark surface. The audit now
  classifies findings so teams can distinguish real migration debt from
  compatibility fallback.
---

# ADR-302: Language-Agnostic Primitive Routing Authoring Contract

## Status

Accepted — 2026-05-13. Implemented in the same change.

## Context

ADR-296 replaced lexical/Jaccard matching with multilingual semantic routing.
ADR-297 added an LLM-dispatched fallback for ambiguous cases. ADR-298/300/301
created the benchmark/model-selection loop. ADR-299 added an offline enrichment
tool that can generate multilingual `routing_intents` for skills.

That stack fixes runtime capability, but it does not by itself fix primitive
authoring habits. Existing skills and rules still contain many
`routing_patterns` that match human-language keywords in English/Spanish. A raw
regex audit previously reported the same number for all cases, which mixed four
different realities:

1. explicit command aliases that should stay regex-based;
2. legacy natural-language regexes with semantic metadata already present;
3. natural-language regexes with no `routing_intents`; and
4. intentionally localized primitives.

Treating all four as equivalent pushes maintainers toward the wrong fix:
deleting regexes blindly. That can break graceful degradation when the semantic
backend is missing, disabled, or below threshold.

## Decision

Cognitive OS adopts a language-agnostic primitive routing authoring contract.

### 1. Regex is allowed only for deterministic aliases

Keep `routing_patterns` for:

- explicit slash commands, e.g. `/run-tests`;
- primitive identifiers, e.g. `product-answer`;
- machine shapes: URLs, paths, file extensions, IDs, config keys.

Do **not** add new regexes whose purpose is natural-language intent detection,
such as matching ad hoc English/Spanish keywords.

### 2. Natural-language routing belongs in semantic metadata

Every new or materially changed skill SHOULD provide:

- `summary_line`: one short routing-oriented sentence;
- `routing_intents`: one or more human-curated intent descriptions; and
- optionally ADR-299-generated multilingual utterances tagged
  `auto_generated: true`.

The semantic matcher indexes `description + summary_line + routing_intents`.
Multilingual examples are allowed as **embedding corpus data**, not as hard
routing conditions. This is not the same anti-pattern as keyword regex: the
router still evaluates semantic similarity and can be benchmarked.

### 3. Compatibility regexes may remain temporarily

Legacy natural-language regexes may stay when they protect graceful degradation,
provided the primitive also has semantic metadata or is queued for enrichment.
Removal requires benchmark evidence that routing quality does not regress.

### 4. Audit findings are classified, not just counted

`cos-language-dependence-audit` now classifies findings:

| Category | Meaning | Action |
|---|---|---|
| `regex_without_intents` | Natural-language regex without semantic metadata. | Priority migration bucket: add `summary_line` + `routing_intents`; consider ADR-299 enrichment. |
| `regex_with_intents` | Natural-language regex coexists with semantic metadata. | Low-severity compatibility inventory; remove only after benchmark/smoke evidence. |
| `explicit_alias` | Regex matches deterministic command/identifier shape. | Allowed. |
| `localized_skill` | Primitive is intentionally localized. | Low-severity allowed exception, but still prefer semantic metadata when practical. |

### 5. Validation uses benchmark + audit

The minimum loop for routing cleanup is:

```bash
scripts/cos-skill-description-enrich --dry-run --skills <skills> --languages en,es,pt,de,fr,it --intents-per-lang 2
scripts/cos-routing-benchmark --quick
scripts/cos-language-dependence-audit --output .cognitive-os/reports/language-dependence-audit.md
```

The default audit measures actionable medium/high lexical-routing debt; `--min-severity low` measures the full compatibility inventory. The benchmark measures
whether the semantic routing behavior actually improved.

## Applicability to SO and consumer projects

This contract applies to both layers:

- **SO construction**: core `skills/`, `rules/`, packages, and future primitives
  must follow the contract so COS does not become English/Spanish-specific.
- **Consumer projects**: projected or project-local primitives should use the
  same shape. Project-specific vocabulary belongs in semantic metadata and
  project overlays, not hardcoded into OS-level keyword regexes.

Consumer projects may keep local deterministic aliases (`/deploy`, service IDs,
team-specific commands), but natural-language trigger behavior should still be
semantic and benchmarkable.

## Consequences

### Positive

- Stops new language-specific keyword routing from accumulating.
- Preserves graceful degradation instead of deleting fallbacks prematurely.
- Makes audit output actionable by separating debt from compatibility.
- Gives primitive authors a reusable rule for SO and downstream project work.

### Negative / tradeoffs

- Some regex counts will remain non-zero by design.
- Full cleanup requires curating/enriching dozens of skills, not only changing
  router code.
- Benchmark evidence becomes part of routing cleanup work, which is slower than
  deleting patterns.

## Verification

Implemented checks and artifacts:

```bash
python3 -m pytest tests/unit/test_language_dependence_audit.py -q
python3 -m pytest tests/unit/test_language_dependence_audit.py tests/unit/test_skill_router.py tests/unit/test_semantic_skill_matcher.py -q
scripts/cos-language-dependence-audit --json
scripts/cos-routing-benchmark --quick
```

Observed on 2026-05-13 after this ADR landed:

- language audit: 97 visible findings / 326 total findings; categories =
  `regex_without_intents: 69`, `regex_with_intents: 27`, `localized_skill: 1`;
- focused tests: 78 passed, 5 skipped;
- quick benchmark regenerated `docs/06-Daily/reports/routing-benchmark-2026-05-13.md`
  and selected `multilingual-e5-large` as best precision@1 in that run, while
  `baseline-minilm` remained the best warm-p95 latency choice.

The audit now reports category counts alongside severity counts, enabling a
migration queue focused on `regex_without_intents` rather than raw totals.

## Evidence

Tier claim evidence is maintained through the boring-reliability control-plane lane:

```bash
scripts/cos-boring-reliability --json
scripts/cos-tier-claim-audit --json
```

This ADR remains `tier: core` because it affects default routing, observability,
or primitive-governance behavior that is part of the core operator control
plane. The tier claim is re-audited by `scripts/cos-tier-claim-audit`.
