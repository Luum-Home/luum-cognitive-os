# ADR Implementation Closure Session — 2026-05-04

> Separate session document for closing the historical ADR implementation ledger up to ADR-138 without blindly implementing obsolete decisions.

## Goal

Conclude, with evidence, that every ADR up to ADR-138 is either implemented, intentionally superseded, obsolete-by-context, deferred with an explicit blocker, or converted into a current implementation task.

## Non-negotiable constraint

Do **not** attack every old ADR as code. Many older ADRs may have been absorbed by later architectural decisions, invalidated by the current reconstruction phase, or reduced to documentation/evidence drift. The work is to reconcile first, implement only when the decision is still current.

## Current ledger snapshot

Generated with:

```bash
python3 scripts/adr_implementation_ledger.py --json
```

- Total ADR records in ledger: `147`
- Ledger implementation counts: `{'blocked': 7, 'implemented': 79, 'pending': 14, 'pending_evidence': 32, 'reserved': 4, 'superseded': 1, 'unknown': 10}`
- ADRs up to ADR-138 requiring attention: `50`
- Up-to-ADR-138 attention split: `{'pending_evidence': 25, 'pending': 8, 'unknown': 10, 'blocked': 7}`

## Closure taxonomy

| Closure class | Meaning | Allowed action |
|---|---|---|
| `implement-current` | The ADR still describes desired current behavior and lacks implementation. | Implement code/config/tests/docs. |
| `evidence-only` | Runtime exists, but ADR status, evidence, or ledger signals are stale. | Update ADR evidence, docs, ledger rules, or tests; do not change runtime unless drift is found. |
| `superseded` | A later ADR intentionally replaced this ADR. | Mark as superseded and link the newer ADR. |
| `absorbed` | A later implementation/architecture satisfies the useful part without one-to-one mapping. | Document absorption and evidence. |
| `obsolete-by-context` | The ADR solved an old architecture problem that no longer applies. | Close as no-op with rationale. |
| `deferred` | The decision is still valid but intentionally postponed. | Record blocker, acceptance criteria, and re-entry trigger. |
| `blocked` | External dependency or unresolved design question prevents closure. | Preserve blocker and add a focused unblock plan. |

## Acceptance criteria for this session

1. Every ADR up to ADR-138 with `pending`, `pending_evidence`, `unknown`, or `blocked` is assigned exactly one closure class.
2. No implementation commit is made for an ADR until newer ADRs and current architecture are checked for supersession or absorption.
3. Every `implement-current` ADR gets concrete files, tests, and validation commands.
4. Every `evidence-only`, `superseded`, `absorbed`, or `obsolete-by-context` ADR gets durable rationale and cross-links.
5. The ledger can distinguish real implementation gaps from documentation/evidence drift after the pass.

## Initial attack order

1. **Reconciler first**: classify the 50 attention ADRs below, oldest-to-newest only when dependencies are unknown; otherwise group related ADR families.
2. **Old infra cluster**: ADR-001/002/006/007/008/009/010/011/014/015/017/018/020/021/022/023/025.
3. **Reliability/observability cluster**: ADR-028/a/b, ADR-030/031/033/034/037/042/044.
4. **Provider/cross-harness cluster**: ADR-049/054/057/058/060/065/069.
5. **Self-improvement/hook safety cluster**: ADR-083/086/088/090/092/093/097/099/103/104/107/110/112/113/114/115.
6. **Then continue post-138 backlog**: ADR-139..142 and current cloud-flow/concurrency/stash/doc-drift items, only after the historical ledger is no longer ambiguous.

## Attention ledger up to ADR-138

