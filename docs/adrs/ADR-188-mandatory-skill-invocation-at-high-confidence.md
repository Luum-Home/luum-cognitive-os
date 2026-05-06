---
adr: 188
title: Mandatory Skill Invocation at High Router Confidence
status: proposed
date: 2026-05-06
supersedes: []
superseded_by: null
extends: [ADR-008, ADR-029b]
implementation_files:
  - lib/skill_router.py
  - hooks/skill-router-prompt-suggest.sh
  - hooks/orchestrator-skill-invocation-gate.sh   # to create
  - rules/skill-invocation-mandatory.md           # to create
  - tests/contracts/test_skill_invocation_gate.py # to create
  - .cognitive-os/metrics/skill-bypass.jsonl     # runtime artifact
tier: maintainer
tags: [skill-router, governance, orchestrator-discipline, postmortem-2026-05-06-repo-scout-batch]
---

# ADR-188: Mandatory Skill Invocation at High Router Confidence

## Status

**Proposed.** Filed in response to a structural orchestrator-discipline failure
on 2026-05-06: the skill router suggested `/repo-scout` (confidence 0.95) for a
batch GitHub-URL research task and emitted system-reminders 12 times across
the session. The orchestrator ignored every suggestion, hand-rolled bespoke
shallow prompts for 20 cluster scout agents, and never triggered the deep
evaluation that the canonical `/repo-scout` skill would have produced
automatically via Step 7 (Deep Evaluation) on ADOPT-classified repos. The
operator had to ask "did you actually use the deep research skill?" to surface
the gap. Without that question, the batch would have shipped at shallow depth
disguised as complete research.

## Context

`lib/skill_router.py` produces a confidence score when matching user prompts
to skill `routing_patterns`. The `skill-router-prompt-suggest.sh` hook surfaces
matches with confidence ≥ threshold as `additionalContext` system-reminders
(advisory).

Today this is **suggestion-only**. The orchestrator can ignore the suggestion
without consequence. In practice, ignoring high-confidence matches has two
recurring failure modes:

1. **Bespoke prompt drift**: orchestrator writes ad-hoc prompts that miss
   guarantees the skill encodes (output schema, depth gates, persistence,
   consolidator). The result looks like research but skips the canonical
   contract.

2. **Orchestrator bandwidth burn**: operator ends up babysitting decisions
   (chunking, depth, model, recovery) that the skill had pre-resolved with
   sensible defaults.

The 2026-05-06 repo-scout incident is the documented case. Earlier sessions
recorded the same anti-pattern in
`docs/reports/audit-corpus-revalidation-2026-05-05.md` (operator caught
"did you use the canonical /repo-scout?" with same answer: no).

## Decision

When the skill router emits a match with `confidence >= 0.90` for the current
user prompt, the orchestrator MUST do one of three things, in order of
preference:

1. **Invoke the suggested skill** (preferred path — single primitive).
2. **Invoke a strictly more powerful skill** that subsumes the suggested one
   (e.g. `/research-protocol` instead of `/repo-scout` if a richer contract
   applies). Justify in 1 line.
3. **Bypass with explicit operator-visible justification** — emit a one-line
   `SKILL_BYPASS:` annotation in the assistant response stating which skill
   was bypassed (`name`, confidence) and the concrete reason. Persist the
   bypass to `.cognitive-os/metrics/skill-bypass.jsonl` for retro-audit.

Threshold is 0.90 — high enough that the router is rarely wrong, low enough
that hand-tuned bespoke prompts remain legitimate for genuine novelty.

### Enforcement layers

- **Soft (advisory)**: existing `skill-router-prompt-suggest.sh` already
  surfaces the suggestion. No change.
