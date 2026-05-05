# Cognitive OS Documentation

> Documentation for the operating layer that makes coding agents more governable, verifiable, and portable in real repositories.

## Overview

Cognitive OS is product-first infrastructure for real development teams. The adoption path is intentionally small: install the core, project settings through a supported harness driver, verify the active hooks and rules, then grow into optional extensions only when they prove value.

The durable product promise is: make coding agents governable, verifiable, and portable without requiring every team to become expert in agent infrastructure.

The repo still contains ambitious future architecture for squads, manager agents, dashboards, and control planes. Those surfaces are useful design material, but they are not first-contact product promises until backed by repeatable demos, tests, and operator workflows.

## Key Documents
- [ADR-162: Task Lifecycle, Interruption, Question, Worktree, and PR Protocol](adrs/ADR-162-task-lifecycle-interruption-question-worktree-pr-protocol.md) — contract for pausing/resuming tasks, structured agent questions, worktree ownership, branches, and propose-only PR flow.
- [Obsidian, Documentation Graphs, and AI Agent Memory — 2026-05-05](research/obsidian-doc-graph-ai-agent-memory-2026-05-05.md) — follow-up on using Obsidian as a human-readable graph layer for Engram-backed agent memory.
- [Remote SO Control Plane Alternatives — 2026-05-05](reports/remote-control-plane-alternatives-2026-05-05.md) — provider, CLI, API-key, chat/Telegram, OpenCode, OpenClaw, and Agent Zero research feeding ADR-161.
- [Primitive Readiness Continuity Plan](architecture/primitive-readiness-continuity-plan.md) — living cycle contract for mapping docs, scripts, hooks, skills, rules, memory, and harness adapters into governed agentic primitives.
- [Primitive Readiness Review — 2026-05-04](reports/primitive-readiness-review-2026-05-04.md) — first continuity-cycle review of lifecycle manifest, family coverage, automation-loop scripts, and low-scoring script triage.
- [Primitive Readiness Ledger Manual Test](manual-tests/primitive-readiness-ledger.md) — manual proof path for regenerating and inspecting the script readiness ledger.
- [ADR-146: Primitive Readiness Ledger](adrs/ADR-146-primitive-readiness-ledger.md) — accepted contract for the machine-readable script role ledger and future ratchet gates.
- [Primitive Readiness Ledger Family Extension Plan](architecture/primitive-readiness-ledger-family-extension.md) — staged plan for extending readiness ledgers from scripts to hooks, skills, and rules.
- [Consumer Project Primitive Accessibility](architecture/consumer-project-primitive-accessibility.md) — downstream-project projection contract and current Claude/Codex proof boundary.
- [Consumer Project Primitive Accessibility Manual Test](manual-tests/consumer-project-primitive-accessibility.md) — manual proof path for temp-project projection and readiness-ledger accessibility checks.
- [Agent Capability Coverage](agent-capability-coverage.md) — strategic report defining ACC as semantic system coverage for agentic primitives.
- [Agent Capability Coverage Pipeline](architecture/agent-capability-coverage-pipeline.md) — unified ACC orchestrator that consumes primitive readiness ledgers and existing audit tools.
- [ADR-147: Agent Capability Coverage Pipeline](adrs/ADR-147-agent-capability-coverage-pipeline.md) — decision record for `scripts/acc_pipeline.py` and `docs/acc/latest.*`.
- [ACC Fail-New Gate Manual Test](manual-tests/acc-fail-new-gate.md) — manual proof that ACC blocks new debt and keeps planned harnesses roadmap-only.
- [ADR-153: ACC Fail-New Gate and Harness Proof Boundary](adrs/ADR-153-acc-fail-new-and-harness-proof-boundary.md) — ratchet decision for strict new-debt blocking and planned-harness non-promotion.
- [Multi-IDE Harness Implementation Plan](architecture/multi-ide-harness-implementation-plan.md) — phased rollout for structural, shell/CI, provider, and account-backed harness support.
- [Harness Proof Levels](architecture/harness-proof-levels.md) — explicit boundary between structural projection, optional runtime smoke, native lifecycle proof, and planned-only support.
- [Multi-IDE Structural Projection Manual Test](manual-tests/multi-ide-structural-projection.md) — manual proof path for Claude, Codex, OpenCode, VS Code Copilot, and Cursor consumer projection.
- [ADR-154: Multi-IDE Structural Harness Projection](adrs/ADR-154-multi-ide-structural-harness-projection.md) — decision to promote OpenCode, VS Code Copilot, and Cursor to implemented structural projection harnesses.
- [Shell CI Formal Harness Manual Test](manual-tests/shell-ci-formal-harness.md) — manual proof path for `cos_init.py --harness shell-ci`, projected commands, and generated workflow.
- [ADR-155: Shell CI Formal Harness Projection](adrs/ADR-155-shell-ci-formal-harness.md) — decision to promote Shell/CI to an implemented structural command/workflow harness.
- [Qwen Code Structural Projection Manual Test](manual-tests/qwen-code-structural-projection.md) — manual proof path for `.qwen/settings.json`, `QWEN.md`, and ACC Qwen projection counts.
- [ADR-156: Qwen Code Structural Harness Projection](adrs/ADR-156-qwen-code-structural-harness-projection.md) — decision to promote Qwen Code to implemented structural projection.
- [Kimi Code CLI Structural Projection Manual Test](manual-tests/kimi-code-cli-structural-projection.md) — manual proof path for `AGENTS.md`, `.kimi/mcp.json`, and optional Kimi CLI smoke.
- [ADR-157: Kimi Code CLI Structural Harness Projection](adrs/ADR-157-kimi-code-cli-structural-harness-projection.md) — decision to promote Kimi Code CLI to implemented structural projection.
- [AI Agent Harness Landscape — 2026-05-04](reports/ai-agent-harness-landscape-2026-05-04.md) — current repo-plus-official-doc review of IDEs, CLIs, hosted agents, provider/tooling surfaces, and missing harness candidates.
- [ADR-158: AI Agent Harness Landscape and Proof Backlog](adrs/ADR-158-ai-agent-harness-landscape-and-proof-backlog.md) — decision to track broad ecosystem coverage in a separate machine-readable backlog without overclaiming runtime support.
- [ADR-159: AGENTS.md-native Structural Harness Batch and Kiro Lifecycle Investigation](adrs/ADR-159-agents-md-native-structural-harness-batch.md) — decision to promote Gemini, Warp, Amp, Junie, Qoder, and Factory Droid to structural projection while keeping Kiro lifecycle-only until adapter proof exists.
- [ADR-160: Rules/MCP Structural Harness Batch and Kiro Adapter Design](adrs/ADR-160-rules-mcp-structural-harness-batch-and-kiro-adapter-design.md) — decision to promote Cline, Continue, Kilo, Zed, Augment, Goose, and Aider to structural projection while preserving Kiro proof gates.
- [Harness Docs Currentness Audit — 2026-05-05](reports/harness-docs-currentness-audit-2026-05-05.md) — official-doc contrast for all implemented/planned harness projection claims, including Kilo, Goose, and Augment corrections.
- [Rules/MCP Structural Projection Manual Test](manual-tests/rules-mcp-structural-projection.md) — account-free temp-project proof path for the seven rules/MCP/context harnesses.
- [Kiro Lifecycle Adapter Design](architecture/kiro-lifecycle-adapter-design.md) — staged adapter design and gates before Kiro can be considered for native lifecycle proof.
- [AGENTS.md-native Structural Projection Manual Test](manual-tests/agents-md-native-structural-projection.md) — account-free temp-project proof path for the six new structural harnesses and Kiro investigation boundary.
- [Kiro Lifecycle Hook Investigation — 2026-05-05](reports/kiro-lifecycle-hook-investigation-2026-05-05.md) — current lifecycle event mapping gap and promotion criteria for Kiro.
- [AI Agent Harness Landscape Manual Test](manual-tests/ai-agent-harness-landscape-review.md) — manual proof path for source spot-checks, stale-claim checks, and ACC ratchet validation.
- [Multi-Session Orchestration Audit — 2026-05-02](architecture/multi-session-orchestration-audit-2026-05-02.md) — documented-vs-implemented matrix for multi-IDE/session/agent orchestration primitives and the next reconciler gap.
- [ADR-116 Direct-Main Policy](architecture/direct-main-policy.md) — local agent-block/operator-warn policy plus remote protection invariant for `main`/`master`.
- [Protected Landing Contract](architecture/protected-landing-contract.md) — vendor-neutral contract for protected `main`/`master` landing across GitHub, GitLab, Gitea/Forgejo, Bitbucket, bare Git, and unknown remotes.
- [ADR-116: Multi-Session Coordination Primitives](adrs/ADR-116-multi-session-coordination-primitives.md) — layered cross-session coordination model for claims, status, push collision checks, branch isolation, merge queue, and Engram evidence.
- [ADR-119: Session Filesystem Reaper](adrs/ADR-119-session-filesystem-reaper.md) — archive-first cleanup for stale `.cognitive-os/sessions/` filesystem artifacts.
- [ADR-120: Conversation-to-Primitive Harvester](adrs/ADR-120-conversation-to-primitive-harvester.md) — advisory classifier for promoting repeatable conversation recipes into governed agentic primitive proposals.
- [ADR-121: Foundation Hardening Program](adrs/ADR-121-foundation-hardening-program.md) — phased invariants for validation capsules, single-writer main, WIP ownership, guard maturity, lane taxonomy, and chaos coverage.
- [ADR-123: Operational Stability and Friction Reduction Program](adrs/ADR-123-operational-stability-friction-reduction.md) — guard maturity, adaptive profiles, repair-first blockers, unified status, and validation lanes.
- [ADR-124: COS Distribution Boundaries](adrs/ADR-124-cos-distribution-boundaries.md) — separates Core, Team, Maintainer, and Lab surfaces so users adopt safety primitives without the full meta-layer.
- [ADR-125: Governance Tools Value Boundary](adrs/ADR-125-governance-tools-value-boundary.md) — classifies governance into runtime safety, delivery structure, and maintainer meta-governance.
- [ADR-126: Agentic Primitive Lifecycle Governor](adrs/ADR-126-agentic-primitive-lifecycle-governor.md) — lifecycle states and gates for creating, promoting, demoting, archiving, and deleting self-adjusting primitives.
- [ADR-128: Data Layer Integrity Fixes](adrs/ADR-128-data-layer-integrity-fixes.md) — Engram upsert/ranking visibility, runtime coverage readiness, version audit, and SDD topic-key canonicalization.
- [Primitive Harvester](architecture/primitive-harvester.md) — architecture and JSON contract for create/improve/use/document/discard decisions.
- [Foundation Hardening Program](../.cognitive-os/plans/architecture/foundation-hardening-program.md) — execution checklist and production border-case matrix for ADR-121.
- [Operational Stability and Friction Reduction Program](../.cognitive-os/plans/architecture/operational-stability-friction-reduction.md) — phase checklist for lowering SO friction without weakening safety.
- [Governance Tools Consolidation Plan](../.cognitive-os/plans/architecture/governance-tools-consolidation.md) — execution plan for reducing governance friction and consolidating duplicate sources of truth.
- [External Review Readiness Plan](../.cognitive-os/plans/architecture/external-review-readiness-plan.md) — phased readiness plan that turns external architecture critique into executable gates and wiring work.
- [DX Tax Reduction Plan](../.cognitive-os/plans/architecture/dx-tax-reduction-plan.md) — phased plan for cognitive load, token tax, latency, indirection, harness coupling, upstream duplication, and self-referential overhead.
- [Integrity and De-Theater Sprint](../.cognitive-os/plans/architecture/integrity-and-de-theater-sprint.md) — P0 execution plan for runtime coverage, Engram reliability, product-claim integrity, and governance maturity labels.
- [Cognitive OS vs Vanilla IDE Agents — Senior DX Review](business/cos-vs-vanilla-dx-review.md) — honest persona-based DX review of COS value versus vanilla Claude Code, Codex, Cursor, and similar IDE-agent defaults.
- [DX Assessment Snapshot — 2026-05-02](reports/dx-assessment-2026-05-02.md) — frozen raw review snapshot of governance, cost, onboarding, cross-harness, SDD, and Engram gaps.
- [Primitive Harvester Implementation Plan](../.cognitive-os/plans/architecture/primitive-harvester-implementation-plan.md) — staged rollout plan and acceptance criteria for the meta-primitive.
- [Session Filesystem Reaper](architecture/session-filesystem-reaper.md) — operator flow and safety invariants for session filesystem cleanup.
- [Multi-IDE Swarm Safety Testbed Plan](../.cognitive-os/plans/architecture/multi-ide-swarm-testbed-plan.md) — executable plan for reproducing same-task, same-file, same-domain, git-overwrite, parity, memory, and watermark races.
- [Cross-IDE Claim Verification Matrix](architecture/claim-verification-matrix.md) — claim verbs mapped to deterministic verifiers, hooks, and tests so agents can report but not close without evidence.
- [ADR Collision Reconciliation — 2026-05-02](architecture/adr-collision-reconciliation.md) — namespace and semantic relationship cleanup for overlapping ADR clusters.
- [Agentic Mastery Operations Plan](architecture/agentic-mastery-operations.md) — executable command plan for local tests, reports, and manual proof paths.
- [Agentic Mastery Validation — 2026-05-02](reports/agentic-mastery-validation-2026-05-02.md) — automated and manual proof results for the MVP slices.
- [Agentic Mastery Manual Test](manual-tests/agentic-mastery.md) — manual proof path for safety, ACI capture, reports, and no-cost validation.
- [Agent Trajectory Schema](architecture/agent-trajectory-schema.md) — normalized ACI-derived tool trajectory rows for benchmark and skill evaluation.
- [Preserve Branch Lifecycle](architecture/preserve-branch-lifecycle.md) — lifecycle, manifest schema, and consumer-project projection for `codex/preserve-*` governance.
- [Preserve Branch Governance Report — 2026-05-02](reports/preserve-branch-governance-2026-05-02.md) — diagnostic report for current preserve branches and required controls.
- [Cognitive OS Agent-Computer Interface](architecture/agent-computer-interface.md) — bounded, explicit, risk-tagged tool observation schema.
- [Boring Reliability Control Plane](architecture/boring-reliability-control-plane.md) — tools and metrics for adoptable layers, DX budgets, WIP safety, false positives, and runtime reality.
- [Agentic Kernel Philosophy](architecture/agentic-kernel-philosophy.md) — kernel-style doctrine for small core, drivers, boot-path diet, and evidence-backed primitives.
- [Headless Self-Improvement Proposer](architecture/headless-self-improvement-proposer.md) — propose-only audit→fix loop that needs no dashboard and keeps human approval plus growth-discipline gates mandatory.
- [Headless Runtime Proof Strategy](architecture/headless-runtime-proof-strategy.md) — analysis of how to prove ADR-091/137/140 without putting heavy cloud/runtime checks into normal test lanes.
- [Headless Runtime Proof Drills](manual-tests/headless-runtime-proof-drills.md) — manual proof ladder for Docker worker, Engram Cloud sync, future headless task execution, crash/resume, VM, Kubernetes, and provider overlays.
- [COS Service Runtime Boundary](architecture/cos-service-runtime-boundary.md) — explicit boundary between today's IDE-embedded runtime, Docker worker surface, Engram Cloud service, and the future `cosd`/scheduler control plane.
- [COS Service Control Plane Research — 2026-05-04](architecture/service-control-plane-research-2026-05-04.md) — reference-system and credential-mode analysis for a future `cosd` scheduler/queue/worker service without credential scraping.
- [COS Service Control Plane Implementation Plan](architecture/service-control-plane-implementation-plan.md) — staged plan for local queue, worker leases, provider executor adapters, crash/resume, and propose-only PR output.
- [COS Service Control Plane Proof Drills](manual-tests/service-control-plane-proof-drills.md) — opt-in heavy/manual proof ladder for `cosd`, account-backed CLI adapters, auth-negative containers, and crash/resume.
- [COS Service Control Plane Contracts](../manifests/service-control-plane-schema.yaml) + [Provider Executor Contracts](../manifests/provider-executor-contracts.yaml) — Phase 0 machine-readable declarations for `cosd`, queue, worker, executor adapters, credential modes, evidence artifacts, and propose-only publication.
- [Self-Evolving Doctrine Proposals](architecture/self-evolving-doctrine-proposals.md) — control-plane evidence can generate proposed doctrine amendments without mutating runtime rules.
- [Cross-Instance Learning Runway](architecture/cross-instance-learning-runway.md) — portable evidence, registry locks, Engram bundles, and Shape-B federation triggers.
- [Cross-Instance Consumer E2E Drill — 2026-05-03](reports/cross-instance-consumer-e2e-2026-05-03.md) — fresh consumer install, provenance export/import, drills, and claim-audit honesty check.
- [Expansion Hardening Plan](architecture/expansion-hardening-plan.md) — three-sprint plan for scaling across PCs, IDEs, sessions, and autonomous agents without growing default-visible theatre.
- [Lifecycle Demotion Proof — task-completed hook](reports/lifecycle-demotion-task-completed-2026-05-03.md) — first semantic `demoted` lifecycle transition proving shrink-without-delete behavior.
- [ADR-133: Expansion Without Monsterization](adrs/ADR-133-expansion-without-monsterization.md) — lab-first promotion, portability-tax visibility, semantic matching, and federation boundaries.
- [ADR-134: Headless Self-Improvement Proposer](adrs/ADR-134-headless-self-improvement-proposer.md) — propose-only audit→fix loop with `human_approval_required: true` hardcoded and a blocked-actions list.
- [ADR-135: Self-Evolving Doctrine Proposals](adrs/ADR-135-self-evolving-doctrine-proposals.md) — control-plane evidence generates proposed doctrine amendments without mutating runtime rules.
- [ADR-136: Cross-Instance Learning Runway](adrs/ADR-136-cross-instance-learning-runway.md) — registry locks, evidence exchange, Engram bundles, and federation triggers as Shape-B runway primitives.
- [ADR-137: Operational Trajectory — Governance Layer → Embedded Runtime](adrs/ADR-137-operational-trajectory-governance-layer-to-embedded-runtime.md) — accepted directional commitment from Framing B (governance over agents) to Framing A (runtime that travels with the agent); orthogonal to ADR-132's Shape A/B axis.
- [ADR-138: Flow Contract Schema](adrs/ADR-138-flow-contract-schema.md) — required shape for `manifests/flow-contract-schema.yaml`; every cloud flow primitive declares its contract before it ships.
- [Vulnerability Remediation Flow](architecture/vuln-remediation-flow.md) — first lab cloud-flow registration surface backed by `skills/vuln-remediation-flow/flow_contract.yaml` and the ADR-138 register gate.
- [ADR-139: Account-Agnostic Multi-Provider Runtime](adrs/ADR-139-account-agnostic-multi-provider-runtime.md) — caller-supplied credentials for all COS surfaces; billing posture taxonomy; provider SDK license gate extending Rules §10; generic env var naming.
- [ADR-140: Cross-OS Containerized Deployment](adrs/ADR-140-cross-os-containerized-deployment.md) — Docker Compose worker stack for Linux/macOS/Windows+WSL2; satisfies `bootstrap-portability.md` for container surfaces; no shell profile assumption.
- [ADR-141: Engram Cloud as Cross-Instance Replication Transport](adrs/ADR-141-engram-cloud-cross-instance-replication.md) — wires upstream `engram cloud` as live-sync complement to git-jsonl; three coexisting modes; local SQLite authoritative; project-scoped tokens; conflict surfacing via propose-only contract.
- [Engram Cloud Docker Sync Manual Test](manual-tests/engram-cloud-docker-sync.md) — one-command and expanded proof that local Docker Engram Cloud can sync `luum-agent-os` plus a consumer project with scoped chunks and sync audit rows.
- [Engram Command Contract](architecture/engram-command-contract.md) — verified Engram CLI/API command shapes used by COS primitives, scripts, tests, and operator docs.
- [ADR-142: Compliance, Audit, and Air-Gapped Surface](adrs/ADR-142-compliance-audit-air-gapped-surface.md) — formalises `agent-audit-trail.jsonl` as compliance evidence surface; `audit_class` enumeration; `tenant_id` isolation; GDPR erasure path; air-gap deployment surface.
- [ADR-143: Closure Discipline Gate](adrs/ADR-143-closure-discipline-gate.md) — blocking maintainer audit that keeps validation infrastructure aligned after fast agent batches; covers suspended workflow references, hook-count snapshots, capsule fallback, primitive lifecycle findings, and quick-CI self-wiring.
- [Closure Discipline Manual Test](manual-tests/closure-discipline.md) — manual proof path for closing validation-system drift before claiming a multi-file maintainer batch is done.
- [ADR-144: Hook-Enforced Rule Projection Contract](adrs/ADR-144-hook-enforced-rule-projection-contract.md) — ensures rules excluded from startup context as hook-enforced have existing hooks in the canonical registry and generated harness settings.
- [ADR-137+ Implementation Review — 2026-05-04](reports/adr-137-plus-implementation-review-2026-05-04.md) — status matrix for ADR-137 through ADR-144, including three-day commit evidence, local implementation gaps, and Engram Cloud research triage.
- [Hook Registration Classification — 2026-05-04](reports/hook-registration-classification-2026-05-04.md) — classifies the remaining unregistered hook surface into future, conditional, manual, deprecated, demoted, and promotion-candidate buckets.
- [Python Major Dependency Review — 2026-05-04](reports/python-major-deps-review-2026-05-04.md) — resolver-backed decisions for the 11 held Python major bumps after `/deps-update`.
- [Python Major Follow-up — 2026-05-04](reports/python-major-followup-2026-05-04.md) — second-pass resolver evidence for wrapt, setuptools, and the remaining blocked major clusters.
- [ADR-145: Dependency Lane Split](adrs/ADR-145-dependency-lane-split.md) — separates heavy optional dependency stacks from the core maintainer lock so upstream optional constraints do not block core dependency hygiene.
- [Python Major Lane Resolution — 2026-05-04](reports/python-major-lane-resolution-2026-05-04.md) — records which formerly retained majors are applied, removed from core, or moved to optional dependency lanes after ADR-145.
- [Docker Image Review — 2026-05-04](reports/docker-image-review-2026-05-04.md) — removes the broken AutoMaker GHCR image from reference compose and keeps pinned Python images unchanged.
- [Hook-Enforced Rule Projection Manual Test](manual-tests/hook-enforced-rule-projection.md) — manual proof path for the EXCLUDED_RULES context diet, Claude/Codex projection, and dependency-upgrade bypass gate.
- [Session Handoff — 2026-05-04](SESSION-HANDOFF-2026-05-04.md) — evidence-based ADR implementation reality matrix and step-by-step execution order after ADR-143/144 closure.
- [ADR Implementation Closure Session — 2026-05-04](SESSION-ADR-CLOSURE-2026-05-04.md) — separate reconciliation pass for all ADRs up to ADR-138, classifying stale, superseded, obsolete, deferred, and still-current implementation gaps before writing code.
- [ADR Closure Policy](architecture/adr-closure-policy.md) — executable interpretation of closure classes: only `implement-current` becomes runtime work; deferred/evidence-only/absorbed/superseded/obsolete classes do not.
- [Claim Boundary Resolution — 2026-05-04](reports/claim-boundary-resolution-2026-05-04.md) — resolves self-building/Shape-B/ADR-closure claims without signing external adoption evidence prematurely.
- [DX-First Cloud Flow Bootstrap Plan](architecture/dx-cloud-flow-bootstrap-plan.md) — strategic plan for COS as runtime-of-prosthesis for cloud agent flows under human audit; vulnerability remediation in `e2b` sandbox as flow #1, with explicit bootstrap budget caps and falsifiable conditions. ADR-139..142 committed as cloud premises prereqs before promoting flow #1 beyond `lab`.
- [Skill Efficacy Measurement](architecture/skill-efficacy.md) — marginal skill utility metrics and report surface.
- [Runtime Benchmark MVP](architecture/runtime-benchmark-mvp.md) — no-cost local schema and leaderboard for vanilla-vs-COS comparisons.
- [Adversarial Generalization MVP](architecture/adversarial-generalization.md) — generated messy-task scenarios and deterministic rubric.
- [Agentic Mastery License, Weight, and DX Matrix](architecture/agentic-mastery-license-weight-dx-matrix.md) — licensing confidence, dependency weight, default-install impact, and DX value for candidate external tools.
- [Lethal Trifecta Gate](security/lethal-trifecta-gate.md) — deterministic PreToolUse block for private data + untrusted content + external communication.
- [Governed Self-Improvement Roadmap](architecture/plans/governed-self-improvement-roadmap.md) — executable plan for detect→draft→verify→approve→promote self-improvement with tests.
- [Suite Signal Triage — 2026-04-29](testing/suite-signal-triage-2026-04-29.md) — explains and reduces broad-lane xfail/warning/skipped noise without relaxing behavior.
- [Test Resource Governance Sprint](architecture/plans/test-resource-governance-sprint.md) — resource policy manifest and staged enforcement plan for safe local/CI/headless test execution.
- [Validation Nervous System](architecture/validation-nervous-system.md) — SO-maintainer doctrine for test selection, resource policy, persistent artifacts, governance gates, and release validation.
- [Rate Limiter Flow Control](architecture/rate-limiter-flow-control.md) — token-bucket action limiter with soft warnings, operator reserve, and diversity penalty.
- [Startup Circuit Breaker Plan](architecture/startup-circuit-breaker-plan.md) — implementation plan for ADR-101 safe mode, storm detection, SessionStart kill switch, and recovery command.
- [Competitive Reassessment: OpenClaw and Hermes Agent](business/competitive-reassessment-openclaw-hermes-2026-04.md) — current evidence-based comparison of self-improvement, memory, skills, deployment, and governance gaps.
- [Runtime Comparison Benchmark Plan](architecture/plans/runtime-comparison-benchmark-plan.md) — benchmark matrix for Claude/Codex vanilla, COS-enabled harnesses, and prior-art tools across deployment surfaces.
- [Headless and Clustered Runtime Plan](architecture/plans/headless-clustered-runtime-plan.md) — staged path from local harness runtime to EC2/container/Kubernetes workers.
- [Local Connected Systems Validation](manual-tests/local-connected-systems-validation.md) — proof path for dependency readiness, automatic install boundaries, MCP wiring, optional services, and persistent test summaries.
- [Claude Code Startup Hang Regression](manual-tests/claude-code-startup-hang-regression.md) — manual proof path for the 2026-05-01 startup hang/duplicate-prompt hardening and its automated regression tests.
- [Validation Capsule](architecture/validation-capsule.md) — scoped worktree-isolated validation wrapper that suppresses snapshot/profile mutators without using the global hook killswitch.
- [Validation Worktree Mutation Postmortem — 2026-05-02](reports/validation-worktree-mutation-postmortem-2026-05-02.md) — root-cause analysis of validation-induced worktree changes and false E2E failures.
- [Validation Capsule Manual Test](manual-tests/validation-capsule.md) — manual proof that release-lane validation runs with scoped guards and persistent artifacts.
- [ADR-109: Validation Capsule Worktree Isolation](adrs/ADR-109-validation-capsule-worktree-isolation.md) — accepted decision separating validation isolation from the global hook killswitch.

