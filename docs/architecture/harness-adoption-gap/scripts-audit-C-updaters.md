# Cluster C Audit — Updater Scripts (Post ADR-001)

## Summary

Two updater scripts audited:

1. `scripts/cos-update.sh` — single-project infrastructure updater (self-hosting only)
2. `scripts/auto-update-projects.sh` — mass updater across all registered COS installs

**Verdict: ADR-001 fix propagates correctly through both updaters.** Neither script
reimplements sync logic. Each delegates to a canonical installer:

- `cos-update.sh` → `hooks/self-install.sh` (fresh-from-disk, no cache)
- `auto-update-projects.sh` → `scripts/cos-init.sh` (which itself has been updated to
  dual-install skills into `.claude/skills/cos/`, matching the ADR-001 intent)

No bugs found in the updaters themselves. **No code changes applied.** The cluster is green
with two caveats that the human must verify (git-remote freshness + `cos-update.sh`
scope confusion in docs).

---

## Findings Table

| Script | What it delegates to | Fresh-version guarantee | Risk | Fix applied |
|---|---|---|---|---|
| `scripts/cos-update.sh` | `hooks/self-install.sh` (line 357) | Yes — invokes file directly from `$PROJECT_ROOT/hooks/` (no stash, no cache) | LOW | N/A — already correct |
| `scripts/auto-update-projects.sh` | `scripts/cos-init.sh` (line 206) | Yes — invokes `$COS_SOURCE_DIR/scripts/cos-init.sh` from current source tree | LOW | N/A — already correct |

---

## Propagation path

How does ADR-001 reach existing COS installs today? Three user-visible paths, all confirmed
to cascade the fix:

### Path 1 — Self-hosting repo (luum-agent-os itself)

```
user runs: bash scripts/cos-update.sh
           └─> Step 6 (line 357):
                 CLAUDE_PROJECT_DIR="$PROJECT_ROOT" bash "$PROJECT_ROOT/hooks/self-install.sh"
                 └─> self-install.sh reads SYNC_DIRS with "skills|claude|tree|"
                     └─> creates .claude/skills/<126 symlinks>
```

Applies to: the `luum-agent-os` source repo only.
Verified: `scripts/cos-update.sh:350-363` invokes `self-install.sh` by absolute path from
`$PROJECT_ROOT`; no cached copy, no stash. Fresh fix lands on next run.

### Path 2 — External project manual update

```
user runs: bash /path/to/luum-agent-os/install.sh --force
           └─> delegates to cos-init.sh (install.sh:232-244)
                 └─> cos-init.sh lines 218-256: SKILL_DESTS=(".cognitive-os/skills/cos" ".claude/skills/cos")
                     └─> copies skills/* into BOTH destinations in the target project
```

Applies to: any external project manually re-installed.
Verified: `scripts/cos-init.sh:225` — `SKILL_DESTS=(".cognitive-os/skills/cos" ".claude/skills/cos")`
— both destinations populated on every install/re-install.

### Path 3 — External projects auto-updated en masse

```
git pull inside luum-agent-os
└─> .git/hooks/post-merge fires
    └─> invokes scripts/auto-update-projects.sh
        └─> iterates registry: ~/.cognitive-os/installations.json
            └─> for each project: cd <project>; bash cos-init.sh --<mode>
                └─> (see Path 2)
```

Applies to: every project listed in the global installations registry whose `source`
matches the source repo where `git pull` ran.
Verified: `auto-update-projects.sh:206` invokes `$COS_SOURCE_DIR/scripts/cos-init.sh` —
fresh script from the just-pulled source tree.

### Diagram

```
  luum-agent-os repo  ───── git pull ─────► post-merge hook ──┐
  │                                                           │
  ├─ hooks/self-install.sh  ◄── cos-update.sh (self-hosting)  │
  │       │                                                   │
  │       └─► .claude/skills/* (self-hosting)                 │
  │                                                           │
  └─ scripts/cos-init.sh  ◄── install.sh  ◄── user (manual)   │
         │                                                    │
         ├─► .cognitive-os/skills/cos/ (kernel)                │
         └─► .claude/skills/cos/ (driver) ◄── auto-update-projects.sh
```

Both driver paths (`.claude/skills/` for self-hosting, `.claude/skills/cos/` for external
projects) are now populated by the respective installer. The ADR-001 fix reaches all
three audiences.

---

