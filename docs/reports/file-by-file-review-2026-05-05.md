# File-by-File Review — Cross-Branch / Cross-Worktree State

**Date**: 2026-05-05
**Status**: read-only review
**Branch inspected**: `session/41961ce2-paperclip-rejection-multi-surface` (HEAD: `aeb391b0`)
**Trigger**: Operator asked for file-level classification rather than commit-level after the cross-session collision incident (see `docs/reports/postmortem-cross-session-collision-2026-05-05.md`).

---

## TL;DR

- **Total files in scope**: ~115 (25 ADR files, 29 paperclip files, 11 manifest files, 18 hooks, 3 settings/config, 3 CHANGELOG/Makefile/docker, 9 untracked ADRs, 8 untracked lib-routing files, 9 recently-tombstoned ADRs)
- **Disposition counts**: KEEP 62 | DELETE 29 | RECOVER 9 | RECONCILE 4 | REVERT 7 | operator-decision-needed 13
- **Top 5 files needing operator decision**:
  1. `lib/skill_router.py` — diverged in both worktrees (session41 WIP adds profile-aware cache + `SkillRoutingIndexCache`; session50 WIP adds ADR-174 frontmatter routing; neither is committed; incompatible changes)
  2. `docs/adrs/ADR-172-multi-surface-ui-architecture.md` — exists as **accepted ADR** in session41 WIP but as a **tombstone** in session50 WIP
  3. `docs/adrs/ADR-174-auto-derived-primitive-routing.md` — committed in session41, but session50 has `ADR-174-tombstone.md` as untracked WIP claiming the same number
  4. `.claude/settings.json` — committed in session41 (stripped to 4 lines); session50 WIP carries its own divergent delta from `2aba0fe9`
  5. `manifests/skill-routing-coverage.yaml` — 267-line file added in session41 (committed), 701-line WIP version in current working tree; session50 WIP has its own version
- **Confirmed conflicts**: 4 (ADR-172, ADR-174/ADR-174b, `lib/skill_router.py`, `manifests/skill-routing-coverage.yaml`)
- **Aligned changes (safe)**: 29 paperclip deletions, 4 new routing hooks from commit 1, 9 tombstone ADRs from commit 3

---

## Methodology

All comparisons used git plumbing:
- `git diff --name-status <ref1> <ref2>` for file-set differences
- `git show <ref>:<path>` for content per branch
- `git ls-tree <ref> <dir>` for directory listings
- `md5sum` / `git hash-object` for content equality checks
- `git log --all --oneline --diff-filter=A/D -- <path>` for file history
- Session50 worktree inspected via `-C <session50-worktree>`

Branch HEAs cited:
- `main`: `9d7598dd` (release v0.26.0)
- `session/41961ce2`: `aeb391b0` (3 commits ahead of main)
- `session/50c35ce9`: `2aba0fe9` (1 commit **behind** main — it is the v0.26.0 parent)

---

## Per-Category Summary

### ADR files

| Disposition | Count |
|---|---|
| KEEP (committed, no conflict) | 12 |
| KEEP (new tombstones — deliberate, uncontested) | 6 (ADR-003/004/005/046/085 + ADR-043 deleted+replaced) |
| RECONCILE | 2 (ADR-172, ADR-174) |
| RECOVER | 3 (ADR-171, ADR-173, ADR-179 were tombstoned over slots that never had content; original content may be in agent JSONL) |
| REVERT (session41 modified main ADR) | 6 |
| Operator decision needed | 5 |

### Paperclip files

| Disposition | Count |
|---|---|
| DELETE (hooks, lib, scripts, package, infra) | 29 |
| Operator decision needed | 0 |

All 29 paperclip deletions are **aligned** across both session41 commits and represent intentional rejection of the surface. Safe to keep deleted.

### lib-routing files

| Disposition | Count |
|---|---|
| KEEP (committed in session41, absent on main) | 2 (skill_store.py, skill_lifecycle_promoter.py) |
| RECONCILE / operator-needed | 1 (skill_router.py — diverged in both WIPs) |
| RECOVER (untracked WIP only) | 8 (rule_router.py, routing_pattern_deriver.py, adr_router.py, hook_types.py, provider_profile.py, research_quality_advisor.py, session_coordination.py, validator_soak_evaluator.py) |

### Hooks

