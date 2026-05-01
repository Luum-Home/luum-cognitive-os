# ADR-096: Review-agent pattern (Hermes-style audit loop)

**Status**: Accepted
**Date**: 2026-05-01
**Author**: Matias Nahuel Améndola (COS sub-agent)
**Engram topic keys**: `cos/learning-loop-final-30pct`, `hermes-learning-loop-source-map`, `cos/review-agent-implementation`
**Related ADRs**: ADR-090 (skill failure repair), ADR-095 (skill synthesis), ADR-102 (task-tracker lifecycle), ADR-099 (pre-agent snapshot)

---

## Status

Accepted.

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
| `_MEMORY_REVIEW_PROMPT` / `_SKILL_REVIEW_PROMPT` (prompt text, ~200 words each) | `lib/review_agent.py::build_review_prompt` | Adapted verbatim (Hermes tool references replaced with COS TRUST_REPORT conventions) |
| `max_iterations=8` cap on reviewer | Same cap via dispatch timeout | Pattern portable |
| Shared memory store between parent and reviewer | COS uses Engram (MCP); reviewer calls `mem_save` | Pattern portable, mechanism differs |
| `threading.Thread` for non-blocking review | v1: sync. v2 async follow-up | Pattern portable, mechanism deferred |

What is NOT portable:
- Hermes's `AIAgent` class (Hermes-internal; COS uses the Claude Code Agent)
- `_memory_store` shared-reference pattern (not applicable with MCP tools)
- Hermes's skill store at `~/.hermes/skills/` (COS skills are in-repo)

---

## Decision

### 1. Trigger: post-hoc async (Accepted)

Review fires AFTER the parent agent reports done. The parent task is never
blocked waiting for review. v1 ships sync (review completes before hook exits)
with an explicit latency note. v2 async (background dispatch + sweeper) is a
documented follow-up once we have data on review quality.

**v1 sync note**: The `review-spawner.sh` hook dispatches the reviewer via
`lib/dispatch.py` and blocks until the review response arrives. Measured
latency budget: 2–15s at haiku/sonnet pricing. This is acceptable for the
PostToolUse hook context (no user-visible latency in the critical path).
v2 async is noted in the hook header as a follow-up.

### 2. Sampling: 20% by default (Accepted)

Reviews fire for 20% of sub-agent outputs by default. Configurable via
`cognitive-os.yaml review.sample_rate: 0.2`. Always-review (`1.0`) and
never-review (`0.0`) are supported edge cases.

### 3. Cross-review enforcement: reviewer model must differ from producer (Accepted)

| Producer | Reviewer |
|----------|----------|
| haiku | sonnet (upward) |
| sonnet | opus (upward) |
| opus | sonnet (lateral, not downward) |

Implemented in `lib/review_agent.py::select_reviewer_model` and enforced in
`hooks/review-spawner.sh`. Operator override via `COS_REVIEW_MODEL` env var.

### 4. Default reviewer model: haiku (Accepted, with override)

Default reviewer tier is `haiku` per `cognitive-os.yaml review.default_model`.
The cross-review matrix (Decision 3) overrides this per-call. Operator can
override globally via `cognitive-os.yaml review.default_model` or per-session
via `COS_REVIEW_MODEL` env var.

### 5. Cost cap: 50 reviews/day (Accepted)

Daily budget tracked in `.cognitive-os/runtime/review-budget.json`. When
exhausted, `should_review()` returns False — reviews are skipped, NOT queued
for later dispatch (queuing would create unbounded latency drift). Budget
auto-rolls over at UTC midnight.

### 6. What to check: trust score validation + claim accuracy + AC coverage (Accepted)

The review prompt (from `build_review_prompt`) instructs the reviewer to:
1. Validate trust report honesty (score calibration, evidence quality)
2. Check claim accuracy (files claimed to exist, tests claimed to pass)
3. Check acceptance-criteria coverage
4. Flag hallucination indicators (confident claims without corroborating output)

NOT checked: code style, formatting, spelling.

### 7. Output: Engram + JSONL (Accepted)

Each finding is persisted to:
- `.cognitive-os/metrics/review-findings.jsonl` (offline analysis, schema stable)
- Engram observation type `review-finding` with topic_key
  `review-finding/<producer_id>-<content_hash8>`

Schema: `{score, evidence, gaps, recommendations, producer_id, producer_model,
reviewer_id, reviewer_model, reviewer_confidence, uncertainty, timestamp}`

### 8. No automatic skill modification in this phase (Accepted)