## Script 1 — `scripts/cos-update.sh`

### Risk: LOW

### Fix applied: N/A (no change required)

### What it does

Self-hosting-only updater. Runs inside the `luum-agent-os` source repo (the pre-flight
check at line 187 requires `cognitive-os.yaml` at `$PROJECT_ROOT=$SCRIPT_DIR/..`, which is
only true when invoked from inside the OS source).

Seven steps: merge env vars, pull Docker images (opt-in), restart services, run health
checks, provision Langfuse keys, **run `self-install.sh`**, print summary.

### Relevant block (step 6, lines 346-363)

```bash
step "Rules and hooks sync (self-install)"

SELF_INSTALL_SCRIPT="${PROJECT_ROOT}/hooks/self-install.sh"
...
  if [[ -f "${SELF_INSTALL_SCRIPT}" ]]; then
    CLAUDE_PROJECT_DIR="${PROJECT_ROOT}" bash "${SELF_INSTALL_SCRIPT}" || warn "self-install.sh encountered an issue."
    ok "Rules and hooks synced"
  else
    warn "hooks/self-install.sh not found — skipping."
  fi
```

### Verification

- Invocation path: `${PROJECT_ROOT}/hooks/self-install.sh`, where `PROJECT_ROOT=
  $(cd "${SCRIPT_DIR}/.." && pwd)` resolves to the on-disk OS repo root at the time of
  execution. No stashed/cached path.
- Environment: `CLAUDE_PROJECT_DIR` is forced to `${PROJECT_ROOT}`, preventing a stale
  env var from redirecting sync to the wrong directory.
- Dry-run: line 352-353 correctly mirrors the command without executing.
- Error handling: non-zero exit from `self-install.sh` is caught with `|| warn` — the
  update continues. Appropriate since health-check and summary steps remain useful even
  if sync has a transient issue.

### Caveat (non-blocking, advisory only)

`docs/getting-started.md:202-207` describes `cos-update.sh` as an *"Infrastructure update
(Docker services)"* immediately after describing *"Manual update of a single project"*
(`install.sh --force`). A reader could reasonably assume `cos-update.sh` is a generic
per-project updater. It is not — it only works inside the OS source repo.

This is a documentation clarity issue, not an updater defect. Out of Cluster C scope to
fix (touches `docs/getting-started.md`, not `scripts/cos-update.sh`).

---

## Script 2 — `scripts/auto-update-projects.sh`

### Risk: LOW

### Fix applied: N/A (no change required)

### What it does

Mass updater. Reads `~/.cognitive-os/installations.json`, filters entries whose `source`
equals the current OS source directory, and for each matching project re-runs
`cos-init.sh --<mode>` inside the project directory.

Intended invocation: `.git/hooks/post-merge` fires after `git pull`/`git merge` in the OS
source repo (confirmed present at `.git/hooks/post-merge`, calls
`scripts/auto-update-projects.sh`).

### Relevant block (lines 155-207)

```bash
(
  cd "$project_path" || { echo "    ERROR: cannot cd to $project_path"; exit 1; }

  # SAFETY: never run destructive ops on the COS source itself
  if [ "$(pwd -P)" = "$(cd "$COS_SOURCE_DIR" && pwd -P)" ]; then
    echo "    SKIPPED: project path is the COS source itself"
    exit 0
  fi

  # SAFETY: if .cognitive-os is a symlink ... replace with real directory
  if [ -L ".cognitive-os" ]; then ...; fi
  if [ -L ".claude" ]; then ...; fi

  # Remove ONLY COS-managed components (namespaced under cos/).
  [ -d ".claude/rules/cos" ] && rm -rf .claude/rules/cos
  [ -d ".cognitive-os/hooks/cos" ] && rm -rf .cognitive-os/hooks/cos
  [ -d ".cognitive-os/skills/cos" ] && rm -rf .cognitive-os/skills/cos
  [ -d ".cognitive-os/templates/cos" ] && rm -rf .cognitive-os/templates/cos

  # Migration: old flat layout cleanup ...

  # Re-run cos-init with original mode
  COS_SOURCE_DIR="$COS_SOURCE_DIR" bash "$COS_SOURCE_DIR/scripts/cos-init.sh" "--$project_mode" > /dev/null 2>&1
)
```

### Verification

- **No reimplemented sync logic.** All file movement is delegated to `cos-init.sh`.
  Whatever fix exists in `cos-init.sh` cascades.
