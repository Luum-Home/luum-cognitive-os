# ADR-220 — Worktree Divergence Audit Toolchain

## Status
Accepted


<!-- SCOPE: OS -->

**Status**: Accepted — preflight/readiness gate active
**Date**: 2026-05-06
**Related**: ADR-035 (worktree CWD enforcement), ADR-099 (pre-agent snapshot), ADR-116 (governed preflight), ADR-117 (stash mutation reversibility), ADR-129 (safe worktree removal), ADR-182 (branch ownership lock), ADR-219 (work ownership liveness preflight)
**Source**: Operator session 2026-05-06 — sed-fix on `.cognitive-os/preserve-manifests/*` appeared "lost" because commits landed on `main` while the operator was viewing a worktree branch 3 commits behind. Forensic conclusion: silent worktree↔main divergence with no first-class detection.

---

## Context

The 2026-05-06 forensic session uncovered a class of bug that no existing primitive surfaces:

1. The operator (and the orchestrator) modify files in working tree A.
2. Some agent or sub-process commits the changes to `main` (a *different* worktree path).
3. The operator's worktree A is left N commits behind `main`, with the working-tree files **looking identical to before the fix** because the fix landed on a branch the worktree doesn't track.
4. The operator concludes "the change never committed" and may re-apply it, creating duplicate or conflicting work.

The same mechanism manifested for the FSL-1.1-MIT license switch (`598b95bd` on `main`) and the operator-email redaction in preserve-manifests (`02e97bcd` on `main`). Both fixes were *correctly committed* but the worktree branch did not include them, so an audit run against the worktree saw "stale" content that was actually current on `main`.

`cos_work_inventory.py` already reports stash counts, claim queues, and basic worktree status, but it does **not** report:

- Worktree branch ↔ `main` (or upstream) commit divergence (ahead/behind).
- Whether `main` commits since the divergence point touched paths the worktree currently has modified, untracked, or stashed.
- Whether other linked worktrees hold stashes referencing paths that overlap with the current worktree's WIP.
- Whether the working-tree state of "looks unchanged" actually matches `main`'s view of those files, or is just frozen at an older revision.

These signals are exactly the ones an operator needs **before** drafting a plan, applying a fix, or pruning a worktree. Without them, the operator and the orchestrator both make decisions on incomplete state and re-apply or discard work erroneously.

ADR-129 already gates worktree *removal* on safety. ADR-182 already locks branch ownership across sessions. ADR-219 enforces liveness for work claims. None of them detect the **silent divergence** failure mode where everything is "healthy" by their criteria but the operator's mental model is wrong.

## Decision

Adopt a manifest-backed worktree-divergence audit primitive, mirroring the ADR-212 / ADR-215 / ADR-217 pattern:

1. **Canonical CLI**: `cos worktree audit [--json] [--strict] [--against <ref>]`.
2. **Default reference**: `origin/main` if present; falls back to `main`; falls back to `HEAD@{upstream}`.
3. **Manifest declaration**: deferred. Slice A intentionally embeds the ruleset (thresholds, finding categories, allowlist semantics) directly in `lib/worktree_audit.py` rather than shipping `manifests/worktree-audit.yaml`. The manifest schema below is documented as the *target* shape but is not loaded at runtime; promoting it to a real manifest is gated on a second consumer that needs to read the same rules out-of-process. Per project rule "no metadata without consuming code" we do not ship the YAML file until that consumer exists.
4. **Schema-versioned report**: `worktree-audit-report/v1`.
5. **Implementation**: `lib/worktree_audit.py` + `scripts/cos-worktree-audit` Python entrypoint, hooked into the `cos worktree` shell dispatch.
6. **Integration**: ADR-116 governed preflight calls `cos worktree audit --strict` as an *additional* check; BLOCK findings prevent agent launch with a clear remediation hint.

## What the manifest *would* declare (target shape, not yet loaded)

The block below is the manifest schema we will ship the day a second
out-of-process consumer needs the ruleset. Until then, `lib/worktree_audit.py`
embeds the equivalent constants directly.

