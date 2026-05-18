# Session report — 2026-05-18 multi-wave cleanup + Wave 4/5/6 attack

> Audit-friendly summary of a long orchestrator session that worked
> through the post-audit-cleanup roadmap end-to-end. Counterpart to
> the per-commit changelog: this is the *why*, the cluster analysis,
> and the operator decisions that shaped the commit chain.

## Goal

Drive the project from "300 declared pending checkboxes + 125 ADRs
partial + 90 backlog items + 0.551 dormant ratio + ~8.5k control-plane
findings" toward a measurable baseline by ordered waves (Wave 0–7,
documented in `.cognitive-os/plans/roadmaps/post-audit-cleanup-roadmap.md`).

## What was actually committed (38+ commits to main)

Grouped by wave for navigation. Hashes are stable references.

### Audit infrastructure root-fixes
- `cb5db8d1` refactor(audit): centralize tracked-code enumeration to plug blind spot
- `3f8ef86e` fix(paths): repair 5 stale legacy doc paths + harden audit gate
- `3373c644` docs(adrs): close 6 partial ADRs (179, 252, 013, 015, 322, 008)
- `a666329a` docs(adr-275): mark session-start hook wiring as deployed
- `54d823ef` docs(plans): add post-audit cleanup roadmap (8 waves)

### Wave 0 — claim ledger + stash ops
- `5dac1a33` feat(stash-ops): lib for ADR-117 stash invariants 3/4/1
- `0bbd0980` refactor(claims): unify task claim ledger on cos_task_claims store

### Wave 1 — quick wins
- `7b042602` feat(skills): add /install-skill and /install-hook
- `c1ac1ef4` feat(self-improve): scheduled propose-only runner with ADR-201 gate
- `ce8042a3` fix(secret-detector): migrate exit-2 to native hookSpecificOutput
- `5145fe54` feat(external-review-readiness): close 3 KEEP-OPEN items
- `5f85b6e1` docs(plans): reconcile checkboxes drift across 3 architecture plans
- `83e9998f` docs(plans): finish checkbox reconciliation across remaining 3 plans

### Wave 2 — ADR-278 timeouts
- `1a5c4948` chore(adr-278): backfill subprocess.run timeouts in 73 files

### Wave 7 — zombie cleanup
- `11bacc43` chore(wave7): formal tombstones for agent-escalation + workflow-engine
  - moved sprint-b37c1353 demo, 7 cancelled-stale active-tasks, work-queue
    noise, handoffs/improvements to `.cognitive-os/archive/wave7-2026-05-18/`
    (gitignored)

### Wave 4 — medium plans
- `c7e60885` docs(plans): mark Wave 4.2 + 4.3 doc-sync checkboxes with evidence
- `c3bbec84` feat(adr-200-plus): outcome-failure queue + close 2 plan items
- `5c166e57` feat(sprint): close ADR-036 SprintTestSummary gap (event 6/6)
- `52a7eae6` fix(sprint): aggregator session detection in aggregate_test_results
- `a71bcab1` test(sprint): prove test-summary aggregator wiring  (operator follow-up)

### Wave 5 — high-leverage slices
- `d6b7c4fb` chore(lifecycle): apply dormant batch — 70 actions, ratio 0.545→0.471
- `c0a8d838` chore(lifecycle): promote 5 lab hooks with active lifecycle to maintainer
- `d4e0b6fa` chore(lifecycle): promote 20 maintainer delivery-structure ADR-146 scripts
- `f37b892a` docs(governance-tools): close 5 Phase 2 + exit-criteria items
- `d1828684` feat(adr-121): single-writer enforcement metric ledger
- `1245f32e` feat(performance-ledger): semantic rollups for skill/provider/primitive
- `32aae0d6` feat(taximeter): ADR-325 Phase 2 cost accounting ledger
- `3bfa160b` feat(adr-319/324): EAS validation gate hook + apply-efficiency-profile wiring

### Wave 6 — sequential ADR chain
- `7b042602` … (skills 037 deps shared with Wave 1 1.2)
- `55d5df38` feat(reinvention): ADR-039 Phase B-β embedding similarity primitives
- `c970bc31` feat(exercised-coverage): ADR-041 pipeline classifying 1143 primitives
- `82fbf7f0` chore(exercised-coverage): baseline snapshot for drift tracking
- `9f214f5c` feat(adr-040): query-tailored context selection primitive
- `817d1133` feat(adr-038): runtime INPUT SCHEMA validator (Wave 1)

