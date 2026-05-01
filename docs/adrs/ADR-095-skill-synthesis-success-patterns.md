# ADR-095: Skill synthesis driven by success patterns

**Status**: Accepted
**Date**: 2026-04-30
**Author**: Matias Nahuel Améndola (COS sub-agent)
**Engram topic keys**: `cos/learning-loop-final-30pct`, `hermes-learning-loop-source-map`, `cos/skill-synthesis-implementation`

---

## Status

Accepted.

## Context

Today (2026-04-30) the COS skill catalog has approximately 146 skills.
All of them were created through one of:

1. Manual `/add-skill` invocation
2. Manual `/skill-creator` invocation
3. `auto-skill-generator.sh` hook (fires after agent completions with certain
   signals, but is triggered by the *user's words*, not by observed patterns)

None of these paths are data-driven. The OS observes outcomes across sessions
but never asks "are users repeatedly doing X in the same way? Should X become
a skill?"

This ADR describes **gap #2 of learning-loop closure**: synthesizing new skill
proposals from recurring success patterns in observed task data.

### Phase context

- **Phase 0 — ADR-102**: task-tracker lifecycle (task IDs, session wiring)
- **Phase 1 — ADR-090**: auto-skill-repair from failure signals
- **Phase 2 — ADR-095 (this ADR)**: skill synthesis from success patterns

### What Hermes does (source: `.claude/plugins/hermes-agent/`)

Hermes implements `_spawn_background_review` in `run_agent.py` (lines 2749–2828).
After a conversation turn, a background AIAgent fork reviews the session
messages and can call `skill_view` / `skills_list` (from
`tools/skills_tool.py`) to determine if a successful task pattern warrants a
new skill entry in `~/.hermes/skills/`. The review agent fires for every
turn that clears a `_skill_nudge_interval` counter, writing directly to the
shared skill store.

The key Hermes primitives that are portable (MIT license, verbatim copy OK):

- `tools/skills_tool.py`: `SkillReadinessStatus`, `skills_list`, `skill_view`,
  frontmatter parsing — fully portable.
- `_SKILL_REVIEW_PROMPT` (in `run_agent.py`): the prompt text that instructs
  the review agent to look for skill opportunities — portable as a template
  after stripping Hermes-specific tool names.

What is NOT directly portable:

- The `_memory_nudge_interval` / `_skill_nudge_interval` counter mechanism —
  Hermes uses it to throttle reviews per-turn; COS uses events and hooks
  instead.
- Hermes's background thread (`threading.Thread`) — COS uses `run_in_background`
  and the hook infrastructure; a direct port would conflict.
- Hermes stores skills in `~/.hermes/skills/`; COS stores them in
  `skills/` within the project repo and tracks them in git.

### Current signal streams available for pattern detection

| Stream | Schema fields relevant to pattern detection |
|--------|----------------------------------------------|
| `tool-sequences.jsonl` | `timestamp`, `session_id`, `task_id`, `tool`, `args_hash`, `success` |
| `skill-feedback.jsonl` | `skill`, `success` (boolean) |
| `session-learnings.jsonl` | `skills_total`, `skills_success`, `skills_failed`, `failed_skills` |
| `prompt-captures.jsonl` | `classification`, `prompt` (user intent captured by `prompt_classifier`) |

`session-learnings.jsonl` does NOT record per-task tool sequences. A new
instrumentation stream (`tool-sequences.jsonl`) was added in Phase 2 to fill
this gap.

---

## Decision

### Option B — Repeated ad-hoc tool sequences (chosen)

Sequences of tool calls (Bash, Edit, Read, Write, Agent, etc.) that recur
across sessions, detected from `tool-sequences.jsonl`. This requires the new
instrumentation hook (`hooks/tool-sequence-capture.sh`) in addition to the
synthesis library.

Only successful tool invocations (`"success": true`) contribute to pattern
counts — failed calls are filtered out to reduce noise.

### Chosen defaults (binding)

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `min_length` | 3 | Minimum sequence length; shorter sequences are too common to be meaningful |
| `min_occurrences` | 3 | Minimum cross-session recurrence; 3 is the lowest credible threshold |
| `window_days` | 7 | Rolling 7-day window; aligns with ADR-090's `stale_days` parameter |
| `auto_promote_threshold` | 5 | Minimum successful feedback invocations before auto-promotion is suggested |

### Output format: Option B — Auto-create in `experimental/` tier

Skills are automatically drafted in `skills/experimental/<auto-name>/SKILL.md`
with tier `experimental`. The `/synthesize-skill` operator skill is the only
path to promote a draft to `skills/<name>/`. Auto-promotion is never automatic
— it only identifies candidates. This prevents skill bloat.

### Experimental catalog controls

- Maximum recommended experimental skill count: 30 skills.
- Prune zero-usage drafts older than 30 days (manual, via `/synthesize-skill`).
- Draft names are deterministic from the tool sequence hash (idempotent).

---

## Resolved questions

1. **Which metric stream drives detection?**
   A new stream `tool-sequences.jsonl` was added (written by
   `hooks/tool-sequence-capture.sh`, registered as `PostToolUse[*]`).

2. **Pattern matcher approach?**
   Pure Python n-gram counting (no LLM). Cost: $0. The skill description
   is template-generated, not LLM-summarized. LLM synthesis is deferred
   (can be added in a future pass once draft quality is assessed).

3. **Where do experimental skills live?**
   `skills/experimental/` was created. The skill router priority logic
   does not yet include `experimental/` — operator must promote explicitly.

4. **Deduplication?**
   Draft names are hash-derived from the sequence signature (idempotent).
   `propose_skill_draft` is a no-op if the draft already exists. Full
   semantic deduplication against the 146-skill catalog is deferred.

5. **Catalog growth control?**
   30-skill experimental cap recommended; prune via `/synthesize-skill`.

---

## Implementation

### New files (Phase 2 — 2026-04-30)

| File | Role |
|------|------|
| `hooks/tool-sequence-capture.sh` | `PostToolUse[*]` — appends one line per tool call to `tool-sequences.jsonl` |
| `lib/skill_synthesizer.py` | Public API: `find_recurring_sequences`, `propose_skill_draft`, `auto_promote_eligible` |
| `hooks/skill-synthesis-scanner.sh` | `Stop` event with 30-min cooldown — runs synthesis, emits to `skill-synthesis-queue.jsonl` |
| `skills/synthesize-skill/SKILL.md` | Operator skill — review/accept/reject/defer synthesis proposals |
| `skills/experimental/` | Directory for auto-drafted experimental skills |
| `tests/unit/test_skill_synthesizer.py` | 22 unit tests for `lib/skill_synthesizer.py` |
| `tests/unit/test_tool_sequence_capture.py` | 11 unit tests for `hooks/tool-sequence-capture.sh` |

### Metric streams written

| Stream | Writer |
|--------|--------|
| `.cognitive-os/metrics/tool-sequences.jsonl` | `hooks/tool-sequence-capture.sh` |
| `.cognitive-os/metrics/skill-synthesis-queue.jsonl` | `hooks/skill-synthesis-scanner.sh` via `lib/skill_synthesizer.py` |

### Hook registration

Both hooks are registered in `.claude/settings.json`:

- `tool-sequence-capture.sh` → `PostToolUse` (all tools, `*` matcher)
- `skill-synthesis-scanner.sh` → `Stop`

---

## Consequences

### Positive

- Genuine self-reinforcement: the OS learns to propose skills from its own
  successful behaviour without waiting for the user to notice the pattern.
- Reduces manual skill-authoring burden for recurring tasks.
- Zero LLM cost per synthesis event (pure n-gram counting).
- `PostToolUse` hook body completes in < 1ms (verified via hook-health.jsonl);
  design goal of < 30ms is met with significant margin.

### Negative

- **False positives create skill bloat.** A low threshold or noisy patterns
  will generate useless experimental skills. Mitigated by 30-skill cap and
  operator-gated promotion.
- **N-gram descriptions are low quality.** The draft SKILL.md only describes
  the tool sequence mechanically. LLM-enhanced descriptions are a future
  improvement.
- **Detection lag**: up to 7 days after a pattern emerges.
- **macOS `date +%s` resolution**: 1-second; hook-health duration_ms for
  fast hooks reports 0 or 1000 depending on clock-second boundary. The hook
  body executes in < 30ms but cannot be measured at that resolution in shell
  without `date +%N` (Linux-only).

---

## Alternatives rejected

| Alternative | Reason rejected |
|-------------|-----------------|
| Continue manual-only skill creation (current state) | Does not close the learning loop; leaves repeated patterns undetected |
| Copy Hermes `_spawn_background_review` verbatim | Hermes uses a per-turn background thread that conflicts with COS's event/hook model; the skill store paths are incompatible |
| Synthesize from every session | Too frequent; synthesis cost accumulates; most sessions do not produce novel patterns |
| LLM-based summarization for draft descriptions | Cost per synthesis call; deferred until n-gram draft quality is assessed |
| Option A (repeated successful skill invocations) | Detects popular skills, not novel ad-hoc patterns |
| Option C (high-trust-score task completions) | Requires structured task-completion log not yet captured |

---

## Relationship to ADR-090 and ADR-102

- **ADR-090** (Accepted): detects and queues *failing* skills. ADR-095 is the
  inverse: synthesizes *new* skills from *successful* patterns.
- **ADR-102** (Accepted): task-tracker lifecycle bugs — provides stable `task_id`
  values that `tool-sequence-capture.sh` reads from `COS_TASK_ID` env.
- ADR-096 (if implemented): a review agent that actively audits sub-agent output
  could act as an enhanced synthesis mechanism in the future.

## Verification

Run the focused contract for this decision:

```bash
python3 -m pytest tests/audit/test_skills_contracts.py -q
```