| Disposition | Count |
|---|---|
| DELETE (paperclip hooks, 6 from commit 2, 6 from commit 3) | 12 |
| KEEP (3 new skill-routing hooks from commit 1) | 3 (orchestrator-decision-trace.sh, skill-md-routing-validator.sh, skill-post-execution-analysis.sh, skill-router-prompt-suggest.sh) |
| RECOVER (untracked WIP only) | 6 (adr-relevance-suggest.sh, cross-session-coordination-guard.sh, promotion-proposer-weekly.sh, research-quality-validator.sh, rule-md-routing-validator.sh, rule-router-prompt-suggest.sh, validator-soak-weekly.sh) |

### Manifests

| Disposition | Count |
|---|---|
| KEEP (modified, paperclip refs stripped) | 9 |
| RECONCILE | 1 (skill-routing-coverage.yaml — 267-line committed vs 701-line WIP) |
| RECOVER (untracked WIP) | 3 (adr-routing-coverage.yaml, rule-routing-coverage.yaml, session-coordination-contract.yaml) |

### Settings / Config

| Disposition | Count |
|---|---|
| RECONCILE | 1 (.claude/settings.json — committed session41 version is drastically stripped) |
| KEEP | 1 (.codex/hooks.json — paperclip hooks removed) |
| KEEP | 1 (cognitive-os.yaml — modified) |

### Docs (CHANGELOG, Makefile, docker-compose)

| Disposition | Count |
|---|---|
| KEEP | 3 |

---

## File-by-File Matrix

### CATEGORY: Conflicts — Operator Decision Required

| Path | Category | State on `main` (9d7598dd) | State on `session/41961ce2` HEAD (aeb391b0) | State on `session/50c35ce9` HEAD (2aba0fe9) | State in WIP | Conflict? | Disposition | Operator decision? |
|---|---|---|---|---|---|---|---|---|
| `lib/skill_router.py` | lib-routing | present (sha e02cd2fd, 1188 lines) | modified (sha 007487fa) — profile-alias table + `SkillRoutingIndexCache` added in commit 1 | present (sha d6515291 — same as main) | modified — additional 185-line WIP diff on top of session41 HEAD (adds `_canonical_profile`, `_skill_md_checksum`, `SkillRoutingIndexCache` class); session50 WIP has 531-line diff adding ADR-174 frontmatter routing loader | YES — two independent WIP features that touch the same file from different angles | RECONCILE | yes |
| `docs/adrs/ADR-172-multi-surface-ui-architecture.md` | adr | absent | absent (added only in WIP, not committed) | absent | untracked — full ADR titled "Multi-Surface UI Architecture - CLI + Phoenix + Engram Cloud + Obsidian", status: accepted, supersedes: ADR-170 | YES — session50 WIP has `ADR-172-tombstone.md` claiming the same number as a reserved slot | RECONCILE | yes |
| `docs/adrs/ADR-174-auto-derived-primitive-routing.md` | adr | absent | present (committed in commit 1, sha added) | absent | committed (via session41) | YES — session50 WIP has `ADR-174-tombstone.md` as untracked, treating 174 as a reserved slot; session41 already committed ADR-174 as an accepted ADR | RECONCILE | yes |
| `docs/adrs/ADR-174b-prevention-followup.md` | adr | absent | absent | absent | untracked WIP only — extends ADR-174 with auto-generation and soak-driven promotion | YES — number collision with ADR-174; the "bis" suffix is non-standard | RECONCILE | yes |
| `manifests/skill-routing-coverage.yaml` | manifest | absent | present (committed in commit 1, 267 lines) | absent | modified — 701-line WIP version extends the committed file; session50 WIP also has an untracked version | YES — WIP version is 2.6x larger than committed; session50 parallel WIP | RECONCILE | yes |
| `.claude/settings.json` | settings | present (sha 360a8077, full hook config ~719 lines) | modified (sha eb904ac1, stripped to 4 lines — most hooks removed) | present (same sha as main — session50 is behind main) | committed (session41 version) — also has session50 WIP delta | YES — session41 committed a drastic strip of settings.json; session50 WIP independently modifies the same file | RECONCILE | yes |
| `docs/adrs/ADR-171-tombstone.md` | adr | absent | present (committed in commit 3) | absent | committed | YES — tombstone with title "Reserved architecture decision slot" implies ADR-171 was never written; but the operator's task description calls it a "newly committed-by-mistake" ADR, implying there was intended content | RECOVER | yes |
| `docs/adrs/ADR-173-tombstone.md` | adr | absent | present (committed in commit 3) | absent | committed | YES — same as ADR-171: slot is tombstoned as "reserved" suggesting original content was lost | RECOVER | yes |
| `docs/adrs/ADR-179-tombstone.md` | adr | absent | present (committed in commit 3) | absent | committed | YES — same pattern: "Reserved architecture decision" tombstone. Post-mortem mentions `ADR-179-rules-auto-derive-routing.md` as a named file that was lost | RECOVER | yes |
| `docs/adrs/ADR-175-research-quality-enforcement.md` | adr | absent | absent | absent | untracked WIP only | NO content conflict (only in session41 WIP), but ADR-175 has no committed counterpart | RECOVER | yes |
| `docs/adrs/ADR-178-openharness-primitive-adoption.md` | adr | absent | absent | absent | untracked WIP only | NO | RECOVER | yes |
| `docs/adrs/ADR-180-lifecycle-promotion-activation.md` | adr | absent | absent | absent | untracked WIP only | NO | RECOVER | yes |
| `docs/adrs/ADR-181-adr-relevance-suggester.md` | adr | absent | absent | absent | untracked WIP only | NO | RECOVER | yes |

