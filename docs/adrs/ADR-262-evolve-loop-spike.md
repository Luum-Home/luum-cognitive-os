---
adr: 262
title: 'Evolve Loop Spike: Task Proposal Queue + LLM-driven Skill Candidates'
status: exploration
implementation_status: not-applicable
date: '2026-05-11'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: explicit spike / not accepted status
---

# ADR-262 — Evolve Loop Spike: Task Proposal Queue + LLM-driven Skill Candidates

## Status

**Spike** (not Accepted — pending exit criteria evaluation)

**Date:** 2026-05-11
**Owner:** orchestrator
**Tier:** core
**Authors:** orchestrator (Claude Sonnet 4.6)
**Spike Duration:** 3-4 days (time-boxed)
**Implements:** ADR-259 (holaOS Adoption Posture — patterns only)
**Source-pattern:** Internal compliance dossier §Evolve loop post-run (AnnexC::Feature 1)
**Related:** hook `auto-skill-generator`, rule `auto-skill-generation`, `self-improvement-protocol`,
ADR-049 (LLM dispatch), ADR-259, ADR-260

---

## Context

### Current state

luum-agent-os has a functioning but limited skill auto-generation pipeline:

- `hooks/auto-skill-generator.sh` (PostToolUse on `Agent`): detects complex tasks using a
  heuristic threshold (≥10 tool uses or ≥8000 chars output) and generates a `SKILL.md` draft
  using regex pattern matching (`grep -cEi "(created|wrote|generated|..."`) on the agent output.
  Trigger fires on **every** Agent completion — no cadence gate.
- `lib/skill_archive.py`, `lib/skill_efficacy.py`, `lib/skill_lifecycle_promoter.py`,
  `lib/self_improvement.py`: robust post-promotion fitness landscape, baseline-vs-candidate
  comparative gate (`scripts/cos_governed_self_improvement.py`), rollback signal. luum is
  **more rigorous than most OSS alternatives at the promotion stage**.
- `rules/skill-invocation-mandatory.md` (ADR-188): mandatory skill invocation gate at
  confidence ≥0.90.

### Identified gaps (from Annex C §1.3)

The research annex [private clean-room research dossier] §Evolve loop post-run identified five
concrete gaps against a patterns-only reference for LLM-driven evolve loops:

1. **No cadence gate**: the hook fires on every Agent completion, generating redundant drafts
   and wasting tokens. A session doing 20 agent turns can generate 20 skill stubs.
2. **Regex-only extraction**: the shell regex cannot detect nuanced skill candidates — e.g., a
   novel orchestration pattern across multiple tools that uses fewer characters. Quality of
   auto-generated drafts is systematically lower than LLM-extracted ones.
3. **No confidence score**: the binary threshold (tool_uses≥10 OR chars≥8000) produces no
   signal about how reusable a candidate actually is. All drafts land in `auto-generated/`
   indistinguishably.
4. **No task proposal queue**: today the flow is "auto-generate → user discovers by accident
   → `/optimize-skill`". There is no visible operator inbox for pending candidates. The
   human-in-loop gate that governs actual promotion (`self-improvement-protocol.md` §6) is
   effectively unreachable without manual discovery.
5. **No `skill_patch` kind**: luum only creates new skills; improving an existing
   auto-generated skill requires manual `/optimize-skill`, with no automated detection that
   an existing skill could be improved based on recent usage patterns.

### Why a Spike, not an Accepted ADR

Three uncertainties justify time-boxing exploration before committing to an Accepted ADR:

- **Task volume**: unclear how many proposals a 7-day production run would generate — could be
  5 or could be 500. Queue saturation behavior and operator UX at high volume are unknown.
- **LLM extraction cost**: running `lib.dispatch` on every N turns adds compute cost. Daily
  cost at realistic cadence is not characterized.
- **False positive rate**: the confidence threshold (0.72 proposed below) is derived from the
  patterns-only reference; its calibration for luum's specific task profile is unvalidated.

This Spike defines interfaces, file paths, and exit criteria. Implementation during the spike
window is exploratory; the exit-criteria gate decides whether a follow-up Accepted ADR is
warranted.

---

## Spike Scope

### IN SCOPE (spike deliverables)

- Design and prototype of `lib/evolve_skill_review.py`: LLM-driven extraction job
- Design and prototype of `lib/evolve_task_queue.py`: SQLite-backed proposal queue
- Design and prototype of `scripts/cos-evolve-tick.py`: CLI entry point for hook and cron
- Integration of `cos-evolve-tick.py` as PostToolUse hook on `Agent` (every N turns)
- Optional read integration of `list_pending` into `/sdd-explore` context
- 7-day observation window to collect data for exit criteria

