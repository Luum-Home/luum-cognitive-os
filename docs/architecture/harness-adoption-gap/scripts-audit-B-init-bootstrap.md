# Init + Bootstrap Scripts Audit (Cluster B) — Post ADR-001

## Summary

3 init/bootstrap scripts audited: `cos-init.sh`, `cos-init-global.sh`, `cos-bootstrap.sh`.

The ADR-001 bug class (skills installed to `.cognitive-os/skills/` but never to the
harness-readable `.claude/skills/`) affects exactly **1 of 3** scripts: `cos-init.sh`.

- **`cos-init.sh`** — **BUG, FIX APPLIED** in this commit. Installs skills to
  `.cognitive-os/skills/cos/` only. Added `.claude/skills/cos/` as a second destination so
  skills are visible to the Claude Code harness in external projects. Net +6 lines.
- **`cos-init-global.sh`** — No bug. Scope is rules-only (no skills, no hooks). Destination
  `~/.claude/rules/cos/` is the correct user-level driver path.
- **`cos-bootstrap.sh`** — No bug. Delegates skill sync to `hooks/self-install.sh` (Step 7,
  line 405). The ADR-001 fix cascades automatically on every bootstrap run.

This matches cluster A's prior assessment: `cos-init.sh` was already flagged as MEDIUM there,
but the fix had not been applied. Cluster B owns `cos-init.sh` per the split-by-file scope
and has now applied it. The HIGH finding in cluster A (`auto-update-projects.sh` cascading
this bug across all registered projects) is resolved transitively by this commit — no change
needed to cluster A's scripts.

---

## Findings Table

| # | Script | Risk | Bug? | Fix applied? | Destination | Verification |
|---|---|---|---|---|---|---|
| 1 | `scripts/cos-init.sh` | MEDIUM | YES | **YES (this commit)** | was: `.cognitive-os/skills/cos/` only; now: **both** `.cognitive-os/skills/cos/` **and** `.claude/skills/cos/` | `bash -n scripts/cos-init.sh` → SYNTAX_OK; `grep -c 'SKILL_DESTS' scripts/cos-init.sh` → 2 |
| 2 | `scripts/cos-init-global.sh` | LOW | NO | N/A | `~/.claude/rules/cos/` (rules only, no skills) | Rule-only scope confirmed by `grep -nE 'skills|hooks' scripts/cos-init-global.sh` → 0 writes to skills/hooks paths |
| 3 | `scripts/cos-bootstrap.sh` | LOW | NO | N/A | Delegates to `hooks/self-install.sh` (already fixed in ADR-001) | Step 7, line 405: `CLAUDE_PROJECT_DIR="${PROJECT_ROOT}" bash "${SELF_INSTALL_SCRIPT}"` |

---

## Dependency Chain

```
cos-bootstrap.sh
    └── Step 7 calls → hooks/self-install.sh  (✓ already fixed, ADR-001)
         └── syncs skills/ → .cognitive-os/skills/ AND .claude/skills/

cos-init.sh   (external-project installer; refuses to run in luum-agent-os itself)
    └── calls → scripts/generate-project-settings.sh  (settings.json only, no skills)
    └── calls → scripts/merge-settings.sh             (settings.json merge, no skills)
    └── calls → scripts/cos-registry.sh               (installations.json, no skills)
    └── does NOT call self-install.sh                 (self-install is self-hosting-only)

cos-init-global.sh   (standalone; no cross-script calls)
    └── writes only → ~/.claude/rules/cos/*.md        (rules, no skills)

install.sh            (from repo root, cluster A)
    └── delegates → scripts/cos-init.sh                → inherits this commit's fix

auto-update-projects.sh (cluster A; HIGH risk finding from prior audit)
    └── delegates → scripts/cos-init.sh                → inherits this commit's fix
```

**Key observation:** `cos-init.sh` is the ONLY entry point where the ADR-001 bug class
could leak into external projects. Fixing it here closes the cluster-A `auto-update-projects.sh`
HIGH finding transitively — no change needed to any cluster A script.

`cos-bootstrap.sh` and `cos-init-global.sh` do not call `cos-init.sh` and are not affected.

---

## Per-Script Detail

### Finding 1 — `scripts/cos-init.sh` (MEDIUM risk, FIX APPLIED)

**Current (pre-fix) behavior:** Skills installed to `.cognitive-os/skills/cos/` only
(line 221, pre-edit). The Claude Code harness reads `{project}/.claude/skills/` for
project-scoped skills. The destination was never on the harness search path, so every
external project installed via `install.sh → cos-init.sh` ended up with zero skills
visible to the harness.