- `cos-init.sh` was updated under ADR-001 (lines 218-256,
  `SKILL_DESTS=(".cognitive-os/skills/cos" ".claude/skills/cos")`), so driver-path
  skills ARE populated on every auto-update.
- **Fresh source guarantee:** line 206 invokes `"$COS_SOURCE_DIR/scripts/cos-init.sh"`,
  where `COS_SOURCE_DIR` is computed as `$(cd "$(dirname "$0")/.." && pwd)` at line 18 —
  i.e., the same source tree whose `post-merge` hook just fired. By then, `git pull` has
  already updated the working tree, so the `cos-init.sh` invoked is the post-pull
  version. No cache, no stash, no stale reference.
- **Pre-cleanup safety before re-init.** Lines 184-187 delete `.claude/rules/cos`,
  `.cognitive-os/hooks/cos`, `.cognitive-os/skills/cos`, `.cognitive-os/templates/cos`
  only. **Missing: `.claude/skills/cos` is NOT deleted before re-init.** See "Observation"
  below.
- Symlink-replacement safety: lines 167-180 correctly detect and replace `.claude` or
  `.cognitive-os` if they are symlinks (would otherwise cause `rm -rf` to escape the
  project directory).
- Dry-run: supported, does not execute the update block.
- `--list` mode: read-only, safe.
- Self-update safety: line 159-162 refuses to update a project whose path equals the OS
  source repo itself.

### Observation (non-blocking, documented for future work)

The pre-cleanup block at lines 184-187 removes `.cognitive-os/skills/cos` but not
`.claude/skills/cos`. `cos-init.sh` re-creates `.claude/skills/cos` with fresh copies
every run, so stale skills in that directory WILL be overwritten, but stale skills
removed from the source (deleted in the OS repo) will persist as orphans in
`.claude/skills/cos`.

This is symmetric to the gap for `.cognitive-os/skills/cos` that was already addressed
by the pre-cleanup removal. For full parity, a future change should add:

```bash
[ -d ".claude/skills/cos" ] && rm -rf .claude/skills/cos
```

before the `cos-init.sh` invocation. Not applied in this audit because:

1. ADR-001's stated goal (make skills visible to the harness) is met without it — every
   skill in `skills/` appears in `.claude/skills/cos/` after the update.
2. The orphaned-skill edge case is out of the Cluster C audit scope (this cluster was
   chartered to verify fix propagation, not to extend cleanup semantics).
3. Adding the `rm -rf` line mid-audit would violate the scope guard ("TOUCH ONLY … only
   if fix needed"). No broken fix was found.

Recommend tracking as a separate ticket for a later session.

### Security caveats (reported, non-blocking)

1. **No `git pull --verify-signatures`.** The post-merge hook fires after ANY merge into
   the source repo — including from an unauthenticated remote. A compromised remote
   could inject malicious changes into `cos-init.sh`, which would then propagate to every
   registered project in a single `git pull`. This is a supply-chain risk inherent to
   the git-auto-update model and is consistent with the existing
   `rules/supply-chain-defense.md`. **The auditor flags this but does NOT HALT** per the
   task's HALT triggers (no privileged ops, no unauthenticated remote explicitly
   configured here — the risk is the general one).

2. **No signature check on `cos-init.sh`.** The updater blindly executes whatever
   `cos-init.sh` exists in the source directory at the time of the hook firing.

3. **Suppressed output.** Line 206 redirects `cos-init.sh` output to `/dev/null`.
   Failures are counted (line 213) but error messages from `cos-init.sh` are lost. A
   silent degradation in one project would not be visible in the aggregate "updated:
   skipped: failed:" summary. Users seeing a `FAILED` count must re-run `cos-init.sh`
   manually per project to see the underlying error.

None of these are blockers for ADR-001 propagation. They are governance concerns for a
separate security review.

---

## Privileged operation scan

Both updaters were scanned for:

- `sudo` — not present in either
- `chmod -R` — not present
- `rm -rf` — present only under guarded paths: `$project_path/.claude/rules/cos`,
  `.cognitive-os/{hooks,skills,templates}/cos`, and the `(cd "$project_path" && ...)`
  subshell. Each `rm -rf` target is a COS-namespaced subdirectory. Symlink replacement
  of `.cognitive-os` / `.claude` is performed FIRST (lines 167-180) to prevent `rm -rf`
  from following a symlink out of the project directory.

