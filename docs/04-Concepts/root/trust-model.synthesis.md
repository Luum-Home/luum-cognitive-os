---
type: concept-synthesis
source: docs/04-Concepts/root/trust-model.md
provenance: "Leaders need to know exactly what the OS does automatically versus what requires approval and how to verify it is working, because a high Trust Score risks being misread as \"everything is perfect.\""
---

## What it is
Defines what Cognitive OS does autonomously, what it asks permission for, and what it never does, via 4 autonomy levels plus the Trust Score (0-100) concept and a deterministic-vs-non-deterministic guarantee split.

## Key mechanics
- **Level 1 (Fully Autonomous, protective guardrails only)**: `rate-limiter.sh` (launch throttling), `error-pipeline.sh`/`error-learning.sh` (error logging), `completion-gate.sh` (acceptance criteria check), `secret-detector.sh` (leaked secrets scan), `content-policy.sh` (prohibited terms/branding), `auto-checkpoint.sh` (git checkpoint every 5 min), `crash-recovery.sh` (orphaned work detection), `resource-check.sh` (cost tracking), `context-watchdog.sh` (context window warnings).
- **Level 2 (Autonomous with Audit Trail, logged to `*.jsonl`)**: `dispatch-gate.sh` (model selection), `blast-radius.sh` (change scope estimate), `scope-proportionality.sh` (disproportionate change warning), `assumption-tracker.sh` (assumption count), `trust-score-validator.sh` (Trust Score calc), `consequence-evaluator.sh` (skill rewrite suggestions).
- **Level 3 (Requires Human Approval, HALT protocol)**: multi-service changes, data migrations, auth/security modifications, API contract changes, mass delete/overwrite, infra config changes, retrying a failed automated fix in production, rewriting a skill definition in production, publishing/pushing to remote.
- **Level 4 (Never Autonomous, hard-refused)**: push to remote, DB migrations, modify `.env`/secrets, change auth code without HALT, force-push/rewrite git history, delete branches, modify payment/billing code without security review, accept terms/licenses, send messages on the user's behalf, create accounts/enter passwords.
- Trust Score bands: 90-100 minimal review, 70-89 spot-check flagged areas, 50-69 thorough human review required, 0-49 automatically blocked in production. Every report must list at least one uncertainty — "100% confident" is treated as a red flag, not a positive signal.
- Audit logs (under `.cognitive-os/metrics/`): `trust-scores.jsonl`, `cost-events.jsonl`, `error-learning.jsonl`, `escalation-events.jsonl`, `assumptions.jsonl`.
- Deterministic layer (hooks — e.g. `secret-detector.sh`, `rate-limiter.sh`, `pre-commit-gate.sh`, `resource-check.sh`, `content-policy.sh`, HALT keyword detection) always produces the same result. Non-deterministic layer (LLM judgment: task decomposition, implementation approach, when work is "done", acceptance-criteria authoring, escalate-vs-retry, Trust Score self-assessment) can vary between runs — modeled on aviation's interlocks + checklists + flight-recorder + two-pilot-rule approach.
- Quick verification: ask "What did you do autonomously this session?" — must answer with specifics (agents launched, blocked count, cost, assumption warnings), not vague reassurance.

## Relations & where used
References `closed-loop-prompts.md` (HALT protocol), `skill-rewrite.md`, git safety rules, and the 5-layer architecture mapping continued in `ux-principles.md`.

## Status / caveats
Last updated 2026-04-09. Explicitly lists what the OS cannot protect against: business logic correctness, novel/zero-day security vulnerabilities, strategic architecture mistakes, vendor lock-in tradeoffs, team health, and requirements quality ("garbage in, garbage out — faster").
