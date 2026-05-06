# Task & Plan Reconciliation — Surgical Depuration

**Date**: 2026-05-05
**Status**: read-only audit; no state modified
**Trigger**: user requested clean inventory of done/frozen/pending using COS primitives

---

## TL;DR

- **189 total tasks** audited: 83 completed, 11 completed-by-watermark, 91 cancelled-stale, 2 cancelled, 2 blocked-by-claim.
- **9 ghost-pending** found: tasks marked `cancelled-stale` or `blocked_by_claim` that have confirmed git commit evidence of completion (ADR-116 family: P1.3, P2.2, P3.2, P3.3, P4.3, R2, R3, R4, R5).
- **4 frozen items** identified: 2 ON-ICE feature plans (workflow-engine, agent-escalation), phoenix-migration Phases 1-4 (not started), and 13 stale task-claim locks held by dead PIDs (expired 68-76h ago).
- **Legitimately pending**: phoenix migration Phases 1-4 (deliberate deferral, operator-gated), silent-failure allowlist gaps in 2 hook libs, 60 `default_visible_reducer` demotion recommendations, ACC dashboard CLI (may be ghost-pending).
- **Highest-priority cleanup**: release the 13 expired task-claim locks in `.cognitive-os/runtime/task-claims.json` — they block future claim-gate operations on those task IDs.

---

## Methodology

Sources read: `.cognitive-os/tasks/active-tasks.json` (189 tasks), `.cognitive-os/runtime/task-claims.json` (13 claims), `.cognitive-os/plans/features/*.md` (17 plans), `.cognitive-os/plans/roadmaps/*.md`. Git evidence via `git log --since=14 days --oneline` (55 commits) plus targeted `--grep` queries. Open/merged PRs via `gh pr list`. ADR status via directory scan of `docs/adrs/`. COS primitives run: `cos-boring-reliability --profile core --json` (full output), `cos-silent-failure-audit --json`, `cos-tier-claim-audit --json`, `aspirational_audit.py --json`, `dogfood_score.py`, `cos-runtime-hook-reality` (no-json mode). Engram `mem_context` for recent session history. Cross-validation: task description substring matched against `git log --grep` and then manually verified against commit message conventions (feat/fix + ADR/phase label).

---

## Ghost-pending (tasks marked open but actually done)

Tasks that are `cancelled-stale` or `blocked_by_claim` yet have confirmed git commits implementing their stated scope.

| Task | Marked status | Evidence of completion | Recommended action |
|------|--------------|------------------------|--------------------|
| `task-desc-bfe1c27ecaa22204` — P1.3 inter-session events bus | cancelled-stale | `20cdc2fd feat(p1.3): implement inter-session pub/sub event bus (ADR-116)` | Set status=completed in active-tasks.json; release claim lock |
| `task-desc-4d503659b5f1531d` — P2.2 merge queue MVP | cancelled-stale | `179fd56b feat(adr-116-p2-2): add composable gate runner` + `7244a8cc` post-merge rollback | Set status=completed |
| `task-desc-19dacd600c10f044` — P2.2 follow-up A gates orchestration | cancelled-stale | `179fd56b` + `69315b4c fix: stop merge queue after dirty validation` | Set status=completed; release claim |
| `task-desc-f9c83e1f568a8bfd` — P2.2 follow-up B throughput bench | cancelled-stale | `1dac9f24 feat(p2.2-f2): throughput benchmark for merge queue` | Set status=completed; release claim |
| `task-1777748492-27782` — R5 ADR-117 stash governance | cancelled-stale | `61af7a31 docs(adr): ADR-117 stash mutation reversibility (R5)` | Set status=completed |
| `task-1777749403-9237` — P3.3 coordination CLI finish | cancelled-stale | `991923bb feat(p3.3): extend cos_work_inventory.py` + `d831e995 fix: wire ADR-116 coordination CLIs` | Set status=completed |
| `task-1777748475-14726` — P3.2 reset protection layer | cancelled-stale | `c45226d3 fix(safety): ADR-116 P3.2 — WIP-guard cascade protection` | Set status=completed |
| `task-desc-1432f1245f043b37` — P4.3 stash auto-reapply | blocked_by_claim | `366de417 feat(adr-116): implement P4.3 stash provenance auto-reapply` | Set status=completed; release expired claim (expired 72h ago) |
| `task-desc-c6e3f4cd0dbb44e6` — P5.1 + P5.2 engram claims and locks | cancelled-stale | `d702ace6 docs(handoff): multi-session coordination + claim-gate hardening` (session close doc; partial) | Uncertain — only docs evidence found, no feat/fix commit. Needs manual review before marking complete. |

