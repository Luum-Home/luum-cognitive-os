---
type: concept-synthesis
source: docs/04-Concepts/architecture/harness-adoption-gap/diagnosis.md
provenance: "126 skills exist on disk under skills/ but only ~40 (16 user-installed + built-in plugins) were visible to the Claude Code harness — 86 'ghost skills' invisible despite existing."
---

## What it is
Root-cause diagnosis (ADR-001): the harness reads `~/.claude/skills/` (user-level), but `self-install.sh` synced `skills/` only to `.cognitive-os/skills/` (project-local, not on the harness search path). No `.claude/skills/` directory existed in the project at all. Confidence 97%.

## Key mechanics
- Facts: skills on disk 126 dirs (124 skill dirs + 2 catalog files); exposed to harness ~40 (16 at `~/.claude/skills/`, frozen since 2026-03-21, real files not symlinks, + ~24 from built-in plugins); `.cognitive-os/skills/` had 150 entries synced but not read by harness.
- 9 confirmed ghost skills verified with dir + SKILL.md present: `compose-prompt`, `exhaustive-prompt`, `agent-dashboard`, `auto-refine`, `verification-before-completion`, `plan-feature`, `session-backlog`, `resource-governor` (+1).
- Hypothesis ranking: H1 wrong sync destination (self-install.sh line 37 `"skills|cos|tree|"` → `.cognitive-os/skills/`) 97% confidence; H2 missing `{project}/.claude/skills/` dir (complementary, 95%); H3 frontmatter fields ruled out (2%, `compose-prompt`'s richer frontmatter was still invisible while sparser `skill-creator` was exposed); H4 permissions ruled out (1%); H5 hard skill-count limit ruled out (1%).
- Key comparison: same-named `skill-creator` exists both at `~/.claude/skills/skill-creator/` (exposed, March-21 frozen) and `skills/skill-creator/` (project version, invisible) — confirms path, not frontmatter, is the discriminator.
- Proposed experiments ranked by cost: Exp 1 (5min) create `.claude/skills/smoke-test-skill/` and check a fresh session; Exp 2 (10min) same for `~/.claude/skills/`; Exp 3 (30min) update `self-install.sh` SYNC_DIRS to add `"skills|claude|tree|"`; Exp 4 (1hr) full fix + `tests/infra/test-skills.sh` regression check.

## Relations & where used
Root document for the ADR-001 harness-adoption-gap cluster; downstream audits (`scripts-audit.md`, `scripts-audit-B/-C/-D`) apply and verify the fix across install/update/uninstall scripts.

## Status / caveats
Diagnosis only (this doc does not itself report the fix as applied); recommendation is to run Experiment 1 first (zero risk) then apply Experiment 3's one-line `self-install.sh` change. Frontmatter is explicitly ruled out as a cause — do not modify SKILL.md files to "fix" this.
