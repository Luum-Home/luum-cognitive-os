# Untracked Work Preservation

## Purpose

Cognitive OS treats untracked files as potentially active human or agent work.
This is especially strict for durable collaboration surfaces:

- `docs/research/**`
- `docs/reports/**`
- `plans/**`
- `.cognitive-os/plans/**`

Those paths are report/research/planning artifacts, not disposable cache. A file
being untracked only means Git has not recorded it yet; it does not prove that it
is safe to delete.

## Runtime contract

The PreToolUse Bash hook `hooks/untracked-work-preservation-guard.sh` blocks
cleanup commands when they target untracked or protected work:

- `rm -r`, `rm -rf`, `rm --recursive`
- `git clean -f`, including `-fd` and `-fdx`
- `find ... -delete`

A delete is allowed only when the operation carries all three pieces of delete
intent metadata:

1. approval: `COS_SAFE_DELETE_APPROVED=1`
2. classification: `COS_DELETE_CLASSIFICATION=generated-cache|temp|duplicate|rejected|operator-approved`
3. reason: `COS_DELETE_REASON='<why this deletion is safe>'`

This makes delete intent explicit and auditable. The hook writes blocks to
`.cognitive-os/metrics/untracked-delete-blocks.jsonl`.

## Safer cleanup primitive

Use `scripts/cos-safe-clean` instead of direct shell deletion:

```bash
scripts/cos-safe-clean --path docs/research/repo-scout --dry-run
```

The dry-run prints a JSON plan showing whether the target exists, whether Git
sees it as untracked, whether it is a protected artifact surface, and whether the
current session owns it.

Execution requires approval metadata:

```bash
scripts/cos-safe-clean \
  --path tmp/rebuildable-cache \
  --execute \
  --approved \
  --classification generated-cache \
  --reason "rebuildable cache from this session"
```

## Cross-session ownership

The classifier checks `.cognitive-os/coordination/artifact-claims.jsonl` as a
best-effort ownership ledger. If a path has no current-session claim, the guard
assumes it may belong to another agent or the operator.

Until `cosd` owns a global artifact ledger, absence of ownership is not a license
to delete. The correct response to unexpected untracked research/report files is:

> I found untracked work at `<path>`. It looks like a research/report artifact.
> Should I preserve it, add it to the commit, or discard it?

## Validation

Primary tests:

```bash
python3 -m pytest tests/unit/test_delete_intent.py -q
python3 -m pytest tests/contracts/test_hook_quality_system.py tests/contracts/test_primitive_runtime_reality.py -q
```