```yaml
schema_version: worktree-audit/v1
status: active
owner: platform-safety

# Reference branch resolution order
reference_resolution:
  - "origin/main"
  - "main"
  - "@{upstream}"

# Thresholds
thresholds:
  # Worktree behind upstream by this many commits → WARN
  behind_warn: 1
  # Worktree behind upstream by this many commits → BLOCK
  behind_block: 5
  # Files modified in worktree AND touched by main since divergence → BLOCK
  conflict_block: 1   # any single overlap blocks

# Categories the audit must produce
audit_categories:
  - silent_divergence       # worktree behind main, paths look "stale" but are current on main
  - path_conflict_pending   # main touched paths the worktree has modified
  - cross_worktree_overlap  # other linked worktree has stash on overlapping paths
  - reapply_risk            # worktree change set is a substring of a commit already on main

# Each rule maps a category to a level (PASS|WARN|BLOCK) and message template
rules:
  - category: silent_divergence
    level: BLOCK
    message: |
      Worktree branch '{branch}' is {behind} commits behind '{ref}'. The
      following files appear unchanged in this worktree but were modified
      on '{ref}': {paths}. Re-applying changes in this worktree may
      duplicate already-committed work. Run: `git -C {worktree_path}
      merge --ff-only {ref}` (safe if dirty=false) before continuing.

  - category: path_conflict_pending
    level: BLOCK

  - category: cross_worktree_overlap
    level: WARN

  - category: reapply_risk
    level: WARN

# Allowlist for known-safe divergences (e.g. release branches that intentionally diverge)
allowlist:
  - branch_pattern: "release/.*"
    against: "main"
    reason: "Release branches intentionally lag main; not a silent-divergence concern."
```

## What the CLI does

```
cos worktree audit
  -> resolves reference (origin/main → main → @{upstream})
  -> for current worktree:
       - git rev-list --count <ref>..HEAD       → ahead
       - git rev-list --count HEAD..<ref>       → behind
       - git diff --name-only HEAD <ref>        → paths_changed_on_ref
       - git status --porcelain                 → paths_modified_in_wt
       - intersection(paths_changed_on_ref, paths_modified_in_wt) → conflict_pending
       - for each linked worktree:
           git stash list + stash show --name-only → stash_paths
           intersection(stash_paths, paths_modified_in_wt) → cross_overlap
       - for each commit on <ref> since divergence:
           git show --stat → if commit's diff is a strict superset of
           paths_modified_in_wt with same hunks: reapply_risk
  -> emits report under .cognitive-os/reports/worktree-audit/{timestamp}.json:
       - reference: "origin/main"
       - branch: "<current-branch>"
       - ahead: N
       - behind: N
       - findings: [
           {category, level, paths, hint, ...}
         ]
       - exit_code: 0 (PASS), 1 (WARN), 2 (BLOCK with --strict)

cos worktree audit --strict
  -> non-zero exit on any BLOCK-level finding
  -> ADR-116 governed-preflight may consume this exit code
```

## Hard rules

- **Read-only**: the audit MUST never mutate refs, the index, the working tree, or the stash. Verified by an `audit_dry_run` flag passed to all subprocess calls and a test that runs the audit against a fixture and asserts `git status` and `git stash list` are byte-identical before and after.
- **No network**: the audit operates on local refs only. `origin/main` is consulted only if already fetched. The CLI surface a hint to run `git fetch` rather than fetching itself, because fetching is operator-policy-governed.
- **Cross-worktree read is best-effort**: `git -C <linked-worktree> stash list` may fail (locked, missing, on a foreign filesystem). Failures degrade to WARN, never BLOCK.
- **Allowlist is the only way to silence a BLOCK**: there is no `--force` flag at the CLI level. Operator policy lives in the manifest, not in CLI invocation knobs.
- **Schema versioning is non-optional**: every report carries `schema_version: worktree-audit/v1`. Consumers (ADR-116 preflight, dashboards, future Singularity loop) MUST check the version.

## Consequences

### Positive

- Closes the silent-divergence class of bug that bit the 2026-05-06 session twice in a row (license-switch and email-redaction both manifested this).
- Gives operators a single, authoritative answer to "is my worktree out of sync with main in a way that affects my pending work?"
- Layers cleanly on existing primitives (ADR-099 snapshots, ADR-116 preflight, ADR-129 safe removal, ADR-182 branch ownership) without overlapping their concerns.
- Manifest + canonical-CLI + schema-versioned-report shape is now the established pattern (ADR-212/215/217/218); ADR-220 reinforces it rather than introducing a new shape.
- Makes the "merge --ff-only origin/main" decision explicit and reviewable instead of leaving operators to discover the need by accident.

### Negative / trade-offs