---

### CATEGORY: Paperclip Deletions (all aligned — safe)

| Path | Category | State on `main` | State on `session/41961ce2` HEAD | State on `session/50c35ce9` HEAD | WIP | Conflict? | Disposition | Operator decision? |
|---|---|---|---|---|---|---|---|---|
| `hooks/paperclip-agent-status.sh` | hook | present (symlink) | deleted (commit 3) | present (symlink, same as main) | deleted | NO — consistent intent | DELETE | no |
| `hooks/paperclip-cost-stream.sh` | hook | present (symlink) | deleted (commit 3) | present (symlink) | deleted | NO | DELETE | no |
| `hooks/paperclip-sdd-sync.sh` | hook | present (symlink) | deleted (commit 3) | present (symlink) | deleted | NO | DELETE | no |
| `hooks/paperclip-squad-sync.sh` | hook | present (symlink) | deleted (commit 3) | present (symlink) | deleted | NO | DELETE | no |
| `hooks/paperclip-sync.sh` | hook | present (symlink) | deleted (commit 3) | present (symlink) | deleted | NO | DELETE | no |
| `hooks/paperclip-task-sync.sh` | hook | present (symlink) | deleted (commit 3) | present (symlink) | deleted | NO | DELETE | no |
| `hooks/_lib/paperclip-notify.sh` | hook | present | deleted (commit 2) | present | deleted | NO | DELETE | no |
| `lib/paperclip_client.py` | lib-routing | present (symlink, sha cc9d71744) | deleted (commit 3) | present (symlink) | deleted | NO | DELETE | no |
| `packages/ecosystem-tools/lib/paperclip_client.py` | paperclip | present | deleted (commit 2) | present | deleted | NO | DELETE | no |
| `packages/paperclip-integration/README.md` | paperclip | present | deleted (commit 2) | present | deleted | NO | DELETE | no |
| `packages/paperclip-integration/cos-package.yaml` | paperclip | present | deleted (commit 2) | present | deleted | NO | DELETE | no |
| `packages/paperclip-integration/hooks/_lib` | paperclip | present (symlink dir) | deleted (commit 3) | present | deleted | NO | DELETE | no |
| `packages/paperclip-integration/hooks/paperclip-agent-status.sh` | paperclip | present | deleted (commit 2) | present | deleted | NO | DELETE | no |
| `packages/paperclip-integration/hooks/paperclip-cost-stream.sh` | paperclip | present | deleted (commit 2) | present | deleted | NO | DELETE | no |
| `packages/paperclip-integration/hooks/paperclip-sdd-sync.sh` | paperclip | present | deleted (commit 2) | present | deleted | NO | DELETE | no |
| `packages/paperclip-integration/hooks/paperclip-squad-sync.sh` | paperclip | present | deleted (commit 2) | present | deleted | NO | DELETE | no |
| `packages/paperclip-integration/hooks/paperclip-sync.sh` | paperclip | present | deleted (commit 2) | present | deleted | NO | DELETE | no |
| `packages/paperclip-integration/hooks/paperclip-task-sync.sh` | paperclip | present | deleted (commit 2) | present | deleted | NO | DELETE | no |
| `packages/paperclip-integration/skills/paperclip-dashboard/SKILL.md` | paperclip | present | deleted (commit 2) | present | deleted | NO | DELETE | no |
| `skills/paperclip-dashboard/` | paperclip | present (skill dir) | deleted (commit 3) | present | deleted | NO | DELETE | no |
| `docs/paperclip-integration.md` | paperclip | present | deleted (commit 2) | present | deleted | NO | DELETE | no |
| `docs/reports/paperclip-integration-audit-2026-05-05.md` | report | present | deleted (commit 2) | present | deleted | NO — intentional purge | DELETE | no |
| `docs/reports/paperclip-live-smoke-2026-05-05.md` | report | present | deleted (commit 2) | present | deleted | NO | DELETE | no |
| `infra/paperclip/init-config.sh` | paperclip | present | deleted (commit 2) | present | deleted | NO | DELETE | no |
| `scripts/cos-paperclip-local.sh` | paperclip | present | deleted (commit 2) | present | deleted | NO | DELETE | no |
| `tests/behavior/test_paperclip_integration_complete.py` | test | present | deleted (commit 2) | present | deleted | NO | DELETE | no |
| `tests/integration/test_paperclip_local_daemon.py` | test | present | deleted (commit 2) | present | deleted | NO | DELETE | no |
| `tests/unit/test_paperclip_client.py` | test | present | deleted (commit 2) | present | deleted | NO | DELETE | no |
| `docs/adrs/ADR-043-paperclip-local-daemon.md` | adr | present (accepted ADR) | deleted (commit 2) + replaced by `ADR-043-tombstone.md` (commit 3) | present (same as main) | deleted+tombstoned | NO — deliberate rejection tombstone | DELETE+KEEP tombstone | no |

