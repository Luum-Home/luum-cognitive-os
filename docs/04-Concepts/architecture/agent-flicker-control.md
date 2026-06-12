# Agent Flicker Control

Agent Flicker Control is the Cognitive OS capability that groups existing agentic primitives for keeping AI-agent behavior stable, evidence-grounded, and bounded. It is not a single model-level algorithm. It is a runtime and documentation layer over primitives that already control false completion, contradictory claims, retry thrashing, no-progress loops, runtime drift, and concurrent-agent overwrite risk.

## Definition

In this repo, **agent flicker** means oscillation or instability in agent behavior, including:

- claiming a task is complete and later revealing unverified remaining work;
- toggling between incompatible states such as open and closed without evidence;
- retrying the same failing action until rate limits, cost, or context budgets are exhausted;
- repeatedly editing the same file or rerunning the same command without progress;
- accepting high-stakes claims from self-report instead of independent evidence;
- letting skill, hook, or runtime drift change behavior silently;
- allowing parallel sessions to overwrite or duplicate each other's work.

The control boundary is deliberately evidence-bounded: Agent Flicker Control reports whether the OS has the relevant primitives, docs, tests, hook registrations, and local runtime signals. It does **not** claim that the model can never change its mind or that every harness enforces every hook identically.

## Runtime report

Use the runtime report when making product, architecture, or release claims about agent stability:

```bash
scripts/cos-agent-flicker-report --json
scripts/cos-agent-flicker-report --strict
```

The report schema is `agent-flicker-control-report/v1`. It has two sections:

1. `controls[]` — static readiness for each control surface: artifacts, docs, tests, hook names, and projected registration surfaces.
2. `runtime_signals[]` — local evidence that needs attention, such as active goals, rate-limit queue pressure, dropped retries, claim-enforcer blocks, skill drift events, or failing quality metrics.

A `warn` result can be healthy in a dirty maintainer workspace: it means the static control mesh exists but local runtime evidence contains attention signals. Do not delete metrics to force a green result; replace stale failing evidence with fresh passing evidence or explain why the signal is advisory.

## Control map

| Control | Primary artifacts | Failure modes controlled | Enforcement level |
|---|---|---|---|
| Bounded reflection loop | `lib/agent_reflection.py` | single-pass answer drift, unbounded self-critique loops | Composable primitive with `min_reflect` and `max_reflect`; not globally auto-wired. |
| Deterministic goal loop | `lib/goal_state.py`, `lib/goal_evaluator.py`, `lib/goal_evidence.py`, `lib/goal_budget.py`, `hooks/goal-stop-gate.sh`, `scripts/cos-goal` | false completion, proxy evidence, no-progress loops, budget runaway | Stop hook blocks active incomplete goals; terminal budget/escalation states allow stop honestly. |
| Task closure ledger | `scripts/cos_task_closure_gate.py`, `scripts/cos-task-closure-gate` | closed/open divergence, claimability oscillation, hidden remaining work | Ledger invariants plus optional `closureGate` execution. |
| High-stakes claim verification | `scripts/claim_enforcer.py`, `hooks/claim-validator.sh`, `hooks/orchestrator-claim-gate.sh`, `hooks/agent-output-verifier.sh` | contradictory completion claims, hallucinated file claims, test-pass self-report | Verification commands are rerun or claims are downgraded/blocked. |
| Retry, backoff, and circuit breaker | `lib/rate_limiter.py`, `lib/circuit_breaker.py`, `hooks/rate-limiter.sh`, `hooks/rate-limit-precheck.sh`, `hooks/rate-limit-drain.sh` | retry thrashing, rate-limit bursts, provider failure loops | Persistent queue, retry caps, exponential backoff, cooldowns, and half-open probes. |
| No-progress escalation | `lib/escalation_detector.py` | same-command loops, same-file edit loops, repeated errors, timeout-risk drift | Emits structured `ESCALATION:` guidance with evidence and next action. |
| Coordination locks | `lib/session_coordination.py`, `lib/task_claim_ledger.py`, `hooks/concurrent-write-guard.sh`, `hooks/cross-session-coordination-guard.sh` | parallel overwrite, duplicate task claims, branch/worktree conflict | Claim ledgers, file locks, and cross-session coordination checks. |
| Checkpoint and repair isolation | `lib/checkpoint_manager.py`, `lib/auto_repair.py`, `hooks/auto-checkpoint.sh`, `hooks/auto-repair-dispatcher.sh` | repair pollution, unsafe rollback, lost work after crash | Copy-only checkpoints, reviewed stash restore, worktree-isolated repair, repair circuit breaker. |
| Skill drift detection | `lib/skill_drift_detector.py`, `hooks/skill-drift-detector.sh` | runtime skill drift, silent mutation, invalid federated evidence | SessionStart detector with warn/block policy. |
| Context and quality close gates | `hooks/context-budget-meter.sh`, `hooks/session-quality-close-gate.sh`, `lib/context_budget_monitor.py` | context overload, closure after failing evidence, validation drift | Prompt budget meter and Stop gate for explicit failing quality evidence. |