- One more tool to maintain. Mitigation: shares ~80% of its plumbing with the existing audit primitives (manifest loader, report writer, exit-code mapping).
- BLOCK on `silent_divergence` will fire when an operator deliberately wants to work on a stale branch (e.g., reproducing an old bug). Mitigation: allowlist supports this via `branch_pattern`.
- `cross_worktree_overlap` requires reading other worktrees' stash list, which can be slow on filesystems with many worktrees. Mitigation: cache stash-list reads per-audit-run with TTL=audit-duration; no cross-run cache.
- Adds a non-zero-cost step to every governed preflight call. Mitigation: typical run on a clean repo is <200ms; budgeted accordingly.

## Alternatives rejected

- **Rely on operator running `git status` / `git log origin/main..HEAD` manually**: rejected. The 2026-05-06 session demonstrates that experienced operators miss this. Tooling is the right fix.
- **Auto-fast-forward the worktree**: rejected. Fast-forwarding a worktree the operator is actively working in changes file mtimes, may break running dev servers, and silently rewrites their mental model of "what's checked out." The audit recommends the merge; the operator runs it.
- **Block all divergence (no thresholds)**: rejected. Worktrees are *expected* to diverge by 1–2 commits during normal flow. Threshold tuning is required.
- **Fold this into `cos_work_inventory.py`**: rejected. `work_inventory` is a snapshot of *active* state (claims, sessions, stashes); divergence is a *comparative* analysis between branches. Different shape, different cadence.
- **Use `git status` upstream tracking output alone**: rejected. `git status` reports ahead/behind counts but not which paths are at risk. Path-level analysis is the whole point.

## Acceptance criteria

```bash
python3 -m pytest tests/unit/test_worktree_audit.py tests/behavior/test_worktree_audit_cli.py -q
scripts/cos worktree audit --json
scripts/cos worktree audit --strict --against origin/main
```

The tests must prove:

- A worktree at parity with `origin/main` produces an empty `findings` list and exit code 0.
- A worktree N commits behind `main` with no overlapping path changes produces a `silent_divergence` finding at WARN level (or BLOCK if N ≥ `behind_block`).
- A worktree behind `main` where `main` modified paths the worktree also has dirty produces a `path_conflict_pending` BLOCK.
- A linked worktree on a different branch with a stash referencing paths in the current worktree's `modified` list produces a `cross_worktree_overlap` WARN.
- A worktree containing changes whose diff is a strict superset of a commit already on `main` produces a `reapply_risk` WARN with the offending commit SHA cited.
- The audit is byte-identical-idempotent on `git status` and `git stash list` (read-only invariant).
- An allowlisted branch pattern (`release/.*`) suppresses the `silent_divergence` finding.
- Schema-version mismatch produces a clear error pointing at the consumer's expected version.

## Implementation slices

1. ~~`manifests/worktree-audit.yaml` skeleton with the rule set above.~~ Deferred (see Decision §3): rules embedded in `lib/worktree_audit.py` until a second consumer needs the manifest.
2. `lib/worktree_audit.py` — embedded ruleset + the five comparison functions (ahead/behind, path-changed-on-ref, modified-in-wt, cross-worktree-overlap, reapply-risk).
3. `scripts/cos-worktree-audit` + `cos worktree` shell dispatch.
4. Unit tests (manifest validation, threshold logic, finding-shape, allowlist).
5. Behavior tests (fixture repo with controlled divergence; assert categories fire correctly).
6. Read-only invariant test (snapshot `git status`/`git stash list`/`.git/index` mtime before/after; assert no drift).
7. ADR-116 governed-preflight integration: optional `audit_calls: [worktree-audit]` array; BLOCK exits propagate.
8. Operator runbook in `docs/runbooks/worktree-audit.md` with the three canonical fix recipes (`merge --ff-only`, rebase-with-care, branch-deliberate-divergence-via-allowlist).

## Open questions

- Should `reapply_risk` BLOCK or WARN by default? Current proposal: WARN, because false positives on hunk-level matching are likely. Revisit after 30 days of telemetry.
- Should the audit fetch automatically when `origin/main` is older than N hours? Current proposal: no. Fetching is operator policy. The audit *reports* staleness ("origin/main is 4h old; consider `git fetch`") but does not act.
- Cross-worktree stash inspection requires acquiring the stash lock briefly. ADR-117 governs that; verify no contention in the integration test before merging.
- Does this primitive need a Singularity reward signal? Defer; out of scope until ADR-200 / Singularity loop is past pilot.

## Verification
```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
```