- [Adoption Tiers](adoption-tiers.md) — concrete guide: which hooks and primitives to enable for lean (solo-dev), standard (small team), and strict (enterprise agentic) configurations, with setup commands and a decision tree.

- [Architecture Principles](architecture-principles.md) — dependency model and layer boundaries
- [Design Philosophy](design-philosophy.md) — biological-system framing for the OS
- [Product Principles](product-principles.md) — product-level constraints and value focus
- [Product Zones](product-zones.md) — core, compatibility, extensions, and experimental taxonomy for keeping the product focused
- [Product Messaging](business/product-messaging.md) — how to present Cognitive OS as easy to adopt without making it feel simplistic
- [Developer Confidence and DX](business/developer-confidence.md) — why Cognitive OS improves trust, safety, onboarding, and continuity without enabling every subsystem by default
- [First-Run Onboarding Proof](manual-tests/first-run-onboarding.md) — executable proof that a fresh project can install, report status, and stay within onboarding budgets
- [Five-Minute Demo](manual-tests/five-minute-demo.md) — a short executable/manual path for proving install, harness projection, quality checks, provider contracts, and status visibility
- [Product Proof Paths](manual-tests/proof-paths.md) — product claims mapped to files, commands, tests, and manual checks
- [Codex Host Tooling Verification](manual-tests/codex-host-tooling-verification.md) — manual proof path for Codex driver wiring, declared dependencies, and Engram MCP registration
- [Memory Lifecycle](architecture/memory-lifecycle.md) — simple map of the hooks, libraries, tests, and doctors that save and recover cross-session context
- [Cross-Tool Task Recovery Research — 2026-05](architecture/cross-tool-task-recovery-research-2026-05.md) — investigation of solved/pending task recovery across Codex, Claude Code, Engram, local ledgers, transcripts, and git.
- [Token-Efficient Agent Messaging](architecture/token-efficient-agent-messaging.md) — compact sub-agent result contracts, JSONL extraction, bounded digests, and format choices for reducing LLM context waste.
- [Harness Transparency Status](architecture/harness-transparency-status.md) — honest matrix of what is automatic today across Claude Code, Codex, and consumer projects, and what remains in ADR-064 surfaces
- [ADR-081: Codex Harness Adapter](adrs/ADR-081-codex-harness-adapter.md) — accepted Codex adapter backed by sanitized live Codex Desktop payload fixtures, making Codex a first-class canonical harness surface
- [Model Evolution Resilience](model-evolution-resilience.md) — how to keep the system durable as models, vendors, and tools change
- [Kernel Contract](kernel-contract.md) — minimal inviolable core and where the machine-readable boundary lives
- [Bootstrap Portability](architecture/bootstrap-portability.md) — where the system is still Claude-first and how to make Codex and other harnesses first-class bootstrap hosts
- [Capability-Centric Runtime Enforcement](architecture/capability-centric-runtime-enforcement.md) — how dispatch, skills, gateways, and metrics choose execution intent before vendors
- [Runtime Hardcoding Discipline](architecture/runtime-hardcoding-discipline.md) — contract for keeping protected runtime paths from silently promoting non-core subsystems
- [Path Portability and Privacy](architecture/path-portability-and-privacy.md) — policy and scanner for blocking developer-home absolute paths in docs, code, scripts, skills, rules, and tests
- [Tooling Stack Rationalization](architecture/tooling-stack-rationalization.md) — how to keep external services lightweight, optional, and aligned with the product promise
- [Infrastructure Service Catalog](architecture/infrastructure-service-catalog.md) — what each Docker/Python/cloud service is for and whether it is core, optional, or reference-only
- [Observability Backend Evaluation](architecture/observability-backend-evaluation-2026-04-24.md) — 2026 decision record for MLflow, Langfuse, Opik, OpenTelemetry, and other observability options
- [Driver-Specific Script Surfaces](architecture/driver-specific-script-surfaces.md) — which user-facing scripts are truly cross-harness today and which remain Claude-driver-only by contract
- [Harness Driver Parity](architecture/harness-driver-parity.md) — how Claude, Codex, and future harness settings projections are compared without pretending every driver has the same capabilities
- [Codex Governed Tool Layer](architecture/codex-governed-tool-layer.md) — governed fallback for Agent and Edit/Write hook chains that Codex cannot emit natively today.
- [Cross-Harness Authoring](architecture/cross-harness-authoring.md) — how to author skills, rules, hooks, and workflows once and project them through harness drivers
- [Behavioral Test Contracts](architecture/behavioral-test-contracts.md) — doctrine for converting structural checks into runtime, projection, and discovery proof
- [Testing Guide](testing.md) — pytest lanes, persistent run summaries, and test-run inventories for large-suite repair work
- [Skills and Rules Portability Gap](architecture/skills-rules-portability-gap.md) — why compatibility is not enough and where `.claude/` gravity still weakens real portability
- [Skills and Rules Canonicalization Risk Analysis](architecture/skills-rules-canonicalization-risk-analysis.md) — why moving skills and rules out of `.claude/` is a contract migration, not a simple path change
- [Why Skills and Rules Became Claude-Centered](architecture/why-skills-and-rules-became-claude-centered.md) — historical root-cause analysis of why the current `.claude/` gravity emerged in the first place
- [Skills and Rules Canonicalization Workplan](architecture/skills-rules-canonicalization-workplan.md) — step-by-step migration plan and invariants for phases 1 through 5
- [Durable Product Master Plan](business/durable-product-master-plan.md) — how to sharpen the wedge, reduce focus drift, and make the repo less aspirational
- [Master Plan Execution Requirements](business/master-plan-execution-requirements.md) — what must become true in code, CI, onboarding, and product structure to make the master plan real
- [Execution Discipline](business/execution-discipline.md) — operating rules for keeping the master plan real, avoiding duplicated logic, and preserving durable memory across sessions
- [Master Plan Checklist](business/master-plan-checklist.md) — living checklist for tracking execution progress against the master plan
- [Feature Reality Audit](business/feature-reality-audit.md) — which feature areas are genuinely core, portable, and product-worthy versus still overextended or harness-advantaged
- [Conversation Reality Audit — 2026-04-30](business/conversation-reality-audit-2026-04-30.md) — investigation plan for validating real behavior, daily efficiency, DX, automagic claims, and competitive alternatives
- [Primitive Gap Matrix — 2026-04](reports/primitive-gap-matrix-2026-04.md) — living evidence matrix for hook, skill, rule, memory, MCP, config, metrics, test, and docs gaps
- [Primitive Coverage Tooling Research — 2026-04](architecture/primitive-coverage-tooling-research-2026-04.md) — external tooling research and architecture for coverage of agentic primitives/docs without loading whole repos into agent context.
- [Primitive Coverage Spike Plan — 2026-04](architecture/primitive-coverage-spike-plan-2026-04.md) — executable plan for a generic primitive coverage framework with graph, rule, and CI report surfaces.
- [Documentation Duplicate Audit](reports/docs-duplicate-latest.md) — latest duplicate-documentation baseline and prevention report
- [Merge Readiness Report](reports/merge-readiness-master-plan-2026-04-23.md) — validation snapshot and remaining work before merging the master-plan portability branch
- [Full Suite Validation Report](reports/full-suite-validation-2026-04-23.md) — current full-suite evidence, passing proof paths, and remaining failure families