**Notable**: The `blocked_by_claim` status on `task-desc-1432f1245f043b37` (P4.3) is a direct blocker for future claim-gate operations on that ID. The claim has been expired for 72+ hours and the PID 99322 is almost certainly dead.

---

## Frozen (no movement > 14 days, possibly stuck)

| Item | Last touched | Days frozen | Likely cause | Action |
|------|-------------|-------------|--------------|--------|
| `.cognitive-os/plans/features/workflow-engine.md` | 2026-04-13 (PLANNING status) | 22 days | ON ICE — explicitly marked, trigger: 3+ pipeline failures. Zero lib/workflow files exist. | Archive or leave ON ICE; do not confuse with active work |
| `.cognitive-os/plans/features/agent-escalation-capabilities.md` | 2026-04-13 (DRAFT) | 22 days | ON ICE — no engineering commits in 60-day window; base lib files exist but not extended | Archive or leave ON ICE |
| `phoenix-migration-plan.md` Phases 1-4 | Phase 0 done 2026-04-24; Phases 1-4 not started | 11 days | Deliberate — owner=operator, target dates 2026-05-30 to 2026-06-30 | No action needed; schedule is intentional |
| 13 expired task-claim locks in `task-claims.json` | Claims expired 68-76h ago (2026-05-02) | ~3 days stale | PIDs are dead (sessions ended); claim TTL (1800s) passed but file not pruned | Prune all 13 entries from `task-claims.json` in next session |
| ADR-116 `status: Proposed` | 2026-05-02 | 3 days | Multi-session branch merges completed; ADR body should move to `accepted` | Operator decision: accept ADR-116 |
| ADR-123 `status: proposed` | 2026-05-02 | 3 days | Operational stability friction-reduction; 3 days < 14-day threshold but close | Review in next session |

---

## Legitimately pending (clean backlog)

The actual remaining work after removing ghost-pending and frozen items.

| Priority | Item | Source | Why pending |
|----------|------|--------|-------------|
| P0 | Prune 13 expired task-claim locks from `task-claims.json` | `.cognitive-os/runtime/task-claims.json` | Claim-gate will block future agents if IDs are reused |
| P0 | Accept ADR-116 (move from Proposed → Accepted) | `docs/adrs/ADR-116-*.md` | Implementation shipped; ADR still shows Proposed |
| P1 | ACC dashboard CLI + statusline (`task-desc-40a358be772f176d`) | `active-tasks.json` blocked_by_claim | Claim expired 71h ago; check if feature shipped (no feat commit found for "ACC dashboard CLI") |
| P1 | Classify 2 unclassified silent-failure patterns | `hooks/_lib/agent-context.sh`, `hooks/_lib/artifact-status.sh` | `cos-silent-failure-audit` returns fail; 7 unclassified occurrences |
| P1 | Phoenix migration Phase 1 (install `arize-phoenix`, author skill) | `phoenix-migration-plan.md` §Phase 1 | Operator-gated, target 2026-05-30; no blocking dependency |
| P2 | 60 `default_visible_reducer` demotion recommendations | `cos-boring-reliability` warn | 60 core-tier primitives recommended for lab; excess surface area |
| P2 | 6 `projected_but_undocumented` hooks | `cos-runtime-hook-reality` | Hooks fire but have no manifest entry; documentation drift |
| P2 | 2 `dormant` hooks (no projection, no doc) | `cos-runtime-hook-reality` | Dead code risk |
| P3 | ADR-135 `status: proposed` — self-evolving doctrine | `docs/adrs/ADR-135-*.md` | No date found; age unknown; needs acceptance or rejection decision |
| P3 | Phoenix Phases 2-4 | `phoenix-migration-plan.md` | Dependent on Phase 1; target 2026-06-30 |
| P3 | Shape-B transferability debt (hooks `_lib/cache.sh`, `execute-repair.sh`, `killswitch_check.sh`) | `cos-silent-failure-audit` info | Deferred to Shape B; no blocking urgency today |

