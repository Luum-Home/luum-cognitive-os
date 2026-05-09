---
report_type: git-history-debug-script-audit
scope: remote-and-upstream-preservation
generated_at: 2026-05-09
status: implemented-gap-closure
related_commits:
  - 9742e28c
---

# Git History / Debug Script Audit — Remote and Upstream Preservation

## Question

After adding remote preservation to prelaunch history rewrite flows, verify whether
other debugging, history, or sanitization scripts can still lose `origin` or branch
upstream tracking (`@{u}` / `branch.<name>.remote` / `branch.<name>.merge`).

## Summary verdict

The original prelaunch path was fixed by `9742e28c`, but the broader audit found a
second live history-rewrite path: ADR-218 history sanitization. That path used
`git-filter-repo` through `scripts/cos-filter-repo-wrap.sh` and already restored
remote URLs, but it did not restore branch upstream tracking or missing
remote-tracking refs. This report's implementation closes that gap.

## Audited surfaces

| Surface | Mutates history? | Mutates remotes? | Upstream risk before fix | Action |
|---|---:|---:|---:|---|
| `lib/prelaunch_audit.py` + `scripts/prelaunch-*` | Yes (`git filter-repo`) | Restores remotes | Fixed in `9742e28c` | No new action |
| `scripts/cos-pre-public-risk-audit` | No | No | Could warn on missing remote only | Already extended in `9742e28c` to warn on missing upstream |
| `lib/history_sanitization.py` | Yes (`execute`) | Restored remotes only | **Gap**: upstream config/ref could be lost | Added snapshot/restore/ref-refresh |
| `scripts/cos-filter-repo-wrap.sh` | Yes (`git filter-repo` wrapper) | Restored remotes only | **Gap**: direct wrapper calls could lose upstream | Added snapshot/restore/ref-refresh |
| `scripts/cos-history-sanitization` | Delegates to `lib.history_sanitization.execute` | Delegated | Inherits library gap | Covered by library fix |
| `scripts/install-git-filter-repo.sh` | No | No | None | No action |
| `hooks/control-plane-audit.sh` | No | No | Mentions `filter-repo` as audit text only | No action |
| `hooks/destructive-git-blocker.sh` | No direct rewrite | No | Blocks/warns around destructive git; false-positive grep hits only | No action |
| `hooks/direct-main-guard.sh` | No | No | Parses `-u`/`--set-upstream` as push flags; no mutation itself | No action |
| `scripts/cos-cleanup.sh` | Worktree/stash cleanup | No | grep hit was `git stash push -u`, not upstream | No action |

## Implemented closure

### `lib/history_sanitization.py`

Added:

- `_snapshot_branch_upstreams()` — captures current branch plus branch tracking
  config for every local branch.
- `_restore_branch_upstreams()` — restores `branch.<name>.remote` and
  `branch.<name>.merge`.
- `_refresh_branch_upstream_refs()` — fetches missing remote-tracking refs such
  as `refs/remotes/origin/main`, because config alone is not enough for `@{u}`
  after `git-filter-repo` removes remote refs.
- `_branch_upstream_restore_issues()` — validates restored config and tracking
  refs, failing the execute flow if restore is incomplete.
- Execute/report payload fields:
  - `branch_upstreams_restored`
  - `branch_upstream_refs_refreshed`

### `scripts/cos-filter-repo-wrap.sh`

Added the same protection for direct wrapper use, because operators/tests can
call the wrapper without going through `lib.history_sanitization.execute`:

- snapshot upstream tracking before `git-filter-repo`;
- restore branch config after remotes are restored;
- fetch missing remote-tracking refs;
- write recovery JSON fields:
  - `branch_upstreams_before`
  - `branch_upstream_restore`.

## Validation

Targeted validation run:

```bash
python3 -m pytest \
  tests/behavior/test_filter_repo_wrap.py \
  tests/behavior/test_history_sanitization_execute.py \
  tests/unit/test_history_sanitization.py \
  tests/unit/test_prelaunch_audit.py \
  tests/behavior/test_pre_public_risk_audit.py -q
```

Result:

```text
41 passed
```

Additional checks:

```bash
bash -n scripts/cos-filter-repo-wrap.sh scripts/cos-pre-public-risk-audit
python3 -m py_compile lib/history_sanitization.py lib/prelaunch_audit.py
```

## Residual limitations

This protection covers COS-owned history rewrite flows and the governed
`git-filter-repo` wrapper. It cannot prevent a user or external tool from
manually running:

```bash
git remote remove origin
git config --unset branch.main.remote
git config --unset branch.main.merge
git filter-repo ...
```

outside COS wrappers. The mitigations are detection (`cos-pre-public-risk-audit`)
and using only governed COS rewrite entrypoints.
