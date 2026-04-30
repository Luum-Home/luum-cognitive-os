# ADR-079 — CORE_RULES applies to self-hosting mode

<!-- SCOPE: OS -->

**Status**: Accepted  
**Date**: 2026-04-30  
**Author**: Matias Nahuel Améndola

---

## Status

Accepted.

## Context

ADR-074 (Tier-0 Learning Loop Closure) introduced a two-stage rules-loading
architecture:

- **Stage 1 (SessionStart)**: only `CORE_RULES` are symlinked into
  `.claude/rules/cos/` and loaded into agent context.
- **Stage 2 (on-demand)**: individual rule bodies flow in via `[ref-key]`
  expansion in `lib/ref_key_loader.py`.

Commit `991b24a` (perf: drop redundant CORE_RULES entries) reduced `CORE_RULES`
from 16 files to a single entry: `RULES-COMPACT.md`.  The compact index is the
Stage-1 entry point; all other rule bodies arrive on-demand via Stage 2.

This patch saves **~19K tokens per SessionStart** for client projects.  However,
`hooks/self-install.sh` contained a hard-coded override:

```bash
if [ "$IS_SELF_HOSTING" = "true" ]; then
  EFFICIENCY_PROFILE="full"          # → SYNC_ALL_RULES=true
fi
```

When running inside the `luum-agent-os` repo itself (self-hosting), this forced
`EFFICIENCY_PROFILE=full`, which bypassed `CORE_RULES` and symlinked every
non-excluded rule file.  The result: the SessionStart savings from commit
`991b24a` were **silently a no-op** for all COS development work.

### Why the override existed

The override predates the CORE_RULES reduction.  When `CORE_RULES` contained 16
rules, "full" vs "default" was a meaningful distinction.  Once `CORE_RULES`
collapsed to 1 entry, the override became a regression that re-loads 16 extra
rule files on every COS development SessionStart.

### Audit findings

Running `wc -c` on the 16 extra rule files currently loaded in self-hosting:

| File | Chars | ~Tokens |
|---|---|---|
| ROADMAP.md | 7,199 | ~1,800 |
| acceptance-criteria.md | 4,635 | ~1,159 |
| adaptive-bypass.md | 4,508 | ~1,127 |
| agent-quality.md | 9,065 | ~2,266 |
| bash-naming.md | 3,068 | ~767 |
| closed-loop-prompts.md | 8,917 | ~2,229 |
| credential-management.md | 1,888 | ~472 |
| definition-of-done.md | 5,764 | ~1,441 |
| error-learning.md | 5,836 | ~1,459 |
| lane-taxonomy.md | 4,421 | ~1,105 |
| model-routing.md | 4,614 | ~1,154 |
| phase-aware-agents.md | 5,661 | ~1,415 |
| python-naming.md | 3,977 | ~994 |
| result-management.md | 5,066 | ~1,267 |
| token-economy.md | 2,909 | ~727 |
| trust-score.md | 5,590 | ~1,398 |
| **Total** | **83,118** | **~20,779** |

All 16 are already referenced via `[ref-key]` markers in `RULES-COMPACT.md` and
expand on-demand via Stage 2.  Loading them at Stage 1 is pure duplication.

---

## Decision

1. **Remove the `IS_SELF_HOSTING → EFFICIENCY_PROFILE=full` override** from
   `hooks/self-install.sh`.  The same default-profile logic (read from
   `cognitive-os.yaml`, fall back to `"default"`) now applies to all projects,
   including the self-hosting repo.

2. **Add `COS_SYNC_ALL_RULES=1` opt-in**.  Developers who need every
   non-excluded rule symlinked locally (e.g., for harness validation, full
   IDE discovery) can set `COS_SYNC_ALL_RULES=1` in their shell environment.
   The opt-in is evaluated after config-file reading:
   ```bash
   if [ "${COS_SYNC_ALL_RULES:-0}" = "1" ]; then
     EFFICIENCY_PROFILE="full"
   fi
   ```

3. **Update `test_self_hosting_always_full`** → renamed
   `test_self_hosting_detects_but_no_longer_forces_full`.  The test now
   verifies:
   - `IS_SELF_HOSTING` detection is still present.
   - The old `IS_SELF_HOSTING → full` force is absent.
   - `COS_SYNC_ALL_RULES` opt-in is present.

---

## Consequences

### Positive

- **–~20,779 tokens per COS development SessionStart** (83 KB of rule content
  no longer loaded at Stage 1).
- Parity with client deployments: the COS development experience now matches
  what clients see, making token-budget claims verifiable during development.
- `test_claude_md_diet.py::TestSymlinkCountAfterInstall::test_rules_symlink_count_under_50`
  now passes without special-casing self-hosting (17 symlinks → 1 after next run).

### Negative / Trade-offs

- Developers who relied on all rule files being pre-symlinked locally must set
  `COS_SYNC_ALL_RULES=1`.  This is documented here and in the code comment.
- The `EFFICIENCY_PROFILE="full"` string is still present in the file (inside
  the `COS_SYNC_ALL_RULES` branch), so grep-based checks will still find it.

### Risks

- Downstream automation outside this repo that silently depends on
  `.claude/rules/cos/` having all 17 non-excluded rule symlinks may break.
  Mitigation: the 17-symlink set was already the post-exclusion result of
  `SYNC_ALL_RULES=true`; any such automation should have been testing against
  the **config-driven** set, not a hardcoded count.

---

## Migration

No action required for client projects (they were never affected by the override).

For COS developers:
- The next `hooks/self-install.sh` run (triggered by SessionStart) will reduce
  `.claude/rules/cos/` from 17 symlinks to 1 (`RULES-COMPACT.md`).
- To restore the full set locally: `COS_SYNC_ALL_RULES=1 bash hooks/self-install.sh`.

---

## Cross-references

- ADR-074: Tier-0 Learning Loop Closure (two-stage loading architecture)
- ADR-075: Stage-2 selective expansion (`[ref-key]` tier filtering)
- Commit `991b24a`: dropped 15 redundant CORE_RULES entries for client projects
- `hooks/self-install.sh` lines 253–270 (IS_SELF_HOSTING detection + opt-in)

## Alternatives rejected

- **Keep self-hosting permanently forced to full profile**: Rejected because it
  hides the real client-project SessionStart budget and makes token savings
  unverifiable while dogfooding COS.
- **Remove full-rule sync completely**: Rejected because maintainers still need
  an explicit `COS_SYNC_ALL_RULES=1` escape hatch for projection/debug sessions.
- **Special-case only this repository by path**: Rejected because absolute or
  repository-specific path logic would violate portability and consumer-project
  hygiene.

## Verification

```bash
python3 -m pytest tests/behavior/test_claude_md_diet.py -q --tb=short
python3 -m pytest tests/integration/test_consolidation_external.py -q --tb=short
```
