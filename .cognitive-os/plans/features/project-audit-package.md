<!--
RECONCILIATION STATUS: SUPERSEDED
Superseded by: packages/project-audit/ exists on disk; hooks/git-context-capture.sh and hooks/session-changelog.sh registered (ROADMAP 1.1 RESOLVED per commit 92cf485); scripts/cos-config-audit.sh (commit f3d4cf7) covers drift detection
Reconciled: 2026-04-21
Reason: the package was built and the four behaviors (git context, audit-id, changelog, gap detection) are all either shipped or have registered hooks.
-->

# Plan: `packages/project-audit/` — Automated Work Tracking and Audit Trail

## Context

The OS moves faster than a human team. Sessions produce code, decisions, and artifacts at high velocity, but there's no unified audit trail. Cost events, task lifecycle, SDD state, and sprint stories exist in separate stores with no cross-cutting ID linking them. A stakeholder asking "what was done in week 3?" gets silence.

This package adds 4 concrete behaviors, each proven by integration tests:

1. **Git context capture** on every session close
2. **Audit ID threading** across all JSONL metrics
3. **Changelog generation** per session/sprint
4. **Traceability gap detection** (requirement → spec → code → test)

## What Already Exists (do NOT reinvent)

| Signal | Store | Quality |
|---|---|---|
| Agent cost per call | `cost-events.jsonl` | Good (real tokens) |
| Task lifecycle | `active-tasks.json` + `agent-timeouts.jsonl` | Good |
| Session metadata | `sessions/{id}/meta.json` | Partial (no git) |
| SDD phase state | Engram `planning/{change}/state` | Good but Engram-only |
| Sprint stories | `sprint-status.yaml` | Good structure, no event log |
| Error learning | `session-learnings.jsonl` | Good |

---

## Components

### 1. Lib Modules

**`lib/git_context.py`**
- `capture_session_git_context(project_dir) -> GitContext` — captures:
  - `branch: str` — current branch name
  - `commit_start: str` — HEAD sha at session start (read from session meta)
  - `commit_end: str` — HEAD sha now
  - `commits: List[CommitInfo]` — commits between start..end (sha, message, author, files_changed)
  - `diff_stat: str` — `git diff --stat {start}..{end}`
  - `files_added: int`, `files_modified: int`, `files_deleted: int`
- `format_git_summary(ctx: GitContext) -> str` — human-readable summary

**`lib/audit_id.py`**
- `AuditContext(session_id, sprint_id, change_id, branch)` — the cross-cutting ID
- `get_current_audit_context(project_dir) -> AuditContext` — reads session ID from env, sprint_id from `sprint-status.yaml`, change_id from active SDD state in Engram or `pipeline-state/`, branch from git
- `enrich_jsonl_entry(entry: dict, ctx: AuditContext) -> dict` — adds `session_id`, `sprint_id`, `change_id`, `branch` fields to any JSONL dict
- `stamp_active_task(task: dict, ctx: AuditContext) -> dict` — adds audit fields to task in active-tasks.json

**`lib/changelog_generator.py`**
- `generate_session_changelog(project_dir, session_id) -> SessionChangelog` — reads git context + task completions + SDD phase transitions for one session
  - `SessionChangelog(session_id, date, duration_minutes, commits, tasks_completed, decisions, files_changed_count, cost_usd)`
- `generate_sprint_changelog(project_dir, sprint_id) -> SprintChangelog` — aggregates all sessions in a sprint
  - `SprintChangelog(sprint_id, sessions, total_commits, total_tasks, total_cost, features_completed, bugs_fixed)`
- `format_changelog_md(changelog) -> str` — markdown output

**`lib/traceability_checker.py`**
- `TraceabilityLink(requirement, spec, code, test, status)` — status: COMPLETE/PARTIAL/MISSING
- `check_traceability(project_dir) -> TraceabilityReport` — scans:
  - Requirements: `docs/05-features/*.md` or `docs/01-context/*.md`
  - Specs: Engram `planning/{change}/spec` or `docs/` SDD artifacts
  - Code: `git log` for commits referencing requirements/specs
  - Tests: test files covering the changed code paths
- `find_gaps(report) -> List[TraceabilityGap]` — requirements without specs, specs without code, code without tests
- `format_gap_report(gaps) -> str`

### 2. Hooks

**`hooks/git-context-capture.sh`** — Stop hook
- Captures git context at session end via `lib/git_context.py`
- Writes to `sessions/{id}/git-context.json`
- Enriches `sessions/{id}/meta.json` with branch, commit_start, commit_end
- Appends session summary to `.cognitive-os/metrics/session-audit.jsonl`

**`hooks/audit-id-enricher.sh`** — PostToolUse on Agent|Bash
- After every tool use, reads current audit context
- Enriches the latest entry in relevant JSONL files with audit IDs
- Lightweight: only runs if sprint or change context exists

**`hooks/session-changelog.sh`** — Stop hook
- At session end, generates session changelog via `lib/changelog_generator.py`
- Writes to `.cognitive-os/changelogs/{session_id}.md`
- If sprint is active, appends to `.cognitive-os/changelogs/sprint-{sprint_id}.md`

### 3. Rules

