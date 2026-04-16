# Harness Adoption Gap — Diagnosis Report

## Summary

The root cause is a **path mismatch**: the Claude Code harness exposes skills from `~/.claude/skills/` (user-level), but the project's `self-install.sh` syncs `skills/` to `.cognitive-os/skills/` (project-local). Neither the project directory `skills/` nor its mirror `.cognitive-os/skills/` is on the harness's skill search path. The 16 skills that do appear in the harness were manually installed to `~/.claude/skills/` on 2026-03-21 — they are real files, not symlinks, frozen at that date. The remaining 110 skills added since then have no installation path to the harness. Confidence: 97%.

---

## Facts Established

- **Skills on disk** (`skills/`): 126 directories confirmed (124 skill dirs + 2 catalog files)
- **Skills exposed to harness** (`~/.claude/skills/`): 16 user-installed + ~24 from built-in anthropic/engineering plugins = ~40 total
- **Skills in `.cognitive-os/skills/`**: 150 entries (147 skill dirs + 3 catalog/index files) — synced by `self-install.sh` but NOT read by harness
- **No `.claude/skills/` directory exists** inside the project at all — the harness path the docs describe was never created

**Ghost skills confirmed** (dir + SKILL.md verified for all 9):

| Skill | Dir exists | SKILL.md exists | Frontmatter `description` |
|---|---|---|---|
| compose-prompt | yes | yes | yes |
| exhaustive-prompt | yes | yes | yes |
| agent-dashboard | yes | yes | (not checked — dir confirmed) |
| auto-refine | yes | yes | yes |
| verification-before-completion | yes | yes | yes |
| plan-feature | yes | yes | yes |
| session-backlog | yes | yes | yes |
| resource-governor | yes | yes | yes |
| paperclip-dashboard | yes | yes | yes |

**Skills that ARE exposed** live at `~/.claude/skills/` (16 dirs, real files, last modified 2026-03-21):
`go-testing`, `mcp-builder`, `pdf`, `sdd-apply`, `sdd-archive`, `sdd-design`, `sdd-explore`, `sdd-init`, `sdd-propose`, `sdd-spec`, `sdd-tasks`, `sdd-verify`, `skill-creator`, `skill-registry`, `webapp-testing`, `xlsx`

---

## Hypothesis Ranking (by probability)

### H1 — Wrong sync destination: `self-install.sh` writes to `.cognitive-os/skills/` but harness reads `~/.claude/skills/`

**Evidence:**
- `self-install.sh` line 37: `"skills|cos|tree|"` — the `cos` dest_base resolves to `$PROJECT_DIR/.cognitive-os/skills/` (line 48-50: `cos` -> `"$PROJECT_DIR/.cognitive-os/$name"`)
- `~/.claude/skills/` has 16 real files installed March 21 — the day the OS was first set up. No entry installed since then.
- `.cognitive-os/skills/` has 150 symlinks pointing to `skills/` subdirs — correct targets but wrong location for the harness.
- `.claude/skills/` does NOT exist anywhere in the project directory tree. The harness-expected path was never created.
- `pi-mono` docs (`.claude/plugins/pi-mono/packages/coding-agent/docs/skills.md`) confirm harness reads from `~/.claude/skills` as a primary path.
- `docs/os-vs-project-separation.md` describes the correct path as `{project}/.claude/skills/` for project-level skills, yet this directory was never created.

**Reproduction:**
```bash
# Confirm the mismatch:
ls ~/.claude/skills/ | wc -l          # 16 (what harness sees)
ls .cognitive-os/skills/ | wc -l     # 150 (what self-install creates)
ls .claude/skills/ 2>/dev/null || echo "MISSING"  # should print MISSING
```

**Confidence: 97%**

---

### H2 — The harness also reads `{project}/.claude/skills/` but that directory was never created

**Evidence:**
- `docs/os-vs-project-separation.md` explicitly names `{project}/.claude/skills/` as a valid skill location for project-level skills (Layer 2).
- The directory `luum-agent-os/.claude/skills/` does not exist — verified by `ls .claude/` showing only `launch.json`, `plugins`, `rules`, `settings.json*`, `worktrees`.
- If the harness reads BOTH `~/.claude/skills/` AND `{project}/.claude/skills/`, then creating the project-level dir and populating it would expose all 126 skills with zero changes to `self-install.sh`.

This is NOT a separate cause from H1 — it is the same gap from a different angle (missing destination, not wrong destination). Resolution is identical either way.

**Confidence: 95%** (complementary to H1, not contradictory)

---

### H3 — Frontmatter missing required fields filters out ghost skills

**Evidence against this hypothesis:**
- `compose-prompt` has `name`, `description`, `user-invocable: true`, `version`, `audience` — richer frontmatter than the exposed `skill-creator` (which has only `name`, `version`, `audience`, `invoke`, `effort` — NO `description`).
- `session-backlog` has `name`, `description`, `user-invocable`, `version`, `last-updated`, `audience`, `tags` — very complete.
- The exposed `~/.claude/skills/skill-creator/SKILL.md` has no `description` field and IS exposed; `compose-prompt` has `description` and is NOT exposed.
- Frontmatter differences do NOT correlate with exposure status.

