# Full Git Stash Recovery Archive — 2026-05-15

This archive preserves every changed/untracked file version extracted from the 37 local `git stash` entries present during recovery.

- Archive: `stash-recovery-2026-05-15-full.tar.gz`
- SHA-256: `3f690f1b38a1ec355ebb32665a8d25198db1ca4dd7c39adb8c79b24a75dae228`
- Stashes exported: 37
- Tracked records: 367
- Untracked records: 635
- Unique file versions: 264
- Paths that were absent in the worktree and restored into the archive's original-path inventory: 95

To inspect locally:

```bash
tar -tzf docs/06-Daily/reports/stash-recovery-2026-05-15-full.tar.gz | head
mkdir -p /tmp/cos-stash-recovery
tar -xzf docs/06-Daily/reports/stash-recovery-2026-05-15-full.tar.gz -C /tmp/cos-stash-recovery
jq '.stashes[] | {label, ref, hash, tracked: (.tracked|length), untracked: (.untracked|length)}' /tmp/cos-stash-recovery/stash-recovery-2026-05-15-full/manifest.json
```

The archive intentionally preserves raw recovered stash contents. Do not treat its embedded historical reports as current product truth; use them as recovery evidence only.
