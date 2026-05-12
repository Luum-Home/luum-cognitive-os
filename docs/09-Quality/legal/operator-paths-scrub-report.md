# Operator Paths Scrub Report

**Date:** 2026-05-07
**Task:** L2 — Worktree / temp-path leakage check (pre-public-readiness-checklist.md)
**Scope:** Committed files in repo HEAD, excluding `.git/`, `node_modules/`, `.cognitive-os/`,
`tests/`, `docs/history/`, `docs/reports/`, `docs/legal/pre-public-readiness-checklist.md`.

---

## Patterns Searched

| Pattern | Description |
|---------|-------------|
| `/private/var/folders/[^/]+/[^/]+/...` | macOS temp directory traces |
| `/tmp/cos-validation-capsules/...` | COS validation capsule paths |
| `.claude/worktrees/agent-[0-9a-f]+` | Per-session agent worktrees |
| `.cos-agent-worktrees/luum-agent-os/task-desc-[0-9a-f]+` | Task-description worktrees |

---

## Discovery Results

Initial broad grep (pattern prefix only) returned 3 candidate files:

| File | Reason for match |
|------|-----------------|
| `docs/legal/pre-public-readiness-checklist.md` | Describes the L2 task itself (explicitly excluded) |
| `scripts/cos-registry.sh` | Code logic: `case "$project_path" in /tmp/*\|/private/tmp/*\|/var/folders/*\|/private/var/folders/*)` |
| `scripts/cos_init.py` | Code logic: `prefixes = ["/tmp/", "/private/tmp/", "/var/folders/", "/private/var/folders/"]` |

A follow-up targeted grep for **actual specific paths** (i.e., paths with real folder IDs such as
`/private/var/folders/ab/cd1234.../`) returned **0 hits** across all in-scope files.

---

## Files Modified

None. No actual leaked operator paths were found.

---

## Summary

| Metric | Count |
|--------|-------|
| Total hits (prefix pattern) | 3 files |
| Hits after specificity filter | 0 |
| Files scrubbed | 0 |
| Replacements applied | 0 |

---

## Intentionally Left Alone

| File | Matching text | Reason |
|------|---------------|--------|
| `scripts/cos-registry.sh` lines 39, 61 | `/private/var/folders/*` (prefix pattern only) | Legitimate code: shell `case` pattern and `jq` regex used to detect ephemeral installs. No real path leaked. |
| `scripts/cos_init.py` line 633 | `"/private/var/folders/"` (prefix string only) | Legitimate code: Python list of path prefixes for ephemeral-install detection. No real path leaked. |

---

## Conclusion

The repo HEAD contains **no leaked operator machine paths** in the target categories within the
defined scope. The L2 checklist item can be marked `done`.
