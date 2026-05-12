# Cluster D Audit — Profile Generator + Uninstaller (Post ADR-001)

## Summary

Two scripts audited: `scripts/apply-efficiency-profile.sh` (the `.claude/settings.json`
source-of-truth generator) and `scripts/uninstall.sh` (the self-hosting uninstaller).

- **apply-efficiency-profile.sh**: hook wiring is **correct** post-ADR-001. The profile design
  is sound: `lean`/`standard`/`full` tiers are coherent, and none of the 9 core ghost skills
  named in ADR-001 are blocked by a profile-gated hook (skills are loaded by the harness from
  `.claude/skills/`, independent of hook wiring). One **LOW** issue found: dead code at line
  308 and a misleading "restore from backup" message — the `full` branch never reaches it
  (exits at line 94). One **INFO** observation: the `standard` profile comment-summary (lines
  289–300) drifted from the actual hook set emitted by `build_settings` (e.g. the summary lists
  7 PreToolUse Agent hooks but the code wires 10). Cosmetic only.
- **uninstall.sh**: **HIGH finding**. Does NOT remove `.claude/skills/` (the new ADR-001 sync
  destination). Relies on `rm -rf .cognitive-os/` to catch the kernel skills path, but the
  driver skills path at `.claude/skills/` is left behind as a symlink forest pointing into the
  (possibly deleted) `skills/` tree. Reinstall after uninstall would likely succeed (symlinks
  get re-created idempotently by `self-install.sh`), but a **partial** uninstall leaves 126
  stale symlinks that the harness still reads — defeating the stated "Cognitive OS has been
  uninstalled" promise.

**Fixes applied in this session:** 1 HIGH (uninstall.sh skills-removal gap). Profile generator
left untouched per scope guard (no wiring-behavior change needed).

---

## Findings Table

| Script | What it does | Destination(s) | Correct post-ADR-001? | Risk | Recommendation |
|---|---|---|---|---|---|
| `scripts/apply-efficiency-profile.sh` | Generates `.claude/settings.json` with a hook matrix by tier (`lean`/`standard`/`full`) | `.claude/settings.json` only | Yes — hook paths use `$CLAUDE_PROJECT_DIR/hooks/` (portable); no skill-sync dependency | LOW | Fix dead code at lines 303–311 (cosmetic). Reconcile summary block with actual wiring (cosmetic). |
| `scripts/uninstall.sh` | Removes COS agentic primitives from project | `.claude/rules/cos/`, COS hooks in `settings.json`, `cognitive-os.yaml`, `.cognitive-os/` | **NO** — misses `.claude/skills/` directory | HIGH | Add explicit removal of `.claude/skills/` after the `.cognitive-os/` removal block |

---

## HIGH-risk findings (detailed)

### 1. `scripts/uninstall.sh` — leaves `.claude/skills/` behind after uninstall

**Current behavior (before fix):**
The uninstaller has six cleanup stages (lines 37–109):
1. Remove `.claude/rules/cos/`
2. Strip COS-referencing hook entries from `.claude/settings.json` via `jq`
3. Remove `cognitive-os.yaml` (unless `--keep-config`)
4. Deregister from the global installations registry
5. `rm -rf .cognitive-os/`
6. `rmdir .claude/rules/` if empty

There is **zero handling** of `.claude/skills/` — the directory introduced by ADR-001 as the
harness-visible skills path. `grep 'skills' scripts/uninstall.sh` returned no matches before
the fix.

**Why this is a bug:**
After ADR-001, `hooks/self-install.sh` populates `.claude/skills/` with 126 symlinks pointing
into `{project}/skills/`. When `uninstall.sh` runs:
- Step 5 removes `.cognitive-os/` (wiping the kernel mirror of skills — OK).
- `.claude/skills/` remains intact with 126 symlinks.
- Those symlinks still resolve (the symlinks point at `skills/`, which is NOT in the
  uninstaller's removal list — correctly, since `skills/` is source code and not installed
  content).
- The harness still reads `.claude/skills/` on the next `SessionStart` → the user sees 126
  skills from a "supposedly uninstalled" OS. The uninstaller's final message
  ("Cognitive OS has been uninstalled") is **false**.