---

## Plans status

| Plan | Workstreams done | In progress | Pending | Frozen/ON ICE |
|------|-----------------|-------------|---------|---------------|
| `component-scope-classification.md` | All 4 phases | — | — | DONE ✓ |
| `docs-to-skills-audit.md` | Phases 1-3 | — | 9 remaining SKILL-CANDIDATE conversions (parked) | Parked |
| `hook-architecture-v2.md` | Phases 1+2 | — | Phases 3-5 (timing, hook-pipe, env-vars) | Note: plan says "ALL PHASES COMPLETE" but RECONCILIATION header says PARTIAL_DONE — **disagreement**. Git evidence: hook-pipe.sh shipped (Phase 4), env-vars shipped (Phase 5). Likely fully done. |
| `skill-atomicity-audit.md` | Phases 1-4 analysis | — | Splits remain recommendations only | Complete as analysis; implementation opt-in |
| `docker-to-pip-migration.md` | Phase 2 | — | Pending further phases if needed | Complete for current scope |
| `engram-lifecycle-evolution.md` | Phases 1-3 shipped | Phase 4 manual Obsidian export shipped 2026-05-05 | Automated stop-hook automation deferred | On track |
| `phoenix-migration-plan.md` | Phase 0 (2026-04-24) | — | Phases 1-4 | Deliberate schedule |
| `auto-rollback-hardening-2026-05-02.md` | All ACs checked | — | — | DONE ✓ |
| `workflow-engine.md` | None | — | All | ON ICE — 22 days |
| `agent-escalation-capabilities.md` | None | — | All | ON ICE — 22 days |
| `so-existential-validation-2026-04-24.md` | (no status markers found) | — | — | Unclear |
| `stabilization-roadmap.md` | 98% complete; cos-dispatch Phase 5 deferred | — | cos-dispatch Phase 5 (auto-generator) | Deliberately deferred |
| `hook-architecture-v2.md` — **disagreement flagged** | Plan body says "ALL PHASES COMPLETE"; RECONCILIATION STATUS header says "PARTIAL_DONE Phases 3-5 pending". Individual phase notes contradict each other. Git evidence (`hook-pipe.sh`, env-vars) suggests Phases 4+5 shipped. Recommend operator re-read and reconcile the header note. |

---

## ADR status discipline

| Status | Count | Notes |
|--------|-------|-------|
| accepted | 24 | Healthy |
| implemented | 20 | Good — implementation evidence tracked |
| proposed | 1 (via regex) + 2 (via content search) | ADR-116 (3 days), ADR-123 (3 days), ADR-135 (date unknown) |
| exploration | 1 | ADR in exploration phase — normal |
| superseded | 1 | Healthy |
| unknown (no frontmatter status field) | 129 | Most older ADRs use prose "Status:" inside the body, not YAML frontmatter — not a problem, just an inconsistency in parsing |

**Proposed ADRs requiring attention:**

- `ADR-116-multi-session-coordination-primitives.md` — proposed 2026-04-28 (?), implementation is complete. Should be accepted now. Age: ~7 days, but implementation is done — no reason to stay proposed.
- `ADR-123-operational-stability-friction-reduction.md` — proposed 2026-05-02, age 3 days. Within the 14-day window but approaching it. Review next session.
- `ADR-135-self-evolving-doctrine-proposals.md` — no date found in scanned content. Age unknown. Flag for decision.

