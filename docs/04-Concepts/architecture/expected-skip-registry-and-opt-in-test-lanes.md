# Expected Skip Registry and Opt-In Test Lanes

This plan implements ADR-166: skipped tests are not removed wholesale; they are
classified and enforced.

## Operating Policy

Use `skip` only when the test is not applicable in the current lane:

- missing Docker, network, provider credentials, Engram, `jq`, `lsof`, `flock`,
  or other host tools;
- explicit Docker/provider/cloud/cost-bearing proof drills;
- `$HOME` mutation tests that must not run in normal laptop validation;
- runtime p95/sample-window checks without enough observations;
- optional profile artifacts that are absent in a valid install profile;
- documented grandfathering or self-check exceptions owned by another audit.

Do not use `skip` for known reproducible debt. Use:

- `xfail(strict=True)` when the behavior is known broken and tracked;
- a normal failing test when it should block now;
- deletion or rewrite when the claim no longer exists.

## Implementation Steps

1. Maintain `manifests/test-skip-registry.yaml` as the expected-skip source of
   truth.
2. Run `scripts/test_skip_registry.py --lane <lane> --junit <junit.xml>` after
   every pytest invocation made through `scripts/pytest-with-summary.sh`.
3. Write per-run artifacts next to the normal summary:
   - `skip-summary.json`
   - `skip-summary.md`
4. Fail the wrapper if pytest succeeded but any skip is unclassified.
5. Surface counts by category in `summary.txt`.

## Opt-In Lane Boundaries

| Lane/check | Default laptop? | Trigger |
|---|---:|---|
| Docker stack / compose / testcontainers | No | `make test-docker` or proof drill |
| Provider smoke / cost-bearing calls | No | `make test-optional` or explicit provider smoke |
| Engram Cloud Docker smoke | No | `scripts/cos-engram-cloud-docker-smoke` via proof drill |
| p95 runtime latency | Conditional | after enough runtime samples exist |
| Full integration/release | No | `make test-laptop-integration`, `make test-release` |

## Maintenance Checklist

When adding or editing a skipped test:

1. Ask if this is applicability or known debt.
2. If applicability, ensure the skip reason matches a registry entry.
3. If known debt, use `xfail(strict=True)` and link the owning ADR/report.
4. If the test is obsolete, delete or rewrite it.
5. Run the affected lane and inspect `skip-summary.md`.

## Acceptance Criteria

- `python3 -m pytest tests/unit/test_test_skip_registry.py -q` passes.
- A sample unknown skip causes `scripts/test_skip_registry.py --fail-unknown` to
  exit non-zero.
- `scripts/pytest-with-summary.sh` emits skip category counts into `summary.txt`
  when the JUnit file contains skipped tests.
- `make test-laptop` fails if a new skip reason does not match the registry.
