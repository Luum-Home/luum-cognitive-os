---
name: pyrefly-typecheck
command: /pyrefly-typecheck
description: Use when Python files changed and you need fast advisory static type/API-shape checking with Pyrefly before finishing Cognitive OS work.
version: 0.1.0
audience: os-dev
triggers:
  - pyrefly
  - typecheck
  - python type check
  - static type check
  - changed Python files
routing_patterns:
  - pattern: \bpyrefly\b
    confidence: 0.98
  - pattern: \btype[- ]?check\b
    confidence: 0.82
  - pattern: \bpython\s+(static\s+)?type\s+check\b
    confidence: 0.9
---
<!-- SCOPE: os-only -->
# Pyrefly Typecheck

## Purpose

Run the Cognitive OS Pyrefly pilot lane as a fast, advisory static check for
Python type/API-shape issues. This skill is for SO maintainers while Pyrefly is
in TRIAL; it does not replace pytest, Ruff, or acceptance criteria.

## When to Use

Use this skill when:

- Python files under `lib/`, `scripts/`, or `packages/agent-service/src/` changed.
- Function signatures, dataclasses, TypedDicts, JSON payload parsing, or agent
  service schemas changed.
- A task is about reducing Pyrefly baseline findings or deciding whether to
  promote the gate from advisory to blocking.

Do not use it for docs-only changes or non-Python work.

## Procedure

1. Run the advisory lane:

   ```bash
   make typecheck-pyrefly
   ```

2. Read the machine receipt first:

   ```bash
   cat .cognitive-os/reports/pyrefly/latest.json
   ```

3. Inspect detailed findings only when needed:

   ```bash
   less .cognitive-os/reports/pyrefly/latest.txt
   ```

4. If optional import health is the target, run the strict import probe:

   ```bash
   COS_PYREFLY_STRICT_IMPORTS=1 make typecheck-pyrefly
   ```

5. Keep the lane advisory unless the task explicitly asks for enforcement:

   ```bash
   COS_PYREFLY_ENFORCE=1 bash scripts/cos-pyrefly-pilot
   ```

## Interpretation

- `pyrefly_exit_code` can be non-zero while the lane exits 0 in advisory mode.
- `error_count` is the current baseline signal, not a release blocker yet.
- Prefer fixing clustered real defects over adding broad suppressions.
- Missing-import diagnostics are disabled by default because COS has optional
  dependency lanes; use strict import mode for targeted import audits.

## Acceptance Criteria

For Pyrefly-related changes, report:

1. The command run.
2. `error_count`, `pyrefly_exit_code`, and elapsed seconds from
   `.cognitive-os/reports/pyrefly/latest.json`.
3. Whether the change reduced, preserved, or intentionally ignored the baseline.

## Contextual Trigger

Keywords: pyrefly, typecheck, type check, Python static analysis, API-shape,
TypedDict, missing-import, agentic loop.
