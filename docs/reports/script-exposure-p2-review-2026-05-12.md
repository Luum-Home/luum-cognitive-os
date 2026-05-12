# Script Exposure P2 Review — 2026-05-12

Source: `scripts/cos-script-exposure-audit --json` after full ADR-283 P2 disposition review.

## Result

| Bucket | Count | Meaning |
|---|---:|---|
| `OK-classified-maintainer` | 48 | Maintainer tools already have lifecycle metadata or override rationale; no skill required by default. |
| `OK-documented-route` | 91 | Hook/router/operator route has an explicit manual disposition; no skill required by default. |
| `OK-internal-backend` | 73 | Python backend helper is owned by wrapper/orchestrator consumers; direct skill surface would be noise. |
| `OK-operator-workflow` | 34 | Top-level shell/no-extension workflows are explicit maintainer/operator workflows rather than narrow skills. |
| `OK-documented-maintainer` | 95 | Doc/manifest/test-backed maintainer tools remain active documented surfaces; no archive without stale evidence proof. |
| `OK-test-fixture` | 17 | Test-only scripts are classified as fixture/smoke targets; no skill required by default. |
| `P2-script-orchestrated` | 0 | Unresolved script-orchestrated maintainer tools. |
| `P2-evidence-only` | 0 | Unresolved docs/tests evidence-only maintainer tools. |
| `P2-doc-only` | 0 | Unresolved documentation-only maintainer tools. |
| `P2-test-only` | 0 | Unresolved test-only maintainer tools. |

Total remaining P2: **0**.

## Final disposition policy

- Do not create one skill per maintainer helper. Promote only grouped workflows that agents should intentionally invoke.
- `internal_backend` is for implementation modules behind wrappers/orchestrators.
- `operator_workflow` is for top-level maintainer/operator workflows where the workflow itself is the surface.
- `documented_maintainer_tool` is for active doc/manifest/test-backed tools; this prevents blind archival while keeping the invocation story explicit.
- `test_fixture` is for scripts whose current consumer is a test or smoke contract.

## Outcome

ADR-283 now has no P0, P1, or P2 findings. Remaining non-OK rows are the expected P3 role exceptions for lab, migration-only, and driver-specific scripts.

## Validation

```bash
python3 -m py_compile lib/script_exposure_audit.py scripts/cos-script-exposure-audit
python3 -m pytest tests/unit/test_script_exposure_audit.py tests/behavior/test_script_exposure_audit_cli.py -q
scripts/cos-script-exposure-audit --json
```
