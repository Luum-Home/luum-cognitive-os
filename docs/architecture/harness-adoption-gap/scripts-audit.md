# Install/Update Scripts Audit — Post ADR-001

## Summary

9 scripts were audited. The ADR-001 bug class is **contained to the self-hosting path** —
`hooks/self-install.sh` was already fixed. However, the external installer (`cos-init.sh`) and
mass-updater (`auto-update-projects.sh`) install skills to `.cognitive-os/skills/cos/` (kernel
path, harness-invisible) in client projects and never populate `.claude/skills/` (driver path).
Client projects have no `self-install.sh` hook to bridge the gap at `SessionStart` — that script
is self-hosting-only. Result: **1 HIGH finding, 1 MEDIUM finding**. `cos-update.sh` and
`cos-bootstrap.sh` call `self-install.sh` directly, so they cascade the ADR-001 fix for the
self-hosting path. Extension installers are harness-agnostic (no incorrect paths).

---

## Findings Table

| Script | What it syncs | Destination(s) | Correct for harness? | Risk | Recommendation |
|---|---|---|---|---|---|
| `install.sh` | Delegates entirely to `cos-init.sh` | Same as `cos-init.sh` | Inherits `cos-init.sh` result | MEDIUM | See cos-init.sh row |
| `scripts/install-cos.sh` | CLI binary only (`cos` executable) | `/usr/local/bin` or `~/.local/bin` | N/A — no skill/rule/hook sync | LOW | No action needed |
| `scripts/cos-init.sh` | skills → `.cognitive-os/skills/cos/`; rules → `.claude/rules/cos/`; hooks → `.cognitive-os/hooks/cos/`; templates → `.cognitive-os/templates/cos/` | Kernel path for skills; driver path for rules | Rules: correct. Skills: **WRONG** — missing `.claude/skills/` dest | MEDIUM | Add `.claude/skills/cos/` as second skills destination |
| `scripts/cos-init-global.sh` | Rules only → `~/.claude/rules/cos/` | `~/.claude/rules/cos/` | Rules: correct (global driver path) | LOW | No action needed |
| `scripts/cos-update.sh` | Calls `hooks/self-install.sh` directly (Step 6) | Inherits self-install.sh output | Correct — cascades ADR-001 fix | LOW | No action needed |
| `scripts/auto-update-projects.sh` | Calls `cos-init.sh` per registered project | Inherits `cos-init.sh` result | Inherits `cos-init.sh` bug | HIGH | Fix cos-init.sh first; auto-update cascades automatically |
| `scripts/cos-bootstrap.sh` | Calls `hooks/self-install.sh` directly (Step 7) | Inherits self-install.sh output | Correct — cascades ADR-001 fix | LOW | No action needed |
| `scripts/apply-efficiency-profile.sh` | `.claude/settings.json` only (hook registrations) | `.claude/settings.json` | Correct — hook paths use `$CLAUDE_PROJECT_DIR/hooks/` | LOW | No action needed |
| `scripts/uninstall.sh` | Removes `.claude/rules/cos/`, `.cognitive-os/hooks/cos/`, `.cognitive-os/skills/cos/` | Removal targets the same wrong path | Incomplete removal if `.claude/skills/cos/` is ever added | LOW | Add `.claude/skills/cos/` removal once cos-init.sh is fixed |

---

## HIGH-risk findings (detailed)

### 1. `scripts/auto-update-projects.sh` — inherits cos-init.sh skills-path bug at mass scale

**Current behavior:**
Iterates over every project registered in `~/.cognitive-os/installations.json` that was
installed from the current COS source, and re-runs `cos-init.sh "--$project_mode"` (line 206)
inside each project directory. Output is suppressed (`> /dev/null 2>&1`).

```
(cd "$project_path" && COS_SOURCE_DIR="$COS_SOURCE_DIR" bash "$COS_SOURCE_DIR/scripts/cos-init.sh" "--$project_mode")
```

**Bug:**
`cos-init.sh` installs skills to `.cognitive-os/skills/cos/` (kernel path) but never to
`.claude/skills/` (driver path). Every project updated via `auto-update-projects.sh` ends up
with skills invisible to the harness — the same root cause as ADR-001 but applied across all
registered projects in one operation.

**Reproduction command:**
```bash
grep -n 'cos-init.sh' <operator-repo-path>/scripts/auto-update-projects.sh
# Line 206: COS_SOURCE_DIR="$COS_SOURCE_DIR" bash "$COS_SOURCE_DIR/scripts/cos-init.sh" "--$project_mode"
grep -n 'skills_dest' <operator-repo-path>/scripts/cos-init.sh
# Line 221: skills_dest=".cognitive-os/skills/cos"
```

**Proposed fix:**
Fix `cos-init.sh` first (see MEDIUM finding below). `auto-update-projects.sh` calls `cos-init.sh`
and requires no changes of its own — the fix cascades automatically.

**Blast radius if not fixed:**
Any project that has run `auto-update-projects.sh` since the last `cos-init.sh` was written
has skills installed exclusively in `.cognitive-os/skills/cos/`. Those projects' harness never
sees the updated skills. The number of affected projects equals the count in
`~/.cognitive-os/installations.json` with a matching `source` path.

---

## MEDIUM-risk findings (detailed)

### 1. `scripts/cos-init.sh` — skills installed only to kernel path, not harness driver path

