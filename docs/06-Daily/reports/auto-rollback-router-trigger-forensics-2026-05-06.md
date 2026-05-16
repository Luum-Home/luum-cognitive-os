# Auto-Rollback Router Trigger Forensics — 2026-05-06

**Scope**: why `/auto-rollback` was suggested during an architecture/strategy
conversation and whether agents could lose work because of it.

## Finding

There are two separate mechanisms named around auto-rollback:

| Mechanism | Path | Trigger | Mutates git? |
|---|---|---|---:|
| Runtime hook | `packages/auto-repair-rollback/hooks/auto-rollback-trigger.sh` | PostToolUse Agent/task/delegate output says verify-apply retries exhausted. | No |
| Skill router hint | `hooks/skill-router-prompt-suggest.sh` -> `lib/skill_router.py` | User prompt text matches router patterns for auto-rollback. | No |

The incident was the second mechanism: a router suggestion. It did not run the
rollback hook and did not execute destructive git.

## Runtime hook safety

The hook exits unless all are true:

1. tool name is `Agent`, `task`, or `delegate`;
2. agent output is present;
3. output matches retry-exhaustion evidence such as:
   - `Verify-apply loop exceeded N retries`;
   - `max retries ... verify`;
   - `retry_count: 3` together with `verdict: FAIL`.

When it fires, it writes `.cognitive-os/metrics/auto-rollback.jsonl` with:

```json
{
  "trigger": "verify-apply-exhaustion",
  "mode": "plan_required",
  "approval_required": true,
  "destructive_commands_executed": false
}
```

It then prints a rollback plan request and explicitly says no `git revert`,
`git restore`, `git reset`, `git clean`, stash mutation, branch deletion, or
worktree mutation was executed.

## Router bug

`lib/skill_router.py` had a hand-coded auto-rollback entry matching:

- explicit `auto-rollback` / `auto rollback` mentions;
- rollback of failed change/apply phrases.

`hooks/skill-router-prompt-suggest.sh` emits a hint whenever the best match has
confidence `>= 0.80`. It does not distinguish direct operator intent from a
meta-discussion such as “the router suggested `/auto-rollback` and that scares
me”.

That is a false positive: mentioning a recovery primitive as risk evidence is
not intent to invoke it.

## Risk assessment

| Risk | Current state |
|---|---|
| Destructive git from router suggestion | Not observed; router only emits additional context. |
| Destructive git from auto-rollback hook | Blocked by ADR-107 and package contract; hook requires human approval. |
| Agent following a bad suggestion | Possible if an agent over-trusts router context. This is the real risk. |
| User work loss from this exact suggestion | Low, because destructive commands remain blocked/approval-gated. |

## Root cause

The router has positive patterns but no sufficient negative-context model for
safety/recovery skills. It can confuse these cases:

```text
intent:       run /auto-rollback for this failed apply
meta-risk:   why did the router suggest /auto-rollback?
quotation:   the agent said `/auto-rollback`
critique:    ignore the /auto-rollback suggestion
```

## Fix applied in this session

The immediate router false positive was fixed by adding negative-context
suppression in `lib/skill_router.py` for auto-rollback mentions that appear in
router critique, scary/risk questions, or ignored-suggestion contexts.

Coverage was added in `tests/unit/test_skill_router.py` proving:

- direct intent still routes: `run auto-rollback for the failed apply`;
- router critique does not route: `Ignoro la sugerencia de /auto-rollback`;
- risk questions do not route: `What triggers /auto-rollback? I am afraid...`.

Validation:

```bash
python3 -m pytest tests/unit/test_skill_router.py -q
python3 -m pytest tests/contracts/test_auto_rollback_safety_contract.py tests/unit/test_skill_router_prompt_suggest_hook.py -q
```

## Remaining fix direction

1. Feed every ignored/wrong router suggestion into ADR-201 telemetry so repeated
   false positives produce a router-confidence proposal.
2. Generalize negative-context handling beyond auto-rollback to other recovery
   or destructive-adjacent skills.
3. Keep ADR-107 unchanged: rollback may prepare evidence, but destructive git
   needs explicit human approval.
