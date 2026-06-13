# Test Execution DX

Cognitive OS keeps full release confidence in CI while making local validation less disruptive on laptops.

## Local defaults

- `make test-targeted` runs `./cos-test focused --ci --no-color` and lets `cos-test` derive affected files from git diff, staged files, and uncommitted files.
- `make test-targeted-plan` adds `--dry-run` so maintainers can inspect the affected lane before paying test cost.
- `make test-laptop-bg` starts `make test-laptop` through `scripts/cos-test-laptop-bg`, writes logs under `.cognitive-os/reports/background-tests/`, records `latest.pid`, updates `latest.log`, and immediately returns the terminal.
- `make test-slow-report` aggregates persisted pytest JUnit timings from `.cognitive-os/reports/test-runs/**/junit.xml` into `.cognitive-os/reports/slow-tests/latest.json` and `.cognitive-os/reports/slow-tests/latest.md`.

## Quality boundary

Local targeted and background lanes are developer ergonomics. They do not replace release gates.

- Local: use `make test-targeted` for diff-driven work and `make test-laptop-bg` when a broad lane would otherwise block the machine.
- CI/pre-merge: use the broad non-Docker lane plus explicit integration and Docker lanes according to the release profile.
- Release: keep full broad lanes in CI and use the slow-test report to decide which tests belong in release-blocking fast, slow nightly, integration explicit, or optional explicit lanes.

## Slow-test interpretation

The slow-test report is observational. It recommends lane buckets using path and timing heuristics:

- `release-blocking-fast` for normal tests below the configured slow threshold.
- `slow-nightly-review` for tests whose max duration crosses the threshold.
- `integration-explicit` for integration/e2e/chaos paths.
- `optional-explicit` for benchmark, quality, or arena paths.

Recommendations require maintainer review before moving tests between lanes.
