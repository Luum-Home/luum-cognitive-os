---
adr: 153
title: ACC Fail-New Gate and Harness Proof Boundary
status: accepted
date: 2026-05-04
supersedes: []
superseded_by: null
implementation_files:
  - scripts/acc_pipeline.py
  - tests/unit/test_acc_pipeline.py
  - docs/architecture/agent-capability-coverage-pipeline.md
  - docs/manual-tests/acc-fail-new-gate.md
tier: maintainer
tags: [acc, fail-new, harness, projection, consumer-availability]
---

# ADR-153: ACC Fail-New Gate and Harness Proof Boundary

## Status

**Accepted** — 2026-05-04

## Context

ADR-152 allowed ACC to report full coverage for the declared scope by using explicit consumer-availability rows plus broad local-surface defaults such as `scripts/**`, `rules/*.md`, and `skills/**/SKILL.md`. That resolved existing debt, but it left two uncertainties:

1. New files could silently inherit broad local defaults and appear aligned without a human or agent making an explicit lifecycle/projection decision.
2. Planned harnesses could be listed in the roadmap and manifest, but they still must not be interpreted as real support until a driver and temp-project proof exist.

## Decision

Add a strict `--fail-new` mode to `scripts/acc_pipeline.py`.

When enabled, ACC compares the current report to an existing baseline, defaulting to `docs/acc/latest.json`, before writing the new report. It blocks if the current run introduces:

- new `missing`, `partial`, `stale`, `overexposed`, or `unverified` capability debt;
- new findings with those statuses;
- new capabilities that are `aligned` only because they matched a broad consumer-availability pattern, unless the operator explicitly passes `--allow-new-local-defaults`.

This makes local-surface defaults safe as a migration baseline while preventing them from becoming a permanent escape hatch for new agentic primitive surfaces.

The harness boundary remains unchanged: only harnesses with `status: implemented` in `manifests/harness-projection.yaml` are executed by the consumer-projection adapter. Planned harnesses remain roadmap entries and report as unverified until they have native driver or wrapper proof.

## Consequences

### Positive

- New ACC debt can be blocked incrementally without reopening all historical classifications.
- Broad local defaults become ratcheted: existing rows are tolerated, new broad-default rows require explicit review.
- The ACC report now carries a `new_debt` section for machine-readable gate evidence.

### Negative

- `--fail-new` requires a baseline file. First-time users must generate `docs/acc/latest.json` before ratcheting.
- A new intentionally local script/rule/skill may fail the strict gate until it receives an exact consumer-availability row or the operator consciously uses `--allow-new-local-defaults`.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Remove broad defaults immediately | Too disruptive during reconstruction; many existing SO-local surfaces are legitimate. |
| Trust `--fail-on-warn` only | It blocks current debt but does not distinguish new debt from historical tolerated debt. |
| Treat planned harnesses as partial support | Overclaims portability; planned means product scope only, not executable support. |

## Verification

```bash
python3 -m pytest tests/unit/test_acc_pipeline.py tests/contracts/test_acc_pipeline_contract.py -q
python3 -m py_compile scripts/acc_pipeline.py
python3 scripts/acc_pipeline.py --project-dir . --brief --fail-new
python3 scripts/acc_pipeline.py --project-dir . --refresh --fail-new
```

## Implementation Evidence

- `scripts/acc_pipeline.py` implements `--fail-new`, `--baseline`, `--allow-new-local-defaults`, `new_debt`, and strict broad-default detection.
- `tests/unit/test_acc_pipeline.py` covers new partial debt, broad local-default debt, and gate mutation.
- `docs/manual-tests/acc-fail-new-gate.md` defines manual proof steps for baseline pass, missing-baseline block, and planned-harness non-promotion.
