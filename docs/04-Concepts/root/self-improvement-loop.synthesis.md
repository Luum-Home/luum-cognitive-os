---
type: concept-synthesis
source: docs/04-Concepts/root/self-improvement-loop.md
provenance: "AI agents tend to do the minimum required, so tasks pass initial checks but fail deeper verification, and the same error patterns recur across sessions with no institutional memory."
---

## What it is
The closed loop by which Cognitive OS captures its own failures (tests/lint/build), retries with refined instructions, and — if failures persist — feeds accumulated patterns into rule/skill/template updates via `/self-improve`.

## Key mechanics
- Full loop: Execution -> Verification (auto-refine, dod-gate, verification-before-completion) -> Error Capture (`error-learning.sh` -> `error-learning.jsonl`) -> Auto-Refine (up to 3 retries) -> [success = Done, else] Session Learning (`session-learning.sh` -> `session-learnings.jsonl`) -> KPI Snapshot (`kpi-trigger.sh` -> `kpi-history.jsonl`) -> [thresholds OK = continue, breached =] Self-Improve skill -> pattern detection, improvement proposals, auto-apply safe changes or flag risky ones for human review -> updated rules/skills/templates -> next execution.
- `LearningPipeline` (`lib/learning_pipeline.py`) unifies 5 previously-isolated subsystems in one pass per agent completion: `prompt_classifier`, `skill_archive`, `consequence_engine`, `error_classifier`, and trigger surfacing; writes `ErrorCorrelation` records to `metrics/error-skill-correlations.jsonl` linking errors back to the skill that caused them.
- 6 components: Error Capture (`hooks/error-learning.sh` PostToolUse; `hooks/error-pattern-detector.sh` PreToolUse warns on 3+ same failures in 24h), Auto-Refine (`hooks/auto-refine.sh` + `skills/auto-refine/SKILL.md`, PITER loop, up to 3 retries, `metrics/auto-refine/`), Session Learning (`hooks/session-learning.sh` Stop hook -> `metrics/session-learnings.jsonl`), KPI Monitoring (`hooks/kpi-trigger.sh` Stop hook, writes `.self-improve-recommended` flag on breach -> `metrics/kpi-history.jsonl`), Self-Improvement (`skills/self-improve/SKILL.md`), Governance (`rules/self-improvement-protocol.md`).
- Config in `cognitive-os.yaml`: `self_improvement.enabled`, `auto_apply` (false by default), `trigger_threshold.first_pass_success` (0.70), `trigger_threshold.iteration_count` (3), `schedule: session_end`, `max_auto_improvements: 5`.
- Real examples: rebranding pre-count step raised first-pass success 25%->80%; exhaustive endpoint listing raised migration coverage 60%->95%; Go framework compliance check dropped architecture violations 40%->0%.

## Relations & where used
Related: `docs/04-Concepts/architecture/agent-training-harness.md` (canonical training contract, operational-learning scope note), `rules/self-improvement-protocol.md` (governance), `skills/agent-kpis/`, `hooks/architecture-compliance.sh`.

## Status / caveats
Scope note: this is operational learning through harness evidence and governed primitive updates, not model fine-tuning (see agent-training-harness.md for non-goals). Debugging section lists concrete checks for when patterns aren't detected, when a bad change is proposed (`git revert` + `metrics/improvement-blocklist.jsonl`), or when KPI thresholds are miscalibrated.
