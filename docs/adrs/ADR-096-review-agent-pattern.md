# ADR-096: Review-agent pattern (Hermes-style audit loop)

**Status**: Proposed
**Date**: 2026-04-30
**Author**: Matias Nahuel Améndola (COS sub-agent)
**Engram topic keys**: `cos/learning-loop-final-30pct`, `hermes-learning-loop-source-map`
**Implementation sprint**: NOT this sprint — implementation is a separate future sprint.

---

## Context

The most distinctive Hermes learning primitive is the *review agent*: after a
conversation turn, a second AIAgent fork runs silently in the background with
the full conversation history as context and a review prompt. The reviewer
identifies skill opportunities, memory updates, and other improvements, then
writes them directly to shared stores — without the user seeing any
intermediate output.

COS currently has passive signal collection:
- `feedback_detector.py`: classifies prompts post-hoc by category
- `feedback_consumer.py`: surfaces negative signals as skill-improvement inputs
- `hooks/skill-feedback-tracker.sh`: records per-invocation success/failure

What COS does NOT have is an **active audit agent** that reads a completed
sub-agent's output and asks "was this correct? did it hallucinate? should a
skill be updated?". The passive classifiers cannot answer these questions
because they do not evaluate agent *outputs*, only user *inputs*.

### Hermes `_spawn_background_review` — what it does

Source: `.claude/plugins/hermes-agent/run_agent.py`, lines 2749–2828.

```
1. A fork AIAgent is created with the same model, platform, and provider.
2. The fork shares _memory_store and _memory_enabled with the parent.
3. The review prompt (_MEMORY_REVIEW_PROMPT, _SKILL_REVIEW_PROMPT, or
   _COMBINED_REVIEW_PROMPT) is appended as the next user turn.
4. The fork runs conversation silently (stdout/stderr redirected to /dev/null).
5. After the fork completes, its _session_messages are scanned for successful
   tool results (memory saves, skill creates).
6. A compact summary ("💾 Memory updated · Skill updated") is printed to the
   parent's output.
```

The review runs in a `threading.Thread` (background, non-blocking).
`max_iterations=8` limits runaway review agents.

### What is portable from Hermes (MIT license)

| Hermes artifact | COS equivalent | Portability |
|-----------------|----------------|-------------|
| `_MEMORY_REVIEW_PROMPT` / `_SKILL_REVIEW_PROMPT` (prompt text, ~200 words each) | New `templates/review-agent-prompt.md` | Verbatim copy OK after stripping Hermes tool references |
| `max_iterations=8` cap on reviewer | Same cap in COS Agent call | Pattern portable |
| Shared memory store between parent and reviewer | COS uses Engram (MCP); reviewer would call `mem_save` | Pattern portable, mechanism differs |
| `threading.Thread` for non-blocking review | COS `run_in_background: true` Agent call | Pattern portable, mechanism differs |

What is NOT portable:
- Hermes's `AIAgent` class (Hermes-internal; COS uses the Claude Code Agent)
- `_memory_store` shared-reference pattern (not applicable with MCP tools)
- Hermes's skill store at `~/.hermes/skills/` (COS skills are in-repo)

---

## Decision space (open — not decided)

### When does review fire?

**Option A — After every sub-agent completion** (Hermes default):
Maximum coverage; maximum cost. Every Agent call in COS triggers a review.
With ~10–15 agents per sprint, and each review at Haiku = ~$0.003–$0.008,
total review cost per sprint = ~$0.03–$0.12. Acceptable but not zero.

**Option B — Only on `failure` outputs**:
Review fires when the PostToolUse hook detects failure markers in the agent
output. Lower cost; focuses review where it matters most (failures are where
skill degradation is likely). Risk: misses successful outputs that contain
hallucinations.

**Option C — Sampled N%**:
Review fires for a random N% of agent completions (e.g. N=20%). Stable cost
regardless of sprint size. Less deterministic; may miss bursty failure modes.

**Open question**: COS already has `trust-score-validator.sh` which fires on
every Agent completion and emits a trust score. Could the trust score gate
review? (e.g. fire review only when trust_score < 0.7.)

### What does the reviewer check?

Three candidate scopes:

1. **Trust score validation**: did the agent provide evidence for its claims?
   (overlaps with existing `trust-score-validator.sh` — must not duplicate)
2. **Claim accuracy**: did the agent claim to write a file that doesn't exist?
   Did it claim tests pass when they didn't? (high value; not currently checked)
3. **Skill opportunity detection**: did the agent solve something that should
   become a skill? (feeds ADR-091)
4. **Memory update**: is there something in this output worth persisting to
   Engram? (partially covered by the `engram-reinforce-on-access.sh` hook)

A combined reviewer (checks 2+3+4) maximises signal per LLM call.

### What does the review produce?

