# Sprint 3 — Physical Vault Rename Plan

**Status**: PLANNED, not yet started.
**Author**: orchestrator session 2026-05-12.
**Resumable from**: any new session by reading this file + `docs/06-Daily/reports/docs-organization-research-2026-05-12.md` + `docs/06-Daily/reports/docs-restructure-impact-2026-05-12.md`.

## Why this exists

Sprint 1 (navigation layer) and Sprint 2 (MOCs at `docs/00-MOCs/`) delivered an intent-based navigation overlay without touching disk. The operator's original ask was a **literal Karpathy/Obsidian vault-numbered rename**: physical `00-MOCs/`, `01-Build-Log/`, `02-Decisions/`, etc. Sprint 3 is that physical rename.

It was deferred multiple times because the impact report ([docs/06-Daily/reports/docs-restructure-impact-2026-05-12.md](docs-restructure-impact-2026-05-12.md)) showed **197 code callers + 151 `.cognitive-os/docs/` symlinks** at risk. Sprint 3 should only run when there is operator commitment to the 3–6h migration window AND coordination with any other active flows in `docs/`.

## Schema (final mapping)

| New prefix | Absorbs from current tree | Risk | Notes |
|---|---|---|---|
| `00-MOCs/` | already exists (Sprint 2) | 0 | Curated entrypoints. Stays. |
| `01-Build-Log/` | `docs/SESSION-HANDOFF-*.md` (root) + `docs/01-Build-Log/history/` | low | Cronological session changelogs. |
| `02-Decisions/` | `docs/02-Decisions/adrs/` | **CRITICAL** | ~80 string-literal callers across hooks, lib, tests, scripts. |
| `03-PoCs/` | `docs/03-PoCs/proposals/` + `docs/03-PoCs/research/` | medium | Both contain WIP-style content. |
| `04-Concepts/` | `docs/04-Concepts/architecture/` + `docs/04-Concepts/patterns/` + `docs/04-Concepts/architecture-principles.md` + `docs/04-Concepts/architecture.md` | high | Many ADRs cite these paths. |
| `05-Methodology/` | `docs/05-Methodology/runbooks/` + `docs/05-Methodology/guides/` + `docs/05-Methodology/usage/` + `docs/05-Methodology/setup/` + `docs/05-Methodology/onboarding/` + `docs/05-Methodology/getting-started/` | medium | Process docs. |
| `06-Daily/` | `docs/06-Daily/reports/` + `docs/06-Daily/incidents/` + `docs/06-Daily/measurements/` | **CRITICAL** | ~65 callers (`research-quality-validator.sh`, `skill-post-execution-analysis.sh`, etc.). |
| `07-Capabilities/` | `docs/07-Capabilities/capabilities/` + `docs/07-Capabilities/acc/` + `docs/07-Capabilities/skills/` | medium | `docs/07-Capabilities/acc/latest.json` consumed by tooling. |
| `08-References/` | `docs/08-References/integrations/` + `docs/08-References/migration-from/` + `docs/08-References/benchmarks/` + `docs/08-References/case-studies/` | low | External-system references. |
| `09-Quality/` | `docs/09-Quality/quality/` + `docs/09-Quality/testing/` + `docs/09-Quality/security/` + `docs/09-Quality/manual-tests/` + `docs/09-Quality/legal/` | medium | Test/audit/legal material. |
| `99-Archive/` | `docs/99-Archive/archive/` | low | Historical-only. |

Stays at root (do not move):
- `docs/00-MOCs/entrypoints/INDEX.md`, `docs/00-MOCs/entrypoints/AGENTS.md`, `docs/00-MOCs/entrypoints/README.md`, `docs/00-MOCs/entrypoints/HOW-TO-USE-COS.md`
- Individual root-level `.md` files: case-by-case during Phase 1.

## Strategy: symlink-bridge in 4 phases