## Current Product Center

The product center is deliberately smaller than the whole repository:

- `core`: canonical hooks, context, policy, package contracts, capability profiles, and outcome metrics.
- `compatibility`: provider, harness, IDE, gateway, and tool-schema adapters that absorb ecosystem churn.
- `extensions`: skills, rules, packages, MCP helpers, dashboards, and workflows that add value without defining the kernel.
- `experimental`: squads, organization specs, future control-plane designs, and high-variance systems that should not dominate the README.

See [Product Zones](product-zones.md) and [manifests/product-zones.yaml](../manifests/product-zones.yaml) for the enforceable taxonomy.

## Future Architecture Layers

The following model describes the long-range architecture. Treat it as future architecture unless a layer has a linked proof path, test, or operator workflow.

```
┌─────────────────────────────────────────┐
│           Organization Layer            │
│  (software-factory, squads, teams)      │
├─────────────────────────────────────────┤
│         Governance Engine               │
│  (approvals, policies, risk detection)  │
├─────────────────────────────────────────┤
│         Manager Agents                  │
│  (evaluation, metrics, autonomy control)│
├─────────────────────────────────────────┤
│     Control Plane (AgentField)          │
│  (lifecycle, identity, registry)        │
├─────────────────────────────────────────┤
│     Data Plane (Plano)                  │
│  (routing, observability, guardrails)   │
├─────────────────────────────────────────┤
│     Runtime Sandbox (E2B)               │
│  (Firecracker microVMs, isolation)      │
├─────────────────────────────────────────┤
│     Execution Agents (Workers)          │
│  (Claude, Go services, specialists)     │
├─────────────────────────────────────────┤
│     Memory Layer (Engram)               │
│  (persistent, cross-session, searchable)│
├─────────────────────────────────────────┤
│     Tool System (MCP)                   │
│  (skills, hooks, integrations)          │
├─────────────────────────────────────────┤
│     Fault Tolerance                     │
│  (task tracking, recovery, checkpoints) │
├─────────────────────────────────────────┤
│     Self-Improvement                    │
│  (error learning, KPIs, model routing)  │
├─────────────────────────────────────────┤
│     Workflow Engine                     │
│  (SDD, OpenSpec, AI workflows)          │
├─────────────────────────────────────────┤
│     Feedback & Retrospective            │
│  (metrics, model optimization, learning)│
└─────────────────────────────────────────┘
```

