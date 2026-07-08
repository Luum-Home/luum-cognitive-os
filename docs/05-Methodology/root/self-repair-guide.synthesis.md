---
type: methodology-synthesis
source: docs/05-Methodology/root/self-repair-guide.md
provenance: "Explains, from the operator's terminal-output point of view, what the automatic trust-score/consequence/error-learning feedback loops look like and how to intervene."
---

## What it is

A user-facing guide (not an architecture doc) to Cognitive OS's automatic self-repair behavior: three feedback loops — Consequence Engine, Error Learning, Self-Improvement — that run via hooks with no configuration required, explained through annotated terminal-output examples. Explicitly scoped to affecting **agent behavior only** (model selection, skill enable/disable) — never project source code directly.

## Key mechanics

- **Trust Report**: every agent completion emits `TRUST_REPORT: SCORE=N STATUS=X EVIDENCE=N UNCERTAINTIES=N` on its first output line. STATUS bands: HIGH 90+, MEDIUM 70-89, LOW 50-69, CRITICAL <50. Missing trust report defaults to SCORE=50 ("honest default for unknown").
- **Consequence cycle** (per skill, driven by consecutive trust scores): score ≥85 five times in a row -> `CONSEQUENCE: PROMOTE` (best-version snapshot saved); score <60 escalates across consecutive occurrences -> 1st: `WARN` (skill still launches), 2nd: `DEGRADE` (model downgraded one tier, e.g. sonnet->haiku), 3rd: `DISABLE` (dispatch gate blocks launch, exit code 2, until `/optimize-skill` fixes it). A single WARN doesn't undo a promotion; recovery requires the streak to reset.
- **Error pattern injection**: after 3+ same-type errors on the same service within 24h, the next agent working that service gets an automatic `WARNING: KNOWN ERROR PATTERN` injected into context before it starts — no user action needed.
- **Retry/escalation loop**: `completion-gate.sh` fires PostToolUse, checks acceptance criteria + DoD + build/test/lint failures; failures trigger a "PITER REFINEMENT" retry (max 3 attempts) with explicit re-launch instructions; 3rd failure escalates to human intervention and sends the task to a Dead Letter Queue, recording a circuit-breaker failure.
- **Circuit breaker**: 2+ consecutive failures for a task *type* opens the circuit (`DISPATCH GATE: Circuit breaker OPEN`), blocking that task type for 1 hour cooldown before a half-open single test attempt.
- **Budget-driven downgrade**: resource governor emits `MODEL_DIRECTIVE` downgrades (e.g., sonnet at 82% budget, haiku at 87%) silently — agents still run, just on cheaper models.
- **Dispatch queue**: when `max_parallel_agents` slots (default 5, `resources.compute.max_parallel_agents` in `cognitive-os.yaml`) are full, launches queue and drain automatically as slots free.
- **Session-end KPI flag**: if quality metrics (e.g., `first_pass_success_rate`) drop below threshold, a `SELF-IMPROVE RECOMMENDED` advisory appears at the *start of the next* session (not the one that generated the dip).
- **Monitoring surfaces**: 8 JSONL files under `.cognitive-os/metrics/` (trust-scores, consequence-history, error-learning, cost-events, kpi-history, skill-archive, dispatch-gate) plus `active-tasks.json` and an optional Langfuse UI at `localhost:3100`; `/agent-kpis` gives a formatted dashboard.
- **Intervention table**: re-enable a disabled skill via `/optimize-skill {name}` or `ConsequenceEngine.re_enable_skill()`; override a degraded model at launch with `model: "opus"`; reset the circuit breaker via `CircuitBreaker().reset()`; reset consequence/skill-archive history by deleting the corresponding JSONL files; disable self-repair entirely by removing `completion-gate.sh`/`dispatch-gate.sh`/`consequence-evaluator.sh` from `settings.json`.

## Relations & where used

- The Trust Report format and score bands match `rules/trust-score.md`, listed as a core always-loaded rule in `rules.md`.
- `completion-gate.sh` and the retry/DoD/failure-detection pipeline it describes correspond to `dod-gate.sh`, `auto-verify.sh`, and `auto-refine.sh` in `hooks.md`'s PostToolUse table (all marked "new in v0.4.0").
- The skill DEGRADE/DISABLE/PROMOTE cycle is the runtime behavior underlying `rules.md`'s Skill Adaptation and Auto-Repair rule summaries, and `skills.md`'s Auto-Improvement Flow.

## Status / caveats

- Written entirely as illustrative example output ("You'll see...") rather than a live capture — the specific numbers (score 88, 42, 38, 29; budget 87%/82%) are representative examples, not measured values, unlike `walkthrough.md`'s explicitly-labeled "verbatim from transcript" outputs.
- No internal inconsistency found relative to itself; consistent with the hook inventory in `hooks.md` and the rule set in `rules.md` on named hooks/rules it references.
