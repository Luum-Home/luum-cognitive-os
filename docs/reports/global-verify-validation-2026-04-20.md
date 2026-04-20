# global-verify.sh Validation Report — ADR-027 Phase 1
**Date:** 2026-04-20  
**Author:** validation agent (Sonnet 4.6)  
**Scope:** ADR-027 Phase 1 deliverable — `hooks/global-verify.sh`

---

## 1. Registration Status — FAIL (gap found)

### Claim vs Reality

| Item | Commit dacd7dc claim | Current state |
|------|----------------------|---------------|
| `PreToolUse Agent: global-verify.sh before` | Added | **REMOVED** by commit `8e943b7` |
| `PostToolUse Agent: global-verify.sh after` | Added | **REMOVED** by commit `8e943b7` |

### What Happened

Commit `dacd7dc` ("feat(cleanup+fix+verify)") added both hooks to `settings.json`.  
Commit `8e943b7` ("feat(audit): ws9 verified…") regenerated `settings.json` and **replaced** the two `global-verify.sh` entries with other hooks:

- `global-verify.sh before` → replaced by `rate-limit-protection.sh`
- `global-verify.sh after` → replaced by `state-heartbeat.sh` (async)

The substitution was silent — the commit message noted "adr-027-phase-1 unblocked" but the settings diff removed the registrations.

### Current grep evidence

```
grep -n "global-verify" .claude/settings.json  →  (no output)
grep -n "global-verify" scripts/apply-efficiency-profile.sh  →  lines 171, 225, 316, 321
```

`apply-efficiency-profile.sh` still references both invocations (it generates the desired config), but the live `settings.json` does not contain them.

---

## 2. Hook File — EXISTS and CORRECT

`hooks/global-verify.sh` is present and well-formed. Key behaviors:

| Phase | Trigger | Behavior |
|-------|---------|----------|
| `before` | PreToolUse Agent | Calls `get_changed_files()` via `git diff --name-only HEAD`; resolves test targets via `lib.targeted_test_resolver` (if available); writes baseline to `.cognitive-os/runtime/verify-baseline/{agent_id}.json` |
| `after` | PostToolUse Agent | Re-runs the same tests; computes `delta_failed`; emits `MetricEvent` to `verify-events.jsonl`; exits 1 with `BLOCKER` message if regression detected |
| safe-skip | Both phases | Exits 0 with informational message if: pytest absent, resolver unavailable, 0 tests resolved, baseline timeout/error |

The hook is **gracefully degrading** — it never blocks when infrastructure is unavailable.

---

## 3. Targeted Test Resolver — MISSING (gap found)

`lib/targeted_test_resolver.py` does **not exist** in the repository. The file was never committed.

Evidence:
```
ls lib/targeted_test_resolver.py  →  No such file or directory
git log --all --oneline -- lib/targeted_test_resolver.py  →  (empty)
```

A `.pyc` file exists at `lib/__pycache__/targeted_test_resolver.cpython-314.pyc` but this is a **test artifact** — the contract test `test_global_verify.py` uses `_FakeResolver` which writes a temporary `targeted_test_resolver.py` and leaves a compiled cache behind.

**Impact:** Without `targeted_test_resolver.py`, the before-phase always resolves 0 tests and writes a `{skipped: true}` baseline. The after-phase then no-ops on the skipped marker. The hook produces NO meaningful output in normal use.

---

## 4. End-to-End Simulation Results

### Before-phase run

```bash
AGENT_ID=test-adr027 COGNITIVE_OS_PROJECT_DIR=$(pwd) bash hooks/global-verify.sh before
```

Output:
```
[global-verify] before: skipped (0 tests resolved for 1 changed files)
EXIT: 0
```

Baseline file `.cognitive-os/runtime/verify-baseline/test-adr027.json`:
```json
{"skipped": true, "reason": "no tests resolved for changed files", "files": [".claude/plugins/hermes-agent"]}
```

Event emitted to `verify-events.jsonl`:
```json
{"event_type":"verify.baseline.skipped","payload":{"agent_id":"test-adr027","files":[".claude/plugins/hermes-agent"]},"schema_version":1,"severity":"info","source":"global-verify","timestamp":"2026-04-20T16:28:30+00:00"}
```

### After-phase run

Output:
```
[global-verify] after: baseline was skipped (no tests resolved), nothing to compare
EXIT: 0
```

No `verify.after.compared` event emitted (correct skip behavior).

### Root cause: 1 changed file (`.claude/plugins/hermes-agent`), no resolver → 0 tests → skip

---

## 5. Edge Case Tests

| Scenario | Result |
|----------|--------|
| No `AGENT_ID` env var | Uses `unknown-{PID}` — exits 0, writes skip marker |
| Non-project `COGNITIVE_OS_PROJECT_DIR` (e.g., `/tmp`) | git diff returns 0 files → skip, exit 0 |
| pytest not installed | Would exit 0 with "pytest not available — skipping" |

No crashes on any edge case tested.

---

## 6. Contract Tests — ALL PASS

```
pytest tests/contracts/test_global_verify.py -v
4 passed, 1 warning in 1.94s
```

Tests cover:
1. Before-phase writes `skipped` marker when resolver returns no tests
2. Before-phase writes baseline with `passed/failed` when tests resolve (via fake resolver)
3. After-phase exits 0 on no regression
4. After-phase exits 1 with `BLOCKER` message on regression

---

## 7. EXCLUDED_HOOKS.txt Note

`tests/contracts/EXCLUDED_HOOKS.txt` describes `global-verify.sh` as:
> "FUTURE: global verification pass at Stop; planned for Stop event — not yet wired"

This is outdated — the hook was built and registered (then de-registered). The planned event type in this file (`Stop`) also differs from the implemented event type (`PreToolUse/PostToolUse Agent`).

---

## 8. Summary of Gaps

| Gap | Severity | Description |
|-----|----------|-------------|
| Hook de-registered | **BLOCKER** | `settings.json` does not contain `global-verify.sh` — hook never fires in production |
| `targeted_test_resolver.py` missing | **BLOCKER** | Without this module, the hook always resolves 0 tests and skips — no meaningful output is produced |
| `EXCLUDED_HOOKS.txt` stale | S3 suggestion | Entry should reflect current state (built, unregistered) not "FUTURE: planned for Stop" |

---

## 9. Recommended Actions

1. **Re-register the hook** in `.claude/settings.json` — add to `PreToolUse Agent` and `PostToolUse Agent` (use `update-config` skill or manually add entries).
2. **Build `lib/targeted_test_resolver.py`** — a minimal implementation mapping changed file paths to their corresponding test files using naming conventions (e.g., `lib/foo.py` → `tests/unit/test_foo.py`).
3. **Update `EXCLUDED_HOOKS.txt`** to remove the stale entry for `global-verify.sh`.
4. **Add a guard in `settings.json` regeneration scripts** to not silently overwrite custom hook registrations.
