---
type: concept-synthesis
source: docs/04-Concepts/root/self-building-protocol.md
status: "Accepted"
provenance: "The orchestrator has sophisticated libraries but relies on manual judgment instead of using them, causing tools to go untested and worse decisions."
---

## What it is
Behavioral protocol (ADR-SBP-001) mandating the orchestrator use its own 25+ library modules (skill_router, WorkloadScheduler, EscalationDetector, etc.) as a first-class part of every session, rather than bypassing its own tooling.

## Key mechanics
- 6 phases: (1) Message Reception — `prompt_classifier.classify_prompt` + `skill_router.best_match` (suggest skill if confidence >=0.80, mention if 0.50-0.79); (2) Task Planning — `WorkloadScheduler.plan(tasks)` when launching >3 agents; (3) Pre-Implementation Investigation — `/reverse-engineer` before trial-and-error, `/repo-forensics` for external repos, `repo_analyzer` for codebase structure; (4) During Agent Execution — `EscalationDetector` every run, `CognitiveLoadMonitor` at context >50% (save at 70%, stop at 85%); (5) Post-Completion — Trust Report validation mandatory, `code_reviewer.review_files()` if code written, auto-skill generation check (10+ tools OR 8K+ chars), `CostDashboard` at session end; (6) When Stuck (>15 min / ~20 tool calls) — `EscalationDetector.check_should_escalate()`, try a different approach, save diagnosis to engram under `bugfix/{service}/{issue-slug}`.
- Tool-to-integration-point map: 22 libraries mapped to files and trigger frequency (e.g. `skill_router` every message, `workload_scheduler` >3 agents, `trust_report_parser` every agent completion, `checkpoint_manager` every 5 minutes).
- Self-Usage KPI: `used_tools / relevant_tools * 100`. Target >50% healthy, 30-50% WARNING, <30% ALERT. Data sources: `metrics/self-usage.jsonl`, `skill-routing.jsonl`, `prompt-captures.jsonl`, `workload-schedule.jsonl`, `escalation-events.jsonl`, `trust-scores.jsonl`, `investigation-methods.jsonl`.
- Decision: Option A (behavioral rules only, chosen) vs Option B (hook-enforced, deferred). Re-evaluate Option B after 2-4 weeks if violations are frequent.
- Implementation phases: Week 1-2 behavioral adoption, Week 3-4 metric instrumentation, Week 5+ enforcement if self-usage <30% for 2+ consecutive weeks.

## Relations & where used
Extends `dogfooding.md`, `adaptive-bypass.md`, `agent-quality.md`, `skill-management.md`, `token-economy.md`, `agent-escalation.md`, `trust-score.md`, `workload-scheduling.md`. The CLAUDE.md Integration block mirrors this protocol into `~/.claude/CLAUDE.md` orchestrator rules.

## Status / caveats
ADR-SBP-001: Accepted. Currently Option A only — no enforcement mechanism, relies on the orchestrator following its own rules; self-usage metrics require manual tracking; violations are invisible unless audited.