| ADR | Ledger state | Decision state | Required closure class | Evidence notes |
|---|---|---|---|---|
| [ADR-001-abc-parallel-dedup-fix-broken-infra-add-global-verify](adrs/ADR-001-abc-parallel-dedup-fix-broken-infra-add-global-verify.md) | `pending_evidence` | `draft` | `evidence-only` | ADR-001: A+B+C parallel — dedup, fix broken infra, add global-verify — Evidence references exist, but the ADR does not state completion clearly **Batch-1 classification:** Auto-generated draft already records source commit `dacd7dc`, global-verify hook, targeted tests, and remaining aspirational items; closure action is status/evidence promotion, not new runtime. |
| [ADR-002-docker-pip-localhost-envs-targetedtestresolver-redis-dep](adrs/ADR-002-docker-pip-localhost-envs-targetedtestresolver-redis-dep.md) | `pending` | `draft` | `evidence-only` | ADR-002: docker-pip localhost envs + targeted_test_resolver + redis dep — Decision exists, but implementation evidence was not found **Batch-1 classification:** Auto-generated draft already records source commit `e4a3c86`, env-var Valkey defaults, targeted_test_resolver, and validation notes; closure action is status/evidence promotion plus checking the old EXCLUDED_HOOKS note. |
| [ADR-006-agpl-license-compliance](adrs/ADR-006-agpl-license-compliance.md) | `unknown` | `missing_status` | `evidence-only` | ADR-006: AGPL License Compliance -- Replace Redis and MinIO — No reliable implementation status signal was found **Batch-1 classification:** ADR already says Accepted with commit evidence; ledger likely misses bold status syntax. Closure action is parser/evidence reconciliation, not replacing services again. |
| [ADR-007-cognitive-os-rebrand](adrs/ADR-007-cognitive-os-rebrand.md) | `unknown` | `missing_status` | `evidence-only` | ADR-007: Rebrand from Agent OS to Cognitive OS — No reliable implementation status signal was found **Batch-1 classification:** ADR already says Accepted and current repo is branded Cognitive OS; any remaining Agent OS mentions need context filtering for historical references only. |
| [ADR-008-multi-tool-support](adrs/ADR-008-multi-tool-support.md) | `unknown` | `missing_status` | `absorbed` | ADR-008: Multi-Tool Support -- Not Claude Code-Only — No reliable implementation status signal was found **Batch-1 classification:** Current cross-harness posture is governed by later harness/adapter ADRs; do not re-implement old multi-tool shape without reconciling ADR-057/064/081/112/124. |
| [ADR-009-package-architecture](adrs/ADR-009-package-architecture.md) | `unknown` | `missing_status` | `absorbed` | ADR-009: Package Architecture -- 375 Agentic Primitives Reclassified — No reliable implementation status signal was found **Batch-1 classification:** Package/reclassification intent is now covered by distribution boundaries and primitive lifecycle governance; reconcile against ADR-124/126 before touching packaging. |
| [ADR-010-hook-architecture-v2](adrs/ADR-010-hook-architecture-v2.md) | `pending_evidence` | `missing_status` | `absorbed` | ADR-010: Hook Architecture v2 -- 10 Event Types, 3 Security Profiles — Evidence references exist, but the ADR does not state completion clearly **Batch-1 classification:** Original event/profile model predates later simplified profiles, distribution tiers, and hook projection contracts; reconcile via ADR-093/124/144 instead of restoring old profile assumptions. |
| [ADR-011-dual-gateway-bifrost-litellm](adrs/ADR-011-dual-gateway-bifrost-litellm.md) | `pending_evidence` | `missing_status` | `superseded` | ADR-011: Dual Gateway -- Bifrost Primary, LiteLLM Fallback — Evidence references exist, but the ADR does not state completion clearly **Batch-1 classification:** ADR explicitly says Superseded by ADR-018; no implementation attack unless a current provider ADR reintroduces a gateway need. |
| [ADR-014-sdd-fast-path](adrs/ADR-014-sdd-fast-path.md) | `pending_evidence` | `missing_status` | `evidence-only` | ADR-014: SDD Fast Path -- Skip Phases for Capable Models — Evidence references exist, but the ADR does not state completion clearly **Batch-1 classification:** ADR records implementation in `lib/sdd_pipeline.py` and commits; closure action is evidence/test verification. |
| [ADR-015-rules-to-hooks-migration](adrs/ADR-015-rules-to-hooks-migration.md) | `unknown` | `missing_status` | `absorbed` | ADR-015: Rules-to-Hooks Migration -- From Context to Enforcement — No reliable implementation status signal was found **Batch-1 classification:** The rule-to-enforcement direction is now constrained by ADR-143/144 closure and projection gates; do not migrate more rules blindly. |
| [ADR-017-stabilization-freeze](adrs/ADR-017-stabilization-freeze.md) | `unknown` | `missing_status` | `obsolete-by-context` | ADR-017: Stabilization Freeze -- No New Features Until Wiring Complete — No reliable implementation status signal was found **Batch-1 classification:** Temporal freeze decision was for the stabilization window; current project phase is reconstruction, so closure should document historical completion/expiry. |
| [ADR-018-docker-to-pip-migration](adrs/ADR-018-docker-to-pip-migration.md) | `pending_evidence` | `missing_status` | `evidence-only` | ADR-018: Docker-to-pip Migration -- Service Infrastructure Change — Evidence references exist, but the ADR does not state completion clearly **Batch-1 classification:** ADR records Accepted status and commits; closure action is evidence/ledger reconciliation and verifying current optional-service posture. |
| [ADR-020-contamination-fix](adrs/ADR-020-contamination-fix.md) | `unknown` | `missing_status` | `evidence-only` | ADR-020: Contamination Fix -- Remove Project-Specific Code from OS — No reliable implementation status signal was found **Batch-1 classification:** ADR records Accepted status and commit; closure action is contamination evidence/audit status, not new feature work. |
| [ADR-021-vendor-agnostic-with-adapters](adrs/ADR-021-vendor-agnostic-with-adapters.md) | `pending_evidence` | `missing_status` | `absorbed` | ADR-021: Vendor-Agnostic State with Provider Adapters — Evidence references exist, but the ADR does not state completion clearly **Batch-1 classification:** Adapter direction is superseded/extended by later cross-harness and account-agnostic provider runtime ADRs, especially ADR-139; reconcile before implementing old adapter assumptions. |
| [ADR-022-prompt-type-hooks-adoption](adrs/ADR-022-prompt-type-hooks-adoption.md) | `pending_evidence` | `missing_status` | `obsolete-by-context` | ADR-022: Prompt-Type Hooks Adoption (Haiku-Evaluated Advisories) — Evidence references exist, but the ADR does not state completion clearly **Batch-1 classification:** The model-specific Haiku framing should not be expanded; preserve generic advisory-hook behavior only where current gates still need it. |
| [ADR-023-updated-input-pattern](adrs/ADR-023-updated-input-pattern.md) | `unknown` | `missing_status` | `evidence-only` | ADR-023: Mutate, Don't Block — `updatedInput` for PreToolUse Hooks — No reliable implementation status signal was found **Batch-1 classification:** ADR has concrete references to `secret-detector`, `blast-radius`, and unit tests; closure action is evidence/test verification. |
| [ADR-025-install-update-loop](adrs/ADR-025-install-update-loop.md) | `unknown` | `missing_status` | `evidence-only` | ADR-025: Install/Update Loop — Closing the Advisory-Only Gap — No reliable implementation status signal was found **Batch-1 classification:** ADR has concrete references to `scripts/register-mcps.sh`, `scripts/cos-update.sh`, and behavior tests; closure action is evidence/test verification. |
| [ADR-028](adrs/ADR-028.md) | `blocked` | `accepted` | `evidence-only` | ADR-028: SO Reliability & Observability Framework — Open questions or dependency language indicate blocked work **Batch-2 classification:** Parent ADR states the 6-pillar framework is CLOSED and addenda resolved pending items; implementation evidence spans `lib/metric_event.py`, metrics rotation, MLflow timeout hardening, global-verify, and reports. Ledger blocker is historical language. | **Final classification:** Full framework says closed by addenda/commits; ledger open-question strings are stale acceptance text. Reconcile ADR evidence/parser only.
| [ADR-028a](adrs/ADR-028a.md) | `blocked` | `unknown` | `evidence-only` | ADR-028a — Addendum: Reconciliation with pre-existing plans — Open questions or dependency language indicate blocked work **Batch-2 classification:** Addendum reconciles WS11 and heartbeat overlap; global-verify and agent-bus boundaries now exist. Closure action is ledger/status reconciliation, not a new heartbeat system. | **Final classification:** Addendum records resolved items and commits; closure is evidence/status reconciliation.
| [ADR-028b](adrs/ADR-028b.md) | `blocked` | `unknown` | `evidence-only` | ADR-028b — Addendum: D1.C Replanned Around agent_bus — Open questions or dependency language indicate blocked work **Batch-2 classification:** Revised D1.C explicitly says do not create duplicate heartbeat primitives; `lib/agent_bus_metrics.py` and `tests/contracts/test_agent_bus_metrics.py` exist and passed in this session. | **Final classification:** agent_bus replanning has implementation evidence; close by evidence/status reconciliation, not new D1.C runtime.
| [ADR-030](adrs/ADR-030.md) | `blocked` | `proposed` | `evidence-only` | ADR-030 — Auto-trigger session-wrapup (Q1 prompt-match + Q2 commit banner) — Open questions or dependency language indicate blocked work **Batch-2 classification:** All acceptance surfaces are present: `hooks/session-wrapup-trigger.sh`, profile/settings registration, `AUTO-TRIGGER` preamble rule, `.githooks/post-commit`, `hooks/session-init.sh`, `skills/session-wrapup/SKILL.md`, and hermetic tests; ADR status is stale Proposed. | **Final classification:** Hook, prompt rule, and commit-banner evidence exist; close by verifying session-wrapup trigger evidence and ADR state.
| [ADR-031](adrs/ADR-031.md) | `pending_evidence` | `accepted` | `evidence-only` | ADR-031 — Continuous Aspirational/Dormant/Real Audit — Evidence references exist, but the ADR does not state completion clearly **Batch-2 classification:** `scripts/aspirational_audit.py`, `hooks/aspirational-audit-weekly.sh`, integration tests, and dated reports exist. Closure is evidence/status reconciliation. | **Final classification:** Aspirational audit script/hook/report path exists; close by evidence/status update.
| [ADR-033-harness-agnostic-event-capture](adrs/ADR-033-harness-agnostic-event-capture.md) | `pending_evidence` | `accepted` | `evidence-only` | ADR-033 — Harness-agnostic event capture layer — Evidence references exist, but the ADR does not state completion clearly **Batch-2 classification:** `lib/harness_adapter/`, `lib/event_bus.py`, `scripts/cos-events.sh`, canonical event contract tests, and portability tests exist. Closure is evidence/status reconciliation. | **Final classification:** Harness adapter/event capture exists; close by evidence mapping to current adapter contract.
| [ADR-034-harness-agnostic-live-streaming](adrs/ADR-034-harness-agnostic-live-streaming.md) | `pending_evidence` | `missing_status` | `evidence-only` | ADR-034 — Harness-Agnostic Live Agent Streaming — Evidence references exist, but the ADR does not state completion clearly **Batch-2 classification:** The Proposed status is stale: `scripts/cos_executor.py`, `scripts/cos_watch.py`, `lib/harness_adapter/aider_streaming.py`, and the three named tests exist and passed in this session. | **Final classification:** Streaming/agent bus evidence exists; close by evidence mapping and note any non-default live-stream features stay maintainer/lab.
| [ADR-037-self-knowledge-base](adrs/ADR-037-self-knowledge-base.md) | `pending_evidence` | `accepted` | `evidence-only` | ADR-037 — Self-Knowledge Base — Evidence references exist, but the ADR does not state completion clearly **Batch-2 classification:** `scripts/cos_build_self_knowledge.py`, `hooks/self-knowledge-refresh.sh`, `lib/self_knowledge.py`, generated `.cognitive-os/self-knowledge/` artifacts, and unit/integration tests exist and passed in this session. | **Final classification:** Commit and API-surface evidence exists; close by evidence/status update.
| [ADR-044-context-payload-slimming](adrs/ADR-044-context-payload-slimming.md) | `blocked` | `unknown` | `evidence-only` | ADR-044: Context Payload Slimming — Non-Rule Startup Payloads — Open questions or dependency language indicate blocked work **Batch-2 classification:** Phase-2 repo surfaces are present (`.claude/commands/*`, compact catalog generator, lazy catalog tests). This session fixed drift in `hooks/session-init.sh`, `scripts/generate_compact_catalog.py`, and regenerated `skills/CATALOG-COMPACT.md`; global user CLAUDE slimming remains opt-in/external, not repo implementation debt. | **Final classification:** Still depends on harness metadata behavior and context budget decisions; defer with re-entry trigger from preamble/session-start budget audits.
| [ADR-049-llm-gateway-selection-and-overflow-providers](adrs/ADR-049-llm-gateway-selection-and-overflow-providers.md) | `pending` | `accepted` | `absorbed` | ADR-049 — LLM Gateway Selection + Overflow Provider Strategy — Decision exists, but implementation evidence was not found | **Final classification:** Current provider/dispatch/account-agnostic runtime work supersedes the old gateway shape; reconcile under later provider ADRs instead.
| [ADR-054-project-docs-convention](adrs/ADR-054-project-docs-convention.md) | `pending_evidence` | `accepted` | `evidence-only` | ADR-054 — Project Documentation Convention (10 Categories) — Evidence references exist, but the ADR does not state completion clearly | **Final classification:** Scaffolder/skill/docs evidence exists; close by evidence/status update.
| [ADR-057-cross-harness-authoring-and-driver-projection](adrs/ADR-057-cross-harness-authoring-and-driver-projection.md) | `pending_evidence` | `accepted` | `evidence-only` | ADR-057: Cross-Harness Authoring and Driver Projection — Evidence references exist, but the ADR does not state completion clearly | **Final classification:** Current projection/adapter machinery exists; close by evidence mapping to ADR-081/111/144 era contracts.
| [ADR-058-observability-migration-langfuse-to-phoenix](adrs/ADR-058-observability-migration-langfuse-to-phoenix.md) | `unknown` | `missing_status` | `obsolete-by-context` | ADR-058 — Observability Migration: Langfuse → Arize Phoenix — No reliable implementation status signal was found | **Final classification:** Old vendor-specific migration is no longer current; optional/local observability posture supersedes it.
| [ADR-060-local-only-optional-services](adrs/ADR-060-local-only-optional-services.md) | `pending_evidence` | `accepted` | `evidence-only` | ADR-060 — Local-Only Policy for Optional Services — Evidence references exist, but the ADR does not state completion clearly | **Final classification:** Service catalog/evaluation evidence exists; close by evidence/status update.
| [ADR-065-radar-update-curation-pipeline](adrs/ADR-065-radar-update-curation-pipeline.md) | `pending_evidence` | `proposed` | `deferred` | ADR-065 — Tech Radar Curation Pipeline (`/radar-update`) — Evidence references exist, but the ADR does not state completion clearly | **Final classification:** Proposed radar workflow remains non-core; defer until external/curation trigger makes it valuable.
| [ADR-069-research-first-protocol](adrs/ADR-069-research-first-protocol.md) | `blocked` | `proposed` | `deferred` | ADR-069: Research-First Protocol for High-Risk Changes — Open questions or dependency language indicate blocked work | **Final classification:** Protocol is still useful but not automatically enforceable for all high-risk changes; defer as doctrine/gate follow-up.
| [ADR-083-governed-self-improvement-loop](adrs/ADR-083-governed-self-improvement-loop.md) | `pending` | `proposed` | `absorbed` | ADR-083 — Governed Self-Improvement Loop — Pending/unresolved language found and no implementation evidence was detected | **Final classification:** Absorbed by ADR-134/135 plus self-improvement discipline gate and claim-signature audit.
| [ADR-086-hook-execution-observability](adrs/ADR-086-hook-execution-observability.md) | `pending_evidence` | `accepted` | `evidence-only` | ADR-086: Hook Execution Observability — Evidence references exist, but the ADR does not state completion clearly | **Final classification:** Timing wrapper evidence exists; close by evidence/status update.
| [ADR-088-provenance-trailer-ppid-chain](adrs/ADR-088-provenance-trailer-ppid-chain.md) | `pending_evidence` | `accepted` | `evidence-only` | ADR-088 — Provenance trailer attribution via PPID chain — Evidence references exist, but the ADR does not state completion clearly | **Final classification:** Commit provenance script evidence exists; close by evidence/status update.
| [ADR-090-auto-skill-repair](adrs/ADR-090-auto-skill-repair.md) | `pending_evidence` | `accepted` | `evidence-only` | ADR-090: Auto-skill repair via failure-threshold signals — Evidence references exist, but the ADR does not state completion clearly | **Final classification:** Skill feedback tracker exists; close by evidence/status update while keeping repair automation non-core.
| [ADR-092-harness-skills-sync-path](adrs/ADR-092-harness-skills-sync-path.md) | `pending_evidence` | `accepted` | `absorbed` | ADR-092: Harness Skills Sync Path — Add `.claude/skills/` as Second Sync Destination — Evidence references exist, but the ADR does not state completion clearly | **Final classification:** Skill sync/namespace work was absorbed by later catalog/projection decisions; do not revive old Claude-only sync assumptions.
| [ADR-093-simplify-profiles](adrs/ADR-093-simplify-profiles.md) | `pending_evidence` | `accepted` | `evidence-only` | ADR-093: Simplify Install Profiles — Collapse 3-Tier System to `default` + `--full` — Evidence references exist, but the ADR does not state completion clearly | **Final classification:** Profile simplification evidence exists but current adoption-tier model supersedes raw lean/standard/full language; reconcile evidence/status.
| [ADR-097-documentation-execution-audit](adrs/ADR-097-documentation-execution-audit.md) | `pending` | `accepted` | `evidence-only` | ADR-097: Documentation Execution Audit — Decision exists, but implementation evidence was not found | **Final classification:** Docs execution reports exist; close by evidence/status update.
| [ADR-099-pre-agent-snapshot-copy-on-untracked](adrs/ADR-099-pre-agent-snapshot-copy-on-untracked.md) | `pending_evidence` | `accepted` | `evidence-only` | ADR-099 — Pre-agent snapshot: copy-on-untracked instead of stash-sweep — Evidence references exist, but the ADR does not state completion clearly | **Final classification:** Snapshot hook exists and current stash/snapshot bugs are handled by later ADR-117/119/132 controls; close evidence, keep cleanup in current backlog only if metrics regress.
| [ADR-103-audit-contract-lane-recovery](adrs/ADR-103-audit-contract-lane-recovery.md) | `pending_evidence` | `accepted` | `evidence-only` | ADR-103: Audit and contract lane recovery before parallel flip — Evidence references exist, but the ADR does not state completion clearly | **Final classification:** Audit/contract lane reports exist; close by evidence/status update.
| [ADR-104-startup-circuit-breaker](adrs/ADR-104-startup-circuit-breaker.md) | `pending_evidence` | `accepted` | `evidence-only` | ADR-104 — Startup Circuit Breaker and Safe Mode — Evidence references exist, but the ADR does not state completion clearly | **Final classification:** Startup recovery/timing evidence exists; close by evidence/status update, with future latency-vs-kill/safe-mode improvements tracked by current readiness gates.
| [ADR-107-human-approved-rollback](adrs/ADR-107-human-approved-rollback.md) | `pending` | `accepted` | `absorbed` | ADR-107 — Human-Approved Rollback Boundary — Decision exists, but implementation evidence was not found | **Final classification:** Rollback boundary is absorbed by current protected publication/approval/recovery primitives; reconcile evidence rather than adding autonomous rollback.
| [ADR-110-preserve-branch-governance](adrs/ADR-110-preserve-branch-governance.md) | `pending` | `proposed` | `absorbed` | ADR-110 — Preserve Branch Governance — Decision exists, but implementation evidence was not found | **Final classification:** Preserve branch governance is absorbed by WIP safety/worktree/branch-lease primitives.
| [ADR-112-codex-governed-tool-layer](adrs/ADR-112-codex-governed-tool-layer.md) | `pending` | `accepted` | `absorbed` | ADR-112 — Codex Governed Tool Layer — Decision exists, but implementation evidence was not found | **Final classification:** Codex governance absorbed by ADR-111/144 projection and portability gates; no separate old layer attack.
| [ADR-113-validation-capsule-liveness](adrs/ADR-113-validation-capsule-liveness.md) | `blocked` | `accepted` | `deferred` | ADR-113: Validation Capsule Liveness Primitives — Open questions or dependency language indicate blocked work | **Final classification:** Valid but not closed here; defer focused liveness primitives until validation-capsule metrics show stale-lock recurrence.
| [ADR-114-hook-quality-system](adrs/ADR-114-hook-quality-system.md) | `pending` | `accepted` | `evidence-only` | ADR-114 — Hook Quality System — Decision exists, but implementation evidence was not found | **Final classification:** Hook quality manifests/tests now exist; close by evidence/status reconciliation.
| [ADR-115-safe-worktree-sweeper](adrs/ADR-115-safe-worktree-sweeper.md) | `pending_evidence` | `accepted` | `evidence-only` | ADR-115: Safe Worktree Sweeper — Evidence references exist, but the ADR does not state completion clearly | **Final classification:** Sweeper scripts exist; close by evidence/status update.

