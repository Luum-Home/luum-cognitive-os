# Script Exposure P2 Review — 2026-05-12

Source: `scripts/cos-script-exposure-audit --json` after P0/P1 closure and P2 refinement.

## Result

| Bucket | Count | Meaning |
|---|---:|---|
| `OK-classified-maintainer` | 48 | Maintainer tools already have lifecycle metadata or override rationale; no skill required by default. |
| `P2-runtime-route-undocumented` | 81 | Hook/router exposure exists but route/internal ownership is not yet explicit. |
| `P2-script-orchestrated` | 107 | Called by other scripts but not directly skill/hook/router exposed. |
| `P2-evidence-only` | 68 | Docs/tests evidence, no runtime route. |
| `P2-doc-only` | 27 | Documentation-only references. |
| `P2-test-only` | 17 | Test-only references. |

Total remaining P2: **300**.

## Interpretation

The important correction is that P2 is not one uniform backlog. The first slice
closed P0/P1 and proved no agentic primitive is both unrouted and unclassified.
For P2, the next safe move is not “create 300 skills”; it is:

1. Add explicit lifecycle/override classification for runtime-routed maintainer
   helpers that are intentionally internal.
2. Promote only grouped operator workflows to skills.
3. Archive or demote stale doc-only/test-only helpers after checking whether the
   doc/test reference is still meaningful.

## Recommended next slices

1. **Runtime-route documentation slice**: inspect the 81
   `P2-runtime-route-undocumented` rows and add route dispositions/lifecycle rows
   for hook/router-owned helpers.
2. **Script-orchestrated backend slice**: inspect the 107 `P2-script-orchestrated`
   rows and mark backend helpers as internal via overrides, leaving only top-level
   operator workflows as skill candidates.
3. **Evidence-only cleanup slice**: inspect 68 evidence-only + 27 doc-only + 17
   test-only rows for stale docs/tests or archive candidates.

## Validation

```bash
scripts/cos-script-exposure-audit --json
python3 -m pytest tests/unit/test_script_exposure_audit.py tests/behavior/test_script_exposure_audit_cli.py -q
```