### Manifest housekeeping triggered along the way
- `f5d5b4d2` chore(manifest): register outcome_failure_queue.py in ADR-251 allowlist
- `555fc394` chore(manifest): register agent_input_validator.py in ADR-251 allowlist
- `e90981ed` feat(cos-status): expose per-distribution primitive counts
- `702dd977` docs(plans): reconcile 8 op-stability checkboxes with shipped work

(38 commits; pseudo-chronological. `git log --oneline origin/main..main` is
canonical.)

## Operator decisions (Wave 3 cluster — 5 humans calls)

| # | Decision | Outcome |
|---|---|---|
| 3.1 ADR-275 staged hooks | **Activate** | Found already deployed in all 3 harnesses; README marked DEPLOYED |
| 3.2 ADR-008 multi-tool | **Close as policy-accepted** | Closed via cos-adr-close |
| 3.3 multilingual-corpus | **Rewrite scope first** | Trimmed ES+EN only; 5h→2.5h estimate (SDD gitignored, on disk) |
| 3.4 dormant ratio target | **Audit lab + tier strategy** | Found archive-only-lab insufficient (0.551→0.42 best case); promotion strategy preferred |
| 3.5 5 closable ADRs (179, 252, 013, 015, 322) | **Close all** | Done via cos-adr-close; backlog 125→119 |

## Dormant ratio tracking (single number, ratchets down)

```
0.551  (session start, 516 dormant / 937 total)
0.545  (post lab promotion v1, 5 hooks)         d-0.006
0.471  (post batch A+B+C, 70 actions)           d-0.074
0.450  (post 20 maintainer delivery promote)    d-0.021

target: 0.250 (so-existential Phase 1)
remaining: -0.200 — requires resolving cluster decisions below.
```

## Cluster analysis — the 192 NEEDS-DECISION items (live data)

Reported as 151 by the first audit; re-pulling against the manifest
post-promotes returned **192** team+maintainer candidates. The
distribution is heavily concentrated in 4 clusters (79% of total):

| Cluster | Count | Operator decision |
|---|---:|---|
| ADR-146 meta-governance maintainer | 57 | Audit case by case (in flight) |
| ADR-019 templates team (project-scaffold-surface) | 29 | Verify project-scaffold consumes (in flight) |
| ADR-146 delivery-structure team | 29 | Verify CI/release wiring (returned) |
| ADR-146 delivery-structure maintainer | 20 | Bulk promote (applied — `d4e0b6fa`) |
| ADR-314 skills maintainer (skill-maintainer-only) | 9 | Exhaustive review (returned) |
| ADR-019 install-scripts team (optional-runtime-tooling) | 8 | Not yet decided |
| Long-tail (other owner_adr) | 40 | Decide per-item later |

### Audit returns (subset, full reports in conversation log)

**ADR-146 delivery-structure team (29)**: 6 PROMOTE-ACTIVE
(`cos-smoke.sh`, `cos-status.sh`, `dogfood_score.py`,
`primitive_surface_reduce.py`, `primitive_usage_map.py`,
`run-all-tests.sh`), 23 KEEP-CANDIDATE (exist + have tests but no CI
wiring — bottleneck is not coverage but wiring). 0 ARCHIVE.

**ADR-314 skills maintainer (9)**: 5 PROMOTE-ADVISORY (`add-rule`,
`agent-control`, `agent-dashboard`, `detect-patterns`, `queue-drain`)
because they have routine operator value (governance authoring, agent
ops, health auditing, queue management). 4 KEEP-CANDIDATE
(`component-classifier`, `primitive-harness-coverage`,
`redteam-harness`, `security-red-team`) because they are sensitive or
maintenance-only. 0 ARCHIVE.

## Bugs found + fixed in flight