## Harness boundary

Agent Flicker Control must stay honest about harness differences:

- Claude Code has the broadest native hook coverage in `.claude/settings.json`.
- Codex projection has a narrower native hook subset in `.codex/hooks.json` and uses explicit governed wrappers for gaps.
- `cos-runner` / `cognitive-os.yaml` declare the broader portable primitive mesh.

The runtime report lists `registered_surfaces` for each hook-backed control so claims can distinguish available code from active projection.

## Verification

Focused verification for this capability:

```bash
uv run python -m pytest \
  tests/unit/test_agent_flicker_report.py \
  tests/unit/test_agent_reflection.py \
  tests/unit/test_goal_state.py \
  tests/unit/test_goal_evidence.py \
  tests/unit/test_goal_evaluator.py \
  tests/unit/test_goal_budget.py \
  tests/unit/test_rate_limiter.py \
  tests/unit/test_rate_limiter_behavior.py \
  tests/unit/test_circuit_breaker.py \
  tests/unit/test_escalation_detector.py \
  tests/unit/test_cos_task_closure_gate.py \
  tests/unit/test_skill_drift_detector.py \
  tests/unit/test_public_claim_gate.py \
  tests/unit/test_session_coordination.py -q
```

Use `scripts/cos-agent-flicker-report --json` as the live status receipt. Use `--strict` only in contexts where local runtime warnings should fail the lane.

## Related decisions and concepts

- [ADR-105 — Claim Verification Contract](../../02-Decisions/adrs/ADR-105-claim-verification-contract.md)
- [ADR-108 — Concurrent Agent Safety Layer](../../02-Decisions/adrs/ADR-108-concurrent-agent-safety-layer.md)
- [ADR-116 — Multi-Session Coordination Primitives](../../02-Decisions/adrs/ADR-116-multi-session-coordination-primitives.md)
- [ADR-143 — Closure Discipline Gate](../../02-Decisions/adrs/ADR-143-closure-discipline-gate.md)
- [ADR-228 — Retry Contract and Cost Session Budget](../../02-Decisions/adrs/ADR-228-retry-contract-and-cost-budget.md)
- [ADR-244 — Trust Report Claim Validator Must Enforce](../../02-Decisions/adrs/ADR-244-trust-report-claim-validator-must-enforce.md)
- [ADR-285 — Skill Registry Runtime Drift Detection](../../02-Decisions/adrs/ADR-285-skill-registry-runtime-drift-detection.md)
- [ADR-295 — Agent Reflection Loop Primitive](../../02-Decisions/adrs/ADR-295-agent-reflection-loop-primitive.md)
- [ADR-318 — Copy-Only Checkpoints and Stash Quarantine](../../02-Decisions/adrs/ADR-318-copy-only-checkpoints-and-stash-quarantine.md)
- [ADR-335 — Generic Task Closure Ledger Gate](../../02-Decisions/adrs/ADR-335-generic-task-closure-ledger-gate.md)
- [Goal Loop Architecture](goal-loop.md)
- [Rate Limiter Flow Control](rate-limiter-flow-control.md)
- [Task Closure Ledger Gate](task-closure-ledger-gate.md)