- **Hard (gate)**: new `hooks/orchestrator-skill-invocation-gate.sh` runs on
  PreToolUse:Agent and PreToolUse:Bash matchers. If the most recent
  user-prompt skill suggestion had `confidence >= 0.90` AND the orchestrator
  is about to launch a sub-agent or run a non-trivial multi-step Bash workflow
  WITHOUT having invoked the suggested skill (or annotated `SKILL_BYPASS:`),
  emit `WARN` to stderr and increment a counter. Three WARNs in one session
  escalate to a single BLOCK with a one-time bypass via
  `COS_ALLOW_SKILL_BYPASS=1` + `COS_SKILL_BYPASS_REASON='<text>'`.

The hard gate is intentionally lenient: it does not block the first or second
ignored suggestion. The goal is to make repeated drift expensive, not to halt
exploratory work.

### Detection of "skill was invoked"

Tracked via either:
- The orchestrator launches a sub-agent whose prompt contains the literal
  `Load skills/<skill-name>/SKILL.md` directive, or
- The orchestrator emits the `SKILL_BYPASS:` annotation, or
- The Skill tool was invoked with `skill: <name>` matching the suggestion.

The hook reads recent session events from `.cognitive-os/sessions/events.jsonl`
(ADR-183) to determine whether the suggested skill was invoked since the last
user prompt.

## Acceptance Criteria

1. `lib/skill_router.py` exposes `last_suggestion(session_id)` returning the
   highest-confidence suggestion since the most recent user prompt, with
   confidence and skill name.
2. `hooks/orchestrator-skill-invocation-gate.sh` registered as PreToolUse on
   both Agent and Bash matchers via `scripts/_lib/settings-driver-claude-code.sh`.
   Latency budget: < 30 ms.
3. `rules/skill-invocation-mandatory.md` documents the 0.90 threshold, the
   three allowed responses, and the SKILL_BYPASS annotation format.
4. `tests/contracts/test_skill_invocation_gate.py` covers:
   - High-confidence suggestion + skill invoked → PASS, no warn.
   - High-confidence suggestion + bypass annotation present → PASS, audited.
   - High-confidence suggestion + bespoke agent launch (no annotation) →
     WARN once, BLOCK after 3.
   - Low-confidence suggestion + bespoke agent launch → PASS (no enforcement).
   - Override env vars (`COS_ALLOW_SKILL_BYPASS=1`+reason) work as documented.
5. `.cognitive-os/metrics/skill-bypass.jsonl` accumulates one entry per
   bypass (annotated or env-overridden) with timestamp, session_id, prompt
   hash, suggested_skill, confidence, reason, actor.
6. NO new pip dependency. Pure shell + python3 stdlib.

## Border Cases

- **Two skills tied at high confidence**: hook treats them as a set; invoking
  any one satisfies the gate. The session.events log records which one.
- **Skill router suggests a skill that doesn't apply** (false positive at
  high confidence): operator should LOWER the routing pattern's confidence
  in `skills/<name>/SKILL.md`, not bypass per-prompt. The bypass path is for
  one-offs, not pattern errors.
- **Multi-step orchestrator workflow** that legitimately needs bespoke
  prompts (e.g. SDD propose phase): orchestrator emits a single
  `SKILL_BYPASS:` early in the response and proceeds; the hook honors it for
  the remainder of the user prompt cycle.
- **Skill is broken or misconfigured**: the bypass + reason serves as the
  bug report; engineering picks it up from `skill-bypass.jsonl`.
- **Sub-agent spawned inside the skill**: not double-counted. The gate fires
  on orchestrator-issued PreToolUse, not on nested skill-internal launches.

## Consequences

### Positive

- The 2026-05-06 repo-scout failure mode becomes structurally detectable and
  auditable. Future operators can answer "did you use the skill?" by reading
  `skill-bypass.jsonl` instead of taking the orchestrator's word.
- Skills become first-class contracts: their output schema, depth gates, and
  persistence guarantees are reliably applied at high confidence rather than
  silently lost in bespoke prompts.
- Operator no longer carries the cognitive load of deciding "is this the
  same as the skill" for high-confidence matches.
