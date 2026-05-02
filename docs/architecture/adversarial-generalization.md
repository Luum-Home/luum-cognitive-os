# Adversarial Generalization MVP

> Status: local fixture-backed MVP. The runner generates concrete scenario workspaces and evaluates deterministic local checks; it does not call models.

This lane tests whether Cognitive OS survives messy, novel, adversarial tasks rather than only known contract tests. The important property is that scenarios become real local fixtures under `.cognitive-os/generated/adversarial-scenarios`, not just prompt/oracle text.

## Scenario families

- prompt injection
- conflicting memory
- ambiguous instructions
- distractor context
- incomplete tests
- over-broad change temptation
- tool poisoning
- novel local APIs
- long-horizon context degradation
- stale docs versus code
- malicious skills
- lethal trifecta

## How it works

1. `scripts/run-adversarial-generalization.sh` loads `.cognitive-os/tests/adversarial-generalization/scenarios.yaml`.
2. Each scenario is materialized by `lib.adversarial_rubric.generate_fixture` into `.cognitive-os/generated/adversarial-scenarios/{scenario_id}`.
3. `lib.adversarial_rubric.evaluate_fixture` evaluates local artifacts. Security families exercise the real lethal-trifecta classifier; other families verify concrete repo/memory/distractor/scope/acceptance fixtures.
4. A Markdown report is written to `.cognitive-os/reports/adversarial-generalization-report.md` and the runner exits non-zero on any failed fixture.

## Runtime surface

- Manifest: `.cognitive-os/tests/adversarial-generalization/scenarios.yaml`
- Rubric/generator/evaluator: `lib/adversarial_rubric.py`
- Single-fixture CLI: `scripts/generate_adversarial_scenario.py`
- Suite runner: `scripts/run-adversarial-generalization.sh`
- Tests: `tests/behavior/test_adversarial_generalization_manifest.py`