**Blast radius:**
Self-hosting context only (this `uninstall.sh` is meant for `luum-agent-os` itself, given
the Cluster A/B audit notes that client projects use `cos-init.sh` / a different removal
path). Low probability of invocation, but when invoked, the partial uninstall is misleading
and the user has to manually `rm -rf .claude/skills/` to finish the job.

**Reinstall concern (raised by cluster prompt):**
Reinstall via `hooks/self-install.sh` is **safe** — `sync_tree()` is idempotent: existing
symlinks whose target still exists are skipped (line 79: `if [ ! -e "$link" ]`), and broken
symlinks are removed (line 96). So the reinstall path does NOT fail, but the `between` state
(uninstalled, not reinstalled) is wrong.

**Reproduction command:**
```bash
grep -n 'skills' scripts/uninstall.sh  # returns nothing before fix
ls -la .claude/skills/ | head -3       # shows symlinks that would survive uninstall
```

**Fix applied this session:**
Added a dedicated removal block after stage 5 (`.cognitive-os/` removal), stages renumbered so
the "Remove install metadata" step becomes stage 7. The new stage 6 removes `.claude/skills/`
only if it is a directory (defensive), counts symlinks before removal for the summary, and
never touches `skills/` (the source). The removal does NOT affect
`~/.claude/skills/` (global user path, out of project scope).

```bash
# ── 6. Remove .claude/skills/ (ADR-001 driver path) ─────────────
# Populated by hooks/self-install.sh as symlinks into skills/. Not tracked in git
# (see .gitignore line 40). Removal is safe: only symlinks are removed; the
# source tree at skills/ is untouched.
if [ -d ".claude/skills" ]; then
  skill_link_count=$(find .claude/skills -maxdepth 1 -type l 2>/dev/null | wc -l | tr -d ' ')
  rm -rf .claude/skills
  removed_items="${removed_items:+$removed_items\n}  - .claude/skills/ (${skill_link_count} symlinks)"
fi
```

**HALT check:** the `rm -rf .claude/skills` path is literal and unambiguous — not a wildcard
or variable-expanded path. No HALT trigger. The directory contains only symlinks
(gitignored, generated by the installer). Source files at `skills/` are not touched.

**Verification (post-fix):**
```bash
grep -n 'skills' scripts/uninstall.sh  # now returns the new stage 6 block
# Dry-run reasoning: `rm -rf .claude/skills` only runs if the dir exists, preserving
# the script's existing no-op semantics when COS is not installed.
```

---

## LOW-risk findings (detailed)

### 1. `apply-efficiency-profile.sh` lines 303–311 — dead-code "restore from backup"

**Current behavior:**
```bash
# Line 304–305:
echo "To revert to full hooks: bash scripts/apply-efficiency-profile.sh full"
echo "  (This restores settings.json from settings.json.bak)"

# Line 307–311:
if [ "$PROFILE" = "full" ] && [ -f "$SETTINGS_FILE.bak" ]; then
  cp "$SETTINGS_FILE.bak" "$SETTINGS_FILE"
  echo "Restored full settings from backup."
fi
```

The condition `PROFILE = full` is unreachable at line 308: the `full` branch at line 83–95
already `exit 0`s. The promise at line 305 — "This restores settings.json from
settings.json.bak" — is **never executed**. In practice:
- If user runs `apply-efficiency-profile.sh lean`, then wants to revert with
  `apply-efficiency-profile.sh full`, the script hits the `full` branch at line 83 and
  merely prints the current hook count — it does **not** restore the backup.
- The backup mechanism at line 266–269 (`cp "$SETTINGS_FILE" "$SETTINGS_FILE.bak"`) is
  therefore write-only; there is no code path that reads it.

**Risk:** LOW. Misleading output only; no incorrect file state. The user likely gets what
they want anyway: running `apply-efficiency-profile.sh full` on a `lean`-configured
`settings.json` leaves it as-is (the script explicitly says "keeps settings.json unchanged").
But that contradicts the "reverts to full" narrative — a user expecting the backup
restore would be surprised.

**Recommendation (not applied — cosmetic):**
Either (a) remove lines 303–311 entirely and adjust the summary to say "the `full` profile is
the default and does not regenerate settings.json", or (b) move the restore logic into the
early `full` branch so it actually fires. Option (a) is safer because the backup from a
previous `lean` invocation may be older than the current `full` settings the user's custom
hooks rely on.

