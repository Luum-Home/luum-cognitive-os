# Governance Tools Consolidation Plan

## Goal

Keep the governance primitives that beat vanilla Claude Code for real work, and
remove or tier the governance that adds friction without immediate product value.
This plan implements ADR-125 and feeds ADR-123/ADR-124.

## What stays valuable by default

| Primitive | Why it stays |
|---|---|
| Engram memory | Persistent cross-session recall is not provided by vanilla harnesses. |
| Claim verification | Prevents false-done reports and unverified completion claims. |
| Concurrent-write guard | Prevents two sessions from editing the same file blindly. |
| Stash auto-reapply / snapshot lifecycle | Protects WIP when agents/rebases/stashes interact. |
| FS/session reaper | Cleans dead residue that otherwise creates false blockers. |
| Branch/worktree closure | Gives agents a safe protocol for leftover worktrees/branches. |
| Protected landing | Serializes main and prevents stale-head pushes. |

## What becomes opt-in or maintainer-only

| Primitive | New default |
|---|---|
| Primitive harvester | `lab` / explicit maintainer run |
| Aspirational audit | `maintainer` / release audit |
| Dogfood scoring | `maintainer` / periodic report |
| Deep hook scorecards | `maintainer` unless hook touched |
| Capability coverage meta-analysis | `maintainer`; statusline may expose only a lightweight metric |
| Large chaos N=50 | `lab` / scheduled, not per landing |
| Heavy ADR formalism | Maintainer/platform changes only; lightweight decisions for consumer projects |

## Phase 1 — Governance inventory metadata

### Deliverables

- Add `governance_class: runtime-safety | delivery-structure | meta-governance`
  to hooks, skills, scripts, and doctors.
- Add `distribution: core | team | maintainer | lab` where missing.
- Generate a report of default-on governance by profile/distribution.

### Border cases

- A primitive has both runtime-safety and meta-governance behavior.
- A maintainer-only hook is referenced by a core profile.
- A script has no hook but is called by a default hook.

### Acceptance

- [ ] Every projected default hook has governance class metadata.
- [ ] Default `core` report contains no meta-governance primitives.
- [ ] Missing metadata fails audit for new primitives.

## Phase 2 — Single-source claim ledger

### Deliverables

- Choose one canonical claim API and storage schema.
- Deprecate duplicate claim files/modules with shims.
- Add migration/read compatibility for existing files.

### Known overlap

- `lib/task_claim_ledger.py` uses `.cognitive-os/runtime/task-claims.json`.
- `scripts/cos_task_claims.py` uses `.cognitive-os/tasks/active-claims.json`.

### Acceptance

- [ ] One canonical claim writer remains.
- [ ] Readers tolerate old schemas but emit canonical output.
- [ ] Dispatch/preflight gates read the same source.

## Phase 3 — Canonical project-root resolution

### Deliverables

- Introduce one project-root resolver used by hooks and scripts.
- Define env precedence for `COGNITIVE_OS_PROJECT_DIR`, `CODEX_PROJECT_DIR`,
  `CLAUDE_PROJECT_DIR`, explicit `--project-dir`, and `pwd`.
- Add contract tests for hooks invoking scripts.

### Acceptance

- [ ] Hook root and script root match in synthetic tests.
- [ ] Explicit `--project-dir` cannot be silently ignored.
- [ ] Diagnostics print the resolved root when blocking.

## Phase 4 — Snapshot lifecycle policy

### Deliverables

- Auto-snapshot only when risk justifies it:
  - dirty tracked state;
  - untracked WIP above threshold;
  - agent launch that can write;
  - strict/team/maintainer mode.
- No runtime marker for `skip_clean` snapshots unless post hook is guaranteed.
- Symmetry tests for pre/post restore under success, block, crash, and timeout.

### Acceptance

- [ ] No stash/marker residue after read-only or clean sub-agent launches.
- [ ] Dirty WIP is recoverable after crash.
- [ ] Blocked launches cannot create orphaned stashes.

## Phase 5 — Active primitive discovery

### Deliverables

- Replace large undifferentiated skill lists with active subsets:
  - active in current distribution;
  - active in current profile;
  - maintainer/lab hidden unless requested.
- Add `cos primitives active` report.

### Acceptance

- [ ] Agents can see the 10–20 relevant primitives, not 150+ items.
- [ ] Hidden primitives remain searchable when explicitly requested.
- [ ] Discovery output marks dormant/experimental primitives honestly.

## Phase 6 — SDD and model routing as complexity-triggered structure

### Deliverables

- SDD defaults to medium+ changes, not trivial edits.
- Model routing policy declares cost/latency targets.
- Audit trail remains always available but low-noise.

### Acceptance

- [ ] Trivial fixes can bypass SDD without warning.
- [ ] Medium+ changes get SDD recommendation.
- [ ] Routing decisions are logged without blocking work.

## Phase 7 — ROI dashboard and friction budget

### Deliverables

- Track friction budget per session:
  - blocker count;
  - false-positive candidates;
  - repair time;
  - bypass count;
  - governance time vs build time estimate.
- Track benefit signals:
  - incidents prevented;
  - WIP recovered;
  - duplicate work avoided;
  - time saved by memory/SDD reuse;
  - model-routing cost avoided.
- Report net estimate: `benefit_minutes - friction_minutes - maintenance_minutes`.

### Acceptance

- [ ] A session can report governance overhead.
- [ ] A session can report at least one benefit category or explicitly say none.
- [ ] Top friction causes feed ADR-123 telemetry.
- [ ] Guards with high false-positive rate are demoted to `warn` until fixed.
- [ ] Dogfood/self-use metrics are not accepted as productivity ROI by
      themselves.

## Phase 8 — Aggressive archive/delete trial

### Deliverables

- Rank primitives by recent actual use, incident-prevention value, and friction.
- Mark the bottom 50% as `archive-candidate` unless they protect secrets, WIP,
  or main landing.
- Move archive candidates out of default projection for one month.
- Track whether operators/agents miss them.

### Acceptance

- [ ] Default active primitive list is small enough for agents to choose from
      without discovery overload.
- [ ] Archived primitives remain recoverable in `lab` or history.
- [ ] No runtime-safety primitive is archived without replacement.
- [ ] After one month, keep only primitives with measured use or clear
      incident-prevention value.

## Exit criteria

- [ ] Core distribution contains only runtime-safety primitives and lightweight
      delivery structure.
- [ ] Team distribution adds coordination without maintainer meta-noise.
- [ ] Maintainer/lab can still run full SO audits intentionally.
- [ ] Duplicate claim ledgers are consolidated.
- [ ] Project-root resolution is canonical.
- [ ] Snapshot/stash lifecycle has crash/block symmetry tests.
- [ ] Active primitive discovery is scoped to distribution/profile.
- [ ] ROI dashboard shows non-negative net productivity for target usage
      contexts, or the active default set is reduced further.
