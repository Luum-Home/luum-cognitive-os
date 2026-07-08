---
type: quality-synthesis
source: docs/09-Quality/legal/operator-paths-scrub-report.md
provenance: "L2 pre-public-readiness checklist item: a worktree/temp-path leakage check confirming no ephemeral macOS/agent-worktree paths from the operator's machine are committed to HEAD."
---

## What it is
A dated scrub report (2026-05-07) checking committed files at repo HEAD for leaked ephemeral local paths: macOS temp-directory traces, COS validation capsule paths, per-session agent worktree paths, and task-description worktree paths.

## Key mechanics
- Scope excludes `.git/`, `node_modules/`, `.cognitive-os/`, `tests/`, `docs/01-Build-Log/history/`, `docs/06-Daily/reports/`, and the readiness checklist itself.
- 4 patterns searched: `/private/var/folders/...` (macOS temp), `/tmp/cos-validation-capsules/...`, `.claude/worktrees/agent-[0-9a-f]+`, `.cos-agent-worktrees/luum-agent-os/task-desc-[0-9a-f]+`.
- Two-pass method: broad prefix grep found 3 candidate files, then a follow-up grep for actual specific paths (real folder IDs) returned 0 hits — the 3 prefix hits were confirmed as legitimate code logic (`scripts/cos-registry.sh` and `scripts/cos_init.py` both contain shell/Python pattern-matching literals for detecting ephemeral installs, not real leaked paths) plus the checklist document describing the task itself.
- Result: 0 files scrubbed, 0 replacements applied — no actual leaked operator paths existed in scope.

## Relations & where used
Evidence source for `docs/09-Quality/legal/pre-public-readiness-checklist.md` §L2 ("Worktree / temp-path leakage check"), marked `done` citing this report. Sibling scan to `docs/09-Quality/legal/operator-data-scan.md` (L1, personal-data leakage) under the same pre-public C1/L-series sanitization effort.

## Status / caveats
Dated, point-in-time snapshot (2026-05-07) of one HEAD commit; a clean result here does not guarantee future commits won't reintroduce ephemeral paths — the report itself makes no claim about ongoing prevention beyond the two legitimate code-logic files it names.
