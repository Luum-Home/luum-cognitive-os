---

adr: 166
title: Expected Skip Registry and Opt-In Test Lanes
status: implemented
implementation_status: implemented
date: 2026-05-05
supersedes: []
superseded_by: null
implementation_files:
  - manifests/test-skip-registry.yaml
  - scripts/test_skip_registry.py
  - scripts/pytest-with-summary.sh
  - docs/04-Concepts/architecture/expected-skip-registry-and-opt-in-test-lanes.md
  - tests/unit/test_test_skip_registry.py
tier: maintainer
tags: [testing, validation, skips, laptop-lane, opt-in-lanes]
---

# ADR-166: Expected Skip Registry and Opt-In Test Lanes

## Status

**Implemented for the first enforcement slice** — 2026-05-05.

This ADR does not require eliminating every skipped test. It makes skipped tests
classified, summarized, and enforceable so new unclassified skips fail the local
validation wrapper.

## Context

`make test-laptop` is intentionally broad but laptop-safe: it avoids Docker,
network, provider credentials, `$HOME` mutation, high-cost lanes, and runtime
checks that need long sample windows. That means a successful laptop run can
include many `skipped` tests. The raw skip count is not actionable by itself:
legitimate environment gates and opt-in proof drills look the same as accidental
or lazy skips.

The maintainer need is:

- keep legitimate skips for Docker, network, credentials, `$HOME` mutation,
  runtime samples, and proof drills;
- fail when a new skip is introduced without classification;
- distinguish skipped environment gates from reproducible product debt;
- keep default lanes fast while preserving explicit heavier lanes.

## Decision

Introduce an expected-skip registry and enforce it from the pytest summary
wrapper used by `cos-test`.

The registry lives at `manifests/test-skip-registry.yaml`. Each expected skip
entry declares:

- category;
- matching lanes;
- reason pattern;
- activation condition;
- opt-in lane or repair path.

Allowed categories are:

| Category | Meaning |
|---|---|
| `external-dependency` | Host tool, package, service, or credential is absent in the current lane. |
| `opt-in-lane` | Test belongs to explicit Docker, network, provider, HOME-mutating, or cost-bearing validation. |
| `runtime-sample-precondition` | Runtime metrics/sample windows are insufficient for a statistical assertion. |
| `optional-runtime-state` | Optional profile artifacts or hooks are absent in a valid profile/lane. |
| `policy-exemption` | Grandfathered, intentionally exempt, or self-check case documented by an audit policy. |

`skip` remains valid only for conditional applicability. Reproducible known debt
must be modeled as `xfail(strict=True)` or as a normal failing test. Tests that
no longer represent a product claim should be deleted or rewritten.

## Implementation

`scripts/test_skip_registry.py` parses a JUnit XML file, classifies each skipped
test against the registry, writes `skip-summary.json` and `skip-summary.md`, and
returns non-zero when an unknown skip appears under enforcement.

`scripts/pytest-with-summary.sh` now runs the registry after pytest when invoked
with a lane, adds category counts to `summary.txt`, and changes the run exit code
to failure if pytest passed but unclassified skips exist.

The first slice uses reason-pattern classification rather than exact per-test
node IDs. This keeps the manifest maintainable while still blocking new kinds of
unexplained skip reasons.

## Consequences

### Positive

- `make test-laptop` can keep legitimate skips without hiding new skip classes.
- Operators see skip counts by category in the normal run summary.
- Docker/provider/Engram/p95 checks remain explicit opt-in lanes.
- The policy creates a path to migrate bad skips to `xfail(strict=True)` or real
  failures.

### Negative

- Reason-pattern matching can be too permissive if entries become broad. The
  registry must stay reviewed.
- Some existing skips need later cleanup from coarse patterns into narrower
  entries if they become ambiguous.
- More metadata exists around tests, but it prevents a worse failure mode: silent
  growth of skipped validation.

## Follow-up

1. Add a periodic audit that reports matched skip counts by rule and highlights
   rules that are too broad.
2. Add explicit opt-in proof lanes for Docker, provider smoke, Engram Cloud,
   p95 runtime, and full integration where they do not already exist.
