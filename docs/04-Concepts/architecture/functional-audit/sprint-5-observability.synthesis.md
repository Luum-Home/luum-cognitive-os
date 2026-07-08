---
type: concept-synthesis
source: docs/04-Concepts/architecture/functional-audit/sprint-5-observability.md
provenance: "Capa-3 scorecards answer what EXISTS and is FUNCTIONAL (static); after real usage, the project also needs Capa-4: what is actually USED (runtime)."
---

## What it is

Sprint adding a minimal, file-based (append-only JSONL, no DB/daemon/network) runtime telemetry layer so skill/hook/agent usage can be measured after the static Capa-3 audits.

## Key mechanics

- Recorders in `lib/telemetry.py`: `record_skill_invocation`, `record_hook_fired`, `record_agent_launch`, `record_rate_limit_event` — write to `.cognitive-os/metrics/{skill-usage,hook-usage,agent-launches,rate-limit-events}.jsonl`. Every event has at minimum `event`, ISO-8601 UTC `timestamp`, and an identifying `name`/`type`.
- `hooks/skill-usage-tracker.sh` (PostToolUse Skill) calls `record_skill_invocation()`; it's fire-and-forget via a backgrounded subshell so it can never delay a tool call or inject content into model context.
- Rotation: files auto-rotate at `COS_TELEMETRY_MAX_BYTES` (default 10MB) to `<stem>.<UTC-timestamp>.jsonl`; `iter_records()` merges rotated siblings transparently, and tolerates corrupt lines / read-only metrics dirs without raising.
- Aggregators: `scripts/cos-usage-report.sh` (top-10 skills/hooks, ghost skills, agent cost per model, rate-limit histogram, optional `--efficiency` section, `--json` output) and `scripts/cos-ghost-skills.sh` (the set `exposed(skills) - invoked(skills, window)`, feeds future archive-candidate cleanup).
- Efficiency heuristic (explicitly approximate): `net_tokens = tokens_saved - tokens_spent`, where `compose-prompt` ~1150 tokens saved/invocation (inline canon ~1200 vs template ref ~50), other skills ~200 tokens saved (generic bound), every hook firing ~50 tokens cost.

## Relations & where used

`tests/behavior/test_telemetry.py`, `scorecard-skills.md`, `scorecard-hooks.md`, `rules/token-economy.md`, `ux6-idempotent-update.md`.

## Status / caveats

At time of writing, `hooks/skill-usage-tracker.sh` was written but **not yet registered** in `.claude/settings.json` — registration was UX8's responsibility, so no skill invocations were captured live except via manual `record_skill_invocation()` calls. `record_agent_launch`/`record_rate_limit_event` had no automatic caller wired yet. Efficiency heuristics are coarse placeholders pending real telemetry.