Big-bang is forbidden — `hooks/session-startup-protocol.sh:87` reads `ADRS_DIR="$PROJECT_DIR/docs/02-Decisions/adrs"` on every session start; if that path is gone before callers update, the session breaks.

### Phase 1 — Create new directories + git mv

For each row in the schema:
1. `mkdir -p docs/<new-prefix>`
2. For each source path under the row, `git mv <old> <new>` preserving history. Use `git mv -k` to tolerate missing files in concurrent flows.
3. After each `git mv`, commit with scope `git commit --only -- <new-path> <old-path>` (ADR-089 enforced).

Estimated duration: **~30 min** mechanical.

Checkpoint after Phase 1: `git status` clean, all `docs/<old>` directories gone, all `docs/<new-prefix>/...` files present with history preserved.

### Phase 2 — Create symlink bridges

For each row in the schema:
1. `ln -s <new-prefix> docs/<old-name>` (relative symlink)

Example: `cd docs && ln -s 02-Decisions adrs`. After this, all 197 callers referencing `docs/02-Decisions/adrs/...` resolve transparently through the symlink.

Also update `.cognitive-os/docs/` symlinks:
- For each of the 151 symlinks under `.cognitive-os/docs/`, verify it still resolves. If pointing at a renamed dir, update to point at the new prefix directly (avoid double-hop through bridge).

Estimated duration: **~20 min**.

Checkpoint: `find . -xtype l -not -path './.git/*' -not -path './.venv/*' -not -path './reference/*'` returns empty.

### Phase 3 — Code surgery (CRITICAL callers)

Update the 5 most fragile string-literal callers identified in the impact report:

1. **`lib/adr_detector.py:68`** — `ADR_PATH_PATTERN = re.compile(r"^docs/02-Decisions/adrs/")` → `re.compile(r"^docs/02-Decisions/")`
2. **`hooks/session-startup-protocol.sh:87`** — `ADRS_DIR="$PROJECT_DIR/docs/02-Decisions/adrs"` → `ADRS_DIR="$PROJECT_DIR/docs/02-Decisions"` (PROTECTED — needs `COS_ALLOW_PROTECTED_CONFIG_WRITE=1`)
3. **`hooks/adr-detector.sh:67`** — `grep -v '^docs/02-Decisions/adrs/'` → `grep -v '^docs/02-Decisions/'` (PROTECTED + portability test must be updated)
4. **`hooks/research-quality-validator.sh`** + **`hooks/skill-post-execution-analysis.sh`** — `docs/06-Daily/reports/` → `docs/06-Daily/reports/` (PROTECTED)
5. **`cmd/cos/internal/cli/release.go:350`** — `filepath.Join(projectRoot, "docs", "INDEX.md")` stays (root file does not move)
6. **`lib/self_improvement_loop.py`** — bulk-update path literals.
7. **`scripts/audit_adrs.py`** — `ADR_DIRS` list.
8. **`scripts/generate_adr_index.py`** — output path.

Run after each: `pytest tests/audit/test_adr_locations.py tests/red_team/portability/adr-detector_test.py -x` + `bash -n hooks/adr-detector.sh hooks/session-startup-protocol.sh`.

Update the portability test (`tests/red_team/portability/adr-detector_test.py`) to assert the new pattern.

Estimated duration: **~1–2 h** (each gate-protected hook requires bypass + careful test).

### Phase 4 — Bulk reference sweep + bridge removal