Each layer builds on the ones below it. The bottom layers (Tools, Memory) are already operational in dev-time. The upper layers (Governance, Organization) represent the production target.

---

## Future YAML Specifications

Cognitive OS may use Kubernetes-style declarative specs to define higher-level agent infrastructure. Today these specs are experimental design material, not the minimum product adoption path.

### Organization

The top-level resource. Defines supervision mode, evaluation metrics, and squad membership.

```yaml
apiVersion: agent.dev/v1
kind: Organization
metadata:
  name: software-factory
spec:
  supervision:
    mode: autonomous
  evaluation:
    metrics:
      - deliverySuccessRate
      - bugsIntroduced
      - costEfficiency
      - resolutionTime
    actions:
      degradeModelIfErrorRateHigh: true
      restrictAutonomyIfRiskDetected: true
  squads:
    - name: payments-team
      manager: manager-agent
    - name: creator-experience
      manager: cx-manager-agent
```

**Key concepts:**
- `supervision.mode` controls how much human oversight the organization requires (autonomous, supervised, manual)
- `evaluation.actions` enable automatic remediation — if error rates spike, the system can downgrade model tier or restrict autonomy
- Squads are the unit of team organization, each with a dedicated manager agent

### Squad

A squad groups agents around a domain with shared repos, governance, and a manager.