## Batch 1 classification notes — old infra cluster

The first cluster is intentionally mostly **not** runtime implementation work. It contains auto-generated ADRs, historical stabilization decisions, and decisions later absorbed by cross-harness/distribution/provider ADRs. The next action for this batch is to update ADR statuses/evidence and, where useful, improve the ledger parser so accepted/superseded ADRs are not misreported as unknown.

Batch 1 covers ADR-001, ADR-002, ADR-006, ADR-007, ADR-008, ADR-009, ADR-010, ADR-011, ADR-014, ADR-015, ADR-017, ADR-018, ADR-020, ADR-021, ADR-022, ADR-023, and ADR-025.

## Batch 2 classification notes — reliability/observability cluster

The second cluster is also mostly **evidence/status closure**, with one real hardening fix discovered while validating ADR-044. ADR-028/028a/028b contain historical blocker language, but the parent ADR now declares the framework closed and the current code contains the replacement mechanisms. ADR-030 and ADR-034 still say Proposed even though their acceptance-test surfaces exist and pass locally. ADR-044 had actual lazy-catalog drift: `COS_LAZY_CATALOG` was not documented in `hooks/session-init.sh`, and internal contract skills could leak into `skills/CATALOG-COMPACT.md`; both were fixed in this pass.

Validation run for this batch:

```bash
python3 -m pytest tests/hooks/test_session_wrapup_trigger.py tests/integration/test_post_commit_banner.py tests/contracts/test_agent_bus_metrics.py tests/unit/test_event_bus.py tests/unit/test_self_knowledge_generator.py tests/unit/test_self_knowledge_query.py tests/integration/test_valkey_local_daemon.py -q
# 70 passed

python3 -m pytest tests/integration/test_executor_publishes_live.py tests/integration/test_cos_watch_renders.py tests/unit/test_aider_streaming_adapter.py -q
# 12 passed

python3 -m pytest tests/integration/test_lazy_catalog_end_to_end.py tests/unit/test_catalog_loading.py tests/unit/test_startup_budget.py -q
# 22 passed, 4 skipped
```

Batch 2 covers ADR-028, ADR-028a, ADR-028b, ADR-030, ADR-031, ADR-033, ADR-034, ADR-037, ADR-042, and ADR-044.

## Ledger metadata extension — post-cap ADRs

After wiring `manifests/adr-closure-metadata.yaml` into `scripts/adr_implementation_ledger.py`, the ledger surfaced additional ADRs up to ADR-138 that were hidden by the previous attention-list cap. These are now covered by closure metadata rather than being forced into runtime work:

| ADR | Closure class | Rationale |
|---|---|---|
| ADR-118 | `deferred` | Multi-IDE swarm testbed has an initial implemented slice; remaining scenarios are phase-level chaos coverage. |
| ADR-120 | `evidence-only` | Primitive harvester implementation, tests, and promotion evidence exist. |
| ADR-121 | `deferred` | Foundation hardening is a phased program tracked by its architecture plan. |
| ADR-122 | `evidence-only` | Preflight refinements are implemented and tested. |
| ADR-123 | `deferred` | Operational stability/friction reduction is a phased program with current slices plus remaining plan work. |
| ADR-124 | `evidence-only` | Distribution boundaries are represented in lifecycle/adoption metadata. |
| ADR-125 | `evidence-only` | Governance value boundaries are represented in lifecycle/distribution and claim-boundary evidence. |
| ADR-127 | `evidence-only` | Active primitive index and runtime coverage hardening exist. |
| ADR-128 | `evidence-only` | Data-layer integrity files/tests/audits exist. |
| ADR-135 | `evidence-only` | Doctrine proposer is a propose-only control-plane primitive. |
| ADR-136 | `evidence-only` | Cross-instance runway primitives and Shape-A deferral audit exist. |

