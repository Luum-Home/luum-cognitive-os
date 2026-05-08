---
adr: 248
title: Control-Plane Audit Loop for ADR-239+ Primitive Drift
status: accepted
date: 2026-05-08
supersedes: []
superseded_by: null
extends: [ADR-239, ADR-240, ADR-247]
implementation_files:
  - manifests/control-plane-audits.yaml
  - scripts/cos-control-plane-audit
  - tests/unit/test_control_plane_audit.py
tier: maintainer
tags: [control-plane, audits, hooks, scheduler, primitive-coherence, adr-239-plus]
---
# ADR-248: Control-Plane Audit Loop for ADR-239+ Primitive Drift

## Status

Accepted — Slice A implemented.

## Context

ADR-239 and later ADRs define the right classes of protection: isolated write
worktrees, primitive coherence, history rewrite wrappers, post-rewrite push
markers, claim enforcement, chaos source guards, release freeze, and
manifest-driven postmortem audits.

The missing operational layer is a way to run those detectors precisely and
repeatedly without hand-invoking every script. The operator explicitly asked for
tools that can run from hooks or every N minutes to detect inconsistencies and
resolve the ADR-239+ backlog without hardcoding sensitive data or manually
fixing each primitive first.

## Decision

Introduce a manifest-driven control-plane audit runner:

```text
manifests/control-plane-audits.yaml
scripts/cos-control-plane-audit
```

The runner executes declared read-only audits by lane and aggregates their JSON
findings into one report. It is not a repair engine. It creates the stable
feedback loop that future hooks, cron jobs, launchd timers, or release-freeze
transactions can consume.

Slice A lanes:

- `hook-fast` — fast non-mutating checks suitable for lifecycle hooks.
- `hourly` — periodic local sweep for primitive drift.
- `pre-public` — release-readiness sweep that can include slower public-risk
  checks.

Slice A audits:

- `primitive-coherence` — `scripts/primitive-coherence-audit.py --json`.
- `postmortem-regressions` — `scripts/cos-postmortem-regression-audit --json`.
- `pre-public-risk` — `scripts/cos-pre-public-risk-audit --json` in the
  `pre-public` lane.

## Enforcement model

1. Audits declare `mutates: false`; mutating audit specs are blocked before
   execution.
2. Audits must emit JSON with an expected `schema_version`.
3. The runner returns block if any underlying audit has block findings.
4. Warnings remain warnings unless `--strict` is passed.
5. Sensitive values stay outside the manifest; audits may consume env-var names
   but not hardcoded private values.

## Hook and schedule integration

The runner is designed to be called by future hooks or timers:

```bash
scripts/cos-control-plane-audit --lane hook-fast --json
scripts/cos-control-plane-audit --lane hourly --json
scripts/cos-control-plane-audit --lane pre-public --json --strict
```

A hook should use `hook-fast`. A launchd/cron automation should use `hourly`.
A release transaction should use `pre-public`.

## Alternatives rejected

- **Run every audit from every hook** — rejected because heavy checks in hot
  paths cause operator fatigue and disablement.
- **Make each ADR install its own scheduler** — rejected because per-ADR timers
  recreate the incoherence problem at the scheduling layer.
- **Auto-fix findings directly from the runner** — rejected because ADR-240 and
  ADR-247 require detect-first/remediate-second with explicit commits.
- **Hardcode audit commands in shell hooks** — rejected because lanes and audit
  membership must be versioned in a manifest.

## Consequences

Positive:

- ADR-239+ detectors can run continuously without bespoke glue per ADR.
- Hooks and cron/launchd can consume the same audit lanes.
- A single report shows whether unresolved postmortem classes remain.
- Future remediation tools can consume stable finding codes.

Negative:

- The runner adds one more manifest to maintain.
- If an underlying audit is noisy, the aggregate lane is noisy.
- Hook integration must be careful to use only the fast lane.

## Verification

```bash
python3 -m pytest tests/unit/test_control_plane_audit.py tests/unit/test_postmortem_regression_audit.py tests/audit/test_adr_contracts.py -q
scripts/cos-control-plane-audit --lane hook-fast --json
```