---

### CATEGORY: New lib-routing files (commit 1 — KEEP)

| Path | Category | State on `main` | State on `session/41961ce2` HEAD | State on `session/50c35ce9` HEAD | WIP | Conflict? | Disposition | Operator decision? |
|---|---|---|---|---|---|---|---|---|
| `lib/skill_store.py` | lib-routing | absent | present (committed commit 1) | absent | committed | NO | KEEP | no |
| `lib/skill_lifecycle_promoter.py` | lib-routing | absent | present (committed commit 1) | absent | committed | NO | KEEP | no |

---

### CATEGORY: New routing hooks (commit 1 — KEEP)

| Path | Category | State on `main` | State on `session/41961ce2` HEAD | State on `session/50c35ce9` HEAD | WIP | Conflict? | Disposition | Operator decision? |
|---|---|---|---|---|---|---|---|---|
| `hooks/orchestrator-decision-trace.sh` | hook | absent | present (committed commit 1) | absent | committed | NO | KEEP | no |
| `hooks/skill-md-routing-validator.sh` | hook | absent | present (committed commit 1) | absent | committed | NO | KEEP | no |
| `hooks/skill-post-execution-analysis.sh` | hook | absent | present (committed commit 1) | absent | committed | NO | KEEP | no |
| `hooks/skill-router-prompt-suggest.sh` | hook | absent | present (committed commit 1) | absent | committed | NO | KEEP | no |

---

### CATEGORY: Tombstone ADRs (commit 3 — KEEP, but see RECOVER note)

| Path | Category | State on `main` | State on `session/41961ce2` HEAD | State on `session/50c35ce9` HEAD | WIP | Conflict? | Disposition | Operator decision? |
|---|---|---|---|---|---|---|---|---|
| `docs/adrs/ADR-003-tombstone.md` | adr | absent (ADR-003 never on main) | present (commit 3) | absent | committed | NO | KEEP | no |
| `docs/adrs/ADR-004-tombstone.md` | adr | absent | present (commit 3) | absent | committed | NO | KEEP | no |
| `docs/adrs/ADR-005-tombstone.md` | adr | absent | present (commit 3) | absent | committed | NO | KEEP | no |
| `docs/adrs/ADR-046-tombstone.md` | adr | absent (ADR-046 never on main) | present (commit 3) | absent | committed | NO | KEEP | no |
| `docs/adrs/ADR-085-tombstone.md` | adr | absent (ADR-085 never on main) | present (commit 3) | absent | committed | NO | KEEP | no |
| `docs/adrs/ADR-171-tombstone.md` | adr | absent | present (commit 3) — title "Reserved architecture decision slot" | absent | committed | YES (content expected, see RECOVER section) | RECOVER | yes |
| `docs/adrs/ADR-173-tombstone.md` | adr | absent | present (commit 3) — title "Reserved architecture decision slot" | absent | committed | YES (content expected) | RECOVER | yes |
| `docs/adrs/ADR-179-tombstone.md` | adr | absent | present (commit 3) — title "Reserved architecture decision" | absent | committed | YES — post-mortem named this as `ADR-179-rules-auto-derive-routing.md`, implying it had real content | RECOVER | yes |

---

### CATEGORY: New ADR files (commit 1 — KEEP)

