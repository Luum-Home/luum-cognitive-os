---
name: test-efficiency
description: SO-maintainer workflow for choosing targeted Cognitive OS test groups before heavy laptop/release lanes.
version: 1.0.0
tags: [testing, efficiency, cognitive-os-maintainers]
---

# Test Efficiency

Use this only while maintaining Cognitive OS itself.

## Workflow

1. Generate a plan before broad validation:

```bash
scripts/cos-test-efficiency-plan --from-git --commands --include-final-laptop
```

2. Run groups in order. If a group fails, stop broad execution.
3. Collect all failures from that group.
4. Repair the batch.
5. Rerun that group or the failed node IDs, not `make test-laptop`.
6. For suite-wide contract repair, use the bounded serial repair lane before any parallel full rerun:

```bash
scripts/cos-pytest-serial-repair tests/ --timeout-seconds 600 --maxfail 1
```

If it exits `124`, check whether it reported `PYTEST_CHUNK_TIMEOUT` or `PYTEST_BUDGET_EXHAUSTED`; rerun the same command to resume saved progress instead of repeating from zero.
7. Only after targeted groups and the serial repair lane pass, run the full SO
   lane through the bounded repair primitive, not as an unbounded direct command:

```bash
scripts/cos-test-repair-loop --full-command "make test-laptop" --timeout-seconds 2400 --require-clean-start
```

If this reports `TEST_REPAIR_LOOP_REPAIR_REQUIRED`, repair the failures, rerun
the exact failed node IDs shown by `TEST_REPAIR_LOOP_FAILED_NODEIDS`, then rerun
the same `scripts/cos-test-repair-loop ...` command. Repeat until the full lane
prints `TEST_REPAIR_LOOP_PASS`. If it reports `TEST_REPAIR_LOOP_TIMEOUT`, treat
the timeout itself as the failing primitive: isolate the timed-out node/file,
repair or quarantine via the skip registry, and rerun the loop.

8. Do not treat “run all tests” as a single fire-and-forget command. In SO
   maintenance, it means the full repair loop: bounded full run → exact failing
   node reruns → repair → exact rerun → full rerun.

## Failure file flow

```bash
make test-laptop 2>&1 | tee /tmp/test-laptop.log
scripts/cos-test-efficiency-plan --failure-file /tmp/test-laptop.log --commands
```

Use the emitted groups to repair/rerun targeted lanes.

## Contextual Trigger

Keywords: make test-laptop, heavy tests, broad validation, targeted rerun, test failure batching, avoid rerun all.
