# Snapshot Chaos Runbook

**Version**: 1.0  
**ADR**: ADR-099  
**Date**: 2026-04-30

This runbook provides reproducible chaos scenarios for `pre-agent-snapshot.sh` (ADR-099).
Each scenario has a corresponding script in `scripts/chaos/` that can be run by the operator.

---

## Scenarios

### Scenario 1: Vanishing Untracked Files

**Script**: `scripts/chaos/snapshot-vanishing-untracked.sh`

**What it tests**: The original bug (ADR-099 context). With `COS_LEGACY_SNAPSHOT=1`,
untracked files vanish from the WT after an agent launch. Without the env var (default),
files survive.

**How to run**:
```bash
bash scripts/chaos/snapshot-vanishing-untracked.sh
```

**Interpreting results**:
- `[PASS] [A] Legacy mode: file vanished` — old bug reproduced as expected under legacy mode.
- `[PASS] [B] New mode: file survived in WT` — ADR-099 fix is working.
- `[PASS] [B] Backup copy exists in snapshot dir` — backup was created.
- `[FAIL]` on scenario B — the fix has regressed; check `lib/snapshot_manager.py` and the hook.

**What to do on FAIL**:
1. Check if `python3` is available (`which python3`).
2. Run `python3 -c "from lib.snapshot_manager import create_snapshot; print('ok')"` from project root.
3. Inspect hook output: `bash hooks/pre-agent-snapshot.sh <<< '{"tool_name":"Agent","tool_input":{}}' 2>&1`.

---

### Scenario 2: Concurrent Race

**Script**: `scripts/chaos/snapshot-concurrent-race.sh`

**What it tests**: Three parallel invocations of `pre-agent-snapshot.sh` against the same
repo. No files should be lost. Snapshot IDs must be unique (timestamp + PID suffix).

**How to run**:
```bash
bash scripts/chaos/snapshot-concurrent-race.sh
```

**Interpreting results**:
- `[PASS] concurrent-N.py survived in WT` — no files ghosted by concurrent snapshots.
- `[PASS] At least one snapshot directory created` — snapshot dirs written.
- `[FAIL] concurrent-N.py was removed from WT!` — collision or race condition; check PID suffix in snapshot IDs.
- `[FAIL] No snapshot directories created` — Python invocation failed; check PYTHONPATH.

**What to do on FAIL**:
1. Check `.cognitive-os/snapshots/` for partial directories.
2. Verify snapshot IDs contain PID: `ls .cognitive-os/snapshots/`.
3. Look for manifest JSON parse errors.

---

### Scenario 3: Crash + Rollback

**Script**: `scripts/chaos/snapshot-crash-rollback.sh`

**What it tests**: Full crash-recovery cycle:
1. Create pre-agent state (untracked + staged-tracked file).
2. Take snapshot.
3. Corrupt both files (simulate agent crash).
4. Restore via `lib/snapshot_manager.restore_snapshot()`.
5. Assert pre-snapshot content restored.

**How to run**:
```bash
bash scripts/chaos/snapshot-crash-rollback.sh
```

**Interpreting results**:
- `[PASS] precious.py restored correctly` — untracked file backup restored from snapshot dir.
- `[PASS] tracked.txt restored correctly from stash` — stash apply worked.
- `[WARN] tracked.txt content: '...'` — stash apply may have conflicted; resolve manually.
- `[FAIL]` on any step — see `lib/snapshot_manager.restore_snapshot()`.

**What to do on FAIL**:
1. Inspect the manifest: `cat .cognitive-os/snapshots/<snap-id>/manifest.json`.
2. Verify backup copy exists: `ls .cognitive-os/snapshots/<snap-id>/`.
3. Manually restore: `python3 -c "from lib.snapshot_manager import restore_snapshot; from pathlib import Path; print(restore_snapshot(Path('.'), '<snap-id>'))"`.

---

## Legacy stash recovery (pre-ADR-099)

The 9 legacy stashes accumulated before this fix can be inspected:

```bash
# List all legacy stashes
git stash list | grep -E '(cos-|auto-pre-agent-)'

# Inspect a specific stash
git stash show -p "stash@{N}"

# Restore a specific file
git checkout "stash@{N}" -- path/to/file.py

# Apply entire stash (may conflict)
git stash apply "stash@{N}"

# Drop after recovery
git stash drop "stash@{N}"
```

The recovery stash from the 2026-04-30 incident: `stash@{1}: cos-20260430-165827`.

---

## Pruning snapshots

```bash
# Dry-run: see what would be deleted
bash scripts/cleanup-snapshots.sh --dry-run

# Prune snapshots older than 30 days (default from cognitive-os.yaml)
bash scripts/cleanup-snapshots.sh

# Prune with custom TTL
bash scripts/cleanup-snapshots.sh --ttl-days 7
```

---

## Running the automated test suite

```bash
# Unit tests (pure Python, no shell)
python3 -m pytest tests/unit/test_snapshot_manager.py -v

# Integration tests (invoke real hooks)
python3 -m pytest tests/integration/test_pre_agent_snapshot_border_cases.py -v

# All snapshot tests
python3 -m pytest tests/unit/test_snapshot_manager.py tests/integration/test_pre_agent_snapshot_border_cases.py -v
```

All 9 unit tests and 9 integration tests should pass. A FAIL indicates a regression in
`lib/snapshot_manager.py` or `hooks/pre-agent-snapshot.sh`.