| Path | Category | State on `main` | State on `session/41961ce2` HEAD | State on `session/50c35ce9` HEAD | WIP | Conflict? | Disposition | Operator decision? |
|---|---|---|---|---|---|---|---|---|
| `docs/adrs/ADR-174-auto-derived-primitive-routing.md` | adr | absent | present (committed commit 1) | absent | committed — but session50 WIP has `ADR-174-tombstone.md` as untracked | YES — number collision with session50 | RECONCILE | yes |
| `docs/adrs/ADR-176-skillstore-and-analysis-trigger.md` | adr | absent | present (committed commit 1) | absent | committed | NO | KEEP | no |
| `docs/adrs/ADR-177-activate-skill-lifecycle-promotion-ladder.md` | adr | absent | present (committed commit 1) | absent | committed | NO | KEEP | no |

---

### CATEGORY: Modified ADRs (commits 2/3 — reference updates, KEEP)

These ADRs were modified to strip paperclip references or update status. No conflicts found vs session50 (which is behind main).

| Path | Modified in | Conflict? | Disposition | Operator decision? |
|---|---|---|---|---|
| `docs/adrs/ADR-009-package-architecture.md` | commit 2 | NO | KEEP | no |
| `docs/adrs/ADR-018-docker-to-pip-migration.md` | commit 2 | NO | KEEP | no |
| `docs/adrs/ADR-027.md` | commit 2 | NO | KEEP | no |
| `docs/adrs/ADR-042-valkey-local-daemon.md` | commit 2 | NO | KEEP | no |
| `docs/adrs/ADR-045-postgres-local-daemon.md` | commit 2 | NO | KEEP | no |
| `docs/adrs/ADR-091-headless-clustered-runtime-direction.md` | commit 2 | NO | KEEP | no |
| `docs/adrs/ADR-092-harness-skills-sync-path.md` | commit 2 | NO | KEEP | no |
| `docs/adrs/ADR-093-simplify-profiles.md` | commit 2 | NO | KEEP | no |
| `docs/adrs/ADR-161-remote-control-plane-and-provider-adapter-boundary.md` | commit 2 | NO | KEEP | no |
| `docs/adrs/ADR-162-task-lifecycle-interruption-question-worktree-pr-protocol.md` | commit 2 | NO | KEEP | no |
| `docs/adrs/ADR-169-dashboard-formal-demotion.md` | commit 2 | NO | KEEP | no |
| `docs/adrs/ADR-170-operator-cli-as-primary-ui-surface.md` | commit 2 | NO | KEEP | no |

---

### CATEGORY: Manifests (modified — KEEP, except skill-routing-coverage)

| Path | Category | State on `main` | State on `session/41961ce2` HEAD | WIP | Conflict? | Disposition | Operator decision? |
|---|---|---|---|---|---|---|---|
| `manifests/adr-closure-metadata.yaml` | manifest | present | modified (commit 2) | committed | NO | KEEP | no |
| `manifests/cos-instance-implementation-phases.yaml` | manifest | present | modified (commit 2) | committed | NO | KEEP | no |
| `manifests/cos-instance-profiles.yaml` | manifest | present | modified (commit 2) | committed | NO | KEEP | no |
| `manifests/hook-registration-classification.yaml` | manifest | present | modified (commit 2) | committed | NO | KEEP | no |
| `manifests/optional-hook-aliases.json` | manifest | present | modified (commit 2) | committed | NO | KEEP | no |
| `manifests/reduction-demotions.json` | manifest | present | modified (commit 2) | committed | NO | KEEP | no |
| `manifests/remote-control-plane-alternatives.yaml` | manifest | present | modified (commit 2) | committed | NO | KEEP | no |
| `manifests/runtime-hardcoding-allowlist.yaml` | manifest | present | modified (commit 2) | committed | NO | KEEP | no |
| `manifests/silent-failure-allowlist.yaml` | manifest | present | modified (commit 2) | committed | NO | KEEP | no |
| `manifests/task-lifecycle-schema.yaml` | manifest | present | modified (commit 2) | committed | NO | KEEP | no |
| `manifests/skill-routing-coverage.yaml` | manifest | absent | present (commit 1, 267 lines) | modified — WIP version has 701 lines; session50 WIP has own untracked version | YES | RECONCILE | yes |

---

### CATEGORY: Settings/Config