| Bug | Where | Fix |
|---|---|---|
| `cos-adr-close` hardcoded `docs/adrs` | scripts/cos-adr-close | path now `docs/02-Decisions/adrs` (`3373c644`) |
| Audit gate `.py/.sh` extension filter | tests/audit/test_canonical_adr_path.py | extended to extensionless shebanged scripts via tests/audit/_lib/tracked_code.py (`cb5db8d1`) |
| 5 stale legacy doc paths in scripts/ | check_lazy_catalog_health, validate_tier_filter, agentic_mastery_summary, security_red_team | repaired + gate hardened to catch (`3f8ef86e`) |
| ADR-278 backfill: comment swallowed `)` in 14 files | scripts/cos-subprocess-timeout-backfill v1 | 19 inline repairs + script patched + operator follow-up `fbbf191a` filters non-code mentions |
| Lab promotion: 52 of 57 hooks blocked by lifecycle_state=sandbox | manifests/primitive-lifecycle.yaml | only 5 promotable in that pass; ADR-146 candidate→sandbox graduation became the bigger lever (70 items in `d6b7c4fb`) |
| outcome_failure_queue.py unmanifested in ADR-251 | manifests/agent-orchestration-adapters.yaml | added to core_file_allowlist (`f5d5b4d2`) |
| agent_input_validator.py same | manifests/agent-orchestration-adapters.yaml | added (`555fc394`) |

## Agent escalations (lessons)

- 3 sub-agents escalated on the 50-tool-call budget. Two were
  recoverable inline (apply remaining items myself); one (ADR-278
  backfill) introduced syntax errors that required cleanup.
- `agent-orchestration-boundary` (ADR-251) blocked every Agent launch
  twice when a new lib/ file matched the audit regex
  `(agent|handoff|dispatch|retry|budget|daemon|team|freeze|worktree|
  session|queue|worker)`. Pattern: when adding any new lib/ file with
  one of those tokens in the name, expect to register it in the
  manifest before further agent launches.
- `ScopeMarkerPortabilityGate` blocked commits where new libs declared
  `SCOPE: both` without paired portability tests. Resolution: for
  internal infra (governance, taximeter, single-writer-metric,
  query-tailored, etc.) prefer `SCOPE: os-only` unless a real
  consumer-facing surface exists.
- `plan-claim-validator` rejects multi-line checkboxes; the
  `(verified: …)` token must be on the same line as the `[x]`.

## Files / artifacts shipped

| Category | Counts |
|---|---|
| Commits to main | 38+ |
| New libs (lib/) | stash_ops, taximeter, outcome_failure_queue, performance_ledger rollups, reinvention_embeddings, exercised_coverage, query_tailored_context, single_writer_metric, agent_input_validator |
| New scripts | cos-self-improvement-runner, cos-install-skill, cos-install-hook, cos-lean-core-5min-proof, cos-strict-maintainer-concurrency-proof, cos-exercised-coverage, cos-subprocess-timeout-backfill |
| New hooks | eas-validation-gate.sh |
| New skills | install-skill, install-hook |
| New manifests | external-review-scenarios.yaml, exercised-coverage-baseline.yaml |
| New ADRs | 326 (agent-escalation tombstone), 327 (workflow-engine tombstone) |
| Test files | 14+ new tests/unit + behavior + hook coverage |

## What is still open (next session pickups)

1. **4 audits in flight** when this report was written: ADR-146
   meta-governance maintainer (57), ADR-019 templates (29), ADR-146
   delivery team (29 — returned), ADR-314 skills (9 — returned).
2. **Wave 5 big remaining**: ADR-121 phases 3-6 (foundation
   hardening), ADR-291 Phase 2 (23 endpoints in 501), ADR-325 Phases
   3-5, DX Tax Reduction big remainder, Operational Stability Phases
   2/3/7/8.
3. **Wave 6 remaining**: ADR-038 Waves 2-4 (preamble template update
   + hook integration + TrustReport schema + planning template).
4. **Maintainer Telemetry**: 15 items still need real impl (Phase 1
   rollups landed, but Phase 2 detections, Phase 5 impact measurement
   still open).
5. **Dormant ratio**: 0.450 → 0.250 still needs ~200 more dormant
   resolutions. The cluster decisions above are the biggest levers
   left; long-tail of 40 items will be slower.
6. **NOT pushed to origin** — local branch is ~38 commits ahead. The
   operator gates the push.
EOF