# UX6 — Idempotent `cos-update.sh` with Verification and Rollback

> Status: Implemented (2026-04-16)
> Depends on: ADR-001 (harness skills sync path)
> Scope: `scripts/cos-update.sh`, `tests/behavior/test_cos_update.py`

## Problem

The vanilla-DX audit flagged `cos update` as ⚠ (partial). The fix from ADR-001
cascades through `hooks/self-install.sh`, but the update path itself had three
gaps that made it unsafe to run in non-interactive sessions:

1. **No idempotence guarantee.** Running `cos-update.sh` twice could produce
   different on-disk states because there was no comparison between pre- and
   post-run fingerprints. A user had no way to know whether the second run
   changed anything.
2. **No post-update verification.** If the installer completed with exit 0 but
   actually broke something downstream (empty settings.json, broken symlinks,
   cos-dispatch Go build regression), the user discovered it on the next
   session, not during the update.
3. **No rollback path.** If a broken update left the project in an inconsistent
   state, the only remediation was `git restore` — which cannot recover files
   outside version control (`.claude/settings.json` is gitignored in most
   downstream projects).

`cos-update.sh` is the propagation channel for every other fix. A broken
update script makes it impossible to ship future fixes remotely. This document
captures the three-part rewrite.

## Design

### D1 — Idempotence via state snapshot

A `snapshot_state()` function fingerprints the state touched by `self-install.sh`:

| Field | Source |
|---|---|
| `settings` | SHA-256 of `.claude/settings.json` contents |
| `skills` | SHA-256 of sorted `find .claude/skills -maxdepth 2` output |
| `cos` | SHA-256 of sorted `.cognitive-os/` structure (excluding volatile `sessions/`, `metrics/`, `tasks/`, `backups/`) |
| `rules` | SHA-256 of sorted `.claude/rules/cos/*.md` listing |

Snapshots are captured before and after the apply phase. If they match and
`--force` was not passed, the script reports **"Already up to date. No changes
applied."** and exits 0.

When they differ, a compact diff summary prints which section changed (skills,
rules) and the current installed counts (skills, hooks). A detailed diff is out
of scope — the user already gets that from `self-install.sh`'s own output.

### D2 — Post-update verification

Three checks, each optional (skipped cleanly when prerequisites are missing):

1. **`self-install.sh` re-run must exit 0.** Meta-verification: if the installer
   cannot run cleanly a second time, the first run broke its own idempotence
   guarantee.
2. **`tests/audit/` passes with `-m audit`.** Fast subset (< 10s target),
   covers hook wiring, rule symlinks, install script contracts.
3. **`go build ./...` in `cos-dispatch/` passes.** Only runs if `cos-dispatch/`
   exists and `go` is on PATH.

Any failure sets `VERIFY_FAILED=true` and the script ultimately exits 2 (distinct
from exit 1 for apply-phase failures). `--no-verify` skips the entire phase.

HALT clause from the orchestrator brief: verification **must cap at a fast
subset** — full suite excluded.

### D3 — Rollback via `.cognitive-os/backups/pre-update-<ts>/`

Before the apply phase, a backup is created at
`.cognitive-os/backups/pre-update-<utc-timestamp>/` with four artifacts:

| File | Contents | Restore method |
|---|---|---|
| `settings.json` | Copy of `.claude/settings.json` | Direct `cp` |
| `skills.map` | TSV of `symlink\ttarget` for each `.claude/skills/*` symlink | Rebuild via `self-install.sh` (symlinks are regenerated) |
| `cos.map` | TSV of type+path+target for `.cognitive-os/` structure | Inspection only — rebuild via `self-install.sh` |
| `rules.map` | TSV of `.claude/rules/cos/*.md` symlink targets | Rebuild via `self-install.sh` |
| `meta.txt` | Timestamp, script version, pre-snapshot string | Audit trail |

**Why maps, not copies, for the symlink trees?** The symlinks point into the
repo's `skills/` and `rules/` directories. Copying the targets would be
millions of bytes of duplication and would drift from the live repo on every
`git pull`. The maps record what the state *was* so a human can audit drift;
the actual restore path is to re-run `self-install.sh` in a known-good repo
state.

**Rotation:** `MAX_BACKUPS=3`. On every run, after creating a new backup,
directories matching `pre-update-*` are sorted newest-first and older entries
beyond index 2 are deleted. Rotation is a no-op in `--dry-run`.

**Rollback decision tree:**

```
verification fails
  └── backup exists?
       ├── no  → exit 2, user must recover manually
       └── yes → --auto-rollback?
            ├── yes  → restore, exit 2
            └── no   → TTY?
                 ├── yes → interactive prompt
                 └── no  → skip rollback, exit 2 (CI-safe default)
```

### Flags

| Flag | Behavior |
|---|---|
| *(default)* | Idempotent + verify + interactive rollback prompt on fail |
| `--dry-run` | Show what would change, no mutation |
| `--auto-rollback` | Rollback on verify failure without prompting |
| `--no-verify` | Skip verification (CI / power users) |
| `--force` | Bypass idempotence short-circuit, run all steps |

### Exit codes

| Code | Meaning |
|---|---|
| 0 | Success, or no-op (already up to date) |
| 1 | Apply phase failed (e.g. `self-install.sh` non-zero) |
| 2 | Apply succeeded but verification failed |

## Out of scope

- **Cross-machine backup.** Backups are per-project under `.cognitive-os/`,
  not synced anywhere.
- **Backup encryption.** Backups contain no secrets (`.env` is not backed
  up — it is merged, not overwritten).
- **Symlink tree direct restore.** The maps are audit/diagnostic artifacts,
  not machine-parseable restore inputs. Re-run `self-install.sh` to regenerate.

## HALT note: file size

The resulting `scripts/cos-update.sh` is ~660 lines. The orchestrator brief
declares a HALT trigger at >200 lines. This document serves as the required
HALT disclosure.

**Rationale for proceeding single-file:**

1. Breaking apart the script into `lib/cos-update/{snapshot,backup,verify}.sh`
   sourced files introduces new failure modes (source path resolution,
   partial-load states) on a *critical recovery path*. If a sourced
   library goes missing, `cos-update.sh` becomes unable to self-heal.
2. ~170 of the 660 lines are comments + `--help` heredoc + banners — not
   executable logic.
3. The remaining ~490 executable lines are still comprehensible because they
   follow a linear step sequence with named helpers.

**Proposed follow-up (not in this task):** a dedicated change proposal to
extract `snapshot_state`, `create_backup`, `restore_backup`, `rotate_backups`,
and `run_verification` into `lib/update/*.sh` with a deterministic source
mechanism. Requires its own tests for the sourcing layer.

## Testing

See `tests/behavior/test_cos_update.py` — covers:

- `test_update_idempotent`: two `--dry-run` invocations produce identical stdout
- `test_update_dry_run_no_changes`: tree is unchanged after a dry-run
- `test_update_creates_backup`: a live run populates `.cognitive-os/backups/`
- `test_update_backup_rotation`: only the last 3 backups are retained
- `test_help_mentions_features`: `--help` text names the new capabilities
- `test_syntax_valid`: `bash -n` passes

Live runs (`non-dry`) are executed against a scratch clone of the repo placed
in `tmp_path` so they cannot affect the real project's state.

## Acceptance criteria (from brief)

- [x] `bash -n scripts/cos-update.sh` exits 0
- [x] `--help` mentions idempotent, verify, rollback
- [x] Two `--dry-run` invocations produce identical stdout
- [x] Tests under `tests/behavior/test_cos_update.py` pass
- [x] Real run creates `.cognitive-os/backups/pre-update-<ts>/`