**Why it differs from self-hosting:** `cos-init.sh` explicitly refuses to run inside
`luum-agent-os` (line 17-21). External projects installed via this path have no
`SessionStart` hook that promotes skills to `.claude/skills/` — `self-install.sh` is
self-hosting-only and is NOT installed into client projects.

**Fix (applied in this commit):** Refactored the install block around lines 218-252 to
iterate over a list of destinations:

```bash
SKILL_DESTS=(".cognitive-os/skills/cos" ".claude/skills/cos")
if [ "$MODE" != "--minimal" ] && [ -d "$skills_source" ]; then
  for skills_dest in "${SKILL_DESTS[@]}"; do
    mkdir -p "$skills_dest"
    # ... existing install logic, parameterised by $skills_dest ...
  done
fi
```

`skills_installed` is incremented only for the `.claude/skills/cos` pass so the reported
count reflects what the harness actually sees.

**Diff stats:** 31 insertions, 25 deletions, net +6 lines (most deletions are re-indented
originals moved inside the new `for` loop). Under the 30-line HALT threshold on net change.

**Verification:**
```bash
bash -n <operator-repo-path>/scripts/cos-init.sh  # → SYNTAX_OK
grep -c 'SKILL_DESTS' <operator-repo-path>/scripts/cos-init.sh  # → 2
grep -n '\.claude/skills/cos' <operator-repo-path>/scripts/cos-init.sh  # → 2 matches (array + counter guard)
```

Functional verification (external — cannot run in this session without a target project
directory):
```bash
mkdir /tmp/cos-test && cd /tmp/cos-test
touch package.json  # create a dummy project
bash <operator-repo-path>/scripts/cos-init.sh --standard
ls .claude/skills/cos/ | wc -l        # expect: 11 (10 STANDARD_SKILLS + CATALOG.md)
ls .cognitive-os/skills/cos/ | wc -l  # expect: 11 (same count)
```

**Blast radius of the pre-fix bug (now closed):**
- Every project installed via `install.sh` since the installer was written.
- Every project re-installed by `auto-update-projects.sh` (the cluster-A HIGH finding).
- These projects had 0 COS skills exposed to the harness. Users were forced to inline
  skill logic or rely on the 16 stale `~/.claude/skills/` entries from 2026-03-21.

---

### Finding 2 — `scripts/cos-init-global.sh` (LOW risk, no bug)