1. `grep -rln "docs/02-Decisions/adrs\|docs/06-Daily/reports\|docs/05-Methodology/runbooks\|docs/04-Concepts/architecture\|docs/07-Capabilities/skills\|docs/07-Capabilities/capabilities\|docs/03-PoCs/research\|docs/06-Daily/incidents\|docs/06-Daily/measurements\|docs/08-References/integrations\|docs/08-References/migration-from\|docs/09-Quality/quality\|docs/09-Quality/testing\|docs/09-Quality/security\|docs/09-Quality/legal\|docs/09-Quality/manual-tests\|docs/03-PoCs/proposals\|docs/08-References/benchmarks\|docs/08-References/case-studies\|docs/05-Methodology/usage\|docs/05-Methodology/setup\|docs/05-Methodology/onboarding\|docs/05-Methodology/getting-started\|docs/05-Methodology/guides\|docs/01-Build-Log/history\|docs/04-Concepts/patterns\|docs/07-Capabilities/acc\|docs/99-Archive/archive" --include="*.py" --include="*.sh" --include="*.go" --include="*.md" --include="*.yaml" --include="*.yml" --include="*.json" .`
2. Filter out legitimate-history matches (Sprint 1 reports, ADR-087, archive/, etc.).
3. Update remaining matches by lots: tests/audit, tests/contracts, tests/unit (~111 Python files); rules/*.md (~25); scripts (~22).
4. After full sweep passes, remove the 11 symlink bridges: `rm docs/02-Decisions/adrs docs/06-Daily/reports docs/05-Methodology/runbooks ...`
5. Final smoke: `bash hooks/session-startup-protocol.sh` (no errors), `pytest tests/audit/ tests/red_team/portability/ tests/contracts/test_docs_archive_path_drift.py -x`.

Estimated duration: **~2–3 h**.

## Gates that will block (and how)

| Gate | When fires | Bypass |
|---|---|---|
| `protected-config-write-guard.sh` | Editing `hooks/adr-detector.sh`, `hooks/session-startup-protocol.sh`, etc. | `COS_ALLOW_PROTECTED_CONFIG_WRITE=1` env var on the edit-issuing command |
| `scope-marker-portability-gate.sh` | Committing a `SCOPE: both` artifact without paired test | Update paired portability test in same commit |
| `git-commit-scope-guard.sh` | `git commit` without explicit scope | Use `git commit --only -- <paths>` |
| Concurrent flow conflicts | Other session edits `docs/02-Decisions/adrs/` while migration is mid-flight | **Coordinate pause before Phase 1**; if conflict detected mid-flight, `git stash` other-flow edits with named label and apply after migration |

## Rollback plan

Each phase commits independently. To rollback:

- **Phase 1**: `git revert <commit>` for each `git mv` commit. History is preserved so the revert puts files back where they were.
- **Phase 2**: `rm` the symlink bridges (they are not tracked; bridges exist only in working tree). Phase 1 commits remain.
- **Phase 3**: `git revert` per code-surgery commit.
- **Phase 4**: Re-create the symlink bridges by hand and `git revert` the sweep commit(s).

## Resumability

A new session picking this up should:

1. Read this file in full.
2. Read `docs/06-Daily/reports/docs-restructure-impact-2026-05-12.md` for the original 197-caller list.
3. Read `docs/06-Daily/reports/docs-organization-research-2026-05-12.md` for the Karpathy/Diátaxis context.
4. Check `git log --oneline -20` for which phases already committed (look for `feat(vault-rename)/phase-N` prefixes).
5. Check `find docs -maxdepth 1 -type d -name "[0-9][0-9]-*"` to see which new prefix dirs exist.
6. Resume from the next pending phase.

Engram topic key (when run): `sprint-3-physical-rename/state` — orchestrator must save after each phase transition.

## Sequence to recommend on resume

Operator's original framing on 2026-05-12:

> Operator framing: start with Phase 1+2 only in the low-cost directories (`08-References/`, `99-Archive/`, `03-PoCs/`) that have few callers. If that is clean, escalate; if it breaks, contain the blast radius.

### Real per-directory caller counts (re-measured 2026-05-12)

The original impact report aggregated subpath mentions and undercounted. Actual non-doc string-literal callers per dir:

| Source dir | Non-doc callers | Risk | Notes |
|---|---|---|---|
| `docs/08-References/benchmarks/` | 4 | low | **recommended first target** |
| `docs/08-References/case-studies/` | 5 | low | second target |
| `docs/08-References/integrations/` | 4 | low | |
| `docs/08-References/migration-from/` | 7 | low-medium | |
| `docs/03-PoCs/proposals/` | 7 | medium | |
| `docs/99-Archive/archive/` | 5+ + **drift-guard test** | medium-high | see BLOCKER below |
| `docs/03-PoCs/research/` | 37 | high | not first-batch material despite "low-risk" framing |

### BLOCKER: docs/99-Archive/archive/ drift guard

Commit `d50a34f9` (other flow, 2026-05-12) created `tests/contracts/test_docs_archive_path_drift.py` which asserts:

```python
assert "docs/99-Archive/archive/" in (REPO_ROOT / "docs" / "AGENTS.md").read_text()
assert '"docs/99-Archive/archive/"' in (REPO_ROOT / "scripts" / "docs_execution_audit.py").read_text()
```

The test **explicitly defends the `docs/99-Archive/archive/` naming**. Renaming requires:
1. Operator authorization to override the drift contract
2. Updating the test to assert the new path
3. Updating `scripts/docs_execution_audit.py` (filters paths from the docs audit)
4. Updating `tests/contracts/test_orchestrator_verify.py`, `tests/red_team/scenarios/archive-presence-fallacy.yaml`, `tests/audit/test_plan_locations.py`, and `docs/00-MOCs/entrypoints/AGENTS.md`

**Default action on resume**: skip `docs/99-Archive/archive/` until operator decides; rename it LAST in its category.

### Revised execution order (operator must reconfirm on resume)

Phase-1+2 starting tier (mechanical, ~4-7 callers each):

1. **`docs/08-References/benchmarks/`** → `docs/08-References/benchmarks/` ← **start here**
2. **`docs/08-References/case-studies/`** → `docs/08-References/case-studies/`
3. **`docs/08-References/integrations/`** → `docs/08-References/integrations/`
4. **`docs/08-References/migration-from/`** → `docs/08-References/migration-from/`

Verify after each: tests pass, session-startup hook runs clean, drift-guards (if any new ones appear) still green.

Medium-risk tier (after verifying tier 1):

5. **`docs/03-PoCs/proposals/`** → `docs/03-PoCs/proposals/`
6. **`docs/99-Archive/archive/`** → `docs/99-Archive/` *(only after drift-guard decision)*

High-risk tier (after verifying tier 2):

7. **`docs/03-PoCs/research/`** → `docs/03-PoCs/research/` (37 callers — needs explicit batch with test re-run between each)

Then medium tier (05-Methodology/, 07-Capabilities/, 09-Quality/) and finally CRITICAL tier (02-Decisions/, 06-Daily/, 04-Concepts/, 01-Build-Log/).

### Why a new session should reconfirm

This plan documents the pre-execution state. By the time a new session resumes:
- The other flow may have added more drift-guard tests
- The caller counts may have changed
- The schema decisions documented above may need re-validation against current `docs/` state

Re-run the caller scan as the first action on resume:

```bash
for d in benchmarks case-studies integrations migration-from proposals archive research; do
  refs=$(grep -rln "docs/$d/" --include="*.py" --include="*.sh" --include="*.go" \
    --include="*.yaml" --include="*.yml" --include="*.json" . 2>/dev/null \
    | grep -v ".git/" | grep -v ".venv/" | grep -v "/reference/" \
    | grep -v "^./docs/" | wc -l | tr -d ' ')
  echo "docs/$d/: $refs non-doc callers"
done
```

If counts have shifted, re-tier the order before execution.

## Blockers / prerequisites before start

- [ ] Operator confirms 3–6h window
- [ ] Verify no other flow has uncommitted edits in `docs/` (`git status --short docs/`)
- [ ] If other flow is active, coordinate explicit pause
- [ ] Check `git worktree list` — purge any orphan worktrees first
- [ ] Snapshot current state: `git tag pre-sprint-3-rename` for clean rollback anchor

Done.