**`rules/audit-trail.md`** — always_active: true
- Every session must produce a git context capture
- Every task must carry audit IDs (session_id, sprint_id if active)
- Session changelogs are mandatory, not optional
- Traceability check runs before `/sdd-archive`

### 4. Skills

**`skills/audit-report/SKILL.md`** — `/audit-report`
- On-demand: generates a full audit report for a sprint or date range
- Reads changelogs, cost events, task history, git context
- Produces `docs/audit/{sprint_id}-report.md`

**`skills/traceability-check/SKILL.md`** — `/traceability-check`
- On-demand: scans for gaps in requirement→spec→code→test chain
- Uses `lib/traceability_checker.py`
- Outputs gap report with recommendations

---

## Behavioral Tests (15 scenarios)

### Group A: Git Context Capture (lib)
- **A1**: Given a project with 3 commits since session start, `capture_session_git_context()` returns commits list with length 3, correct branch, and diff_stat with file counts
- **A2**: Given a project with 0 commits (no changes), returns empty commits list and files_added/modified/deleted all 0
- **A3**: Given commit messages "feat: add auth" and "fix: typo", format_git_summary includes both messages

### Group B: Audit ID (lib)
- **B1**: Given session_id="sess-123", sprint from sprint-status.yaml="2026-w15", branch="feature/auth", `get_current_audit_context()` returns all 3 fields populated
- **B2**: Given a JSONL entry `{"timestamp": "...", "agent": "..."}`, `enrich_jsonl_entry()` adds session_id, sprint_id, change_id, branch without losing existing fields
- **B3**: Given no active sprint (no sprint-status.yaml), sprint_id is empty string, other fields still populated

### Group C: Changelog Generator (lib)
- **C1**: Given 2 completed tasks and 5 commits in a session, `generate_session_changelog()` returns SessionChangelog with tasks_completed=2, commits count=5
- **C2**: Given 3 sessions in sprint "2026-w15", `generate_sprint_changelog()` aggregates all sessions' commits, tasks, and costs
- **C3**: `format_changelog_md()` produces valid markdown with headers, bullet lists, and cost summary

### Group D: Traceability Checker (lib)
- **D1**: Given docs/05-features/auth.md exists, a spec in Engram, code commits referencing "auth", and test_auth.py exists → TraceabilityLink status is COMPLETE
- **D2**: Given docs/05-features/payments.md exists but NO spec, NO code, NO tests → TraceabilityLink status is MISSING, find_gaps returns 3 gaps
- **D3**: Given 5 requirements, 3 with full traceability, 2 with gaps → gap report lists exactly the 2 incomplete ones

### Group E: Git Context Hook (behavioral — subprocess)
- **E1**: Hook runs at Stop, writes `sessions/{id}/git-context.json` with branch and commit fields
- **E2**: Hook enriches `meta.json` with git_branch field

### Group F: Audit ID Enricher Hook (behavioral — subprocess)
- **F1**: After Agent completion, latest cost-events.jsonl entry has session_id field
- **F2**: With no active sprint, enricher still adds session_id and branch (sprint_id empty)

### Group G: Session Changelog Hook (behavioral — subprocess)
- **G1**: At session Stop, `.cognitive-os/changelogs/{session_id}.md` is created with commit list and task summary
- **G2**: With active sprint, changelog is also appended to `sprint-{sprint_id}.md`

---

## Package Manifest

```yaml
name: "@luum/project-audit"
version: "1.0.0"
description: "Automated work tracking, audit trail, and traceability for Cognitive OS projects"
license: "Apache-2.0"
cos_version: ">=0.1.0"
provides: [skill, rule, hook]
exports:
  - source: "../../hooks/git-context-capture.sh"
    type: hook
    hook_event: Stop
    hook_matcher: ""
  - source: "../../hooks/audit-id-enricher.sh"
    type: hook
    hook_event: PostToolUse
    hook_matcher: "Agent|Bash"
  - source: "../../hooks/session-changelog.sh"
    type: hook
    hook_event: Stop
    hook_matcher: ""
  - source: "../../rules/audit-trail.md"
    type: rule
    always_active: true
  - source: "../../.cognitive-os/skills/audit-report/SKILL.md"
    type: skill
  - source: "../../.cognitive-os/skills/traceability-check/SKILL.md"
    type: skill
```

## Order of Implementation

1. `lib/git_context.py` + `tests/unit/test_git_context.py` (A1-A3)
2. `lib/audit_id.py` + `tests/unit/test_audit_id.py` (B1-B3)
3. `lib/changelog_generator.py` + `tests/unit/test_changelog_generator.py` (C1-C3)
4. `lib/traceability_checker.py` + `tests/unit/test_traceability_checker.py` (D1-D3)
5. `hooks/git-context-capture.sh` + `tests/behavior/test_git_context_hook.py` (E1-E2)
6. `hooks/audit-id-enricher.sh` + `tests/behavior/test_audit_enricher.py` (F1-F2)
7. `hooks/session-changelog.sh` + `tests/behavior/test_session_changelog.py` (G1-G2)
8. `rules/audit-trail.md`
9. Skills: audit-report, traceability-check
10. `packages/project-audit/cos-package.yaml` + README.md
