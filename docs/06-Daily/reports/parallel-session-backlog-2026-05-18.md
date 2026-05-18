# Parallel-session backlog — 2026-05-18

> Self-contained task briefs for distributing work across multiple
> Cognitive OS sessions / operators / agents. Each item lists what to
> read first, the bounded scope, acceptance, and which other items
> depend on it. Group by "wave" only for narrative; items inside a
> wave are independent unless explicitly noted.

## How to use this doc

For each session you spin up, pick one item, paste the brief into the
new orchestrator, and run. The "Read first" list is the minimum
context to load before starting; the orchestrator should not need to
guess anything else.

All items assume: branch is `main`, ~38 commits ahead of origin, no
push without operator OK; commits land directly on `main` with
`COS_ALLOW_MAIN_BRANCH_WRITE=1 git commit --only -F /tmp/msg.txt -- path`.
See `docs/06-Daily/reports/session-2026-05-18-multi-wave.md` section
"Recurring blockers" for the full hook gauntlet.

---

## WAVE 5 — Big plan slices (1 plan per session)

### S1. ADR-121 Foundation Hardening Phase 3 — file/domain/registry claim ledger
- **Read first**: `docs/02-Decisions/adrs/ADR-121*.md` §Phase 3, `lib/task_claim_ledger.py`, `scripts/cos_task_claims.py`, `tests/unit/test_claim_ledger_coherence.py`.
- **Scope**: ~1 session (~2h).
- **Deliverable**: extend the claim ledger schema to track files / domains / registry entries per claim, plus crash-symmetry tests in `tests/integration/`. Plan acceptance line 113.
- **Blockers**: none.

### S2. ADR-121 Phase 4 — guard maturity rollout
- **Read first**: ADR-121 §Phase 4, `manifests/primitive-lifecycle.yaml` (search for `maturity:`), `rules/RULES-COMPACT.md` §10.
- **Scope**: ~1-2 sessions depending on hook count.
- **Deliverable**: add `maturity: observe|warn|block|emergency` field to every registered hook entry. New default = `observe`. Add `tests/audit/test_hook_maturity_coverage.py` enforcing presence. Acceptance lines 135-136.
- **Blockers**: none.

### S3. ADR-121 Phase 6 — ADR-118 multi-agent chaos suite
- **Read first**: ADR-121 §Phase 6, ADR-118, current chaos tests `tests/chaos/`.
- **Scope**: ~3 sessions.
- **Deliverable**: chaos tests covering same-task, same-file, same-domain, projection drift, stash reapply, validation cleanup, merge queue races. Each must produce an actionable artifact. Acceptance lines 179-181.

### S4. ADR-291 Phase 2 — first 6 of 23 endpoints
- **Read first**: ADR-291, current cosd endpoint registry, `cosd-secure-api` rule, `lib/cosd*` files for 501 handlers.
- **Scope**: ~1 session per 6 endpoints (4 sessions total).
- **Deliverable**: 6 highest-priority 501s return real responses with auth checks and tests.

### S5. ADR-325 Phase 3 — provider cost ingestion
- **Read first**: `docs/02-Decisions/adrs/ADR-325*.md` §Phase 3, `lib/taximeter.py` (commit 32aae0d6), `lib/dispatch.py`.
- **Scope**: ~1 session.
- **Deliverable**: hook `lib/dispatch.py` to call `taximeter.tick()` after each provider response with real prompt_tokens, completion_tokens, latency_ms, cost_usd. Add provider-specific cost-per-token lookup.
- **Acceptance**: live dispatch writes to `.cognitive-os/metrics/taximeter.jsonl` automatically.

### S6. ADR-325 Phase 4 — anti-loop enforcement
- **Read first**: ADR-325 §Phase 4, existing `token-budget-monitor` hook, `lib/taximeter.py`.
- **Scope**: ~1 session.
- **Deliverable**: detection rule that fires when total cost OR same-task spend OR loop signature crosses threshold. Block with hookSpecificOutput.
- **Blockers**: S5 first.

### S7. ADR-325 Phase 5 — language token economy
- **Read first**: ADR-325 §Phase 5, `rules/language-token-economy.md`.
- **Scope**: ~1 session.
- **Deliverable**: per-language token accounting + the rule's measurable enforcement. Internal artifacts compact per the rule; user-facing language preserved.
- **Blockers**: S5.

### S8. Operational Stability Phase 3 — adaptive profile resolver
- **Read first**: `.cognitive-os/plans/architecture/operational-stability-friction-reduction.md` §Phase 3, `scripts/cos-profile-explain`.
- **Scope**: ~1 session.
- **Deliverable**: `cos profile explain` shows WHY a profile was selected; lean still protects secrets; strict for main landing. Acceptance lines 146-148.

### S9. Operational Stability Phase 7 — distribution boundary in default install
- **Read first**: §Phase 7, `manifests/primitive-lifecycle.yaml` (distribution field), ADR-124.
- **Scope**: ~2 sessions.
- **Deliverable**: default install path includes ONLY `core` unless explicitly configured. Maintainer/lab tooling available but not default runtime. Acceptance lines 291-294.

