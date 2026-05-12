---
title: Post-Mortem — Cross-Session Branch Collision and Data Loss
date: 2026-05-05
status: draft
scope: maintainer
severity: HIGH
tags: [postmortem, concurrency, worktree, adr, governance, blameless]
incident_window: '2026-05-05 22:45–22:55 UTC-3 (~10 min)'
author: orchestrator-LLM (Claude) under operator review
---

# Post-Mortem — Cross-Session Branch Collision and Data Loss

## Severity classification

**HIGH.** Two concurrent orchestrator sessions wrote to the same branch
without mutual visibility, producing one auto-commit of correct work plus
two auto-commits of conflicting work, and overwriting two in-flight ADR
files (ADR-171, ADR-179) that contained ~12 KB of recoverable but not yet
git-tracked content. No production system was affected; no data shipped to
users. The incident exposed a structural concurrency gap in COS that has
been latent since the multi-worktree pattern was introduced.

## Incident summary

During an active session that the operator had explicitly placed under a
"no commits until I tell you" constraint, three commits landed on the
active branch (`session/41961ce2-paperclip-rejection-multi-surface`) over
approximately ten minutes:

1. `937d0ece feat(skills): activate routing store and lifecycle proposals`
   — internally consistent capture of this session's agent work; treated
   as **CORRECT**.
2. `a4bd126d refactor: tombstone rejected integration surface` — applied a
   "delete-and-tombstone" disposition to Paperclip surfaces; **CONFLICTS**
   with this session's "annotate-and-keep" pattern.
3. `aeb391b0 chore: finish rejected surface tombstones` — added 9 ADR
   tombstones (003, 004, 005, 043, 046, 085, **171**, **173**, **179**)
   and deleted further Paperclip files; **DESTROYED** ADR-171-reject (~12
   KB) and ADR-179-rules-auto-derive content that was authored earlier
   tonight and not yet committed.

All three carried `X-COS-Origin: kind=orchestrator harness=claude`
metadata. Commit 1 used the same `X-COS-Session` ID as the active session;
commits 2 and 3 used **different session IDs**, indicating a separate
concurrent orchestrator process committed onto the same branch.

Recovery: ADR-171-reject and ADR-179-rules content remain accessible in
agent JSONL output files at
`/private/tmp/claude-501/<project>/<session>/tasks/<agent-id>.output`
until the parent session terminates. Six other newly-authored ADRs of this
session (172, 174-bis, 175, 178, 180, 181) survive as untracked files on
disk.

## Timeline (UTC−3)

| Time | Event |
|---|---|
| ~17:00 | Active session begins, branch `session/41961ce2-paperclip-rejection-multi-surface`. Operator instructs "no commits until I tell you." |
| 17:00 – 22:30 | Multiple agents launched in this session: skill router observability, ADR-174 auto-derive, ADR-176 SkillStore, ADR-177 lifecycle, ADR-178 OpenHarness, ADR-179 rules, ADR-181 ADR-relevance, etc. All produce content; some ADRs are authored as untracked files. |
| 22:45:30 | **Commit 1** lands automatically (`937d0ece`). Same `X-COS-Session` as active session. Captures most of session work. Auto-commit hook in COS infrastructure fired without explicit operator approval. |
| 22:53:18 | **Commit 2** lands automatically (`a4bd126d`). Different `X-COS-Session` ID. Applies hard-delete disposition to Paperclip surfaces; modifies 174 files. |
| 22:54:45 | **Commit 3** lands automatically (`aeb391b0`). Different `X-COS-Session` ID. Adds 9 ADR tombstones, including ADR-171, ADR-173, ADR-179 — **overwriting in-flight content** of ADR-171-reject-paperclip-integration.md and ADR-179-rules-auto-derive-routing.md. |
| 23:00 (approx) | Operator notices "many uncommitted changes across worktrees" and asks orchestrator to verify state. |
| 23:05–23:15 | Forensics: `git log main..HEAD` reveals 3 commits operator did not authorize. Per-commit diff inspection identifies content overlap (commit 1) versus content collision (commits 2, 3). ADR-171/173/179 collisions confirmed. |
| 23:15 | Two in-flight agents stopped pre-emptively to prevent further drift. |
| 23:30 | Forensics report drafted (`docs/06-Daily/reports/session-state-forensics-2026-05-05.md`). |
| ~23:45 | Manifest schema migrated v1 → v2 to expose the categorical truth that the flat "86.5% coverage" had been masking. Tests updated; 74/76 pass. |
| 23:50 | Operator asks for post-mortem. |

## Impact