| Path | Category | State on `main` (9d7598dd) | State on `session/41961ce2` HEAD | State on `session/50c35ce9` HEAD (2aba0fe9) | WIP | Conflict? | Disposition | Operator decision? |
|---|---|---|---|---|---|---|---|---|
| `.claude/settings.json` | settings | present — full hook config ~719 lines (sha 360a8077) | modified (commit 2) — stripped to 4 lines (sha eb904ac1) | present — same sha as main (2aba0fe9 is behind main by 1 commit) | committed (stripped version) — session50 WIP adds own delta | YES — drastic stripping in session41 conflicts with session50's state which still has full hooks | RECONCILE | yes |
| `.codex/hooks.json` | settings | present (sha 7b31787d) | modified (commit 2) — paperclip hooks removed (sha adf1958d) | present (sha same as main) | committed | NO — deliberate paperclip purge | KEEP | no |
| `cognitive-os.yaml` | settings | present (sha 87d17b6e) | modified (commit 2) (sha 3e9cdc12) | present (sha same as main) | committed | NO | KEEP | no |

---

### CATEGORY: CHANGELOG / Makefile / docker-compose

| Path | Category | State on `main` | State on `session/41961ce2` HEAD | State on `session/50c35ce9` HEAD | WIP | Conflict? | Disposition | Operator decision? |
|---|---|---|---|---|---|---|---|---|
| `CHANGELOG.md` | docs | present | modified (commit 2) | present (same as main) | committed | NO | KEEP | no |
| `Makefile` | docs | present | modified (commit 2) — 12-line diff, paperclip targets removed | present (same as main) | committed | NO | KEEP | no |
| `docker-compose.cognitive-os.yml` | docs | present | modified (commit 2) — 125-line diff | present (same as main) | committed | NO | KEEP | no |

---

### CATEGORY: Untracked WIP lib-routing files (session41 working tree only)

| Path | Category | All branch states | WIP | Conflict? | Disposition | Operator decision? |
|---|---|---|---|---|---|---|
| `lib/rule_router.py` | lib-routing | absent everywhere | untracked | NO (unique to session41 WIP) | RECOVER (stage and commit or stash) | no |
| `lib/routing_pattern_deriver.py` | lib-routing | absent everywhere | untracked | NO | RECOVER | no |
| `lib/adr_router.py` | lib-routing | absent everywhere | untracked | NO | RECOVER | no |
| `lib/hook_types.py` | lib-routing | absent everywhere | untracked | NO | RECOVER | no |
| `lib/provider_profile.py` | lib-routing | absent everywhere | untracked | NO | RECOVER | no |
| `lib/research_quality_advisor.py` | lib-routing | absent everywhere | untracked | NO | RECOVER | no |
| `lib/session_coordination.py` | lib-routing | absent everywhere | untracked | NO | RECOVER | no |
| `lib/validator_soak_evaluator.py` | lib-routing | absent everywhere | untracked | NO | RECOVER | no |

---

### CATEGORY: Untracked WIP hooks (session41 working tree only)

| Path | Category | All branch states | WIP | Conflict? | Disposition | Operator decision? |
|---|---|---|---|---|---|---|
| `hooks/adr-relevance-suggest.sh` | hook | absent | untracked | NO | RECOVER | no |
| `hooks/cross-session-coordination-guard.sh` | hook | absent | untracked | NO | RECOVER | no |
| `hooks/promotion-proposer-weekly.sh` | hook | absent | untracked | NO | RECOVER | no |
| `hooks/research-quality-validator.sh` | hook | absent | untracked | NO | RECOVER | no |
| `hooks/rule-md-routing-validator.sh` | hook | absent | untracked | NO | RECOVER | no |
| `hooks/rule-router-prompt-suggest.sh` | hook | absent | untracked | NO | RECOVER | no |
| `hooks/validator-soak-weekly.sh` | hook | absent | untracked | NO | RECOVER | no |

---

### CATEGORY: Untracked WIP manifests (session41 working tree only)

| Path | Category | All branch states | WIP | Conflict? | Disposition | Operator decision? |
|---|---|---|---|---|---|---|
| `manifests/adr-routing-coverage.yaml` | manifest | absent | untracked | NO | RECOVER | no |
| `manifests/rule-routing-coverage.yaml` | manifest | absent | untracked | NO | RECOVER | no |
| `manifests/session-coordination-contract.yaml` | manifest | absent | untracked | NO | RECOVER | no |
| `manifests/provider-profiles.yaml` | manifest | absent | untracked | NO | RECOVER | no |

---

### CATEGORY: Untracked WIP scripts (session41 working tree only)

| Path | Category | All branch states | WIP | Conflict? | Disposition | Operator decision? |
|---|---|---|---|---|---|---|
| `scripts/cos-demotion-proposer` | other | absent | untracked | NO | RECOVER | no |
| `scripts/cos-promotion-proposer` | other | absent | untracked | NO | RECOVER | no |
| `scripts/cos-session-coordination` | other | absent | untracked | NO | RECOVER | no |
| `scripts/cos_demotion_proposer.py` | other | absent | untracked | NO | RECOVER | no |
| `scripts/cos_promotion_proposer.py` | other | absent | untracked | NO | RECOVER | no |
| `scripts/cos_session_coordination.py` | other | absent | untracked | NO | RECOVER | no |