```yaml
apiVersion: agent.dev/v1
kind: Squad
metadata:
  name: payments-team
spec:
  manager:
    type: agent
    role: engineering-manager
  members:
    - role: backend-dev
      agentRef: sre-agent
    - role: product-owner
      agentRef: po-agent
    - role: agile-coach
      agentRef: agile-agent
    - role: treasury
      agentRef: treasury-agent
  repos:
    - github.com/org/payments-api
    - github.com/org/infra
  governance:
    approvalFlow: manager-required
```

**Key concepts:**
- Members reference Agent resources by name (`agentRef`)
- `repos` scope what code the squad can access
- `governance.approvalFlow` determines who must approve changes (manager-required, peer-review, auto-approve)

### Agent

An individual agent with its model, runtime, tools, autonomy level, and resource limits.

```yaml
apiVersion: agent.dev/v1
kind: Agent
metadata:
  name: sre-agent
spec:
  brain:
    model: architecture-review-model
    reasoning: reactive
  runtime:
    type: sandbox
    provider: e2b
    isolation: microvm
    persistence: true
  tools:
    protocol: MCP
    allowed:
      - kubernetes
      - github
      - slack
  autonomy:
    mode: supervised
    approvals:
      destructiveActions: required
  memory:
    shortTerm: true
    longTerm:
      provider: engram
  policies:
    budget:
      maxTokensPerHour: 50000
    security:
      networkAccess: restricted
  scaling:
    minInstances: 1
    maxInstances: 5
  scheduling:
    strategy: costAware
```

