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

If it times out, isolate the last surfaced test/file; do not repeat an unbounded full suite.
7. Only after targeted groups and the serial repair lane pass, run `make test-laptop` or the parallel full lane once.

## Failure file flow

```bash
make test-laptop 2>&1 | tee /tmp/test-laptop.log
scripts/cos-test-efficiency-plan --failure-file /tmp/test-laptop.log --commands
```

Use the emitted groups to repair/rerun targeted lanes.

## Contextual Trigger

Keywords: make test-laptop, heavy tests, broad validation, targeted rerun, test failure batching, avoid rerun all.