---

## Confirmed Conflicts Requiring Operator Decision

### 1. `lib/skill_router.py`

**Divergence**: Three independent versions exist:
- `main` (9d7598dd): 1188 lines, baseline
- `session/41961ce2` HEAD (aeb391b0): adds profile-alias table + routing improvements (commit 1, sha `007487fa`)
- **Current WIP** (session41 working tree): 185 additional lines on top of HEAD — adds `_canonical_profile()`, `_skill_md_checksum()`, and `SkillRoutingIndexCache` class (profile/checksum-aware caching layer for service runtimes)
- **session50 WIP** working tree: 531-line diff from `2aba0fe9` (main parent) — adds ADR-174 frontmatter routing loader, entirely different feature branch

The session41 WIP and session50 WIP cannot be trivially merged as they add unrelated but overlapping internals. **Operator must decide**: accept session41's caching layer OR session50's frontmatter routing, OR both in a manual merge.

---

### 2. `docs/adrs/ADR-172-multi-surface-ui-architecture.md` vs `ADR-172-tombstone.md`

**Divergence**: 
- Session41 working tree: untracked `ADR-172-multi-surface-ui-architecture.md` — an **accepted** ADR defining multi-surface UI architecture (CLI, Phoenix, Engram Cloud, Obsidian), supersedes ADR-170
- Session50 WIP: untracked `ADR-172-tombstone.md` — treats ADR-172 as a "Reserved architecture decision slot"

These are mutually exclusive. The tombstone was presumably generated by an automated `adr_tombstone.py` run in session50 that didn't know session41 had already written a real ADR-172. **Operator must decide which is canonical for number 172.**

---

### 3. `docs/adrs/ADR-174-auto-derived-primitive-routing.md` vs `ADR-174-tombstone.md` (session50)

**Divergence**:
- Session41 commit 1: ADR-174 is a committed, accepted ADR ("Auto-Derived Primitive Routing for Skills and Rules")
- Session50 WIP: untracked `ADR-174-tombstone.md` claims 174 as a reserved slot

The session41 committed version should be authoritative since it predates session50's untracked file, but the session50 worktree operator needs to know to discard their tombstone. **Operator must confirm and discard session50's `ADR-174-tombstone.md`.**

---

### 4. `manifests/skill-routing-coverage.yaml`

**Divergence**: 
- Session41 committed (commit 1): 267 lines — baseline routing coverage
- Session41 WIP: 701 lines — significantly extended version (not yet committed)
- Session50 WIP: untracked version (line count not verified but same pattern)

The WIP extension is substantial (2.6x). Both worktrees hold diverging versions. **Operator must stage and commit the WIP extension in session41 before session50 makes it stale.**

---

### 5. `.claude/settings.json`

**Divergence**:
- `main` (9d7598dd): ~719-line full hook configuration
- Session41 HEAD (aeb391b0): stripped to ~4 lines (only bare JSON object) — paperclip hooks removed but most other hooks also dropped, likely unintentional overbreadth
- Session50 HEAD (2aba0fe9): same as `main` parent (full hooks intact)
- Session50 WIP: delta from session50's HEAD

This is a high-risk file. The stripping in session41 commit 2 (`a4bd126d`) removed non-paperclip hooks. **Operator must verify whether the stripping was intentional or an artifact of the auto-commit scope creep documented in the post-mortem.**

---

## Files That Align Across All Sources (Safe)

All 29 paperclip deletions are confirmed aligned across session41 commits with no session50 contention (session50 HEAD predates them, session50 WIP independently also deletes them).

The following new files from session41 commit 1 are unique to session41 with no conflicts:
- `lib/skill_store.py`, `lib/skill_lifecycle_promoter.py`
- `hooks/orchestrator-decision-trace.sh`, `hooks/skill-md-routing-validator.sh`, `hooks/skill-post-execution-analysis.sh`, `hooks/skill-router-prompt-suggest.sh`
- `docs/adrs/ADR-176-skillstore-and-analysis-trigger.md`, `docs/adrs/ADR-177-activate-skill-lifecycle-promotion-ladder.md`
- `manifests/adr-closure-metadata.yaml` (modified, paperclip refs stripped)
- All 12 modified ADRs (ADR-009, 018, 027, 042, 045, 091, 092, 093, 161, 162, 169, 170) — reference updates only
- `CHANGELOG.md`, `Makefile`, `docker-compose.cognitive-os.yml`, `cognitive-os.yaml`, `.codex/hooks.json`
- All tombstone ADRs for ADR-003, 004, 005, 043, 046, 085 — uncontested reserved slots