**Current behavior:**
Skills are installed to `.cognitive-os/skills/cos/` (lines 221–249), which is the
vendor-agnostic kernel path. The harness reads `{project}/.claude/skills/`, which is never
created or populated by `cos-init.sh`. Rules correctly go to `.claude/rules/cos/` (driver path).
The skills path follows a different convention than the rules path — an inconsistency.

```bash
skills_dest=".cognitive-os/skills/cos"          # line 221 — kernel path, harness-invisible
# No second destination to .claude/skills/cos/  # absent — this is the gap
```

**Bug:**
Every external project that installs COS via `install.sh → cos-init.sh` ends up with skills
invisible to the harness. Unlike the self-hosting fix (ADR-001), there is no
`self-install.sh` running at `SessionStart` inside these projects to bridge the gap, because
`self-install.sh` is a self-hosting-only script and is not installed into client projects.

**Reproduction command:**
```bash
grep -n 'skills_dest' <operator-repo-path>/scripts/cos-init.sh
# Line 221: skills_dest=".cognitive-os/skills/cos"
ls /some-client-project/.claude/skills/ 2>/dev/null || echo "MISSING"  # will print MISSING
```

**Proposed fix:**
After the kernel-path install, add a parallel install to the driver path. Minimal change —
add after line 249 (the closing `fi` of the skills install block):

```bash
# Mirror skills to the harness driver path (.claude/skills/) so they are
# visible to the Claude Code harness (see ADR-001).
if [ "$MODE" != "--minimal" ] && [ -d "$skills_source" ]; then
  driver_skills_dest=".claude/skills/cos"
  mkdir -p "$driver_skills_dest"
  if [ "$MODE" = "--full" ]; then
    for skill_dir in "$skills_source"/*/; do
      [ -d "$skill_dir" ] || continue
      skill_name=$(basename "$skill_dir")
      cp -r "$skill_dir" "$driver_skills_dest/$skill_name"
    done
    [ -f "$skills_source/CATALOG.md" ] && cp "$skills_source/CATALOG.md" "$driver_skills_dest/CATALOG.md"
  else
    for name in $STANDARD_SKILLS; do
      [ -d "$skills_source/$name" ] && cp -r "$skills_source/$name" "$driver_skills_dest/$name"
    done
    [ -f "$skills_source/CATALOG.md" ] && cp "$skills_source/CATALOG.md" "$driver_skills_dest/CATALOG.md"
  fi
fi
```

**Blast radius if not fixed:**
All external projects that installed COS via `install.sh` (the documented onboarding path) have
zero skills visible to the harness. Users are forced to inline skill logic or rely on the 16
stale globally-installed skills at `~/.claude/skills/`, compounding the drift problem ADR-001
identified.

---

## LOW-risk (summarized only)

- `scripts/install-cos.sh`: Installs the `cos` CLI binary only. No skill/rule/hook sync. Harness-agnostic.
- `scripts/cos-init-global.sh`: Installs rules to `~/.claude/rules/cos/`. No skills. Destination is correct for global harness rules.
- `scripts/cos-update.sh`: Delegates skill sync to `hooks/self-install.sh` at Step 6. Cascades ADR-001 fix correctly for the luum-agent-os self-hosting path.
- `scripts/cos-bootstrap.sh`: Delegates skill sync to `hooks/self-install.sh` at Step 7 (same as `cos-update.sh`). Self-hosting path only.
- `scripts/apply-efficiency-profile.sh`: Writes `.claude/settings.json` with hook entries using `$CLAUDE_PROJECT_DIR/hooks/` paths. No skill/rules sync. Correct.
- `scripts/uninstall.sh`: Removes `.cognitive-os/skills/cos/` and `.claude/rules/cos/`. Does not remove `.claude/skills/cos/` because that path does not yet exist. Once `cos-init.sh` is fixed, `uninstall.sh` needs a matching removal line.
- `scripts/install-pre-commit.sh`: Symlinks `hooks/pre-commit-gate.sh` into `.git/hooks/`. Not a harness path. Correct.
- `scripts/install-aguara.sh`, `install-garak.sh`, `install-promptfoo.sh`, `install-mcp-scan.sh`: Install external binaries only; print manual hook registration instructions but do not modify harness paths.
- `scripts/install-tob-skills.sh`: Adds submodule to `.claude/plugins/trailofbits-skills/`. Plugin path is valid for harness — not a bug.

---

## Recommended commit plan

1. **Fix `cos-init.sh`** — add `.claude/skills/cos/` as a second install destination (the MEDIUM finding). This is the root fix.

2. **Fix `uninstall.sh`** — add `[ -d ".claude/skills/cos" ] && rm -rf .claude/skills/cos` after the existing `.cognitive-os/skills/cos` removal (line 186). Depends on fix #1.

3. **Re-run `auto-update-projects.sh`** after fix #1 to re-install skills to `.claude/skills/cos/` in all registered client projects. No code change needed — the fix cascades automatically.

Dependency order: (1) must precede (2) and (3). Fixes (2) and (3) are independent of each other.

---

## What was NOT audited

- `scripts/generate-project-settings.sh` — called by `cos-init.sh` to generate `settings.json`; only writes hook registrations, no skill/rule sync. Excluded as out-of-scope for this audit.
- `scripts/merge-settings.sh` — merges `settings.json` fragments; no skill/rule sync. Excluded.
- `scripts/cos-registry.sh` — manages `installations.json`; no harness paths. Excluded.
- `scripts/setup-langfuse.sh` — provisions Langfuse API keys; no harness paths. Excluded.