Findings surface to `/analyze-improvements` (Phase 1's downstream consumer).
The review agent emits data; it does NOT act on it. Closing the loop fully
(review → auto-modify) requires a separate implementation sprint with quality
data on review accuracy.

---

## Resolved questions

1. **Sync or async?** v1: sync (block until review done, document latency cost).
   v2 async (background + sweeper) is a follow-up ADR. Rationale: shipping
   something useful now > shipping nothing pending a complex async design.

2. **Self-review vs cross-review?** Cross-review, enforced by the model matrix.
   Same model reviewing its own output has known echo-chamber risks.

3. **Where do review findings persist?** Engram type=`review-finding` +
   `.cognitive-os/metrics/review-findings.jsonl`. Deduplication via content
   hash suffix in topic_key.

4. **Deduplication and loop prevention?** Content hash in topic_key prevents
   Engram upsert collisions. JSONL append is per-call (no dedup in JSONL —
   offline analysis is responsible for dedup there).

5. **Integration with `trust-score-validator.sh`?** The review agent runs as
   a separate PostToolUse hook, after trust-score-validator. The two hooks do
   NOT share state; trust-score-validator is lightweight (<200ms); review-spawner
   is heavier but fires only for sampled outputs.

---

## Implementation

| Artifact | Path | Notes |
|----------|------|-------|
| Library | `lib/review_agent.py` (source: `packages/agent-lifecycle/lib/review_agent.py`) | Public API: `should_review`, `select_reviewer_model`, `build_review_prompt`, `parse_review_response`, `persist_finding`, `daily_budget_state` |
| Hook | `hooks/review-spawner.sh` (source: `packages/agent-lifecycle/hooks/review-spawner.sh`) | PostToolUse on Agent; v1 sync |
| Skill | `skills/review-output/` (source: `packages/agent-lifecycle/skills/review-output/`) | Manual trigger: `/review-output --task-id <id>` or `--recent N` |
| Config | `cognitive-os.yaml review:` block | `sample_rate`, `max_per_day`, `default_model`, `always_review_kinds` |
| Unit tests | `tests/unit/test_review_agent.py` | All public functions; edge cases for should_review, parse_review_response |
| Integration tests | `tests/integration/test_review_agent_flow.py` | End-to-end: synthetic producer → gate → prompt → mock dispatch → persist |

### Hook registration

Register `review-spawner.sh` as a PostToolUse hook via `apply-efficiency-profile.sh`
or directly in `.claude/settings.json` under `hooks.PostToolUse` with matcher `Agent`.

---

## Consequences

### Positive

- Closes the self-reinforcing gap explicitly: the OS can detect its own
  errors in agent outputs, not just user corrections.
- Produces Engram evidence that downstream agents (and the user) can query
  ("what did the reviewer find about yesterday's deploy agent?").
- Enables the ADR-095 skill synthesis path: the reviewer is the natural place
  to detect skill opportunities in successful task completions.
- Cross-review matrix prevents echo chambers (reviewer always differs from producer).

### Negative

- **v1 latency**: sync review adds 2–15s to hook exit time for sampled outputs.
  This is PostToolUse, not in the user's critical render path, but it is
  measurable. v2 async resolves this.
- **False trust risk**: a reviewer that consistently says "verified" provides
  false assurance. The prompt explicitly forbids rubber-stamping (MUST find
  at least 1 gap), but LLM compliance is stochastic. Meta-evaluation of review
  quality is a future follow-up.
- **Cost**: at 20% sample rate and haiku pricing, daily cost ≈ $0.02–$0.05
  for typical sprint load. Within governance bounds.

### Follow-up

- v2 async: background dispatch + `.cognitive-os/runtime/review-pending-*.json`
  markers + sweeper hook. Separate ADR when v1 data shows latency is a problem.
- Meta-evaluation: instrument whether review findings are acted on and whether
  they correlate with later user corrections.
- `always_review_kinds: ["sdd-verify"]` for high-stakes task types — config
  hook already reads this field; enforcement is a 1-line extension.

---

## Alternatives rejected

| Alternative | Reason rejected |
|-------------|-----------------|
| Passive classifier only (current state) | Classifies user inputs, not agent outputs. The closed loop never fully closes — agent errors that users do not correct are invisible. |
| Human-in-the-loop only | Defeats the autonomous learning goal. Requires the user to manually audit every agent output. |
| Static linter / grep-based checker | Cannot evaluate claim accuracy or detect hallucination without LLM reasoning. |
| Extend `trust-score-validator.sh` to do claim verification | The hook already runs on every agent completion and is latency-sensitive. Adding LLM calls to it would violate its <200ms budget. |
| Same model for self-review | Echo chamber: same biases, same blind spots. Cross-review matrix prevents this. |

---

## Relationship to other ADRs

- ADR-090 (Accepted): detects and queues *failing skills* from metric data.
  No review agent involved.
- ADR-095 (Proposed): synthesizes *new skills* from success patterns.
  The review agent is the natural detector for ADR-095's "repeated success
  pattern" signal — the reviewer can say "this task pattern recurred; propose
  a skill."
- ADR-102 (Accepted): task-tracker lifecycle. Review findings reference
  producer_id which aligns with the task-tracker task IDs.
- ADR-099 (Accepted): pre-agent snapshot fix. Untracked files now survive
  agent launches, so review findings written during the hook are safe.
- Together ADR-090 + ADR-095 + ADR-096 form a complete learning loop:
  detect failure (090) → detect success patterns (095) → actively audit
  outputs (096).

## Verification

Run the focused contract for this decision:

```bash
python3 -m pytest tests/behavior/test_code_review_skill.py -q
```
