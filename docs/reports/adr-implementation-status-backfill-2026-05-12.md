# ADR Implementation Status Backfill — 2026-05-12

## Scope

This report records the completed implementation-status backfill after the ADR status taxonomy split. The pass migrated tracked prose-only ADRs to YAML frontmatter, using explicit prose status/evidence where present and preserving the original body unchanged after the frontmatter.

## Result

| Metric | Count |
|---|---:|
| Total tracked ADR files | 284 |
| Tracked ADRs with YAML frontmatter | 284 |
| Tracked ADRs still prose-only | 0 |
| Active ADRs | 243 |
| Active with implementation_status | 243 |
| Active still unclassified | 0 |

## Active Navigation Buckets

| Bucket | Count |
|---|---:|
| Active / Implemented | 97 |
| Active / Partial | 114 |
| Active / Partial / Blocked | 1 |
| Active / Deferred | 1 |
| Active / Planned | 1 |
| Active / Not Applicable | 29 |
| Active / Unclassified | 0 |

## Decision Rules Used

- `implemented`: ADR text explicitly says implemented/materialized/shipped/delivered/closed, or frontmatter already used `status: implemented` and declared implementation files/tests.
- `partial`: ADR text says partially implemented, first slice implemented, MVP/phase-only scope, or remaining runtime/wiring work is explicitly called out.
- `partial-blocked`: some slice is done and a named external/local blocker remains.
- `deferred`: the ADR intentionally delays implementation or keeps optional work unimplemented.
- `planned`: proposed or accepted work is not started.
- `not-applicable`: terminal/tombstone/superseded/exploration records, or accepted policy/decision records with no concrete implementation surface in the ADR prose.

## Backfilled Active ADRs

