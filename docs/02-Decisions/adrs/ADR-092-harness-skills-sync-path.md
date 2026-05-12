---
adr: 92
title: Harness Skills Sync Path — Add `.claude/skills/` as Second Sync Destination
status: accepted
implementation_status: implemented
date: '2026-04-30'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: 'self-install resolves claude skills destinations and syncs skills into harness-specific paths'
---

# ADR-092: Harness Skills Sync Path — Add `.claude/skills/` as Second Sync Destination

<!-- Renumbered-from: ADR-001 (docs/04-Concepts/architecture/harness-adoption-gap/ADR-001-harness-skills-sync-path.md) -->
<!-- Renumbered-to: ADR-092 (ADR-087 migration, 2026-04-30) -->

## Status

Accepted

## Context

As of 2026-04-16, the project has 126 skill directories under `skills/`. The Claude Code harness
exposes only ~40 skills: 16 manually installed to `~/.claude/skills/` on 2026-03-21, plus ~24
built-in harness skills. The remaining 86 skills are invisible to the harness ("ghosts").

The 9 most-requested ghost skills, all confirmed present on disk with `SKILL.md` and valid
frontmatter, are:

| Skill | Directory | SKILL.md |
|---|---|---|
| compose-prompt | yes | yes |
| exhaustive-prompt | yes | yes |
| agent-dashboard | yes | yes |
| auto-refine | yes | yes |
| verification-before-completion | yes | yes |
| plan-feature | yes | yes |
| session-backlog | yes | yes |
| resource-governor | yes | yes |

Root cause (from `diagnosis.md`): `self-install.sh` syncs `skills/` only to
`.cognitive-os/skills/` via the `"skills|cos|tree|"` entry in `SYNC_DIRS`. The harness does
NOT read `.cognitive-os/skills/`. It reads `{project}/.claude/skills/` for project-scoped
skills, and `~/.claude/skills/` for user-scoped skills. The project directory `.claude/skills/`
was never created.

**Experiment 1 confirmation (2026-04-16):** A `smoke-test-skill` placed manually under
`.claude/skills/smoke-test-skill/` appeared in the harness system-reminder skills list on the
next session start, empirically confirming that `{project}/.claude/skills/` is a live harness
search path. Full details in `diagnosis.md`, Experiment 1.

The 16 skills currently exposed via `~/.claude/skills/` are real files (not symlinks), frozen
at the 2026-03-21 install date. Any skill added to `skills/` after that date — 110 skills — has
no install path to the harness. The orchestrator has been inlining skill logic that should be
invoked via `/skill-name`, wasting tokens and duplicating behavior.

## Decision

Add `{project}/.claude/skills/` as a **second** sync destination in `self-install.sh` alongside
the existing `.cognitive-os/skills/` sync.

Concretely, two changes to `hooks/self-install.sh`:

1. **SYNC_DIRS entry** (one line appended after the existing `skills|cos|tree|` entry):
   ```
   "skills|claude|tree|"
   ```

2. **`resolve_dest()` case**: the `claude` case already exists in `resolve_dest()` (line 49),
   resolving to `$PROJECT_DIR/.claude/$name`. No additional case is needed — the existing
   handler covers the new entry.

The result: on every `SessionStart`, `self-install.sh` creates symlinks in `.claude/skills/`
pointing into `skills/` subdirs, the same tree structure already created in
`.cognitive-os/skills/`. Both destinations stay in sync automatically. The change is
idempotent: re-running the installer does not duplicate symlinks.

## Alternatives rejected

**1. Sync to `~/.claude/skills/` (user-level global install)**

Rejected. Requires write access outside the project directory. Not repo-trackable — the
symlink state cannot be committed or audited via `git status`. The 16 manually-installed skills
at `~/.claude/skills/` already demonstrate the drift problem: they are frozen real files from
2026-03-21, not symlinks, and do not pick up updates from `skills/`. Adding 126 more frozen
files to the user-level path compounds the drift problem rather than solving it. Future projects
on the same machine would inherit these skills unintentionally.

**2. Replace `.cognitive-os/skills/` with `.claude/skills/` entirely**

Rejected. Violates the OS kernel vs driver separation principle:
- `.cognitive-os/` is the vendor-agnostic kernel layer. It must remain usable by non-Claude-Code
  harnesses (Codex, Cursor, future tools) that may adopt a different skill path convention.
- `.claude/` is the Claude-Code-specific driver layer. Skills synced there are explicitly for
  the Claude Code harness.

Removing the `.cognitive-os/skills/` sync would couple the OS kernel to a single vendor's path
convention, making it harder to run the same skills under a different harness in the future.
Both destinations must coexist.

**3. Per-skill opt-in list (allow-list before harness exposure)**

Rejected. Every new skill would require a manual update to the allow-list before it becomes
usable. This adds a recurring maintenance gate that defeats the purpose of the skill library: a
skill added to `skills/` should be usable immediately after `self-install.sh` runs, without
any secondary registration step. The current ghost problem is itself evidence of what happens
when skills require a manual install step — they fall behind.

## Consequences

- All 126 project skills become exposed to the harness on the next `SessionStart` after
  `self-install.sh` runs, de-ghosting all 86 invisible skills in one pass.

- `.claude/skills/` becomes the driver-specific skill surface: 126 symlinks pointing into
  `skills/`. The directory is maintained entirely by the installer — no manual symlink
  management.

- `.cognitive-os/skills/` retains its 150 entries (147 skill dirs + 3 catalog/index files) and
  continues to serve as the vendor-agnostic kernel path for any non-Claude-Code harness that
  reads it.

- The orchestrator gains access to `/compose-prompt`, `/auto-refine`, `/exhaustive-prompt`,
  `/plan-feature`, and all other ghost skills via the harness slash-command mechanism. Inlined
  skill logic in orchestrator prompts can be replaced with proper `/skill-name` invocations,
  reducing prompt token overhead.

- Other projects with COS installed are unaffected by this change (they do not run
  `luum-agent-os/hooks/self-install.sh`). They would need to re-run their own project installer
  to apply an equivalent fix to their own `self-install.sh`.

- The `.claude/skills/` directory should be added to `.gitignore` alongside
  `.cognitive-os/skills/` since it contains generated symlinks, not source files.

**Cross-references:** `docs/04-Concepts/architecture/harness-adoption-gap/diagnosis.md` (root cause
analysis, hypothesis ranking, Experiment 1 confirmation); `docs/04-Concepts/root/os-vs-project-separation.md`
(kernel vs driver layer convention).

## Verification

Run the focused contract for this decision:

```bash
python3 -m pytest tests/behavior/test_core_skills_check.py -q
```
