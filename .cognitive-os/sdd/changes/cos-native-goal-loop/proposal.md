# Proposal: cos-native-goal-loop

## Intent

Build a COS-native `/goal` primitive that turns long-running user objectives into persistent, evidence-evaluated completion contracts. This is not a prompt convention. It is an operating-system capability: stateful objective tracking, continuation, separate completion evaluation, budget/iteration limits, pause/resume, and an auditable evidence trail.

The immediate driver is the repeated failure mode observed in long cleanup/routing/audit sessions: the agent can stop after proxy evidence, while the user's real instruction was to keep iterating until the measurable objective is satisfied or a blocker is surfaced. The research report `docs/06-Daily/reports/goal-features-internals-2026-05-16.md` compares OpenAI Codex goals and Claude Code goals and identifies the architecture COS should adopt.

## Scope

### In Scope

- Define a COS-native goal state model with statuses: `active`, `paused`, `budget_limited`, `complete`, and `escalated`.
- Persist active and historical goal state outside the conversation context.
- Add a Stop-hook-driven continuation loop that blocks final stop while the active goal remains incomplete.
- Add a separate evaluator path so completion is not judged solely by the worker that performed the task; whether MVP must use a model-backed evaluator or may start with deterministic contract evaluation remains an explicit open decision.
- Require explicit structured goal evidence after each iteration: changed files, commands run, passing checks, remaining findings, blockers, and next action. Transcript scraping is not an MVP evidence source.
- Add structured budgets for max turns and max wall-clock minutes. Token/cost budget enforcement remains an explicit open decision until a real metrics reader is wired.
- Support pause/resume/clear behavior.
- Provide a CLI/script surface for creating, inspecting, pausing, resuming, clearing, and evaluating goals.
- Add tests that prove the loop does not complete on proxy evidence alone.
- Document an operator-facing `/goal` contract for long-running work.

### Out of Scope

- Replacing built-in Codex or Claude Code `/goal` features.
- Relying on any proprietary internal goal storage from a host tool.
- Background cron scheduling for goals after the interactive thread is closed.
- Full multi-user shared goal queues.
- Model-specific prompt tuning beyond the default evaluator template.
- Implementing a full autonomous task runner independent of the host harness.

## Approach

Use a hybrid design:

- **Loop driver:** a harness adapter invoked by the Stop hook where the harness supports Stop; unsupported harnesses get honest preflight/status only.
- **Evaluator:** separate evaluation step inspired by Claude Code's fresh-model evaluator to reduce rationalization bias; MVP evaluator strategy is not decided until the self-eval vs separate-eval decision is closed.
- **Budget:** max-turn and wall-clock budgets with explicit `budget_limited` terminal state. Token/cost budgets are not accepted as inert config.
- **Persistence:** COS-owned durable state protected by a workspace/thread lock, with Engram integration as a later persistence backend and local JSON state as the implementation baseline.
- **Prompt-injection defense:** wrap user goal text and evidence as escaped untrusted data and keep evaluator instructions separate from worker-generated evidence.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `hooks/` | New/modified | Stop hook gate for active goals and continuation guidance. |
| `scripts/` | New | CLI scripts for goal create/status/pause/resume/clear/evaluate. |
| `lib/` | New | Goal state, evaluator prompt, evidence parser, budget accounting. |
| `rules/` | New | Operational rule for long-running goal contracts. |
| `skills/` | New or modified | `/goal` skill/user surface, if skill projection is needed. |
| `tests/unit/` | New | Goal state, budget, evidence, evaluator unit tests. |
| `tests/behavior/` | New | End-to-end hook/CLI behavior tests. |
| `.cognitive-os/goals/` | New runtime path | Local goal state storage, ignored or runtime-managed. |

## Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---:|---:|---|
| Stop hook loops indefinitely on vague goals | Medium | High | Require max turns/wall-clock budget and escalation after repeated no-progress evaluations. |
| Evaluator marks complete from transcript-only proxy evidence | Medium | High | Require structured evidence and explicit acceptance criteria; evaluator rejects incomplete evidence. |
| Hook disabled or unsupported in a harness | Medium | Medium | CLI reports unsupported mode; goal remains stateful but cannot auto-continue. |
| Goal state becomes stale after compaction or resume | Medium | High | Re-project the active goal from COS persistence after process boundaries and mid-conversation context truncation; never rely on transcript memory as authority. |
| Concurrent sessions overwrite goal state | Medium | High | Use a workspace/thread lock and reject or queue conflicting writes; surface coordination status instead of silently replacing `current.json`. |
| Prompt injection inside goal text or command output | Medium | High | Escape nested untrusted-data delimiters, treat objective/evidence as untrusted data, and reject instruction-following inside evidence. |
| Rate limiter blocks required continuation | Medium | Medium | Define a bounded priority-lane carve-out for goal continuation guidance, still subject to hard stop budgets. |
| Cost blow-up from evaluator calls | Medium | Medium | Enforce max-turn/max-minute budgets and do not add token/cost fields until dispatch metrics are readable. |

## Rollback Plan

- Disable the Stop hook gate and leave goal state files inert.
- Keep CLI read-only status for any existing goal files.
- Remove new hook registration from settings projection.
- Tests should prove disabling the hook returns normal Stop behavior.

## Dependencies

- Existing hook infrastructure and settings projection.
- Existing resource-governance rules for budget semantics.
- Optional Engram integration for durable observations; not required for MVP.
- The research artifact `docs/06-Daily/reports/goal-features-internals-2026-05-16.md` is the primary design input.

## Success Criteria

- [ ] A user can create a goal with objective, acceptance checks, constraints, and budget.
- [ ] Goal state survives process/session boundaries and mid-conversation context truncation through COS-owned persistence re-projection.
- [ ] Stop hook blocks final stop when acceptance evidence is incomplete and returns concrete next-step guidance.
- [ ] Separate evaluator rejects proxy-only evidence.
- [ ] `pause`, `resume`, and `clear` commands transition state deterministically.
- [ ] Budget exhaustion transitions to `budget_limited`, not `complete`.
- [ ] Tests cover false completion, budget limit, pause/resume, and disabled hook behavior.
- [ ] English-only audit remains at zero findings.

## Effort & Classification

- Classification: **large / operating-system primitive**.
- Estimated SDD work: 1-2 days for spec/design/tasks; 2-4 days for MVP implementation depending on hook registration complexity.
- Requires adversarial verify before archive.


## Open Decisions Before Apply

- **OD-001 — Evaluator strategy**: decide whether MVP requires a model-backed separate evaluator or may start with deterministic contract evaluation plus a model-adapter seam. Do not describe deterministic-only evaluation as a separate evaluator until this is resolved.
- **OD-002 — Token/cost budget**: decide whether to implement real token/cost enforcement by reading dispatch metrics or remove token/cost fields from the MVP and keep such limits as natural-language constraints only.