3. Review old skips and migrate reproducible product debt to `xfail(strict=True)`.
4. Delete tests whose product claim no longer exists.

## Operational Guide

### What changes for the operator

Before this ADR, `make test-laptop` could silently accumulate new skip classes — Docker env gates and accidental/lazy skips looked identical in raw output. After this ADR:

- `manifests/test-skip-registry.yaml` is the machine-readable registry of allowed skip categories (`external-dependency`, `opt-in-lane`, `runtime-sample-precondition`, `optional-runtime-state`, `policy-exemption`).
- `scripts/test_skip_registry.py` parses the JUnit XML output, classifies each skipped test against the registry, writes `skip-summary.json` and `skip-summary.md`, and returns non-zero when an unclassified skip appears under enforcement.
- `scripts/pytest-with-summary.sh` now runs the registry after pytest, adds category counts to `summary.txt`, and changes the run exit code to failure if pytest passed but unclassified skips exist.
- A new `skip` is only valid for conditional applicability. Reproducible known debt must be modeled as `xfail(strict=True)` or as a normal failing test.

### What this answers (and what it doesn't)

**Answers:**
- "Is this skip legitimate or accidental?" — check `manifests/test-skip-registry.yaml`; if the skip reason matches an entry, it is classified; if not, the wrapper fails and the category must be declared.
- "How many skips are Docker/provider/network vs. product debt?" — read `skip-summary.md` in the test report directory; counts appear by category.
- "Why did `make test-laptop` exit non-zero even though pytest passed?" — an unclassified skip was introduced; check `skip-summary.json` for the unknown reason pattern.

**Does not answer:**
- Whether an individual test's skip reason is correct — reason-pattern matching is the first slice; exact node-ID matching is a follow-up.
- Whether it is safe to promote a skip to `xfail(strict=True)` — that is an engineering judgment; the registry documents the path but does not automate the migration.

### When sources disagree

- **Registry says skip is classified but test author disagrees**: the category in `manifests/test-skip-registry.yaml` is authoritative. Update the entry's `reason` or `category` to match the actual intent, then re-run.
- **`make test-laptop` passes locally but fails in CI on skip classification**: the reason string in the pytest output must match a pattern in the registry. Run `scripts/pytest-with-summary.sh` locally with the same lane flag to reproduce; compare `skip-summary.json` entries against `manifests/test-skip-registry.yaml` patterns.

## Alternatives rejected

- Eliminate every skipped test immediately — rejected because many skips are correct applicability gates for Docker, network, credentials, HOME mutation, runtime sample windows, and proof drills.
- Keep raw skip counts without classification — rejected because raw counts cannot distinguish legitimate environment gates from accidental validation loss.
- Track every skip by exact node ID only — rejected for the first slice because reason-pattern classes solve the immediate governance problem with less manifest churn.

### Eliminate every skipped test immediately

Rejected. Many skips are correct applicability gates for Docker, network,
credentials, HOME mutation, runtime sample windows, and proof drills. Forcing
all of them into default laptop validation would make the lane slow, flaky, or
unsafe.

### Keep raw skip counts without classification

Rejected. Raw counts do not distinguish legitimate environment gates from lazy
or accidental skips, so maintainers cannot tell whether validation quality is
improving or decaying.

### Track every skip by exact node ID only

Rejected for the first slice. Exact node IDs are useful later, but the current
problem is unclassified skip classes. Reason-pattern classification gives a
smaller durable registry while still failing new unexplained skip reasons.

## Verification

```bash
python3 -m pytest tests/unit/test_test_skip_registry.py -q
```

```bash
COS_TEST_REPORT_DIR="$(mktemp -d)/reports" COS_PYTEST_NO_RERUN=1   bash scripts/pytest-with-summary.sh --workers 0 --lane contract --   tests/contracts/test_p95_hook_latency.py   tests/contracts/test_redteam_portability_coverage.py -q
```

The first command proves the registry script accepts known skips and rejects
unknown skips. The second command proves the pytest wrapper emits
`skip-summary.json`, `skip-summary.md`, and category counts in `summary.txt` for
a real lane with expected skips.
