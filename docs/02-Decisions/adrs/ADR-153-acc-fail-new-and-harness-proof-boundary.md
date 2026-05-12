---

adr: 153
title: ACC Fail-New Gate and Harness Proof Boundary
status: accepted
implementation_status: implemented
date: 2026-05-04
supersedes: []
superseded_by: null
implementation_files:
  - scripts/acc_pipeline.py
  - tests/unit/test_acc_pipeline.py
  - docs/04-Concepts/architecture/agent-capability-coverage-pipeline.md
  - docs/09-Quality/manual-tests/acc-fail-new-gate.md
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

When enabled, ACC compares the current report to an existing baseline, defaulting to `docs/07-Capabilities/acc/latest.json`, before writing the new report. It blocks if the current run introduces:

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

- `--fail-new` requires a baseline file. First-time users must generate `docs/07-Capabilities/acc/latest.json` before ratcheting.
- A new intentionally local script/rule/skill may fail the strict gate until it receives an exact consumer-availability row or the operator consciously uses `--allow-new-local-defaults`.

## Operational Guide

### What changes for the operator

Before this ADR: ACC could reach full coverage for declared scope, but a new script silently inheriting a broad local default (e.g., `scripts/**` → SO-local) would pass ACC without any explicit lifecycle decision. Planned harnesses had no enforced boundary separating "roadmap" from "proven support."

After this ADR:

- **`--fail-new` mode** compares the current ACC run against a baseline (`docs/07-Capabilities/acc/latest.json` by default) and blocks if new debt or new broad-default-aligned rows appear:
  ```bash
  python3 scripts/acc_pipeline.py --project-dir . --refresh --fail-new
  ```
- To allow a new script that is intentionally SO-local without blocking: add it to `manifests/primitive-consumer-availability.yaml` with an explicit status before running `--fail-new`, or pass `--allow-new-local-defaults` for a one-time exemption (logged).
- The `new_debt` field in the report is machine-readable and lists exactly which new rows introduced debt.

### What this answers (and what it doesn't)

**Answers:**
- "Did my change introduce new ACC debt?" — Run `--fail-new`; exit code 0 means no new debt, non-zero lists what introduced it.
- "Is a planned harness treated as partial support in the report?" — No. Only harnesses with `status: implemented` in `manifests/harness-projection.yaml` are executed. Planned entries are roadmap-only.
- "What does the `new_debt` section contain?" — Rows where the current run has a worse status than the baseline, plus any new broad-default-aligned rows.

**Does not answer:**
- "Is the baseline itself correct?" — The baseline is `docs/07-Capabilities/acc/latest.json`; if it was generated while debt existed, it will tolerate that historical debt. Use `--baseline <file>` to choose a known-clean baseline.
- "What happens the first time `--fail-new` is run?" — It requires a baseline. Generate one with `python3 scripts/acc_pipeline.py --project-dir . --refresh` first, then start gating on it.

### Daily operational pattern

1. After adding any new script, rule, skill, or hook: explicitly classify it in `manifests/primitive-consumer-availability.yaml` before committing.
2. Run `python3 scripts/acc_pipeline.py --project-dir . --refresh --fail-new` as part of the pre-commit checklist.
3. If the gate fires, read the `new_debt` section in the output — it names the specific rows that crossed the threshold.
4. Fix by either: adding an explicit availability entry for the new primitive, or confirming it should be partial (and updating the baseline intentionally).

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
- `docs/09-Quality/manual-tests/acc-fail-new-gate.md` defines manual proof steps for baseline pass, missing-baseline block, and planned-harness non-promotion.
