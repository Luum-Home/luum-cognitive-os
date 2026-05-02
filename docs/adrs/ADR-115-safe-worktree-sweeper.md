# ADR-115: Safe Worktree Sweeper

- Status: Accepted
- Date: 2026-05-02
- Scope: OS core
- Related: ADR-109, ADR-111, ADR-113

## Context

Cognitive OS creates temporary and validation worktrees for laptop tests, validation capsules, and recovery workflows. These worktrees are useful while active, but stale detached worktrees can accumulate and confuse operators.

Manual cleanup with recursive deletion is unsafe. A worktree can look stale while still being used by `make`, `cos-test`, `pytest`, hooks, or daemons. Raw deletion can also leave git worktree metadata stale.

## Decision

Introduce a safe sweeper primitive:

- implementation module: `scripts/cos_worktree_sweeper.py`
- human CLI wrapper: `scripts/cos-worktree-sweeper.py`

The implementation uses underscore naming so it is importable and testable. The hyphenated wrapper exists only as an operator-friendly CLI path.

## Safety invariants

1. Dry-run is the default.
2. `--apply` is required for deletion.
3. The primary repository worktree is never removed.
4. Branch worktrees are never removed by default.
5. Worktrees outside safe prefixes are kept.
6. Worktrees with live processes or open files are kept.
7. Worktrees with tracked modifications are kept.
8. Worktrees with non-allowlisted untracked files are kept.
9. TTL must elapse before a detached worktree can be removed.
10. Removal uses `git worktree remove --force`, never raw recursive deletion.

## Consequences

The SO can automate cleanup of stale laptop worktrees while preserving active validation capsules and hidden work. This also establishes the naming pattern for Python CLIs: underscore implementation first, optional hyphenated wrapper only when a human-facing path is needed.
