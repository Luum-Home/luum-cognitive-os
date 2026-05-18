<!-- SCOPE: os-only -->
# Goal Loop — Operator Rule

## Purpose

The COS native goal loop lets an operator set a completion contract before a
work session starts. The agent cannot stop until the goal's acceptance checks
are satisfied with **structured evidence** — not a text claim that the work is
done.

Goals are **evidence contracts**, not motivational prompts. Writing "fix the
routing benchmark" as an objective without specifying verifiable acceptance
checks produces an unenforceable goal.

---

## Contextual Trigger

Load this rule when the operator or an agent:

- Creates, modifies, or queries a goal (`cos-goal create/status/pause/resume/clear`).
- Asks the agent to complete a goal-tracked task.
- Troubleshoots why a Stop was blocked by `hooks/goal-stop-gate.sh`.
- Requests a goal-aware session plan.

---

## Quick Reference

| Command | Effect |
|---|---|
| `scripts/cos-goal create --objective <text> --check <check>` | Start a new goal with one or more verifiable acceptance checks. |
| `scripts/cos-goal evaluate --evidence-file <path>` | Store an explicit evidence packet for the active goal and show a deterministic preview verdict. |
| `scripts/cos-goal status` | Show goal status, last evaluator verdict, and remaining checks (human-readable). |
| `scripts/cos-goal status --json` | Same output in machine-readable JSON. |
| `scripts/cos-goal pause` | Suspend enforcement; Stop is allowed while paused. |
| `scripts/cos-goal resume` | Re-activate enforcement. |
| `scripts/cos-goal clear` | Abandon the goal; archives it in a `cleared` state. |
| `scripts/cos-goal doctor` | Report harness support level for Stop enforcement. |

---

## Writing an Evidence Contract

A goal must have at least one acceptance check that maps to a deterministic
rule the evaluator can verify:

| Rule type | Example check |
|---|---|
| `file_exists` | `docs/04-Concepts/architecture/goal-loop.md exists` |
| `test_command_passes` | `.venv/bin/python -m pytest tests/behavior/test_goal_cli.py -q` |
| `command_exit_zero` | `bash -n hooks/goal-stop-gate.sh` |
| `regex_match` | `rg -q 'evidence contract' rules/goal-loop.md` |

Vague checks such as "the code looks good" or "I believe the tests pass"
are rejected by the evaluator as proxy evidence.

---

## Example: Repo Cleanup Goal

```bash
scripts/cos-goal create \
  --objective "Remove deprecated hook fragments from hooks/ and update RULES-COMPACT.md reference count" \
  --check "find hooks/ -name '*.deprecated' | wc -l outputs 0" \
  --check "rg -c 'DEPRECATED' hooks/ || true outputs 0 matches" \
  --max-turns 10 \
  --max-minutes 30
```

---

## Example: Routing Benchmark Goal

```bash
scripts/cos-goal create \
  --objective "Routing benchmark passes all intent coverage checks with score >= 0.90" \
  --check ".venv/bin/python scripts/routing_benchmark.py --assert-min 0.90 exits 0" \
  --check "rg -q 'PASS' .cognitive-os/reports/routing-latest.txt" \
  --max-turns 20
```

---

## Budget Dimensions

| Dimension | Flag | Behaviour when exhausted |
|---|---|---|
| Turns | `--max-turns N` | Goal transitions to `budget_limited`; Stop is allowed. |
| Minutes | `--max-minutes N` | Same; wall-clock checked at each Stop event. |
| Tokens | `--max-tokens N` | Accumulated from `llm-dispatch.jsonl` since goal creation. |
| Cost (USD) | `--max-cost-usd N` | Accumulated from the same dispatch log. |

Budget exhaustion is **not** completion. The goal archives with status
`budget_limited`, not `complete`.

---

## Enforcement Model

`hooks/goal-stop-gate.sh` runs on every Stop event when registered in
**standard** or **paranoid** hook profiles. Minimal installs expose status
and doctor commands only.

Run `scripts/cos-goal doctor` to confirm which mode is active:

```
Harness support: native-stop-hook
  Hook registered: yes
  Enforcement:    active
```

If enforcement shows `status-only`, the hook is not registered. Add it to
`hooks.Stop` in `.claude/settings.json`. Codex projection is generated from the same registry when the hook is supported by the harness.

---

## Warning — Structured Evidence Required

Goals are **evidence contracts**, not motivational prompts. The agent must
provide **structured evidence** (explicit `GOAL_EVIDENCE` packet) that maps
each acceptance check to a verifiable outcome. A text assertion that the goal
is complete is not accepted as evidence and will not satisfy any check.

Proxy evidence — evidence that is plausible but does not directly satisfy a
check — is also rejected.

---

## References

- Implementation: `lib/goal_state.py`, `lib/goal_evaluator.py`, `lib/goal_evidence.py`, `lib/goal_budget.py`
- CLI: `scripts/cos_goal.py` / `scripts/cos-goal`
- Hook: `hooks/goal-stop-gate.sh`
- Architecture: `docs/04-Concepts/architecture/goal-loop.md`
- Research origin: `docs/06-Daily/reports/goal-features-internals-2026-05-16.md`