**Key concepts:**
- `brain.reasoning` can be reactive (respond to events), proactive (seek work), or planning (use SDD)
- `runtime.isolation: microvm` means each agent runs in a Firecracker microVM via E2B
- `autonomy.mode` controls how much the agent can do without human approval
- `policies.budget` prevents runaway costs with per-agent token caps
- `scheduling.strategy: costAware` routes to cheaper models when possible

### Manager Agent

A specialized agent that evaluates team performance and proposes organizational improvements.

```yaml
apiVersion: agent.dev/v1
kind: ManagerAgent
metadata:
  name: payments-manager
spec:
  evaluation:
    metrics:
      - successRate
      - hallucinationScore
      - bugsIntroduced
      - issueResolutionTime
  governance:
    requiresApprovalFor:
      - productionChanges
      - financialOperations
  retrospective:
    frequency: weekly
    actions:
      - analyzeFailures
      - proposeImprovements
      - adjustModelRouting
```

**Key concepts:**
- Manager agents observe execution agents and collect metrics
- `retrospective` runs periodically to analyze patterns and propose changes
- `adjustModelRouting` can switch agents to cheaper/better models based on performance data

---

## Execution Flow

```
Execution Agents (do work)
        ↓
Feedback & Events (capture metrics)
        ↓
Manager Agent (analyze, propose improvements)
        ↓
Governance Engine (validate proposals against policies)
        ↓
Mutation Engine (apply approved changes)
```

