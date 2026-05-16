# Primitive Structure Manual Audit Checklist — 2026-05-14

## Goal

Clean up primitive structural standardization after automatic normalization, separating three concerns:

1. parseable file structure;
2. behavior/projection contract (`manifests/primitive-contracts.yaml`);
3. semantic taxonomy `SCOPE` governed by ADR-314.

## Non-goals

- Do not reclassify `SCOPE` by grep.
- Do not turn `primitive-structure-scopes.yaml` into a second behavior registry.
- Do not edit procedural content unless it breaks parseable structure.

## Acceptance criteria

- [ ] Parser inventory: `missing_scope_marker = 0`.
- [ ] Parser inventory: `structural_findings = {}`.
- [ ] `primitive-contracts.yaml` remains documented as the canonical behavior/projection registry.
- [ ] Skills: YAML starts at byte 0; `SCOPE` appears after frontmatter; there is no loss of relevant non-SCOPE comments.
- [ ] Rules: normal rules have `Contextual Trigger`; indexes (`RULES-COMPACT`, `ROADMAP`) are not treated as normal rules.
- [ ] Hooks: real hooks have scope; archived/disabled/support do not inflate debt.
- [ ] Scripts: scripts with added scope use existing evidence; support files are not primitives.
- [ ] Templates: rendered artifacts are not corrupted with inline comments; templates comment-hostile use structural metadata.
- [ ] Locks/registries pass audit.
- [ ] Focused tests pass.

## Manual review matrix

| Family | Sample paths | What to check | Status | Notes |
|---|---|---|---|---|
| Root skills | `skills/code-review/SKILL.md`, `skills/deep-tool-research/SKILL.md`, `skills/__contracts__/canonical-event-emitter/SKILL.md` | YAML first, SCOPE after YAML or YAML `scope`, triggers, H1/name fallback. | Passed | Manual sample parses cleanly; hardened parser now distinguishes YAML `scope` from prose `scope:`. |
| Package skills | `packages/adaptive-workflow/skills/self-review/SKILL.md`, `packages/document-sync/skills/doc-sync/SKILL.md`, `packages/verification-audit/skills/trust-audit/SKILL.md` | YAML first, SCOPE preserved, generated triggers plausible. | Passed | Structure parses cleanly. Some generated triggers are generic and can be refined later, but they are structurally valid. |
| Root rules | `rules/adversarial-review.md`, `rules/model-routing.md`, `rules/context-management.md` | Contextual Trigger exists and is not misleading. | Passed with caveat | Metadata-rich rules got concrete trigger patterns; metadata-poor rules got title-derived fallback triggers for structural compliance. |
| Package rules | `packages/document-sync/rules/doc-sync.md`, `packages/ecosystem-tools/rules/context7-auto-trigger.md` | Parser recognizes package rules; contextual trigger exists. | Passed | Parser now recognizes `packages/*/rules/*`. |
| Rule indexes | `rules/RULES-COMPACT.md`, `rules/ROADMAP.md` | Classified as `rule-index`, no contextual trigger required. | Passed | Parser distinguishes `rule-index` from normal rules. |
| Hooks | `hooks/claim-validator.sh`, `packages/adaptive-workflow/hooks/adaptive-bypass.sh`, `hooks/_lib/registration-allowlist.txt` | Real hooks parse as hooks; support files excluded. | Passed | Root and package hooks parse as hooks; registration allowlist is support. |
| Scripts | `scripts/align_skill_frontmatter.py`, `scripts/cos`, `scripts/cos-init.sh`, `scripts/postinstall.js` | Scope comment syntax correct for language; shebang preserved. | Passed | Python/bash/node examples preserve shebang and use language-appropriate SCOPE comments. |
| Script libs/support | `scripts/_lib/local-service.sh`, `scripts/shellcheck-baseline.txt` | Not counted as primitives. | Passed | `scripts/_lib/*` parses as `script-lib`; `.txt` support files parse as support. |
| Templates | `templates/project-templates/typescript/package.json.tmpl`, `templates/security-profiles/standard.json`, `templates/service-map.example.yaml` | No inline comments added; scope visible through structure manifest. | Passed | Manual samples are unmodified render targets; parser gets scope from `primitive-structure-scopes.yaml`. Added missing `templates/CLAUDE.md.template`. |
| Contract registry | `manifests/primitive-contracts.yaml`, `manifests/primitive-structure-scopes.yaml` | No role confusion; structure-scopes does not duplicate behavior contracts. | Passed | Reviewed `primitive-contracts.yaml`: 340 behavior/projection contracts. `primitive-structure-scopes.yaml` remains structural-only for comment-hostile templates. |

## Commands

```bash
.venv/bin/python scripts/primitive_parse_inventory.py --project-dir .
.venv/bin/python scripts/primitive_scope_classifier.py --project-dir .
.venv/bin/python scripts/primitive_scope_unknown_triage.py --project-dir .
.venv/bin/python -m pytest tests/unit/test_primitive_parser.py tests/unit/test_primitive_scope_unknown_triage.py tests/unit/test_primitive_scope_classifier.py -q
bash scripts/cos-registry-lock --project-dir . --audit
```

## Findings log

- Manual sample review found one parser hardening issue: generic regex detected prose/frontmatter `scope:` too broadly. Fixed parser to accept only explicit SCOPE comments or YAML frontmatter `scope`.
- Manual sample review found one missing comment-hostile template path: `templates/CLAUDE.md.template`. Added to `manifests/primitive-structure-scopes.yaml`.
- Manual review confirms `primitive-contracts.yaml` is behavior/projection registry, not the structural parser registry.
- Title-derived rule triggers are structurally valid but semantically shallow; future trigger-quality refinement can improve them without blocking structure standardization.

## Decisions made in this audit

- Accept YAML frontmatter `scope` as a valid skill scope marker when present.
- Do not add inline comments to JSON/TOML/YAML/rendered templates; use `primitive-structure-scopes.yaml`.
- Treat `scripts/_lib/*` and `.txt` baselines/allowlists as support, not primitives.
- Treat `rules/RULES-COMPACT.md` and `rules/ROADMAP.md` as `rule-index`.

## Final result

```json
{
  "primitive_total": 1188,
  "missing_scope_marker": 0,
  "structural_findings": {}
}
```

Validation passed on 2026-05-14:

```bash
.venv/bin/python -m pytest tests/unit/test_primitive_parser.py tests/unit/test_primitive_scope_unknown_triage.py tests/unit/test_primitive_scope_classifier.py -q
# 28 passed

bash scripts/cos-registry-lock --project-dir . --audit
# status: pass
```

Semantic taxonomy remains open and is tracked by ADR-314 triage: `total_unknown = 562`.
