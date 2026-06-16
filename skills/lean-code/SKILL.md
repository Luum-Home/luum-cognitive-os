---
name: lean-code
version: 1.0.0
description: Use when work should minimize unnecessary code, dependencies, abstractions, or boilerplate while preserving correctness, security, accessibility, and explicit requirements.
audience: both
platforms:
  - codex
  - claude-code
  - opencode
  - generic-cli
platform_support:
  generic-cli:
    support_level: executable
    evidence:
      - scripts/cos-lean-review
      - scripts/cos-lean-audit
      - scripts/cos-lean-debt
      - tests/red_team/portability/test_cos_lean_skillopt_primitives.py
routing_patterns:
  - pattern: \b(lean[- ]code|lean[- ]review|lean[- ]audit|reduce overengineering|no unnecessary dependencies|fewer lines)\b
    confidence: 0.9
routing_intents:
  - intent: lean_code_request
    description: User asks to minimize code, dependencies, abstractions, or overengineering while preserving correctness.
    confidence: 0.9
triggers:
  - /lean-code
  - /lean-review
  - /lean-audit
  - reduce overengineering
  - fewer lines
  - no unnecessary dependencies
---
<!-- SCOPE: both -->
# Lean Code

Use this skill to bias implementation and review toward the smallest correct
solution. It is not a license to remove safety, validation, accessibility,
error handling that prevents data loss, or anything the user explicitly asked to
keep.

## Decision Ladder

Before adding code, stop at the first rung that satisfies the requirement:

1. **Do not build it** if the requirement is speculative or not needed now.
2. **Use the standard library** if it already solves the problem.
3. **Use a native platform feature** if the runtime/browser/framework already provides it.
4. **Use an installed dependency** before adding a new one.
5. **Use one clear line** if it is still readable and correct.
6. **Write the minimum new code** with one runnable check for non-trivial logic.

## Intensity

- `lite`: build what was asked, but name the simpler alternative.
- `full`: default; avoid unrequested abstractions and dependencies.
- `ultra`: deletion before addition; challenge requirements that appear speculative.

## Commands

```bash
scripts/cos-lean-review --json
scripts/cos-lean-audit --json
scripts/cos-lean-debt --json
```

## Debt Marker

If a simplification has a known ceiling, record it with an upgrade trigger:

```text
# cos-lean: simple file scan; upgrade: repo exceeds 10k files or latency >2s
```

`cos-lean-debt` harvests these markers and flags entries without an upgrade trigger.

## Boundaries

- Review overengineering separately from correctness.
- Keep tests and verification proportional to risk.
- Do not add dependencies unless standard-library, native-platform, or already-installed options are insufficient.
- Do not compress away security, data-loss prevention, accessibility, or explicit user requirements.

## Contextual Trigger

Use for lean implementation, diff review for overengineering, dependency restraint,
repo-wide simplification audits, and simplification-debt tracking.
