# Consumer Upgrade Note — `lib` → `cos_lib` Package Rename

- **Date:** 2026-07-09
- **Repo:** luum-cognitive-os
- **Change:** SDD `cos-lib-package-rename` — resolves U1 namespace collision.
- **Depends on:** `hook-lib-projection-contract` (merged `6a0971910..7afca9351`).

## What changed

The projected Python package the Cognitive OS ships to consumer installs was
renamed from `lib` to `cos_lib`. All internal `from lib.X import Y` imports and
hook shell-embedded `python3 -m lib.X` invocations were rewritten to `cos_lib.X`
in a single atomic commit.

The rename resolves the risk flagged in
`docs/02-Decisions/designs/hook-lib-projection-contract.md` §7 (U1 — a consumer
with its own top-level `lib/` package silently shadowed the projected COS
`lib/`, degrading governance to a silent no-op via the fail-open backstop).
Post-rename, the shipped package name is namespaced and cannot collide.

## Impact on consumers

**Every consumer install must re-init.**

- The installer is idempotent. Re-running `cos init` for your profile
  overwrites:
  - `.cognitive-os/hooks/cos/**` (projected hooks now source `cos_lib`)
  - `.cognitive-os/hooks/cos/_lib/hook-python-env.sh` (bootstrap)
  - `.cognitive-os/cos_lib/**` (new — the renamed package)
  - `.cognitive-os/lib/**` (old — REMOVED on next init; stale copies are safe
    to delete manually)
- Consumer data (project code, tests, configs) is not touched.

**If a consumer does NOT re-init:**
- Static hook projection is left in place, but the projected hooks now
  reference `cos_lib.X` while `.cognitive-os/cos_lib/` does not exist yet.
- The hook-lib fail-open backstop (from prior SDD) catches this: guard hooks
  exit 0 with a `scan_error_fail_open` metrics row rather than false-blocking.
- Governance is degraded to a silent no-op until re-init — same failure mode
  as the U1 collision the rename fixes, just with a different root cause
  (missing directory vs. name shadow).

## Migration steps

For any consumer project:

```bash
cd <consumer-project-root>
cos init --full   # or --default, per your profile
```

Confirm success:

```bash
python3 -c "import cos_lib.confidentiality_scanner; print('OK')"   # -> OK
test -d .cognitive-os/cos_lib                                        # -> 0
test ! -d .cognitive-os/lib                                          # -> 0
```

If you have hand-authored consumer scripts that `from lib.X import Y` from a
COS module directly (rare), rewrite to `from cos_lib.X import Y`. The rename
is boundary-anchored (negative lookbehind rejects `_lib` suffixes) so no
`workflows/lib.*` or unrelated `_lib` references are affected.

## Rollback

Should the rename need to be undone in a consumer, either:

1. Re-init from a prior COS release tag (`cos update --pin v0.29.36`), or
2. Symlink the stale copy: `ln -s cos_lib .cognitive-os/lib` — a compatibility
   shim that bridges the transition period. Expedient, not clean; prefer re-init.

## Reference

- Proposal: `docs/02-Decisions/proposals/cos-lib-package-rename.md` (`f2306b08`)
- Design: `docs/02-Decisions/designs/cos-lib-package-rename.md` (`20c01e3d` +
  addendum `f8ae08c7` for the 2-phase codemod recipe)
- Dry-run manifest: `docs/06-Daily/reports/cos-lib-rename-dryrun-2026-07-08.md`
- Codemod: `scripts/cos_lib_rename_codemod.py` (order-independent
  `load_allowlist`, `--prose-sweep` flag)
- Prior SDD context: `docs/02-Decisions/designs/hook-lib-projection-contract.md` §7