No HALT triggers fired.

---

## Verification commands

```bash
# 1. cos-update.sh invokes self-install.sh directly
grep -n 'self-install\.sh' <repo-root>/scripts/cos-update.sh
# Expected: line ~357 — bash "${SELF_INSTALL_SCRIPT}"

# 2. self-install.sh contains both SYNC_DIRS entries
grep -n 'skills|claude\|skills|cos' <repo-root>/hooks/self-install.sh
# Expected: lines 37-38 — "skills|cos|tree|" and "skills|claude|tree|"

# 3. auto-update-projects.sh delegates to cos-init.sh
grep -n 'cos-init\.sh' <repo-root>/scripts/auto-update-projects.sh
# Expected: line 206 — bash "$COS_SOURCE_DIR/scripts/cos-init.sh" "--$project_mode"

# 4. cos-init.sh dual-installs skills
grep -n 'SKILL_DESTS' <repo-root>/scripts/cos-init.sh
# Expected: line 225 — SKILL_DESTS=(".cognitive-os/skills/cos" ".claude/skills/cos")

# 5. post-merge hook invokes auto-update-projects.sh
grep -n 'auto-update-projects' <repo-root>/.git/hooks/post-merge
# Expected: line ~12 — bash "$_COS_DIR/scripts/auto-update-projects.sh"

# 6. Self-hosting sanity check: .claude/skills/ is populated
ls <repo-root>/.claude/skills | wc -l
# Expected: > 0 (populated by self-install.sh)

# 7. Confirm no reimplemented sync logic in updaters
grep -n 'ln -sf\|ln -s ' <repo-root>/scripts/cos-update.sh \
                        <repo-root>/scripts/auto-update-projects.sh
# Expected: no matches (updaters never create symlinks themselves)
```

---

## Steps the human must verify

1. **Git remote freshness.** `auto-update-projects.sh` runs from the source tree as it
   exists at the moment `post-merge` fires. For the ADR-001 fix to reach downstream
   projects, the change must be present in the source tree BEFORE the hook fires. Two
   sub-cases:

   - **Upstream push required.** If ADR-001 was committed locally but not pushed to
     the remote, projects that pull from that remote will NOT receive the fix until
     after the push. Verify: `git -C <repo-root>
     log --oneline origin/main..main | grep -i 'adr-001\|self-install\|skills'` —
     expected output: empty (fully pushed) or a list of local-only commits (push required).

   - **Downstream pull required.** Each machine running a separate clone of
     `luum-agent-os` (other users, other dev machines) must `git pull` before the
     post-merge hook can fire the mass update. The registry at
     `~/.cognitive-os/installations.json` is per-machine; there is no central
     orchestrator.

2. **Manual external-project update.** Users with projects installed via
   `install.sh --force` but whose OS source has NOT been git-pulled since ADR-001 must
   re-run `install.sh --force` to pick up `cos-init.sh`'s dual-install behavior.

3. **Registry coverage.** Projects installed from a different OS source directory
   (e.g., an old clone) will not be visible to the current source's
   `auto-update-projects.sh` — the filter at `auto-update-projects.sh:92-94` matches
   only installations whose `source` path equals the current `COS_SOURCE_DIR`. Users
   with multiple OS clones must run the updater from each.

4. **The `.cognitive-os/install-meta.json` version stamp.** The auto-updater skips
   projects where `version` in the registry equals the current OS version
   (line 138-141). If ADR-001 shipped WITHOUT a VERSION bump, the updater will skip
   projects that need the fix. Verify: `git -C <repo-root>
   log --oneline -- VERSION` — check whether VERSION was updated in the ADR-001 commit.

---

## Adversarial review

Per `rules/adversarial-review.md`, a review must produce at least one finding. The
tiered findings below cover maintainability and security gaps even where no functional
bug exists.

### [S3 SUGGESTION] `auto-update-projects.sh` pre-cleanup misses `.claude/skills/cos`

**Location**: `scripts/auto-update-projects.sh:184-187`
**What**: Pre-cleanup before `cos-init.sh` re-runs removes `.cognitive-os/skills/cos`
but not `.claude/skills/cos`. Skills deleted from the OS source will remain as orphans
in the driver path.
**Why**: Symmetry — kernel path is cleaned; driver path is not. Will accumulate
stale skill directories over time. Not blocking the ADR-001 fix but violates the
"clean before re-init" invariant that the existing code aims for.
**Recommendation**: Add `[ -d ".claude/skills/cos" ] && rm -rf .claude/skills/cos`
alongside line 186 in a follow-up change.