### OUT OF SCOPE (explicit exclusions)

- **Replacement of the regex shell hook**: parallel rollout only — `auto-skill-generator.sh`
  continues to run unchanged during the spike. Deprecation decision deferred to a follow-up ADR.
- **Auto-promotion of any candidate**: human-in-loop is unconditional and non-negotiable.
  No candidate may be promoted to `skills/<slug>/SKILL.md` without explicit operator approval.
- **`skill_patch` implementation**: the kind field will be present in the schema and stored in
  the queue, but the actual patch-apply workflow is deferred to the next sprint.
- **Async worker with claim-lease semantics**: the Annex C reference describes a worker with
  lease expiry and retry backoff. This is premature for luum's current volume; the hook is
  synchronous for now.
- **Auto-coupling to `/sdd-new`**: explicitly rejected (see Decision §4 and Alternatives).

---

## Decision

The following decisions are **binding for the spike implementation**. They are not binding
as final architecture until exit criteria are met and a follow-up Accepted ADR supersedes
this one.

### 1. `lib/evolve_skill_review.py` — LLM extraction review job

The review job runs every N turns (default: 3, configurable via `cognitive-os.yaml`
`evolve.review_interval_turns`). It:

1. Reads the last N turns of session log from `.cognitive-os/sessions/<session_id>/`.
2. Calls the LLM via `lib.dispatch` (Qwen primary, Claude fallback — per ADR-049,
   `--providers qwen,claude`). The prompt is written clean-room from functional criteria
   defined in this ADR; it is not derived from any holaOS prompt text.
3. Expects a JSON response conforming to:

   ```json
   [
     {
       "kind": "skill_new | skill_patch",
       "title": "<short title>",
       "rationale": "<why this is reusable>",
       "draft": "<markdown SKILL.md content>",
       "confidence": 0.0,
       "fingerprint_sha256": "<sha256 of normalized draft>"
     }
   ]
   ```

4. Filters out any candidate with `confidence < 0.72` (initial calibration threshold;
   adjustable in `cognitive-os.yaml` `evolve.min_confidence`).
5. Deduplicates against existing queue entries by `fingerprint_sha256`.
6. For passing candidates, delegates to `lib/evolve_task_queue.py` `enqueue()`.

Identifiers use luum-native naming: `EvolveProposal` (not `TaskProposal`),
`evolve_skill_review` (not `evolveSkillReview`), `SkillCandidateResult` (not
`EvolveSkillCandidateRecord`). The LLM prompt is authored from scratch using only the
functional criteria above — no textual content from the Annex C reference implementation
may be incorporated.

### 2. `lib/evolve_task_queue.py` — SQLite-backed proposal queue

Persistent queue backed by SQLite at `.cognitive-os/state/evolve-proposals.db`. Schema:

```sql
CREATE TABLE evolve_proposals (
  proposal_id   TEXT PRIMARY KEY,
  kind          TEXT NOT NULL,         -- 'skill_new' | 'skill_patch'
  title         TEXT NOT NULL,
  rationale     TEXT NOT NULL,
  draft         TEXT NOT NULL,
  confidence    REAL NOT NULL,
  fingerprint   TEXT NOT NULL UNIQUE,
  status        TEXT NOT NULL DEFAULT 'pending',
    -- 'pending' | 'approved' | 'rejected' | 'promoted'
  created_at    TEXT NOT NULL,         -- ISO-8601
  reviewed_at   TEXT,
  reviewer      TEXT,
  reject_reason TEXT
);
```

Operations exposed as public API:

- `enqueue(proposal: EvolveProposal) -> str | None` — inserts if fingerprint not present;
  returns `proposal_id` or `None` if duplicate. Hard cap: if `count(status='pending') >= 50`,
  log warning to `error-learning.jsonl` and return `None` without inserting.
- `list_pending() -> list[EvolveProposal]` — returns all rows with `status='pending'`,
  ordered by `confidence DESC`.
- `approve(proposal_id: str) -> bool` — sets `status='approved'`, records `reviewed_at`
  and `reviewer`. Does not promote; promotion is a separate operator action.
- `reject(proposal_id: str, reason: str) -> bool` — sets `status='rejected'`, records
  `reviewed_at`, `reviewer`, and `reject_reason` (used for future prompt calibration).
- `mark_promoted(proposal_id: str) -> bool` — sets `status='promoted'`. Called by the
  operator after manually copying the draft to `skills/<slug>/SKILL.md` and passing the
  comparative-promotion gate.

### 3. `scripts/cos-evolve-tick.py` — CLI entry point