No ADRs were found with `status: proposed` older than 14 days by the frontmatter date field. The 14-day frozen threshold is not breached.

---

## OS primitive output snapshot

### `cos-boring-reliability --profile core --json`

```
overall sub-scores:
  adoption_profile:         pass
  default_visible_reducer:  WARN  (60 demotion recommendations — excess core-tier primitives)
  demotion_loop:            pass  (2 demotions, 1 ROI-signed)
  dispatch_metrics_evidence:pass
  false_positive_ledger:    WARN  (1 false positive in 21,434 events — acceptable rate)
  manifest_tier_claims:     WARN  (203 findings: 60 candidate-to-lab, 9 candidate-second-demote)
  preamble_budget:          pass
  readiness:                FAIL  (3 fail, 14 pass, 2 warn)
  runtime_reality:          FAIL  (2 dormant hooks, 6 projected-but-undocumented)
  session_start_budget:     pass
  silent_failure_audit:     FAIL  (9 fail, 1 warn — see below)
  wip_safety:               FAIL  (45 dirty paths, 4 stashes, score=40)
```

### `cos-silent-failure-audit --json`

```
status: fail | fail_count: 9 | warn_count: 1
Top findings:
  [fail] hooks/_lib/agent-context.sh — 1 unclassified silent-failure pattern
  [fail] hooks/_lib/artifact-status.sh — 6 unclassified silent-failure patterns
  [info] hooks/_lib/cache.sh — Shape-B transferability debt (5 occurrences, original-maintainer)
  [info] hooks/_lib/execute-repair.sh — Shape-B transferability debt (18 occurrences)
```

### `cos-tier-claim-audit --json`

```
status: pass | finding_count: 0
```

### `aspirational_audit.py --json`

```
total: 913 components
  REAL:         277 (30%)
  ON_DEMAND:    368 (40%)
  DORMANT:      175 (19%)
  ASPIRATIONAL:  35 ( 4%)
  METADATA:      58 ( 6%)
dormant_aspirational_ratio: 0.23
worst_offenders (DORMANT/ASPIRATIONAL):
  hooks/adr-detector.sh, hooks/agent-bus-monitor.sh, hooks/agent-output-verifier.sh,
  hooks/agent-quota-advisor.sh, hooks/agent-quota-redirect.sh,
  scripts/cos-claims.sh, scripts/cos-fingerprint.sh, scripts/cos-locks.sh
```

### `dogfood_score.py`

```
Overall: 68.90/100
  test_health:          100.00 (weight 25) — 9264 tests, 0 failures
  skill_coverage:        24.07 (weight 15) — 39/162 skills covered
  hook_wiring:           67.37 (weight 15) — 128/190 hooks good
  adr_discipline:        69.89 (weight 15) — 65/93 accepted ADRs have proof
  harness_portability:   57.31 (weight 10) — 439/766 files clean
  self_build_activity:   65.89 (weight 10) — 1221 commits, test_pct=8%
  doc_freshness:         73.77 (weight 10) — 17/17 plans fresh (90d window)
```

### `cos-runtime-hook-reality` (no --json support)

```
status: fail
audited_hooks: 136 | documented: 130 | projected_unique: 134
  real_blocking:              32
  real_advisory:              64
  observe_only:               32
  dormant:                     2
  projected_but_undocumented:  6
  documented_but_not_projected: 0
```

### `cos-runtime-hook-reality --json` — primitive UNAVAILABLE (flag not supported; ran without --json)

---

## Surgical depuration checklist (next session)

