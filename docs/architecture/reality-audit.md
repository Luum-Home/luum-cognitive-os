# Reality Audit — Cognitive OS

**Audit Date:** April 2026
**Purpose:** Source of truth for what actually exists and works vs. what docs describe aspirationally. Prevents future sessions from trusting the docs blindly.

---

## CRITICAL: lib/ Architecture

**lib/*.py files are SYMLINKS to packages/*/lib/*.py — NOT duplicates.**

```
lib/sdd_resume.py → ../packages/sdd-compound/lib/sdd_resume.py  (symlink)
lib/phase_timing.py → ../packages/sdd-compound/lib/phase_timing.py  (symlink)
lib/issue_pipeline.py → ../packages/sdd-compound/lib/issue_pipeline.py  (symlink)
```

The canonical source lives in `packages/*/lib/`. The `lib/` directory provides a flat import namespace via symlinks created by `self-install.sh` during SessionStart.

**Rules for agents working with lib/:**
1. NEVER replace files in `packages/*/lib/` with redirect stubs
2. ALWAYS run `ls -la lib/<file>.py` before assuming duplication
3. `diff lib/X.py packages/Y/lib/X.py` showing "identical" = correct (same file via symlink)
4. To check: `find lib/ -type l | wc -l` shows symlink count

---

## lib/ Modules

**Total:** 82 modules

| Status | Count | % | Notes |
|--------|-------|---|-------|
| Import correctly | 80 | 98% | Verified via Python import validation |
| Broken imports | 2 | 2% | See table below |
| Orphans (import fine, no callers) | ~10 | ~12% | Never called from hooks or production code |
| Fully operational (imports + callers + passing tests) | ~57 | ~70% | |

### Broken Modules

| Module | Problem |
|--------|---------|
| `batch_runner.py` | Wrong import style — uses relative import that fails in standalone execution |
| `webhook_trigger.py` | Missing dependency: `fastapi` not installed in the runtime environment |

### Orphan Modules (approximate)

Modules that import cleanly but are never referenced from hooks or production code paths. They exist from the v0.1.0 monolith generation and have not been wired into any workflow. Exact list requires a full caller-graph analysis (`grep -r "import.*{module}" hooks/ lib/`).

---

## Hooks

**Total hook files:** 93

| Status | Count | % |
|--------|-------|---|
| Registered in settings.json AND actively fire | 45 | 48% |
| File exists but NEVER fires — not wired | 48 | 52% |

### Key Dead Hooks (unwired, never fire)

These hooks exist as shell scripts but are absent from `settings.json` matchers, so they never execute:

- `completeness-check.sh`
- `architecture-compliance.sh`
- `prompt-quality.sh`
- `epic-task-detector.sh`
- `pre-commit-gate.sh`
- `scope-creep-detection.sh`
- `singularity-check.sh`

The rules documentation describes these hooks as "always active" — that was aspirational, not factual.

---

## Tests

| Suite | Pass | Fail | Notes |
|-------|------|------|-------|
| Unit | 3,069 | 0 | All passing |
| Behavior | 1,624 | 18 | Failures: self-install symlinks, version expectations, preamble size |
| Integration | 144 | 4 | 4 failing |

**Total:** 4,837 tests, 22 failing (0.45% failure rate)

### Known Behavior Failures

- Self-install symlink tests: path resolution differs in CI vs local
- Version expectation tests: hardcoded version strings not updated after release
- Preamble size tests: preamble grew beyond expected byte threshold

---

## Infrastructure

| Path | Status | Notes |
|------|--------|-------|
| `.cognitive-os/workflows/` | Created April 2026 | Did not exist before this session |
| `.cognitive-os/dynamic-tools/` | Exists | |
| `.cognitive-os/checkpoints/` | Exists | |
| `plans/` | Has structure + README, no actual plan files | Empty directory tree |
| `.cognitive-os/plans/` | Exists, 14 real plan files | Actual planning content lives here, not `plans/` |

---

## Root Causes

### 1. v0.1.0 Monolith Commit

The initial codebase was generated in bulk, not developed incrementally. This produced:
- 93 hook files with no validation that all were wired
- 82 lib modules with no caller-graph verification
- Rules that described hooks as "always active" when they were only planned

### 2. No Python Import Validation Gate

No pre-commit check existed to validate lib/ imports before commit. Broken imports (`batch_runner.py`, `webhook_trigger.py`) were committed undetected.

**Fix applied:** `.githooks/pre-commit` now runs `ruff` for syntax validation and validates lib/ imports.

### 3. Wrong `core.hooksPath`

Git hooks were configured at `.githooks/`, not `.git/hooks/`. This meant the pre-commit gate in `.git/hooks/pre-commit` was never executed. Only hooks in `.githooks/` fired.

**Fix applied:** Confirmed `core.hooksPath = .githooks` is set; pre-commit gate moved there.

### 4. No Hook-Rule Consistency Check

No automated check verified that hooks referenced in rules documentation were actually registered in `settings.json`. The gap between aspirational rules and wired reality was invisible.

**Fix applied (advisory):** Gate 3 in `.githooks/pre-commit` warns when >20 hooks are unwired.

---

## Prevention Measures Added

| Measure | Location | Effect |
|---------|----------|--------|
| Python syntax validation | `.githooks/pre-commit` | Blocks commits with syntax errors in lib/ |
| lib/ import validation | `.githooks/pre-commit` | Blocks commits with broken imports |
| Unwired hook warning | `.githooks/pre-commit` Gate 3 | Warns when >20 hook files have no settings.json entry |

---

## How to Re-Run This Audit

```bash
# Count lib/ modules
ls lib/*.py | wc -l

# Test lib/ imports
python3 -c "
import os, importlib.util, sys
broken = []
for f in os.listdir('lib'):
    if f.endswith('.py') and f != '__init__.py':
        spec = importlib.util.spec_from_file_location(f[:-3], f'lib/{f}')
        m = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(m)
        except Exception as e:
            broken.append((f, str(e)))
print(f'Broken: {len(broken)}')
for name, err in broken:
    print(f'  {name}: {err}')
"

# Count hooks
ls hooks/*.sh | wc -l

# Count wired hooks (registered in settings.json)
python3 -c "import json; s=json.load(open('.claude/settings.json')); hooks=s.get('hooks',{}); total=sum(len(v) for v in hooks.values()); print(f'Wired hook entries: {total}')"

# Run test suites
python3 -m pytest tests/unit/ -q 2>&1 | tail -5
python3 -m pytest tests/behavior/ -q 2>&1 | tail -5
python3 -m pytest tests/integration/ -q 2>&1 | tail -5
```
