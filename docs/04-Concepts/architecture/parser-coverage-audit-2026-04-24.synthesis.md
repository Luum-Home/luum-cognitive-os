---
type: concept-synthesis
source: docs/04-Concepts/architecture/parser-coverage-audit-2026-04-24.md
provenance: "Triggered by the _fm() frontmatter-parser bug (fixed in commit c6c84e4); audits whether 12 sibling parsers share the same synthetic-only test coverage gap."
---

## What it is
Coverage audit classifying 11 non-skipped Python parser/extractor modules as GREEN (real-file tested), YELLOW (mixed), RED (synthetic-only), or GREEN-by-design (no parsing). Root failure pattern: parsers checking `lines[0] == "---"` without skipping a leading `<!-- SCOPE: ... -->` HTML comment.

## Key mechanics
- GREEN: `lib/session_hygiene.py` (`_fm()`, fixed, reference case), `lib/skill_routing.py` (`_extract_frontmatter`/`parse_routing_block`, 3 real SKILL.md fixtures), `scripts/generate_compact_catalog.py` (`parse_frontmatter()`, runs against real repo tree end-to-end).
- RED (confirmed same bug as `_fm()`): `lib/pattern_detector.py` (`_parse_frontmatter_keys()` — feeds `/pattern-audit`, `/detect-patterns`; silently drops keys for all `SCOPE: both` SKILL.md files, ~half the repo; fix cost 4-10 tests); `lib/smart_access.py` (`get_skill_frontmatter()` — highest blast radius, used by multiple skills/hooks for routing metadata, returns `{}` for every `<!-- SCOPE: both -->` file; fix cost 1-3 tests).
- RED (different failure mode, same "no production-shaped input tested" gap): `lib/doc_review_personas.py` (`parse_findings()` parses LLM free-form text via `_HEADER_RE`/`_FIELD_RE`, tested only with `_mock_llm_response()` synthetic strings; fix cost 1-3 — capture real persona outputs as fixtures).
- RED (no dedicated test): `scripts/regen_catalog_bullets.py` delegates entirely to fixed `_fm()`; no `tests/unit/test_regen_catalog_bullets.py` exists; fix cost 1-3.
- YELLOW: `scripts/radar_merge.py` (`parse_artifact()` uses permissive `re.DOTALL` regex, lower risk; `parse_doc_entries()` tested only on hardcoded strings, no real `docs/ecosystem-tools/` artifacts; fix cost 4-10).
- GREEN-by-design (no parsing): `packages/ecosystem-tools/lib/notifications.py`, `packages/infra-lifecycle/lib/performance_monitor.py`, `scripts/dogfood_score.py`.
- Risk ranking: 1) `lib/smart_access.py` (highest blast radius, routing cascades), 2) `lib/pattern_detector.py` (false "dead metadata" positives), 3) `scripts/regen_catalog_bullets.py` (no test at all, silent regression risk).

## Relations & where used
`_fm()` fix commit `c6c84e4`; recommended fixes apply the same HTML-comment-prefix-skip logic already in `skill_routing.py::_extract_frontmatter`.

## Status / caveats
Audit is a point-in-time finding (2026-04-24); recommendations table lists exact fix per module but does not confirm fixes were applied — treat `pattern_detector.py` and `smart_access.py` RED classifications as still-open until verified against current code.