Executable at `scripts/cos-evolve-tick.py` (snake_case per `[python-naming]` rule).
Commands:

```
cos-evolve-tick run               # Execute review job once (reads last N turns)
cos-evolve-tick list              # Print pending proposals, sorted by confidence
cos-evolve-tick approve <id>      # Mark proposal approved (human decision)
cos-evolve-tick reject <id> \
  --reason "..."                  # Mark rejected; reason stored for prompt tuning
```

**Hook integration**: `hooks/auto-skill-generator.sh` gains a turn-counter gate. On each
PostToolUse `Agent` event, it increments `.cognitive-os/runtime/evolve-turn-counter`. When
the counter reaches `evolve.review_interval_turns` (default 3), it resets the counter and
invokes `scripts/cos-evolve-tick.py run` in the background (non-blocking). The existing
regex-based skill draft generation continues to run in parallel (parallel rollout; no
replacement during spike).

**Kill switch**: if `evolve.enabled: false` in `cognitive-os.yaml`, `cos-evolve-tick run`
exits 0 immediately without calling the LLM. If `COS_DISABLE_EVOLVE_TICK=1` is set in the
environment, same behavior.

### 4. No automatic coupling to `/sdd-new`

The evolve loop does **not** trigger `/sdd-new` automatically. Reasons:

- Annex C §4 explicitly recommends against it: auto-generated `sdd-new` changes would bypass
  the comparative-promotion gate (`self-improvement-protocol.md` §6), which requires
  baseline-vs-candidate metrics.
- SDD is designed for substantial changes; a 50-line skill draft does not warrant the full
  explore→propose→spec→design→tasks pipeline overhead.
- Cascading risk: a busy session could generate 5+ `sdd-new` proposals per day, saturating
  the SDD queue.

**Permitted integration**: `/sdd-explore` may optionally read `lib/evolve_task_queue.list_pending()`
and surface pending proposals as suggested context to the operator. The operator decides
whether to act. This is a read-only, advisory integration — no state is written, no change
is initiated automatically.

### 5. Parallel rollout: coexistence with regex shell hook

During the spike window, both the existing `auto-skill-generator.sh` regex heuristic and the
new `cos-evolve-tick.py` LLM extractor run independently. After the 7-day observation window,
the data collected under the exit criteria will inform a decision on whether to deprecate the
regex hook. That decision is captured in a follow-up ADR, not here.

---

## Consequences

- Spike validates the evolve-loop assumptions in a bounded time window
  with a clear exit decision (proceed / shelve / pivot).
- Risks are listed in §Risks; outcomes feed the Spike Exit Criteria.
- If spike fails its exit criteria, the loop is shelved without further
  investment; if it passes, follow-up ADR formalizes production scope.

## Spike Exit Criteria

The spike converts to a follow-up **Accepted ADR** if and only if all five criteria are met
after the 7-day observation window:

- [ ] **Volume**: queue accumulated ≥ 10 proposals with `confidence ≥ 0.72` in 7 days
      (validates that the LLM extractor is sensitive enough to be useful)
- [ ] **Human approval rate ≥ 30%**: at least 30% of proposals reviewed by the operator
      are approved (validates that the prompt quality is high enough to avoid noise)
- [ ] **LLM cost ≤ $0.05/day**: total dispatch cost for `evolve_skill_review` calls across
      the 7-day window does not exceed $0.35 total (validates that cadence is not wasteful)
- [ ] **Zero high-confidence false positives**: no candidate with `confidence ≥ 0.85` that
      was approved and promoted regresses skill quality below baseline as detected by
      `lib/skill_archive.py` (validates that the confidence threshold filters noise)
- [ ] **Evolve-unique proposals ≥ 50% of total**: proposals generated only by the LLM
      extractor (not also generated by the regex hook) represent at least 50% of the total
      proposal set (validates that the LLM adds detection coverage beyond the regex heuristic)