1. **Execution Agents** perform tasks: write code, review PRs, deploy services, respond to incidents
2. **Feedback & Events** capture everything: token usage, success/failure, latency, quality scores
3. **Manager Agent** runs retrospectives — analyzes failures, identifies patterns, proposes improvements
4. **Governance Engine** validates proposals against organizational policies (budget limits, security constraints, approval requirements)
5. **Mutation Engine** applies approved changes: model routing updates, autonomy adjustments, scaling changes

---

## Organization Hierarchy

```
Organization
   |
   +--- Squads
           |
           +--- Manager Agents (governance + evaluation)
                   |
                   +--- Operational Agents (backend-dev, frontend-dev, devops)
                   |
                   +--- Specialist Agents (PO, QA, UX, Finance, Security)
                   |
Retrospective Engine (cross-cutting layer — analyzes all squads)
```

- **Organization** owns global policies, budget, and evaluation criteria
- **Squads** own domain-specific repos, agents, and governance rules
- **Manager Agents** sit between the organization and operational agents — they enforce governance and evaluate performance
- **Operational Agents** do the actual work (coding, testing, deploying)
- **Specialist Agents** provide domain expertise (product decisions, security audits, financial analysis)
- **Retrospective Engine** runs across all squads, identifying cross-team patterns and proposing organizational improvements

---

## 13 Infrastructure Components

All gaps are now filled. The dev-time Cognitive OS is fully operational.

| # | Component | Status | Tool/Port |
|---|-----------|--------|-----------|
| 1 | Control Plane | Dev: CLAUDE.md orchestrator | -- |
| 2 | Scheduler | CronCreate + scheduled-tasks MCP | -- |
| 3 | Runtime Sandbox | E2B (cloud SDK + mock) | Port 8086 |
| 4 | Multi-Agent | Agent Teams Lite + sub-agents | -- |
| 5 | Identity | 6-layer identity stack documented (AIM, OneCLI, Cerbos, A2A, Agent Passport, SPIFFE) | -- |
| 6 | Memory | Engram | Port 7437 |
| 7 | Tool System | MCP + Skills + Hooks | -- |
| 8 | Observability | Langfuse + skill-metrics | Port 3100 |
| 9 | Cost Control | LiteLLM + model-optimizer | Port 4000 |
| 10 | Security | NeMo Guardrails + constitutional gates | Port 8088 |
| 11 | Fault Tolerance | Hooks + active-tasks.json + /resume-tasks | -- |
| 12 | Self-Improvement | Error learning + KPIs + model routing | -- |
| 13 | Workflow Engine | SDD + OpenSpec + AI workflows | -- |

### Self-Improvement Loop (Component 12)

The self-improvement loop is a closed feedback cycle where every agent execution produces data that improves future executions:

```
Agentes ejecutan tareas
    |
    v
Hooks capturan: metricas (tokens, tiempo, costo) + errores (test/lint/build)
    |
    v
Pattern detector inyecta warnings en proximos agentes
    |
    v
/error-analyzer propone skill updates
    |
    v
/model-optimizer ajusta routing de modelos
    |
    v
/agent-kpis mide todo con 20 KPIs
    |
    v
Alertas -> remediation automatica
    |
    v
Skills mejorados -> agentes mas eficientes
    |
    v
KPIs suben -> loop cerrado
```

### Component Details

### 1. Control Plane — AgentField

| Aspect | Detail |
|--------|--------|
| What it does | Agent lifecycle management, identity, registry, health checks |
| Current state | Dev: CLAUDE.md orchestrator with Agent Teams Lite |
| Target state | Declarative agent specs reconciled by control loops (K8s-style) |
| Implementation | AgentField (Apache 2.0) or custom Go controller |

### 2. Scheduler — Distributed

| Aspect | Detail |
|--------|--------|
| What it does | Assigns tasks to agents based on capacity, cost, and specialization |
| Current state | CronCreate + scheduled-tasks MCP for recurring/one-time tasks |
| Target state | Distributed scheduler with cost-aware routing and priority queues |
| Implementation | Custom scheduler with integration to AgentField |

### 3. Runtime Sandbox — E2B

| Aspect | Detail |
|--------|--------|
| What it does | Isolated execution environments for agents (code execution, tool use) |
| Current state | E2B cloud SDK + local mock on port 8086 |
| Target state | Each agent gets a Firecracker microVM with persistent filesystem |
| Implementation | E2B (Apache 2.0) — Firecracker-based sandboxes |

### 4. Multi-Agent Orchestration — Agent Teams + Squad Model

| Aspect | Detail |
|--------|--------|
| What it does | Coordinates multiple agents working on shared goals |
| Current state | Agent Teams Lite (orchestrator + sub-agents in single session) |
| Target state | Squad model with persistent agents, manager oversight, and cross-squad coordination |
| Implementation | Custom orchestration layer on top of AgentField |

### 5. Identity — 6-Layer Identity Stack

| Aspect | Detail |
|--------|--------|
| What it does | Unique, verifiable identity for each agent (for audit trails, access control, delegation) |
| Current state | Phase 1 implemented: agent identification, audit trail rules, trust levels, credential rules |
| Target state | 6-layer stack: AIM (crypto), OneCLI (credentials), Cerbos (permissions), A2A Agent Cards (discovery), Agent Passport (delegation), SPIFFE/SPIRE (infra) |
| Implementation | See [identity-stack.md](identity-stack.md) for full architecture |

### 6. Memory — Engram

| Aspect | Detail |
|--------|--------|
| What it does | Persistent, searchable memory across sessions and agents |
| Current state | Engram operational on port 7437 — FTS5 search, session tracking, topic keys |
| Target state | Multi-agent shared memory with access control and namespacing |
| Implementation | Engram (already built) — extend with multi-agent support |

### 7. Tool System — MCP

| Aspect | Detail |
|--------|--------|
| What it does | Standardized protocol for agent-tool communication |
| Current state | MCP servers for Chrome, Preview, Context7, Google Drive, scheduled-tasks, etc. |
| Target state | Tool marketplace with per-agent permissions and usage tracking |
| Implementation | MCP (already operational) — extend with registry and permissions |

### 8. Observability — Langfuse + skill-metrics

| Aspect | Detail |
|--------|--------|
| What it does | Traces, metrics, and logs for all agent activity |
| Current state | Langfuse on port 3100 + skill-metrics-tracker.sh capturing per-execution data |
| Target state | Full OpenTelemetry integration with dashboards, alerting, cost attribution |
| Implementation | Langfuse + skill-metrics.jsonl + /agent-kpis for KPI dashboards |