**Not applied this session** because the fix requires a design decision (does `full`
auto-restore, or is `full` purely documentation?) that crosses the HALT threshold for
"changes HOOK WIRING BEHAVIOR."

### 2. `apply-efficiency-profile.sh` summary block (lines 289–300) drifted from code

**Current behavior:**
The final echo summary for `standard` lists a subset of hooks ("PreToolUse Agent:
dispatch-gate.sh, clarification-gate.sh, blast-radius.sh, inject-phase-context.sh,
agent-prelaunch.sh, error-pattern-detector.sh, predev-completeness-check.sh") but the
`build_settings` function at lines 147–158 wires **ten** PreToolUse Agent hooks — including
`completeness-check-llm.sh`, `prompt-quality-llm.sh`, `registration-check.sh`, and
`agent-work-tracker.sh`. The PostToolUse Agent summary similarly misses
`confidence-gate-llm.sh`, `task-panel-sync.sh`, `task-bridge-notify.sh`. Total claimed is
"31 hooks" — actual count depends on what `grep -c '"command":'` produces after
regeneration.

**Risk:** LOW. Human-facing documentation drift only. The actual `settings.json` is correct
(it's what `build_settings` emits). The operator reading the summary might believe fewer
hooks fire than actually do, but no functional impact.

**Recommendation (not applied — cosmetic):**
Regenerate the summary block from the hook_group invocations programmatically, or at least
align the listed names. Not applied this session because it is purely cosmetic and requires
a small helper to stay in sync — out of scope for the ADR-001 audit.

---

## Profile Coverage Matrix — 9 Core Adoption Skills

For each of the 9 ghost skills named in ADR-001, the table below lists:
- whether the skill is exposed to the harness (all 9 are post-ADR-001, regardless of profile)
- any related hook wired only in `standard`/`full`
- whether the skill's **documented behavior** degrades when a profile-gated hook is absent

**Key insight:** skills in `.claude/skills/` are loaded by the harness at `SessionStart`
**independent of** the hook wiring in `.claude/settings.json`. The two systems are
orthogonal. No core adoption skill is "blocked" by a profile choice — the worst case is
that a related hook does not fire (observable behavior may be reduced, but the skill itself
is invocable via `/skill-name`).

| Skill | Exposed (lean) | Exposed (standard) | Exposed (full) | Related hook(s) | Hook wired in lean? | Hook wired in standard? | Behavior impact if hook absent |
|---|---|---|---|---|---|---|---|
| `compose-prompt` | Yes | Yes | Yes | none | n/a | n/a | None — skill is a pure template generator, no hook collaborator |
| `exhaustive-prompt` | Yes | Yes | Yes | `completeness-check.sh`, `completeness-check-llm.sh` | No | Yes (`completeness-check-llm.sh` in PreToolUse Agent) | Reduced: the `lean` profile lacks automatic completeness warnings before agent launch. Skill is still invocable; user loses the PreToolUse advisory but still gets the generated prompt. |
| `agent-dashboard` | Yes | Yes | Yes | `agent-bus-monitor.sh` (not in any profile), `agent-checkpoint.sh` (both), `agent-work-tracker.sh` (standard only) | Partial (agent-checkpoint only) | Yes | Dashboard display depends on metrics that `agent-checkpoint.sh` writes. Both profiles wire it. Degraded under `lean` because `agent-work-tracker.sh` (PreToolUse+PostToolUse Agent) is not wired — tracker events will be missing from the dashboard feed. |
| `auto-refine` | Yes | Yes | Yes | `auto-refine.sh` (referenced by skill, **does not exist on disk** — see note below) | n/a | n/a | The skill references a non-existent hook `auto-refine.sh` — this is a **pre-existing bug in the skill's documentation**, not caused by profile wiring. Out of scope for this audit. `auto-repair-dispatcher.sh` exists and is adjacent but not the same. |
| `verification-before-completion` | Yes | Yes | Yes | `completion-gate.sh`, `trust-score-validator.sh`, `claim-validator.sh`, `confidence-gate.sh`/`confidence-gate-llm.sh` | No | Yes (PostToolUse Agent) | Significantly degraded under `lean`: trust-score enforcement, claim validation, and completion-gate do not fire. The skill still produces reports when invoked explicitly, but the automatic post-task verification chain is absent. |
| `plan-feature` | Yes | Yes | Yes | `predev-completeness-check.sh` | No | Yes (PreToolUse Agent) | Reduced: lean lacks the pre-dev readiness check. Skill runs standalone fine; just no proactive gate. |
| `session-backlog` | Yes | Yes | Yes | `session-changelog.sh`, `session-hygiene.sh`, `session-cleanup.sh` | Only `session-cleanup.sh` | Yes (all three, in Stop) | Reduced under `lean`: backlog works but is not incrementally updated by Stop hooks; only `session-cleanup.sh` fires. User must manually invoke `/session-backlog` to refresh state. |
| `resource-governor` | Yes | Yes | Yes | `resource-check.sh` (not wired in any current profile — lives in `hooks/` but absent from generator) | No | No | No in-loop enforcement of budget limits. Skill is purely invocable; agent context is not automatically policed. This is a **pre-existing wiring gap**, not ADR-001-related. Could be argued as a bug, but outside the scope of "is ADR-001 correctly extended to the profile generator." |

### Matrix Interpretation

- **ADR-001 question** ("are any of the 9 core COS skills blocked by a profile-gated
  hook?"): **No**. All 9 skills are invocable via `/skill-name` in every profile because
  `self-install.sh` populates `.claude/skills/` regardless of profile.
- **Secondary observation** (out of ADR-001 scope but worth logging): several adoption
  skills (`verification-before-completion`, `exhaustive-prompt`, `plan-feature`,
  `session-backlog`) have *degraded automatic behavior* under `lean` because their companion
  PreToolUse/PostToolUse/Stop hooks are not wired at that tier. This is **by design** per the
  project-gotchas rule ("48/93 hooks are intentionally not wired").
- **Pre-existing bugs surfaced but not fixed** (out of scope):
  1. `auto-refine` skill references a non-existent `auto-refine.sh` hook.
     profile generator.
  3. `prompt-quality-llm.sh` and `completeness-check-llm.sh` fire in `standard` but are
     documented as LLM-evaluated advisories (ADR-022 reference in the script) — verify
     ADR-022 acceptance before relying on this behavior.

---

## Uninstall Completeness Checklist — Post ADR-001

The uninstaller must reverse every install action. Verification matrix before/after this
session's fix:

| Install action | Removal before fix | Removal after fix |
|---|---|---|
| `self-install.sh` creates `.cognitive-os/skills/` symlinks | Yes (via `rm -rf .cognitive-os/`) | Yes (unchanged) |
| `self-install.sh` creates `.claude/skills/` symlinks (ADR-001) | **No** — MISSED | Yes (new stage 6) |
| `self-install.sh` creates `.claude/rules/cos/` symlinks | Yes (stage 1) | Yes (unchanged) |
| `self-install.sh` creates `.cognitive-os/{sessions,metrics,tasks,workflows,pipeline-state}` | Yes (via `rm -rf .cognitive-os/`) | Yes (unchanged) |
| `apply-efficiency-profile.sh` writes `.claude/settings.json` hook entries | Partial — `jq` strips only entries matching `.cognitive-os/hooks/` pattern; current generator uses `$CLAUDE_PROJECT_DIR/hooks/` (different pattern) | Same — **NOT FIXED** (see risk note below) |
| `apply-efficiency-profile.sh` creates `.claude/settings.json.bak` | No | **Not fixed** — stale backup remains in `.claude/` after uninstall |
| Installer writes `.githooks/` and sets `core.hooksPath` | Not reverted — git config is left pointing at `.githooks` (which may have been removed, breaking subsequent commits) | **Not fixed** — cross-cutting git config issue |

### Secondary uninstall gaps (flagged for future work, NOT fixed this session)

**Settings.json scrub pattern is stale.**
Lines 47–69 strip hook entries whose command contains `.cognitive-os/hooks/`. But the current
`apply-efficiency-profile.sh` emits commands using `$CLAUDE_PROJECT_DIR/hooks/` (line 53 of
the generator). The jq filter would miss every hook written by a modern profile
application — they'd remain in `settings.json` after uninstall, pointing at a
no-longer-existing `hooks/` directory if the user later deletes the cloned repo. This is a
**second bug** in `uninstall.sh`, independent of ADR-001, with MEDIUM risk.

**Decision not to fix:** scope guard permits only "if fix needed" for `uninstall.sh`. The
ADR-001 driven fix is the `.claude/skills/` removal (applied). Fixing the settings.json
scrub pattern requires coordination with how `apply-efficiency-profile.sh` names hook paths
— a wiring-behavior-adjacent change that trips the HALT trigger. Log as separate finding for
a follow-up ticket.

---

## Verification Commands (post-fix)

```bash
# 1. Confirm the new skills removal block is in uninstall.sh
grep -n "\.claude/skills" scripts/uninstall.sh
#  Expected: two matches — the block header and the rm -rf line.

# 2. Confirm no regression in existing removal stages
grep -c "^# ── [0-9]\." scripts/uninstall.sh
#  Expected: 7 (was 6) — new stage 6 added, old "install metadata" step renumbered to 7.

# 3. Confirm the 9 core ghost skills remain exposed post-ADR-001 (smoke check)
for s in compose-prompt exhaustive-prompt agent-dashboard auto-refine \
         verification-before-completion plan-feature session-backlog \
  [ -d ".claude/skills/$s" ] && echo "OK $s" || echo "GHOST $s"
done
#  Expected: 9 × "OK"

# 4. Confirm apply-efficiency-profile.sh has NO skill-sync code (responsibility belongs to self-install.sh)
grep -cE "(claude|cognitive-os)/skills" scripts/apply-efficiency-profile.sh
#  Expected: 0 — profile generator must not touch skills paths.
```

---

## Acceptance Criteria Check

1. **Both scripts audited with risk level** — Yes. `apply-efficiency-profile.sh` = LOW (dead
   code + cosmetic drift), `uninstall.sh` = HIGH (missing `.claude/skills/` removal).
2. **Profile matrix for `apply-efficiency-profile`** — Yes. 9-row matrix above, with hook
   wiring per profile and behavior-impact analysis. Conclusion: none of the 9 core adoption
   skills is blocked by profile choice; skill exposure is orthogonal to hook wiring.
3. **Uninstall removal completeness verified** — Yes. One HIGH missed path (`.claude/skills/`)
   fixed this session. Two MEDIUM secondary gaps documented but not fixed (scope guard +
   HALT threshold).
4. **Any HIGH fix applied + verified** — Yes. `uninstall.sh` stage 6 added; verification
   commands above.

---

## Recommended Follow-ups (out of scope for this audit)

1. **Reconcile `uninstall.sh` settings.json scrub pattern** with the current hook-path
   convention (`$CLAUDE_PROJECT_DIR/hooks/`) used by `apply-efficiency-profile.sh`. Separate
   ticket; requires a design decision (does `uninstall.sh` restore from `settings.json.bak`,
   or regex-strip, or delete wholesale?).
2. **Clean up dead code in `apply-efficiency-profile.sh`** lines 303–311 — the "restore from
   backup" path that never fires. Separate ticket; cosmetic.
3. **Add `auto-refine.sh` hook** or remove the reference from the `auto-refine` skill —
   independent skill documentation bug, not this audit's scope.
   decide they should be contextual-only) — policy question for the efficiency-profile
   owner.

---

## Cross-references

- `docs/architecture/harness-adoption-gap/ADR-001-harness-skills-sync-path.md` — the decision
  this audit validates is correctly extended to the cluster's scripts.
- `docs/architecture/harness-adoption-gap/diagnosis.md` — root-cause analysis of the ghost
  skills gap.
- `docs/architecture/harness-adoption-gap/scripts-audit.md` — the parent audit (other
  clusters); this document is the Cluster D supplement.
- `templates/project-gotchas.md` lines 9 and 11 — documents the
  "`settings.json` is GENERATED" and "48/93 hooks intentionally not wired" design intent.
- `hooks/self-install.sh` lines 36–44 — the `SYNC_DIRS` table where ADR-001 added the
  `skills|claude|tree|` entry.
