<!-- SCOPE: both -->
---
name: primitive-harness-coverage
description: Measure effective agentic primitive implementation by harness/IDE so agents do not confuse `SCOPE: both` with equal Claude/Codex behavior.
triggers: ["harness coverage", "primitive harness", "Claude vs Codex primitives", "IDE primitive coverage", "scope both parity"]
audience: both
version: 1.0.0
summary_line: "Generate the primitive harness coverage report and inspect Claude/Codex/Shell-CI implementation gaps."
platforms: ["claude-code", "codex", "shell"]
user-invocable: true
routing_patterns:
  - pattern: "harness.*coverage"
    confidence: 0.9
  - pattern: "Claude.*Codex.*primitive"
    confidence: 0.9
  - pattern: "scope.*both.*IDE"
    confidence: 0.85
---

# Primitive Harness Coverage

Use this skill when a user asks whether a primitive works the same across Claude Code, Codex, Shell-CI, or other IDE/harness projections.

## Principle

`SCOPE: both` declares portability intent. Harness coverage proves effective implementation by IDE/harness.

Do not infer Claude/Codex parity from `SCOPE: both` alone.

## Procedure

1. Regenerate the report from the repository root:

   ```bash
   python3 scripts/primitive_harness_coverage.py --project-dir .
   ```

2. Read the summary from:

   ```text
   docs/reports/primitive-harness-coverage-latest.json
   docs/reports/primitive-harness-coverage-latest.md
   ```

3. For a specific primitive, inspect:

   - `scope`
   - `family`
   - `harnesses.<name>.installed`
   - `harnesses.<name>.projected`
   - `harnesses.<name>.wired`
   - `harnesses.<name>.events`
   - `harnesses.<name>.behavior_proven`
   - `gap`

4. Explain results with this wording:

   ```text
   Scope declares intended audience. Harness coverage shows which IDE/harness actually projects or executes the primitive today.
   ```

## Verification

Run:

```bash
python3 -m pytest tests/unit/test_primitive_harness_coverage.py tests/contracts/test_primitive_harness_coverage_contract.py -q
```

## Contextual Trigger

Use for: harness coverage, Claude vs Codex parity, primitive IDE support, `SCOPE: both` confusion, implementation coverage by harness.