### Direct impact (this incident)

- **Two ADR files lost from disk** (recoverable from agent JSONL outputs):
  - `docs/02-Decisions/adrs/ADR-171-reject-paperclip-integration.md` (~12 KB, full
    rejection ADR with falsifiable claim, drafted earlier tonight).
  - `docs/02-Decisions/adrs/ADR-179-rules-auto-derive-routing.md` (drafted by agent
    `a7360daf` earlier tonight).
- **Three ADR number slots compromised**: 171, 173, 179 now occupied by
  generic "Reserved architecture decision slot" tombstones.
- **One file deleted that this session had deliberately preserved**:
  `lib/paperclip_client.py` (~15 KB), which this session had annotated as
  ARCHIVED-per-ADR-171 and intentionally retained for archaeology. The
  competing session deleted it outright.
- **Working tree desynchronization**: 107 modified + 58 untracked files
  on top of HEAD, which itself contains commits the operator did not
  authorize. Reconciliation requires a deliberate branch-state correction.

### Indirect impact

- **Operator trust impact**: explicit "no commits" instruction was
  violated by infrastructure-level automation. The operator must now
  audit commit provenance even on instructions they believed enforced.
- **Doctrine drift**: the active branch now carries two contradictory
  policy choices (annotate-and-keep vs delete-and-tombstone) for the
  same subject (Paperclip rejection). Downstream contributors may apply
  either pattern, increasing confusion.
- **Numbering integrity**: the ADR sequence has tombstones occupying
  numbers that were actively being used. Future ADR authors face risk of
  repeated collision unless the numbering surface gains a global lock.

### Non-impact

- No production code shipped.
- No external user affected.
- No commit pushed to remote (`origin`); incident is fully local.
- No tests broken on `937d0ece` snapshot; the working tree state passes
  74/76 contract tests after the v2 schema migration.

## Root causes

### Primary — structural concurrency gap

**No branch ownership lock exists across orchestrator sessions.** Each
Claude Code session is a separate process with isolated context. The
filesystem (git, `.cognitive-os/`, `manifests/`) is the only shared bus,
and it is read asynchronously without coordination. Two orchestrators
can hold the same branch simultaneously and neither will see the other
until a `git status` or similar inspection happens.

The COS already has partial concurrency primitives:

- `.cognitive-os/runtime/task-claims.json` (advisory leases, not
  enforced),
- `.cognitive-os/sessions/active-sessions.json` (registry, not
  exclusion),
- `X-COS-Origin / X-COS-Session` commit markers (post-hoc audit, not
  prevention),
- `destructive-git-blocker.sh` hook (per-session, does not see other
  sessions),
- ADR-111 concurrency_safety (passive observation, no force arbitration).

None of these prevent concurrent commits to the same branch from
different orchestrator processes.

### Secondary — auto-commit infrastructure with insufficient gating

Several COS subsystems can produce git commits without orchestrator-LLM
authorization:

- `auto-skill-generator.sh` (PostToolUse Agent) writes new SKILL.md and
  may trigger an auto-commit chain.
- `consequence-evaluator.sh` (per ADR-100) records consequences, which
  may project to commits.
- ADR tombstone tooling created in commit 3 (`scripts/cos-adr-tombstone`)
  itself produces commits when invoked.
- The `commit_provenance.py` infrastructure (ADR-088) is designed to
  *attribute* such commits via PPID-chain lookup, but it does not gate
  whether the commits should happen.

These auto-commits are intentional architectural design (the operating
philosophy is that low-tier work should self-heal) but they bypass the
operator's "no commits" instruction because that instruction targets
the orchestrator-LLM, not the lower automation layers.

### Tertiary — multi-worktree pattern without cross-worktree coordination

A second worktree
(`luum-agent-os-session50-paperclip-purge`) existed from a prior session,
on a sibling branch (`session/50c35ce9-remove-paperclip-multi-surface`).
This worktree itself was not the source of commits 2 and 3 (its HEAD is
the same as the v0.26.0 release commit), but its existence reflects a
pattern where multiple worktrees with overlapping task scopes coexist.
The session that authored commits 2 and 3 may have used a third
worktree or a subprocess invocation that was not attributable to any
visible IDE tab.

### Quaternary — ADR numbering has no global lock

ADR numbers are assigned by file naming convention. Two sessions can
both author "ADR-171" without either seeing the conflict until commit
time. Tonight's collision (171, 173, 179) is the surfaced example; the
risk is structural and pre-existing.

## Detection

