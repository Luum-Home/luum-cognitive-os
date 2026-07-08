---
type: methodology-synthesis
source: docs/05-Methodology/root/prompt-driven-governance.md
provenance: "Proposes converting natural-language-judgment governance hooks from bash/regex to Haiku-evaluated prompt hooks, and analyzes the cost/latency/accuracy tradeoffs."
---

## What it is

ADR-012's proposal (status: Proposed) to convert a subset of Cognitive OS's 80+ bash governance hooks — specifically the ones doing natural-language judgment via regex — into `type: prompt` hooks evaluated by Haiku, while keeping deterministic-check hooks in bash.

## Key mechanics

- **Problem with current bash hooks**: low accuracy (regex can't distinguish "implement auth" (vague) from "follow the approach we discussed" (clear in context)); hard to modify (a non-engineer can't tune a threshold without understanding `grep -qiE`); brittle boilerplate (30-40 lines of identical stdin/jq/session-dir scaffolding repeated per hook).
- **Convert to prompt hooks**: `clarification-gate.sh` (180 lines), `assumption-tracker.sh` (164 lines), `prompt-quality.sh` (161 lines), `scope-creep-detector.sh` (~100 lines) — all involve contextual/semantic judgment.
- **Keep as bash**: `blast-radius.sh`, `completeness-check.sh`, `content-policy.sh`, `secret-detector.sh`, `rate-limiter.sh`, `auto-checkpoint.sh`, `error-learning.sh`, `result-truncator.sh`, `scope-proportionality.sh` — all deterministic/exact-match logic.
- **Cost**: ~$0.00045 per Haiku 3.5 call (800 in / 200 out tokens). Normal session (15 agent launches, 2 hooks each = 30 calls) ≈ $0.014; annual cost of the 4-hook conversion estimated under $11/year.
- **Latency**: bash 50-200ms vs prompt hook 1-2s; two chained prompt hooks add 2-4s. Mitigation recommendation: merge the two PreToolUse prompt hooks (clarification + quality) into one combined-rubric call to halve latency; keep the PostToolUse hook (assumption-tracker) separate since it doesn't block.
- **Template contract**: every prompt hook template must state scoring criteria with weights, define a strict JSON output format, state the decision threshold, include 2-3 calibration examples, and fit within 500 tokens (~$0.0005/call ceiling). Concrete example templates given for Clarification Gate (7 weighted signals, PASS/WARN/BLOCK at 0-29/30-60/61-100) and Assumption Tracker (HIGH vs MEDIUM confidence, explicit "reasoning-from-evidence is not an assumption" rule).
- **4-phase rollout plan**: Phase 1 merged clarification+quality hook with 1-week bash/prompt parallel run and acceptance criteria (latency <2.5s, zero false positives on well-formed prompts, metrics format unchanged); Phase 2 assumption-tracker; Phase 3 scope-creep-detector (flagged as needing possible async execution since Edit/Write fires more often than Agent); Phase 4 evaluate and decide per-hook (keep/revert/hybrid).
- **Metrics continuity requirement**: prompt hooks MUST write to the same JSONL files as their bash predecessors (`clarification-events.jsonl`, `prompt-quality.jsonl`, `assumptions.jsonl`, `scope-creep.jsonl`) so downstream orchestrator/KPI/dashboard consumers are unaffected.

## Relations & where used

- Directly extends the hook inventory in `hooks.md` (same hook names: clarification-gate, blast-radius, assumption-tracker, scope-creep-detector, error-learning, result-truncator, scope-proportionality) and the "14 always-loaded rules" list in `rules-consolidation-plan.md`, which includes `closed-loop-prompts.md` and references clarification-gate/blast-radius by name.
- Named ADR-012, filed at `docs/02-Decisions/adrs/ADR-012-prompt-driven-governance.md`.
- The "Hybrid Architecture" section's PreToolUse/PostToolUse Agent pipelines mirror the PreToolUse/PostToolUse hook tables in `hooks.md` almost exactly (rate-limiter, blast-radius, clarification-gate, error-learning, trust-score-validator, consequence-evaluator).

## Status / caveats

- **Status: Proposed** — this is a design proposal (ADR-012), not a description of implemented/shipped behavior. Readers should not assume `type: prompt` hooks are currently active; `hooks.md`'s live hook inventory still lists `clarification-gate.sh`, `blast-radius.sh`, `assumption-tracker.sh`, and `scope-creep-detector.sh` as plain bash/command hooks with no `type: prompt` variant mentioned, consistent with "Proposed" rather than "Accepted/Implemented."
- Contains an explicit **open question** left unresolved in-source: whether Claude Code's `type: prompt` hooks can write to files directly, or only return text to the hook pipeline (affects whether a hybrid bash-wrapper is needed for metrics writing).
- Acknowledges non-determinism as a real tradeoff (same prompt may score 72 one time, 68 another) and proposes score-band decisions (PASS/WARN/BLOCK) rather than exact-number decisions as the mitigation.
