# ADR Index

## How to Use This Index

This generated table is the status inventory for all 283 Architecture Decision Record files (ADRs).
Status semantics are defined in [STATUS-TAXONOMY.md](STATUS-TAXONOMY.md): decision status, implementation status, and index bucket are separate fields.
Rows link to the canonical ADR file and group by index bucket for human and agent navigation.

## Active

### Active / Implemented (49)

| ADR | Title | Decision Status | Implementation | Date | Summary |
|---|---|---|---|---|---|
| [052](ADR-052-provider-benchmark-harness.md) | Provider Benchmark Harness | implemented | implemented |  | **Implemented for the no-cost offline harness scope.** The repository now ships a |
| [053](ADR-053-dispatch-auto-optimizer.md) | Dispatch Auto-Optimizer | implemented | implemented |  | **Implemented for reviewed proposal generation.** The repository now ships a |
| [119](ADR-119-session-filesystem-reaper.md) | Session Filesystem Reaper | implemented | implemented | 2026-05-02 | Accepted — 2026-05-02. Related: ADR-102, ADR-106, ADR-111, ADR-116, ADR-117. |
| [123](ADR-123-operational-stability-friction-reduction.md) | Operational Stability and Friction Reduction Program | implemented | implemented | 2026-05-02 | Implemented — 2026-05-08 status sync |
| [129](ADR-129-safe-worktree-removal.md) | Safe Worktree Removal — No Silent rm -rf Fallback | accepted | implemented | 2026-05-02 | Accepted. Implemented in commit `d5ecda43` with the shared |
| [130](ADR-130-suspend-claude-api-workflows.md) | Suspend All GitHub Actions Workflows — Preserve as .disabled Until Local-CI Migration | accepted | implemented | 2026-05-03 | Accepted. |
| [131](ADR-131-local-ci-migration.md) | Local-CI Migration — Three-Layer Architecture to Replace GitHub Actions | accepted | implemented | 2026-05-03 | Accepted. Implemented in the same PR that lands this ADR. Companion |
| [138](ADR-138-flow-contract-schema.md) | Flow Contract Schema — Required Shape for Cloud Flow Manifests | accepted | implemented | 2026-05-03 | **Accepted and materialized for first lab registration.** The companion |
| [139](ADR-139-account-agnostic-multi-provider-runtime.md) | Account-Agnostic Multi-Provider Runtime | implemented | implemented | 2026-05-04 | **Accepted — Implemented** as the credential and billing posture for all COS runtime surfaces — local maintainer, cloud worker, and ephemeral sandbox. |
| [140](ADR-140-cross-os-containerized-deployment.md) | Cross-OS Containerized Deployment via Docker Compose | accepted | implemented | 2026-05-04 | **Accepted — Implemented** as the containerised deployment shape for COS cloud |
| [141](ADR-141-engram-cloud-cross-instance-replication.md) | Engram Cloud as Cross-Instance Replication Transport | implemented | implemented | 2026-05-04 | **Accepted — Implemented** as the replication strategy for Engram observations across COS instances. Local SQLite remains authoritative. Cloud is replication-on |
| [142](ADR-142-compliance-audit-air-gapped-surface.md) | Compliance, Audit, and Air-Gapped Surface (SOC 2 / ISO 27001 / GDPR) | implemented | implemented | 2026-05-04 | **Accepted — Implemented** as the compliance posture and audit-trail bridge for all COS cloud worker surfaces. |
| [143](ADR-143-closure-discipline-gate.md) | Closure Discipline Gate — Validation Nervous System Must Close With the Change | accepted | implemented | 2026-05-04 | **Accepted.** Closure discipline is now a first-class blocking maintainer gate. |
| [144](ADR-144-hook-enforced-rule-projection-contract.md) | Hook-Enforced Rule Projection Contract | accepted | implemented | 2026-05-04 | Accepted. Hook-enforced rule exclusions are now a projection contract, not a prose convention. |
| [148](ADR-148-adr-authoring-primitive.md) | ADR Authoring Primitive | accepted | implemented | 2026-05-04 | **Accepted** — 2026-05-04 |
| [149](ADR-149-primitive-duplication-audit.md) | Primitive Duplication Audit | accepted | implemented | 2026-05-04 | **Accepted** — 2026-05-04 |
| [150](ADR-150-acc-projection-profiles-and-harness-registry.md) | ACC Projection Profiles and Expanded Harness Registry | accepted | implemented | 2026-05-04 | **Accepted** — 2026-05-04 |
| [151](ADR-151-consumer-availability-classification.md) | Consumer Availability Classification Manifest | implemented | implemented | 2026-05-04 | **Implemented for manifest/classification scope** — 2026-05-04. The consumer availability manifest, ACC adapter, and contract tests named below exist; future sc |
| [152](ADR-152-shell-ci-projection-and-local-surface-defaults.md) | Shell CI Projection and Local Surface Defaults | implemented | implemented | 2026-05-04 | **Implemented for shell/CI projection and local-surface defaults** — 2026-05-04. The projection manifest, projector, ACC integration, and artifact-status extrac |
| [153](ADR-153-acc-fail-new-and-harness-proof-boundary.md) | ACC Fail-New Gate and Harness Proof Boundary | accepted | implemented | 2026-05-04 | **Accepted** — 2026-05-04 |
| [154](ADR-154-multi-ide-structural-harness-projection.md) | Multi-IDE Structural Harness Projection | implemented | implemented | 2026-05-04 | **Implemented for structural projection scope** — 2026-05-04. OpenCode, VS Code Copilot, and Cursor project-local projections are generated and tested; this doe |
| [155](ADR-155-shell-ci-formal-harness.md) | Shell CI Formal Harness Projection | accepted | implemented | 2026-05-04 | **Accepted** — 2026-05-04 |
| [156](ADR-156-qwen-code-structural-harness-projection.md) | Qwen Code Structural Harness Projection | implemented | implemented | 2026-05-04 | **Implemented for structural projection scope** — 2026-05-04. Qwen Code project-local settings/context projection is generated and tested; account-backed Qwen r |
| [157](ADR-157-kimi-code-cli-structural-harness-projection.md) | Kimi Code CLI Structural Harness Projection | implemented | implemented | 2026-05-04 | **Implemented for structural CLI projection scope** — 2026-05-04. Kimi Code project-local CLI context/config projection is generated and tested; authenticated C |
| [158](ADR-158-ai-agent-harness-landscape-and-proof-backlog.md) | AI Agent Harness Landscape and Proof Backlog | accepted | implemented | 2026-05-04 | **Accepted** — 2026-05-04 |
| [159](ADR-159-agents-md-native-structural-harness-batch.md) | AGENTS.md-native Structural Harness Batch and Kiro Lifecycle Investigation | accepted | implemented | 2026-05-05 | **Accepted** — 2026-05-05 |
| [160](ADR-160-rules-mcp-structural-harness-batch-and-kiro-adapter-design.md) | Rules/MCP Structural Harness Batch and Kiro Adapter Design | implemented | implemented | 2026-05-05 | **Implemented for structural projection and Kiro design scope** — 2026-05-05. The seven rules/MCP harness projections and Kiro adapter design artifacts exist an |
| [161](ADR-161-remote-control-plane-and-provider-adapter-boundary.md) | Remote Control Plane and Provider Adapter Boundary | implemented | implemented | 2026-05-05 | **Implemented for boundary/inventory scope** — 2026-05-05. The remote ingress versus provider/executor adapter boundary, alternatives manifest, report, manual t |
| [165](ADR-165-proof-drill-and-smoke-opt-in-primitives.md) | Proof Drill and Smoke Opt-In Agentic Primitives | implemented | implemented | 2026-05-05 | **Implemented for the proof-drill registry and smoke opt-in primitive scope** — 2026-05-05. The ADR closes the governed registry, agent procedure, manual proof  |
| [166](ADR-166-expected-skip-registry-and-opt-in-test-lanes.md) | Expected Skip Registry and Opt-In Test Lanes | implemented | implemented | 2026-05-05 | **Implemented for the first enforcement slice** — 2026-05-05. |
| [167](ADR-167-proof-drill-selector-and-acc-evidence-adapter.md) | Proof Drill Selector and ACC Evidence Adapter | implemented | implemented | 2026-05-05 | **Implemented for the proof-drill selector, evidence recorder, ACC adapter, instance-profile projection, and runtime-flag registry scope** — 2026-05-05. Live pr |
| [169](ADR-169-dashboard-formal-demotion.md) | Dashboard Formal Demotion | accepted | implemented | 2026-05-05 | Accepted. |
| [171](ADR-171-reject-paperclip-integration.md) | Reject Paperclip Integration — API was Aspirational, Multi-Surface Replaces It | accepted | implemented | 2026-05-05 | Accepted. Supersedes ADR-043. |
| [174](ADR-174-auto-derived-primitive-routing.md) | Auto-Derived Primitive Routing for Skills (and Rules) | accepted | implemented | 2026-05-05 | As of 2026-05-05, `lib/skill_router.py` contains a hand-maintained |
| [174b](ADR-174b-prevention-followup.md) | Routing-Pattern Prevention Followup — Auto-Generation and Soak-Driven Promotion | accepted | implemented | 2026-05-05 | Accepted. This ADR owns Part A (auto-generation includes `routing_patterns:`) and the implemented propose-only soak evaluator. The actual advisory-to-blocking p |
| [175](ADR-175-research-quality-enforcement.md) | Research-quality enforcement for audit reports | accepted | implemented | 2026-05-05 | **Accepted** — 2026-05-05 |
| [176](ADR-176-skillstore-and-analysis-trigger.md) | SkillStore SQLite Schema Adoption + Post-Execution Analysis Trigger (Discipline-Gated) | accepted | implemented | 2026-05-05 | Accepted. |
| [177](ADR-177-activate-skill-lifecycle-promotion-ladder.md) | Activate Skill Lifecycle Promotion Ladder | accepted | implemented | 2026-05-06 | Accepted. |
| [180](ADR-180-lifecycle-promotion-activation.md) | Lifecycle Promotion Activation — Concrete Proposers and Hook Wiring | accepted | implemented | 2026-05-05 | Accepted. |
| [181](ADR-181-adr-relevance-suggester.md) | ADR Relevance Suggester — Lightweight Routing for Architecture Decisions | accepted | implemented | 2026-05-05 | Accepted — 2026-05-05 |
| [182](ADR-182-branch-ownership-lock.md) | Branch Ownership Lock — Single-Writer Surface for Concurrent Orchestrators | accepted | implemented | 2026-05-05 | **Accepted.** Implemented as the ADR-182 branch-lock hook, library, CLI wrappers, and contract tests. Filed in response to the cross-session collision incident |
| [183](ADR-183-cross-session-event-log.md) | Cross-Session Event Log — Append-Only Visibility for Peer Orchestrators | accepted | implemented | 2026-05-05 | **Accepted.** Implemented as an extension of the existing `lib/session_bus.py` plus emit/context hooks. Companion to ADR-182. ADR-182 prevents *conflicts*; ADR- |
| [184](ADR-184-manager-of-managers-daemon.md) | Manager-of-Managers Daemon — Authoritative Single-Writer for Critical Surfaces | accepted | implemented | 2026-05-05 | **Accepted.** First implementation landed as a local file-queue daemon for ADR identity arbitration. Long-horizon refinement of ADR-163 (cos-instance-installer) |
| [185](ADR-185-cross-agent-audit-findings.md) | Cross-Agent Audit Findings Queue — Auditor → Implementer Directive Channel | accepted | implemented | 2026-05-05 | **Accepted.** Implemented as the directed message bus, inbox/context hooks, CLI, and tests. Fourth architectural layer companion to ADR-182 (branch |
| [186](ADR-186-context-budget-enforcement.md) | Context Budget Enforcement — Activate the ADR-038 Wave 3 Limits | accepted | implemented | 2026-05-05 | **Accepted.** Implemented as `lib/context_budget.py`, a shared hook accountant, a UserPromptSubmit meter, and hook-level budget checks. Filed in response to tod |
| [188](ADR-188-mandatory-skill-invocation-at-high-confidence.md) | Mandatory Skill Invocation at High Router Confidence | accepted | implemented | 2026-05-06 | **Accepted (2026-05-06).** Implementation landed on session branch |
| [239](ADR-239-isolated-worktree-default-for-write-agents.md) | Isolated Worktree Default for Write Agents | accepted | implemented | 2026-05-08 | Accepted. This ADR records the corrective decision after the 2026-05-08 |
| [269](ADR-269-mandatory-adr-reference-for-history-rewrites.md) | Mandatory ADR Reference for History Rewrites | accepted | implemented | 2026-05-11 | Accepted (2026-05-11). Implementation lands in companion commit set. |
| [270](ADR-270-legal-compliance-workflow-automation.md) | Legal Compliance Workflow Automation | accepted | implemented | 2026-05-11 | Accepted (2026-05-11). Implementation lands in companion commit. |

### Active / Partial (22)

| ADR | Title | Decision Status | Implementation | Date | Summary |
|---|---|---|---|---|---|
| [105](ADR-105-claim-verification-contract.md) | Bilateral Claim Verification Contract | implemented | partial | 2026-05-02 | **Author**: Maintainer |
| [116](ADR-116-multi-session-coordination-primitives.md) | Multi-Session Coordination Primitives | accepted | partial | 2026-05-02 | **Author**: Maintainer (operator) + Software Architect (analysis) |
| [121](ADR-121-foundation-hardening-program.md) | Foundation Hardening Program | accepted | partial | 2026-05-02 | Accepted — 2026-05-02 |
| [162](ADR-162-task-lifecycle-interruption-question-worktree-pr-protocol.md) | Task Lifecycle, Interruption, Question, Worktree, and PR Protocol | implemented | partial | 2026-05-05 | **Implemented for contract scope** — 2026-05-05. The task lifecycle schema, contract tests, and manual proof checklist exist; full queue/worker/PR runtime enfor |
| [163](ADR-163-cos-instance-installer.md) | Cognitive OS Instance Installer | accepted | partial | 2026-05-05 | **Accepted** — 2026-05-05 |
| [164](ADR-164-host-cli-bridge-security-boundary.md) | Host CLI Bridge Security Boundary | implemented | partial | 2026-05-05 | **Implemented for the design-only security contract scope** — 2026-05-05. |
| [168](ADR-168-cross-device-dependency-installation.md) | Cross-Device Dependency Installation Contract | implemented | partial | 2026-05-05 | **Implemented for the manifest-driven dry-run installer and credential-safe |
| [172](ADR-172-multi-surface-ui-architecture.md) | Multi-Surface UI Architecture - CLI + Phoenix + Engram Cloud + Obsidian | accepted | partial | 2026-05-05 | Accepted. Supersedes [ADR-170](ADR-170-operator-cli-as-primary-ui-surface.md). |
| [179](ADR-179-rules-auto-derive-routing.md) | Auto-Derived Rule Routing for Agent-Instruction Rules | accepted | partial | 2026-05-05 | **Accepted** — 2026-05-05 |
| [241](ADR-241-consolidated-cos-bypass-allowlist.md) | Consolidate Hook-Bypass Envs into a Single COS_BYPASS Allowlist | accepted | partial | 2026-05-08 | Accepted — Slice A implemented. Shared resolver, cheatsheet, target hook integration, and behavior tests are active; broad ecosystem bypass consolidation remain |
| [242](ADR-242-git-filter-repo-wrapper-preserves-remote.md) | git-filter-repo Wrapper Preserves Remote and Refuses Non-Idempotent Re-Runs | accepted | partial | 2026-05-08 | Accepted — Slice A implemented. `scripts/cos-filter-repo-wrap.sh` preserves remotes, refuses idempotent reruns, writes recovery artifacts, and `lib/history_sani |
| [243](ADR-243-post-rewrite-push-collision-exception.md) | Post-Rewrite Push-Collision Check Exception | accepted | partial | 2026-05-08 | Accepted — Slice A implemented. History sanitization writes `.cognitive-os/runtime/last-rewrite.json`; push-collision detection consumes it to allow matching po |
| [244](ADR-244-trust-report-claim-validator-must-enforce.md) | Trust Report Claim-Validator Must Enforce, Not Advise | accepted | partial | 2026-05-08 | Accepted — Slice A implemented. `scripts/claim_enforcer.py` enforces structured `verification:` evidence for high-stakes claims, `hooks/claim-validator.sh` bloc |
| [245](ADR-245-chaos-tests-readonly-production-source.md) | Chaos Tests Run with Read-Only Production Source | accepted | partial | 2026-05-08 | Accepted — Slice A implemented. `tests/chaos/conftest.py` installs `chaos_readonly_workspace`, restores source mutations under `lib/`, `scripts/`, and `hooks/`, |
| [246](ADR-246-release-transaction-freeze.md) | Release Transaction Freeze for Destructive and Public-State Operations | accepted | partial | 2026-05-08 | Accepted — Slice A implemented. `scripts/cos-release-freeze` now provides `--prepare`, `--begin`, `--status`, and `--end`; receipts are written under `.cognitiv |
| [247](ADR-247-manifest-driven-postmortem-regression-audits.md) | Manifest-Driven Postmortem Regression Audits and External Tool Adapters | accepted | partial | 2026-05-08 | Accepted. This ADR documents the policy correction made after ADR-242 through |
| [248](ADR-248-control-plane-audit-loop.md) | Control-Plane Audit Loop for ADR-239+ Primitive Drift | accepted | partial | 2026-05-08 | Accepted — Slice A implemented. |
| [249](ADR-249-primitive-behavioral-proof-anti-overfit-tests.md) | Primitive Behavioral Proof and Anti-Overfit Testing | accepted | partial | 2026-05-08 | Accepted — Slice A implemented. |
| [250](ADR-250-skill-router-retrieval-adapter-boundary.md) | Skill Router Retrieval Adapter Boundary | accepted | partial | 2026-05-08 | Accepted — Slice A implemented. |
| [251](ADR-251-agent-orchestration-adapter-boundary.md) | Agent Orchestration Adapter Boundary | accepted | partial | 2026-05-08 | Accepted — Slice A implemented. |
| [252](ADR-252-capability-coverage-matrix-and-feature-reality-ledger.md) | Capability Coverage Matrix and Feature Reality Ledger | accepted | partial | 2026-05-08 | Accepted — Slice A implemented. |
| [273](ADR-273-pending-truth-ledger-and-bilateral-verification.md) | Pending Truth Ledger and Bilateral Verification Loop | accepted | partial | 2026-05-12 | Accepted — Slice A implemented (schema + aggregator); Slices B (verifier) and C (hooks) tracked. |

### Active / Partial / Blocked (1)

| ADR | Title | Decision Status | Implementation | Date | Summary |
|---|---|---|---|---|---|
| [044](ADR-044-context-payload-slimming.md) | Context Payload Slimming — Non-Rule Startup Payloads | accepted | partial-blocked | 2026-04-20 | **Authors**: Agent C (startup-optimization initiative, stream 3/4) |

### Active / Deferred (1)

| ADR | Title | Decision Status | Implementation | Date | Summary |
|---|---|---|---|---|---|
| [173](ADR-173-surface-5-research-gate.md) | Surface 5 Research Gate — No Custom TUI/UI Adoption Without Source-Level Proof | accepted | deferred | 2026-05-06 | **Accepted** — 2026-05-06. |

### Active / Planned (1)

| ADR | Title | Decision Status | Implementation | Date | Summary |
|---|---|---|---|---|---|
| [137](ADR-137-operational-trajectory-governance-layer-to-embedded-runtime.md) | Operational Trajectory — From Governance Layer Over Agents to Embedded Runtime | accepted | planned | 2026-05-03 | **Accepted** for the trajectory itself. The directional commitment (B → A, defined below) is firm. |

### Active / Unclassified (171)

| ADR | Title | Decision Status | Implementation | Date | Summary |
|---|---|---|---|---|---|
| [006](ADR-006-agpl-license-compliance.md) | AGPL License Compliance -- Replace Redis and MinIO | accepted |  |  | **Date:** 2026-03-23 |
| [007](ADR-007-cognitive-os-rebrand.md) | Rebrand from Agent OS to Cognitive OS | accepted |  |  | **Date:** 2026-03-24 |
| [008](ADR-008-multi-tool-support.md) | Multi-Tool Support -- Not Claude Code-Only | accepted |  |  | **Date:** 2026-03-28 |
| [009](ADR-009-package-architecture.md) | Package Architecture -- 375 Agentic Primitives Reclassified | accepted |  |  | **Date:** 2026-03-28 |
| [010](ADR-010-hook-architecture-v2.md) | Hook Architecture v2 -- 10 Event Types, 3 Security Profiles | accepted |  |  | **Date:** 2026-03-28 to 2026-04-13 |
| [011](ADR-011-dual-gateway-bifrost-litellm.md) | Dual Gateway -- Bifrost Primary, LiteLLM Fallback | accepted |  |  | **Date:** 2026-03-28 |
| [012](ADR-012-prompt-driven-governance.md) | Prompt-Driven Governance -- Declarative Hook Logic | accepted |  |  | **Date:** 2026-03-29 |
| [013](ADR-013-security-stack.md) | Security Stack -- 8 Layers, 32 Tools | accepted |  |  | **Date:** 2026-03-29 |
| [014](ADR-014-sdd-fast-path.md) | SDD Fast Path -- Skip Phases for Capable Models | accepted |  |  | **Date:** 2026-03-31 |
| [015](ADR-015-rules-to-hooks-migration.md) | Rules-to-Hooks Migration -- From Context to Enforcement | accepted |  |  | **Date:** 2026-04-10 |
| [016](ADR-016-context-diet.md) | Context Diet -- Token Optimization Strategy | accepted |  |  | **Date:** 2026-03-31 |
| [017](ADR-017-stabilization-freeze.md) | Stabilization Freeze -- No New Features Until Wiring Complete | accepted |  |  | **Date:** 2026-04-11 |
| [018](ADR-018-docker-to-pip-migration.md) | Docker-to-pip Migration -- Service Infrastructure Change | accepted |  |  | **Date:** 2026-04-11 to 2026-04-13 |
| [019](ADR-019-scope-tagging.md) | Scope Tagging -- Agentic Primitive Audience Classification | accepted |  |  | **Date:** 2026-04-13 |
| [020](ADR-020-contamination-fix.md) | Contamination Fix -- Remove Project-Specific Code from OS | accepted |  |  | **Date:** 2026-04-13 |
| [021](ADR-021-vendor-agnostic-with-adapters.md) | Vendor-Agnostic State with Provider Adapters | accepted |  |  | **Date:** 2026-04-16 |
| [022](ADR-022-prompt-type-hooks-adoption.md) | Prompt-Type Hooks Adoption (Haiku-Evaluated Advisories) | accepted |  |  | **Date:** 2026-04-15 |
| [023](ADR-023-updated-input-pattern.md) | Mutate, Don't Block — `updatedInput` for PreToolUse Hooks | accepted |  |  | **Date:** 2026-04-15 |
| [024](ADR-024-task-panel-bridge.md) | Task Panel Bridge — Correlate COS Tasks with Claude Code tool_use_id | accepted |  |  | **Date:** 2026-04-16 |
| [025](ADR-025-install-update-loop.md) | Install/Update Loop — Closing the Advisory-Only Gap | accepted |  |  | **Date:** 2026-04-17 |
| [026](ADR-026-r2-r3-design-review.md) | R2 and R3 Consolidation — Design Review | accepted |  |  | **Date:** 2026-04-17 |
| [026a](ADR-026a-decisions.md) | R2 and R3 Design Review — Proposed Decisions (Addendum) | accepted |  |  | **Status:** CLOSED — R3 decisions (D3.1–D3.3) accepted and implemented 2026-04-17 |
| [027](ADR-027.md) | SO Slimming — Test Strategy, Context Overhead, Resource Consumption | accepted |  |  | ACCEPTED (2026-04-21) — WS1-WS3 shipped, included in v0.12.0 release. Implementation commits: 8dc4a6e, 9bd895b, 15d67eb. Resolved by ADR-027a. Originally propos |
| [028](ADR-028.md) | SO Reliability & Observability Framework | accepted |  |  | ACCEPTED (2026-04-21) — Full 6-pillar framework CLOSED. Addenda ADR-028a/b/c resolved all PENDING items (commit 423bd86). Originally proposed 2026-04-17. |
| [028c](ADR-028c.md) | Addendum: MetricEvent schema versioning + migration strategy | accepted |  |  | MetricEvent.schema_version is a monotonically-increasing integer starting at 1. |
| [029](ADR-029.md) | Anti-reinvention gate (reinvention-check.sh wired) | accepted |  |  | **Deciders**: Maintainer |
| [029b](ADR-029b-reinvention-phase-b-semantic.md) | Reinvention gate Phase B: semantic similarity | accepted |  |  | **Deciders**: Maintainer |
| [030](ADR-030.md) | Auto-trigger session-wrapup (Q1 prompt-match + Q2 commit banner) | accepted |  |  | Today the orchestrator has 7 session lifecycle skills (`/session-wrapup`, `/session-backlog`, `/session-report-executive`, `/resume-tasks`, `/session-manager`,  |
| [031](ADR-031.md) | Continuous Aspirational/Dormant/Real Audit | accepted |  |  | Manual forensic audits showed a persistent gap between the agentic primitives we build and the agentic primitives |
| [032](ADR-032-orchestrator-trap-preview.md) | Orchestrator-side trap awareness before Agent launch | accepted |  |  | The COS currently operates in FIRE_AND_FORGET mode (banner: "Valkey ✅, Executor ❌"). In this mode: |
| [033](ADR-033-harness-agnostic-event-capture.md) | Harness-agnostic event capture layer | accepted |  |  | The Cognitive OS observes agent activity through two JSONL streams: |
| [033b](ADR-033b-duration-correlation-and-aider-hardening.md) | Duration Correlation and Aider Version Dispatch Hardening | accepted |  |  | **Parent**: ADR-033 (`c9f52bf` — harness-agnostic event capture) |
| [035](ADR-035-worktree-cwd-enforcement.md) | Worktree CWD Enforcement: 3-Layer Defense | accepted |  |  | **Deciders**: Maintainer |
| [037](ADR-037-self-knowledge-base.md) | Self-Knowledge Base | accepted |  |  | Sub-agents spend 3-10K tokens per session grepping source files to answer basic questions: |
| [040](ADR-040-query-tailored-context-injection.md) | Query-Tailored Context Injection | accepted |  |  | **Deciders**: Matias Amendola |
| [041](ADR-041.md) | Exercised Coverage Pipeline (MVP) | accepted |  |  | **Deciders**: luum-agent-os team |
| [042](ADR-042-valkey-local-daemon.md) | Valkey Local Daemon — Extract from Docker (D34 Partial) | accepted |  |  | **Deciders**: Matias Améndola |
| [045](ADR-045-postgres-local-daemon.md) | PostgreSQL Local Daemon — Extract from Docker (D34) | accepted |  |  | **Deciders**: Matias Améndola |
| [048](ADR-048-docker-container-image-freshness.md) | Docker Container Image Freshness | accepted |  |  | **Accepted** — 2026-04-21. Follow-up to a live incident the same day. |
| [049](ADR-049-llm-gateway-selection-and-overflow-providers.md) | LLM Gateway Selection + Overflow Provider Strategy | accepted |  |  | **Accepted** — 2026-04-21. Supersedes implicit adoption of `litellm` (present |
| [050](ADR-050-per-skill-routing-policy.md) | Per-Skill Routing Policy | accepted |  |  | **Accepted** — 2026-04-21. Schema + dispatch integration shipped. Builds on |
| [051](ADR-051-qwen-agent-loop.md) | Qwen Agent Loop (Tool-Use Parity with Claude Code Agent) | accepted |  |  | - **Status**: Accepted (2026-04-21) — Phases 1, 2, 3, 4 all DELIVERED this session. Commits: MVP phase 1, 1e6542c (phase 2), 534814e (phase 3), 925dff5 (phase 4 |
| [054](ADR-054-project-docs-convention.md) | Project Documentation Convention (10 Categories) | accepted |  |  | **Accepted** — 2026-04-21. Implementation lives in `lib/project_scaffolder.py` |
| [055](ADR-055-docs-convention-enforcement.md) | Docs Convention Enforcement + Skill Writers | accepted |  |  | **Accepted** — 2026-04-21. Addendum to ADR-054. Implementation lives in |
| [055b](ADR-055b-destructive-git-block.md) | Destructive Git Op Block (User Context Elevation) | accepted |  |  | **Supersedes**: partial warn-only behavior of `hooks/destructive-git-blocker.sh` |
| [057](ADR-057-cross-harness-authoring-and-driver-projection.md) | Cross-Harness Authoring and Driver Projection | accepted |  |  | Date: 2026-04-23 |
| [058](ADR-058-observability-migration-langfuse-to-phoenix.md) | Observability Migration: Langfuse → Arize Phoenix | accepted |  |  | - **Status**: Accepted |
| [059](ADR-059-so-existential-validation.md) | SO Existential Validation: Prune, Install Timing, Core-vs-Extensions Split | accepted |  |  | **Proposed** — 2026-04-24. 3-phase plan with measurable exit criteria, |
| [060](ADR-060-local-only-optional-services.md) | Local-Only Policy for Optional Services | accepted |  |  | **Accepted** — 2026-04-24. Effective immediately. |
| [061](ADR-061-focus-narrative-and-external-evidence.md) | Focus Narrative and External Evidence | accepted |  |  | **Accepted** — 2026-04-24. Fills the 5 gaps identified during the existential |
| [062](ADR-062-multi-provider-agent-loop.md) | Multi-Provider Agent Loop | accepted |  |  | **Proposed** — 2026-04-24. Extends ADR-049 (provider cascade) and ADR-051 |
| [063](ADR-063-agent-tool-replication-strategy.md) | Agent() Tool Replication Strategy | accepted |  |  | **Accepted** — 2026-04-24. Clarifies the scope of ADR-051 / ADR-062 and |
| [064](ADR-064-harness-agnostic-cognitive-os.md) | Harness-Agnostic Cognitive OS | accepted |  |  | **Implementation-plan**: `.cognitive-os/plans/architecture/adr-064-implementation-plan.md` |
| [065](ADR-065-radar-update-curation-pipeline.md) | Tech Radar Curation Pipeline (`/radar-update`) | accepted |  |  | **Proposed** — 2026-04-24. Builds on `/repo-scout` (formerly `/eval-repo`, |
| [068](ADR-068-adaptive-test-runner-capacity.md) | Adaptive Test Runner Capacity Detection | accepted |  |  | **Accepted** — Phase 2 implemented 2026-04-30. Original proposal: 2026-04-24. |
| [069](ADR-069-research-first-protocol.md) | Research-First Protocol for High-Risk Changes | accepted |  |  | **Proposed** — 2026-04-24. Adopted alongside three concrete research tasks (H/I/J) |
| [070](ADR-070-convention-enforcement-mechanism.md) | Convention Enforcement — From Documentation to Mechanism | accepted |  |  | **Proposed** — 2026-04-27. Direct outcome of the |
| [071](ADR-071-engram-lifecycle-evolution.md) | Engram Lifecycle Evolution via Wrapper Layer | accepted |  |  | **Accepted** — 2026-04-27 |
| [072](ADR-072-test-lane-taxonomy.md) | Test Lane Taxonomy & Escalation Ladder | accepted |  |  | **Accepted** — 2026-04-29. |
| [073](ADR-073-test-architecture-role-registry.md) | Test Architecture Role Registry | accepted |  |  | **Accepted** — 2026-04-30. |
| [074](ADR-074-tier-0-learning-loop-closure.md) | Tier-0 Learning-Loop Closure | accepted |  |  | **Status:** Accepted |
| [075](ADR-075-stage2-selective-expansion.md) | Stage 2 Selective Expansion — Tier-Based Ref-Key Filtering | accepted |  |  | **Engram topic**: `cos/stage2-selective-expansion-plan` |
| [076](ADR-076-skill-frontmatter-alignment.md) | SKILL.md Frontmatter Alignment with Hermes Spec | accepted |  |  | **Engram topic**: `cos/tier2-hermes-alignment` |
| [077](ADR-077-peer-card-local-model.md) | Peer-Card Local User-Memory Model (Replaces Honcho) | accepted |  |  | **Engram topic**: `cos/tier2-hermes-alignment` |
| [078](ADR-078-mid-task-memory-tool.md) | Mid-Task Memory Tool (Port from Hermes) | accepted |  |  | **Deciders**: Maintainer |
| [079](ADR-079-corerules-applies-to-self-hosting.md) | CORE_RULES applies to self-hosting mode | accepted |  |  | **Author**: Maintainer |
| [080](ADR-080-hermes-cross-harness-adoption.md) | Hermes Cross-Harness Adoption (Umbrella) | accepted |  |  | **Author**: Maintainer |
| [081](ADR-081-codex-harness-adapter.md) | Codex Harness Adapter | accepted |  |  | **Author**: Maintainer |
| [082](ADR-082-plan-location-convention.md) | Plan Location Convention | accepted |  |  | **Author**: Maintainer |
| [083](ADR-083-governed-self-improvement-loop.md) | Governed Self-Improvement Loop | accepted |  |  | **Author**: Maintainer |
| [086](ADR-086-hook-execution-observability.md) | Hook Execution Observability | accepted |  |  | Accepted. The canonical number is ADR-086; ADR-085 was an abandoned contested reservation during the concurrent ADR slot race documented by ADR-089. |
| [087](ADR-087-adr-namespace-consolidation.md) | ADR Namespace Consolidation | accepted |  |  | **Author**: Maintainer |
| [088](ADR-088-provenance-trailer-ppid-chain.md) | Provenance trailer attribution via PPID chain | accepted |  |  | Accepted. |
| [089](ADR-089-multi-session-git-coordination.md) | Multi-Session Git Coordination | accepted |  |  | **Author**: Maintainer |
| [090](ADR-090-auto-skill-repair.md) | Auto-skill repair via failure-threshold signals | accepted |  |  | **Author**: Maintainer (COS sub-agent) |
| [091](ADR-091-headless-clustered-runtime-direction.md) | Headless and Clustered Runtime Direction | accepted |  |  | - **Status**: Accepted as direction, not yet implemented as a production cluster |
| [092](ADR-092-harness-skills-sync-path.md) | Harness Skills Sync Path — Add `.claude/skills/` as Second Sync Destination | accepted |  |  | As of 2026-04-16, the project has 126 skill directories under `skills/`. The Claude Code harness |
| [093](ADR-093-simplify-profiles.md) | Simplify Install Profiles — Collapse 3-Tier System to `default` + `--full` | accepted |  |  | Accepted (2026-04-16) |
| [094](ADR-094-agent-git-safety.md) | Agent Git Operations Safety — Layered Prevention of Destructive Git Ops | accepted |  |  | Accepted (2026-04-16) |
| [095](ADR-095-skill-synthesis-success-patterns.md) | Skill synthesis driven by success patterns | accepted |  |  | **Author**: Maintainer (COS sub-agent) |
| [096](ADR-096-review-agent-pattern.md) | Review-agent pattern (Hermes-style audit loop) | accepted |  |  | **Author**: Maintainer (COS sub-agent) |
| [097](ADR-097-documentation-execution-audit.md) | Documentation Execution Audit | accepted |  |  | - Status: Accepted |
| [098](ADR-098-multi-agent-file-coordination.md) | Multi-Agent File Coordination | accepted |  |  | **Author**: Maintainer |
| [099](ADR-099-pre-agent-snapshot-copy-on-untracked.md) | Pre-agent snapshot: copy-on-untracked instead of stash-sweep | accepted |  |  | **Supersedes**: (part of ADR-003 Mechanism A) |
| [100](ADR-100-resource-governed-test-execution.md) | Resource-Governed Test Execution | accepted |  |  | **Author**: Maintainer |
| [101](ADR-101-intent-aware-rate-limiter.md) | Intent-Aware Rate Limiter Flow Control | accepted |  |  | **Author**: Maintainer |
| [102](ADR-102-task-tracker-lifecycle.md) | Task tracker lifecycle: pending → in_progress → terminal, with PID capture and zombie reaper | accepted |  |  | Accepted. |
| [103](ADR-103-audit-contract-lane-recovery.md) | Audit and contract lane recovery before parallel flip | accepted |  |  | Accepted. |
| [104](ADR-104-startup-circuit-breaker.md) | Startup Circuit Breaker and Safe Mode | accepted |  |  | **Author**: Maintainer |
| [106](ADR-106-multi-session-safety-primitives.md) | Multi-Session Safety Primitives | accepted |  |  | **Author**: Maintainer |
| [107](ADR-107-human-approved-rollback.md) | Human-Approved Rollback Boundary | accepted |  |  | **Author**: Maintainer |
| [108](ADR-108-concurrent-agent-safety-layer.md) | Concurrent Agent Safety Layer | accepted |  |  | **Author**: Maintainer + Cognitive OS |
| [109](ADR-109-validation-capsule-worktree-isolation.md) | Validation Capsule Worktree Isolation | accepted |  |  | Accepted — 2026-05-02. |
| [110](ADR-110-preserve-branch-governance.md) | Preserve Branch Governance | accepted |  |  | **Author**: Maintainer + Cognitive OS |
| [111](ADR-111-core-consumer-concurrency-safety-boundary.md) | Core/Consumer Boundary for Concurrent-Agent Safety | accepted |  |  | Accepted — Implemented 2026-05-02. Related: ADR-108, ADR-110. |
| [112](ADR-112-codex-governed-tool-layer.md) | Codex Governed Tool Layer | accepted |  |  | Accepted — 2026-05-02. |
| [113](ADR-113-validation-capsule-liveness.md) | Validation Capsule Liveness Primitives | accepted |  |  | Accepted — 2026-05-02. |
| [114](ADR-114-hook-quality-system.md) | Hook Quality System | accepted |  |  | Accepted — 2026-05-02. |
| [115](ADR-115-safe-worktree-sweeper.md) | Safe Worktree Sweeper | accepted |  |  | Accepted — 2026-05-02. Scope: OS core. Related: ADR-109, ADR-111, ADR-113. |
| [118](ADR-118-multi-ide-swarm-testbed.md) | Multi-IDE Swarm Safety Testbed | accepted |  |  | Accepted (2026-05-02). This is the automated acceptance-test umbrella for ADR-116 and its transactional coordination rollout. |
| [120](ADR-120-conversation-to-primitive-harvester.md) | Conversation-to-Primitive Harvester | accepted |  |  | Accepted — 2026-05-02 |
| [122](ADR-122-preflight-gate-refinements.md) | Preflight Gate Refinements | accepted |  |  | **Author**: Maintainer (operator) |
| [127](ADR-127-active-primitive-index.md) | Active Primitive Index | accepted |  |  | Accepted for Phase 1 DX. |
| [133](ADR-133-expansion-without-monsterization.md) | Expansion Without Monsterization | accepted |  |  | Accepted — 2026-05-03 |
| [134](ADR-134-headless-self-improvement-proposer.md) | Headless Self-Improvement Proposer | accepted |  |  | **Implementation**: `scripts/cos-self-improvement-loop` |
| [135](ADR-135-self-evolving-doctrine-proposals.md) | Self-Evolving Doctrine Proposals | accepted |  |  | **Implementation**: `scripts/cos-doctrine-proposer` |
| [136](ADR-136-cross-instance-learning-runway.md) | Cross-Instance Learning Runway | accepted |  |  | **Implementation**: `scripts/cos_cross_instance_learning.py` |
| [145](ADR-145-dependency-lane-split.md) | Split heavy optional dependencies into explicit dependency lanes | accepted |  |  | Date: 2026-05-04 |
| [146](ADR-146-primitive-readiness-ledger.md) | Primitive Readiness Ledger | accepted |  |  | Accepted — 2026-05-04 |
| [147](ADR-147-agent-capability-coverage-pipeline.md) | Agent Capability Coverage Pipeline | accepted |  |  | Accepted — 2026-05-04 |
| [178](ADR-178-openharness-primitive-adoption.md) | OpenHarness Primitive Adoption (HttpHookDefinition, PromptHookDefinition, ProviderProfile) | accepted |  |  | **Deciders**: Maintainer |
| [189](ADR-189-harness-implementation-coverage.md) | Surface Implementation Coverage for Agentic Primitives | accepted |  |  | Accepted — 2026-05-06 |
| [190](ADR-190-harness-action-receipts.md) | Harness Action Receipts and VCS Event Telemetry | accepted |  |  | Accepted — 2026-05-06 |
| [191](ADR-191-cos-binary-release-pipeline.md) | COS Binary Release Pipeline | accepted |  |  | Accepted — 2026-05-06 |
| [192](ADR-192-surface-5-adopt-bubbletea.md) | Surface 5 Bubble Tea Adoption | accepted |  |  | Accepted — 2026-05-06 |
| [193](ADR-193-cosd-local-network-api.md) | cosd Local Network API | accepted |  |  | Accepted — 2026-05-06 |
| [194](ADR-194-cosd-secure-remote-api.md) | cosd Secure Remote API Guardrails | accepted |  |  | Accepted — 2026-05-06 |
| [195](ADR-195-surface-5-operable-tui-contract.md) | Surface 5 Operable TUI Contract | accepted |  |  | Accepted — 2026-05-06 |
| [196](ADR-196-cosd-task-api-and-provider-boundary.md) | cosd Task API and Provider Boundary | accepted |  |  | Accepted — 2026-05-06 |
| [197](ADR-197-surface-5-operable-actions.md) | Surface 5 Operable Actions | accepted |  |  | Accepted — 2026-05-06 |
| [198](ADR-198-release-external-readiness-gate.md) | Release External Readiness Gate | accepted |  |  | Accepted — 2026-05-06 |
| [199](ADR-199-state-retention-policy-and-reaper-protocol.md) | State Retention Policy and Reaper Protocol | accepted |  |  | Accepted — 2026-05-06 |
| [200](ADR-200-state-retention-controller.md) | State Retention Controller | accepted |  |  | Accepted — 2026-05-06 |
| [201](ADR-201-maintainer-agent-telemetry-promotion-loop.md) | Maintainer Agent and Telemetry Promotion Loop | accepted |  |  | **Report**: `docs/reports/self-improvement-maintainer-agent-gap-2026-05-06.md` |
| [202](ADR-202-private-content-cross-harness-portability-boundary.md) | Private Content Cross-Harness Portability Boundary | accepted |  |  | **Report**: `docs/reports/private-content-portability-gap-2026-05-06.md` |
| [203](ADR-203-subagent-capability-contract-and-launch-preflight.md) | Subagent Capability Contract and Launch Preflight | accepted |  |  | **Implementation**: `manifests/subagent-capabilities.yaml`, `scripts/subagent_launch_preflight.py`, `scripts/cos subagent preflight` |
| [204](ADR-204-signal-quality-and-reward-integrity-boundary.md) | Signal Quality and Reward Integrity Boundary | accepted |  |  | Accepted — implemented |
| [205](ADR-205-cross-stream-trace-joiner-and-flight-recorder.md) | Cross-Stream Trace Joiner and Flight Recorder | accepted |  |  | Accepted — implemented |
| [206](ADR-206-aspirational-claim-decommission-gate.md) | Aspirational Claim Decommission Gate | accepted |  |  | **Source**: `.cognitive-os/strategy/research/03-aspirational-dormant.md`, `.cognitive-os/strategy/00-first-approach.md`, `.cognitive-os/strategy/02-pre-launch-p |
| [208](ADR-208-imported-pattern-closure-contract.md) | Imported Pattern Closure Contract | accepted |  |  | **Source**: `.cognitive-os/strategy/research/05-hermes-imitation-forensics.md`, `.cognitive-os/strategy/research/06-external-patterns-benchmark.md` |
| [209](ADR-209-maintainer-reconciler-experiment-contract.md) | Maintainer Reconciler Experiment Contract | accepted |  |  | **Source**: `.cognitive-os/strategy/research/06-external-patterns-benchmark.md`, `.cognitive-os/strategy/research/08-self-improvement-roadmap.md` |
| [210](ADR-210-fleet-aggregated-confidence-boundary.md) | Fleet-Aggregated Confidence Boundary | accepted |  |  | Accepted — Slice A dry-run exporter implemented |
| [211](ADR-211-service-mode-readiness-gate.md) | Service-Mode Readiness Gate | accepted |  |  | Accepted — initial readiness gate implemented |
| [212](ADR-212-cross-stack-license-audit-toolchain.md) | Cross-Stack License Audit Toolchain | accepted |  |  | **Source**: Q2 tool-adoption review, `.cognitive-os/strategy/research/11-cross-stack-license-audit-tools.md` |
| [213](ADR-213-agent-preflight-before-stash-snapshot.md) | Agent Preflight Before Stash Snapshot | accepted |  |  | **Source**: `docs/reports/stash-hidden-wip-postmortem-2026-05-06.md` |
| [215](ADR-215-cross-stack-secret-audit-toolchain.md) | Cross-Stack Secret Audit Toolchain | accepted |  |  | **Source**: Q3 tool-adoption review (cross-stack secret/credential/PII detection), |
| [216](ADR-216-tool-discovery-pre-use-gate.md) | Tool Discovery Pre-Use Gate | accepted |  |  | **Source**: repeated dogfood evidence of ad-hoc external tool selection over existing COS primitives |
| [217](ADR-217-cross-stack-adoption-truth-audit.md) | Cross-Stack Adoption Truth Audit Toolchain | accepted |  |  | **Source**: Operator question — *"falta análisis de si está adoptado ya y de qué forma (esto también debería estar en las primitivas)"* |
| [218](ADR-218-history-sanitization-toolchain.md) | History Sanitization Toolchain | accepted |  |  | **Source**: Operator question — *"cómo depuramos lo que está en git sobre datos sensibles y estos cambios de licencias sin crear un repo nuevo?"* |
| [219](ADR-219-work-ownership-liveness-preflight.md) | Work Ownership Liveness Preflight | accepted |  |  | During the license-switch work, WIP was preserved to a temporary branch |
| [220](ADR-220-worktree-divergence-audit.md) | Worktree Divergence Audit Toolchain | accepted |  |  | **Source**: Operator session 2026-05-06 — sed-fix on `.cognitive-os/preserve-manifests/*` appeared "lost" because commits landed on `main` while the operator wa |
| [221](ADR-221-stash-ref-by-sha-not-by-position.md) | Stash References by SHA, Not by Position | accepted |  |  | **Supersedes (in part)**: the marker-file format produced by `pre-agent-snapshot.sh` and consumed by `post-agent-snapshot-restore.sh`. |
| [222](ADR-222-pre-agent-stash-defer-until-launch-confirmed.md) | Pre-Agent Stash Deferred Until Agent Launch Confirmed | accepted |  |  | **Supersedes (in part)**: the PreToolUse-Agent ordering currently relied on by `pre-agent-snapshot.sh`. |
| [223](ADR-223-agent-lifecycle-reconstruction.md) | Agent Lifecycle Reconstruction: Worktree-Per-Write-Agent | accepted |  |  | **Source**: `docs/research/multi-agent-orchestration-prior-art-2026-05-06.md`, `docs/research/orchestration-gaps/background-agent-patterns.md`, and the operator |
| [225](ADR-225-branch-per-task-mode.md) | Branch-Per-Task Mode | accepted |  |  | Worktree-per-write-agent isolates filesystem mutations, but branch identity still needs a stable operator-visible contract. Without a branch-per-task policy, de |
| [226](ADR-226-event-sourced-session-bus.md) | Event-Sourced Session Bus | accepted |  |  | **Extends**: **ADR-205 (Cross-Stream Trace Joiner and Flight Recorder)** — ADR-226 is an *extension* of the Flight Recorder's append-only event substrate, not a |
| [227](ADR-227-shadow-git-checkpoint-substrate.md) | Shadow-Git Checkpoint Substrate | accepted |  |  | **Source**: [`docs/research/orchestration-gaps/replay-timeline-architectures.md`](../research/orchestration-gaps/replay-timeline-architectures.md). Cline, Herme |
| [228](ADR-228-retry-contract-and-cost-budget.md) | Retry Contract + Cost Session Budget (consolidated) | accepted |  |  | Accepted — Slices A–F implemented (2026-05-07) |
| [230](ADR-230-handoff-envelope-and-cycle-deduplication.md) | Agent Handoff Envelope + Call-Chain Deduplication | accepted |  |  | **Source**: [`docs/research/orchestration-gaps/agent-to-agent-handoff.md`](../research/orchestration-gaps/agent-to-agent-handoff.md). Production failure rate of |
| [231](ADR-231-mcp-server-surface-for-cos-primitives.md) | MCP Server Surface for COS Primitives | accepted |  |  | **Source**: [`docs/research/orchestration-gaps/mcp-as-orchestration-bus.md`](../research/orchestration-gaps/mcp-as-orchestration-bus.md) |
| [232](ADR-232-sandbox-adapter-tiers.md) | Sandbox Adapter Tiers | accepted |  |  | COS needs filesystem/process permission boundaries that are enforced below the prompt layer. Prior-art research recommends OS-native sandbox tiers first: Bubble |
| [233](ADR-233-cross-session-agent-team-file-ipc.md) | Cross-Session Agent-Team File IPC | accepted |  |  | **Source**: [`docs/research/orchestration-gaps/cross-session-agent-teams.md`](../research/orchestration-gaps/cross-session-agent-teams.md) |
| [234](ADR-234-approval-policies-as-code.md) | Approval Policies as Code | accepted |  |  | COS has many shell hooks with embedded allow/deny logic. Research recommended a COS-native YAML policy evaluator before adopting heavy engines such as OPA, Ceda |
| [235](ADR-235-detached-agent-daemon.md) | Detached Agent Daemon | accepted |  |  | **Source**: [`docs/research/orchestration-gaps/background-agent-patterns.md`](../research/orchestration-gaps/background-agent-patterns.md) |
| [236](ADR-236-deferred-tool-loading-and-toolsearch.md) | Deferred Tool Loading + ToolSearch Adoption | accepted |  |  | The orchestration research recommended adopting the ToolSearch/deferred-loading pattern instead of loading every tool schema into every session. This is not a s |
| [237](ADR-237-test-execution-efficiency-protocol.md) | Test Execution Efficiency Protocol | accepted |  |  | Cognitive OS test lanes are intentionally broad: unit, behavior, integration, chaos, benchmark, audit, smoke, cross-harness, and release gates. Running `make te |
| [240](ADR-240-primitive-coherence-audit-and-ownership-manifest.md) | Primitive Coherence Audit and Ownership Manifest | accepted |  |  | status: accepted |
| [254](ADR-254-external-tool-intelligence-plane-and-project-overlays.md) | External Tool Intelligence Plane and Project Overlays | accepted |  |  | status: accepted |
| [255](ADR-255-feature-to-external-tool-due-diligence.md) | Feature-to-External-Tool Due Diligence | accepted |  |  | Accepted — Slice A implemented |
| [256](ADR-256-primitive-contract-registry-and-runtime-evidence-ledger.md) | Primitive Contract Registry and Runtime Evidence Ledger | accepted |  |  | Accepted — implemented through Phases 1–6; all primitive-lifecycle rows are registry-backed; OpenCode signed smoke covers the first 20 runtime primitives |
| [257](ADR-257-primitive-contract-registry-phase-1.md) | Primitive Contract Registry Phase 1 | accepted |  |  | Accepted — implemented |
| [258](ADR-258-portable-ai-overlay-for-agentic-primitives.md) | Portable `.ai` Overlay for Agentic Primitives | accepted |  |  | Accepted — generated overlay implemented; canonical migration intentionally deferred |
| [259](ADR-259-external-pattern-adoption-posture.md) | holaOS Adoption Posture: Patterns-Only Library with Clean-Room Rewrite | accepted |  |  | **Date:** 2026-05-11 |
| [260](ADR-260-grant-signed-cosd-api.md) | Grant-Signed cosd API: HMAC + Nonce + TTL + Scope Binding | accepted |  |  | **Date:** 2026-05-11 |
| [261](ADR-261-memory-governance-v2.md) | Memory Governance v2: Typed Memory with Verification & Staleness Policies | accepted |  |  | **Date:** 2026-05-11 |
| [262](ADR-262-evolve-loop-spike.md) | Evolve Loop Spike: Task Proposal Queue + LLM-driven Skill Candidates | accepted |  |  | **Spike** (not Accepted — pending exit criteria evaluation) |
| [263](ADR-263-tool-replay-budget-ledger.md) | Tool-Replay Budget Ledger: Per-Session Cap + Preview/Reference-Only Modes | accepted |  |  | **Date:** 2026-05-11 |
| [264](ADR-264-tool-result-envelope.md) | Tool Result Envelope: Compact Envelope Format for Large Tool Outputs | accepted |  |  | **Date:** 2026-05-11 |
| [267](ADR-267-license-compliance-enforcement-architecture.md) | License-Compliance Enforcement Architecture | accepted |  |  | Accepted (2026-05-11) |
| [268](ADR-268-history-sanitization-2026-05-11.md) | Defensive history sanitization for external-pattern attribution | accepted |  |  | Accepted (2026-05-11) |
| [272](ADR-272-structural-rule-backend-boundary.md) | Structural Rule Backend Boundary | accepted |  |  | Status: Accepted |

## Proposed

| ADR | Title | Decision Status | Implementation | Date | Summary |
|---|---|---|---|---|---|
| [001](ADR-001-abc-parallel-dedup-fix-broken-infra-add-global-verify.md) | A+B+C parallel — dedup, fix broken infra, add global-verify | proposed |  |  | Draft |
| [002](ADR-002-docker-pip-localhost-envs-targetedtestresolver-redis-dep.md) | docker-pip localhost envs + targeted_test_resolver + redis dep | proposed |  |  | Draft |
| [034](ADR-034-harness-agnostic-live-streaming.md) | Harness-Agnostic Live Agent Streaming | proposed |  |  | - **Status**: Proposed |
| [036](ADR-036-sprint-orchestration-primitives.md) | Sprint orchestration primitives | proposed |  |  | Proposed — MVP implemented 2026-04-20 (CLI skeleton + manifest + canonical events + example spec). Wave 1 test aggregation shipped 2026-04-21. Dispatch wiring v |
| [038](ADR-038-preamble-v2-industry-aligned.md) | Preamble v2: Industry-Aligned Contract | proposed |  |  | > Originally drafted in `.cognitive-os/pending-tasks/adr-038-preamble-v2-industry-aligned.md`; canonical location is `docs/adrs/`. |
| [039](ADR-039-reinvention-phase-b-beta.md) | Reinvention Phase B-β (semantic embeddings) | proposed |  |  | > Originally drafted in `.cognitive-os/pending-tasks/adr-039-reinvention-phase-b-beta.md`; canonical location is `docs/adrs/`. |
| [047](ADR-047-session-lifecycle-management.md) | Session Lifecycle Management | proposed |  |  | Proposed — 2026-04-20. Author: Agent E (software-architect). Coordinates with |
| [066](ADR-066-polyglot-language-boundaries.md) | Polyglot Language Boundaries & Migration Pressure | proposed |  |  | Proposed — 2026-04-24. |
| [067](ADR-067-frontmatter-defense-in-depth.md) | Defense-in-Depth for SKILL.md Frontmatter Quality | proposed |  |  | Proposed — 2026-04-24. Implementation tracked separately as Phase 1 of this ADR. |
| [117](ADR-117-stash-mutation-reversibility.md) | Stash Mutation Must Be Reversible-by-Design | proposed |  |  | **Status:** Proposed |
| [124](ADR-124-cos-distribution-boundaries.md) | COS Distribution Boundaries — Core, Team, Maintainer, Lab | proposed |  |  | Proposed — 2026-05-02 |
| [125](ADR-125-governance-tools-value-boundary.md) | Governance Tools Value Boundary | proposed |  |  | Proposed — 2026-05-02 |
| [126](ADR-126-agentic-primitive-lifecycle-governor.md) | Agentic Primitive Lifecycle Governor | proposed |  |  | Proposed — 2026-05-02 |
| [128](ADR-128-data-layer-integrity-fixes.md) | Data Layer Integrity Fixes | proposed |  |  | Proposed — 2026-05-03 |
| [174c](ADR-174c-validator-blocking-promotion.md) | Validator Advisory-to-Blocking Promotion After Soak | proposed | deferred | 2026-05-12 | Proposed. This ADR is intentionally not accepted until soak data proves the |
| [265](ADR-265-mandatory-minimum-inspection-caps.md) | Mandatory-minimum inspection caps for COS eval surfaces | proposed |  |  | Proposed (2026-05-11) |
| [266](ADR-266-protected-config-write-guard-bash-coverage.md) | Extend protected-config-write-guard to intercept Bash file-write commands | proposed |  |  | `hooks/protected-config-write-guard.sh` blocks writes to agent control-plane paths (hooks, rules, skills, manifests, etc.) by intercepting `PreToolUse` events.  |
| [271](ADR-271-clean-room-detection-tier-2-ast-similarity.md) | Clean-Room Detection Tier 2: AST-Normalized Similarity | proposed |  |  | Proposed (2026-05-11) |

## Exploration

| ADR | Title | Decision Status | Implementation | Date | Summary |
|---|---|---|---|---|---|
| [132](ADR-132-solo-swarm-vs-multi-maintainer-fork.md) | Solo-Swarm vs Multi-Maintainer Fork — Documenting the Pending Strategic Decision | exploration | not-applicable | 2026-05-03 | **Exploration.** This ADR does not commit to an architectural change. |

## Resolved

| ADR | Title | Decision Status | Implementation | Date | Summary |
|---|---|---|---|---|---|
| [238](ADR-238-tier-1-4-followup-bug-tracking.md) | Tier 1-4 Follow-Up Bug Tracking | resolved | resolved | 2026-05-07 | During the Tier 1-4 case-study leak audit (privacy decoupling, commits |

<details>
<summary>Superseded ADRs (3)</summary>

## Superseded

| ADR | Title | Decision Status | Implementation | Date | Summary |
|---|---|---|---|---|---|
| [084](ADR-084-headless-clustered-runtime-shape.md) | Headless and Clustered Runtime Shape | superseded |  |  | **Author**: Maintainer |
| [170](ADR-170-operator-cli-as-primary-ui-surface.md) | Operator-CLI as Primary UI Surface — No Web Dashboard Until a Real Driver Exists | superseded | not-applicable | 2026-05-05 | Superseded by [ADR-172](ADR-172-multi-surface-ui-architecture.md) (2026-05-05). |
| [187](ADR-187-surface-5-adoption-proof-contract.md) | Surface 5 Adoption Proof Contract — Source-Level Gate for Custom TUI/UI | superseded | not-applicable | 2026-05-06 | **Superseded by ADR-192** — the proof contract was satisfied by the accepted Bubble Tea adoption decision. Future Surface 5 adoption work extends ADR-192 rather |

</details>

<details>
<summary>Tombstone ADRs (11)</summary>

## Tombstone

| ADR | Title | Decision Status | Implementation | Date | Summary |
|---|---|---|---|---|---|
| [003](ADR-003-tombstone.md) | Reserved architecture decision slot | tombstone | not-applicable | 2026-05-05 | **Tombstone** — 2026-05-05 |
| [004](ADR-004-tombstone.md) | Reserved architecture decision slot | tombstone | not-applicable | 2026-05-05 | **Tombstone** — 2026-05-05 |
| [005](ADR-005-tombstone.md) | Reserved architecture decision slot | tombstone | not-applicable | 2026-05-05 | **Tombstone** — 2026-05-05 |
| [043](ADR-043-tombstone.md) | Removed local-daemon integration decision | tombstone | not-applicable | 2026-05-05 | **Tombstone** — 2026-05-05 |
| [046](ADR-046-tombstone.md) | Reserved architecture decision slot | tombstone | not-applicable | 2026-05-05 | **Tombstone** — 2026-05-05 |
| [085](ADR-085-tombstone.md) | Reserved architecture decision slot | tombstone | not-applicable | 2026-05-05 | **Tombstone** — 2026-05-05 |
| [207](ADR-207-skill-ecosystem-performance-and-lifecycle-closure.md) | Skill Ecosystem Performance and Lifecycle Closure | tombstone |  |  | **Source**: `.cognitive-os/strategy/research/07-skill-ecosystem-evolution.md`, `.cognitive-os/strategy/research/05-hermes-imitation-forensics.md` |
| [214](ADR-214-tombstone.md) | Reserved — vacated by parallel-session number collision | tombstone | not-applicable | 2026-05-06 | **Tombstone** — 2026-05-06 |
| [224](ADR-224-shadow-state-snapshots-off-repo.md) | Tombstone (consolidated into ADR-227) | tombstone |  |  | status: tombstone |
| [229](ADR-229-tombstone.md) | Tombstone (consolidated into ADR-228) | tombstone |  |  | status: tombstone |
| [253](ADR-253-tombstone-squads.md) | Tombstone — squads orchestration superseded by ADR-251 | tombstone | not-applicable | 2026-05-08 | The `packages/squads/` orchestration package (multi-agent team coordination |

</details>

## Other

| ADR | Title | Decision Status | Implementation | Date | Summary |
|---|---|---|---|---|---|
| [027a](ADR-027a.md) | Addendum: Reconciliation with main baseline | other |  |  | **Supersedes**: ADR-027 §Baseline (context overhead table), §KPIs row "CLAUDE.md tokens loaded on session start" |
| [028a](ADR-028a.md) | Addendum: Reconciliation with pre-existing plans | other |  |  | **Amends**: ADR-028 D1.A, D1.C, D4 |
| [028b](ADR-028b.md) | Addendum: D1.C Replanned Around agent_bus | other |  |  | **Supersedes**: ADR-028 D1.C (original spec, lines 166–214) |
| [056](ADR-056-adaptive-agent-dispatch.md) | Adaptive Agent() dispatch: 3-tier auto-switch Claude → Qwen | other |  |  | - **Status**: L1 IMPLEMENTED (advisory-only). L2/L3 DEFERRED. |