The incident was detected by the operator manually inspecting branch
state, not by any automated alarm. Detection latency: approximately 5–10
minutes after the third commit landed.

No COS automation detected:

- That commits had landed during a "no commits" window.
- That two `X-COS-Session` IDs had touched the same branch.
- That an ADR file present in the working tree had been overwritten by a
  same-named tombstone.
- That two contradictory disposition policies (annotate vs delete) were
  now both present in the branch history.

## Response

| Action | Time | Outcome |
|---|---|---|
| Pause in-flight agents | 23:15 | Two agents stopped (`a8095cf5`, `afe317dd`); one had been started ~5 minutes earlier on a related task and would have compounded drift. |
| Run `git log main..HEAD` and per-commit diff | 23:15–23:25 | 3 unauthorized commits identified; per-file impact mapped. |
| Verify ADR collision via `ls` | 23:30 | Confirmed `ADR-171-tombstone.md` exists; `ADR-171-reject-paperclip-integration.md` absent. |
| Search stash + reflog + git fsck for recovery | 23:35 | Lost ADRs not in any git object. Confirmed recovery path is agent JSONL outputs. |
| Draft forensics report | 23:30–23:45 | `docs/06-Daily/reports/session-state-forensics-2026-05-05.md` lands; classifies commits, lists collisions, documents recovery options. |
| Migrate manifest schema v1 → v2 | 23:45–23:55 | Categorical truth restored. Coverage broken out by canonical (51.2 %), runtime-projection (40.3 %), package-bundled (28.4 %); legacy flat 86.5 % deprecated. Tests updated; 74/76 pass. |
| Draft post-mortem (this document) | 23:55+ | Records timeline, root causes, action items, lessons. |

No reset, revert, or rebase has been performed. No commit has been
pushed to remote. The branch is in a recoverable state pending operator
disposition decision.

## Lessons learned

### 1. "No commits" is an incomplete contract under current architecture

The operator's instruction targeted the orchestrator-LLM, but the COS
runtime (auto-skill-generator, consequence-evaluator, ADR tooling) has
its own commit-emitting paths that the orchestrator-LLM does not
control. Future "no commits" windows must either:

- be enforced at a lower layer (a global commit kill-switch hook), or
- be communicated as "no commits *to remote*" rather than "no commits
  at all", with an explicit understanding that local commits may still
  occur.

### 2. Branch ownership cannot be assumed

Tonight is the first time this session has observed two orchestrator
processes touching the same branch concurrently. The COS has carried
this latent risk for the entire multi-worktree era. The doctrine
"branch is a single-writer surface" was implicit and unenforced;
multiple writers exposed the gap immediately.

### 3. Tombstone-as-disposition is not a no-op

The ADR tombstone primitive added in commit 3 (`scripts/adr_tombstone.py`,
`skills/adr-tombstone/SKILL.md`) is a useful tool for marking abandoned
decisions, but applied without numbering integrity checks it can
overwrite live work. Tonight it overwrote ADR-171 and ADR-179 silently.
The tool itself needs a precondition: refuse to tombstone a number that
is currently authored or referenced elsewhere.

### 4. Heuristic claims need symmetric verification

Earlier in this same session, the audit-of-audits found that prior
research reports had asymmetric depth: external side examined at
source-level, COS side at description-level. The pattern recurred at the
infrastructure layer: this session's orchestrator inspected its own
work in detail but did not inspect the parallel session's work at all.
Symmetric verification is a doctrine that must apply to *processes* as
well as *artifacts*.

### 5. Coverage metrics that mix universes lie

The legacy `min_routed_skill_coverage_percent: 86.4` reported a
green-looking number against a confused universe (canonical + runtime-
projection + some package-bundled, with disabled and name-mismatched
skills mis-counted). The v2 schema reveals the true picture: 51.2 %
canonical, 40.3 % runtime-projection, 28.4 % package-bundled. The
operator's intuition — "test green over wrong-modeled truth" — was
correct.

## Action items