- Creates back-pressure on skill quality: if a skill is ignored often at
  high confidence, that's a signal the skill is broken or its routing
  pattern over-fits.

### Negative

- Adds ~10–30 ms latency per Agent/Bash launch.
- Operators / orchestrators must learn the `SKILL_BYPASS:` annotation when
  they genuinely need to deviate. Friction is the point but it costs minutes
  on first encounter.
- Risk of false-positive blocks if the router becomes too liberal with 0.90+
  ratings. Mitigation: tune routing patterns when bypasses cluster.

### Neutral

- Soft layer (suggestion) remains unchanged. The new hook only adds
  enforcement when bypass-without-annotation accumulates.

## Alternatives Rejected

- **Hard block on first ignored suggestion**: too aggressive; operator
  exploratory work would block too easily. Rejected; three-strike pattern
  preserves liberty while making drift expensive.
- **Lower threshold to 0.80**: too many false positives at 0.80 today
  (matches like generic `repo` keyword). Rejected for v1; revisit if 0.90
  proves over-cautious.
- **Mandatory invocation at any confidence**: trivializes the router. The
  router scores meaningfully; treat 0.90+ as "router is confident", lower
  as "router is suggesting".
- **No enforcement, just better suggestions**: today's state. The 2026-05-06
  incident is the proof that suggestions alone are insufficient — the
  orchestrator can and does ignore them at scale.

## Falsifiable Claim

ADR-188 is correct if, in a 60-day audit window after activation:

1. **Bypass rate**: < 10 % of high-confidence suggestions are bypassed
   (annotation or env-override). Higher rate indicates either the threshold
   is wrong or the skills suite is misconfigured.
2. **Repeat-bypass-same-skill rate**: < 3 bypasses for the same skill in a
   week without a corresponding routing-pattern fix. Higher rate indicates
   the skill is broken and the gate is producing noise rather than signal.
3. **Skill invocation frequency**: ≥ 30 % increase in `Skill` tool calls vs
   the 60 days preceding activation, attributable to high-confidence
   suggestions now being honored.
4. **Latency**: 99th percentile gate hook latency < 50 ms.

If (1) or (2) exceed the threshold, the gate is producing friction without
signal — revisit threshold or skill quality. If (3) does NOT increase, the
gate isn't actually changing behavior. If (4) exceeds, optimize the hook.

## Cross-References

- `docs/reports/external-tools-radar-2026-05-06.md` — origin batch where the
  failure was visible.
- `docs/reports/audit-corpus-revalidation-2026-05-05.md` — earlier instance
  of same anti-pattern (operator caught "did you use canonical primitive?").
- `skills/repo-scout/SKILL.md` — the skill that was bypassed; v2.0.1 already
  has Step 7 (Deep Evaluation) that would have produced source-level audits
  automatically.
- `lib/skill_router.py` — confidence scoring source-of-truth.
- `hooks/skill-router-prompt-suggest.sh` — current advisory layer.
- ADR-008 — Multi-Tool Support (skill router design).
- ADR-029b — Reinvention gate Phase B: semantic similarity (related anti-
  duplication enforcement; ADR-188 generalizes the pattern from "don't
  duplicate code" to "don't bypass canonical primitives").
- ADR-183 — Cross-session event log (gate reads recent events to detect
  whether suggested skill was invoked).

## Open Questions

- Whether to also enforce on operator-direct skill invocations (vs only
  agent-launched). Proposed: no for v1 — operators invoking explicitly are
  already informed; the gate is for orchestrator drift specifically.
- Whether to surface the gate's WARN counter in the orchestrator's UI/banner
  so the orchestrator self-corrects before hitting the third strike.
  Proposed: yes, but as a follow-up after v1 lands.
- Threshold calibration: 0.90 is a guess. After 60 days of skill-bypass
  audit data, recalibrate per-skill if needed (some skills may need 0.85,
  others 0.95).
