# Lean Governance and Skill Optimization

Cognitive OS includes two complementary advisory primitive families:

1. **Lean governance**: review and audit code for avoidable code, dependencies,
   abstractions, and boilerplate.
2. **Skill optimization**: treat `SKILL.md` files as staged, validation-gated
   text artifacts that can improve from evidence without changing model weights.

The design is inspired by public MIT-licensed and research sources, but the COS
implementation is clean-room and generic. Source concepts reviewed:

- DietrichGebert/ponytail — lean-code ladder, mode/adapters/review/audit/debt pattern.
- Microsoft SkillOpt — rollout, reflection, bounded edits, held-out validation gate, rejected-edit buffer, slow/meta update, and staged skill artifacts.
- AI Papers Academy SkillOpt article, Microsoft project page, and arXiv:2605.23904 — public method explanation and result framing.

## Lean governance primitives

| Primitive | Role |
| --- | --- |
| `scripts/cos-lean-review` | Diff-focused overengineering review; not a correctness review. |
| `scripts/cos-lean-audit` | Repo-wide scan for avoidable abstraction/dependency/shrink candidates. |
| `scripts/cos-lean-debt` | Harvest `cos-lean:` simplification markers and enforce upgrade triggers. |
| `skills/lean-code/SKILL.md` | Conversation-facing lean implementation mode. |

The decision ladder is:

```text
not needed → standard library → native platform → installed dependency → one clear line → minimum new code
```

Lean governance must not remove safety, validation, accessibility, data-loss
prevention, or explicit user requirements.

## Skill optimization primitives

| Primitive | Role |
| --- | --- |
| `scripts/cos-skill-opt-run` | End-to-end local run: stage proposal and optionally gate it. |
| `scripts/cos-skill-proposal-stage` | Write a candidate `proposed_SKILL.md`; never mutate live skill. |
| `scripts/cos-skill-edit-gate` | Accept only strict score improvements over baseline. |
| `scripts/cos-skill-adopt` | Adopt an accepted proposal with backup; `--apply` is explicit. |
| `scripts/cos-skill-rejected-buffer` | Persist rejected edits as negative feedback. |
| `scripts/cos-skill-slow-update` | Stage protected longitudinal guidance. |
| `scripts/cos-skill-sleep` | Offline/nightly-style trace mining and staged slow update. |
| `skills/skill-optimization/SKILL.md` | Conversation-facing workflow for skill evolution. |

## State layout

```text
.cognitive-os/lean/
  audit-latest.json
  debt-ledger.json

.cognitive-os/skill-opt/{run-id}/
  staging/
    proposed_SKILL.md
    proposal.diff
    manifest.json
  gate.json
  rejected-edits.jsonl
  sleep-report.json
  backups/
```

## Claim boundaries

- These primitives are advisory/candidate maturity until harnesses enforce the
  policies at runtime.
- `cos-skill-sleep` is deterministic and staged; it does not autonomously mutate
  live skills.
- Scores are supplied by caller/eval harness. The gate is only as meaningful as
  the held-out evaluation behind those scores.
