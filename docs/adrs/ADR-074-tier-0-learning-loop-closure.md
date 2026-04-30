# ADR-074: Tier-0 Learning-Loop Closure

**Status:** Accepted  
**Date:** 2026-04-30  
**Author:** Matias Nahuel Améndola  

---

## Status

Accepted.

## Context

A 4-agent audit on 2026-04-30 (Engram topics: `cos-learning-loop-wiring-audit`,
`hermes-learning-loop-source-map`, `cos/sessionstart-core-rules-patch`,
`cos/stage2-selective-expansion-plan`) inspected 7 components of COS's
Hermes-inspired learning loop and produced the following wiring verdict:

| Component | Verdict |
|---|---|
| `lib/memory_scanner.py` | LIVE |
| `lib/memory_retriever.py` | PARTIAL |
| `lib/feedback_detector.py` | PARTIAL |
| `hooks/error-learning.sh` | LIVE |
| `hooks/error-pattern-detector.sh` | LIVE |
| `hooks/session-learning.sh` | LIVE |
| `hooks/skill-feedback-tracker.sh` | DETACHED (never fired, 0-byte output) |

Three Tier-0 gaps were identified:

1. **Detached hook**: `hooks/skill-feedback-tracker.sh` was fully implemented
   (59 LOC, PostToolUse[Agent] pattern) but not registered in any profile,
   so `skill-feedback.jsonl` was always 0 bytes and skill-degradation warnings
   were never emitted.

2. **Open feedback loop**: `lib/feedback_detector.py` classified every user
   prompt (EXPLICIT_POSITIVE/NEGATIVE/CORRECTION/ESCALATION) and wrote a
   `category` field to `.cognitive-os/metrics/prompt-captures.jsonl` via
   `hooks/user-prompt-capture.sh`, but nothing downstream read those signals.
   The loop was half-open: detected but never consumed.

3. **CORE_RULES scope clarification**: A prior investigation flagged a patch
   to `hooks/self-install.sh` that would reduce `CORE_RULES` to
   `("RULES-COMPACT.md")` alone, minimising context overhead for client
   projects. However, this repo runs with `IS_SELF_HOSTING=true`, which
   unconditionally syncs the full rules directory — the patch would have no
   effect here. The change is not applied to self-hosting repos.

---

## Decision

### Action 1 — Register `skill-feedback-tracker.sh` (Item 1)

Added `skill-feedback-tracker.sh` to the `standard` efficiency profile's
`PostToolUse[Agent]` hook list in
`scripts/apply-efficiency-profile.sh` (line ~237).

After running `bash scripts/apply-efficiency-profile.sh standard`,
`.claude/settings.json` now includes the hook in the PostToolUse[Agent] block.
Going forward every Agent tool completion will append a JSON record to
`.cognitive-os/metrics/skill-feedback.jsonl` and warn (stderr) when a skill
accumulates 3+ failures within 24 h.

### Action 2 — Close the feedback loop via `lib/feedback_consumer.py` (Item 2)

Created `lib/feedback_consumer.py`, which exposes:
- `read_recent_feedback(limit: int = 50) -> list[dict]` — reads last N entries
  from `prompt-captures.jsonl`
- `group_by_classification(entries) -> dict[str, list[dict]]` — groups by the
  `category` field written by `prompt_classifier`
- `surface_actionable(grouped) -> list[dict]` — filters to
  `{feedback, correction, escalation}` categories above a 0.5 confidence
  threshold, adds `signal_category`, `is_actionable`, and `recency_rank` fields

Updated `skills/analyze-improvements/SKILL.md` Step 0 to call
`summarise_for_skill_improvement()` before the deeper analysis, surfacing
actionable signals as an additional data source for skill repair proposals.

Updated `skills/self-improve/SKILL.md` Integration Points table to reference
`lib/feedback_consumer.py` and its role in the consumption flow.

22 unit tests added at `tests/unit/test_feedback_consumer.py` covering all three
public functions plus the high-level summary helper; all pass.

### Action 3 — Document CORE_RULES scope (Item 3)

The `CORE_RULES=("RULES-COMPACT.md")` patch was confirmed to have no effect in
this repository because `IS_SELF_HOSTING=true` bypasses the CORE_RULES list and
syncs the full `rules/` directory. The patch is intentionally not applied here.
Client projects (where `IS_SELF_HOSTING` is unset or false) would benefit from
it; that deployment path is tracked as a Tier-1 follow-up.

---

## Consequences

### Positive

- `skill-feedback.jsonl` will now populate on every Agent call; skill-degradation
  warnings will surface in real time (previously silent).
- `/analyze-improvements` and `/self-improve` now consume user feedback signals
  (correction, escalation, negative feedback) when generating proposals, closing
  the detect → capture → consume loop that was previously open.
- The CORE_RULES scope confusion is documented and will not be re-attempted
  for self-hosting repos.

### Negative / Trade-offs

- The `feedback_consumer` surfaces `category: feedback` entries from
  `prompt_classifier`, not the more granular `FeedbackType` enum values from
  `feedback_detector`. Raw prompt text is not persisted, so re-classification at
  consume time is not possible. Finer granularity requires extending
  `hooks/user-prompt-capture.sh` to write `feedback_type` as well (Tier-1 follow-up).

### Follow-ups (Tier 1, not in scope here)

- **Tier 1 #4 — Stage 2 selective expansion**: add mid-session memory injection
  (Hermes-style mid-task scan as a PreToolUse[Agent] hook wrapping
  `lib/memory_scanner.scan()`).
- **Tier 1 #5 — Mid-task memory tool**: wire `lib/memory_retriever.py` as an
  explicit tool invokable by agents during task execution, rather than only as a
  fallback in the MCP server.
- Extend `user-prompt-capture.sh` to persist `feedback_type` (from
  `feedback_detector`) alongside `category` (from `prompt_classifier`) so that
  `feedback_consumer` can surface `EXPLICIT_NEGATIVE`, `CORRECTION`, and
  `ESCALATION` as first-class fields.

---

## Alternatives rejected

- **Full Hermes verbatim port**: Porting the complete Hermes learning-loop
  (skill review prompts, RLHF-style rating, memory replay) would require replacing
  existing hooks wholesale. Rejected as out of scope; the incremental wiring
  approach achieves 80% of the value at 20% of the risk.

- **Honcho service**: Using Honcho (external session memory service) as a feedback
  store was considered. Rejected: external dependency, network requirement, no
  offline path.

## Verification

```bash
python3 -m pytest tests/unit/test_feedback_consumer.py -q --tb=short
python3 -m pytest tests/behavior/test_engram_reinforce_hook.py -q --tb=short
```
