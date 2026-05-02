# Adversarial Generalization MVP

> Status: MVP implemented as deterministic scenario manifest, generator, rubric, and report runner.

This lane tests whether Cognitive OS survives messy, novel, adversarial tasks rather than only known contract tests.

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

## Runtime surface

- Manifest: `.cognitive-os/tests/adversarial-generalization/scenarios.yaml`
- Rubric: `lib/adversarial_rubric.py`
- Generator: `scripts/generate-adversarial-scenario.py`
- Runner: `scripts/run-adversarial-generalization.sh`
- Tests: `tests/behavior/test_adversarial_generalization_manifest.py`
