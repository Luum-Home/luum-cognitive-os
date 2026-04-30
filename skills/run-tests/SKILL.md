<!-- SCOPE: both -->
---
name: run-tests
description: Auto-detect project test framework and run tests with structured reporting
invoke: /run-tests
version: 1.1.0
audience: project
triggers: ["/run-tests", "/test", "/tests"]
---

# /run-tests

> Detect and run the project's test suite with structured pass/fail reporting.

## Cognitive OS canonical entry (ADR-072)

When running inside the Cognitive OS repo (i.e., `cmd/cos-test/` exists or the `cos-test`
binary is on PATH or built at `./cos-test`), **prefer `cos-test`** over direct pytest:

| Mode | Command | When to use |
|---|---|---|
| Focused | `cos-test focused` | Single-file edit or tight iteration loop (<30 s) |
| Cluster | `cos-test cluster --lane <name>` | Validate one lane (unit, audit, contract, …) |
| Broad | `cos-test broad` | Full pre-push sweep |

**Fallback**: if the `cos-test` binary is not present and cannot be built (non-COS project
or Go toolchain absent), fall back to direct pytest as described in the steps below.

Detection order:
1. `cos-test` on PATH? → use it.
2. `./cos-test` binary present? → use it.
3. `cmd/cos-test/` directory present + `go` available? → build with `cd cmd/cos-test && go build -o ../../cos-test .`, then use it.
4. None of the above? → fall back to framework auto-detection below.

## What It Does

Auto-detects the test framework from project files, runs the test suite, and reports structured results (pass/fail/skip counts, coverage, failure details). Works with any project regardless of language or framework.

## Usage

```
/run-tests                      # Run all tests with auto-detected framework
/run-tests path/to/test         # Run specific test file or directory
/run-tests --coverage           # Run with coverage enabled
/run-tests --watch              # Run in watch mode (if framework supports it)
```

## Instructions

### Step 1: Detect test framework

Use `lib/test_framework_detector.py` to identify the project's test framework:

```python
from lib.test_framework_detector import TestFrameworkDetector

detector = TestFrameworkDetector()
frameworks = detector.detect(".")
primary = detector.detect_primary(".")
```

If no framework is detected, inform the user and suggest creating test configuration.

If multiple frameworks are detected, show the list and use the primary (highest confidence).

Report to the user:
```
Detected: {framework.name} (confidence {confidence}%)
Config:   {framework.config_file}
Command:  {framework.command}
```

### Step 2: Determine the command

Based on user input and detected framework:

| User request | Command to use |
|-------------|---------------|
| `/run-tests` | `framework.command` |
| `/run-tests path/to/file` | `framework.command_for_path("path/to/file")` |
| `/run-tests --coverage` | `framework.coverage_command` (fall back to `framework.command` if None) |
| `/run-tests --watch` | `framework.watch_command` (inform user if None) |

### Step 3: Run tests

Execute the test command via Bash.

- For test suites that typically take >30 seconds (large projects, integration tests), use `run_in_background: true` and check back when notified.
- Pipe output through `tail -100` if the framework is verbose, to stay within context limits.
- Always capture exit code to determine pass/fail.

### Step 4: Parse results

Extract pass/fail/skip counts from the output. Common patterns:

| Framework | Pass pattern | Fail pattern |
|-----------|-------------|-------------|
| pytest | `N passed` | `N failed` |
| jest/vitest | `Tests: N passed` | `Tests: N failed` |
| go test | `ok` (per package) | `FAIL` (per package) |
| cargo test | `test result: ok. N passed` | `N failed` |
| rspec | `N examples, 0 failures` | `N failures` |
| gradle/maven | `BUILD SUCCESSFUL` | `BUILD FAILED` |

### Step 5: Report results

Output a structured report:

```
TEST RESULTS: {framework.name}
  Status:  PASS | FAIL
  Passed:  N
  Failed:  N
  Skipped: N
  Total:   N
  Time:    Ns
```

If tests failed, show the last 30 lines of output to help diagnose.

If `--coverage` was used and coverage data is available, include:

```
COVERAGE:
  Lines:    N%
  Branches: N%
```

### Step 6: Handle failures

If tests fail:
1. Show the failure summary (last 30 lines of output)
2. If the failure count is small (<5), suggest investigating specific failures
3. If the failure count is large (>20), suggest running a subset first

## Framework Detection Table

| File | Framework | Command |
|------|-----------|---------|
| `pytest.ini`, `pyproject.toml` with `[tool.pytest]`, `conftest.py` | pytest | `python -m pytest` |
| `package.json` with "test" script | npm/yarn/bun | `{runner} test` |
| `vitest.config.*` | vitest | `npx vitest run` |
| `jest.config.*` | jest | `npx jest` |
| `go.mod` | go test | `go test ./...` |
| `Cargo.toml` | cargo test | `cargo test` |
| `build.gradle*` | gradle | `./gradlew test` |
| `pom.xml` | maven | `mvn test` |
| `mix.exs` | mix test | `mix test` |
| `.rspec` or `spec/` + `Gemfile` | rspec | `bundle exec rspec` |
| `Makefile` with test target | make | `make test` |

## Notes

- This skill has NO dependency on Cognitive OS infrastructure. It works standalone in any project.
- The detection library is at `lib/test_framework_detector.py` and can be used programmatically.
- When multiple frameworks are detected (e.g., pytest + go test in a polyglot repo), the primary is chosen by confidence score. The user can override by specifying a path that targets a specific framework.