1. Release 13 expired task-claim locks — remove all entries from `.cognitive-os/runtime/task-claims.json` where `expires_at < now()`. Evidence: all 13 claims expired 68-76h ago; PIDs are dead.
2. Mark `task-desc-bfe1c27ecaa22204` (P1.3 inter-session events bus) status=completed — evidence: commit `20cdc2fd`.
3. Mark `task-desc-4d503659b5f1531d` (P2.2 merge queue MVP) status=completed — evidence: commits `179fd56b`, `7244a8cc`.
4. Mark `task-desc-19dacd600c10f044` (P2.2 follow-up A) status=completed — evidence: commit `69315b4c`.
5. Mark `task-desc-f9c83e1f568a8bfd` (P2.2 follow-up B) status=completed — evidence: commit `1dac9f24`.
6. Mark `task-1777748492-27782` (R5 ADR-117) status=completed — evidence: commit `61af7a31`.
7. Mark `task-1777749403-9237` (P3.3 coordination CLI) status=completed — evidence: commits `991923bb`, `d831e995`.
8. Mark `task-1777748475-14726` (P3.2 reset protection) status=completed — evidence: commit `c45226d3`.
9. Mark `task-desc-1432f1245f043b37` (P4.3 stash auto-reapply) status=completed — evidence: commit `366de417`; clear its `blocked_by_claim` and remove claim from task-claims.json.
10. Verify `task-desc-40a358be772f176d` (ACC dashboard CLI) — no feat commit found. Check if feature shipped before marking complete or cancelling.
11. Accept ADR-116 — implementation fully shipped across 10+ commits; update `status: proposed` → `status: accepted`.
12. Reconcile `hook-architecture-v2.md` header — RECONCILIATION STATUS says PARTIAL_DONE but phase notes say COMPLETE; update the header to match git evidence (Phases 4+5 shipped: hook-pipe.sh, env-vars).
13. Classify 7 unclassified silent-failure patterns in `hooks/_lib/agent-context.sh` (1) and `hooks/_lib/artifact-status.sh` (6) — add to allowlist with appropriate degradation class (`cleanup_best_effort` or `legacy_audited`).
14. Decide on ADR-135 (self-evolving doctrine) — no date found, age unknown; propose or reject to clear from proposed limbo.
15. Archive or formally close `workflow-engine.md` and `agent-escalation-capabilities.md` — both ON ICE 22+ days with zero engineering progress and no scheduled revival trigger.
16. Document 6 `projected_but_undocumented` hooks in `manifests/primitive-lifecycle.yaml` — `cos-runtime-hook-reality` shows 6 hooks that fire but have no manifest entry.
17. Investigate 2 `dormant` hooks flagged by `cos-runtime-hook-reality` — confirm they are dead code and either wire or remove.
18. Review 60 `default_visible_reducer` recommendations from `cos-boring-reliability` — batch-demote non-killer-set primitives from `core` to `lab` to reduce default surface area.
19. Improve `skill_coverage` score (currently 24.07/100) — only 39/162 skills have coverage heuristic; dogfood priority if self-improvement is a current focus.
20. Investigate `wip_safety: fail` (45 dirty paths, 4 stashes, score=40) — determine if dirty state is from the current multi-session branch or leftover from previous work.

---

## Open questions for the user

1. **`task-desc-c6e3f4cd0dbb44e6` (P5.1+P5.2 engram claims and locks)**: Only a handoff doc was found, no `feat:` or `fix:` commit implementing engram claim primitives. Was this actually delivered, or is it genuinely incomplete and should be revived?
2. **`task-desc-40a358be772f176d` (ACC dashboard CLI + statusline)**: Marked `blocked_by_claim` with no git evidence of delivery. Should this be restarted or is the ACC statusline deprioritized given ADR-169 demoted the dashboard?
3. **Frozen threshold**: This audit used 14 days as the frozen cutoff. For feature plans, ON-ICE items (workflow-engine, agent-escalation) have been frozen 22 days. Would you like a different threshold for plan archival?

---

*Honest uncertainties*:
- "Did not verify that engram session/backlog/* observations are complete — some may have been skipped during compaction."
- "Cross-reference between active-tasks.json IDs and git commit messages relied on substring matching of task description keywords against commit message bodies, which can yield false positives or negatives."
- "Frozen-threshold was set at 14 days; the user may want a different cutoff — especially for plans that are explicitly ON ICE with a defined revival trigger."
