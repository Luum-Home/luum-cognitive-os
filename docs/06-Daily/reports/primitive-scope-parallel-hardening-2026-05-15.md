# Parallel Primitive Scope Hardening — 2026-05-15

## Goal

Execute the six-step hardening pass requested for primitive scope classification:
medium-confidence audit, deterministic random audit tooling, CI ratchets,
primitive creator hardening, project bucket audit, and os-only projection audit.

## Parallel agent findings integrated

| Step | Finding | Action taken |
|---|---|---|
| 1. Medium-confidence audit | 229 medium rows, mostly single-source `consumer-availability`; risky groups include `install-*.sh`, `cos-*-local.sh`, hook/rule asymmetries, and generic-looking os-only skills. | Captured a medium-confidence sample report and left remaining ambiguous rows as review queue instead of blindly changing markers. |
| 2. Random audit tooling | Manual random review needs reproducibility. | Added `scripts/primitive_scope_random_audit.py` and `scripts/primitive-scope-random-audit` with seeded JSON/Markdown output. |
| 3. CI ratchet | `scripts/cos status --portability --json` can report projection blocks without failing. | Added direct strict classifier, strict scope projection, both-portability, and install-projection commands to CI/local CI. |
| 4. Primitive creators | `primitive-authoring` is the shared standard; several creators/promoters bypassed exact-path classifier/proof language. | Hardened add-rule, skill-creator, primitive-harvester, scaffold/init, synthesize/repair skill, dynamic-tool creation, prompt composition, and generator code prompts. |
| 5. Project bucket audit | 55 project rows: 21 high, 34 medium. Medium rows are mostly project templates with projected consumer surface but no second evidence source. | Generated a full project-bucket review report; no immediate marker flips from the sampled evidence. |
| 6. os-only projection audit | 34 `hooks/_lib/*` files were projected into consumer installs while marked `SCOPE: os-only`. | Reclassified those helper libraries to `SCOPE: both` and updated consumer/lifecycle metadata as shared runtime support primitives. |

## Generated reports

- `docs/06-Daily/reports/primitive-scope-random-audit-2026-05-15.json`
- `docs/06-Daily/reports/primitive-scope-random-audit-2026-05-15.md`
- `docs/06-Daily/reports/primitive-scope-project-bucket-audit-2026-05-15.json`
- `docs/06-Daily/reports/primitive-scope-project-bucket-audit-2026-05-15.md`
- `docs/06-Daily/reports/primitive-scope-medium-sample-2026-05-15.json`
- `docs/06-Daily/reports/primitive-scope-medium-sample-2026-05-15.md`

## Current classifier state after changes

```json
{
  "total": 1209,
  "by_suggested_scope": {"both": 531, "os-only": 623, "project": 55},
  "by_confidence": {"high": 986, "medium": 223},
  "contradictions": 0,
  "low_confidence": 0
}
```

## Remaining debt

- Review medium-confidence `install-*.sh` and `cos-*-local.sh` scripts manually; they should not be `both` merely because they are useful.
- Add second evidence sources for 34 medium project rows, mainly project templates.
- Add hook/rule dependency asymmetry detector for cases like project/both hooks relying on os-only rules.
- Decide whether batch portability proof should keep counting for medium rows or be downgraded unless a primitive-specific test exists.

## Acceptance criteria executed

- Strict classifier with `--fail-contradictions --fail-low-confidence`.
- Strict both-portability audit.
- Strict projection audit with install smoke.
- Install projection audit.
- Unit/contract/integration tests for classifier, random audit, scope projection, and install projection.