| ADR | Decision | Implementation | Classification basis | Evidence summary |
|---|---|---|---|---|
| [006](../adrs/ADR-006-agpl-license-compliance.md) | `accepted` | `partial` | accepted record with explicit pending/deferred/planned scope | **Date:** 2026-03-23 |
| [007](../adrs/ADR-007-cognitive-os-rebrand.md) | `accepted` | `not-applicable` | accepted decision/policy record with no explicit implementation surface | **Date:** 2026-03-24 |
| [008](../adrs/ADR-008-multi-tool-support.md) | `accepted` | `not-applicable` | accepted decision/policy record with no explicit implementation surface | **Date:** 2026-03-28 |
| [009](../adrs/ADR-009-package-architecture.md) | `accepted` | `not-applicable` | accepted decision/policy record with no explicit implementation surface | **Date:** 2026-03-28 |
| [010](../adrs/ADR-010-hook-architecture-v2.md) | `accepted` | `not-applicable` | accepted decision/policy record with no explicit implementation surface | **Date:** 2026-03-28 to 2026-04-13 |
| [012](../adrs/ADR-012-prompt-driven-governance.md) | `accepted` | `implemented` | implementation/shipped/delivered evidence | **Date:** 2026-03-29 |
| [013](../adrs/ADR-013-security-stack.md) | `accepted` | `partial` | implementation evidence plus partial/deferred/future signal | **Date:** 2026-03-29 |
| [014](../adrs/ADR-014-sdd-fast-path.md) | `accepted` | `partial` | accepted record with explicit partial/phase scope | **Date:** 2026-03-31 |
| [015](../adrs/ADR-015-rules-to-hooks-migration.md) | `accepted` | `partial` | implementation evidence plus partial/deferred/future signal | **Date:** 2026-04-10 |
| [016](../adrs/ADR-016-context-diet.md) | `accepted` | `partial` | implementation evidence plus partial/deferred/future signal | **Date:** 2026-03-31 |
| [017](../adrs/ADR-017-stabilization-freeze.md) | `accepted` | `partial` | accepted record with explicit partial/phase scope | **Date:** 2026-04-11 |
| [018](../adrs/ADR-018-docker-to-pip-migration.md) | `accepted` | `partial` | implementation evidence plus partial/deferred/future signal | **Date:** 2026-04-11 to 2026-04-13 |
| [019](../adrs/ADR-019-scope-tagging.md) | `accepted` | `partial` | implementation evidence plus partial/deferred/future signal | **Date:** 2026-04-13 |
| [020](../adrs/ADR-020-contamination-fix.md) | `accepted` | `partial` | accepted record with explicit partial/phase scope | **Date:** 2026-04-13 |
| [021](../adrs/ADR-021-vendor-agnostic-with-adapters.md) | `accepted` | `partial` | implementation evidence plus partial/deferred/future signal | **Date:** 2026-04-16 |
| [022](../adrs/ADR-022-prompt-type-hooks-adoption.md) | `accepted` | `partial` | accepted record with explicit partial/phase scope | **Date:** 2026-04-15 |
| [023](../adrs/ADR-023-updated-input-pattern.md) | `accepted` | `not-applicable` | accepted decision/policy record with no explicit implementation surface | **Date:** 2026-04-15 |
| [024](../adrs/ADR-024-task-panel-bridge.md) | `accepted` | `partial` | implementation evidence plus partial/deferred/future signal | **Date:** 2026-04-16 |
| [025](../adrs/ADR-025-install-update-loop.md) | `accepted` | `partial` | implementation evidence plus partial/deferred/future signal | **Date:** 2026-04-17 |
| [026](../adrs/ADR-026-r2-r3-design-review.md) | `accepted` | `partial` | implementation evidence plus partial/deferred/future signal | **Date:** 2026-04-17 |
| [026a](../adrs/ADR-026a-decisions.md) | `accepted` | `partial` | accepted/implemented text with explicit partial/deferred scope | **Status:** CLOSED — R3 decisions (D3.1–D3.3) accepted and implemented 2026-04-17 |
| [027](../adrs/ADR-027.md) | `accepted` | `implemented` | explicit all-delivered/full-closed status | ACCEPTED (2026-04-21) — WS1-WS3 shipped, included in v0.12.0 release. Implementation commits: 8dc4a6e, 9bd895b, 15d67eb. Resolved by ADR-027a. Originally propos |
| [027a](../adrs/ADR-027a.md) | `accepted` | `implemented` | explicit prose status migration for previously prose-only ADR | **Supersedes**: ADR-027 §Baseline (context overhead table), §KPIs row "CLAUDE.md tokens loaded on session start" |
| [028](../adrs/ADR-028.md) | `accepted` | `implemented` | explicit all-delivered/full-closed status | ACCEPTED (2026-04-21) — Full 6-pillar framework CLOSED. Addenda ADR-028a/b/c resolved all PENDING items (commit 423bd86). Originally proposed 2026-04-17. |
| [028a](../adrs/ADR-028a.md) | `accepted` | `implemented` | explicit prose status migration for previously prose-only ADR | **Amends**: ADR-028 D1.A, D1.C, D4 |
| [028b](../adrs/ADR-028b.md) | `accepted` | `implemented` | explicit prose status migration for previously prose-only ADR | **Supersedes**: ADR-028 D1.C (original spec, lines 166–214) |
| [028c](../adrs/ADR-028c.md) | `accepted` | `partial` | implementation evidence plus partial/deferred/future signal | MetricEvent.schema_version is a monotonically-increasing integer starting at 1. |
| [029](../adrs/ADR-029.md) | `accepted` | `partial` | implementation evidence plus partial/deferred/future signal | **Deciders**: Maintainer |
| [029b](../adrs/ADR-029b-reinvention-phase-b-semantic.md) | `accepted` | `partial` | implementation evidence plus partial/deferred/future signal | **Deciders**: Maintainer |
| [030](../adrs/ADR-030.md) | `accepted` | `partial` | accepted/implemented text with explicit partial/deferred scope | Today the orchestrator has 7 session lifecycle skills (`/session-wrapup`, `/session-backlog`, `/session-report-executive`, `/resume-tasks`, `/session-manager`,  |
| [031](../adrs/ADR-031.md) | `accepted` | `partial` | accepted record with explicit pending/deferred/planned scope | Manual forensic audits showed a persistent gap between the agentic primitives we build and the agentic primitives |
| [032](../adrs/ADR-032-orchestrator-trap-preview.md) | `accepted` | `partial` | accepted record with explicit partial/phase scope | The COS currently operates in FIRE_AND_FORGET mode (banner: "Valkey ✅, Executor ❌"). In this mode: |
| [033](../adrs/ADR-033-harness-agnostic-event-capture.md) | `accepted` | `partial` | accepted record with explicit pending/deferred/planned scope | The Cognitive OS observes agent activity through two JSONL streams: |
| [033b](../adrs/ADR-033b-duration-correlation-and-aider-hardening.md) | `accepted` | `partial` | implementation evidence plus partial/deferred/future signal | **Parent**: ADR-033 (`c9f52bf` — harness-agnostic event capture) |
| [035](../adrs/ADR-035-worktree-cwd-enforcement.md) | `accepted` | `partial` | implementation evidence plus partial/deferred/future signal | **Deciders**: Maintainer |
| [037](../adrs/ADR-037-self-knowledge-base.md) | `accepted` | `not-applicable` | accepted decision/policy record with no explicit implementation surface | Sub-agents spend 3-10K tokens per session grepping source files to answer basic questions: |
| [040](../adrs/ADR-040-query-tailored-context-injection.md) | `accepted` | `implemented` | implementation/shipped/delivered evidence | **Deciders**: Matias Amendola |
| [041](../adrs/ADR-041.md) | `accepted` | `partial` | accepted record with explicit partial/phase scope | **Deciders**: luum-agent-os team |
| [042](../adrs/ADR-042-valkey-local-daemon.md) | `accepted` | `partial` | accepted record with explicit partial/phase scope | **Deciders**: Matias Améndola |
| [044](../adrs/ADR-044-context-payload-slimming.md) | `accepted` | `partial-blocked` |  | **Authors**: Agent C (startup-optimization initiative, stream 3/4) |
| [045](../adrs/ADR-045-postgres-local-daemon.md) | `accepted` | `partial` | implementation evidence plus partial/deferred/future signal | **Deciders**: Matias Améndola |
| [048](../adrs/ADR-048-docker-container-image-freshness.md) | `accepted` | `partial` | accepted record with explicit partial/phase scope | **Accepted** — 2026-04-21. Follow-up to a live incident the same day. |
| [049](../adrs/ADR-049-llm-gateway-selection-and-overflow-providers.md) | `accepted` | `implemented` | implementation/shipped/delivered evidence | **Accepted** — 2026-04-21. Supersedes implicit adoption of `litellm` (present |
| [050](../adrs/ADR-050-per-skill-routing-policy.md) | `accepted` | `partial` | implementation evidence plus partial/deferred/future signal | **Accepted** — 2026-04-21. Schema + dispatch integration shipped. Builds on |
| [051](../adrs/ADR-051-qwen-agent-loop.md) | `accepted` | `implemented` | explicit all-delivered/full-closed status | - **Status**: Accepted (2026-04-21) — Phases 1, 2, 3, 4 all DELIVERED this session. Commits: MVP phase 1, 1e6542c (phase 2), 534814e (phase 3), 925dff5 (phase 4 |
| [052](../adrs/ADR-052-provider-benchmark-harness.md) | `implemented` | `implemented` |  | **Implemented for the no-cost offline harness scope.** The repository now ships a |
| [053](../adrs/ADR-053-dispatch-auto-optimizer.md) | `implemented` | `implemented` |  | **Implemented for reviewed proposal generation.** The repository now ships a |
| [054](../adrs/ADR-054-project-docs-convention.md) | `accepted` | `partial` | implementation evidence plus partial/deferred/future signal | **Accepted** — 2026-04-21. Implementation lives in `lib/project_scaffolder.py` |
| [055](../adrs/ADR-055-docs-convention-enforcement.md) | `accepted` | `partial` | implementation evidence plus partial/deferred/future signal | **Accepted** — 2026-04-21. Addendum to ADR-054. Implementation lives in |
| [055b](../adrs/ADR-055b-destructive-git-block.md) | `accepted` | `partial` | implementation evidence plus partial/deferred/future signal | **Supersedes**: partial warn-only behavior of `hooks/destructive-git-blocker.sh` |
| [056](../adrs/ADR-056-adaptive-agent-dispatch.md) | `accepted` | `partial` | explicit prose status migration for previously prose-only ADR | - **Status**: L1 IMPLEMENTED (advisory-only). L2/L3 DEFERRED. |
| [057](../adrs/ADR-057-cross-harness-authoring-and-driver-projection.md) | `accepted` | `partial` | accepted record with explicit pending/deferred/planned scope | Date: 2026-04-23 |
| [058](../adrs/ADR-058-observability-migration-langfuse-to-phoenix.md) | `accepted` | `partial` | accepted record with explicit partial/phase scope | - **Status**: Accepted |
| [060](../adrs/ADR-060-local-only-optional-services.md) | `accepted` | `partial` | accepted record with explicit partial/phase scope | **Accepted** — 2026-04-24. Effective immediately. |
| [061](../adrs/ADR-061-focus-narrative-and-external-evidence.md) | `accepted` | `partial` | accepted record with explicit pending/deferred/planned scope | **Accepted** — 2026-04-24. Fills the 5 gaps identified during the existential |
| [063](../adrs/ADR-063-agent-tool-replication-strategy.md) | `accepted` | `partial` | implementation evidence plus partial/deferred/future signal | **Accepted** — 2026-04-24. Clarifies the scope of ADR-051 / ADR-062 and |
| [064](../adrs/ADR-064-harness-agnostic-cognitive-os.md) | `accepted` | `partial` | implementation evidence plus partial/deferred/future signal | **Implementation-plan**: `.cognitive-os/plans/architecture/adr-064-implementation-plan.md` |
| [068](../adrs/ADR-068-adaptive-test-runner-capacity.md) | `accepted` | `partial` | accepted/implemented text with explicit partial/deferred scope | **Accepted** — Phase 2 implemented 2026-04-30. Original proposal: 2026-04-24. |
| [071](../adrs/ADR-071-engram-lifecycle-evolution.md) | `accepted` | `partial` | implementation evidence plus partial/deferred/future signal | **Accepted** — 2026-04-27 |
| [072](../adrs/ADR-072-test-lane-taxonomy.md) | `accepted` | `partial` | implementation evidence plus partial/deferred/future signal | **Accepted** — 2026-04-29. |
| [073](../adrs/ADR-073-test-architecture-role-registry.md) | `accepted` | `partial` | implementation evidence plus partial/deferred/future signal | **Accepted** — 2026-04-30. |
| [074](../adrs/ADR-074-tier-0-learning-loop-closure.md) | `accepted` | `partial` | implementation evidence plus partial/deferred/future signal | **Status:** Accepted |
| [075](../adrs/ADR-075-stage2-selective-expansion.md) | `accepted` | `partial` | implementation evidence plus partial/deferred/future signal | **Engram topic**: `cos/stage2-selective-expansion-plan` |
| [076](../adrs/ADR-076-skill-frontmatter-alignment.md) | `accepted` | `partial` | accepted record with explicit partial/phase scope | **Engram topic**: `cos/tier2-hermes-alignment` |
| [077](../adrs/ADR-077-peer-card-local-model.md) | `accepted` | `partial` | implementation evidence plus partial/deferred/future signal | **Engram topic**: `cos/tier2-hermes-alignment` |
| [078](../adrs/ADR-078-mid-task-memory-tool.md) | `accepted` | `partial` | implementation evidence plus partial/deferred/future signal | **Deciders**: Maintainer |
| [079](../adrs/ADR-079-corerules-applies-to-self-hosting.md) | `accepted` | `partial` | implementation evidence plus partial/deferred/future signal | **Author**: Maintainer |
| [080](../adrs/ADR-080-hermes-cross-harness-adoption.md) | `accepted` | `implemented` | explicit accepted/implemented status | **Author**: Maintainer |
| [081](../adrs/ADR-081-codex-harness-adapter.md) | `accepted` | `partial` | implementation evidence plus partial/deferred/future signal | **Author**: Maintainer |
| [082](../adrs/ADR-082-plan-location-convention.md) | `accepted` | `partial` | implementation evidence plus partial/deferred/future signal | **Author**: Maintainer |
| [083](../adrs/ADR-083-governed-self-improvement-loop.md) | `accepted` | `partial` | accepted/implemented text with explicit partial/deferred scope | **Author**: Maintainer |
| [086](../adrs/ADR-086-hook-execution-observability.md) | `accepted` | `partial` | accepted record with explicit partial/phase scope | Accepted. The canonical number is ADR-086; ADR-085 was an abandoned contested reservation during the concurrent ADR slot race documented by ADR-089. |
| [087](../adrs/ADR-087-adr-namespace-consolidation.md) | `accepted` | `partial` | accepted record with explicit pending/deferred/planned scope | **Author**: Maintainer |
| [088](../adrs/ADR-088-provenance-trailer-ppid-chain.md) | `accepted` | `not-applicable` | accepted decision/policy record with no explicit implementation surface | Accepted. |
| [089](../adrs/ADR-089-multi-session-git-coordination.md) | `accepted` | `partial` | implementation evidence plus partial/deferred/future signal | **Author**: Maintainer |
| [090](../adrs/ADR-090-auto-skill-repair.md) | `accepted` | `partial` | accepted record with explicit pending/deferred/planned scope | **Author**: Maintainer (COS sub-agent) |
| [091](../adrs/ADR-091-headless-clustered-runtime-direction.md) | `accepted` | `partial` | accepted/implemented text with explicit partial/deferred scope | - **Status**: Accepted as direction, not yet implemented as a production cluster |
| [092](../adrs/ADR-092-harness-skills-sync-path.md) | `accepted` | `not-applicable` | accepted decision/policy record with no explicit implementation surface | As of 2026-04-16, the project has 126 skill directories under `skills/`. The Claude Code harness |
| [093](../adrs/ADR-093-simplify-profiles.md) | `accepted` | `partial` | implementation evidence plus partial/deferred/future signal | Accepted (2026-04-16) |
| [094](../adrs/ADR-094-agent-git-safety.md) | `accepted` | `partial` | accepted record with explicit partial/phase scope | Accepted (2026-04-16) |
| [095](../adrs/ADR-095-skill-synthesis-success-patterns.md) | `accepted` | `partial` | accepted record with explicit partial/phase scope | **Author**: Maintainer (COS sub-agent) |
| [096](../adrs/ADR-096-review-agent-pattern.md) | `accepted` | `partial` | implementation evidence plus partial/deferred/future signal | **Author**: Maintainer (COS sub-agent) |
| [097](../adrs/ADR-097-documentation-execution-audit.md) | `accepted` | `partial` | implementation evidence plus partial/deferred/future signal | - Status: Accepted |
| [098](../adrs/ADR-098-multi-agent-file-coordination.md) | `accepted` | `partial` | accepted/implemented text with explicit partial/deferred scope | **Author**: Maintainer |
| [099](../adrs/ADR-099-pre-agent-snapshot-copy-on-untracked.md) | `accepted` | `not-applicable` | accepted decision/policy record with no explicit implementation surface | **Supersedes**: (part of ADR-003 Mechanism A) |
| [100](../adrs/ADR-100-resource-governed-test-execution.md) | `accepted` | `implemented` | explicit accepted/implemented status | **Author**: Maintainer |
| [101](../adrs/ADR-101-intent-aware-rate-limiter.md) | `accepted` | `partial` | accepted/implemented text with explicit partial/deferred scope | **Author**: Maintainer |
| [102](../adrs/ADR-102-task-tracker-lifecycle.md) | `accepted` | `partial` | implementation evidence plus partial/deferred/future signal | Accepted. |
| [103](../adrs/ADR-103-audit-contract-lane-recovery.md) | `accepted` | `not-applicable` | accepted decision/policy record with no explicit implementation surface | Accepted. |
| [104](../adrs/ADR-104-startup-circuit-breaker.md) | `accepted` | `implemented` | implementation/shipped/delivered evidence | **Author**: Maintainer |
| [105](../adrs/ADR-105-claim-verification-contract.md) | `implemented` | `partial` | ADR status explicitly says Partially Implemented; verification hooks/scripts exist but the contract is not marked closed | **Author**: Maintainer |
| [106](../adrs/ADR-106-multi-session-safety-primitives.md) | `accepted` | `implemented` | explicit accepted/implemented status | **Author**: Maintainer |
| [107](../adrs/ADR-107-human-approved-rollback.md) | `accepted` | `partial` | accepted record with explicit partial/phase scope | **Author**: Maintainer |
| [108](../adrs/ADR-108-concurrent-agent-safety-layer.md) | `accepted` | `implemented` | explicit accepted/implemented status | **Author**: Maintainer + Cognitive OS |
| [109](../adrs/ADR-109-validation-capsule-worktree-isolation.md) | `accepted` | `implemented` | implementation/shipped/delivered evidence | Accepted — 2026-05-02. |
| [110](../adrs/ADR-110-preserve-branch-governance.md) | `accepted` | `partial` | accepted/implemented text with explicit partial/deferred scope | **Author**: Maintainer + Cognitive OS |
| [111](../adrs/ADR-111-core-consumer-concurrency-safety-boundary.md) | `accepted` | `partial` | accepted/implemented text with explicit partial/deferred scope | Accepted — Implemented 2026-05-02. Related: ADR-108, ADR-110. |
| [112](../adrs/ADR-112-codex-governed-tool-layer.md) | `accepted` | `not-applicable` | accepted decision/policy record with no explicit implementation surface | Accepted — 2026-05-02. |
| [113](../adrs/ADR-113-validation-capsule-liveness.md) | `accepted` | `implemented` | implementation/shipped/delivered evidence | Accepted — 2026-05-02. |
| [114](../adrs/ADR-114-hook-quality-system.md) | `accepted` | `not-applicable` | accepted decision/policy record with no explicit implementation surface | Accepted — 2026-05-02. |
| [115](../adrs/ADR-115-safe-worktree-sweeper.md) | `accepted` | `implemented` | implementation/shipped/delivered evidence | Accepted — 2026-05-02. Scope: OS core. Related: ADR-109, ADR-111, ADR-113. |
| [116](../adrs/ADR-116-multi-session-coordination-primitives.md) | `accepted` | `partial` | multi-session primitive set spans multiple phases; implemented files exist but several coordination surfaces remain rollout scope | **Author**: Maintainer (operator) + Software Architect (analysis) |
| [118](../adrs/ADR-118-multi-ide-swarm-testbed.md) | `accepted` | `partial` | accepted record with explicit pending/deferred/planned scope | Accepted (2026-05-02). This is the automated acceptance-test umbrella for ADR-116 and its transactional coordination rollout. |
| [119](../adrs/ADR-119-session-filesystem-reaper.md) | `implemented` | `implemented` |  | Accepted — 2026-05-02. Related: ADR-102, ADR-106, ADR-111, ADR-116, ADR-117. |
| [120](../adrs/ADR-120-conversation-to-primitive-harvester.md) | `accepted` | `not-applicable` | accepted decision/policy record with no explicit implementation surface | Accepted — 2026-05-02 |
| [121](../adrs/ADR-121-foundation-hardening-program.md) | `accepted` | `partial` | program ADR tracks phased hardening invariants; S1/S4 evidence exists while remaining phases stay open | Accepted — 2026-05-02 |
| [122](../adrs/ADR-122-preflight-gate-refinements.md) | `accepted` | `not-applicable` | accepted decision/policy record with no explicit implementation surface | **Author**: Maintainer (operator) |
| [123](../adrs/ADR-123-operational-stability-friction-reduction.md) | `implemented` | `implemented` |  | Implemented — 2026-05-08 status sync |
| [127](../adrs/ADR-127-active-primitive-index.md) | `accepted` | `partial` | implementation evidence plus partial/deferred/future signal | Accepted for Phase 1 DX. |
| [129](../adrs/ADR-129-safe-worktree-removal.md) | `accepted` | `implemented` |  | Accepted. Implemented in commit `d5ecda43` with the shared |
| [130](../adrs/ADR-130-suspend-claude-api-workflows.md) | `accepted` | `implemented` |  | Accepted. |
| [131](../adrs/ADR-131-local-ci-migration.md) | `accepted` | `implemented` |  | Accepted. Implemented in the same PR that lands this ADR. Companion |
| [133](../adrs/ADR-133-expansion-without-monsterization.md) | `accepted` | `not-applicable` | accepted decision/policy record with no explicit implementation surface | Accepted — 2026-05-03 |
| [134](../adrs/ADR-134-headless-self-improvement-proposer.md) | `accepted` | `implemented` | implementation/shipped/delivered evidence | **Implementation**: `scripts/cos-self-improvement-loop` |
| [135](../adrs/ADR-135-self-evolving-doctrine-proposals.md) | `accepted` | `partial` | accepted record with explicit partial/phase scope | **Implementation**: `scripts/cos-doctrine-proposer` |
| [136](../adrs/ADR-136-cross-instance-learning-runway.md) | `accepted` | `partial` | implementation evidence plus partial/deferred/future signal | **Implementation**: `scripts/cos_cross_instance_learning.py` |
| [137](../adrs/ADR-137-operational-trajectory-governance-layer-to-embedded-runtime.md) | `accepted` | `planned` |  | **Accepted** for the trajectory itself. The directional commitment (B → A, defined below) is firm. |
| [138](../adrs/ADR-138-flow-contract-schema.md) | `accepted` | `implemented` |  | **Accepted and materialized for first lab registration.** The companion |
| [139](../adrs/ADR-139-account-agnostic-multi-provider-runtime.md) | `implemented` | `implemented` |  | **Accepted — Implemented** as the credential and billing posture for all COS runtime surfaces — local maintainer, cloud worker, and ephemeral sandbox. |
| [140](../adrs/ADR-140-cross-os-containerized-deployment.md) | `accepted` | `implemented` |  | **Accepted — Implemented** as the containerised deployment shape for COS cloud |
| [141](../adrs/ADR-141-engram-cloud-cross-instance-replication.md) | `implemented` | `implemented` |  | **Accepted — Implemented** as the replication strategy for Engram observations across COS instances. Local SQLite remains authoritative. Cloud is replication-on |
| [142](../adrs/ADR-142-compliance-audit-air-gapped-surface.md) | `implemented` | `implemented` |  | **Accepted — Implemented** as the compliance posture and audit-trail bridge for all COS cloud worker surfaces. |
| [143](../adrs/ADR-143-closure-discipline-gate.md) | `accepted` | `implemented` |  | **Accepted.** Closure discipline is now a first-class blocking maintainer gate. |
| [144](../adrs/ADR-144-hook-enforced-rule-projection-contract.md) | `accepted` | `implemented` |  | Accepted. Hook-enforced rule exclusions are now a projection contract, not a prose convention. |
| [145](../adrs/ADR-145-dependency-lane-split.md) | `accepted` | `implemented` | explicit accepted/implemented status | Date: 2026-05-04 |
| [146](../adrs/ADR-146-primitive-readiness-ledger.md) | `accepted` | `implemented` | implementation/shipped/delivered evidence | Accepted — 2026-05-04 |
| [147](../adrs/ADR-147-agent-capability-coverage-pipeline.md) | `accepted` | `partial` | accepted record with explicit partial/phase scope | Accepted — 2026-05-04 |
| [148](../adrs/ADR-148-adr-authoring-primitive.md) | `accepted` | `implemented` |  | **Accepted** — 2026-05-04 |
| [149](../adrs/ADR-149-primitive-duplication-audit.md) | `accepted` | `implemented` |  | **Accepted** — 2026-05-04 |
| [150](../adrs/ADR-150-acc-projection-profiles-and-harness-registry.md) | `accepted` | `implemented` |  | **Accepted** — 2026-05-04 |
| [151](../adrs/ADR-151-consumer-availability-classification.md) | `implemented` | `implemented` |  | **Implemented for manifest/classification scope** — 2026-05-04. The consumer availability manifest, ACC adapter, and contract tests named below exist; future sc |
| [152](../adrs/ADR-152-shell-ci-projection-and-local-surface-defaults.md) | `implemented` | `implemented` |  | **Implemented for shell/CI projection and local-surface defaults** — 2026-05-04. The projection manifest, projector, ACC integration, and artifact-status extrac |
| [153](../adrs/ADR-153-acc-fail-new-and-harness-proof-boundary.md) | `accepted` | `implemented` |  | **Accepted** — 2026-05-04 |
| [154](../adrs/ADR-154-multi-ide-structural-harness-projection.md) | `implemented` | `implemented` |  | **Implemented for structural projection scope** — 2026-05-04. OpenCode, VS Code Copilot, and Cursor project-local projections are generated and tested; this doe |
| [155](../adrs/ADR-155-shell-ci-formal-harness.md) | `accepted` | `implemented` |  | **Accepted** — 2026-05-04 |
| [156](../adrs/ADR-156-qwen-code-structural-harness-projection.md) | `implemented` | `implemented` |  | **Implemented for structural projection scope** — 2026-05-04. Qwen Code project-local settings/context projection is generated and tested; account-backed Qwen r |
| [157](../adrs/ADR-157-kimi-code-cli-structural-harness-projection.md) | `implemented` | `implemented` |  | **Implemented for structural CLI projection scope** — 2026-05-04. Kimi Code project-local CLI context/config projection is generated and tested; authenticated C |
| [158](../adrs/ADR-158-ai-agent-harness-landscape-and-proof-backlog.md) | `accepted` | `implemented` |  | **Accepted** — 2026-05-04 |
| [159](../adrs/ADR-159-agents-md-native-structural-harness-batch.md) | `accepted` | `implemented` |  | **Accepted** — 2026-05-05 |
| [160](../adrs/ADR-160-rules-mcp-structural-harness-batch-and-kiro-adapter-design.md) | `implemented` | `implemented` |  | **Implemented for structural projection and Kiro design scope** — 2026-05-05. The seven rules/MCP harness projections and Kiro adapter design artifacts exist an |
| [161](../adrs/ADR-161-remote-control-plane-and-provider-adapter-boundary.md) | `implemented` | `implemented` |  | **Implemented for boundary/inventory scope** — 2026-05-05. The remote ingress versus provider/executor adapter boundary, alternatives manifest, report, manual t |
| [162](../adrs/ADR-162-task-lifecycle-interruption-question-worktree-pr-protocol.md) | `implemented` | `partial` | implemented for contract scope; full queue/worker/PR runtime enforcement remains follow-up | **Implemented for contract scope** — 2026-05-05. The task lifecycle schema, contract tests, and manual proof checklist exist; full queue/worker/PR runtime enfor |
| [163](../adrs/ADR-163-cos-instance-installer.md) | `accepted` | `partial` | first implementation slice supports local/docker-headless profiles; future profiles remain planned/write-blocked | **Accepted** — 2026-05-05 |
| [164](../adrs/ADR-164-host-cli-bridge-security-boundary.md) | `implemented` | `implemented` | ADR scope is the design-only security contract; future host bridge execution is a separate implementation scope | **Implemented for the design-only security contract scope** — 2026-05-05. |
| [165](../adrs/ADR-165-proof-drill-and-smoke-opt-in-primitives.md) | `implemented` | `implemented` |  | **Implemented for the proof-drill registry and smoke opt-in primitive scope** — 2026-05-05. The ADR closes the governed registry, agent procedure, manual proof  |
| [166](../adrs/ADR-166-expected-skip-registry-and-opt-in-test-lanes.md) | `implemented` | `implemented` |  | **Implemented for the first enforcement slice** — 2026-05-05. |
| [167](../adrs/ADR-167-proof-drill-selector-and-acc-evidence-adapter.md) | `implemented` | `implemented` |  | **Implemented for the proof-drill selector, evidence recorder, ACC adapter, instance-profile projection, and runtime-flag registry scope** — 2026-05-05. Live pr |
| [168](../adrs/ADR-168-cross-device-dependency-installation.md) | `implemented` | `partial` | manifest-driven dry-run installer exists; setup delegation and richer automation remain follow-up | **Implemented for the manifest-driven dry-run installer and credential-safe |
| [169](../adrs/ADR-169-dashboard-formal-demotion.md) | `accepted` | `implemented` |  | Accepted. |
| [171](../adrs/ADR-171-reject-paperclip-integration.md) | `accepted` | `implemented` |  | Accepted. Supersedes ADR-043. |
| [172](../adrs/ADR-172-multi-surface-ui-architecture.md) | `accepted` | `not-applicable` | architecture/doctrine ADR assigns existing surfaces; implementation evidence is a snapshot rather than a direct work item | Accepted. Supersedes [ADR-170](ADR-170-operator-cli-as-primary-ui-surface.md). |
| [173](../adrs/ADR-173-surface-5-research-gate.md) | `accepted` | `deferred` |  | **Accepted** — 2026-05-06. |
| [174](../adrs/ADR-174-auto-derived-primitive-routing.md) | `accepted` | `implemented` |  | As of 2026-05-05, `lib/skill_router.py` contains a hand-maintained |
| [174b](../adrs/ADR-174b-prevention-followup.md) | `accepted` | `implemented` |  | Accepted. This ADR owns Part A (auto-generation includes `routing_patterns:`) and the implemented propose-only soak evaluator. The actual advisory-to-blocking p |
| [175](../adrs/ADR-175-research-quality-enforcement.md) | `accepted` | `implemented` |  | **Accepted** — 2026-05-05 |
| [176](../adrs/ADR-176-skillstore-and-analysis-trigger.md) | `accepted` | `implemented` |  | Accepted. |
| [177](../adrs/ADR-177-activate-skill-lifecycle-promotion-ladder.md) | `accepted` | `implemented` |  | Accepted. |
| [178](../adrs/ADR-178-openharness-primitive-adoption.md) | `accepted` | `not-applicable` | accepted decision/policy record with no explicit implementation surface | **Deciders**: Maintainer |
| [179](../adrs/ADR-179-rules-auto-derive-routing.md) | `accepted` | `partial` | initial PoC migrates five high-value rules while rule frontmatter migration remains incomplete | **Accepted** — 2026-05-05 |
| [180](../adrs/ADR-180-lifecycle-promotion-activation.md) | `accepted` | `implemented` |  | Accepted. |
| [181](../adrs/ADR-181-adr-relevance-suggester.md) | `accepted` | `implemented` |  | Accepted — 2026-05-05 |
| [182](../adrs/ADR-182-branch-ownership-lock.md) | `accepted` | `implemented` |  | **Accepted.** Implemented as the ADR-182 branch-lock hook, library, CLI wrappers, and contract tests. Filed in response to the cross-session collision incident |
| [183](../adrs/ADR-183-cross-session-event-log.md) | `accepted` | `implemented` |  | **Accepted.** Implemented as an extension of the existing `lib/session_bus.py` plus emit/context hooks. Companion to ADR-182. ADR-182 prevents *conflicts*; ADR- |
| [184](../adrs/ADR-184-manager-of-managers-daemon.md) | `accepted` | `implemented` |  | **Accepted.** First implementation landed as a local file-queue daemon for ADR identity arbitration. Long-horizon refinement of ADR-163 (cos-instance-installer) |
| [185](../adrs/ADR-185-cross-agent-audit-findings.md) | `accepted` | `implemented` |  | **Accepted.** Implemented as the directed message bus, inbox/context hooks, CLI, and tests. Fourth architectural layer companion to ADR-182 (branch |
| [186](../adrs/ADR-186-context-budget-enforcement.md) | `accepted` | `implemented` |  | **Accepted.** Implemented as `lib/context_budget.py`, a shared hook accountant, a UserPromptSubmit meter, and hook-level budget checks. Filed in response to tod |
| [188](../adrs/ADR-188-mandatory-skill-invocation-at-high-confidence.md) | `accepted` | `implemented` |  | **Accepted (2026-05-06).** Implementation landed on session branch |
| [189](../adrs/ADR-189-harness-implementation-coverage.md) | `accepted` | `implemented` | implementation/shipped/delivered evidence | Accepted — 2026-05-06 |
| [190](../adrs/ADR-190-harness-action-receipts.md) | `accepted` | `partial` | accepted record with explicit partial/phase scope | Accepted — 2026-05-06 |
| [191](../adrs/ADR-191-cos-binary-release-pipeline.md) | `accepted` | `partial` | accepted record with explicit partial/phase scope | Accepted — 2026-05-06 |
| [192](../adrs/ADR-192-surface-5-adopt-bubbletea.md) | `accepted` | `not-applicable` | accepted decision/policy record with no explicit implementation surface | Accepted — 2026-05-06 |
| [193](../adrs/ADR-193-cosd-local-network-api.md) | `accepted` | `partial` | implementation evidence plus partial/deferred/future signal | Accepted — 2026-05-06 |
| [194](../adrs/ADR-194-cosd-secure-remote-api.md) | `accepted` | `partial` | implementation evidence plus partial/deferred/future signal | Accepted — 2026-05-06 |
| [195](../adrs/ADR-195-surface-5-operable-tui-contract.md) | `accepted` | `partial` | accepted record with explicit partial/phase scope | Accepted — 2026-05-06 |
| [196](../adrs/ADR-196-cosd-task-api-and-provider-boundary.md) | `accepted` | `partial` | accepted record with explicit pending/deferred/planned scope | Accepted — 2026-05-06 |
| [197](../adrs/ADR-197-surface-5-operable-actions.md) | `accepted` | `partial` | accepted record with explicit pending/deferred/planned scope | Accepted — 2026-05-06 |
| [198](../adrs/ADR-198-release-external-readiness-gate.md) | `accepted` | `not-applicable` | accepted decision/policy record with no explicit implementation surface | Accepted — 2026-05-06 |
| [199](../adrs/ADR-199-state-retention-policy-and-reaper-protocol.md) | `accepted` | `implemented` | implementation/shipped/delivered evidence | Accepted — 2026-05-06 |
| [200](../adrs/ADR-200-state-retention-controller.md) | `accepted` | `not-applicable` | accepted decision/policy record with no explicit implementation surface | Accepted — 2026-05-06 |
| [201](../adrs/ADR-201-maintainer-agent-telemetry-promotion-loop.md) | `accepted` | `implemented` | explicit accepted/implemented status | **Report**: `docs/reports/self-improvement-maintainer-agent-gap-2026-05-06.md` |
| [202](../adrs/ADR-202-private-content-cross-harness-portability-boundary.md) | `accepted` | `implemented` | explicit accepted/implemented status | **Report**: `docs/reports/private-content-portability-gap-2026-05-06.md` |
| [203](../adrs/ADR-203-subagent-capability-contract-and-launch-preflight.md) | `accepted` | `not-applicable` | accepted decision/policy record with no explicit implementation surface | **Implementation**: `manifests/subagent-capabilities.yaml`, `scripts/subagent_launch_preflight.py`, `scripts/cos subagent preflight` |
| [204](../adrs/ADR-204-signal-quality-and-reward-integrity-boundary.md) | `accepted` | `partial` | accepted/implemented text with explicit partial/deferred scope | Accepted — implemented |
| [205](../adrs/ADR-205-cross-stream-trace-joiner-and-flight-recorder.md) | `accepted` | `partial` | accepted/implemented text with explicit partial/deferred scope | Accepted — implemented |
| [206](../adrs/ADR-206-aspirational-claim-decommission-gate.md) | `accepted` | `partial` | implementation evidence plus partial/deferred/future signal | **Source**: `.cognitive-os/strategy/research/03-aspirational-dormant.md`, `.cognitive-os/strategy/00-first-approach.md`, `.cognitive-os/strategy/02-pre-launch-p |
| [208](../adrs/ADR-208-imported-pattern-closure-contract.md) | `accepted` | `partial` | implementation evidence plus partial/deferred/future signal | **Source**: `.cognitive-os/strategy/research/05-hermes-imitation-forensics.md`, `.cognitive-os/strategy/research/06-external-patterns-benchmark.md` |
| [209](../adrs/ADR-209-maintainer-reconciler-experiment-contract.md) | `accepted` | `partial` | implementation evidence plus partial/deferred/future signal | **Source**: `.cognitive-os/strategy/research/06-external-patterns-benchmark.md`, `.cognitive-os/strategy/research/08-self-improvement-roadmap.md` |
| [210](../adrs/ADR-210-fleet-aggregated-confidence-boundary.md) | `accepted` | `implemented` | explicit accepted/implemented status | Accepted — Slice A dry-run exporter implemented |
| [211](../adrs/ADR-211-service-mode-readiness-gate.md) | `accepted` | `partial` | accepted/implemented text with explicit partial/deferred scope | Accepted — initial readiness gate implemented |
| [212](../adrs/ADR-212-cross-stack-license-audit-toolchain.md) | `accepted` | `not-applicable` | accepted decision/policy record with no explicit implementation surface | **Source**: Q2 tool-adoption review, `.cognitive-os/strategy/research/11-cross-stack-license-audit-tools.md` |
| [213](../adrs/ADR-213-agent-preflight-before-stash-snapshot.md) | `accepted` | `implemented` | implementation/shipped/delivered evidence | **Source**: `docs/reports/stash-hidden-wip-postmortem-2026-05-06.md` |
| [215](../adrs/ADR-215-cross-stack-secret-audit-toolchain.md) | `accepted` | `partial` | implementation evidence plus partial/deferred/future signal | **Source**: Q3 tool-adoption review (cross-stack secret/credential/PII detection), |
| [216](../adrs/ADR-216-tool-discovery-pre-use-gate.md) | `accepted` | `not-applicable` | accepted decision/policy record with no explicit implementation surface | **Source**: repeated dogfood evidence of ad-hoc external tool selection over existing COS primitives |
| [217](../adrs/ADR-217-cross-stack-adoption-truth-audit.md) | `accepted` | `partial` | implementation evidence plus partial/deferred/future signal | **Source**: Operator question — *"falta análisis de si está adoptado ya y de qué forma (esto también debería estar en las primitivas)"* |
| [218](../adrs/ADR-218-history-sanitization-toolchain.md) | `accepted` | `partial` | implementation evidence plus partial/deferred/future signal | **Source**: Operator question — *"cómo depuramos lo que está en git sobre datos sensibles y estos cambios de licencias sin crear un repo nuevo?"* |
| [219](../adrs/ADR-219-work-ownership-liveness-preflight.md) | `accepted` | `implemented` | implementation/shipped/delivered evidence | During the license-switch work, WIP was preserved to a temporary branch |
| [220](../adrs/ADR-220-worktree-divergence-audit.md) | `accepted` | `partial` | implementation evidence plus partial/deferred/future signal | **Source**: Operator session 2026-05-06 — sed-fix on `.cognitive-os/preserve-manifests/*` appeared "lost" because commits landed on `main` while the operator wa |
| [221](../adrs/ADR-221-stash-ref-by-sha-not-by-position.md) | `accepted` | `partial` | implementation evidence plus partial/deferred/future signal | **Supersedes (in part)**: the marker-file format produced by `pre-agent-snapshot.sh` and consumed by `post-agent-snapshot-restore.sh`. |
| [222](../adrs/ADR-222-pre-agent-stash-defer-until-launch-confirmed.md) | `accepted` | `implemented` | explicit accepted/implemented status | **Supersedes (in part)**: the PreToolUse-Agent ordering currently relied on by `pre-agent-snapshot.sh`. |
| [223](../adrs/ADR-223-agent-lifecycle-reconstruction.md) | `accepted` | `implemented` | explicit accepted/implemented status | **Source**: `docs/research/multi-agent-orchestration-prior-art-2026-05-06.md`, `docs/research/orchestration-gaps/background-agent-patterns.md`, and the operator |
| [225](../adrs/ADR-225-branch-per-task-mode.md) | `accepted` | `partial` | explicit not implemented yet signal | Worktree-per-write-agent isolates filesystem mutations, but branch identity still needs a stable operator-visible contract. Without a branch-per-task policy, de |
| [226](../adrs/ADR-226-event-sourced-session-bus.md) | `accepted` | `partial` | accepted/implemented text with explicit partial/deferred scope | **Extends**: **ADR-205 (Cross-Stream Trace Joiner and Flight Recorder)** — ADR-226 is an *extension* of the Flight Recorder's append-only event substrate, not a |
| [227](../adrs/ADR-227-shadow-git-checkpoint-substrate.md) | `accepted` | `implemented` | explicit accepted/implemented status | **Source**: [`docs/research/orchestration-gaps/replay-timeline-architectures.md`](../research/orchestration-gaps/replay-timeline-architectures.md). Cline, Herme |
| [228](../adrs/ADR-228-retry-contract-and-cost-budget.md) | `accepted` | `implemented` | explicit accepted/implemented status | Accepted — Slices A–F implemented (2026-05-07) |
| [230](../adrs/ADR-230-handoff-envelope-and-cycle-deduplication.md) | `accepted` | `implemented` | explicit accepted/implemented status | **Source**: [`docs/research/orchestration-gaps/agent-to-agent-handoff.md`](../research/orchestration-gaps/agent-to-agent-handoff.md). Production failure rate of |
| [231](../adrs/ADR-231-mcp-server-surface-for-cos-primitives.md) | `accepted` | `implemented` | explicit accepted/implemented status | **Source**: [`docs/research/orchestration-gaps/mcp-as-orchestration-bus.md`](../research/orchestration-gaps/mcp-as-orchestration-bus.md) |
| [232](../adrs/ADR-232-sandbox-adapter-tiers.md) | `accepted` | `implemented` | explicit accepted/implemented status | COS needs filesystem/process permission boundaries that are enforced below the prompt layer. Prior-art research recommends OS-native sandbox tiers first: Bubble |
| [233](../adrs/ADR-233-cross-session-agent-team-file-ipc.md) | `accepted` | `implemented` | explicit accepted/implemented status | **Source**: [`docs/research/orchestration-gaps/cross-session-agent-teams.md`](../research/orchestration-gaps/cross-session-agent-teams.md) |
| [234](../adrs/ADR-234-approval-policies-as-code.md) | `accepted` | `partial` | explicit not implemented yet signal | COS has many shell hooks with embedded allow/deny logic. Research recommended a COS-native YAML policy evaluator before adopting heavy engines such as OPA, Ceda |
| [235](../adrs/ADR-235-detached-agent-daemon.md) | `accepted` | `implemented` | explicit accepted/implemented status | **Source**: [`docs/research/orchestration-gaps/background-agent-patterns.md`](../research/orchestration-gaps/background-agent-patterns.md) |
| [236](../adrs/ADR-236-deferred-tool-loading-and-toolsearch.md) | `accepted` | `partial` | explicit not implemented yet signal | The orchestration research recommended adopting the ToolSearch/deferred-loading pattern instead of loading every tool schema into every session. This is not a s |
| [237](../adrs/ADR-237-test-execution-efficiency-protocol.md) | `accepted` | `implemented` | explicit accepted/implemented status | Cognitive OS test lanes are intentionally broad: unit, behavior, integration, chaos, benchmark, audit, smoke, cross-harness, and release gates. Running `make te |
| [239](../adrs/ADR-239-isolated-worktree-default-for-write-agents.md) | `accepted` | `implemented` |  | Accepted. This ADR records the corrective decision after the 2026-05-08 |
| [240](../adrs/ADR-240-primitive-coherence-audit-and-ownership-manifest.md) | `accepted` | `implemented` | explicit accepted/implemented status | status: accepted |
| [241](../adrs/ADR-241-consolidated-cos-bypass-allowlist.md) | `accepted` | `partial` | Slice A resolver/hook integration is active; broad ecosystem bypass consolidation remains future expansion | Accepted — Slice A implemented. Shared resolver, cheatsheet, target hook integration, and behavior tests are active; broad ecosystem bypass consolidation remain |
| [242](../adrs/ADR-242-git-filter-repo-wrapper-preserves-remote.md) | `accepted` | `implemented` | wrapper, library delegation, recovery artifacts, idempotency guard, and behavior tests satisfy the ADR acceptance criteria | Accepted — Slice A implemented. `scripts/cos-filter-repo-wrap.sh` preserves remotes, refuses idempotent reruns, writes recovery artifacts, and `lib/history_sani |
| [243](../adrs/ADR-243-post-rewrite-push-collision-exception.md) | `accepted` | `implemented` | history rewrite receipt and push-collision exception are implemented; future expires_at is an enhancement not core closure | Accepted — Slice A implemented. History sanitization writes `.cognitive-os/runtime/last-rewrite.json`; push-collision detection consumes it to allow matching po |
| [244](../adrs/ADR-244-trust-report-claim-validator-must-enforce.md) | `accepted` | `implemented` | claim enforcer, blocking hook behavior, rule update, and behavior tests satisfy the ADR enforcement scope | Accepted — Slice A implemented. `scripts/claim_enforcer.py` enforces structured `verification:` evidence for high-stakes claims, `hooks/claim-validator.sh` bloc |
| [245](../adrs/ADR-245-chaos-tests-readonly-production-source.md) | `accepted` | `implemented` | chaos read-only workspace fixture and regression tests satisfy the ADR source-protection scope | Accepted — Slice A implemented. `tests/chaos/conftest.py` installs `chaos_readonly_workspace`, restores source mutations under `lib/`, `scripts/`, and `hooks/`, |
| [246](../adrs/ADR-246-release-transaction-freeze.md) | `accepted` | `partial` | Slice A read-only/lock-file freeze exists; future slices explicitly remain open | Accepted — Slice A implemented. `scripts/cos-release-freeze` now provides `--prepare`, `--begin`, `--status`, and `--end`; receipts are written under `.cognitiv |
| [247](../adrs/ADR-247-manifest-driven-postmortem-regression-audits.md) | `accepted` | `implemented` | manifest-driven audit, runner, runbook, and verification commands implement the policy correction scope | Accepted. This ADR documents the policy correction made after ADR-242 through |
| [248](../adrs/ADR-248-control-plane-audit-loop.md) | `accepted` | `partial` | hook-fast/control-plane loop is wired; broader hourly scheduler and future remediation surfaces remain open | Accepted — Slice A implemented. |
| [249](../adrs/ADR-249-primitive-behavioral-proof-anti-overfit-tests.md) | `accepted` | `partial` | Slice A critical contracts exist; broader chaos/race hardening remains escalation/future scope | Accepted — Slice A implemented. |
| [250](../adrs/ADR-250-skill-router-retrieval-adapter-boundary.md) | `accepted` | `implemented` | boundary manifest, audit, benchmark fixtures, and tests implement the retrieval adapter boundary scope | Accepted — Slice A implemented. |
| [251](../adrs/ADR-251-agent-orchestration-adapter-boundary.md) | `accepted` | `implemented` | boundary manifest, audit, benchmark fixtures, and tests implement the orchestration adapter boundary scope | Accepted — Slice A implemented. |
| [252](../adrs/ADR-252-capability-coverage-matrix-and-feature-reality-ledger.md) | `accepted` | `partial` | Slice A establishes the matrix for ADR-230+; historical COS feature classification remains intentionally incomplete | Accepted — Slice A implemented. |
| [254](../adrs/ADR-254-external-tool-intelligence-plane-and-project-overlays.md) | `accepted` | `partial` | accepted record with explicit partial/phase scope | status: accepted |
| [255](../adrs/ADR-255-feature-to-external-tool-due-diligence.md) | `accepted` | `implemented` | explicit accepted/implemented status | Accepted — Slice A implemented |
| [256](../adrs/ADR-256-primitive-contract-registry-and-runtime-evidence-ledger.md) | `accepted` | `implemented` | explicit accepted/implemented status | Accepted — implemented through Phases 1–6; all primitive-lifecycle rows are registry-backed; OpenCode signed smoke covers the first 20 runtime primitives |
| [257](../adrs/ADR-257-primitive-contract-registry-phase-1.md) | `accepted` | `partial` | accepted/implemented text with explicit partial/deferred scope | Accepted — implemented |
| [258](../adrs/ADR-258-portable-ai-overlay-for-agentic-primitives.md) | `accepted` | `partial` | accepted/implemented text with explicit partial/deferred scope | Accepted — generated overlay implemented; canonical migration intentionally deferred |
| [259](../adrs/ADR-259-external-pattern-adoption-posture.md) | `accepted` | `partial` | accepted record with explicit partial/phase scope | **Date:** 2026-05-11 |
| [260](../adrs/ADR-260-grant-signed-cosd-api.md) | `accepted` | `not-applicable` | accepted decision/policy record with no explicit implementation surface | **Date:** 2026-05-11 |
| [261](../adrs/ADR-261-memory-governance-v2.md) | `accepted` | `not-applicable` | accepted decision/policy record with no explicit implementation surface | **Date:** 2026-05-11 |
| [263](../adrs/ADR-263-tool-replay-budget-ledger.md) | `accepted` | `not-applicable` | accepted decision/policy record with no explicit implementation surface | **Date:** 2026-05-11 |
| [264](../adrs/ADR-264-tool-result-envelope.md) | `accepted` | `not-applicable` | accepted decision/policy record with no explicit implementation surface | **Date:** 2026-05-11 |
| [267](../adrs/ADR-267-license-compliance-enforcement-architecture.md) | `accepted` | `partial` | accepted record with explicit pending/deferred/planned scope | Accepted (2026-05-11) |
| [268](../adrs/ADR-268-history-sanitization-2026-05-11.md) | `accepted` | `not-applicable` | accepted decision/policy record with no explicit implementation surface | Accepted (2026-05-11) |
| [269](../adrs/ADR-269-mandatory-adr-reference-for-history-rewrites.md) | `accepted` | `implemented` |  | Accepted (2026-05-11). Implementation lands in companion commit set. |
| [270](../adrs/ADR-270-legal-compliance-workflow-automation.md) | `accepted` | `implemented` |  | Accepted (2026-05-11). Implementation lands in companion commit. |
| [272](../adrs/ADR-272-structural-rule-backend-boundary.md) | `accepted` | `not-applicable` | accepted decision/policy record with no explicit implementation surface | Status: Accepted |
| [273](../adrs/ADR-273-pending-truth-ledger-and-bilateral-verification.md) | `accepted` | `partial` | Slices A and B are implemented; Slice C hook deployment is staged and pending operator authorization | Accepted — Slices A + B implemented; Slice C designed and staged (deployment requires operator authorization via `COS_ALLOW_PROTECTED_CONFIG_WRITE=1` per `hooks |
| [274](../adrs/ADR-274-operational-guide-required-for-capability-adrs.md) | `accepted` | `partial` | Slice A audit and Phase 1 enforcement exist; P1/P2 backfill and trust-score integration remain future scope | Accepted — Slice A implemented (audit + Phase 1 enforcement). |

## 2026-05-12 Partial Basis Audit

Reviewed the 23 tracked `Active / Partial` ADRs that had no `classification_basis`. Nine were reclassified out of `partial` where the ADR's own scope/evidence supported closure: eight to `implemented` and one architecture/doctrine ADR to `not-applicable`. The remaining fourteen now carry explicit basis text instead of a blank classification.

## Remaining Work

- No tracked ADR remains `Active / Unclassified` in the generated index.
- Future ADRs with YAML frontmatter fail audit if `implementation_status` is missing or invalid.
- Untracked local ADR drafts are intentionally outside this report until they are staged/tracked.
