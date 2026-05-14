<!-- SCOPE: both -->
<!-- TIER: 2 -->
# Pre-Commit Coverage Gate

## Purpose

A git pre-commit hook that prevents committing when tests are failing and warns when coverage drops below threshold.

## Behavior

### Test Gate (blocking)

1. Runs `python3 -m pytest tests/ -q --tb=no` to get a summary line
2. If any tests **FAIL** -> blocks the commit (exit 1) with message `COMMIT BLOCKED: N tests failing`
3. If pytest errors or produces no recognizable output -> blocks the commit
4. If all tests pass -> proceeds to coverage check

### Coverage Gate (advisory)

1. Runs `bash tests/coverage-report.sh` and extracts the Composite coverage percentage
2. If coverage is below `COVERAGE_THRESHOLD` -> prints a WARNING but does NOT block
3. Default threshold is 80% (configurable via environment variable)

### Skip

Standard git `--no-verify` flag skips the hook entirely (handled by git, not the hook).

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `COVERAGE_THRESHOLD` | `80` | Minimum composite coverage % before warning |

## Installation

```bash
bash scripts/install-pre-commit.sh
```

This symlinks `hooks/pre-commit-gate.sh` to `.git/hooks/pre-commit`.

## Integration

- **Error Learning**: Test failures detected by this hook are not logged to error-learning.jsonl (it runs outside Claude sessions)
- **Coverage Report**: Uses the same `tests/coverage-report.sh` as the CI pipeline
- **Quality Gates**: Complements the agent-level quality gates with a developer-level gate

## Contextual Trigger

- When work relates to Pre-Commit Coverage Gate.
