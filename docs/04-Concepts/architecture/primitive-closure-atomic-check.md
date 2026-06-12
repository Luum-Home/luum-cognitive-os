# Primitive Closure Atomic Check

Cognitive OS primitives are cross-surface objects. A script, hook, skill, or rule is not closed until its canonical metadata and generated projections agree.

## Problem

Primitive changes used to fail one lane at a time:

- lifecycle metadata missing or weaker than the claim;
- portable `.ai/primitives` overlay stale;
- `skills/REGISTRY.lock` or `manifests/agentic-primitive-registry.lock.yaml` stale;
- ACC/readiness reports stale;
- `.claude/` or `.cognitive-os/` projections missing tracked files;
- new wrapper scripts lacking lifecycle rows;
- stale pytest `lastfailed` cache treated as current failure evidence;
- historical flicker metrics reported as active runtime warnings.

These were deterministic closure gaps, not random flaky tests.

## Command

Use this before broad validation when touching `scripts/`, `hooks/`, `skills/`, `rules/`, `templates/`, `agents/`, or primitive manifests:

```bash
scripts/cos-primitive-closure-check --repair --strict
```

For a read-only gate after repair:

```bash
scripts/cos-primitive-closure-check --strict
```

The command checks:

1. harness and derived-artifact gate;
2. agentic script wrappers have lifecycle metadata;
3. portable `.ai` overlay is current;
4. primitive and skill registry locks are current;
5. ACC can read generated readiness reports.

`--repair` refreshes the generated surfaces in the safe order:

1. `python3 scripts/acc_pipeline.py --refresh`;
2. `python3 scripts/portable_ai_overlay.py`;
3. `scripts/cos-registry-lock --write`;
4. all strict checks.

## Runtime flicker evidence

`cos-agent-flicker-report` now distinguishes active warning evidence from historical evidence:

- current skill drift against `skills/REGISTRY.lock` remains a warning;
- historical drift metrics with no current hash mismatch are informational;
- the latest claim-enforcer event must be blocking to warn;
- older claim blocks followed by passing verification are informational.

This preserves audit history without keeping the repo in a false WARN state.

## Pytest lastfailed evidence

Use this to distinguish active failures from stale cache:

```bash
scripts/cos-pytest-lastfailed-health --verify --clear-stale
```

The command deletes `.pytest_cache/v/cache/lastfailed` only after `pytest --lf` passes.

## Operator rule

Do not run `make test-laptop` as the first repair tool for primitive changes. Run the closure check first, then targeted tests, and only then a broad lane.
