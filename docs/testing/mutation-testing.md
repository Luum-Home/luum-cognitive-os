# Mutation Testing

## What is mutation testing?

Mutation testing measures how well your tests actually verify behavior. It works by making small changes ("mutations") to your source code — replacing `>` with `<`, deleting a return statement, swapping `True` for `False` — and checking whether your tests catch the change. If a test fails after a mutation, the mutant is "killed." If all tests still pass, the mutant "survives," meaning your tests don't actually verify that behavior.

## Why we use it

We observed that many tests in the codebase are **structural-only**: they check that files exist, that config contains certain strings, or that sections have the right headers. These tests provide zero protection against logic bugs because they never exercise the code's behavior. Mutation testing quantifies this gap objectively.

Current baseline: ~34% kill rate on `lib/rate_limiter.py`. Target: 60%+ for new code.

## CI gate

The GitHub Actions workflow `.github/workflows/test-quality.yml` runs two checks on every PR:

1. **Structural test detector** — fast static analysis that flags test files containing only existence/content checks. Blocks merge if new tests are purely structural.
2. **Mutation testing** — runs cosmic-ray on changed `lib/*.py` files (max 5 per PR for speed). Blocks merge if mutation kill rate is below 40%.

## Running locally

### Structural test detector

```bash
# Check all test files
python scripts/check-test-quality.py

# Check specific files
python scripts/check-test-quality.py tests/test_rate_limiter.py

# Simulate CI mode (only new tests vs main)
python scripts/check-test-quality.py --ci
```

### Mutation testing with cosmic-ray

```bash
# Install
pip install cosmic-ray pytest

# Initialize, execute, report
cosmic-ray init .cosmic-ray.toml db.sqlite
cosmic-ray exec .cosmic-ray.toml db.sqlite
cr-report db.sqlite
```

To test a single module, create a temporary config:

```toml
[cosmic-ray]
module-path = "lib/rate_limiter.py"
timeout = 30
test-command = "python -m pytest tests/unit/test_rate_limiter.py -x -q"

[cosmic-ray.distributor]
name = "local"
```

Then run:

```bash
cosmic-ray init /tmp/cr-single.toml /tmp/cr.sqlite
cosmic-ray exec /tmp/cr-single.toml /tmp/cr.sqlite
cr-report /tmp/cr.sqlite
```

## Writing tests that kill mutants

A test kills a mutant when it asserts on the **return value or side effect** of the code under test. Compare:

```python
# Structural (survives all mutations):
def test_rate_limiter_exists():
    assert Path("lib/rate_limiter.py").exists()

# Behavioral (kills mutants):
def test_rate_limiter_blocks_excess():
    rl = RateLimiter(max_calls=2, period=1.0)
    assert rl.allow() is True
    assert rl.allow() is True
    assert rl.allow() is False  # kills boundary mutations
```

Guidelines for behavioral tests:
- Assert on return values from the function under test
- Assert on exceptions raised for invalid input
- Assert on state changes (object attributes, database rows, file contents after an operation)
- Use `pytest.raises` for error paths
- Avoid asserting only on file existence or string containment in source files

## Thresholds

| Metric | Current | Target |
|--------|---------|--------|
| Mutation kill rate (new code) | 40% min | 60%+ |
| Structural-only test files | blocked | 0 |
