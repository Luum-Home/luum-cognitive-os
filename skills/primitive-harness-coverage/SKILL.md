<!-- SCOPE: os-only -->
---
name: primitive-harness-coverage
description: "Use when you need this Cognitive OS skill: Measure effective agentic primitive implementation by surface so agents do not confuse `SCOPE: both` with equal Claude/Codex/CLI/UI behavior.; do not use when a narrower skill directly matches the task."
triggers: ["harness coverage", "surface coverage", "primitive harness", "primitive surface", "Claude vs Codex primitives", "CLI primitive coverage", "UI primitive coverage", "scope both parity"]
audience: both
version: 1.0.0
summary_line: "Generate the primitive surface coverage report and inspect IDE/CLI/UI/report implementation gaps."
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

# Primitive Surface Coverage

Use this skill when a user asks whether a primitive works the same across Claude Code, Codex, CLI commands, Shell-CI, dashboard/UI, reports, or other IDE/harness projections.

## Principle

`SCOPE: both` declares portability intent. Surface coverage proves effective implementation by IDE, CLI, shell-CI, UI, service, or report surface.

Do not infer Claude/Codex/CLI/UI parity from `SCOPE: both` alone, and do not treat every implementation as a wired hook.

## Procedure

1. Regenerate the report from the repository root:

   ```bash
   python3 scripts/primitive_harness_coverage.py --project-dir .
   bash scripts/cos primitive harness-coverage --print-json >/tmp/primitive-surface-coverage.json
   ```

2. Read the summary from:

   ```text
   docs/06-Daily/reports/primitive-harness-coverage-latest.json
   docs/06-Daily/reports/primitive-harness-coverage-latest.md
   ```

3. For a specific primitive, inspect:

   - `scope`
   - `family`
   - `surfaces.<surface_id>.surface_kind`
   - `surfaces.<surface_id>.installed`
   - `surfaces.<surface_id>.projected`
   - `surfaces.<surface_id>.wired`
   - `surfaces.<surface_id>.events`
   - `surfaces.<surface_id>.commands`
   - `surfaces.<surface_id>.observable`
   - `surfaces.<surface_id>.operable`
   - `surfaces.<surface_id>.json_contract`
   - `surfaces.<surface_id>.exit_code_contract`
   - `surfaces.<surface_id>.behavior_proven`
   - `gap`
   - `gap_policy`
   - `gap_status`
   - `gap_severity`

4. Explain results with this wording:

   ```text
   Scope declares intended audience. Surface coverage shows which IDE, CLI, UI, CI, service, or report surface actually projects, observes, operates, or executes the primitive today.
   ```

## Verification

Run:

```bash
python3 -m pytest tests/unit/test_primitive_harness_coverage.py tests/contracts/test_primitive_harness_coverage_contract.py tests/contracts/test_cos_cli_surface_contract.py -q
```

## Contextual Trigger

Use for: harness coverage, surface coverage, Claude vs Codex parity, CLI/UI primitive support, primitive IDE support, `SCOPE: both` confusion, implementation coverage by surface.