### [S2 CONCERN] `cos-update.sh` documentation conflates infra update with project update

**Location**: `docs/getting-started.md:195-210`; conceptual defect, script itself is
correct.
**What**: Docs describe `cos-update.sh` as the update mechanism after describing
`install.sh --force` as the "manual update of a single project." A user reading
quickly may run `cos-update.sh` inside an external project expecting skills/rules
to re-sync. They will NOT — the script exits with `cognitive-os.yaml not found` at
line 188 (pre-flight check), which is misleading about the actual scope (self-hosting
only).
**Why**: If a downstream user assumes `cos-update.sh` covers their project, they will
miss the ADR-001 fix until they discover `install.sh --force`. Increases support
surface.
**Recommendation**: Rename the docs section to "Cognitive OS self-hosting update
(infrastructure + rules)" or split the infrastructure-only steps (env + Docker) from
the sync step. Out of Cluster C scope; tracking suggestion only.

### [S2 CONCERN] Auto-updater hides per-project errors

**Location**: `scripts/auto-update-projects.sh:206`
**What**: `cos-init.sh` output is redirected to `/dev/null 2>&1`. Failures increment
the `failed` counter but the specific error message is discarded.
**Why**: If one project's `cos-init.sh` fails (permissions, partial disk, symlink
trap, etc.), the user sees only "FAILED — manual upgrade may be needed" and must
reproduce locally to diagnose. A mass update across 10+ projects with silent failures
makes triage labor-intensive.
**Recommendation**: Redirect stderr to a per-project logfile under
`~/.cognitive-os/auto-update-logs/<project_name>-<timestamp>.log` and include the
path in the failure message. Out of Cluster C scope; tracking suggestion only.

### [S4 QUESTION] Should `auto-update-projects.sh` verify the source working tree is clean?

**Location**: `scripts/auto-update-projects.sh` (entire file, no check present)
**What**: The script runs `cos-init.sh` from the source working tree. If the user
has uncommitted local modifications to `cos-init.sh` (mid-merge conflict, debug
edits), those unstaged changes WILL propagate to every registered project on the
next `git pull` via post-merge.
**Why**: A merge that leaves conflict markers in `cos-init.sh` would be silently
mass-installed across every COS project. Unlikely in practice (merge would fail
first) but worth a pre-flight `git diff --quiet scripts/cos-init.sh` check.
**Recommendation**: Human to decide whether to add a clean-tree check or document
the implicit "never pull with dirty tree" assumption. No action required for ADR-001.

---

## Acceptance criteria check

Per the task prompt:

1. **Both updaters audited with risk level + fix-applied status.**
   - `cos-update.sh`: LOW risk, N/A (no fix needed) — delegates to `self-install.sh`
     which already has ADR-001 fix.
   - `auto-update-projects.sh`: LOW risk, N/A (no fix needed) — delegates to
     `cos-init.sh` which already has ADR-001 fix.

2. **Propagation path documented.** See "Propagation path" section above — three paths
   (self-hosting, manual install, auto-update) each verified to cascade the fix.

3. **If updater bug found: fix applied + verification via grep.** No updater bug found.
   Updaters are correct delegators; the fix already lives in the delegatees
   (`self-install.sh` and `cos-init.sh`).

4. **Report exists at specified path.** This document, at
   `docs/architecture/harness-adoption-gap/scripts-audit-C-updaters.md`.

---

## Cross-references

- `docs/architecture/harness-adoption-gap/ADR-001-harness-skills-sync-path.md` — the
  decision record for the skills-path fix
- `docs/architecture/harness-adoption-gap/diagnosis.md` — root-cause analysis
- `docs/architecture/harness-adoption-gap/scripts-audit.md` — prior (general) scripts
  audit; this Cluster C report complements it with updater-specific depth
- `hooks/self-install.sh` — reference implementation of the fix (SYNC_DIRS entry
  `"skills|claude|tree|"` at line 38)
- `scripts/cos-init.sh` lines 218-256 — dual-install SKILL_DESTS logic
- `.git/hooks/post-merge` — the mechanism that fires `auto-update-projects.sh`
- `rules/supply-chain-defense.md` — context for the security caveats noted above