If any criterion fails, the spike is **closed without promotion**. Findings are archived to
engram under `topic_key: adr/262` and the regex hook remains the sole mechanism.

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **Skill auto-degradation**: LLM proposes a patch that replaces a correct workflow with a hallucinated one | Low (humano-in-loop blocks auto-promote) | High (session broken) | Unconditional human-in-loop; comparative-promotion gate (`self-improvement-protocol.md` §6); `lib/skill_archive.py` rollback signal; draft lives in staging zone, never in `skills/<slug>/` until manually promoted |
| **LLM hallucination in draft**: confidence metric is gamed by a fluent but incorrect draft | Medium | Medium | Confidence threshold (0.72) + fingerprint dedup + reviewer rejection feedback loop stored in `reject_reason`; rejection data used for prompt calibration |
| **Queue saturation**: high-activity sessions flood the queue, degrading list UX | Medium | Low | Hard cap of 50 pending proposals; `enqueue()` returns `None` silently when at capacity; warning emitted to `error-learning.jsonl` |
| **Cost overrun**: review_interval_turns set too low or sessions too long | Low | Medium | Kill switch `evolve.enabled: false` in `cognitive-os.yaml`; daily cost monitored against $0.05/day exit criterion; cadence gate (N turns, not every turn) |
| **Regex hook + LLM hook duplicate proposals**: same skill generated by both mechanisms | High | Low | Fingerprint dedup in `enqueue()` eliminates duplicates; parallel rollout comparison is a feature, not a bug |
| **Turn counter drift on session restart**: counter file not cleaned up between sessions | Medium | Low | Counter file keyed by `<session_id>` in `.cognitive-os/runtime/evolve-turn-counter-<session_id>`; cleaned up on PostStop hook |

---

## Implementation Plan

Spike window: 3-4 days, time-boxed.

**Day 1 — Queue foundation**
- `lib/evolve_task_queue.py`: `EvolveProposal` dataclass, SQLite schema, all five public
  operations, unit tests (`tests/unit/test_evolve_task_queue.py`)
- `scripts/cos_evolve_tick.py`: `list` and `approve`/`reject` commands only (no `run` yet)

**Day 2 — LLM extraction**
- `lib/evolve_skill_review.py`: session log reader, `lib.dispatch` call, JSON response parser,
  confidence filter, fingerprint computation, `enqueue()` delegation
- Clean-room LLM prompt authored from the functional criteria in Decision §1 (no holaOS
  source material)
- Unit tests with mocked dispatch responses (`tests/unit/test_evolve_skill_review.py`)

**Day 3 — Hook integration and CLI**
- `scripts/cos_evolve_tick.py`: `run` command wired to `evolve_skill_review`
- `hooks/auto-skill-generator.sh`: turn-counter gate, background invocation of `run`, kill
  switch check
- Integration test: `tests/integration/test_evolve_tick_integration.py` — end-to-end from
  counter increment to proposal in queue

**Day 4 — Observability and SDD-explore hook**
- Optional: `/sdd-explore` reads `list_pending()` as context
- `cognitive-os.yaml` entries: `evolve.enabled`, `evolve.review_interval_turns`,
  `evolve.min_confidence`
- 7-day observation window starts; daily cost tracked via `llm-dispatch.jsonl`

---

## Alternatives rejected

| Alternative | Rationale for rejection |
|---|---|
| **Auto-promote approved candidates without human review** | Rejected unconditionally. Bypasses the comparative-promotion gate in `self-improvement-protocol.md` §6, which requires baseline-vs-candidate fitness metrics. A single degraded skill silently broken into live rotation could corrupt multiple downstream sessions before detection. |
| **Improve regex shell heuristic instead of LLM extraction** | Regex cannot detect orchestration patterns, multi-tool compositions, or reusable prompt structures that are not reflected in surface-level token counts. The gap is fundamental, not addressable by adding more regex clauses. |
| **Direct coupling of evolve loop to `/sdd-new`** | Rejected per Annex C §4 recommendation. SDD pipeline overhead is disproportionate to a 50-line skill draft; cascade risk at scale is real; comparative-promotion gate would be bypassed. See Decision §4. |
| **Async worker with claim-lease (ADR-073 style)** | Premature for current session volume. The synchronous hook-driven approach is sufficient and easier to debug. Worker semantics can be added as a follow-up if volume data from the spike warrants it. |
| **Dual confidence threshold (high/low)** | Annex C §7 notes that the reference uses a single `MIN_SKILL_CONFIDENCE = 0.72`. A dual threshold (e.g., 0.60 for `skill_patch`, 0.72 for `skill_new`) may be warranted after spike data is collected. Left as an open question rather than a premature decision. |

---

## Compliance Certification

Per ADR-259 §3 requirements:

```yaml
pattern_source: "holaos-annex-c-evolution.md::§Feature 1 (Evolve loop post-run)"
holaos_files_read_by_research:
  - runtime/api-server/src/evolve.ts
  - runtime/api-server/src/evolve-worker.ts
  - runtime/api-server/src/evolve-skill-review.ts
  - runtime/api-server/src/evolve-tasks.ts
holaos_files_blocked_for_impl: ["ALL"]
```

Checklist (Annex F §5):

