# Full Suite Validation Report — 2026-04-23

## Summary

The full Cognitive OS validation pass is not fully green yet. Core portability
and product-proof paths passed, but the historical Python test surface still has
substantial legacy, environment, and contract drift failures.

## Commands Run

- `python3 -m pytest tests/ -n auto -q --tb=short --disable-warnings --timeout=120 --timeout-method=thread --session-timeout=2400 --durations=50`
- `go test ./... -count=1`
- `bash -n hooks/*.sh scripts/*.sh bin/cognitive-os.sh install.sh`
- `LANGFUSE_ENCRYPTION_KEY=<dummy-64-hex> docker compose -f docker-compose.cognitive-os.yml config --quiet`
- `bash scripts/demo-first-run-onboarding.sh --harness=codex`
- `bash scripts/demo-portability-proof.sh`
- `python3 -m pytest tests/audit/test_skills_contracts.py tests/audit/test_hooks_contracts.py tests/audit/test_rules_enforcement.py tests/architecture/test_wiring.py tests/behavior/test_claude_md_diet.py tests/behavior/test_efficiency_profiles.py tests/unit/test_efficiency_stress.py::TestTokenBudgets::test_no_orphan_references_in_compact tests/integration/test_consolidation_external.py::TestExternalProjectSimulation::test_core_rules_match_self_install_constant -q --tb=short --disable-warnings`

## Results

| Lane | Result | Evidence |
|---|---:|---|
| Go full suite | PASS | All Go packages passed with `go test ./... -count=1`. |
| Structural checks | PASS | Bash syntax, YAML loading, and Docker Compose config passed. |
| Codex first-run onboarding demo | PASS | Fresh Codex install completed in 9.3s total, under the 40s budget. |
| Portability proof demo | PASS | Codex and Claude projections produced matching core fingerprints. |
| Audit/wiring repair target | PASS | `1166 passed, 80 skipped`. |
| Python full suite | FAIL | `10629 passed, 1274 skipped, 18 xfailed, 195 failed` in 8m48s. |

## What Was Fixed In This Pass

- Skill contract tests now accept the repository's leading `<!-- SCOPE: ... -->`
  loader comment before YAML frontmatter.
- Catalog sync validates both legacy table entries and bullet-list entries.
- Hook and rule audit contracts read the explicit registration allowlist instead
  of treating every non-default hook as an accidental orphan.
- Runtime-generated JSONL references in rules are no longer treated as missing
  source files.
- `hooks/self-install.sh` now writes relative symlinks for self-hosting
  projections, avoiding machine-specific absolute paths in tracked projections.
- Declarative patterns moved to `docs/04-Concepts/patterns/` remain documented patterns,
  not recreated enforceable rules.

## Remaining Failure Families

The Python full-suite failures cluster around these areas:

- Auto-update and installer/update flows.
- Legacy efficiency-profile and hook-registration expectations.
- Code-review and security skill frontmatter expectations.
- Telemetry/data-pipeline feedback-loop tests.
- Safety-mesh behavior tests with older scoring assumptions.
- Manifest, coverage-report, and live component-usage tests.
- Fresh-install canary failures where full profile reports missing hooks.
- Parallel xdist worker instability around release/check canary tests.

## Doctrine

Finding failures outside the immediate task is product evidence, not noise. The
right policy is:

- Do not claim full-suite health while these failures remain.
- Keep the smaller product-core lanes green and documented.
- Convert broad-suite failures into explicit repair slices instead of allowing
  them to remain an unbounded background concern.
- Prefer fixing stale tests/contracts when product behavior intentionally moved,
  and fixing runtime behavior when tests expose a real product promise gap.

## Next Repair Slices

1. Fix fresh-install canary/full-profile hook-missing failures.
2. Reconcile legacy efficiency-profile tests with the current default/full
   profile model.
3. Repair skill frontmatter tests for `code-review`, `pr-review`,
   `pentest-self`, and `semgrep-scan` without weakening the SKILL.md contract.
4. Triage telemetry/data-pipeline tests for Python 3.14 and temp-dir isolation.
5. Re-run the full Python suite after each slice and reduce the failure count
   monotonically.