### 9. Cost Control — LiteLLM + Model Optimizer

| Aspect | Detail |
|--------|--------|
| What it does | Prevents runaway costs, routes to optimal model per task |
| Current state | LiteLLM proxy on port 4000 + model-routing.md rule + /model-optimizer skill |
| Target state | Automatic model routing based on task complexity, per-agent budget caps, cost dashboards |
| Implementation | LiteLLM proxy + model-routing rule + /model-optimizer skill |

### 10. Security — NeMo Guardrails + Constitutional Gates

| Aspect | Detail |
|--------|--------|
| What it does | Prevents agents from taking harmful actions, enforces policies |
| Current state | NeMo Guardrails on port 8088 + constitutional gates + license policy + control manifest |
| Target state | Runtime policy enforcement, sandbox network isolation, cryptographic audit trails |
| Implementation | NeMo Guardrails + constitutional gates + E2B isolation |

### 11. Fault Tolerance — Hooks + Task Recovery

| Aspect | Detail |
|--------|--------|
| What it does | Ensures tasks survive agent crashes, session timeouts, and compactions |
| Current state | 3 hooks (agent-prelaunch, agent-checkpoint, session-resume) + active-tasks.json + /resume-tasks skill |
| Target state | Distributed task queue with at-least-once delivery guarantees |
| Implementation | Hook-based lifecycle tracking with JSON state file |

### 12. Self-Improvement — Error Learning + KPIs + Model Routing

| Aspect | Detail |
|--------|--------|
| What it does | Closed feedback loop: captures errors, detects patterns, improves skills, optimizes models |
| Current state | error-learning.sh + error-pattern-detector.sh + /error-analyzer + /model-optimizer + /agent-kpis (20 KPIs, 5 OKRs) |
| Target state | Autonomous self-healing: agents that fix their own skills without human intervention |
| Implementation | Hook-based data capture + skill-based analysis + rule-based routing |

### 13. Workflow Engine — SDD + OpenSpec

| Aspect | Detail |
|--------|--------|
| What it does | Structured multi-phase workflows for substantial changes |
| Current state | SDD (7 phases) + OpenSpec file-based artifacts + AI workflows |
| Target state | Visual workflow editor with drag-and-drop phase composition |
| Implementation | SDD skills + OpenSpec convention + Engram persistence |

---

## Implementation Phases

### Phase 1 — Dev-time Cognitive OS (DONE)

What exists today as the Cognitive OS ecosystem (all 13 components operational):

- Engram persistent memory (port 7437)
- SDD (Spec-Driven Development) workflow with 7 phases
- Skills system with auto-detection, auto-improvement, and 13+ skills
- 41 hooks: stack-detector, session-resume, block-prod-urls, error-pattern-detector, agent-prelaunch, auto-test-on-edit, skill-feedback-tracker, skill-metrics-tracker, error-learning, agent-checkpoint, auto-repair-dispatcher, metrics-rotation, metrics-calibrator-trigger, tool-discovery-trigger, conversation-capture, session-knowledge-extractor, and more
- 44 rules: constitutional-gates, control-manifest, license-policy, skill-adaptation, skill-auto-loader, skill-registry, model-routing, error-learning, fault-tolerance, agent-kpis, services-config, auto-repair, metrics-calibration, and more
- Agent Teams Lite (orchestrator + sub-agents)
- Self-improvement loop: error learning -> pattern detection -> skill updates -> model optimization -> KPI measurement
- Fault tolerance: task registration, checkpointing, automatic recovery
- Observability: Langfuse (port 3100) + skill-metrics.jsonl
- Cost control: LiteLLM (port 4000) + model-routing rule + /model-optimizer skill
- Security: NeMo Guardrails (port 8088) + constitutional gates
- Workflow engine: SDD + OpenSpec + AI workflows

### Phase 2 — Production Agent Infrastructure (Near-term)

Extending from dev-time to production-capable (partially done):

- E2B sandboxes for isolated code execution (cloud SDK + local mock on port 8086)
- Langfuse for observability (port 3100) + skill-metrics for per-execution tracking
- LiteLLM for cost control (port 4000) + model-routing for optimal model selection
- Agent identity (Phase 1 rules + 6-layer stack designed — see [identity-stack.md](identity-stack.md))
- Persistent agent state via fault-tolerance hooks + active-tasks.json

### Phase 3 — Squad Model (Medium-term)

Organizational structure for agent teams:

- Organization / Squad / Agent YAML specifications
- Manager agents with governance and evaluation
- Retrospective engine (weekly analysis, improvement proposals)
- Evaluation metrics pipeline (success rate, cost efficiency, bugs introduced)
- Cross-squad visibility and coordination

### Phase 4 — Full Cognitive OS (Long-term)

Target architecture for production-grade autonomous agent infrastructure
(not current default behavior):

- kagent for Kubernetes-native agent deployment
- Auto-scaling agents based on workload
- Cross-squad coordination and resource sharing
- Self-improving organization (retrospective engine proposes and applies org changes)
- W3C DID-based identity and cryptographic audit trails
- Tool marketplace with community contributions

---

## License Requirements

All components MUST be Apache 2.0 or MIT (SaaS-safe per license-policy.md).

| Component | License | Status |
|-----------|---------|--------|
| AgentField | Apache 2.0 | Candidate |
| E2B | Apache 2.0 | Candidate |
| Plano | Apache 2.0 | Candidate |
| Engram | Custom (internal) | Built |
| MCP | Open standard | In use |
| OpenTelemetry | Apache 2.0 | Standard |
| kagent | Apache 2.0 | Candidate |

No AGPL, SSPL, BSL, or ELv2 components are permitted. See [Blocked Tools](blocked-tools.md) and [Component Sources](component-sources.md) for license decisions and source tracking.

---

## Related Documents

- [Cognitive OS Index](INDEX.md) — Sub-document index for the Cognitive OS section
- [Overview](overview.md) — Current system overview
- [Tool Stack](tool-stack.md) — Evaluated tools and integration posture
- [Blocked Tools](blocked-tools.md) — SaaS safety verdicts and blocked licenses
- [Harness Engineering](architecture/harness-engineering.md) — Harness portability doctrine, init checks, and profile measurement
- [Architecture Principles](architecture-principles.md) — How the durable product boundaries fit together

## Getting started

- [Cognitive OS Core in 30 Minutes](getting-started/core-30-minute-onboarding.md) — smallest reliable adoption path.

## Architecture

- [ADR-111: Core/Consumer Boundary for Concurrent-Agent Safety](adrs/ADR-111-core-consumer-concurrency-safety-boundary.md)
- [Concurrent-Agent Safety Core/Consumer Contract](architecture/concurrency-safety-core-consumer-contract.md)