---

## Files Lost (Need Recovery from Non-Git Sources)

### ADR-171: Original content unknown

The tombstone `docs/adrs/ADR-171-tombstone.md` (committed in `aeb391b0`) has title "Reserved architecture decision slot" — the slot was never a real ADR in any tracked branch. However the post-mortem implies session41 was generating ADRs in this range. **Recovery source**: search agent JSONL files in `/private/tmp/claude-501/` for any draft with `adr: 171` in frontmatter. If not found, the tombstone is correct and no recovery is needed.

### ADR-173: Original content unknown

Same pattern as ADR-171. **Recovery source**: search agent JSONL in `/private/tmp/claude-501/` for `adr: 173`.

### ADR-179: `ADR-179-rules-auto-derive-routing.md`

Post-mortem explicitly names this file as lost. The tombstone's title "Reserved architecture decision" confirms it was overwritten. **Recovery source**: search agent JSONL for `adr: 179` or `rules-auto-derive-routing`. This is the highest-priority recovery since the post-mortem explicitly documented it.

### Untracked WIP ADRs (risk of loss on branch switch or stash)

The following 9 untracked files exist only in the session41 working tree and will be lost if the worktree is cleaned or the branch is switched without staging:
- `docs/adrs/ADR-172-multi-surface-ui-architecture.md`
- `docs/adrs/ADR-174b-prevention-followup.md`
- `docs/adrs/ADR-175-research-quality-enforcement.md`
- `docs/adrs/ADR-178-openharness-primitive-adoption.md`
- `docs/adrs/ADR-180-lifecycle-promotion-activation.md`
- `docs/adrs/ADR-181-adr-relevance-suggester.md`
- `docs/adrs/ADR-182-branch-ownership-lock.md`
- `docs/adrs/ADR-183-cross-session-event-log.md`
- `docs/adrs/ADR-184-manager-of-managers-daemon.md`

**Recovery**: Stage and commit immediately, or copy to a safe location before any worktree operations.

### Untracked WIP lib-routing files (8 files)

`lib/rule_router.py`, `lib/routing_pattern_deriver.py`, `lib/adr_router.py`, `lib/hook_types.py`, `lib/provider_profile.py`, `lib/research_quality_advisor.py`, `lib/session_coordination.py`, `lib/validator_soak_evaluator.py`

These exist only in the session41 working tree. **Recovery**: Stage and commit, or stash with a named stash (`git stash push -u -m "session41-wip-lib-routing"`).

---

## Trust Report

- **Uncertainty 1**: Some content comparisons were SHA-based; subtle whitespace or comment-only changes may not be flagged as "modified" where the diff exists but is trivial.
- **Uncertainty 2**: The conflict-vs-aligned classification is heuristic; some flagged conflicts (particularly `.claude/settings.json`) may resolve trivially once the operator confirms the stripping was intentional.
- **Uncertainty 3**: The recovery instructions for ADR-171, ADR-173, and ADR-179 assume the agent JSONL files at `/private/tmp/claude-501/` remain accessible during this session; tmp files are not guaranteed to persist across reboots.
- **Uncertainty 4**: Session50's worktree state was inspected via `-C` to the secondary worktree path; the untracked files there were enumerated but their full content was not diff'd against session41's versions in all cases.

---

## Sources

```
git diff --name-status 9d7598dd aeb391b0         # session41 HEAD vs main
git diff --name-status 9d7598dd 2aba0fe9         # session50 HEAD vs main
git diff --name-status 9d7598dd 937d0ece         # commit 1 vs main
git diff --name-status 937d0ece a4bd126d         # commit 2 vs commit 1
git diff --name-status a4bd126d aeb391b0         # commit 3 vs commit 2
git status --porcelain                           # WIP in session41 working tree
git -C <session50-path> status --porcelain       # WIP in session50 working tree
git show <ref>:<path>                            # per-branch content checks
git ls-tree <ref> <dir>/                         # directory listings per branch
md5sum / git hash-object --stdin                 # content equality checks
```

Branch HEAD SHAs:
- `main`: `9d7598dd`
- `session/41961ce2-paperclip-rejection-multi-surface`: `aeb391b0`
- `session/50c35ce9-remove-paperclip-multi-surface`: `2aba0fe9` (1 commit behind `main`)
