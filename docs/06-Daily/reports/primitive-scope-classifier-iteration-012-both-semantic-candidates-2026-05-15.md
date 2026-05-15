# Primitive Scope Classifier — Iteration 012: both-semantic-candidate review

Date: 2026-05-15

## Goal

Manually review the full `both-semantic-candidate` bucket from Iteration 011. The bucket had 36 rows: generic rules, reusable review/recon skills, one quality script, and prompt templates.

## Decision policy applied

- `both`: reusable guidance or primitive that applies to COS source work and to adopter/project repositories.
- `project`: primitive affects adopter projects and is not needed for COS construction.
- `os-only`: primitive is written as a COS maintainer/runtime integration or depends on COS internals.

## Summary

| Result | Count | Notes |
|---|---:|---|
| `both` | 33 | Generic rules, repo review/recon skills, test-quality script, prompt templates. |
| `project` | 1 | `skills/install-recommended/SKILL.md` recommends project-local skills from a target stack. |
| `os-only` | 2 | `skills/add-mcp/SKILL.md` and `skills/agent-stress-test/SKILL.md` are COS integration/runtime diagnostics. |

## Reclassified exceptions

| Primitive | From | To | Evidence |
|---|---|---|---|
| `skills/add-mcp/SKILL.md` | `both` | `os-only` | Written as a Cognitive OS MCP integration procedure; updates COS ecosystem docs/config. |
| `skills/agent-stress-test/SKILL.md` | `both` | `os-only` | Uses COS cognitive-load monitor and measures COS agent runtime health. |
| `skills/install-recommended/SKILL.md` | `both` | `project` | Detects a target project stack and recommends project skills; not required for COS construction. |

## Confirmed shared `both`

The following were kept as `both` and given durable `shared-surface` + lifecycle metadata:

- `rules/acceptance-criteria.md`
- `rules/adversarial-review.md`
- `rules/agent-quality.md`
- `rules/agent-sidecars.md`
- `rules/auto-repair.md`
- `rules/broken-window-policy.md`
- `rules/decomposition.md`
- `rules/error-learning.md`
- `rules/fault-tolerance.md`
- `rules/hook-security-profiles.md`
- `rules/impact-analysis.md`
- `rules/model-routing.md`
- `rules/pentesting-readiness.md`
- `rules/pre-commit-gate.md`
- `rules/private-mode.md`
- `rules/python-naming.md`
- `rules/response-compression.md`
- `rules/sandbox-sampling.md`
- `rules/scout-pattern.md`
- `rules/skill-management.md`
- `rules/squad-protocol.md`
- `rules/trailofbits-skills.md`
- `rules/user-prompt-capture.md`
- `scripts/check_test_quality.py`
- `skills/code-review/SKILL.md`
- `skills/pr-review/SKILL.md`
- `skills/repo-forensics/SKILL.md`
- `skills/reverse-engineer/SKILL.md`
- `skills/scout/SKILL.md`
- `skills/sdd-explore/SKILL.md`
- `templates/generator-validator-pair.md`
- `templates/prompt-hooks/clarification-gate-prompt.md`
- `templates/prompt-hooks/prompt-quality-prompt.md`

## Result

The `both-semantic-candidate` bucket is now empty.

```json
{
  "by_suggested_scope": {
    "both": 106,
    "os-only": 536,
    "project": 91,
    "unknown": 455
  },
  "unknown_delta": -36,
  "both_semantic_candidate_bucket": 0
}
```

## Next iteration

Recommended next target: `declared-both-needs-proof-and-metadata` (70 rows). It should be split into:

1. real missing paired portability proof;
2. metadata-only debt where proof already exists but lifecycle/consumer rows are missing;
3. stale `both` markers that should demote after manual review.
