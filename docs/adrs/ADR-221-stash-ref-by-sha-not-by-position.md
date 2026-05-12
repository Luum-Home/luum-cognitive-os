---
adr: 221
title: Stash References by SHA, Not by Position
status: accepted
implementation_status: partial
date: '2026-05-06'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: implementation evidence plus partial/deferred/future signal
---

# ADR-221 — Stash References by SHA, Not by Position

## Status
Accepted


<!-- SCOPE: OS -->

**Status**: Accepted — slice 1 active
**Date**: 2026-05-06
**Related**: ADR-099 (pre-agent snapshot copy-on-untracked), ADR-117 (stash mutation reversibility), ADR-200 (state retention controller), ADR-213 (agent preflight before stash snapshot), ADR-220 (worktree divergence audit)
**Supersedes (in part)**: the marker-file format produced by `pre-agent-snapshot.sh` and consumed by `post-agent-snapshot-restore.sh`.
**Source**: Operator session 2026-05-06 — `pre-agent-snapshot.sh` recorded `stash_ref: "stash@{0}"` in three consecutive markers within 60s; the third marker pointed at a different stash than the first marker intended, because new pushes shift the position-based ref.

---

## Context

The current pre/post-agent-snapshot pipeline records stash identity using `stash@{N}` position-based refs:

```bash
# pre-agent-snapshot.sh, after `git stash push`:
STASH_REF=$(git stash list --max-count=1 | head -1 | cut -d: -f1)   # → "stash@{0}"
# Marker file:
{"stash_ref":"stash@{0}", "agent_id":"...", ...}
```

`stash@{N}` is a **position-based reflog ref**, not an immutable identifier:

- `stash@{0}` always means "the most recent stash entry."
- Each new `git stash push` shifts every existing entry: yesterday's `stash@{0}` is today's `stash@{1}`.
- Multi-agent / parallel sessions interleave pushes, so the ref recorded in marker A may now point to the stash created by B by the time A's `post-agent-snapshot-restore.sh` runs.

The 2026-05-06 session reproduced this: three identical `auto-pre-agent-*` stashes accumulated, each marker recorded `stash_ref: "stash@{0}"`, and any one of them resolving its marker would have applied the *wrong* stash. By a sequence of preflight blocks, no `post-agent-snapshot-restore.sh` ever fired and all three orphaned. The bug pattern is documented industry-wide:

- Anthropic Claude Code shipped this exact class of bug ([issue #11005](https://github.com/anthropics/claude-code/issues/11005)).
- The official `git-stash(1)` page warns: *"If you mistakenly drop or clear stashes, they cannot be recovered through the normal safety mechanisms."* — ref-by-position makes "mistakenly" almost certain under concurrency.
- HN consensus, 2016 onward: "I've seen more stash accidents than any other kind with git" ([item 12613062](https://news.ycombinator.com/item?id=12613062)).

The deeper question — whether the OS should be using `git stash` at all as a pre-agent state-capture primitive — is the subject of a separate research report (`docs/research/multi-agent-orchestration-prior-art-2026-05-06.md`). The honest answer there is *no, it shouldn't*, and the recommended replacement is worktree-per-write-agent. That replacement is a larger architectural move tracked separately.

**This ADR is the tactical fix for as long as `git stash` remains in the pre-agent path.** If/when that path is removed, this ADR's hard rules still apply to any other place in the OS that records stash identity (ADR-117 reversibility table, ADR-200 retention controller, future `stash_provenance` calls).

## Decision

All persistence of stash identity in Cognitive OS MUST use the **stash commit SHA** (a 40-char immutable git object hash), never the `stash@{N}` reflog ref.

1. **Capture rule**: at the moment of `git stash push` success, the SHA MUST be resolved via `git rev-parse stash@{0}` and that SHA — not the `@{0}` ref — is the canonical identity.
2. **Persistence rule**: marker files, JSONL events, manifests, and reports written by the pre/post-agent path, by `stash_provenance`, by ADR-117 reversibility tooling, and by any future stash-aware primitive MUST use a `stash_sha` field. The legacy `stash_ref` field MAY be retained for human readability but is informational, not authoritative.
3. **Lookup rule**: consumers MUST locate stashes by enumerating `git stash list --format='%H %gd %gs'` and matching on `stash_sha` to discover the *current* `stash@{N}` position. They MUST NOT use the historical `stash@{N}` value to apply, drop, or inspect.
4. **Drift rule**: if the recorded `stash_sha` is not present in the current stash list, the consumer MUST treat the stash as **already-resolved-or-pruned** and emit a `stash_lost` event rather than silently misapplying.
5. **Apply rule**: `git stash apply <stash_sha>` is the only supported apply form. `git stash apply stash@{0}` MUST NOT appear in any OS-managed code path.

## Marker schema (v2)

```json
{
  "schema_version": "pre-agent-snapshot/v2",
  "stash_sha": "9f3a2c0e7b8d1f4a6c5b8e0d2f3a5c7b9d0e1f2a",
  "stash_ref_at_capture": "stash@{0}",
  "stash_subject": "auto-pre-agent-toolu_01ABC",
  "files": [".goreleaser.yaml", "LICENSE", "..."],
  "agent_id": "toolu_01ABC",
  "session_id": "1778093717-89822-82b264eb",
  "created_at": "2026-05-06T22:42:48Z",
  "snapshot_id": "auto-pre-agent-toolu_01ABC-20260506-224248-64257"
}
```

`stash_ref_at_capture` is preserved purely for human debugging and forensic reconstruction. Consumers MUST ignore it for any decision-making.

## Schema migration

Existing v1 markers (with `stash_ref` only) are tolerated for one release cycle:

- `post-agent-snapshot-restore.sh` reads v1 markers but **logs a `marker_v1_legacy` warning** and resolves the SHA opportunistically by matching the recorded subject (`auto-pre-agent-<agent-id>`) against current stash subjects. If exactly one match is found, restore proceeds. If zero or multiple, restore is refused and the marker is moved aside to `.cognitive-os/runtime/legacy-markers/`.
- v1 markers older than 7 days are auto-quarantined to `.cognitive-os/runtime/legacy-markers/` by the next SessionStart hook (consumes ADR-200 retention controller cadence).
- After one release cycle, v1 markers are no longer read; the legacy-markers directory is the only home for them.

## Hard rules

- **No position refs in persisted artifacts.** Audit: `grep -RE 'stash@\\{[0-9]+\\}' .cognitive-os/runtime/ .cognitive-os/sessions/ .cognitive-os/metrics/` MUST return zero matches in v2-and-later artifacts. CI test enforces this (`tests/audit/test_no_position_stash_refs.py`).
- **No `git stash apply stash@{N}` in OS code.** Audit: `grep -RE 'git stash (apply|drop|pop|show) stash@\\{[0-9]+\\}' hooks/ scripts/ lib/ packages/` MUST return zero matches. CI test enforces (`tests/audit/test_no_position_apply_in_os_code.py`).
- **`git rev-parse stash@{0}` is the only supported capture path.** Document the exact command; provide a single helper (`lib/stash_sha.py:resolve_top_stash_sha`) that ALL hooks share. No inlining.
- **Drift handling is mandatory, not optional.** A `stash_lost` event MUST be emitted to the metrics JSONL whenever a recorded SHA is absent from the current stash list. Silent miss = test failure.
- **The lookup helper enumerates `git stash list --format='%H %gd'`**, not the default human format that ADR-099 currently parses. The default format is whitespace-fragile. v2 mandates `--format` to make parsing unambiguous.

## Consequences

### Positive

- Eliminates the entire class of "applied the wrong stash" / "applied an already-applied stash" bug under concurrency. The 2026-05-06 forensic incident becomes structurally impossible.
- Makes stash identity portable across processes, sessions, and time. Two sessions inspecting the same SHA see the same object regardless of stash list ordering on either end.
- Aligns Cognitive OS with how Anthropic's eventual fix to [#11005](https://github.com/anthropics/claude-code/issues/11005) will likely have to be shaped (immutable identity by hash). Reduces post-fix migration cost.
- Clean, narrow, testable: ~50 LOC of code change per consumer, plus one shared helper, plus two CI audit tests.

### Negative / trade-offs

- One-release-cycle of dual-format support adds complexity. Mitigation: the migration path is explicit, time-bounded, and exercised by tests.
- Operator-facing logs lose the convenient `stash@{0}` shorthand. Mitigation: keep `stash_ref_at_capture` in the marker for forensic readability; tooling can still display `stash@{0} (sha: 9f3a...)` for humans.
- Existing in-flight markers from prior sessions become "v1 legacy" and trigger the warning path on restore. Mitigation: the v1 reader is conservative (refuses ambiguous matches), so this is fail-safe.
- Increases the amount of code that depends on the `stash_provenance.jsonl` writer staying schema-correct. Mitigation: the writer was already governed; ADR-221 just adds a field.

## Alternatives rejected

- **Continue using `stash@{N}` and deduplicate by enforcing a single-agent-at-a-time invariant**: rejected. ADR-211 (service mode readiness) explicitly contemplates parallel agents; ADR-099 is already running stash-via-SHA collision-prone code in the parallel case.
- **Rename stashes to embed agent-id in the subject and look up by subject**: rejected. The subject *is* already the agent-id (`auto-pre-agent-<agent-id>`). Subject-matching is what v1-legacy fallback does — it works for one release but is fundamentally fragile (not unique across sessions, not unique under retry).
- **Use `git stash store --message` with a deterministic SHA-based message**: rejected. `store` requires a tree object, not a stash entry; it would mean reimplementing what `stash push` does and managing the working-tree state manually. Bigger blast radius than the bug being fixed.
- **Eliminate `git stash` from the pre-agent path entirely (worktree-per-agent)**: this is the right long-term move and is tracked separately by the prior-art research report. ADR-221 is the tactical fix that holds while the larger move is sequenced. Not rejected — deferred.
- **Use `git rev-parse refs/stash@{<id>}` syntax**: rejected. Same position semantics, just a different spelling.

## Implementation status — 2026-05-06

Slice 1 is active:

- `lib/stash_sha.py` provides SHA-first stash helpers.
- `lib/snapshot_manager.py` writes `tracked_stash_sha` in snapshot manifests and applies by SHA when available.
- `hooks/pre-agent-snapshot.sh` writes marker schema `pre-agent-snapshot/v2` with `stash_sha` and `stash_ref_at_capture`.
- `hooks/post-agent-snapshot-restore.sh` resolves current stash position from `stash_sha`, applies by SHA, drops the resolved ref only after success, and tolerates shifted stash positions.
- Regression tests cover SHA resolution under stash position drift and PostToolUse restore after a later stash shifts `stash@{0}`.

Remaining follow-up: update `stash_provenance` / SessionStart reapply to persist and consume `stash_sha`; add grep-based audit tests forbidding position refs in apply/drop/show code paths.

## Acceptance criteria

```bash
python3 -m pytest tests/unit/test_stash_sha.py tests/behavior/test_pre_post_agent_snapshot_sha.py tests/audit/test_no_position_stash_refs.py tests/audit/test_no_position_apply_in_os_code.py -q

# Behavior: capture → drift-introduce → restore-by-sha
python3 -m pytest tests/behavior/test_stash_drift_safe_restore.py -q
```

The tests must prove:

- `lib/stash_sha.resolve_top_stash_sha(repo)` returns the 40-char SHA of the most recent stash and asserts the SHA is present in `git stash list --format='%H'`.
- After `pre-agent-snapshot.sh` runs in a dirty repo, the marker file contains `schema_version: pre-agent-snapshot/v2` and a `stash_sha` field whose value matches `git rev-parse stash@{0}` taken immediately after.
- Pushing two more stashes (which shifts `stash@{0}`) does NOT change the consumer's ability to find and apply the original stash by SHA in the post-agent restore.
- A v1 legacy marker (no `stash_sha`) with an unambiguous subject match resolves successfully and emits a `marker_v1_legacy` warning.
- A v1 legacy marker with ambiguous subject matches refuses to restore and quarantines the marker.
- A marker whose `stash_sha` is no longer present in stash list emits `stash_lost` and exits 0 (advisory; never blocks).
- The CI audit tests fail when introducing a `stash@{0}` literal in OS code.
- Round-trip on a fixture repo: capture → 5 concurrent stashes pushed by other actors → original stash still applied correctly by SHA.

## Implementation slices

1. `lib/stash_sha.py` — `resolve_top_stash_sha`, `resolve_sha_to_position`, `find_sha_in_stash_list`. ~40 LOC.
2. Update `pre-agent-snapshot.sh` (legacy mode and copy-on-untracked mode both) to call the helper post-`stash push`, write `stash_sha` into marker, retain `stash_ref_at_capture` for forensics. Bump marker schema_version to v2.
3. Update `post-agent-snapshot-restore.sh` to read `stash_sha` first, fall back to subject-match for v1, refuse-and-quarantine on ambiguity. Apply via `git stash apply <sha>`.
4. Update `lib/snapshot_manager.py` (Python copy-on-untracked path) to mirror the bash changes.
5. Update `stash_provenance` module (ADR-116 P4.3) to record `stash_sha`.
6. Update `session-start-stash-reapply.sh` (ADR-116 P4.3 reapply) to look up by SHA.
7. CI audit tests `tests/audit/test_no_position_stash_refs.py` and `test_no_position_apply_in_os_code.py`. Both grep-based; both fast.
8. Behavior tests for drift-safe restore and v1-legacy fallback.
9. Update operator runbook `docs/runbooks/agent-snapshot-recovery.md` with the SHA-first guidance.

## Open questions

- Should `stash_provenance.jsonl` be migrated retroactively (rewrite v1 entries to v2)? Initial answer: no. Append-only log; v1 entries are read by the v1-legacy reader for one cycle, then archived.
- Should we also record the stash *tree SHA* (the commit's tree) for an additional integrity check? Initial answer: defer. Stash commit SHA is sufficient for identity; tree SHA is redundant unless we discover hash collisions in practice (we won't).
- Does the v1-legacy fallback need to handle the case where the recorded subject was modified (e.g., `git stash apply --message`)? Initial answer: no. OS-managed stashes never set custom messages; operator-managed stashes are out of scope for this ADR.
- Coordinate with ADR-117 reversibility: the reversibility table records stash ops by `stash_ref`; v2 should add `stash_sha`. Tracked as a sub-task in slice 5.

## Verification
```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
```