ADR-144 is also closed as `evidence-only` in the metadata because the ledger scans all ADRs, not only ADR≤138. ADR-140 remains intentionally unclosed because its Docker Compose worker surface still requires separate implementation evidence.

## Working notes

- `pending_evidence` is not automatically implementation debt; it is a request for proof or status correction.
- `unknown` is high-risk because missing status can hide either obsolete decisions or real gaps.
- `blocked` must not be silently converted to done; it needs either an unblock plan or a supersession/obsolete rationale.
- ADR-138 is already materialized as first lab registration; its remaining condition is promotion to shared schema after a second flow registers unchanged.

## Validation commands

```bash
python3 scripts/adr_implementation_ledger.py --json
scripts/cos-closure-discipline-audit --fail-on-findings --json
bash scripts/cos-ci-local.sh quick
```

## Session log

- 2026-05-04: Created this separate ADR closure session document from the ledger snapshot. No ADR is declared closed by this document alone; closure requires classification plus evidence.


## Final classification summary

All ADRs up to ADR-138 that appeared as `pending`, `pending_evidence`, `unknown`, or `blocked` now have a closure class in this document. This document does **not** claim every ADR is implemented; it converts ambiguous backlog into one of: evidence/status reconciliation, absorbed/superseded/obsolete, or explicitly deferred.

