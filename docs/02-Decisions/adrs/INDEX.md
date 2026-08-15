# ADR Index

## How to Use This Index

This generated table is the status inventory for all 503 Architecture Decision Record files (ADRs).
Status semantics are defined in [STATUS-TAXONOMY.md](STATUS-TAXONOMY.md): decision status, implementation status, and index bucket are separate fields.
Rows link to the canonical ADR file and group by index bucket for human and agent navigation.

## Active

### Active / Implemented (175)

| ADR | Title | Decision Status | Implementation | Date | Summary |
|---|---|---|---|---|---|
| [008](ADR-008-multi-tool-support.md) | Multi-Tool Support -- Not Claude Code-Only | accepted | implemented | 2026-03-28 | **Date:** 2026-03-28 |
| [009](ADR-009-package-architecture.md) | Package Architecture -- Agentic Primitive Reclassification | accepted | implemented | 2026-03-28 | **Date:** 2026-03-28 |
| [010](ADR-010-hook-architecture-v2.md) | Hook Architecture v2 -- 10 Event Types, 3 Security Profiles | accepted | implemented | 2026-03-28 | **Date:** 2026-03-28 to 2026-04-13 |
| [012](ADR-012-prompt-driven-governance.md) | Prompt-Driven Governance -- Declarative Hook Logic | accepted | implemented | 2026-03-29 | **Date:** 2026-03-29 |
| [013](ADR-013-security-stack.md) | Security Stack -- 8 Layers, 32 Tools | accepted | implemented | 2026-03-29 | **Date:** 2026-03-29 |
| [015](ADR-015-rules-to-hooks-migration.md) | Rules-to-Hooks Migration -- From Context to Enforcement | accepted | implemented | 2026-04-10 | **Date:** 2026-04-10 |
| [027](ADR-027.md) | SO Slimming — Test Strategy, Context Overhead, Resource Consumption | accepted | implemented | 2026-04-21 | ACCEPTED (2026-04-21) — WS1-WS3 shipped, included in v0.12.0 release. Implementation commits: 8dc4a6e, 9bd895b, 15d67eb. Resolved by ADR-027a. Originally propos |
| [027a](ADR-027a.md) | Addendum: Reconciliation with main baseline | accepted | implemented | 2026-04-18 | **Supersedes**: ADR-027 §Baseline (context overhead table), §KPIs row "CLAUDE.md tokens loaded on session start" |
| [028](ADR-028.md) | SO Reliability & Observability Framework | accepted | implemented | 2026-04-21 | ACCEPTED (2026-04-21) — Full 6-pillar framework CLOSED. Addenda ADR-028a/b/c resolved all PENDING items (commit 423bd86). Originally proposed 2026-04-17. |
| [028a](ADR-028a.md) | Addendum: Reconciliation with pre-existing plans | accepted | implemented | 2026-04-18 | **Amends**: ADR-028 D1.A, D1.C, D4 |
| [028b](ADR-028b.md) | Addendum: D1.C Replanned Around agent_bus | accepted | implemented | 2026-04-20 | **Supersedes**: ADR-028 D1.C (original spec, lines 166–214) |
| [037](ADR-037-self-knowledge-base.md) | Self-Knowledge Base | accepted | implemented | 2026-04-20 | Sub-agents spend 3-10K tokens per session grepping source files to answer basic questions: |
| [038](ADR-038-preamble-v2-industry-aligned.md) | Preamble v2: Industry-Aligned Contract | accepted | implemented | 2026-04-20 | > Originally drafted in `.cognitive-os/pending-tasks/adr-038-preamble-v2-industry-aligned.md`; canonical location is `docs/02-Decisions/adrs/`. |
| [040](ADR-040-query-tailored-context-injection.md) | Query-Tailored Context Injection | accepted | implemented | 2026-04-30 | **Deciders**: Matias Amendola |
| [049](ADR-049-llm-gateway-selection-and-overflow-providers.md) | LLM Gateway Selection + Overflow Provider Strategy | accepted | implemented | 2026-04-21 | **Accepted** — 2026-04-21. Supersedes implicit adoption of `litellm` (present |
| [051](ADR-051-qwen-agent-loop.md) | Qwen Agent Loop (Tool-Use Parity with Claude Code Agent) | accepted | implemented | 2026-04-21 | - **Status**: Accepted (2026-04-21) — Phases 1, 2, 3, 4 all DELIVERED this session. Commits: MVP phase 1, 1e6542c (phase 2), 534814e (phase 3), 925dff5 (phase 4 |
| [052](ADR-052-provider-benchmark-harness.md) | Provider Benchmark Harness | implemented | implemented |  | **Implemented for the no-cost offline harness scope.** The repository now ships a |
| [053](ADR-053-dispatch-auto-optimizer.md) | Dispatch Auto-Optimizer | implemented | implemented |  | **Implemented for reviewed proposal generation.** The repository now ships a |
| [080](ADR-080-hermes-cross-harness-adoption.md) | Hermes Cross-Harness Adoption (Umbrella) | accepted | implemented | 2026-04-30 | **Author**: Maintainer |
| [088](ADR-088-provenance-trailer-ppid-chain.md) | Provenance trailer attribution via PPID chain | accepted | implemented | 2026-04-30 | Accepted. |
| [092](ADR-092-harness-skills-sync-path.md) | Harness Skills Sync Path — Add `.claude/skills/` as Second Sync Destination | accepted | implemented | 2026-04-30 | As of 2026-04-16, the project has 126 skill directories under `skills/`. The Claude Code harness |
| [099](ADR-099-pre-agent-snapshot-copy-on-untracked.md) | Pre-agent snapshot: copy-on-untracked instead of stash-sweep | accepted | implemented | 2026-04-30 | **Supersedes**: (part of ADR-003 Mechanism A) |
| [100](ADR-100-resource-governed-test-execution.md) | Resource-Governed Test Execution | accepted | implemented | 2026-04-30 | **Author**: Maintainer |
| [104](ADR-104-startup-circuit-breaker.md) | Startup Circuit Breaker and Safe Mode | accepted | implemented | 2026-05-01 | **Author**: Maintainer |
| [106](ADR-106-multi-session-safety-primitives.md) | Multi-Session Safety Primitives | accepted | implemented | 2026-05-02 | **Author**: Maintainer |
| [108](ADR-108-concurrent-agent-safety-layer.md) | Concurrent Agent Safety Layer | accepted | implemented | 2026-05-02 | **Author**: Maintainer + Cognitive OS |
| [109](ADR-109-validation-capsule-worktree-isolation.md) | Validation Capsule Worktree Isolation | accepted | implemented | 2026-05-02 | Accepted — 2026-05-02. |
| [112](ADR-112-codex-governed-tool-layer.md) | Codex Governed Tool Layer | accepted | implemented | 2026-05-02 | Accepted — 2026-05-02. |
| [113](ADR-113-validation-capsule-liveness.md) | Validation Capsule Liveness Primitives | accepted | implemented | 2026-05-02 | Accepted — 2026-05-02. |
| [114](ADR-114-hook-quality-system.md) | Hook Quality System | accepted | implemented | 2026-05-02 | Accepted — 2026-05-02. |
| [115](ADR-115-safe-worktree-sweeper.md) | Safe Worktree Sweeper | accepted | implemented | 2026-05-02 | Accepted — 2026-05-02. Scope: OS core. Related: ADR-109, ADR-111, ADR-113. |
| [119](ADR-119-session-filesystem-reaper.md) | Session Filesystem Reaper | implemented | implemented | 2026-05-02 | Accepted — 2026-05-02. Related: ADR-102, ADR-106, ADR-111, ADR-116, ADR-117. |
| [123](ADR-123-operational-stability-friction-reduction.md) | Operational Stability and Friction Reduction Program | implemented | implemented | 2026-05-02 | Implemented — 2026-05-08 status sync |
| [129](ADR-129-safe-worktree-removal.md) | Safe Worktree Removal — No Silent rm -rf Fallback | accepted | implemented | 2026-05-02 | Accepted. Implemented in commit `d5ecda43` with the shared |
| [130](ADR-130-suspend-claude-api-workflows.md) | Suspend All GitHub Actions Workflows — Preserve as .disabled Until Local-CI Migration | accepted | implemented | 2026-05-03 | Accepted. |
| [131](ADR-131-local-ci-migration.md) | Local-CI Migration — Three-Layer Architecture to Replace GitHub Actions | accepted | implemented | 2026-05-03 | Accepted. Implemented in the same PR that lands this ADR. Companion |
| [134](ADR-134-headless-self-improvement-proposer.md) | Headless Self-Improvement Proposer | accepted | implemented | 2026-05-03 | **Implementation**: `scripts/cos-self-improvement-loop` |
| [138](ADR-138-flow-contract-schema.md) | Flow Contract Schema — Required Shape for Cloud Flow Manifests | accepted | implemented | 2026-05-03 | **Accepted and materialized for first lab registration.** The companion |
| [139](ADR-139-account-agnostic-multi-provider-runtime.md) | Account-Agnostic Multi-Provider Runtime | implemented | implemented | 2026-05-04 | **Accepted — Implemented** as the credential and billing posture for all COS runtime surfaces — local maintainer, cloud worker, and ephemeral sandbox. |
| [140](ADR-140-cross-os-containerized-deployment.md) | Cross-OS Containerized Deployment via Docker Compose | accepted | implemented | 2026-05-04 | **Accepted — Implemented** as the containerised deployment shape for COS cloud |
| [141](ADR-141-engram-cloud-cross-instance-replication.md) | Engram Cloud as Cross-Instance Replication Transport | implemented | implemented | 2026-05-04 | **Accepted — Implemented** as the replication strategy for Engram observations across COS instances. Local SQLite remains authoritative. Cloud is replication-on |
| [142](ADR-142-compliance-audit-air-gapped-surface.md) | Compliance, Audit, and Air-Gapped Surface (SOC 2 / ISO 27001 / GDPR) | implemented | implemented | 2026-05-04 | **Accepted — Implemented** as the compliance posture and audit-trail bridge for all COS cloud worker surfaces. |
| [143](ADR-143-closure-discipline-gate.md) | Closure Discipline Gate — Validation Nervous System Must Close With the Change | accepted | implemented | 2026-05-04 | **Accepted.** Closure discipline is now a first-class blocking maintainer gate. |
| [144](ADR-144-hook-enforced-rule-projection-contract.md) | Hook-Enforced Rule Projection Contract | accepted | implemented | 2026-05-04 | Accepted. Hook-enforced rule exclusions are now a projection contract, not a prose convention. |
| [145](ADR-145-dependency-lane-split.md) | Split heavy optional dependencies into explicit dependency lanes | accepted | implemented | 2026-05-04 | Date: 2026-05-04 |
| [146](ADR-146-primitive-readiness-ledger.md) | Primitive Readiness Ledger | accepted | implemented | 2026-05-04 | Accepted — 2026-05-04 |
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
| [164](ADR-164-host-cli-bridge-security-boundary.md) | Host CLI Bridge Security Boundary | implemented | implemented | 2026-05-05 | **Implemented for the design-only security contract scope** — 2026-05-05. |
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
| [179](ADR-179-rules-auto-derive-routing.md) | Auto-Derived Rule Routing for Agent-Instruction Rules | accepted | implemented | 2026-05-05 | **Accepted** — 2026-05-05 |
| [180](ADR-180-lifecycle-promotion-activation.md) | Lifecycle Promotion Activation — Concrete Proposers and Hook Wiring | accepted | implemented | 2026-05-05 | Accepted. |
| [181](ADR-181-adr-relevance-suggester.md) | ADR Relevance Suggester — Lightweight Routing for Architecture Decisions | accepted | implemented | 2026-05-05 | Accepted — 2026-05-05 |
| [182](ADR-182-branch-ownership-lock.md) | Branch Ownership Lock — Single-Writer Surface for Concurrent Orchestrators | accepted | implemented | 2026-05-05 | **Accepted.** Implemented as the ADR-182 branch-lock hook, library, CLI wrappers, and contract tests. Filed in response to the cross-session collision incident |
| [183](ADR-183-cross-session-event-log.md) | Cross-Session Event Log — Append-Only Visibility for Peer Orchestrators | accepted | implemented | 2026-05-05 | **Accepted.** Implemented as an extension of the existing `lib/session_bus.py` plus emit/context hooks. Companion to ADR-182. ADR-182 prevents *conflicts*; ADR- |
| [184](ADR-184-manager-of-managers-daemon.md) | Manager-of-Managers Daemon — Authoritative Single-Writer for Critical Surfaces | accepted | implemented | 2026-05-05 | **Accepted.** First implementation landed as a local file-queue daemon for ADR identity arbitration. Long-horizon refinement of ADR-163 (cos-instance-installer) |
| [185](ADR-185-cross-agent-audit-findings.md) | Cross-Agent Audit Findings Queue — Auditor → Implementer Directive Channel | accepted | implemented | 2026-05-05 | **Accepted.** Implemented as the directed message bus, inbox/context hooks, CLI, and tests. Fourth architectural layer companion to ADR-182 (branch |
| [186](ADR-186-context-budget-enforcement.md) | Context Budget Enforcement — Activate the ADR-038 Wave 3 Limits | accepted | implemented | 2026-05-05 | **Accepted.** Implemented as `lib/context_budget.py`, a shared hook accountant, a UserPromptSubmit meter, and hook-level budget checks. Filed in response to tod |
| [188](ADR-188-mandatory-skill-invocation-at-high-confidence.md) | Mandatory Skill Invocation at High Router Confidence | accepted | implemented | 2026-05-06 | **Accepted (2026-05-06).** Implementation landed on session branch |
| [189](ADR-189-harness-implementation-coverage.md) | Surface Implementation Coverage for Agentic Primitives | accepted | implemented | 2026-05-06 | Accepted — 2026-05-06 |
| [191](ADR-191-cos-binary-release-pipeline.md) | COS Binary Release Pipeline | accepted | implemented | 2026-05-06 | Accepted — 2026-05-06 |
| [192](ADR-192-surface-5-adopt-bubbletea.md) | Surface 5 Bubble Tea Adoption | accepted | implemented | 2026-05-06 | Accepted — 2026-05-06 |
| [198](ADR-198-release-external-readiness-gate.md) | Release External Readiness Gate | accepted | implemented | 2026-05-06 | Accepted — 2026-05-06 |
| [199](ADR-199-state-retention-policy-and-reaper-protocol.md) | State Retention Policy and Reaper Protocol | accepted | implemented | 2026-05-06 | Accepted — 2026-05-06 |
| [200](ADR-200-state-retention-controller.md) | State Retention Controller | accepted | implemented | 2026-05-06 | Accepted — 2026-05-06 |
| [201](ADR-201-maintainer-agent-telemetry-promotion-loop.md) | Maintainer Agent and Telemetry Promotion Loop | accepted | implemented | 2026-05-06 | **Report**: `docs/06-Daily/reports/self-improvement-maintainer-agent-gap-2026-05-06.md` |
| [202](ADR-202-private-content-cross-harness-portability-boundary.md) | Private Content Cross-Harness Portability Boundary | accepted | implemented | 2026-05-06 | **Report**: `docs/06-Daily/reports/private-content-portability-gap-2026-05-06.md` |
| [203](ADR-203-subagent-capability-contract-and-launch-preflight.md) | Subagent Capability Contract and Launch Preflight | accepted | implemented | 2026-05-06 | **Implementation**: `manifests/subagent-capabilities.yaml`, `scripts/subagent_launch_preflight.py`, `scripts/cos subagent preflight` |
| [210](ADR-210-fleet-aggregated-confidence-boundary.md) | Fleet-Aggregated Confidence Boundary | accepted | implemented | 2026-05-06 | Accepted — Slice A dry-run exporter implemented |
| [212](ADR-212-cross-stack-license-audit-toolchain.md) | Cross-Stack License Audit Toolchain | accepted | implemented | 2026-05-06 | **Source**: Q2 tool-adoption review, `.cognitive-os/strategy/research/11-cross-stack-license-audit-tools.md` |
| [213](ADR-213-agent-preflight-before-stash-snapshot.md) | Agent Preflight Before Stash Snapshot | accepted | implemented | 2026-05-06 | **Source**: `docs/06-Daily/reports/stash-hidden-wip-postmortem-2026-05-06.md` |
| [216](ADR-216-tool-discovery-pre-use-gate.md) | Tool Discovery Pre-Use Gate | accepted | implemented | 2026-05-06 | **Source**: repeated dogfood evidence of ad-hoc external tool selection over existing COS primitives |
| [219](ADR-219-work-ownership-liveness-preflight.md) | Work Ownership Liveness Preflight | accepted | implemented | 2026-05-06 | During the license-switch work, WIP was preserved to a temporary branch |
| [222](ADR-222-pre-agent-stash-defer-until-launch-confirmed.md) | Pre-Agent Stash Deferred Until Agent Launch Confirmed | accepted | implemented | 2026-05-07 | **Supersedes (in part)**: the PreToolUse-Agent ordering currently relied on by `pre-agent-snapshot.sh`. |
| [223](ADR-223-agent-lifecycle-reconstruction.md) | Agent Lifecycle Reconstruction: Worktree-Per-Write-Agent | accepted | implemented | 2026-05-07 | **Source**: `docs/03-PoCs/research/multi-agent-orchestration-prior-art-2026-05-06.md`, `docs/03-PoCs/research/orchestration-gaps/background-agent-patterns.md`,  |
| [227](ADR-227-shadow-git-checkpoint-substrate.md) | Shadow-Git Checkpoint Substrate | accepted | implemented | 2026-05-07 | **Source**: [`docs/03-PoCs/research/orchestration-gaps/replay-timeline-architectures.md`](../../03-PoCs/research/orchestration-gaps/replay-timeline-architecture |
| [228](ADR-228-retry-contract-and-cost-budget.md) | Retry Contract + Cost Session Budget (consolidated) | accepted | implemented | 2026-05-07 | Accepted — Slices A–F implemented (2026-05-07) |
| [230](ADR-230-handoff-envelope-and-cycle-deduplication.md) | Agent Handoff Envelope + Call-Chain Deduplication | accepted | implemented | 2026-05-07 | **Source**: [`docs/03-PoCs/research/orchestration-gaps/agent-to-agent-handoff.md`](../../03-PoCs/research/orchestration-gaps/agent-to-agent-handoff.md). Product |
| [231](ADR-231-mcp-server-surface-for-cos-primitives.md) | MCP Server Surface for COS Primitives | accepted | implemented | 2026-05-07 | **Source**: [`docs/03-PoCs/research/orchestration-gaps/mcp-as-orchestration-bus.md`](../../03-PoCs/research/orchestration-gaps/mcp-as-orchestration-bus.md) |
| [232](ADR-232-sandbox-adapter-tiers.md) | Sandbox Adapter Tiers | accepted | implemented | 2026-05-07 | COS needs filesystem/process permission boundaries that are enforced below the prompt layer. Prior-art research recommends OS-native sandbox tiers first: Bubble |
| [233](ADR-233-cross-session-agent-team-file-ipc.md) | Cross-Session Agent-Team File IPC | accepted | implemented | 2026-05-07 | **Source**: [`docs/03-PoCs/research/orchestration-gaps/cross-session-agent-teams.md`](../../03-PoCs/research/orchestration-gaps/cross-session-agent-teams.md) |
| [234](ADR-234-approval-policies-as-code.md) | Approval Policies as Code | accepted | implemented | 2026-05-07 | COS has many shell hooks with embedded allow/deny logic. Research recommended a COS-native YAML policy evaluator before adopting heavy engines such as OPA, Ceda |
| [235](ADR-235-detached-agent-daemon.md) | Detached Agent Daemon | accepted | implemented | 2026-05-07 | **Source**: [`docs/03-PoCs/research/orchestration-gaps/background-agent-patterns.md`](../../03-PoCs/research/orchestration-gaps/background-agent-patterns.md) |
| [237](ADR-237-test-execution-efficiency-protocol.md) | Test Execution Efficiency Protocol | accepted | implemented | 2026-05-07 | Cognitive OS test lanes are intentionally broad: unit, behavior, integration, chaos, benchmark, audit, smoke, cross-harness, and release gates. Running `make te |
| [239](ADR-239-isolated-worktree-default-for-write-agents.md) | Isolated Worktree Default for Write Agents | accepted | implemented | 2026-05-08 | Accepted. This ADR records the corrective decision after the 2026-05-08 |
| [240](ADR-240-primitive-coherence-audit-and-ownership-manifest.md) | Primitive Coherence Audit and Ownership Manifest | accepted | implemented | 2026-05-08 | status: accepted |
| [242](ADR-242-git-filter-repo-wrapper-preserves-remote.md) | git-filter-repo Wrapper Preserves Remote and Refuses Non-Idempotent Re-Runs | accepted | implemented | 2026-05-08 | Accepted — Slice A implemented. `scripts/cos-filter-repo-wrap.sh` preserves remotes, refuses idempotent reruns, writes recovery artifacts, and `lib/history_sani |
| [243](ADR-243-post-rewrite-push-collision-exception.md) | Post-Rewrite Push-Collision Check Exception | accepted | implemented | 2026-05-08 | Accepted — Slice A implemented. History sanitization writes `.cognitive-os/runtime/last-rewrite.json`; push-collision detection consumes it to allow matching po |
| [244](ADR-244-trust-report-claim-validator-must-enforce.md) | Trust Report Claim-Validator Must Enforce, Not Advise | accepted | implemented | 2026-05-08 | Accepted — Slice A implemented. `scripts/claim_enforcer.py` enforces structured `verification:` evidence for high-stakes claims, `hooks/claim-validator.sh` bloc |
| [245](ADR-245-chaos-tests-readonly-production-source.md) | Chaos Tests Run with Read-Only Production Source | accepted | implemented | 2026-05-08 | Accepted — Slice A implemented. `tests/chaos/conftest.py` installs `chaos_readonly_workspace`, restores source mutations under `lib/`, `scripts/`, and `hooks/`, |
| [247](ADR-247-manifest-driven-postmortem-regression-audits.md) | Manifest-Driven Postmortem Regression Audits and External Tool Adapters | accepted | implemented | 2026-05-08 | Accepted. This ADR documents the policy correction made after ADR-242 through |
| [250](ADR-250-skill-router-retrieval-adapter-boundary.md) | Skill Router Retrieval Adapter Boundary | accepted | implemented | 2026-05-08 | Accepted — Slice A implemented. |
| [251](ADR-251-agent-orchestration-adapter-boundary.md) | Agent Orchestration Adapter Boundary | accepted | implemented | 2026-05-08 | Accepted — Slice A implemented. |
| [252](ADR-252-capability-coverage-matrix-and-feature-reality-ledger.md) | Capability Coverage Matrix and Feature Reality Ledger | accepted | implemented | 2026-05-08 | Accepted — Slice A implemented. |
| [255](ADR-255-feature-to-external-tool-due-diligence.md) | Feature-to-External-Tool Due Diligence | accepted | implemented | 2026-05-08 | Accepted — Slice A implemented |
| [256](ADR-256-primitive-contract-registry-and-runtime-evidence-ledger.md) | Primitive Contract Registry and Runtime Evidence Ledger | accepted | implemented | 2026-05-09 | Accepted — implemented through Phases 1–6; all primitive-lifecycle rows are registry-backed; OpenCode signed smoke covers the first 20 runtime primitives |
| [257](ADR-257-primitive-contract-registry-phase-1.md) | Primitive Contract Registry Phase 1 | accepted | implemented | 2026-05-09 | Accepted — implemented |
| [260](ADR-260-grant-signed-cosd-api.md) | Grant-Signed cosd API: HMAC + Nonce + TTL + Scope Binding | accepted | implemented | 2026-05-11 | **Date:** 2026-05-11 |
| [261](ADR-261-memory-governance-v2.md) | Memory Governance v2: Typed Memory with Verification & Staleness Policies | accepted | implemented | 2026-05-11 | **Date:** 2026-05-11 |
| [263](ADR-263-tool-replay-budget-ledger.md) | Tool-Replay Budget Ledger: Per-Session Cap + Preview/Reference-Only Modes | accepted | implemented | 2026-05-11 | **Date:** 2026-05-11 |
| [264](ADR-264-tool-result-envelope.md) | Tool Result Envelope: Compact Envelope Format for Large Tool Outputs | accepted | implemented | 2026-05-11 | **Date:** 2026-05-11 |
| [268](ADR-268-history-sanitization-2026-05-11.md) | Defensive history sanitization for external-pattern attribution | accepted | implemented | 2026-05-11 | Accepted (2026-05-11) |
| [269](ADR-269-mandatory-adr-reference-for-history-rewrites.md) | Mandatory ADR Reference for History Rewrites | accepted | implemented | 2026-05-11 | Accepted (2026-05-11). Implementation lands in companion commit set. |
| [270](ADR-270-legal-compliance-workflow-automation.md) | Legal Compliance Workflow Automation | accepted | implemented | 2026-05-11 | Accepted (2026-05-11). Implementation lands in companion commit. |
| [276](ADR-276-primitive-authority-write-effects.md) | Primitive Authority and Write-Effects Audit | accepted | implemented | 2026-05-12 | Accepted and implemented for the first ratchet. |
| [277](ADR-277-documentation-truth-control.md) | Documentation Truth Control | accepted | implemented | 2026-05-12 | Accepted and implemented. |
| [279](ADR-279-orphan-repo-scan-process-audit.md) | Orphan Repo-Scan Process Audit | accepted | implemented | 2026-05-12 | Accepted and implemented — 2026-05-12. |
| [280](ADR-280-product-question-to-evidence-primitive.md) | Product Question-to-Evidence Primitive | accepted | implemented | 2026-05-12 | Accepted and implemented — 2026-05-12. |
| [281](ADR-281-adr-implementation-reality-audit.md) | ADR Implementation Reality Audit | accepted | implemented | 2026-05-12 | Accepted — Phase 1 shipped 2026-05-12 (audit + allowlist + tests + control-plane wiring). |
| [282](ADR-282-product-answer-card-cache-and-freshness-ledger.md) | Product Answer Card Cache and Freshness Ledger | accepted | implemented | 2026-05-12 | Accepted and implemented — 2026-05-12. |
| [283](ADR-283-script-exposure-audit-and-invocation-ratchet.md) | Script Exposure Audit and Invocation Ratchet | accepted | implemented | 2026-05-12 | Accepted and implemented — 2026-05-12. |
| [284](ADR-284-doc-path-reference-audit.md) | Documentation Path Reference Audit | accepted | implemented | 2026-05-12 | Accepted and implemented — 2026-05-12. |
| [285](ADR-285-skill-registry-runtime-drift-detection.md) | Skill Registry Runtime Drift Detection | accepted | implemented | 2026-05-13 | Accepted and implemented — 2026-05-13. |
| [286](ADR-286-stack-aware-skill-recommendation-session-start.md) | Stack-Aware Skill Recommendation at Session Start | accepted | implemented | 2026-05-13 | Accepted and implemented — 2026-05-13. |
| [287](ADR-287-engram-v3-evidence-grounded-claims-and-portable-bundles.md) | Engram v3: Evidence-Grounded Claims, Write Gate, BM25 Retrieval Wrapper, and Portable Bundles | accepted | implemented | 2026-05-13 | **Date:** 2026-05-13 |
| [288](ADR-288-web-automation-adapter-for-dispatch.md) | Web-Automation Adapter for Dispatch (browser-use) | accepted | implemented | 2026-05-13 | - **Status:** Accepted |
| [292](ADR-292-runtime-perf-primitives-lazy-imports-and-mcp-thread-bridge.md) | Runtime Performance Primitives: Lazy Imports and MCP Sync↔Async Thread Bridge | accepted | implemented | 2026-05-13 | **Date:** 2026-05-13 |
| [293](ADR-293-typed-hook-event-contracts.md) | Typed Hook Event Contracts: Frozen Dataclasses for Claude Code Hook Payloads | accepted | implemented | 2026-05-13 | **Date:** 2026-05-13 |
| [294](ADR-294-memory-quality-scoring-extension.md) | Memory Quality Scoring: Four-Dimension Quality Fields and min_quality Filter for Engram v3 | accepted | implemented | 2026-05-13 | **Date:** 2026-05-13 |
| [295](ADR-295-agent-reflection-loop-primitive.md) | Agent Reflection Loop Primitive: Bounded Iterative Critique with Min/Max Floors | accepted | implemented | 2026-05-13 | **Date:** 2026-05-13 |
| [296](ADR-296-language-agnostic-semantic-routing.md) | Language-Agnostic Semantic Routing for the COS Skill Router | accepted | implemented | 2026-05-13 | Accepted — 2026-05-13. |
| [297](ADR-297-llm-dispatched-routing-fallback.md) | LLM-Dispatched Routing as Low-Confidence Fallback for the Skill Router | accepted | implemented | 2026-05-13 | Accepted — 2026-05-13. |
| [298](ADR-298-routing-model-benchmark-harness.md) | Reproducible Routing-Model Benchmark Harness | accepted | implemented | 2026-05-13 | Accepted — 2026-05-13. |
| [299](ADR-299-skill-description-enrichment.md) | LLM-Driven Multilingual Enrichment of Skill Routing Intents | accepted | implemented | 2026-05-13 | Accepted — 2026-05-13. Implemented in the same change. |
| [300](ADR-300-semantic-routing-model-selection.md) | Semantic Routing Model Selection — Operator Swap + Benchmark Winner Discovery | accepted | implemented | 2026-05-13 | Accepted — 2026-05-13. |
| [301](ADR-301-onnx-direct-routing-adapter.md) | ONNX-Direct Routing Adapter — Generic HF-Hosted ONNX Bi-Encoder Loader | accepted | implemented | 2026-05-13 | Accepted — 2026-05-13. |
| [302](ADR-302-language-agnostic-primitive-routing-authoring.md) | Language-Agnostic Primitive Routing Authoring Contract | accepted | implemented | 2026-05-13 | Accepted — 2026-05-13. Implemented in the same change. |
| [303](ADR-303-agent-spawn-cold-start-benchmark.md) | Sub-Agent Spawn Cold-Start Benchmark | accepted | implemented | 2026-05-13 | Session 2026-05-13 identified a measurement gap: orchestrator SessionStart is |
| [304](ADR-304-telemetry-aggregator-feedback-loop.md) | Telemetry Aggregator + Feedback Loop | accepted | implemented | 2026-05-13 | Accepted, implemented 2026-05-13. |
| [305](ADR-305-dependency-coverage-reconciliation-audit.md) | Dependency Coverage Reconciliation Audit | accepted | implemented | 2026-05-14 | Accepted and implemented 2026-05-14. |
| [306](ADR-306-scope-projection-runtime-audit.md) | Scope Projection Runtime Audit | accepted | implemented | 2026-05-14 | Accepted, implemented 2026-05-14. |
| [307](ADR-307-dependency-tool-intake-and-profile-ratchet.md) | Dependency Tool Intake and Profile Ratchet | accepted | implemented | 2026-05-14 | Accepted and implemented 2026-05-14. |
| [308](ADR-308-dependency-maintenance-install-update-git-hooks.md) | Dependency Maintenance in Install, Update, and Git Hooks | accepted | implemented | 2026-05-14 | ADR-305 added a read-only dependency coverage audit and ADR-307 added triage plus a fail-new profile ratchet. Those primitives make dependency drift visible, bu |
| [309](ADR-309-current-window-subagent-spawn-slos.md) | Current-Window Subagent Spawn SLOs | accepted | implemented | 2026-05-14 | ADR-303 introduced a synthetic sub-agent spawn cold-start benchmark. ADR-304 made production telemetry the authoritative latency signal through `manifests/obser |
| [310](ADR-310-cross-platform-headless-dependency-bootstrap.md) | Cross-Platform and Headless Dependency Bootstrap | accepted | implemented | 2026-05-14 | ADR-168 created the dependency installation contract and ADR-308 made dependency drift visible during install, update, push, and pull. That still left a product |
| [311](ADR-311-primitive-closure-ratchets-and-subagent-budget-enforcement.md) | Primitive Closure Ratchets and Subagent Budget Enforcement | accepted | implemented | 2026-05-14 | - **Status**: Accepted |
| [312](ADR-312-harness-normalized-primitive-closure.md) | Harness-Normalized Primitive Closure | accepted | implemented | 2026-05-14 | - **Status**: Accepted |
| [313](ADR-313-commercial-architecture-map-answer-primitive.md) | Commercial Architecture Map Answer Primitive | accepted | implemented | 2026-05-14 | Accepted and implemented — 2026-05-14. |
| [314](ADR-314-primitive-scope-taxonomy-calibration-loop.md) | Primitive Scope Taxonomy Calibration Loop | accepted | implemented | 2026-05-14 | Accepted and implemented — 2026-05-14. |
| [315](ADR-315-primitive-parser-contracts.md) | Primitive Parser Contracts Before Scope Classification | accepted | implemented | 2026-05-14 | Accepted and implemented — 2026-05-14. |
| [316](ADR-316-agentic-literacy-before-os-abstraction.md) | Agentic Literacy Before OS Abstraction | accepted | implemented | 2026-05-15 | Accepted and implemented as documentation doctrine — 2026-05-15. |
| [317](ADR-317-cos-falsification-before-promotion.md) | COS Falsification Before Promotion | accepted | implemented | 2026-05-15 | Accepted and implemented as product-governance doctrine — 2026-05-15. |
| [318](ADR-318-copy-only-checkpoints-and-stash-quarantine.md) | Copy-Only Checkpoints and Stash Quarantine | accepted | implemented | 2026-05-15 | Accepted. |
| [320](ADR-320-install-scope-surface-debt.md) | Install Scope Surface Debt and Protected Config Boundary | accepted | implemented | 2026-05-15 | Accepted. |
| [321](ADR-321-primitive-scope-plane-balance-and-proof-ratchets.md) | Primitive Scope Plane Balance and Proof Ratchets | accepted | implemented | 2026-05-15 | Accepted. |
| [322](ADR-322-consumer-sdd-lane-contract.md) | Consumer SDD Lane Contract | accepted | implemented | 2026-05-15 | Accepted. |
| [323](ADR-323-primitive-behavior-depth-ratchet.md) | Primitive Behavior Depth Ratchet | accepted | implemented | 2026-05-15 | Accepted. |
| [329](ADR-329-skill-platform-support-levels.md) | Skill Platform Support Levels | accepted | implemented | 2026-05-20 | Accepted and implemented for the existing `generic-cli` skill surface. |
| [333](ADR-333-publication-safety-primitive.md) | Publication Safety Primitive | accepted | implemented | 2026-05-31 | Accepted — implemented on 2026-05-31. |
| [334](ADR-334-portable-duplicate-code-quality-primitive.md) | Portable Duplicate-Code Quality Primitive | accepted | implemented | 2026-06-05 | Accepted — implemented on 2026-06-05. |
| [335](ADR-335-generic-task-closure-ledger-gate.md) | Generic Task Closure Ledger Gate | accepted | implemented | 2026-06-06 | Accepted — implemented on 2026-06-06. |
| [336](ADR-336-agent-loop-engineering-runtime.md) | Agent Loop Engineering Runtime | accepted | implemented | 2026-06-13 | Cognitive OS already had bounded reflection, goal-state gates, flicker reports, and task closure checks, but agent loops were not represented as a first-class p |
| [337](ADR-337-agent-process-loop-contract-layer.md) | Agent Process Loop Contract Layer | accepted | implemented | 2026-06-13 | Accepted — implemented on 2026-06-13. |
| [340](ADR-340-english-native-artifacts-multilingual-user-routing.md) | English-Native Artifacts with Multilingual User-Facing Routing | accepted | implemented | 2026-06-17 | Accepted — 2026-06-17. Implemented by the language policy manifest and audit ratchets listed in this ADR. |

### Active / Partial (124)

| ADR | Title | Decision Status | Implementation | Date | Summary |
|---|---|---|---|---|---|
| [006](ADR-006-agpl-license-compliance.md) | AGPL License Compliance -- Replace Redis and MinIO | accepted | partial | 2026-03-23 | **Date:** 2026-03-23 |
| [014](ADR-014-sdd-fast-path.md) | SDD Fast Path -- Skip Phases for Capable Models | accepted | partial | 2026-03-31 | **Date:** 2026-03-31 |
| [016](ADR-016-context-diet.md) | Context Diet -- Token Optimization Strategy | accepted | partial | 2026-03-31 | **Date:** 2026-03-31 |
| [018](ADR-018-docker-to-pip-migration.md) | Docker-to-pip Migration -- Service Infrastructure Change | accepted | partial | 2026-04-11 | **Date:** 2026-04-11 to 2026-04-13 |
| [019](ADR-019-scope-tagging.md) | Scope Tagging -- Agentic Primitive Audience Classification | accepted | partial | 2026-04-13 | **Date:** 2026-04-13 |
| [020](ADR-020-contamination-fix.md) | Contamination Fix -- Remove Project-Specific Code from OS | accepted | partial | 2026-04-13 | **Date:** 2026-04-13 |
| [021](ADR-021-vendor-agnostic-with-adapters.md) | Vendor-Agnostic State with Provider Adapters | accepted | partial | 2026-04-16 | **Date:** 2026-04-16 |
| [022](ADR-022-prompt-type-hooks-adoption.md) | Prompt-Type Hooks Adoption (Haiku-Evaluated Advisories) | accepted | partial | 2026-04-15 | **Date:** 2026-04-15 |
| [023](ADR-023-updated-input-pattern.md) | Mutate, Don't Block — `updatedInput` for PreToolUse Hooks | accepted | partial | 2026-04-15 | **Date:** 2026-04-15 |
| [024](ADR-024-task-panel-bridge.md) | Task Panel Bridge — Correlate COS Tasks with Claude Code tool_use_id | accepted | partial | 2026-04-16 | **Date:** 2026-04-16 |
| [025](ADR-025-install-update-loop.md) | Install/Update Loop — Closing the Advisory-Only Gap | accepted | partial | 2026-04-17 | **Date:** 2026-04-17 |
| [026](ADR-026-r2-r3-design-review.md) | R2 and R3 Consolidation — Design Review | accepted | partial | 2026-04-17 | **Date:** 2026-04-17 |
| [026a](ADR-026a-decisions.md) | R2 and R3 Design Review — Proposed Decisions (Addendum) | accepted | partial | 2026-04-17 | **Status:** CLOSED — R3 decisions (D3.1–D3.3) accepted and implemented 2026-04-17 |
| [028c](ADR-028c.md) | Addendum: MetricEvent schema versioning + migration strategy | accepted | partial | 2026-04-20 | MetricEvent.schema_version is a monotonically-increasing integer starting at 1. |
| [029](ADR-029.md) | Anti-reinvention gate (reinvention-check.sh wired) | accepted | partial | 2026-04-20 | **Deciders**: Maintainer |
| [029b](ADR-029b-reinvention-phase-b-semantic.md) | Reinvention gate Phase B: semantic similarity | accepted | partial | 2026-04-20 | **Deciders**: Maintainer |
| [030](ADR-030.md) | Auto-trigger session-wrapup (Q1 prompt-match + Q2 commit banner) | accepted | partial | 2026-04-20 | Today the orchestrator has 7 session lifecycle skills (`/session-wrapup`, `/session-backlog`, `/session-report-executive`, `/resume-tasks`, `/session-manager`,  |
| [031](ADR-031.md) | Continuous Aspirational/Dormant/Real Audit | accepted | partial | 2026-04-20 | Manual forensic audits showed a persistent gap between the agentic primitives we build and the agentic primitives |
| [032](ADR-032-orchestrator-trap-preview.md) | Orchestrator-side trap awareness before Agent launch | accepted | partial | 2026-04-20 | The COS currently operates in FIRE_AND_FORGET mode (banner: "Valkey ✅, Executor ❌"). In this mode: |
| [033](ADR-033-harness-agnostic-event-capture.md) | Harness-agnostic event capture layer | accepted | partial | 2026-04-20 | The Cognitive OS observes agent activity through two JSONL streams: |
| [033b](ADR-033b-duration-correlation-and-aider-hardening.md) | Duration Correlation and Aider Version Dispatch Hardening | accepted | partial | 2026-04-20 | **Parent**: ADR-033 (`c9f52bf` — harness-agnostic event capture) |
| [035](ADR-035-worktree-cwd-enforcement.md) | Worktree CWD Enforcement: 3-Layer Defense | accepted | partial | 2026-04-20 | **Deciders**: Maintainer |
| [041](ADR-041.md) | Exercised Coverage Pipeline (MVP) | accepted | partial | 2026-04-20 | **Deciders**: luum-agent-os team |
| [042](ADR-042-valkey-local-daemon.md) | Valkey Local Daemon — Extract from Docker (D34 Partial) | accepted | partial | 2026-04-20 | **Deciders**: Matias Améndola |
| [045](ADR-045-postgres-local-daemon.md) | PostgreSQL Local Daemon — Extract from Docker (D34) | accepted | partial | 2026-04-30 | **Deciders**: Matias Améndola |
| [048](ADR-048-docker-container-image-freshness.md) | Docker Container Image Freshness | accepted | partial | 2026-04-21 | **Accepted** — 2026-04-21. Follow-up to a live incident the same day. |
| [050](ADR-050-per-skill-routing-policy.md) | Per-Skill Routing Policy | accepted | partial | 2026-04-21 | **Accepted** — 2026-04-21. Schema + dispatch integration shipped. Builds on |
| [054](ADR-054-project-docs-convention.md) | Project Documentation Convention (10 Categories) | accepted | partial | 2026-04-21 | **Accepted** — 2026-04-21. Implementation lives in `lib/project_scaffolder.py` |
| [055](ADR-055-docs-convention-enforcement.md) | Docs Convention Enforcement + Skill Writers | accepted | partial | 2026-04-21 | **Accepted** — 2026-04-21. Addendum to ADR-054. Implementation lives in |
| [055b](ADR-055b-destructive-git-block.md) | Destructive Git Op Block (User Context Elevation) | accepted | partial | 2026-04-21 | **Supersedes**: partial warn-only behavior of `hooks/destructive-git-blocker.sh` |
| [056](ADR-056-adaptive-agent-dispatch.md) | Adaptive Agent() dispatch: 3-tier auto-switch Claude → Qwen | accepted | partial | 2026-04-21 | - **Status**: L1 IMPLEMENTED (advisory-only). L2/L3 DEFERRED. |
| [057](ADR-057-cross-harness-authoring-and-driver-projection.md) | Cross-Harness Authoring and Driver Projection | accepted | partial | 2026-04-23 | Date: 2026-04-23 |
| [058](ADR-058-observability-migration-langfuse-to-phoenix.md) | Observability Migration: Langfuse → Arize Phoenix | accepted | partial | 2026-04-24 | - **Status**: Accepted |
| [060](ADR-060-local-only-optional-services.md) | Local-Only Policy for Optional Services | accepted | partial | 2026-04-24 | **Accepted** — 2026-04-24. Effective immediately. |
| [061](ADR-061-focus-narrative-and-external-evidence.md) | Focus Narrative and External Evidence | accepted | partial | 2026-04-24 | **Accepted** — 2026-04-24. Fills the 5 gaps identified during the existential |
| [063](ADR-063-agent-tool-replication-strategy.md) | Agent() Tool Replication Strategy | accepted | partial | 2026-04-24 | **Accepted** — 2026-04-24. Clarifies the scope of ADR-051 / ADR-062 and |
| [064](ADR-064-harness-agnostic-cognitive-os.md) | Harness-Agnostic Cognitive OS | accepted | partial | 2026-04-30 | **Implementation-plan**: `.cognitive-os/plans/architecture/adr-064-implementation-plan.md` |
| [068](ADR-068-adaptive-test-runner-capacity.md) | Adaptive Test Runner Capacity Detection | accepted | partial | 2026-04-30 | **Accepted** — Phase 2 implemented 2026-04-30. Original proposal: 2026-04-24. |
| [071](ADR-071-engram-lifecycle-evolution.md) | Engram Lifecycle Evolution via Wrapper Layer | accepted | partial | 2026-04-27 | **Accepted** — 2026-04-27 |
| [072](ADR-072-test-lane-taxonomy.md) | Test Lane Taxonomy & Escalation Ladder | accepted | partial | 2026-04-29 | **Accepted** — 2026-04-29. |
| [073](ADR-073-test-architecture-role-registry.md) | Test Architecture Role Registry | accepted | partial | 2026-04-30 | **Accepted** — 2026-04-30. |
| [074](ADR-074-tier-0-learning-loop-closure.md) | Tier-0 Learning-Loop Closure | accepted | partial | 2026-04-30 | **Status:** Accepted |
| [075](ADR-075-stage2-selective-expansion.md) | Stage 2 Selective Expansion — Tier-Based Ref-Key Filtering | accepted | partial | 2026-04-30 | **Engram topic**: `cos/stage2-selective-expansion-plan` |
| [076](ADR-076-skill-frontmatter-alignment.md) | SKILL.md Frontmatter Alignment with Hermes Spec | accepted | partial | 2026-04-30 | **Engram topic**: `cos/tier2-hermes-alignment` |
| [077](ADR-077-peer-card-local-model.md) | Peer-Card Local User-Memory Model (Replaces Honcho) | accepted | partial | 2026-04-30 | **Engram topic**: `cos/tier2-hermes-alignment` |
| [078](ADR-078-mid-task-memory-tool.md) | Mid-Task Memory Tool (Port from Hermes) | accepted | partial | 2026-04-30 | **Deciders**: Maintainer |
| [079](ADR-079-corerules-applies-to-self-hosting.md) | CORE_RULES applies to self-hosting mode | accepted | partial | 2026-04-30 | **Author**: Maintainer |
| [081](ADR-081-codex-harness-adapter.md) | Codex Harness Adapter | accepted | partial | 2026-04-30 | **Author**: Maintainer |
| [082](ADR-082-plan-location-convention.md) | Plan Location Convention | accepted | partial | 2026-04-30 | **Author**: Maintainer |
| [083](ADR-083-governed-self-improvement-loop.md) | Governed Self-Improvement Loop | accepted | partial | 2026-04-29 | **Author**: Maintainer |
| [086](ADR-086-hook-execution-observability.md) | Hook Execution Observability | accepted | partial | 2026-04-30 | Accepted. The canonical number is ADR-086; ADR-085 was an abandoned contested reservation during the concurrent ADR slot race documented by ADR-089. |
| [087](ADR-087-adr-namespace-consolidation.md) | ADR Namespace Consolidation | accepted | partial | 2026-04-30 | **Author**: Maintainer |
| [089](ADR-089-multi-session-git-coordination.md) | Multi-Session Git Coordination | accepted | partial | 2026-04-30 | **Author**: Maintainer |
| [090](ADR-090-auto-skill-repair.md) | Auto-skill repair via failure-threshold signals | accepted | partial | 2026-04-30 | **Author**: Maintainer (COS sub-agent) |
| [091](ADR-091-headless-clustered-runtime-direction.md) | Headless and Clustered Runtime Direction | accepted | partial | 2026-04-30 | - **Status**: Accepted as direction, not yet implemented as a production cluster |
| [093](ADR-093-simplify-profiles.md) | Simplify Install Profiles — Collapse 3-Tier System to `default` + `--full` | accepted | partial | 2026-04-30 | Accepted (2026-04-16) |
| [094](ADR-094-agent-git-safety.md) | Agent Git Operations Safety — Layered Prevention of Destructive Git Ops | accepted | partial | 2026-04-30 | Accepted (2026-04-16) |
| [095](ADR-095-skill-synthesis-success-patterns.md) | Skill synthesis driven by success patterns | accepted | partial | 2026-04-30 | **Author**: Maintainer (COS sub-agent) |
| [096](ADR-096-review-agent-pattern.md) | Review-agent pattern (Hermes-style audit loop) | accepted | partial | 2026-05-01 | **Author**: Maintainer (COS sub-agent) |
| [097](ADR-097-documentation-execution-audit.md) | Documentation Execution Audit | accepted | partial | 2026-04-30 | - Status: Accepted |
| [098](ADR-098-multi-agent-file-coordination.md) | Multi-Agent File Coordination | accepted | partial | 2026-04-30 | **Author**: Maintainer |
| [101](ADR-101-intent-aware-rate-limiter.md) | Intent-Aware Rate Limiter Flow Control | accepted | partial | 2026-05-01 | **Author**: Maintainer |
| [102](ADR-102-task-tracker-lifecycle.md) | Task tracker lifecycle: pending → in_progress → terminal, with PID capture and zombie reaper | accepted | partial | 2026-04-30 | Accepted. |
| [105](ADR-105-claim-verification-contract.md) | Bilateral Claim Verification Contract | implemented | partial | 2026-05-02 | **Author**: Maintainer |
| [107](ADR-107-human-approved-rollback.md) | Human-Approved Rollback Boundary | accepted | partial | 2026-05-02 | **Author**: Maintainer |
| [110](ADR-110-preserve-branch-governance.md) | Preserve Branch Governance | accepted | partial | 2026-05-02 | **Author**: Maintainer + Cognitive OS |
| [111](ADR-111-core-consumer-concurrency-safety-boundary.md) | Core/Consumer Boundary for Concurrent-Agent Safety | accepted | partial | 2026-05-02 | Accepted — Implemented 2026-05-02. Related: ADR-108, ADR-110. |
| [116](ADR-116-multi-session-coordination-primitives.md) | Multi-Session Coordination Primitives | accepted | partial | 2026-05-02 | **Author**: Maintainer (operator) + Software Architect (analysis) |
| [118](ADR-118-multi-ide-swarm-testbed.md) | Multi-IDE Swarm Safety Testbed | accepted | partial | 2026-05-02 | Accepted (2026-05-02). This is the automated acceptance-test umbrella for ADR-116 and its transactional coordination rollout. |
| [120](ADR-120-conversation-to-primitive-harvester.md) | Conversation-to-Primitive Harvester | accepted | partial | 2026-05-02 | Accepted — 2026-05-02 |
| [121](ADR-121-foundation-hardening-program.md) | Foundation Hardening Program | accepted | partial | 2026-05-02 | Accepted — 2026-05-02 |
| [127](ADR-127-active-primitive-index.md) | Active Primitive Index | accepted | partial | 2026-05-12 | Accepted for Phase 1 DX. |
| [135](ADR-135-self-evolving-doctrine-proposals.md) | Self-Evolving Doctrine Proposals | accepted | partial | 2026-05-03 | **Implementation**: `scripts/cos-doctrine-proposer` |
| [136](ADR-136-cross-instance-learning-runway.md) | Cross-Instance Learning Runway | accepted | partial | 2026-05-03 | **Implementation**: `scripts/cos_cross_instance_learning.py` |
| [147](ADR-147-agent-capability-coverage-pipeline.md) | Agent Capability Coverage Pipeline | accepted | partial | 2026-05-04 | Accepted — 2026-05-04 |
| [162](ADR-162-task-lifecycle-interruption-question-worktree-pr-protocol.md) | Task Lifecycle, Interruption, Question, Worktree, and PR Protocol | implemented | partial | 2026-05-05 | **Implemented for contract scope** — 2026-05-05. The task lifecycle schema, contract tests, and manual proof checklist exist; full queue/worker/PR runtime enfor |
| [163](ADR-163-cos-instance-installer.md) | Cognitive OS Instance Installer | accepted | partial | 2026-05-05 | **Accepted** — 2026-05-05 |
| [168](ADR-168-cross-device-dependency-installation.md) | Cross-Device Dependency Installation Contract | implemented | partial | 2026-05-05 | **Implemented for the manifest-driven dry-run installer and credential-safe |
| [178](ADR-178-openharness-primitive-adoption.md) | OpenHarness Primitive Adoption (HttpHookDefinition, PromptHookDefinition, ProviderProfile) | accepted | partial | 2026-05-05 | **Deciders**: Maintainer |
| [190](ADR-190-harness-action-receipts.md) | Harness Action Receipts and VCS Event Telemetry | accepted | partial | 2026-05-06 | Accepted — 2026-05-06 |
| [193](ADR-193-cosd-local-network-api.md) | cosd Local Network API | accepted | partial | 2026-05-06 | Accepted — 2026-05-06 |
| [194](ADR-194-cosd-secure-remote-api.md) | cosd Secure Remote API Guardrails | accepted | partial | 2026-05-06 | Accepted — 2026-05-06 |
| [195](ADR-195-surface-5-operable-tui-contract.md) | Surface 5 Operable TUI Contract | accepted | partial | 2026-05-06 | Accepted — 2026-05-06 |
| [196](ADR-196-cosd-task-api-and-provider-boundary.md) | cosd Task API and Provider Boundary | accepted | partial | 2026-05-06 | Accepted — 2026-05-06 |
| [197](ADR-197-surface-5-operable-actions.md) | Surface 5 Operable Actions | accepted | partial | 2026-05-06 | Accepted — 2026-05-06 |
| [204](ADR-204-signal-quality-and-reward-integrity-boundary.md) | Signal Quality and Reward Integrity Boundary | accepted | partial | 2026-05-06 | Accepted — implemented |
| [205](ADR-205-cross-stream-trace-joiner-and-flight-recorder.md) | Cross-Stream Trace Joiner and Flight Recorder | accepted | partial | 2026-05-06 | Accepted — implemented |
| [206](ADR-206-aspirational-claim-decommission-gate.md) | Aspirational Claim Decommission Gate | accepted | partial | 2026-05-06 | **Source**: `.cognitive-os/strategy/research/03-aspirational-dormant.md`, `.cognitive-os/strategy/00-first-approach.md`, `.cognitive-os/strategy/02-pre-launch-p |
| [208](ADR-208-imported-pattern-closure-contract.md) | Imported Pattern Closure Contract | accepted | partial | 2026-05-06 | **Source**: `.cognitive-os/strategy/research/05-hermes-imitation-forensics.md`, `.cognitive-os/strategy/research/06-external-patterns-benchmark.md` |
| [209](ADR-209-maintainer-reconciler-experiment-contract.md) | Maintainer Reconciler Experiment Contract | accepted | partial | 2026-05-06 | **Source**: `.cognitive-os/strategy/research/06-external-patterns-benchmark.md`, `.cognitive-os/strategy/research/08-self-improvement-roadmap.md` |
| [211](ADR-211-service-mode-readiness-gate.md) | Service-Mode Readiness Gate | accepted | partial | 2026-05-06 | Accepted — initial readiness gate implemented |
| [215](ADR-215-cross-stack-secret-audit-toolchain.md) | Cross-Stack Secret Audit Toolchain | accepted | partial | 2026-05-06 | **Source**: Q3 tool-adoption review (cross-stack secret/credential/PII detection), |
| [217](ADR-217-cross-stack-adoption-truth-audit.md) | Cross-Stack Adoption Truth Audit Toolchain | accepted | partial | 2026-05-06 | **Source**: Operator question — *"analysis is missing on whether it is already adopted and how (this should also be in the primitives)"* |
| [218](ADR-218-history-sanitization-toolchain.md) | History Sanitization Toolchain | accepted | partial | 2026-05-07 | **Source**: Operator question — *"how do we clean what is in git about sensitive data and these license changes without creating a new repo?"* |
| [220](ADR-220-worktree-divergence-audit.md) | Worktree Divergence Audit Toolchain | accepted | partial | 2026-05-06 | **Source**: Operator session 2026-05-06 — sed-fix on `.cognitive-os/preserve-manifests/*` appeared "lost" because commits landed on `main` while the operator wa |
| [221](ADR-221-stash-ref-by-sha-not-by-position.md) | Stash References by SHA, Not by Position | accepted | partial | 2026-05-06 | **Supersedes (in part)**: the marker-file format produced by `pre-agent-snapshot.sh` and consumed by `post-agent-snapshot-restore.sh`. |
| [225](ADR-225-branch-per-task-mode.md) | Branch-Per-Task Mode | accepted | partial | 2026-05-07 | Worktree-per-write-agent isolates filesystem mutations, but branch identity still needs a stable operator-visible contract. Without a branch-per-task policy, de |
| [226](ADR-226-event-sourced-session-bus.md) | Event-Sourced Session Bus | accepted | partial | 2026-05-07 | **Extends**: **ADR-205 (Cross-Stream Trace Joiner and Flight Recorder)** — ADR-226 is an *extension* of the Flight Recorder's append-only event substrate, not a |
| [236](ADR-236-deferred-tool-loading-and-toolsearch.md) | Deferred Tool Loading + ToolSearch Adoption | accepted | partial | 2026-05-07 | The orchestration research recommended adopting the ToolSearch/deferred-loading pattern instead of loading every tool schema into every session. This is not a s |
| [241](ADR-241-consolidated-cos-bypass-allowlist.md) | Consolidate Hook-Bypass Envs into a Single COS_BYPASS Allowlist | accepted | partial | 2026-05-08 | Accepted — Slice A implemented. Shared resolver, cheatsheet, target hook integration, and behavior tests are active; broad ecosystem bypass consolidation remain |
| [246](ADR-246-release-transaction-freeze.md) | Release Transaction Freeze for Destructive and Public-State Operations | accepted | partial | 2026-05-08 | Accepted — Slice A implemented. `scripts/cos-release-freeze` now provides `--prepare`, `--begin`, `--status`, and `--end`; receipts are written under `.cognitiv |
| [248](ADR-248-control-plane-audit-loop.md) | Control-Plane Audit Loop for ADR-239+ Primitive Drift | accepted | partial | 2026-05-08 | Accepted — Slice A implemented. |
| [249](ADR-249-primitive-behavioral-proof-anti-overfit-tests.md) | Primitive Behavioral Proof and Anti-Overfit Testing | accepted | partial | 2026-05-08 | Accepted — Slice A implemented. |
| [254](ADR-254-external-tool-intelligence-plane-and-project-overlays.md) | External Tool Intelligence Plane and Project Overlays | accepted | partial | 2026-05-08 | status: accepted |
| [258](ADR-258-portable-ai-overlay-for-agentic-primitives.md) | Portable `.ai` Overlay for Agentic Primitives | accepted | partial | 2026-05-09 | Accepted — generated overlay implemented; canonical migration intentionally deferred |
| [259](ADR-259-external-pattern-adoption-posture.md) | holaOS Adoption Posture: Patterns-Only Library with Clean-Room Rewrite | accepted | partial | 2026-05-11 | **Date:** 2026-05-11 |
| [267](ADR-267-license-compliance-enforcement-architecture.md) | License-Compliance Enforcement Architecture | accepted | partial | 2026-05-11 | Accepted (2026-05-11) |
| [273](ADR-273-pending-truth-ledger-and-bilateral-verification.md) | Pending Truth Ledger and Bilateral Verification Loop | accepted | partial | 2026-05-12 | Accepted — Slices A + B implemented; Slice C designed and staged (deployment requires operator authorization via `COS_ALLOW_PROTECTED_CONFIG_WRITE=1` per `hooks |
| [274](ADR-274-operational-guide-required-for-capability-adrs.md) | Operational Guide Required for Maintainer-Tier Capability ADRs | accepted | partial | 2026-05-12 | Accepted — Slice A implemented (audit + Phase 1 enforcement). |
| [275](ADR-275-closure-and-projection-primitives.md) | Closure & Projection Primitives (Pending-Truth Read/Write Symmetry) | accepted | partial | 2026-05-12 | Accepted — Slice A implemented (projector + close primitive + tests). Hook |
| [278](ADR-278-subprocess-run-timeout-discipline.md) | subprocess.run Timeout Discipline | accepted | partial | 2026-05-12 | Accepted — audit + allowlist + test-default shipped 2026-05-12. Per-call |
| [289](ADR-289-three-layer-knowledge-architecture.md) | Three-Layer Knowledge Architecture: Raw Sources, Compiled Vault, Operational Engram | accepted | partial | 2026-05-13 | Accepted — 2026-05-13. |
| [291](ADR-291-agent-runtime-web-service.md) | Agent Runtime Web Service: HTTP + SSE Surface for Harness-Independent Clients | accepted | partial | 2026-05-13 | **Date:** 2026-05-13 |
| [319](ADR-319-detractor-review-modes.md) | Detractor Review Modes for Planning and Verification | accepted | partial | 2026-05-15 | Accepted. |
| [324](ADR-324-executable-acceptance-specification-eas.md) | Executable Acceptance Specification (EAS) Evidence Artifact | accepted | partial | 2026-05-15 | Accepted. |
| [325](ADR-325-ai-resource-economy-and-degradation.md) | AI Resource Economy, Budget Preflight, and Graceful Degradation | accepted | partial | 2026-05-15 | Accepted. Partial implementation starts with a manifest, audit, preflight CLI, and language-token-economy rule. Phase 3 now has an initial bounded hook path: `c |
| [328](ADR-328-governance-roi-friction-vs-catch.md) | Governance ROI Friction-vs-Catch Ratios | accepted | partial | 2026-05-20 | Accepted. Read-side dashboard, write-side catch logging, optional blocked-hook prompts, weighted severity normalization, and the executable phase-policy adapter |
| [330](ADR-330-typed-capability-ceiling-signals.md) | Typed capability-ceiling signals | accepted | partial | 2026-05-20 | Accepted — first slice implemented as read-only detection. |
| [331](ADR-331-graphify-portable-context-optimization-primitive.md) | Graphify Portable Context Optimization Primitive | accepted | partial | 2026-05-22 | Accepted with partial implementation. |
| [332](ADR-332-sia-inspired-self-improvement-benchmark-loop.md) | SIA-inspired self-improvement benchmark loop | accepted | partial | 2026-05-29 | Accepted — partially implemented on 2026-05-29. |
| [338](ADR-338-so-wide-impact-evaluation-plane.md) | SO-Wide Impact Evaluation Plane | accepted | partial | 2026-06-13 | Accepted. Implementation remains advisory until workflow capsules include replicated cross-harness measured usage receipts. |
| [339](ADR-339-efficiency-operating-model-primitives.md) | Cognitive OS Efficiency Operating Model Primitives | accepted | partial | 2026-06-15 | Accepted. Initial primitives are advisory and receipt-oriented; runtime enforcement requires separate lifecycle promotion. |
| [341](ADR-341-iroh-optional-transport-adapter.md) | Iroh Optional Transport Adapter | accepted | partial | 2026-06-18 | - Implementation status: partial |
| [342](ADR-342-existence-criterion-for-primitives.md) | Existence Criterion for Primitives | accepted | partial | 2026-08-15 | - Implementation status: partial (three of the four censuses exist; the first has no census yet) |

### Active / Partial / Blocked (2)

| ADR | Title | Decision Status | Implementation | Date | Summary |
|---|---|---|---|---|---|
| [044](ADR-044-context-payload-slimming.md) | Context Payload Slimming — Non-Rule Startup Payloads | accepted | partial-blocked | 2026-04-20 | **Authors**: Agent C (startup-optimization initiative, stream 3/4) |
| [343](ADR-343-codebase-memory-mcp-recommend-only-and-conditional-discovery-directive.md) | codebase-memory-mcp — Recommend-Only, and a Conditional Structural-Discovery Directive | accepted | partial-blocked | 2026-08-15 | - Implementation status: partial-blocked (detection script landed and demonstrated; the rule file is blocked by the protected-config write guard and ships as a  |

### Active / Deferred (1)

| ADR | Title | Decision Status | Implementation | Date | Summary |
|---|---|---|---|---|---|
| [173](ADR-173-surface-5-research-gate.md) | Surface 5 Research Gate — No Custom TUI/UI Adoption Without Source-Level Proof | accepted | deferred | 2026-05-06 | **Accepted** — 2026-05-06. |

### Active / Planned (1)

| ADR | Title | Decision Status | Implementation | Date | Summary |
|---|---|---|---|---|---|
| [137](ADR-137-operational-trajectory-governance-layer-to-embedded-runtime.md) | Operational Trajectory — From Governance Layer Over Agents to Embedded Runtime | accepted | planned | 2026-05-03 | **Accepted** for the trajectory itself. The directional commitment (B → A, defined below) is firm. |

### Active / Not Applicable (140)

| ADR | Title | Decision Status | Implementation | Date | Summary |
|---|---|---|---|---|---|
| [007](ADR-007-cognitive-os-rebrand.md) | Rebrand from Agent OS to Cognitive OS | accepted | not-applicable | 2026-03-24 | **Date:** 2026-03-24 |
| [017](ADR-017-stabilization-freeze.md) | Stabilization Freeze -- No New Features Until Wiring Complete | accepted | not-applicable | 2026-04-11 | **Date:** 2026-04-11 |
| [026](ADR-026-r2-r3-design-review.synthesis.md) | r2-r3-design-review.synthesis | accepted | not-applicable |  | R2 (`cognitive-os.yaml` readers, 3 characterized sites with 5 locked behavioral divergences): adopt Option B — a single `lib/config_loader.py` exposing three va |
| [026a](ADR-026a-decisions.synthesis.md) | decisions.synthesis | accepted | not-applicable |  | Answers all 7 open questions from ADR-026 with evidence and explicit confidence levels: D2.1 YES adopt Option B (multi-variant `lib/config_loader.py`) — HIGH co |
| [027](ADR-027.synthesis.md) | ADR-027.synthesis | accepted | not-applicable |  | Three decisions to slim the SO: (D1) agents verify TARGETED (only files they touched) while the orchestrator verifies GLOBAL (full suite) once at Stop; (D2) red |
| [027a](ADR-027a.synthesis.md) | ADR-027a.synthesis | accepted | not-applicable |  | Correct ADR-027's baseline and scope in place rather than re-doing already-completed work. Remove from D2: the `scripts/compact-claude-md.py` migration script ( |
| [028](ADR-028.synthesis.md) | ADR-028.synthesis | accepted | not-applicable |  | Establish a 6-pillar SO Reliability & Observability Framework: (D1) runtime observability (metrics census, process registry + reaper, sub-agent heartbeat, unifi |
| [028a](ADR-028a.synthesis.md) | ADR-028a.synthesis | accepted | not-applicable |  | Four reconciliations to ADR-028 before its execution phases launch: (1) WS11 replacement — `hooks/global-verify.sh` (ADR-027 Phase 1) becomes the anti-confirmat |
| [028b](ADR-028b.synthesis.md) | ADR-028b.synthesis | accepted | not-applicable |  | Do not recreate the reverted artifacts (`lib/agent_heartbeat.py`, `hooks/_lib/heartbeat.sh`, `.cognitive-os/tasks/{agent_id}.heartbeat`). Instead, build a thin  |
| [029b](ADR-029b.synthesis.md) | ADR-029b.synthesis | accepted | not-applicable |  | Ship Jaccard token-bag similarity (docstring + function-name tokens) as Phase B-alpha: stdlib-only, <300ms, advisory-only (never blocks), scored 0.3 threshold b |
| [030](ADR-030.synthesis.md) | ADR-030.synthesis | accepted | not-applicable |  | Wire two opt-in, advisory-only auto-trigger mechanisms, neither of which replaces manual invocation. Q1: a `UserPromptSubmit` hook (`hooks/session-wrapup-trigge |
| [033](ADR-033.synthesis.md) | ADR-033.synthesis | accepted | not-applicable |  | Introduce a `HarnessAdapter` abstraction under `lib/harness_adapter/`: an ABC with `detect_harness`/`parse_event`/`emit_canonical`, a canonical event schema (`A |
| [035](ADR-035.synthesis.md) | ADR-035.synthesis | accepted | not-applicable |  | A 3-layer defense-in-depth. Layer 1 (this ADR, implemented): `hooks/session-start-worktree-nudge.sh` fires on SessionStart, detects a non-main worktree by check |
| [036](ADR-036.synthesis.md) | ADR-036.synthesis | implemented | not-applicable |  | Introduce `cos sprint` as a first-class, harness-agnostic concept with four primitives: a declarative Sprint YAML spec, a durable JSON manifest (`.cognitive-os/ |
| [041](ADR-041.synthesis.md) | ADR-041.synthesis | accepted | not-applicable |  | Drive the dormant+aspirational ratio below 40% via a structured exercise pipeline: classify all agentic primitives into 4 risk tiers (A-Safety-Critical, B-Infra |
| [044](ADR-044.synthesis.md) | ADR-044.synthesis | accepted | not-applicable |  | Adopt a tiered (T1/T2/T3) context loading model for everything non-rule (a paired Agent B ADR, ADR-043, covers rule payload separately). T1 (always loaded): ide |
| [048](ADR-048.synthesis.md) | ADR-048.synthesis | accepted | not-applicable |  | A 4-layer defense: (1) `scripts/cos-config-audit.sh` gains a `meta.docker_container_freshness` contract comparing the compose file's `@sha256:` pin against each |
| [049](ADR-049-llm-gateway-selection-and-overflow-providers.synthesis.md) | providers.synthesis | accepted | not-applicable |  | Remove LiteLLM entirely and do not adopt Bifrost as a proxy; implement direct-SDK dispatch in `lib/model_router.py` instead. Build a multi-provider overflow cas |
| [051](ADR-051.synthesis.md) | ADR-051.synthesis | accepted | not-applicable |  | Build `lib/qwen_agent_loop.py`, a Qwen agent loop mirroring Claude Code's `Agent()` tool iteration using OpenAI-style function-calling (Qwen's native tool-call  |
| [056](ADR-056.synthesis.md) | ADR-056.synthesis | accepted | not-applicable |  | Ship a three-tier progressive adaptive-dispatch system, independently togglable, with only L1 shipping now. L1 (Quota Pressure Advisory, advisory-only, always o |
| [058](ADR-058.synthesis.md) | ADR-058.synthesis | accepted | not-applicable |  | Deprecate Langfuse (frozen trace sink, containers stopped but volumes preserved) and adopt Arize Phoenix (`pip install arize-phoenix`, no Docker/ClickHouse) as  |
| [064](ADR-064.synthesis.md) | ADR-064.synthesis | accepted | not-applicable |  | Define four harness integration surfaces the OS must abstract, with Claude Code staying the on-by-default reference harness and other harnesses opt-in via adapt |
| [068](ADR-068.synthesis.md) | ADR-068.synthesis | accepted | not-applicable |  | Ship a self-contained heuristic (`scripts/detect_runner_capacity.py`) evaluated top-to-bottom, first-match-wins: cores ≤2 -> serial (`0`); load >70% -> `2` work |
| [071](ADR-071-engram-lifecycle-evolution.synthesis.md) | evolution.synthesis | accepted | not-applicable |  | Extend engram's behavior via a Python wrapper layer (`lib/engram_lifecycle.py`) rather than forking or migrating the backend: lifecycle metadata (confidence, la |
| [072](ADR-072.synthesis.md) | ADR-072.synthesis | accepted | not-applicable |  | Codify eight canonical test lanes (unit, audit, contract, integration-isolated, integration-shared, behavior, hooks, e2e, chaos — note the ADR body table lists  |
| [073](ADR-073.synthesis.md) | ADR-073.synthesis | accepted | not-applicable |  | Adopt a role registry where every test-related primitive gets exactly one primary role: Selection (`.cognitive-os/test-lanes.yaml`, `tests/conftest.py`, `cmd/co |
| [077](ADR-077.synthesis.md) | ADR-077.synthesis | accepted | not-applicable |  | Implement a local peer-card model as an Engram observation (type `peer-card`, scope `personal`, topic_key `user/peer-card`, upserted on update) holding structur |
| [080](ADR-080-hermes-cross-harness-adoption.synthesis.md) | adoption.synthesis | accepted | not-applicable |  | Umbrella ADR grouping remaining MIT-licensed Hermes plugin pieces into four tiers by cross-harness necessity: Tier 1 (critical parity — multi-provider adapters, |
| [081](ADR-081.synthesis.md) | ADR-081.synthesis | accepted | not-applicable |  | Implement `lib/harness_adapter/codex.py` satisfying the same `HarnessAdapter` ABC as `claude_code.py`: parses Codex hook stdin, maps native events to canonical  |
| [082](ADR-082.synthesis.md) | ADR-082.synthesis | accepted | not-applicable |  | Adopt Option A: a single root `.cognitive-os/plans/` with typed subdirectories — `features/` (SDD change plans), `research/` (pre-decision research/audits), `ar |
| [087](ADR-087.synthesis.md) | ADR-087.synthesis | accepted | not-applicable |  | Consolidate all project-level ADRs into a single canonical root, `docs/02-Decisions/adrs/`, using `ADR-NNN-kebab-slug.md` naming (Option A, rejecting Option B's |
| [089](ADR-089-multi-session-git-coordination.synthesis.md) | coordination.synthesis | accepted | not-applicable |  | Three coordination layers shipped in value-to-risk order. Layer 1 (high value, low risk): mandate `git commit --only -- <path>` (or explicit `-a` with stated in |
| [091](ADR-091.synthesis.md) | ADR-091.synthesis | accepted | not-applicable |  | Accept a two-mode runtime taxonomy — (1) local harness runtime (current mode) and (2) headless runtime (future mode accepting tasks from queues/CI/tickets witho |
| [093](ADR-093.synthesis.md) | ADR-093.synthesis | accepted | not-applicable |  | Collapse the three-tier installer (`--lean`/`--standard`/`--full`, plus an internal `--minimal` alias and an auto-detection heuristic `has_git && src_count >= 5 |
| [094](ADR-094.synthesis.md) | ADR-094.synthesis | accepted | not-applicable |  | Three layered defenses, registered in both `default` and `full` profiles as safety-critical: Mechanism A, `hooks/pre-agent-snapshot.sh` (PreToolUse:Agent) runs  |
| [095](ADR-095.synthesis.md) | ADR-095.synthesis | accepted | not-applicable |  | Detect recurring tool-call sequences (Bash, Edit, Read, Write, Agent, etc.) across sessions via a new `tool-sequences.jsonl` instrumentation stream and pure Pyt |
| [096](ADR-096.synthesis.md) | ADR-096.synthesis | accepted | not-applicable |  | Add a Hermes-inspired review-agent pattern: after a sub-agent completes, a second agent (reviewer) is triggered post-hoc/async on a 20% sample rate by default,  |
| [098](ADR-098.synthesis.md) | ADR-098.synthesis | accepted | not-applicable |  | Add a file-level edit-coordination layer built on the same atomic-mkdir primitive as ADR-089's git-coop, with a deliberately rich (~15-field) YAML lock schema s |
| [102](ADR-102.synthesis.md) | ADR-102.synthesis | accepted | not-applicable |  | Four coordinated fixes to the task tracker lifecycle. Fix 1: defer `in_progress` until the agent process actually starts — `hooks/agent-prelaunch.sh` and `hooks |
| [103](ADR-103-audit-contract-lane-recovery.md) | Audit and contract lane recovery before parallel flip | accepted | not-applicable | 2026-05-12 | Accepted. |
| [105](ADR-105.synthesis.md) | ADR-105.synthesis | implemented | not-applicable |  | Define a bilateral claim verification contract: high-stakes claim verbs (`archived`, `deleted`, `removed`, `wired`, `integrated`, `registered`, `done`, `closed` |
| [106](ADR-106.synthesis.md) | ADR-106.synthesis | accepted | not-applicable |  | Four independently-deployable primitives. (1) Stash Leak Alarm: at SessionStart and before every agent dispatch, scan for `auto-pre-agent-*` stashes; WARN via ` |
| [108](ADR-108.synthesis.md) | ADR-108.synthesis | accepted | not-applicable |  | Establish a named "Concurrent Agent Safety Layer" as an umbrella contract composing existing/adjacent primitives rather than replacing them: ADR-089 (git-index  |
| [113](ADR-113.synthesis.md) | ADR-113.synthesis | accepted | not-applicable |  | Extend the validation capsule lock (`hooks/_lib/validation-lock.sh`, `scripts/cos-validation-capsule.sh`) with 5 liveness primitives: P1 heartbeat (writer updat |
| [116](ADR-116.synthesis.md) | ADR-116.synthesis | accepted | not-applicable |  | Twelve coordination primitives organized into six layers (L1 Detection through L6 Shared evidence): task-claim ledger, work-identity fingerprinting, inter-sessi |
| [122](ADR-122-preflight-gate-refinements.md) | Preflight Gate Refinements | accepted | not-applicable | 2026-05-02 | **Author**: Maintainer (operator) |
| [130](ADR-130.synthesis.md) | ADR-130.synthesis | accepted | not-applicable |  | Suspend all eleven GitHub Actions workflow YAML files by renaming them to `.disabled` (a filesystem rename, not `gh workflow disable`), preserving their content |
| [131](ADR-131.synthesis.md) | ADR-131.synthesis | accepted | not-applicable |  | Replace GitHub Actions with a three-layer local architecture. Layer 1 (pre-push hook): `git-hooks/pre-push` invokes `scripts/cos-ci-local.sh`, consolidating the |
| [133](ADR-133-expansion-without-monsterization.md) | Expansion Without Monsterization | accepted | not-applicable | 2026-05-03 | Accepted — 2026-05-03 |
| [137](ADR-137.synthesis.md) | ADR-137.synthesis | accepted | not-applicable |  | Commit Cognitive OS to a directional trajectory from "Framing B" (governance layer wrapped around an existing harness/agent) to "Framing A" (COS as a runtime th |
| [138](ADR-138.synthesis.md) | ADR-138.synthesis | accepted | not-applicable |  | Commit `manifests/flow-contract-schema.yaml`, a required shape every flow primitive registered after this ADR must satisfy (partial conformance rejected at regi |
| [139](ADR-139.synthesis.md) | ADR-139.synthesis | implemented | not-applicable |  | Every COS runtime surface (local maintainer session, cloud worker, ephemeral sandbox) must use credentials supplied by that surface's own caller — never forward |
| [140](ADR-140.synthesis.md) | ADR-140.synthesis | accepted | not-applicable |  | Cloud workers needing COS as an embedded runtime MUST be launchable via a Docker Compose stack (`docker/cos-worker/docker-compose.yml`) containing a `cos-worker |
| [141](ADR-141.synthesis.md) | ADR-141.synthesis | implemented | not-applicable |  | Wire the upstream `engram cloud` feature into COS without replacing any existing path — this is explicitly not an adoption decision for Engram itself (already i |
| [142](ADR-142.synthesis.md) | ADR-142.synthesis | implemented | not-applicable |  | `.cognitive-os/runtime/agent-audit-trail.jsonl` becomes the single canonical, append-only compliance evidence surface that other per-domain JSONLs (`blast-radiu |
| [143](ADR-143.synthesis.md) | ADR-143.synthesis | accepted | not-applicable |  | Add `scripts/cos-closure-discipline-audit` as a blocking maintainer primitive wired into `scripts/cos-ci-local.sh quick`. It is intentionally narrow, checking e |
| [144](ADR-144.synthesis.md) | ADR-144.synthesis | accepted | not-applicable |  | A rule may only be listed in `EXCLUDED_RULES` with a `# → hook.sh` enforcement claim if: (1) the referenced hook file exists; (2) it is registered in `cognitive |
| [146](ADR-146.synthesis.md) | ADR-146.synthesis | accepted | not-applicable |  | Add a primitive readiness ledger for scripts (`python3 scripts/primitive_readiness_ledger.py --project-dir .`), generating `docs/06-Daily/reports/primitive-read |
| [149](ADR-149.synthesis.md) | ADR-149.synthesis | accepted | not-applicable |  | Add `scripts/primitive_duplication_audit.py` as the first unified, dependency-free duplication audit across agentic-primitive and configuration surfaces, writin |
| [159](ADR-159.synthesis.md) | ADR-159.synthesis | accepted | not-applicable |  | Promote six harnesses to implemented structural projection: `gemini-cli`, `warp`, `amp-code`, `jetbrains-junie`, `qoder`, `factory-droid`. Each gets specific ge |
| [161](ADR-161.synthesis.md) | ADR-161.synthesis | implemented | not-applicable |  | Separate remote ingress from provider/executor adapters as a hard architectural boundary. Remote ingress adapters (Telegram, REST, allowlist-based) may receive  |
| [162](ADR-162.synthesis.md) | ADR-162.synthesis | implemented | not-applicable |  | Adopt `manifests/task-lifecycle-schema.yaml` as the contract for COS task execution outside a single IDE session. It defines: task statuses from `queued` throug |
| [166](ADR-166.synthesis.md) | ADR-166.synthesis | implemented | not-applicable |  | Introduce an expected-skip registry (`manifests/test-skip-registry.yaml`) enforced from the pytest summary wrapper used by `cos-test`. Each expected-skip entry  |
| [167](ADR-167.synthesis.md) | ADR-167.synthesis | implemented | not-applicable |  | Add `scripts/proof-drill-select` as the selector/doctor primitive for the proof-drill registry, selecting by id, scope, class, projection profile, and text toke |
| [168](ADR-168.synthesis.md) | ADR-168.synthesis | implemented | not-applicable |  | Evolve `manifests/dependencies.yaml` into the single source of truth for cross-device dependency installation. Each entry must declare: name, category (runtime/ |
| [172](ADR-172-multi-surface-ui-architecture.md) | Multi-Surface UI Architecture - CLI + Phoenix + Engram Cloud + Obsidian | accepted | not-applicable | 2026-05-05 | Accepted. Supersedes [ADR-170](ADR-170-operator-cli-as-primary-ui-surface.md). |
| [172](ADR-172.synthesis.md) | ADR-172.synthesis | accepted | not-applicable |  | The UI is four cooperating, independently opt-in surfaces, none mandatory: **Surface 1 — Operator CLI** (always-on; live operator state via scripts like `cos-bo |
| [174](ADR-174.synthesis.md) | ADR-174.synthesis | accepted | not-applicable |  | Add a `routing_patterns:` field to the SKILL.md frontmatter schema (list of `{pattern (regex, IGNORECASE), confidence (0.0-1.0)}`, English or Spanish). A new `_ |
| [174b](ADR-174b.synthesis.md) | ADR-174b.synthesis | accepted | not-applicable |  | Part A: when `auto-skill-generator.sh` fires, it now calls `lib/routing_pattern_deriver.py` to derive 2–3 routing patterns (skill-name match, hyphen-collapsed v |
| [175](ADR-175.synthesis.md) | ADR-175.synthesis | accepted | not-applicable |  | Add a lightweight, non-blocking research-quality scorer running as a PostToolUse Edit/Write hook (`hooks/research-quality-validator.sh`) on `**/docs/06-Daily/re |
| [176](ADR-176.synthesis.md) | ADR-176.synthesis | accepted | not-applicable |  | Adopt OpenSpace's 6-table SQLite schema verbatim into `lib/skill_store.py` (COS-namespace column adjustments only: `creator_id`→session IDs not user IDs, `analy |
| [178](ADR-178.synthesis.md) | ADR-178.synthesis | accepted | not-applicable |  | Cherry-pick exactly 3 primitives from OpenHarness (commit `7873f0d109174a57b3b1af7aa5397a6b3b0bd551`, fields read verbatim via `gh api`) — explicitly NOT a subs |
| [180](ADR-180.synthesis.md) | ADR-180.synthesis | accepted | not-applicable |  | Operationally activate the skill lifecycle promotion ladder (doctrinally declared in ADR-177) with five concrete artifacts: `scripts/cos-promotion-proposer` (ev |
| [181](ADR-181.synthesis.md) | ADR-181.synthesis | accepted | not-applicable |  | A lightweight `AdrRouter` (`lib/adr_router.py`) indexes all non-tombstone/non-superseded/non-deprecated ADRs lazily, scoring keywords from three weighted tiers: |
| [182](ADR-182.synthesis.md) | ADR-182.synthesis | accepted | not-applicable |  | Introduce a branch ownership lock primitive. A session intending to mutate a branch acquires a lease recorded at `.cognitive-os/runtime/branch-locks/<branch-slu |
| [183](ADR-183.synthesis.md) | ADR-183.synthesis | accepted | not-applicable |  | Extend the existing minimal `lib/session_bus.py` append-only bus with a fixed event schema and two hooks. Event log: `.cognitive-os/sessions/events.jsonl`, appe |
| [184](ADR-184.synthesis.md) | ADR-184.synthesis | accepted | not-applicable |  | Introduce `cosd` — an opt-in, per-machine, long-running daemon that is the sole authoritative writer for critical surfaces: ADR sequence/ownership (number reser |
| [185](ADR-185.synthesis.md) | ADR-185.synthesis | accepted | not-applicable |  | Adopt a typed, severity-graded, append-only directed message queue (`lib/agent_message_bus.py`, implemented as `agent_message_bus` because it also carries imple |
| [186](ADR-186.synthesis.md) | ADR-186.synthesis | accepted | not-applicable |  | Activate ADR-038 Wave 3 enforcement via `lib/context_budget.py` (pure stdlib, `len(text)//4` heuristic token counting with optional `tiktoken` via `COS_USE_REAL |
| [188](ADR-188.synthesis.md) | ADR-188.synthesis | accepted | not-applicable |  | When the skill router emits a match at `confidence >= 0.90` for the current user prompt, the orchestrator must do one of three things: invoke the suggested skil |
| [190](ADR-190.synthesis.md) | ADR-190.synthesis | accepted | not-applicable |  | Model this as "harness action receipts" — a vendor-neutral event vocabulary (schema `harness-action-receipt.v1`) describing an action's source, repository conte |
| [201](ADR-201.synthesis.md) | ADR-201.synthesis | accepted | not-applicable |  | Introduce a Maintainer Agent as a bounded, scheduled, propose-only runtime role that owns the loop: observe telemetry -> detect drift -> propose change -> valid |
| [202](ADR-202.synthesis.md) | ADR-202.synthesis | accepted | not-applicable |  | Define a private-content portability boundary orthogonal to public harness portability. Every private-content surface must declare one of 6 portability classes: |
| [215](ADR-215.synthesis.md) | ADR-215.synthesis | accepted | not-applicable |  | Adopt a manifest-backed cross-stack secret audit policy: primary toolchain is `gitleaks` + `trufflehog` (both run by default, either finding a real secret fails |
| [217](ADR-217.synthesis.md) | ADR-217.synthesis | accepted | not-applicable |  | Adopt a manifest-backed cross-stack adoption-truth audit mirroring ADR-212's shape: canonical CLI `cos adoption audit [--json] [--strict]`, manifest `manifests/ |
| [218](ADR-218.synthesis.md) | ADR-218.synthesis | accepted | not-applicable |  | Adopt a manifest-backed history-sanitization primitive: canonical CLI `cos history sanitize [--dry-run\|--execute] [--json]`, default mode `--dry-run` (in-memory |
| [220](ADR-220.synthesis.md) | ADR-220.synthesis | accepted | not-applicable |  | Adopt a manifest-backed worktree-divergence audit primitive: `cos worktree audit [--json] [--strict] [--against <ref>]`, defaulting to comparing against `origin |
| [221](ADR-221.synthesis.md) | ADR-221.synthesis | accepted | not-applicable |  | All persistence of stash identity in Cognitive OS MUST use the immutable 40-char stash commit SHA (resolved via `git rev-parse stash@{0}` at the moment of push  |
| [222](ADR-222.synthesis.md) | ADR-222.synthesis | implemented | not-applicable |  | Replace speculative-capture-on-PreToolUse with a two-phase capture-then-commit pattern. Phase 1 (Plan, PreToolUse, after all blocking preflight passes): `pre-ag |
| [226](ADR-226-event-sourced-session-bus.synthesis.md) | bus.synthesis | accepted | not-applicable |  | Extend the ADR-205 Flight Recorder substrate with three additive, opt-in primitives on top of the existing `session_bus.append_event()` API: (1) monotonic per-s |
| [227](ADR-227.synthesis.md) | ADR-227.synthesis | accepted | not-applicable |  | Ship `lib/shadow_git.py` as the canonical checkpoint substrate: one bare git repo per session at `~/.cognitive-os/snapshots/{project_id}/{session_id}/.git`, out |
| [228](ADR-228.synthesis.md) | ADR-228.synthesis | implemented | not-applicable |  | Ship `lib/dispatch_gate.py` as a unified pre-call gate consolidating both fixes into one chokepoint (both live in `dispatch()`, both need a sync gate, both need |
| [230](ADR-230.synthesis.md) | ADR-230.synthesis | implemented | not-applicable |  | Ship `lib/handoff_envelope.py` + `lib/handoff_dispatcher.py` as the canonical handoff protocol, with three primitives: (1) a frozen `HandoffEnvelope` dataclass  |
| [239](ADR-239.synthesis.md) | ADR-239.synthesis | accepted | not-applicable |  | Change the default `cognitive-os.yaml` setting from `sub_agent_cwd: main_worktree` to `sub_agent_cwd: isolated_worktree`. Write-capable agents now get a dedicat |
| [240](ADR-240.synthesis.md) | ADR-240.synthesis | accepted | not-applicable |  | Adopt a machine-readable primitive coherence manifest (`manifests/primitive-coherence.yaml`) declaring surfaces, owners, writers, write-protocols, and ordering  |
| [241](ADR-241.synthesis.md) | ADR-241.synthesis | accepted | not-applicable |  | Replace seven separately-named bypass env vars (`COS_ALLOW_DESTRUCTIVE_GIT`, `COS_BYPASS_COMMIT_GUARD`, `COS_ALLOW_MAIN_BRANCH_WRITE`, `COS_ALLOW_UNPROVEN_SCOPE |
| [242](ADR-242.synthesis.md) | ADR-242.synthesis | accepted | not-applicable |  | Ship `scripts/cos-filter-repo-wrap.sh` as the sole call site for `git filter-repo --execute` within the governed toolchain; `lib/history_sanitization.py:execute |
| [243](ADR-243.synthesis.md) | ADR-243.synthesis | accepted | not-applicable |  | Introduce a "post-rewrite mode": `lib/history_sanitization.py` (and the ADR-242 wrapper) writes `.cognitive-os/runtime/last-rewrite.json` (`pre_head`, `post_hea |
| [244](ADR-244.synthesis.md) | ADR-244.synthesis | accepted | not-applicable |  | Promote the claim-validator from advisory to blocking for high-stakes claims. Renamed `claim-enforcer` (`hooks/claim-validator.sh` retained as a one-release bac |
| [245](ADR-245.synthesis.md) | ADR-245.synthesis | accepted | not-applicable |  | Enforce `lib/`, `scripts/`, and `hooks/` as read-only for the duration of every chaos test via an autouse pytest fixture, `chaos_readonly_workspace`, in `tests/ |
| [246](ADR-246.synthesis.md) | ADR-246.synthesis | accepted | not-applicable |  | Introduce `cos release freeze` as a transaction primitive for high-risk public/destructive operations. It creates a `release_transaction_id` and writes an immut |
| [247](ADR-247.synthesis.md) | ADR-247.synthesis | accepted | not-applicable |  | Postmortem regression audits must be manifest-driven: `manifests/postmortem-regression-audit.yaml` declares checks (`forbidden_pattern`, `required_paths` types) |
| [248](ADR-248.synthesis.md) | ADR-248.synthesis | implemented | not-applicable |  | Introduce a manifest-driven control-plane audit runner (`manifests/control-plane-audits.yaml` + `scripts/cos-control-plane-audit`) that executes declared read-o |
| [249](ADR-249.synthesis.md) | ADR-249.synthesis | accepted | not-applicable |  | A critical governance primitive is not behaviorally proven until it has a declared behavioral proof contract with at least one falsification probe, tracked in ` |
| [250](ADR-250.synthesis.md) | ADR-250.synthesis | accepted | not-applicable |  | Split the skill router into an explicit pipeline: skill catalog → candidate retriever adapter → COS policy/intent guard → telemetry/feedback ledger → suggest/bl |
| [251](ADR-251.synthesis.md) | ADR-251.synthesis | accepted | not-applicable |  | Define an explicit boundary: COS owns policy/safety gates, work ownership/liveness/branch-worktree boundaries, release-freeze preconditions, evidence receipts a |
| [252](ADR-252.synthesis.md) | ADR-252.synthesis | accepted | not-applicable |  | Introduce a manifest-backed Capability Coverage Matrix and Feature Reality Ledger: `manifests/capability-coverage.yaml` (declares every capability's stable id,  |
| [256](ADR-256.synthesis.md) | ADR-256.synthesis | accepted | not-applicable |  | Introduce a Primitive Contract Registry (`manifests/primitive-contracts.yaml`) and a Runtime Evidence Ledger. A primitive is not fully governed until it has: a  |
| [258](ADR-258.synthesis.md) | ADR-258.synthesis | accepted | not-applicable |  | Adopt `.ai/` as a **generated portable overlay/export surface**, not as the internal canonical source of truth. Canonical sources remain `manifests/primitive-co |
| [259](ADR-259.synthesis.md) | ADR-259.synthesis | accepted | not-applicable |  | Treat holaOS as a **patterns-only reference library**: ideas, algorithms, policies, state machines, and taxonomies are freely adoptable (17 USC §102(b)); source |
| [260](ADR-260-grant-signed-cosd-api.synthesis.md) | api.synthesis | accepted | not-applicable |  | Replace the static bearer token with a self-contained HMAC-signed capability grant: `lib/cosd_grant.py` provides `issue_token(scope, ttl_seconds)` and `verify_t |
| [261](ADR-261-memory-governance-v2.synthesis.md) | v2.synthesis | accepted | not-applicable |  | New stdlib-only module `lib/memory_governance.py` defines a static per-type policy table (`MemoryTypePolicy`: verification tier, staleness tier, stale-after thr |
| [263](ADR-263-tool-replay-budget-ledger.synthesis.md) | ledger.synthesis | accepted | not-applicable |  | New module `lib/tool_replay_ledger.py` with a per-session SQLite-backed ledger tracking `(tool_name, target_hash)` tuples through three modes: FRESH (first occu |
| [264](ADR-264.synthesis.md) | ADR-264.synthesis | accepted | not-applicable |  | New dependency-free module `lib/tool_result_envelope.py` exposing `wrap_if_large(raw_result, tool_name, target_hint, threshold=28*1024, preview_size=7*1024, per |
| [267](ADR-267.synthesis.md) | ADR-267.synthesis | accepted | not-applicable |  | A layered defense: six new pre-commit hooks, two new governance manifests/scripts, and this ADR plus a deferred future "legal review gate" ADR — while explicitl |
| [268](ADR-268.synthesis.md) | ADR-268.synthesis | accepted | not-applicable |  | Two `git filter-repo` passes plus an Engram SQL maintenance pass, scoped strictly to surface text and never touching ADRs, recovery bundles, or audit artifacts: |
| [269](ADR-269.synthesis.md) | ADR-269.synthesis | accepted | not-applicable |  | A four-primitive enforcement layer operating at three time points (pre-execute gate, post-rewrite ledger entry, periodic audit). Primitive 1: `manifests/history |
| [270](ADR-270.synthesis.md) | ADR-270.synthesis | accepted | not-applicable |  | Introduce eight primitives that mechanize the evidence-gathering and bookkeeping parts of legal compliance while leaving all counsel judgment manual: `cos-uspto |
| [272](ADR-272-structural-rule-backend-boundary.md) | Structural Rule Backend Boundary | accepted | not-applicable | 2026-05-12 | Status: Accepted |
| [273](ADR-273.synthesis.md) | ADR-273.synthesis | accepted | not-applicable |  | Introduce one canonical pending-truth ledger with bilateral verification. A schema (`manifests/pending-truth.yaml`) gives every actionable item a stable composi |
| [274](ADR-274.synthesis.md) | ADR-274.synthesis | accepted | not-applicable |  | Establish a contract requiring a §Operational Guide section in maintainer-tier ADRs that introduce a new capability (new script/manifest/hook/schema/public surf |
| [275](ADR-275.synthesis.md) | ADR-275.synthesis | accepted | not-applicable |  | Ship two Slice-A primitives with a shared schema and trust contract: (1) `scripts/cos-session-start-projector`, which reads pending-truth, operational-guide-aud |
| [278](ADR-278.synthesis.md) | ADR-278.synthesis | accepted | not-applicable |  | Three-layer enforcement mirroring the ADR-274 audit pattern. (1) Convention: every `subprocess.run(...)` in scripts/, hooks/, lib/, tests/, or packages/ MUST in |
| [281](ADR-281.synthesis.md) | ADR-281.synthesis | accepted | not-applicable |  | Add a permanent audit (`scripts/cos-adr-implementation-audit.py`) that cross-validates every ADR declaring `implementation_status: implemented` against on-disk  |
| [283](ADR-283.synthesis.md) | ADR-283.synthesis | accepted | not-applicable |  | Add `scripts/cos-script-exposure-audit` (with `--json` and `--fail-p0` modes), reading `docs/06-Daily/reports/primitive-readiness-ledger-scripts-latest.json` by |
| [287](ADR-287.synthesis.md) | ADR-287.synthesis | accepted | not-applicable |  | Ship four orthogonal, additive Engram v3 capabilities, each independently adoptable without breaking the v2 surface: (1) evidence-grounded claims — new `evidenc |
| [288](ADR-288.synthesis.md) | ADR-288.synthesis | accepted | not-applicable |  | Adopt `browser-use>=0.12.6` (MIT, 93.7k stars) as an optional runtime dependency under a new `web-automation` extra in `pyproject.toml` (not in default install) |
| [289](ADR-289.synthesis.md) | ADR-289.synthesis | accepted | not-applicable |  | Adopt a three-layer knowledge architecture as the canonical model: Layer 1 (raw sources) — immutable original inputs, SHA-256 identified, canonical location pro |
| [291](ADR-291.synthesis.md) | ADR-291.synthesis | accepted | not-applicable |  | Build `packages/agent-service/` as a standalone FastAPI + Uvicorn HTTP service exposing the agent runtime: plain HTTP REST for request/response, Server-Sent Eve |
| [296](ADR-296.synthesis.md) | ADR-296.synthesis | accepted | not-applicable |  | Replace the Jaccard semantic fallback in the skill router with a multilingual embedding matcher backed by FastEmbed (MIT) using `sentence-transformers/paraphras |
| [299](ADR-299.synthesis.md) | ADR-299.synthesis | accepted | not-applicable |  | Build an offline enricher (`lib/skill_description_enricher.py`, CLI `scripts/cos-skill-description-enrich`) that, per skill, generates ~2 short natural-language |
| [300](ADR-300.synthesis.md) | ADR-300.synthesis | accepted | not-applicable |  | Phase 1 (accepted): document the benchmark winner (`multilingual-e5-large`, MIT-adjacent per its own license, precision@1 0.897 vs MiniLM's 0.753) and expose a  |
| [304](ADR-304.synthesis.md) | ADR-304.synthesis | accepted | not-applicable |  | A periodic telemetry aggregator with three independently-testable slices. Slice 1: `lib/telemetry_aggregator.py` reads SLO declarations from `manifests/observab |
| [314](ADR-314.synthesis.md) | ADR-314.synthesis | accepted | not-applicable |  | Adopt an evidence-weighted Primitive Scope Taxonomy Calibration Loop with two parts: (1) `scripts/primitive_scope_classifier.py`, which emits row-level hypothes |
| [315](ADR-315.synthesis.md) | ADR-315.synthesis | accepted | not-applicable |  | Introduce a canonical primitive parser layer (`lib/primitive_parser.py`) that runs before scope classification. It produces a normalized, descriptive-only `Prim |
| [320](ADR-320.synthesis.md) | ADR-320.synthesis | accepted | not-applicable |  | Treat the installer as having two real installed surfaces until a future ADR gives `project` and `both` separate executable semantics: (1) consumer filtered ins |
| [321](ADR-321.synthesis.md) | ADR-321.synthesis | accepted | not-applicable |  | Classify every primitive along four orthogonal axes instead of scope alone: (1) **Scope** — `os-only`/`project`/`both` (install surface); (2) **Plane** — `contr |
| [325](ADR-325.synthesis.md) | ADR-325.synthesis | accepted | not-applicable |  | Introduce an explicit AI Resource Economy control plane in five phases, canonically declared in `manifests/ai-resource-economy.yaml`. (1) Taximeter ledger: ever |
| [328](ADR-328.synthesis.md) | ADR-328.synthesis | accepted | not-applicable |  | Add a first-class friction-vs-catch ratio to the governance ROI dashboard, exposed via `cos status` / `cos governance roi`. Three executable surfaces: (1) read- |
| [331](ADR-331.synthesis.md) | ADR-331.synthesis | accepted | not-applicable |  | Adopt Graphify as a maintainer-only context optimization backend for an owned COS context-graph primitive, in controlled phases, treating Graphify as replaceabl |

## Proposed

| ADR | Title | Decision Status | Implementation | Date | Summary |
|---|---|---|---|---|---|
| [001](ADR-001-abc-parallel-dedup-fix-broken-infra-add-global-verify.md) | A+B+C parallel — dedup, fix broken infra, add global-verify | proposed | planned | 2026-04-20 | Draft |
| [002](ADR-002-docker-pip-localhost-envs-targetedtestresolver-redis-dep.md) | docker-pip localhost envs + targeted_test_resolver + redis dep | proposed | planned | 2026-04-20 | Draft |
| [034](ADR-034-harness-agnostic-live-streaming.md) | Harness-Agnostic Live Agent Streaming | proposed | planned | 2026-04-20 | - **Status**: Proposed |
| [034](ADR-034.synthesis.md) | ADR-034.synthesis | proposed | not-applicable |  | Introduce three components to promote ADR-033's event schema from a write-only sink to a live, subscribable stream: (1) `scripts/cos_executor.py`, a PID-locked  |
| [036](ADR-036-sprint-orchestration-primitives.md) | Sprint orchestration primitives | proposed | partial | 2026-04-20 | Proposed — MVP implemented 2026-04-20 (CLI skeleton + manifest + canonical events + example spec). Wave 1 test aggregation shipped 2026-04-21. Dispatch wiring v |
| [039](ADR-039-reinvention-phase-b-beta.md) | Reinvention Phase B-beta (semantic embeddings) | proposed | planned | 2026-04-20 | > Originally drafted in `.cognitive-os/pending-tasks/adr-039-reinvention-phase-b-beta.md`; canonical location is `docs/02-Decisions/adrs/`. |
| [047](ADR-047-session-lifecycle-management.md) | Session Lifecycle Management | proposed | planned | 2026-04-20 | Proposed — 2026-04-20. Author: Agent E (software-architect). Coordinates with |
| [047](ADR-047.synthesis.md) | ADR-047.synthesis | proposed | not-applicable |  | Introduce a Session Lifecycle Management (SLM) subsystem: a psutil-based watchdog daemon (`scripts/so_session_watchdog.py`) enforcing TTL + idle heuristics + TT |
| [059](ADR-059-so-existential-validation.md) | SO Existential Validation: Prune, Install Timing, Core-vs-Extensions Split | proposed | planned | 2026-04-24 | **Proposed** — 2026-04-24. 3-phase plan with measurable exit criteria, |
| [059](ADR-059.synthesis.md) | ADR-059.synthesis | proposed | not-applicable |  | Adopt a 3-phase validation plan with hard exit criteria, explicitly designed to demote unproven claims rather than quietly preserve them. Phase 1 (Aggressive Pr |
| [062](ADR-062-multi-provider-agent-loop.md) | Multi-Provider Agent Loop | proposed | planned | 2026-04-24 | **Proposed** — 2026-04-24. Extends ADR-049 (provider cascade) and ADR-051 |
| [062](ADR-062.synthesis.md) | ADR-062.synthesis | proposed | not-applicable |  | Generalize `lib/qwen_agent_loop.py` (misnamed — it's a generic OpenAI-SDK-compatible loop, not Qwen-specific) into `lib/openai_compatible_agent_loop.py`, keepin |
| [065](ADR-065-radar-update-curation-pipeline.md) | Tech Radar Curation Pipeline (`/radar-update`) | proposed | planned | 2026-04-24 | **Proposed** — 2026-04-24. Builds on `/repo-scout` (formerly `/eval-repo`, |
| [065](ADR-065.synthesis.md) | ADR-065.synthesis | proposed | not-applicable |  | Create a new SO-only skill `/radar-update <url-or-file> [--apply]` that delegates per-repo evaluation entirely to the existing `/repo-scout` pipeline (no new De |
| [066](ADR-066-polyglot-language-boundaries.md) | Polyglot Language Boundaries & Migration Pressure | proposed | planned | 2026-04-24 | Proposed — 2026-04-24. |
| [066](ADR-066.synthesis.md) | ADR-066.synthesis | proposed | not-applicable |  | This is a design-only ADR (no code rewritten) that codifies an explicit role matrix for the three in-tree languages — bash for event handlers/hooks/thin glue (r |
| [067](ADR-067-frontmatter-defense-in-depth.md) | Defense-in-Depth for SKILL.md Frontmatter Quality | proposed | planned | 2026-04-24 | Proposed — 2026-04-24. Implementation tracked separately as Phase 1 of this ADR. |
| [067](ADR-067.synthesis.md) | ADR-067.synthesis | proposed | not-applicable |  | Ratify a mandatory three-layer, defense-in-depth policy for SKILL.md frontmatter quality — all three layers required, none optional: (A) a canonical skill templ |
| [069](ADR-069-research-first-protocol.md) | Research-First Protocol for High-Risk Changes | proposed | planned | 2026-04-24 | **Proposed** — 2026-04-24. Adopted alongside three concrete research tasks (H/I/J) |
| [069](ADR-069.synthesis.md) | ADR-069.synthesis | proposed | not-applicable |  | Route any task by four risk dimensions (acceptance-criteria clarity, blast radius, reversibility, decision count). If any dimension is "High," the task goes thr |
| [070](ADR-070-convention-enforcement-mechanism.md) | Convention Enforcement — From Documentation to Mechanism | proposed | planned | 2026-04-27 | **Proposed** — 2026-04-27. Direct outcome of the |
| [070](ADR-070.synthesis.md) | ADR-070.synthesis | proposed | not-applicable |  | Codify four enforcement patterns as the menu every new convention must pick from: (A) an audit test that walks artifacts read-only and asserts pattern complianc |
| [117](ADR-117-stash-mutation-reversibility.md) | Stash Mutation Must Be Reversible-by-Design | proposed | planned | 2026-05-02 | **Status:** Proposed |
| [117](ADR-117.synthesis.md) | ADR-117.synthesis | proposed | not-applicable |  | Every `git stash` operation executed by an OS hook (in `hooks/`, `packages/*/hooks/`, or any hook-invoked script) MUST satisfy five invariants simultaneously: ( |
| [124](ADR-124-cos-distribution-boundaries.md) | COS Distribution Boundaries — Core, Team, Maintainer, Lab | proposed | planned | 2026-05-02 | Proposed — 2026-05-02 |
| [125](ADR-125-governance-tools-value-boundary.md) | Governance Tools Value Boundary | proposed | planned | 2026-05-02 | Proposed — 2026-05-02 |
| [126](ADR-126-agentic-primitive-lifecycle-governor.md) | Agentic Primitive Lifecycle Governor | proposed | planned | 2026-05-02 | Proposed — 2026-05-02 |
| [126](ADR-126.synthesis.md) | ADR-126.synthesis | proposed | not-applicable |  | Introduce a governed lifecycle state machine for any primitive (hook, skill, rule, script, doctor) created/modified/promoted/demoted/archived/deleted by an agen |
| [128](ADR-128-data-layer-integrity-fixes.md) | Data Layer Integrity Fixes | proposed | planned | 2026-05-03 | Proposed — 2026-05-03 |
| [174c](ADR-174c-validator-blocking-promotion.md) | Validator Advisory-to-Blocking Promotion After Soak | proposed | deferred | 2026-05-12 | Proposed. This ADR is intentionally not accepted until soak data proves the |
| [265](ADR-265-mandatory-minimum-inspection-caps.md) | Mandatory-minimum inspection caps for COS eval surfaces | proposed | planned | 2026-05-11 | Proposed (2026-05-11) |
| [266](ADR-266-protected-config-write-guard-bash-coverage.md) | Extend protected-config-write-guard to intercept Bash file-write commands | proposed | planned | 2026-05-11 | Proposed (2026-05-11). |
| [271](ADR-271-clean-room-detection-tier-2-ast-similarity.md) | Clean-Room Detection Tier 2: AST-Normalized Similarity | proposed | planned | 2026-05-11 | Proposed (2026-05-11) |
| [271](ADR-271.synthesis.md) | ADR-271.synthesis | proposed | not-applicable |  | Build `hooks/clean-room-ast-similarity-gate.sh` plus `scripts/cos_clean_room_ast_similarity.py` as ADR-267 Hook #8 (Tier 2 of the clean-room detection matrix).  |

## Exploration

| ADR | Title | Decision Status | Implementation | Date | Summary |
|---|---|---|---|---|---|
| [132](ADR-132-solo-swarm-vs-multi-maintainer-fork.md) | Solo-Swarm vs Multi-Maintainer Fork — Documenting the Pending Strategic Decision | exploration | not-applicable | 2026-05-03 | **Exploration.** This ADR does not commit to an architectural change. |
| [132](ADR-132.synthesis.md) | ADR-132.synthesis | exploration | not-applicable |  | This ADR deliberately commits to nothing except naming the decision space. It documents two hypothetical shapes — Shape A (current solo-swarm: one maintainer, m |
| [262](ADR-262-evolve-loop-spike.md) | Evolve Loop Spike: Task Proposal Queue + LLM-driven Skill Candidates | exploration | not-applicable | 2026-05-11 | **Spike** (not Accepted — pending exit criteria evaluation) |
| [262](ADR-262.synthesis.md) | ADR-262.synthesis | exploration | not-applicable |  | Time-boxed 3-4 day Spike (not an Accepted ADR) to design and prototype an LLM-driven evolve loop: `lib/evolve_skill_review.py` (LLM extraction job via `cos_lib. |

## Resolved

| ADR | Title | Decision Status | Implementation | Date | Summary |
|---|---|---|---|---|---|
| [238](ADR-238-tier-1-4-followup-bug-tracking.md) | Tier 1-4 Follow-Up Bug Tracking | resolved | resolved | 2026-05-07 | During the Tier 1-4 case-study leak audit (privacy decoupling, commits |
| [238](ADR-238.synthesis.md) | ADR-238.synthesis | resolved | not-applicable |  | Track all 5 bugs found during the audit as a single consolidated ADR Bug Registry (severity, affected file, reproducer, proposed remediation, status per entry)  |

<details>
<summary>Superseded ADRs (7)</summary>

## Superseded

| ADR | Title | Decision Status | Implementation | Date | Summary |
|---|---|---|---|---|---|
| [011](ADR-011-dual-gateway-bifrost-litellm.md) | Dual Gateway -- Bifrost Primary, LiteLLM Fallback | superseded | not-applicable | 2026-03-28 | **Date:** 2026-03-28 |
| [084](ADR-084-headless-clustered-runtime-shape.md) | Headless and Clustered Runtime Shape | superseded | not-applicable | 2026-04-30 | **Author**: Maintainer |
| [170](ADR-170-operator-cli-as-primary-ui-surface.md) | Operator-CLI as Primary UI Surface — No Web Dashboard Until a Real Driver Exists | superseded | not-applicable | 2026-05-05 | Superseded by [ADR-172](ADR-172-multi-surface-ui-architecture.md) (2026-05-05). |
| [170](ADR-170.synthesis.md) | ADR-170.synthesis | superseded | not-applicable |  | The primary UI surface for Cognitive OS is the operator CLI plus the markdown report library, period — no web dashboard until a real driver exists. `scripts/cos |
| [187](ADR-187-surface-5-adoption-proof-contract.md) | Surface 5 Adoption Proof Contract — Source-Level Gate for Custom TUI/UI | superseded | not-applicable | 2026-05-06 | **Superseded by ADR-192** — the proof contract was satisfied by the accepted Bubble Tea adoption decision. Future Surface 5 adoption work extends ADR-192 rather |
| [290](ADR-290-five-agent-quality-patterns.md) | Five Agent Quality-of-Life Patterns: Lazy Imports, Typed Hook Events, MCP Sync↔Async Bridge, Memory Quality Scoring, Reflection Loop | superseded | resolved | 2026-05-13 | **Status: superseded — 2026-05-13.** Split into four standalone ADRs because this |
| [290](ADR-290.synthesis.md) | ADR-290.synthesis | superseded | not-applicable |  | This is a tombstone ADR: superseded and split into four standalone successor ADRs — ADR-292 (Pattern 1 lazy imports + Pattern 3 MCP thread bridge), ADR-293 (Pat |

</details>

<details>
<summary>Tombstone ADRs (13)</summary>

## Tombstone

| ADR | Title | Decision Status | Implementation | Date | Summary |
|---|---|---|---|---|---|
| [003](ADR-003-tombstone.md) | Reserved architecture decision slot | tombstone | not-applicable | 2026-05-05 | **Tombstone** — 2026-05-05 |
| [004](ADR-004-tombstone.md) | Reserved architecture decision slot | tombstone | not-applicable | 2026-05-05 | **Tombstone** — 2026-05-05 |
| [005](ADR-005-tombstone.md) | Reserved architecture decision slot | tombstone | not-applicable | 2026-05-05 | **Tombstone** — 2026-05-05 |
| [043](ADR-043-tombstone.md) | Removed local-daemon integration decision | tombstone | not-applicable | 2026-05-05 | **Tombstone** — 2026-05-05 |
| [046](ADR-046-tombstone.md) | Reserved architecture decision slot | tombstone | not-applicable | 2026-05-05 | **Tombstone** — 2026-05-05 |
| [085](ADR-085-tombstone.md) | Reserved architecture decision slot | tombstone | not-applicable | 2026-05-05 | **Tombstone** — 2026-05-05 |
| [207](ADR-207-skill-ecosystem-performance-and-lifecycle-closure.md) | Skill Ecosystem Performance and Lifecycle Closure | tombstone | not-applicable | 2026-05-06 | **Source**: `.cognitive-os/strategy/research/07-skill-ecosystem-evolution.md`, `.cognitive-os/strategy/research/05-hermes-imitation-forensics.md` |
| [214](ADR-214-tombstone.md) | Reserved — vacated by parallel-session number collision | tombstone | not-applicable | 2026-05-06 | **Tombstone** — 2026-05-06 |
| [224](ADR-224-shadow-state-snapshots-off-repo.md) | Tombstone (consolidated into ADR-227) | tombstone | not-applicable | 2026-05-08 | status: tombstone |
| [229](ADR-229-tombstone.md) | Tombstone (consolidated into ADR-228) | tombstone | not-applicable | 2026-05-06 | status: tombstone |
| [253](ADR-253-tombstone-squads.md) | Tombstone — squads orchestration superseded by ADR-251 | tombstone | not-applicable | 2026-05-08 | The `packages/squads/` orchestration package (multi-agent team coordination |
| [326](ADR-326-tombstone-agent-escalation-capabilities.md) | Tombstone — agent-escalation-capabilities plan (Phase 3 tombstoned, Phases 1+2 archived) | tombstone | not-applicable | 2026-05-18 | The plan `.cognitive-os/plans/features/agent-escalation-capabilities.md` was |
| [327](ADR-327-tombstone-workflow-engine.md) | Tombstone — workflow-engine plan superseded by shipped ADW substrate | tombstone | not-applicable | 2026-05-18 | The plan `.cognitive-os/plans/features/workflow-engine.md` was reconciled in two |

</details>