### S10. Operational Stability Phase 8 — productization threshold
- **Read first**: §Phase 8.
- **Scope**: ~2 sessions.
- **Deliverable**: cos status reports safe/unsafe accurately in fixture repos; false-positive blocker rate tracked and trending down; safe repairs idempotent + race tests; new guards cannot enter `block` without maturity metadata + tests. Acceptance lines 311-316.
- **Blockers**: S2 (maturity rollout).

### S11. DX Tax Reduction — finish remaining 13 items
- **Read first**: `.cognitive-os/plans/architecture/dx-tax-reduction-plan.md`.
- **Scope**: ~2 sessions.
- **Deliverable**: implement or mark-with-evidence each open item. Several are doc-sync of already-shipped work (per-distribution counts in cos-status landed in e90981ed).

### S12. Governance Tools Consolidation — remaining items
- **Read first**: `.cognitive-os/plans/architecture/governance-tools-consolidation.md`, reconciliation header decisions.
- **Scope**: ~2 sessions.
- **Deliverable**: Phase 4 stash-symmetry tests, Phase 5 surface filtering 10-20 for agents, Phase 7 friction telemetry feed into ADR-123, Phase 8 archive trial.

---

## WAVE 6 — ADR sequential chain remainder

### S13. ADR-038 Wave 2 — preamble template update + integration hook
- **Read first**: `templates/agent-preamble.md` (CANONICAL), `lib/agent_input_validator.py` (commit 817d1133), `manifests/hook-registration-classification.yaml` entry already present for `hooks/subagent-input-schema-validator.sh`.
- **Scope**: ~2h.
- **Deliverable**: preamble explicitly calls validate_input at startup. New hook `hooks/subagent-input-schema-validator.sh` emits ESCALATION on failure. Tests at `tests/hooks/test_subagent_input_schema_validator.py`.
- **Blockers**: protected-config-write-guard for preamble — use `COS_ALLOW_PROTECTED_CONFIG_WRITE=1` via python subprocess.

### S14. ADR-038 Wave 3 — TrustReport Pydantic schema
- **Read first**: ADR-038 Gap #3 in pending-task, `rules/trust-score.md`.
- **Scope**: ~1 session.
- **Deliverable**: `lib/trust_report_schema.py` with Pydantic model matching the TRUST_REPORT format. Tests covering bands HIGH 90+, MEDIUM 70-89, LOW 50-69, CRITICAL <50.
- **Blockers**: S13.

### S15. ADR-038 Wave 4 — planning template separation
- **Read first**: ADR-038 Gap #6.
- **Scope**: ~1 session.
- **Deliverable**: split planning prompts from execution prompts in the preamble. Planning template emits a different output shape optimized for review-before-act.

---

## WAVE 4 — Plans still mid-completion

### S16. Maintainer Telemetry Phase 2 — 3 detections
- **Read first**: `.cognitive-os/plans/architecture/maintainer-agent-telemetry-promotion-loop.md` §Phase 2, `lib/promote_from_telemetry.py`, `lib/performance_ledger.py` (rollups from commit 1245f32e).
- **Scope**: ~2h.
- **Deliverable**: `detect_skill_override_patterns`, `detect_provider_fallback_drift`, `detect_dormant_no_evidence`. Tests at `tests/unit/test_promote_from_telemetry_phase2.py`.
- **Blockers**: none — Phase 1 rollups landed.

### S17. Maintainer Telemetry Phase 5 — impact measurement
- **Read first**: §Phase 5, ADR-201.
- **Scope**: ~2 sessions.
- **Deliverable**: post-change impact records, outcome-failure protocol (quarantine, penalize confidence, manual investigation), baseline vs candidate comparison over declared window, mark improved/neutral/regressed/inconclusive, feed regressions into PromoteFromTelemetry.
- **Blockers**: S16.

---

## DORMANT RATIO 0.25 PUSH

### S18. Wiring slice — 23 ADR-146 delivery-team scripts
- **Read first**: cluster analysis in `docs/06-Daily/reports/session-2026-05-18-multi-wave.md`. The 23 scripts EXIST and HAVE TESTS but are NOT wired in CI/Makefile/hooks.
- **Scope**: ~1-2 sessions.
- **Deliverable**: wire each into one of: `.github/workflows/`, `Makefile`, `cognitive-os.yaml` cron, `cos-runner-hooks.json`. Dormant ratio drops further; flip lifecycle entries from candidate to advisory/active in a follow-up manifest commit.

### S19. Long-tail dormants — 40 items across 25+ owner_adr combos
- **Read first**: the agent backlog audit launched at end of 2026-05-18 (id starts with `a6b84b644`). Cluster breakdown will be in Engram once it returns.
- **Scope**: ~2 sessions (research) + 2 sessions (apply).
- **Deliverable**: per-cluster decision (promote / keep / archive) applied to manifest.