| # | Priority | Action | Owner | Tracking |
|---|---|---|---|---|
| 1 | P0 | Recover ADR-171-reject and ADR-179-rules content from agent JSONL outputs before session terminates. | operator | manual recovery |
| 2 | P0 | Tag a snapshot of current state: `git tag pre-recovery-snapshot-2026-05-05`. | operator | one-line command |
| 3 | P1 | Decide Paperclip disposition policy explicitly: annotate-and-keep vs delete-and-tombstone. Document in an ADR. Then reconcile commits 2+3 against the chosen policy. | operator | follow-up ADR |
| 4 | P1 | Implement **branch ownership lock** primitive (proposed ADR-182). Hook on `PreToolUse Bash` matcher `git checkout|switch|commit`; uses `flock` over `.git/refs/heads/<branch>` keyed on `session_id`. Releases on session-end or TTL. | infrastructure | ADR-182 |
| 5 | P1 | Implement **cross-session event log** (proposed ADR-183). Append-only `.cognitive-os/cross-session-events.jsonl` of session-start, branch-acquire, agent-spawn, file-write-intent, commit-intent, branch-release, session-end. Consumed by UserPromptSubmit hook to inject peer-session awareness into the orchestrator's context. | infrastructure | ADR-183 |
| 6 | P2 | Implement **manager-of-managers daemon** (proposed ADR-184, refines ADR-163 cos-instance-installer). The only process with direct write access to certain critical paths. Other sessions submit intent via API; daemon arbitrates. | infrastructure | ADR-184 |
| 7 | P1 | Add **ADR numbering integrity** test (`tests/contracts/test_adr_numbering_integrity.py` already exists from commit 3 — extend or rewrite). Should refuse: (a) two non-tombstone ADRs with the same number, (b) tombstone overwriting an active ADR, (c) ADR file with frontmatter `adr: N` that does not match `ADR-N-` filename prefix. | tests | enhancement to existing |
| 8 | P2 | Add **commit kill-switch hook** for "no commits" windows: env var `COS_NO_COMMITS_THIS_SESSION=1` blocks all local commits regardless of source (auto-skill-generator, consequence-evaluator, etc.). Operator sets it; clears explicitly. | infrastructure | small new hook |
| 9 | P2 | Document the **multi-worktree pattern** safely. ADR proposing: (a) one worktree per task scope, (b) explicit `git worktree list` audit at session start, (c) cleanup of stale worktrees as part of session-wrapup. | docs | ADR follow-up |
| 10 | P3 | Add **agent JSONL recovery primitive**: `scripts/cos-recover-from-agent-output <agent-id> <file-path>` that extracts file content from a stored agent JSONL when on-disk content has been lost. Tonight this would have been used to recover ADR-171-reject. | tooling | scripts/ |

## Recovery plan (for the active branch state)

The forensics report already proposed three options; the post-mortem
recommends **Option C** (branch surgery + cherry-pick), restated here as
the canonical sequence:

```bash
# Step 0 — safety
git tag pre-recovery-snapshot-2026-05-05
zip -r /tmp/wip-snapshot-$(date +%s).zip . \
  -x '*/.git/*' '*/node_modules/*' '*/.venv/*'

# Step 1 — recover lost ADR content from agent outputs
# (manual: parse agent JSONL files to extract ADR-171-reject and ADR-179-rules text)

# Step 2 — clean branch
git checkout -b session/41961ce2-clean 9d7598dd

# Step 3 — cherry-pick the good commit
git cherry-pick 937d0ece

# Step 4 — re-author Paperclip disposition under explicit policy
# (manual: apply chosen disposition to Paperclip surfaces)

# Step 5 — restore lost ADRs as new files
# (manual: write ADR-171-reject-* and ADR-179-rules-auto-derive-* with recovered content;
#  delete or merge the tombstones depending on chosen numbering integrity policy)

# Step 6 — commit WIP in coherent groupings
# (manual: stage by topic, commit small)
```

This must be done by the operator, not by an autonomous agent. Tonight's
incident demonstrates that autonomous agents, even well-instructed ones,
do not currently have enough cross-session situational awareness to
perform this safely.

## Cross-references

- `docs/06-Daily/reports/session-state-forensics-2026-05-05.md` — forensic detail
  per commit and per file.
- `docs/06-Daily/reports/lifecycle-promotion-gap-2026-05-05.md` — earlier in this
  session, identifies the doctrine-vs-enforcement pattern that recurs
  here at the concurrency layer.
- ADR-088 — commit_provenance attribution (post-hoc audit infra).
- ADR-100 — auto-rollback (relevant for self-healing pattern that fired
  tonight).
- ADR-111 — concurrency_safety (passive primitives present today).
- ADR-163 — cos-instance-installer (precursor to the manager-of-managers
  daemon proposed in action item #6).

## Closing note

This is a blameless post-mortem. No agent or operator action is faulted.
The incident exposes a structural gap that has been latent in the COS
design since multi-worktree was introduced. The action items above
target the gap, not any participant.

The operator's instinct ("we have many worktrees and branches with many
changes — let's unify and review minutely") was correct and prevented
escalation. Without that catch, the next session would have inherited
two contradictory disposition policies as if both were settled.