Final counts for the 50-attention set:

| Closure class | Count | Meaning for next work |
|---|---:|---|
| `evidence-only` | 31 | Update ADR status/evidence/ledger parsing; do not write runtime unless validation finds drift. |
| `absorbed` | 11 | Later ADRs/current primitives satisfy or replace the useful part; cross-link instead of reimplementing old shape. |
| `superseded` | 1 | A later ADR explicitly replaces the decision. |
| `obsolete-by-context` | 3 | Historical decision no longer applies to reconstruction/current architecture. |
| `deferred` | 4 | Valid concern remains, but re-entry trigger is explicit and implementation now would be speculative. |
| `implement-current` | 0 | No ADR ≤138 should be attacked blindly as new runtime work from this reconciliation pass. |

### Deferred re-entry triggers

- ADR-044: reopen only if core preamble/session-start budgets regress or harness metadata behavior is empirically confirmed to support slimmer payload projection.
- ADR-065: reopen when a real `/radar-update` consumer asks for curation automation or external ecosystem evidence starts feeding product decisions.
- ADR-069: reopen when research-first failures recur or high-risk change classes need a blocking preflight rather than advisory doctrine.
- ADR-113: reopen when validation-capsule stale locks recur in metrics or `make test-laptop`/capsule runs produce stale-lock operator incidents.

### Current backlog boundary

Post-138 work remains outside this historical closure pass: cloud-flow bootstrap, Shape-B triggers, external adoption evidence, and future self-improvement promotions are governed by their newer ADRs and control-plane audits.
