# Primitive Structure Standardization — 2026-05-14

## Scope

This pass standardized primitive file structure only. It did not use raw grep to reclassify semantic `SCOPE`; existing markers were preserved where present, and template paths that cannot safely carry inline comments were recorded in parser metadata.

## Changes

- Added parser coverage for `packages/*/hooks/*` and `packages/*/rules/*`.
- Excluded non-primitive support files from primitive debt:
  - archived/disabled hooks;
  - hook/script `.txt` support files;
  - `scripts/_lib/*` helper libraries.
- Treated `rules/RULES-COMPACT.md` and `rules/ROADMAP.md` as `rule-index`, not normal contextual rules.
- Normalized all discovered `SKILL.md` files so YAML frontmatter starts at byte 0 and `SCOPE` follows the frontmatter.
- Added missing `triggers` metadata to skills using existing name/title/summary signals.
- Added `## Contextual Trigger` sections to normal rules missing that section.
- Added `SCOPE` comments to scripts whose classifier had high-confidence durable evidence.
- Added `manifests/primitive-structure-scopes.yaml` for templates whose native rendered format should not receive inline comments.

## Parser inventory after standardization

```json
{
  "total": 1201,
  "primitive_total": 1188,
  "missing_scope_marker": 0,
  "structural_findings": {}
}
```


## Existing primitive contract registry

`manifests/primitive-contracts.yaml` was reviewed after this pass. It currently contains 340 signed behavior/projection contracts and remains the ADR-256/ADR-257 canonical registry for runtime intent, trigger semantics, evidence, and per-harness fidelity.

This structure-standardization pass did not replace that registry. The new `manifests/primitive-structure-scopes.yaml` has zero path overlap with `primitive-contracts.yaml`; it only covers comment-hostile template files that need parser-visible scope without changing rendered project artifacts.

## Remaining taxonomy work

Structural standardization is complete under the current parser contract. Scope calibration is not complete and remains governed by ADR-314:

```json
{
  "total_unknown": 562,
  "by_bucket": {
    "declared-both-needs-proof-and-metadata": 364,
    "declared-both-os-internal-heavy": 81,
    "insufficient-metadata": 65,
    "conflicting-metadata": 32,
    "os-only-semantic-candidate": 19,
    "both-semantic-candidate": 1
  }
}
```

## Validation

```bash
bash scripts/cos-registry-lock --project-dir . --write
.venv/bin/python -m pytest tests/unit/test_primitive_parser.py tests/unit/test_primitive_scope_unknown_triage.py tests/unit/test_primitive_scope_classifier.py -q
.venv/bin/python -m py_compile lib/primitive_parser.py scripts/primitive_parse_inventory.py scripts/primitive_structure_standardizer.py scripts/primitive_scope_classifier.py scripts/primitive_scope_unknown_triage.py
bash scripts/cos-registry-lock --project-dir . --audit
.venv/bin/python scripts/primitive_parse_inventory.py --project-dir .
.venv/bin/python scripts/primitive_scope_classifier.py --project-dir .
.venv/bin/python scripts/primitive_scope_unknown_triage.py --project-dir .
```

Result: parser inventory has zero structural findings, registry audit passes, and the manual checklist is recorded in `primitive-structure-manual-audit-checklist-2026-05-14.md`.