| Output type | Destination |
|-------------|-------------|
| Verified/falsified claim | Engram, type=`review-finding`, with `verified: bool` |
| Skill opportunity | `skill-repair-queue.jsonl` (pending ADR-091 skill synthesis) OR a direct `/add-skill` call |
| Memory update | `mem_save` call to Engram |
| Trust score override | `trust-score.jsonl` with reviewer's independent score |

### Cost gate

A review agent is an additional LLM call per task. At Haiku pricing (~$0.003
per 10K tokens, reviewer context ~5K tokens), cost per review ≈ $0.0015.
At 50 agents/day × $0.0015 = $0.075/day — within governance bounds.

At Sonnet pricing: $0.04/10K → $0.02/review → $1.00/day at 50 agents. This
exceeds the $0.50 decomposition threshold from RULES-COMPACT §4. Reviewer
MUST use Haiku unless the task requires deep reasoning.

**Open question**: should the cost of review be charged against the task's
budget or tracked separately? The current cost-governance system tracks per-
task costs; a post-task review blurs the boundary.

---

## Open questions (must be answered before implementation sprint)

1. **Sync or async?** Hermes uses `threading.Thread` (async, non-blocking).
   COS's `run_in_background: true` is the natural equivalent, but background
   agent results arrive as notifications, not as inline output. The reviewer's
   findings (e.g. `mem_save` calls) are fire-and-forget. If the review finds
   a critical claim error, can a notification surface it usefully? Or should
   it be sync (block until done)?

2. **Self-review vs cross-review?** Using the same model to audit its own
   output has known limitations (same biases, same blind spots). Hermes uses
   the same model because it shares the `_memory_store` reference. COS could
   use a different model for the reviewer (e.g. Opus reviews Sonnet output)
   but this doubles the already-elevated cost.

3. **Where do review findings persist?** Engram with `type=review-finding`
   is the natural choice. The schema must be defined before implementation to
   ensure findings are searchable and not confused with other observation
   types. Proposed schema fields: `task_id`, `reviewer_model`, `claim`,
   `verified`, `confidence`, `evidence`.

4. **Deduplication and loop prevention**: if the reviewer calls `mem_save`
   for the same claim twice (across two sessions), does Engram deduplicate?
   The current `mem_save` protocol uses `topic_key` for upsert — but review
   findings don't have stable topic keys (each is tied to a specific task).
   A content-hash deduplication scheme is needed.

5. **Integration with `trust-score-validator.sh`**: the existing hook already
   scores agent outputs. The reviewer must either augment the trust score or
   run entirely separately. Running both risks inconsistent scores visible to
   the user.

---

## Consequences (anticipated)

### Positive

- Closes the self-reinforcing gap explicitly: the OS can detect its own
  errors in agent outputs, not just user corrections.
- Produces Engram evidence that downstream agents (and the user) can query
  ("what did the reviewer find about yesterday's deploy agent?").
- Enables the ADR-095 skill synthesis path: the reviewer is the natural place
  to detect skill opportunities in successful task completions.

### Negative

- **LLM cost**: a review agent doubles the effective cost per task if it runs
  on every agent completion. Must be gated by trust_score or sampling.
- **Latency**: if sync, adds reviewer latency to every task. If async, the
  review may arrive after the user has moved on (stale context).
- **False trust**: a reviewer that consistently says "verified" without
  actually checking provides false assurance and is worse than no reviewer.
  Evaluation criteria for the reviewer itself are needed (meta-evaluation).

### Follow-up

- Evaluate whether the review-agent pattern can be piloted on a single
  high-stakes hook (e.g. only review `sdd-apply` outputs) before generalizing.
- Define Engram schema for `review-finding` observations before implementation.
- Determine cost amortization strategy (budget per sprint? per task? separate
  "learning budget"?).

---

## Alternatives rejected

| Alternative | Reason rejected |
|-------------|-----------------|
| Passive classifier only (current state) | Classifies user inputs, not agent outputs. The closed loop never fully closes — agent errors that users do not correct are invisible. |
| Human-in-the-loop only | Defeats the autonomous learning goal. Requires the user to manually audit every agent output. |
| Static linter / grep-based checker | Cannot evaluate claim accuracy or detect hallucination without LLM reasoning. |
| Extend `trust-score-validator.sh` to do claim verification | The hook already runs on every agent completion and is latency-sensitive. Adding LLM calls to it would violate its <200ms budget. |

---

## Relationship to ADR-090 and ADR-095

- ADR-090 (Accepted): detects and queues *failing skills* from metric data.
  No review agent involved.
- ADR-095 (Proposed): synthesizes *new skills* from success patterns.
  The review agent is the natural detector for ADR-095's "repeated success
  pattern" signal — the reviewer can say "this task pattern recurred; propose
  a skill."
- The three ADRs form a complete learning loop: detect failure (090) →
  detect success patterns (095) → actively audit outputs (096). They should
  be designed together before 095 or 096 enter implementation.