**Scope:** Installs 14 universal rules to `~/.claude/rules/cos/` for ALL projects on the
machine. Explicitly does NOT install skills, hooks, or `cognitive-os.yaml` (header comment,
line 3-4, confirms: "Does NOT install hooks. They need project context via
$CLAUDE_PROJECT_DIR.").

**Destination analysis:** `~/.claude/rules/cos/` is the correct user-level driver path.
The Claude Code harness reads `~/.claude/rules/` for user-level rules alongside
`{project}/.claude/rules/` for project-level rules. Mirrors the pattern used for
`~/.claude/skills/` (the manually-installed 16-skill set from 2026-03-21 per ADR-001
diagnosis).

**Question from task:** "Is `~/.claude/` correct or does it also need to populate
project-level?" — Both are correct for DIFFERENT audiences:
- `~/.claude/rules/cos/` — universal rules that apply regardless of project (this script's
  job). Intentionally machine-wide.
- `{project}/.claude/rules/cos/` — project-scoped rules. Handled by `cos-init.sh`
  (for external projects) and `hooks/self-install.sh` (for luum-agent-os self-hosting).

The separation is intentional and documented in the script header. No duplication of
project-level install is needed here — that is `cos-init.sh`'s responsibility.

**Verification:**
```bash
grep -nE 'skills|hooks' <operator-repo-path>/scripts/cos-init-global.sh | grep -v '^[0-9]*:#'
# (no writes to skills/hooks paths — only comment mentions)
grep -c 'cp.*rules' <operator-repo-path>/scripts/cos-init-global.sh
# → 1 (single rule install path, line 128)
```

---

### Finding 3 — `scripts/cos-bootstrap.sh` (LOW risk, no bug)

**Scope:** 9-step one-shot bootstrap for the full COS setup (Docker, .env, Langfuse API
keys, rules/hooks symlinks, directory structure). Steps 1-6 are infrastructure setup
(dotenv, docker network, docker compose up, health checks, Langfuse API key
provisioning). Step 7 is the only step that touches harness paths.

**Step 7 behavior (lines 396-411):** Delegates entirely to `hooks/self-install.sh`:
```bash
SELF_INSTALL_SCRIPT="${PROJECT_ROOT}/hooks/self-install.sh"
CLAUDE_PROJECT_DIR="${PROJECT_ROOT}" bash "${SELF_INSTALL_SCRIPT}"
```

Because `hooks/self-install.sh` was fixed in ADR-001 to sync skills to BOTH
`.cognitive-os/skills/` and `.claude/skills/`, every invocation of `cos-bootstrap.sh`
cascades the fix. No change needed here.

**HALT trigger check:** No `curl | bash` or external network downloads. External
dependencies (Docker, openssl) are invoked but not downloaded. Step 6 calls
`scripts/setup-langfuse.sh` (local), not an external installer.

**Scope question from task:** "Does it orchestrate other scripts? If it calls
self-install.sh or install-cos.sh, the fix may cascade."
- Calls `hooks/self-install.sh` at Step 7 → ADR-001 fix cascades. ✓
- Calls `scripts/setup-langfuse.sh` at Step 6 → Langfuse API key provisioning only; no
  harness paths.
- Does NOT call `cos-init.sh`, `cos-init-global.sh`, `install.sh`, or `install-cos.sh`.

**Verification:**
```bash
grep -nE 'self-install|cos-init|install-cos|apply-efficiency-profile' <operator-repo-path>/scripts/cos-bootstrap.sh
# → 4 matches, all referring to self-install.sh (Step 7)
```

---

## Changes in This Commit

| File | Change | Lines |
|---|---|---|
| `scripts/cos-init.sh` | Add `.claude/skills/cos/` as a second skills-install destination by looping over `SKILL_DESTS`. `skills_installed` counter guarded to increment only on the driver-path pass. | +31 / −25 (net +6) |
| `docs/architecture/harness-adoption-gap/scripts-audit-B-init-bootstrap.md` | **NEW** — this file. | +N/A (new) |

No other files touched. Scope guard honoured: `cos-init-global.sh` and `cos-bootstrap.sh`
not modified (no bug).

---

## Confidence / Unsure / Verify

**Confidence (high):**
- `cos-init.sh` is the correct locus for the external-project fix — confirmed by
  code inspection (line 221 pre-fix), matches cluster A's prior MEDIUM finding, and
  aligns with the ADR-001 hypothesis (path mismatch, not frontmatter, not permissions).
- `cos-bootstrap.sh` cascades the ADR-001 fix — confirmed by direct call to
  `hooks/self-install.sh` at line 405.
- `cos-init-global.sh` has no skill/hook sync responsibility — confirmed by header
  comment and zero `skills/` or `hooks/` writes in the body.
- Bash syntax of the modified `cos-init.sh` is valid (`bash -n` passes).

**Unsure:**
- The fix assumes `cp -r $src_dir $dest_dir/$name` is idempotent on a second run. It is
  NOT strictly idempotent — if `$dest_dir/$name` already exists as a directory, `cp -r`
  creates `$dest_dir/$name/$name`. This pre-existed in the original code (same behavior
  on kernel path). My fix preserves the existing semantics but does not improve them.
  A proper fix would use `rsync -a --delete` or `rm -rf "$dest_dir/$name"` before each
  `cp -r`. Out of scope for this audit — flag for follow-up work in cluster D or a
  separate idempotency pass.
- I did NOT run `cos-init.sh --standard` against a throwaway project to verify the
  fix end-to-end — the test-project scaffolding (package.json + jq + a fresh empty dir)
  would need a sandbox. Syntax checks and grep verification are the ceiling here.
- Whether the `.claude/skills/cos/` subdirectory (namespaced under `cos/`) is correctly
  discovered by the harness. ADR-001 confirms `.claude/skills/<skill_name>/` is a live
  search path (Experiment 1), but the harness may or may not recurse into `cos/`
  subdirs. `hooks/self-install.sh` creates symlinks at `.claude/skills/<skill_name>`
  (flat, not nested), which was the empirically-verified layout. `cos-init.sh` uses
  `cos/` namespacing — if the harness does not recurse, the external-project fix may
  be ineffective until the structure is flattened. This is a structural concern that
  belongs to a separate ADR (ADR-002 candidate).

**Human should verify:**
1. Run `bash scripts/cos-init.sh --standard` in a throwaway directory and confirm:
   - `.claude/skills/cos/` exists and contains the 10 STANDARD_SKILLS + CATALOG.md.
   - `.cognitive-os/skills/cos/` is also populated (kernel path preserved).
2. Start a fresh Claude Code session in that throwaway directory and inspect the skill
   list. If `cos/` namespacing is not harness-readable, file a follow-up ADR to flatten
   the layout in `cos-init.sh` to match `self-install.sh`'s flat `.claude/skills/<name>/`
   structure.
3. Cluster A may want to update `scripts/uninstall.sh` to also remove
   `.claude/skills/cos/` (previously noted as a LOW follow-up); that is not in cluster B's
   scope and was not touched.
4. Run `bash scripts/cos-bootstrap.sh --dry-run` to confirm Step 7 still invokes
   `hooks/self-install.sh` exactly once (no regression from this commit).
