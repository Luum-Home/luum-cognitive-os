---
type: quality-synthesis
source: docs/09-Quality/legal/operator-data-scan.md
provenance: "L1 pre-public-readiness checklist item: a git-grep scan of all HEAD-tracked files for operator personal data (email, home path, name, MCP UUIDs) before flipping the repo to public visibility."
---

## What it is
A dated scan report (2026-05-08, branch `session/889b6132-adr-238-bug-tracking`) checking every git-tracked file at HEAD for leaked operator personal data across four categories: email, home path, name variants, and personal MCP server UUIDs.

## Key mechanics
- Method: `git grep -Il` for the operator email, home-path pattern, and name variants; a UUID sweep cross-checked against known-safe buckets (auto-generated agent session IDs in `docs/01-Build-Log/history/`, test fixtures).
- Skip list applied: `docs/01-Build-Log/history/` (frozen pre-sanitization archive), the readiness checklist itself, `tests/`, `scripts/audit-consumer-dependence.sh` (placeholder tokens only), `manifests/history-sanitization.yaml` (legitimate replacement rules), and non-source dirs (`.git/`, `node_modules/`, `.cognitive-os/`).
- 2 leaks found: (1) `CONTRIBUTING.md` line 237 lists the operator's real email as the public security/licensing contact — recommended fix is a role-based address or GitHub Discussions link; (2) `scripts/validate_tier_filter.py` line 39 hardcodes an absolute session-directory path derived from the operator's home directory (the Claude Code hashed project key), leaking both username and local layout — recommended fix is dynamic slug derivation or an `os.environ` override.
- 0 leaks for home path (only appears in the untracked `dashboard/.next/` build artifact) and 0 for personal MCP UUIDs.
- Summary table: 2 total leaks (1 email, 1 name-in-path), 0 legitimate/allowed hits, across 4 categories.
- Priority-ordered remediation: fix `validate_tier_filter.py` first (low blast radius code change), then `CONTRIBUTING.md` email swap, then confirm `dashboard/.next/` is gitignored as a preventive measure.

## Relations & where used
Evidence source for `docs/09-Quality/legal/pre-public-readiness-checklist.md` §L1 ("Operator personal data leakage check"), which marks the item `done` citing this report. Complements `docs/09-Quality/legal/operator-paths-scrub-report.md` (L2, worktree/temp-path leakage — a narrower scan) under the same C1 history-sanitization umbrella (ADR-218).

## Status / caveats
Dated, point-in-time snapshot (2026-05-08) of one specific HEAD commit — a later commit could reintroduce leaks in either flagged file, and this report does not itself confirm the recommended fixes were applied (that confirmation lives in the checklist, not here).
