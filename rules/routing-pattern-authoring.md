<!-- SCOPE: os-only -->
---
slug: routing-pattern-authoring
scope: authoring
enforced_by: tests/audit/test_skill_routing_patterns_ascii.py
---

# Routing Pattern Authoring Rule

## Purpose

Lock in the language-agnostic routing contract established by ADR-296:
`routing_patterns:` regex in any `SKILL.md` are an ASCII-only fast path.
Multilingual matching is handled by the semantic fallback
(`lib/semantic_skill_matcher.py`), not by hand-coded locale-folding regex.

## Rules

1. **ASCII-only patterns.** Every `pattern:` string under `routing_patterns:`
   in a `SKILL.md` frontmatter block MUST contain only ASCII codepoints
   (U+0000 through U+007F).
2. **No locale-folding character classes.** Constructions of the form
   `[nn]`, `[aa]`, `[ee]`, `[oo]`, `[ii]`, `[uu]` paired with accented
   variants (for example, character classes pairing ASCII letters with U+00F1, U+00E1, U+00E9, U+00F3, U+00ED, or U+00FA) and
   their reversed orderings are PROHIBITED. They produce false negatives
   on prompts that use only the accented or only the unaccented form and
   bypass the semantic fallback that ADR-296 designates as the
   authoritative path.
3. **Authoritative multilingual path.** Any prompt that should match in
   Spanish, Portuguese, French, German, etc. MUST flow through
   `lib/semantic_skill_matcher.py` (ADR-296). The matcher uses FastEmbed's
   `paraphrase-multilingual-MiniLM-L12-v2` and covers 50+ languages with
   ~9 ms warm latency.
4. **Comments are exempt.** End-of-line `# ...` comments inside a `pattern:`
   string MAY contain Unicode; the audit strips comments before scanning.
5. **Non-`routing_patterns:` frontmatter is exempt.** Descriptions,
   examples, and prose may contain Unicode freely.

## CI Enforcement

`tests/audit/test_skill_routing_patterns_ascii.py` runs on every PR and
fails the build if any `SKILL.md` violates rules (1) or (2). The audit
walks `skills/**/SKILL.md` and `packages/*/skills/**/SKILL.md`.

For per-language routing coverage validation, the opt-in CI job
`cos-routing-benchmark --multilingual` validates the ADR-296 runtime
fallback path against `manifests/routing-benchmark-corpus-multilingual.yaml`
(OBJ-2 mitigation from the spec).

## Cross-references

- ADR-296 — semantic multilingual routing path
- ADR-298 — routing benchmark harness
- `rules/RULES-COMPACT.md` §11 Skill Lifecycle

## Contextual Trigger

Load this rule when editing `routing_patterns:` in `SKILL.md` files, updating skill routing regexes, changing multilingual routing behavior, or reviewing ADR-296 routing fallback contracts.
