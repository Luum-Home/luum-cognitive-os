---
name: skill-optimization
version: 1.0.0
description: Use when improving Cognitive OS skills as staged, validation-gated text artifacts without mutating live skills before explicit adoption.
audience: os-dev
platforms:
  - codex
  - claude-code
  - opencode
  - generic-cli
platform_support:
  generic-cli:
    support_level: executable
    evidence:
      - scripts/cos-skill-opt-run
      - scripts/cos-skill-edit-gate
      - scripts/cos-skill-adopt
      - tests/red_team/portability/test_cos_lean_skillopt_primitives.py
routing_patterns:
  - pattern: \b(skill[- ]opt|skill[- ]sleep|optimi[sz]e skill|validation-gated skill update|self-evolving skill)\b
    confidence: 0.9
routing_intents:
  - intent: skill_optimization_request
    description: User asks to optimize, stage, validate, adopt, reject, or sleep-update a Cognitive OS skill.
    confidence: 0.9
triggers:
  - /skill-opt
  - /skill-sleep
  - optimize skill
  - train skill
  - validation-gated skill update
  - self-evolving skill
---
<!-- SCOPE: os-only -->
# Skill Optimization

Use this skill when improving a `SKILL.md` based on traces, evals, or recurring
failures. The live skill is never edited directly by the optimization step.
Proposals are staged, gated, and adopted separately.

## Loop

```text
rollout/evidence → reflect → aggregate → select → stage proposal → validation gate → adopt
```

## Commands

```bash
scripts/cos-skill-opt-run \
  --skill skills/example/SKILL.md \
  --edit-add "Use held-out validation before final claims." \
  --baseline-score 0.60 \
  --candidate-score 0.72 \
  --json

scripts/cos-skill-proposal-stage --skill skills/example/SKILL.md --edit-add "..." --json
scripts/cos-skill-edit-gate --run-id default --baseline-score 0.60 --candidate-score 0.72 --json
scripts/cos-skill-adopt --run-id default --apply --json
scripts/cos-skill-rejected-buffer --run-id default --report --json
scripts/cos-skill-slow-update --skill skills/example/SKILL.md --guidance "..." --json
scripts/cos-skill-sleep --skill skills/example/SKILL.md --json
```

## Safety Contract

- Candidate edits are written under `.cognitive-os/skill-opt/{run-id}/staging/`.
- `cos-skill-edit-gate` accepts only strict score improvements unless a caller sets a delta.
- `cos-skill-adopt --apply` requires an accepted gate unless `--force` is explicit.
- Adoption creates a backup before copying the staged proposal over the live skill.
- Rejected edits are retained as negative feedback in `rejected-edits.jsonl`.
- Longitudinal guidance lives in a protected `COS_SKILL_SLOW_UPDATE` block.

## Contextual Trigger

Use for skill improvement, eval-driven skill edits, nightly/offline skill learning,
held-out validation, rejected edit buffers, staged adoption, and slow skill updates.