- [x] Pattern source cited with specific section reference
- [x] No holaOS identifiers used: `EvolveProposal` (≠ `EvolveSkillCandidateRecord`),
      `evolve_skill_review` (≠ `evolveSkillReview`), `evolve_task_queue` (≠ `evolve-tasks.ts`)
- [x] LLM prompt written clean-room from functional criteria in this ADR; no textual
      content from `evolve-skill-review.ts:444-487` or any other holaOS source
- [x] Implementer agent prohibited from reading `/tmp/holaOS*` (ADR-259 §4)
- [x] Implementation language (Python + bash) differs from reference (TypeScript)
- [x] Schema column names independently derived: `proposal_id`, `kind`, `title`, `rationale`,
      `draft`, `confidence`, `fingerprint`, `status`, `reject_reason` (none copied from holaOS)
- [x] Directory structure independently chosen: `lib/evolve_*.py`, `scripts/cos_evolve_tick.py`
      (not mirroring `runtime/api-server/src/evolve*.ts`)
- [x] Audit trail: engram observation to be created at `topic_key: compliance/holaos-adoption/evolve-loop`
      after first verified commit
- [x] Registry entry to be appended to the private holaOS adoptions registry (internal records) before first commit
- [x] `hooks/external-pattern-cleanroom-gate.sh` to run on pre-commit for adoption commits
- [x] Status is **Spike**, not Accepted — implementation is exploratory pending exit criteria
- [x] No `/tmp/holaOS*` paths appear anywhere in this document

---

## Open Questions

1. **Confidence threshold calibration**: this ADR sets `min_confidence = 0.72` based on the
   patterns-only reference. Annex C §5 describes a dual-threshold pattern (one for `skill_patch`,
   one for `skill_new`) that may better match luum's task profile. Should the spike validate a
   single vs. dual threshold, and how does this relate to the `0.90` threshold already used by
   ADR-188? Convergence with the skill-invocation-mandatory threshold is desirable but not yet
   designed. **UNSURE — requires spike data.**

2. **Fixed vs. adaptive cadence**: `review_interval_turns = 3` is a fixed default. A session
   doing 3 micro-turns (each with 1-2 tool calls) generates very little signal; a session doing
   3 heavy turns (each with 15+ tool calls) generates abundant signal. Should the cadence adapt
   to task complexity (e.g., skip review if average tool_uses per turn < 5 in the last window)?
   The turn-counter approach is simpler to reason about but may waste LLM calls on low-signal
   sessions. **UNSURE — requires spike data.**

3. **`skill_patch` versioning**: this ADR stores `kind: skill_patch` in the queue schema but
   defers the patch-apply workflow. A `skill_patch` proposal needs to reference the target skill
   by slug, record the pre-patch fingerprint for rollback, and version the patch itself. Does this
   require a separate ADR for skill versioning (analogous to a migration framework for SKILL.md
   files), or can it reuse `lib/skill_archive.py` snapshots as the rollback mechanism? **UNSURE
   — blocked on `skill_patch` implementation scope decision.**

---

## References

- [private clean-room research dossier] §Evolve loop post-run — abstract specification that is the
  pattern source for this ADR; primary reference for the evolve loop design
- [private compliance dossier — see internal records] — clean-room protocol; governs
  identifier choice, prompt authorship, and audit trail requirements
- ADR-259 — holaOS Adoption Posture (patterns-only library with clean-room rewrite); parent
  governance ADR; all obligations in §3–§5 apply to this ADR
- ADR-049 — LLM Dispatch (`lib/dispatch.py`); governs provider routing (`--providers qwen,claude`),
  Qwen primary to preserve Claude Max budget, metrics to `llm-dispatch.jsonl`
- ADR-188 — Mandatory Skill Invocation at High Confidence; the `0.90` threshold here and the
  `0.72` confidence threshold in this ADR should converge in a future unified signal
- `hooks/auto-skill-generator.sh` — current regex-based trigger; modified in Day 3 to add
  turn-counter gate without removing existing behavior
- `rules/auto-skill-generation.md` — documents the Act/Learn/Reuse cycle and opt-out mechanism
  (`NO_AUTO_SKILL`); to be updated post-spike if exit criteria are met
- `rules/self-improvement-protocol.md` §6 — comparative-promotion gate that remains mandatory
  regardless of evolve loop approval
- `lib/skill_archive.py`, `lib/skill_lifecycle_promoter.py` — promotion infrastructure reused
  by the evolve loop; no modifications required during spike

---
*This ADR references a private clean-room research dossier whose specific
file paths and section headings are intentionally redacted from this public
record per ADR-267 §Layer 4 and the privatize-research migration (commit e961fd3b).*

## Verification

```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q -k ADR-262
```