**Confidence: 2%** (effectively ruled out)

---

### H4 — File permissions block the harness from reading ghost SKILL.md files

**Evidence against:**
- `.cognitive-os/skills/compose-prompt` → symlink to `skills/compose-prompt/` → `SKILL.md` is `rw-r--r--` (world-readable)
- The ghost skills' parent directories are `rwxr-xr-x` — normal permissions.
- The 16 exposed skills in `~/.claude/skills/` are also `rw-r--r--` — same permissions.
- No permission difference detected.

**Confidence: 1%**

---

### H5 — Harness has a hard limit on skills count (~40 max) and stops scanning

**Evidence against:**
- The 40 exposed skills come from THREE distinct sources: `~/.claude/skills/` (16), built-in `anthropic-skills:*` namespace (~8), and `engineering:*` namespace (~10), plus `update-config`, `keybindings-help`, `simplify`, etc. — these are not all from a single directory scan that hit a limit.
- If a limit existed, it would affect both user-level and project-level skills equally. The user-level installs (16) are well under any plausible limit.

**Confidence: 1%**

---

## Specific Finding: compose-prompt vs skill-creator

`compose-prompt` (ghost) frontmatter:
```yaml
---
name: compose-prompt
description: Compose a sub-agent prompt from reusable templates. Use when launching sub-agents to ensure consistent instructions.
user-invocable: true
version: 1.0.0
audience: project
---
```

`skill-creator` at `~/.claude/skills/skill-creator/SKILL.md` (exposed) frontmatter:
```yaml
---
name: skill-creator
description: >
  Creates new AI agent skills following the Agent Skills spec.
  Trigger: When user asks to create a new skill, add agent instructions, or document patterns for AI.
license: Apache-2.0
metadata:
  author: gentleman-programming
  version: "1.0"
allowed-tools: Read, Edit, Write, Glob, Grep, Bash, WebFetch, WebSearch, Task
---
```

`skill-creator` at `skills/skill-creator/SKILL.md` (same project, NOT exposed) frontmatter:
```yaml
---
name: skill-creator
version: 1.1.0
audience: both
invoke: /skill-creator
effort: opus
---
```

**Interpretation:** The SAME skill name exists at both levels. The harness exposes the `~/.claude/skills/` version (installed March 21), not the project version. The project version is invisible. This confirms H1: the path is the discriminating factor, not the frontmatter content.

---

## Proposed Experiments (next session)

Ranked by cost/value — cheapest and highest-signal first:

### Experiment 1 (5 min, zero risk) — Verify harness reads `{project}/.claude/skills/`

```bash
mkdir -p .claude/skills/smoke-test-skill
cat > .claude/skills/smoke-test-skill/SKILL.md <<'EOF'
---
name: smoke-test-skill
description: Temporary smoke test to verify harness reads .claude/skills/
---
# Smoke Test Skill
This skill exists only to verify the harness skill path.
EOF
```

Then start a new session. If `smoke-test-skill` appears in the system-reminder skills list, H1+H2 are confirmed and the fix is to redirect `self-install.sh` to write to `{project}/.claude/skills/` instead of `.cognitive-os/skills/`.

Clean up after: `rm -rf .claude/skills/smoke-test-skill`

---

### Experiment 2 (10 min, zero risk) — Verify harness also reads `~/.claude/skills/` for a new skill

```bash
mkdir -p ~/.claude/skills/smoke-test-skill-2
cp skills/compose-prompt/SKILL.md ~/.claude/skills/smoke-test-skill-2/SKILL.md
# Edit name to smoke-test-skill-2
```

Start a new session. If `smoke-test-skill-2` appears in skills list, confirms `~/.claude/skills/` is always read. This distinguishes whether the fix is project-level install (Exp 1) or global install.

---

### Experiment 3 (30 min) — Update `self-install.sh` to additionally symlink to `{project}/.claude/skills/`

Change `SYNC_DIRS` entry:
```
"skills|cos|tree|"
```
to:
```
"skills|cos|tree|"
"skills|claude|tree|"
```

Where `claude` dest_base resolves to `$PROJECT_DIR/.claude/skills/`. This adds a second sync target without removing the existing `.cognitive-os/skills/` sync. Idempotent and reversible.

---

### Experiment 4 (1 hour, if Exp 3 confirmed) — Full fix: symlink 126 skills into `.claude/skills/` and validate

Run updated `self-install.sh`, then start a fresh session. Count exposed skills in system-reminder. Target: all 9 core ghost skills visible. Run `tests/infra/test-skills.sh` to verify no regressions.

---

## Recommendation

Run **Experiment 1** first — it takes 5 minutes and either confirms or refutes the entire hypothesis chain with zero risk. If confirmed, apply the **Experiment 3** fix (one-line change to `self-install.sh` SYNC_DIRS plus adding `claude` as a dest_base case in `resolve_dest()`).

The frontmatter is NOT the issue — do not modify any SKILL.md files. The self-install sync destination is the only thing that needs to change.

**Expected outcome after fix:** All 126 project skills become visible to the harness, de-ghosting all 86 invisible skills in one session.