### S20. ADR-019 install-scripts (8) — promote vs archive
- **Read first**: candidates in `manifests/primitive-lifecycle.yaml` matching `owner_adr=ADR-019 governance_class=optional-runtime-tooling`.
- **Scope**: ~1h.
- **Deliverable**: verify which are reachable via `cos install`; archive the rest. Probable archives: install-aguara.sh, cos-postgres-local.sh if no consumer.

---

## PROCESS / META

### S21. Push to origin
- **Read first**: `git log origin/main..main` (~38 commits ahead).
- **Scope**: 5 min.
- **Deliverable**: `git push origin main` after operator review.
- **Blockers**: operator OK only.

### S22. ADR-038 Wave 2 hook tests — broaden behavior coverage
- **Read first**: `tests/unit/test_agent_input_validator.py` (commit 817d1133).
- **Scope**: ~1h.
- **Deliverable**: integration tests showing a real sub-agent prompt with INPUT SCHEMA flows end-to-end through the new hook.
- **Blockers**: S13.

### S23. ADR-278 Phase 2 backfill — remaining 240 calls
- **Read first**: `scripts/cos-subprocess-timeout-backfill` (v2 per operator commit fbbf191a — now filters non-code mentions).
- **Scope**: ~2 sessions.
- **Deliverable**: continue backfill on lib/+scripts/+packages/+tests/. Each batch ~20-30 files. subprocess.run calls without timeout drop further.

### S24. Wave 7 long-tail — 5 remaining cancelled-stale active-tasks
- **Read first**: `.cognitive-os/tasks/active-tasks.json` (cancelled-stale entries fa72b1, d29758, 371310, 83a0c7, b9a834 per Wave 7 agent residual debt).
- **Scope**: 15 min.
- **Deliverable**: purge them like the first 7 were purged.

### S25. Rebuild self-knowledge index
- **Read first**: `scripts/cos_build_self_knowledge.py` + cron entry.
- **Scope**: 5 min.
- **Deliverable**: run the builder, verify `.cognitive-os/self-knowledge/` files are fresh (mtime within this week).

### S26. Refresh apply-efficiency-profile.sh — pick up EAS hook
- **Read first**: commit 3bfa160b (EAS gate lands in apply-efficiency-profile.sh but `.claude/settings.json` is generated and not auto-refreshed).
- **Scope**: 5 min.
- **Deliverable**: `bash scripts/apply-efficiency-profile.sh standard` + verify Stop matcher in settings.json now includes the gate.

### S27. ADR-038 Wave 1 portability test
- **Read first**: `lib/agent_input_validator.py`, `tests/red_team/portability/` directory structure.
- **Scope**: ~30 min.
- **Deliverable**: paired portability test so the lib could switch from `SCOPE: os-only` to `SCOPE: both` later.

### S28. Multilingual SDD activation (if prioritized)
- **Read first**: `.cognitive-os/sdd/changes/multilingual-corpus-expansion/proposal.md` (the rewritten ES+EN-only version on disk; SDD changes are gitignored).
- **Scope**: ~2.5h per the rewritten estimate.
- **Deliverable**: `/sdd-continue multilingual-corpus-expansion` through propose → spec → apply → verify → archive.
- **Blockers**: operator-gated.

### S29. ADR-040 real-embedding swap
- **Read first**: `lib/reinvention_embeddings.py` (STUB), `lib/query_tailored_context.py`, ADR-039 follow-up debt.
- **Scope**: ~1 session.
- **Deliverable**: install fastembed (or confirm it is already in pyproject), swap stub for real model, re-tune cosine threshold against a small corpus.
- **Blockers**: dep adoption gate must OK fastembed.

### S30. Adversarial review of this session's commits
- **Read first**: `git log --oneline origin/main..main`, then walk each commit's diff.
- **Scope**: ~2 sessions to do properly.
- **Deliverable**: code-review findings per commit, severity-tagged, filed in `.cognitive-os/metrics/review-findings.jsonl` and Engram.
- **Blockers**: none; should run BEFORE the push (S21).

---

## Quick reference by effort

- **30 min or less (6 items)**: S20, S21, S24, S25, S26, S27 — basically free wins.
- **1-2h (8 items)**: S1, S5, S6, S7, S8, S13, S16, S29.
- **1 session ~4h (8 items)**: S2, S11, S12, S14, S15, S17, S18, S23.
- **Multi-session (8 items)**: S3, S4, S9, S10, S19, S22, S28, S30.

## Dependency graph

```
S5 (cost ingestion) -> S6 (anti-loop) -> S7 (lang economy)
S13 (preamble v2) -> S14 (TrustReport) -> S15 (planning template)
                  -> S22 (broader tests)
S16 (Phase 2 detect) -> S17 (Phase 5 impact)
S2 (maturity rollout) -> S10 (productization threshold)
S30 (review) -> S21 (push)
S29 depends on dep-adoption-gate approval (out of band)
```

## Engram pointers

The cluster analysis and gotchas are saved at observations:
- `dormant-ratio-strategy` (topic_key)
- `orchestrator-commit-gotchas` (topic_key)
- session_summary for 2026-05-18 — `mem_search` "multi-wave" returns it.

Future sessions should `mem_context` first, then `mem_search` for the specific cluster they are attacking.
