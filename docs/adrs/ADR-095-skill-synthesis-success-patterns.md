# ADR-095: Skill synthesis driven by success patterns

**Status**: Proposed
**Date**: 2026-04-30
**Author**: Maintainer (COS sub-agent)
**Engram topic keys**: `cos/learning-loop-final-30pct`, `hermes-learning-loop-source-map`
**Implementation sprint**: NOT this sprint — implementation is a separate future sprint.

---

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
| `session-learnings.jsonl` | `skills_total`, `skills_success`, `skills_failed`, `failed_skills` |
| `skill-feedback.jsonl` | `skill`, `success` (boolean) |
| `skill-invocation-logger.sh` output | skill name + context (exact schema TBD — read before implementing) |
| `prompt-captures.jsonl` | `classification`, `prompt` (user intent captured by `prompt_classifier`) |

The `session-learnings.jsonl` schema has `skills_total` and `skills_success`
but does NOT record which specific skill was invoked per task or what the tool
sequences were. This is the primary schema gap blocking implementation.

---

## Decision space (open — not decided)

### What constitutes a "success pattern"?

Three candidate definitions, each with different detection complexity:

**Option A — Repeated successful skill invocations**
A skill that is invoked ≥ N times across ≥ M distinct sessions with a high
success rate. This is detectable from existing `skill-feedback.jsonl` today.
Problem: it detects popular skills, not recurring *novel* patterns. It would
not propose a skill for something currently done ad-hoc (without a skill).

**Option B — Repeated ad-hoc tool sequences**
Sequences of tool calls (Bash, Edit, Read) that recur across sessions without
a corresponding skill invocation. Requires an audit trail of tool sequences
per session — not currently captured in any metric stream.

**Option C — High-trust-score task completions with low retry count**
Tasks that completed with trust_score ≥ 0.8 and retry_count = 0, where the
same task description (fuzzy-matched) recurred ≥ 3 times. Requires a
structured task-completion log — not currently captured.

**Recommendation (not yet binding)**: Option A is implementable with existing
data. Options B and C require new instrumentation. Begin with A; extend later.

### Detection window

- Rolling 7 days: captures recent patterns, ignores stale data, aligns with
  the `propose_repair_action` stale_days parameter in ADR-090.
- Per-session: too narrow; a pattern across sessions is more signal.
- On-demand triggered by `/scout`: avoids any background cost; puts the user
  in the loop. Most conservative choice.

### Recurrence threshold

- 3 occurrences: too low; coincidental repetition common in active projects.
- 5 occurrences: matches the ADR-090 failure threshold; symmetrically chosen.
- 10 occurrences: high confidence but slow to trigger.

**Open question**: should the threshold vary by skill catalog size? With 146
skills, 5 occurrences of something new is meaningful. With 500 skills,
baseline usage per skill drops and 5 may be noise.

### Output format

**Option A — Draft SKILL.md for human review**
The synthesis process produces a candidate `skills/experimental/{name}/SKILL.md`
with status `experimental`. A human must promote it (move to `skills/{name}/`)
before it becomes active.

**Option B — Auto-create skill in `experimental/` tier**
The skill is created automatically in `skills/experimental/`. The router may
include it at lower priority. A usage threshold (e.g. invoked 3 times without
failure) auto-promotes it.

Concern: Option B can cause skill bloat. The existing 146-skill catalog is
already large enough to cause progressive-disclosure overhead.

---

## Open questions (must be answered before implementation sprint)

1. **Which metric stream drives detection?** `session-learnings.jsonl` has
   `skills_total`/`success` but lacks per-task tool sequences. Is
   `skill-feedback.jsonl` + `prompt-captures.jsonl` sufficient for Option A,
   or do we need a new instrumentation hook?

2. **Pattern matcher approach**: regex (fast, brittle), AST of tool sequences
   (requires structured capture), or LLM-based summarization (accurate but
   costly)? Cost at 5 syntheses/session × Haiku = ~$0.015; acceptable.

3. **Where do experimental skills live?** `skills/experimental/` is the
   natural location but it does not exist yet and requires changes to the
   skill router priority logic (`lib/skill_router.py`). Alternatively,
   experimental skills could live in a per-session directory and be promoted
   to `skills/` only on user confirmation.

4. **Deduplication**: how does the synthesizer know a pattern already has a
   skill? It must compare the candidate against the existing 146 skills'
   descriptions. `lib/skill_router.py`'s `best_match()` can be reused.

5. **Catalog growth control**: the ADR must propose a maximum experimental
   skill count and an auto-pruning policy (e.g. prune experimental skills
   with zero usage after 30 days).

---

## Consequences (anticipated)

### Positive

- Genuine self-reinforcement: the OS learns to propose skills from its own
  successful behaviour without waiting for the user to notice the pattern.
- Reduces manual skill-authoring burden for recurring tasks.

### Negative

- **False positives create skill bloat.** The existing catalog is already
  large. A low threshold or a noisy pattern matcher will generate many
  useless experimental skills.
- **LLM cost**: if synthesis uses an LLM summarizer, each synthesis call
  adds cost. Must be gated by the cost-governance rules in RULES-COMPACT §4.
- **Detection lag**: a rolling-window approach delays synthesis by up to
  7 days after the pattern emerges.

---

## Alternatives rejected

| Alternative | Reason rejected |
|-------------|-----------------|
| Continue manual-only skill creation (current state) | Does not close the learning loop; leaves repeated patterns undetected |
| Copy Hermes `_spawn_background_review` verbatim | Hermes uses a per-turn background thread that conflicts with COS's event/hook model; the skill store paths are incompatible |
| Synthesize from every session | Too frequent; synthesis cost accumulates; most sessions do not produce novel patterns |

---

## Relationship to ADR-090 and ADR-096

- ADR-090 (Accepted): detects and queues *failing* skills. ADR-095 is the
  inverse: synthesizes *new* skills from *successful* patterns.
- ADR-096 (Proposed): a review agent that actively audits sub-agent output.
  ADR-096 could be the *mechanism* that performs pattern detection for
  ADR-095 if it runs post-task. The two ADRs should be designed together
  before either is implemented.
