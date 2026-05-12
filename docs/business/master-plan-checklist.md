# Master Plan Checklist

> Living checklist for tracking execution of the durable product master plan.

## How To Use This Checklist

- Mark items complete only when there is evidence in code, docs, CI, demos, or tests.
- Prefer linking real artifacts when a checkbox is completed.
- Treat unchecked items as product work, not just documentation wishes.

## 1. Product Promise

- [ ] Keep the [Primitive Readiness Continuity Plan](../architecture/primitive-readiness-continuity-plan.md) current in every SO evolution cycle: refresh primitive index, gap snapshot, coverage, docs audit, script role classification, and harness proof before claiming universal agent-tool support.
- [x] Machine-readable script primitive readiness ledger exists through `scripts/primitive_readiness_ledger.py`, [ADR-146](../adrs/ADR-146-primitive-readiness-ledger.md), and `docs/reports/primitive-readiness-ledger-scripts-latest.json`; remaining work is triage/ratchet, not first-pass visibility.
- [x] Hooks/skills/rules ledger extension is staged in [Primitive Readiness Ledger Family Extension Plan](../architecture/primitive-readiness-ledger-family-extension.md).
- [x] Finish the script lifecycle backlog in `docs/reports/primitive-readiness-lifecycle-backlog-scripts-latest.json`; script agentic primitives now have lifecycle rows or non-agentic roles, with promotion/downgrade/archive remaining as candidate-state work.
- [x] Script readiness low-confidence triage is closed through `manifests/primitive-readiness-script-overrides.yaml`; `python3 scripts/primitive_readiness_ledger.py --fail-low-confidence` exits 0.
- [x] Profile-managed install/projection scripts are protected from naive demotion through `manifests/primitive-readiness-protected-install-surfaces.yaml` and lifecycle backlog `priority: protected`.
- [x] Protected install/profile scripts have candidate lifecycle metadata in `manifests/primitive-lifecycle.yaml` without changing runtime projection; remaining script lifecycle backlog is 0 rows.
- [x] Script readiness now tracks `consumer_accessibility` so repository-local docs/skills are not mistaken for downstream project availability.
- [x] Hooks/skills/rules readiness ledgers exist through `scripts/primitive_family_readiness_ledger.py` and the generated `docs/reports/primitive-readiness-ledger-{hooks,skills,rules}-latest.*` reports.
- [x] Consumer-project projection proof is documented in [Consumer Project Primitive Accessibility](../architecture/consumer-project-primitive-accessibility.md) and automated for implemented native/structural harnesses by `tests/behavior/test_consumer_project_projection.py`; structural projection does not imply runtime enforcement.
- [x] Primitive write authority is documented and implemented through [ADR-276](../adrs/ADR-276-primitive-authority-write-effects.md), [Primitive Authority and Write-Effects Boundary](../architecture/primitive-authority-write-effects.md), `manifests/primitive-authority.yaml`, `scripts/primitive_authority_audit.py`, dynamic filesystem-delta smokes, and ACC `authority_write_effects`.
- [x] Documentation truth drift is contract-tested through [ADR-277](../adrs/ADR-277-documentation-truth-control.md), [Documentation Truth Control](../architecture/documentation-truth-control.md), `manifests/documentation-truth-claims.yaml`, `scripts/documentation_truth_audit.py`, generated truth blocks, and ACC `documentation_truth`.
- [x] ADR verification evidence levels are documented in [ADR Verification Evidence Contract](../architecture/adr-verification-evidence-contract.md) so ADR-067 `## Verification` blocks cannot rely on grep-only theater.
- [x] Harness implementation coverage is separated from `SCOPE` intent through [ADR-189](../adrs/ADR-189-harness-implementation-coverage.md), `scripts/primitive_harness_coverage.py`, and `docs/reports/primitive-harness-coverage-latest.json`, so agents can see Claude/Codex/Shell-CI primitive differences without overclaiming parity.
- [x] OpenSage-inspired self-programming patterns are constrained by a pattern-only manifest and audit (`manifests/self-programming-agent-patterns.yaml`, `scripts/cos-self-programming-pattern-audit`) before any dynamic agent/tool/memory/sandbox runtime adoption.
- [x] Unified ACC pipeline exists through `scripts/acc_pipeline.py`, [ADR-147](../adrs/ADR-147-agent-capability-coverage-pipeline.md), and `docs/acc/latest.json`; it consumes readiness ledgers and existing audit tools instead of requiring manual interpretation.
- [x] The README expresses the same core product promise as the master plan.
- [x] CONTRIBUTING is aligned with the product-core narrative instead of subsystem sprawl.
- [x] The product promise is documented in [Durable Product Master Plan](durable-product-master-plan.md).
- [x] The product promise is documented in [Master Plan Execution Requirements](master-plan-execution-requirements.md).
- [x] Product positioning is documented in [Product Messaging](product-messaging.md).
- [x] Product and commercial answers are now evidence-backed through [ADR-280](../adrs/ADR-280-product-question-to-evidence-primitive.md), [Product Answer Playbook](product-answer-playbook.md), `manifests/product-question-bank.yaml`, `manifests/product-claim-evidence.yaml`, and `scripts/cos-product-answer`.
- [x] Repeated product and commercial answers are token-efficient through [ADR-282](../adrs/ADR-282-product-answer-card-cache-and-freshness-ledger.md), local `.cognitive-os/product-answers/` answer cards, source-hash freshness checks, compact routing index, and `scripts/cos-product-answer-refresh`.

## 2. Protected Core

- [x] A machine-readable kernel contract exists in [manifests/kernel-contract.yaml](../../manifests/kernel-contract.yaml).
- [x] Kernel scope is documented in [Kernel Contract](../kernel-contract.md).
- [x] Kernel contract tests exist.
- [x] The skills/rules portability gap is documented in [Skills and Rules Portability Gap](../architecture/skills-rules-portability-gap.md).
- [x] The canonicalization risk of moving skills/rules out of `.claude/` is documented in [Skills and Rules Canonicalization Risk Analysis](../architecture/skills-rules-canonicalization-risk-analysis.md).
- [x] A step-by-step migration plan exists in [Skills and Rules Canonicalization Workplan](../../.cognitive-os/plans/architecture/skills-rules-canonicalization-workplan.md).
- [x] Status and diagnostic tooling can read canonical-first artifact surfaces without changing install destinations.
- [x] Core versus compatibility versus extension versus experimental taxonomy is documented in [Product Zones](../product-zones.md).
- [x] New runtime additions are consistently classified by zone through root guardrails in [Product Zones Manifest](../../manifests/product-zones.yaml).
- [x] Central runtime paths avoid hardcoding non-core subsystems by default through [Runtime Hardcoding Discipline](../architecture/runtime-hardcoding-discipline.md) and `tests/contracts/test_runtime_hardcoding.py`.

## 3. Capability-Centric Enforcement

- [x] Capability profiles exist in the runtime.
- [x] Model routing uses capability-centric execution profiles before model choice.
- [x] Compatibility inventory explicitly distinguishes implemented and documented surfaces.
- [x] Dispatch uses capability-centric execution paths.
- [x] Gateway selection is capability-centric before vendor-centric.
- [x] Skill routing is capability-centric before vendor-centric.
- [x] Execution records and metrics include execution-profile data, not only model branding.
- [x] Direct Anthropic API usage is separated from Claude Code native account execution through [Direct Anthropic API Policy](../architecture/direct-anthropic-api-policy.md) and centralized runtime tests.
- [x] Advisor MCP is classified as optional external-advisor transport, not the canonical native advisor primitive, through [Advisor MCP Architecture Review](../architecture/advisor-mcp-architecture-review.md).

## 4. CI and Validation Integrity

- [x] Silent branch switches are covered by [Post-Mortem — Silent Agent Branch Switch and Unexpected Commit Destination — 2026-05-08](../reports/silent-agent-branch-switch-postmortem-2026-05-08.md), `hooks/destructive-git-blocker.sh`, and unit tests that block unaudited `git switch` / `git checkout <branch>` context changes.
- [x] Default CI covers representative Python product tests.
- [x] Default CI covers Go kernel and provider tests.
- [x] Default CI covers representative contract tests.
- [x] Default CI covers key behavior tests.
- [x] Default CI includes documentation integrity checks.
- [x] Release-plumbing checks can reason about canonical-first skill surfaces without changing install destinations.
- [x] Release-plumbing checks can validate the active settings driver instead of assuming `.claude/settings.json` is the only settings surface.
- [x] Audit and wiring validation can read the active settings driver instead of assuming `.claude/settings.json` is the only runtime surface.
- [x] CLI health and hook reporting can read the active settings driver instead of assuming `.claude/settings.json` is the only user-facing runtime surface.
- [x] Transparency/status reporting can read the active settings driver instead of assuming `.claude/settings.json` is the only hook-wiring surface.
- [x] Uninstall paths clean the active settings driver instead of assuming `.claude/settings.json` is the only hook-registration surface.
- [x] Secondary user-facing scripts use canonical project-root precedence when reading runtime state.
- [x] Update and auto-update paths preserve the active harness/settings driver instead of silently assuming Claude.
- [x] Git-triggered `post-merge` and `pre-push` auto-update paths preserve Codex-first installations through install metadata, even when `.claude/` compatibility markers are present.
- [x] Driver-specific user-facing scripts are explicitly classified so Claude-only registration/profile flows do not masquerade as Codex support.
- [x] Broken product-facing links fail visibly in automation.
- [x] Product claims in README and pitch map to explicit verification paths through [Product Proof Paths](../manual-tests/proof-paths.md).
- [x] Structural tests that support product claims are being converted into behavioral contracts through [Behavioral Test Contracts](../architecture/behavioral-test-contracts.md) and `tests/contracts/test_canonical_projection_behavior.py`.
- [x] Slow full-suite repair runs leave persistent summaries and actionable inventories through `scripts/pytest-with-summary.sh`, `scripts/test_run_inventory.py`, and [Testing Guide](../testing.md).
- [x] Test resource policy has a first manifest in `.cognitive-os/test-resource-policy.yaml`, with dry-run visibility and audit coverage for lane/resource alignment.
- [x] Test resource policy enforces timeout and explicit opt-in gates for cost-bearing and docker-required lanes in `cos-test`.
- [x] Test runs persist resource-policy metadata and outcome classification in
  `resource-policy.json`, including functional failures, policy blocks, and
  timeout exhaustion.
- [x] Local and CI test defaults are explicit: fast focused, broad non-Docker,
  Docker/e2e opt-in, and cost-bearing optional lanes have separate commands.
- [x] Slow live integration is explicit rather than part of the default
  non-Docker broad lane.
- [x] SessionStart performs a cached host-tool doctor check through `hooks/host-tool-doctor.sh`, while keeping broad pytest inventory explicit to avoid startup overload.
- [x] Primitive-coverage backend candidates have a documented local benchmark and unit-tested harness in [Primitive Coverage Backend Benchmark Research](../architecture/primitive-coverage-backend-benchmark-2026-05.md), so future graph/index integrations must prove license, offline, JSON/SARIF, stale-doc, and primitive-semantic fit before adoption.
- [x] Hook-enforced rule exclusions are contract-tested through [ADR-144](../adrs/ADR-144-hook-enforced-rule-projection-contract.md), `tests/audit/test_hook_enforced_exclusions.py`, and the projection drivers, so startup context diet cannot silently remove enforcement.
- [x] ADR-137 through ADR-144 have an implementation-status review in [ADR-137+ Implementation Review — 2026-05-04](../reports/adr-137-plus-implementation-review-2026-05-04.md), separating accepted cloud-flow premises from executable gates and naming the remaining local/web research.

## 5. Onboarding and Operational Simplicity

- [x] Standalone ship-readiness status is captured in [Standalone Ship Readiness — 2026-05-06](../architecture/standalone-ship-readiness-2026-05-06.md), including release, Surface 5, `cosd` API, and install-root portability evidence.
- [x] Surface 5 and secure `cosd` next-slice scope is grounded in existing SO features through [Surface 5 TUI and Secure cosd Roadmap](../architecture/surface-5-and-secure-cosd-roadmap.md).
- [x] `cosd` remote exposure is guarded by [ADR-194](../adrs/ADR-194-cosd-secure-remote-api.md): non-local binds require `--allow-remote` plus bearer-token auth, and protected writes emit audit rows.
- [x] Surface 5 has a read-only operator MVP through [ADR-195](../adrs/ADR-195-surface-5-operable-tui-contract.md), `cos tui`, and `cos tui --snapshot`.
- [x] Standalone release plumbing is represented by [ADR-191](../adrs/ADR-191-cos-binary-release-pipeline.md), `.goreleaser.yaml`, `.github/workflows/cos-binary-release.yml`, and a non-placeholder HEAD Homebrew formula.
- [x] Surface 5 has a sourced TUI substrate decision through [ADR-192](../adrs/ADR-192-surface-5-adopt-bubbletea.md) and a compile-tested Bubble Tea proof package.
- [x] `cosd` has a local network API decision and implementation through [ADR-193](../adrs/ADR-193-cosd-local-network-api.md), `scripts/cos_daemon.py serve`, and API tests.
- [x] Headless standalone validation has an install-path-safe wrapper through `scripts/cos-headless-pipeline` and root resolution through `scripts/cos-root`.
- [x] First-run installation is one-pass and low-friction through [First-Run Onboarding Proof](../manual-tests/first-run-onboarding.md).
- [x] Autodetection reduces required configuration for new users through shared harness detection and Codex-driver bootstrap coverage in `tests/integration/test_project_settings_generation.py`.
- [x] Settings projection supports more than one harness target in bootstrap paths.
- [x] Codex settings projection uses native `.codex/hooks.json` lifecycle keys
  instead of preserving Claude's `hooks` wrapper as a hidden compatibility crutch.
- [x] CLI runtime reads canonical skill/rule artifacts when the Claude projection is absent.
- [x] Upgrade paths preserve the active harness instead of silently falling back to Claude-first settings projection.
- [x] Emergency-stop keeps the core safety path cross-harness while marking Claude-only profile projection honestly.
- [x] Skills and rules use canonical-first discovery instead of depending on `.claude/` as the primary surface.
- [x] Codex-first projects get automatic advisory detection for active driver, dependency manifest, and Engram/MCP host wiring without requiring users to know the deep verification command.
- [x] Harness driver parity is now audited through `manifests/harness-driver-capabilities.yaml` and `scripts/harness_parity_audit.py`, so supported Codex gaps fail while limited/unsupported hook surfaces remain visible roadmap work.
- [x] Codex and Claude sessions now auto-load the portable memory lifecycle on
  supported events, with tests proving Codex can write session learning and
  resume tasks without `CLAUDE_PROJECT_DIR`.
- [x] The host doctor now includes a synthetic memory lifecycle check, proving
  that a new Codex session can start Engram, recover pending work, capture
  prompt/session state, write git context, write a changelog, and emit the
  compaction memory-save reminder.
- [x] A portable session backlog reconciler (`scripts/cos_session_backlog.py`) now
  consolidates active tasks, plans, request queues, changelogs, handoffs, ADR
  implementation status, git, and optional Engram memory into
  `.cognitive-os/sessions/{session_id}/backlog.md`,
  `.cognitive-os/metrics/backlog-reconciliation.jsonl`,
  `.cognitive-os/metrics/adr-implementation-latest.json`, and `session/backlog/latest`.
- [x] Agentic primitive classification is now contract-enforced through
  `tests/contracts/test_primitive_scope_classification.py`: new skills, hooks,
  templates, and skill-referenced scripts must declare scope/audience/platform
  metadata and remain covered by product-zone guardrails and install-scope proof.
- [x] Conversation-to-primitive promotion is now advisory and tested through `scripts/cos_primitive_harvester.py`, `skills/primitive-harvester/SKILL.md`, and ADR-120: repeatable recipes can become primitive proposals, existing primitives are reused/improved, docs-only decisions stay docs-only, and low-signal conversations are discarded.
- [x] Developer-confidence positioning is documented as a lightweight adoption
  path: memory, doctor, minimal hooks, safety, changelog/session learning, and
  checks only where they provide clear value.
- [x] Harness transparency status is documented honestly: memory protection and fallback persistence work today across Claude Code and Codex, while ADR-064 Surfaces 2–4 remain the path to full cross-harness transparency.
- [x] AI agent IDE/CLI/hosted-agent landscape is tracked without overclaiming runtime support through [AI Agent Harness Landscape — 2026-05-04](../reports/ai-agent-harness-landscape-2026-05-04.md), [ADR-158](../adrs/ADR-158-ai-agent-harness-landscape-and-proof-backlog.md), and `manifests/ai-agent-harness-landscape.yaml`.
- [x] Multi-provider agent delegation research is refreshed in [Multi-Provider Agent Delegation Research — 2026-05-05](../reports/multi-provider-agent-delegation-research-2026-05-05.md), covering Qwen, Kimi, DeepSeek, MiniMax, OpenClaw/Lucy, and router/coworker patterns across 51 current sources.
- [x] Gemini CLI plus AGENTS.md-native Warp, Amp, Junie, Qoder, and Factory Droid have structural temp-project projection, while Kiro lifecycle hooks remain investigation-only until adapter/runtime proof exists.
- [x] Cline, Continue.dev, Kilo Code, Zed AI, Augment/Auggie, Goose, and Aider have structural temp-project projection, with Kiro native-lifecycle promotion gated behind adapter design, event mapping, and runtime smoke.
- [x] Harness projection claims were contrasted against current official docs in [Harness Docs Currentness Audit — 2026-05-05](../reports/harness-docs-currentness-audit-2026-05-05.md), correcting Kilo, Goose, and Augment file-shape drift.
- [x] Codex has a governed fallback layer for non-native Agent and Edit/Write hook chains through `scripts/cos_governed_runner.py` plus the Codex wrapper `scripts/cos_codex_guard.py`, so portability gaps are explicit rather than silently accepted.
- [x] Harness engineering is now documented and protected through [Harness Engineering](../architecture/harness-engineering.md), `manifests/harness-profiles.yaml`, `cos init-check`, `cos doctor harness`, `cos measure harness-profiles`, and `cos sprint run --dispatch`.
- [x] IDE-agnostic primitive projection is documented in [IDE-Agnostic Primitive Projection](../architecture/ide-agnostic-primitive-projection.md), clarifying canonical primitive → portable contract → harness adapter → runtime evidence and the fidelity gap between native lifecycle enforcement and structural advisory projection.
- [x] Implement ADR-256 Primitive Contract Registry and Runtime Evidence Ledger in phases: contract freeze, minimal contract registry, intervention ledger, codebase itinerary, projection-fidelity report, trace-joiner integration, and consumer UX. Plan-first docs exist in [ADR-256](../adrs/ADR-256-primitive-contract-registry-and-runtime-evidence-ledger.md), [Primitive Contract Registry Implementation Plan](../architecture/primitive-contract-registry-implementation-plan.md), and [IDE-Agnostic Primitive Documentation Review — 2026-05-09](../reports/ide-agnostic-primitive-docs-review-2026-05-09.md). OpenCode must use its native permissions/plugins (`tool.execute.before` / `tool.execute.after`) before COS invents any parallel OpenCode enforcement layer.
  - [x] Deep premise review completed in [Primitive Contract / Cross-IDE Premise Investigation — 2026-05-09](../reports/primitive-contract-cross-ide-premise-investigation-2026-05-09.md): existing ADRs contemplate the direction, but `manifests/primitive-contracts.yaml` and the runtime ledgers remain the implementation bridge.
  - [x] ADR-256 Phase 1 implemented through [ADR-257](../adrs/ADR-257-primitive-contract-registry-phase-1.md), `manifests/primitive-contracts.yaml`, and `tests/contracts/test_primitive_contract_registry.py` for the first five portable primitive contracts.
  - [x] ADR-256 operationalization closed: `scripts/primitive_projection_fidelity.py` is part of the ACC refresh lane, `primitive-interventions.jsonl` and `codebase-itinerary.jsonl` have writers/tests, `lib/trace_joiner.py` consumes both streams, and pytest no longer depends on optional `authlib` for warning-filter parsing.
  - [x] Implement [ADR-258](../adrs/ADR-258-portable-ai-overlay-for-agentic-primitives.md): generated `.ai` overlay/export surface covering all lifecycle primitives as reference rows and enriching the five ADR-257 contracts, with round-trip conformance tests before canonical migration. External due diligence is documented in [Portable AI Primitive Standards Due Diligence — 2026-05-09](../reports/portable-ai-primitive-standards-due-diligence-2026-05-09.md).
  - [x] Implement the native OpenCode starter slice: `packages/opencode-adapter/plugins/cos-primitive-guard.js`, `scripts/cos-opencode-primitive-adapter-smoke`, and [OpenCode Primitive Adapter Smoke — Latest](../reports/opencode-primitive-adapter-smoke-latest.md) promote only `destructive-git-blocker`, `destructive-rm-blocker`, `large-file-advisor`, and `skill-router`; all other OpenCode primitives remain `host-plugin-lifecycle-capable`.
- [x] Primitive authoring is guarded by `/primitive-authoring` (`skills/primitive-authoring/SKILL.md`), so new SO or consumer-project primitives must pass reuse, ownership, portable-contract, projection-fidelity, runtime-evidence, and downstream-impact checks before implementation.
- [x] Primitive portability test impact is mapped in [Primitive Portability Test Impact Review — 2026-05-09](../reports/primitive-portability-test-impact-review-2026-05-09.md), including P0/P1/P2/P3 validation bundles for contract registry, `.ai` overlay, adapters, ledgers, hooks, consumer fleet, and service/headless mode.
- [x] Consumer and service/headless proof is strengthened by [Portable `.ai` Consumer Smoke — Latest](../reports/portable-ai-consumer-smoke-latest.md) and [Primitive Service/Headless Smoke — Latest](../reports/primitive-service-headless-smoke-latest.md).
- [x] Maintainer-vs-consumer `.ai` semantics are documented in [Portable `.ai` Overlay vs Consumer `.ai` Model Impact — 2026-05-12](../reports/portable-ai-overlay-consumer-model-impact-2026-05-12.md): maintainer `.ai/` remains generated/proof-oriented while consumer `.ai/` may be README-first packaging projected from canonical contracts.
- [x] Human-readable consumer `.ai` package spec and smoke are implemented in [Portable `.ai` Consumer Package Spec](../architecture/portable-ai-consumer-package-spec.md) and `scripts/cos-portable-ai-consumer-package-smoke`; the package is Markdown-only and generated from canonical contracts/overlay data.
- [x] Add the first adapter compiler entry point for consumer-facing IDE files: `lib/adapter_compile.py`, `scripts/cos-adapter-compile`, and `cos adapters compile` preserve fidelity claims while delegating native writes to governed harness projection drivers.
- [x] Decide whether future structural rule-file backends stay first-party or use a governed `rulesync`-style backend: [ADR-272](../adrs/ADR-272-structural-rule-backend-boundary.md) keeps the first-party compiler as the authority and limits external backends to optional `structural-advisory` file emission behind COS fidelity filters.
- [x] User-facing setup messages are clear and product-grade.
- [x] `hooks/self-install.sh` meets its performance expectations.
- [x] Setup and onboarding flows have visible performance budgets and regression tests through `scripts/demo-first-run-onboarding.sh` and `tests/integration/test_first_run_onboarding.py`.
- [x] A non-expert can reach a working baseline without reading deep architecture docs through [First-Run Onboarding Proof](../manual-tests/first-run-onboarding.md).

## 6. Complexity Compression

- [x] The repo is explicitly classified into core, compatibility, extensions, and experimental zones through [manifests/product-zones.yaml](../../manifests/product-zones.yaml).
- [x] Major docs present non-core systems as optional or secondary through [README](../../README.md), [Docs Index](../README.md), and [Product Zones](../product-zones.md).
- [x] Dashboard-heavy messaging is de-emphasized in top-level product docs.
- [x] Squad and organization-heavy messaging is de-emphasized in top-level product docs.
- [x] Experimental subsystems that compete with the wedge are archived, frozen, or clearly demoted through the product-zone taxonomy and top-level docs.
- [x] A feature reality audit exists to classify core, optional, and overextended surfaces.
- [x] External infrastructure is evaluated through a lightweight/default versus optional/reference decision frame in [Tooling Stack Rationalization](../architecture/tooling-stack-rationalization.md).
- [x] Docker, Python, cloud, and reference services are cataloged in [Infrastructure Service Catalog](../architecture/infrastructure-service-catalog.md).
- [x] Local connected-system validation is documented in [Local Connected Systems Validation](../manual-tests/local-connected-systems-validation.md), including dependency manifest checks, setup profiles, MCP wiring, optional-service boundaries, and persistent test summaries.
- [x] Observability backends are evaluated through a backend-neutral event-contract decision in [Observability Backend Evaluation](../architecture/observability-backend-evaluation-2026-04-24.md).
- [x] The maintainer-agent gap is documented in [Self-Improvement Maintainer Agent Gap](../reports/self-improvement-maintainer-agent-gap-2026-05-06.md) and proposed as [ADR-201](../adrs/ADR-201-maintainer-agent-telemetry-promotion-loop.md): telemetry alone does not close the loop without a scheduled owner and `PromoteFromTelemetry` primitive.
- [x] The private-content portability gap is documented in [Private Content Cross-Harness Portability Gap](../reports/private-content-portability-gap-2026-05-06.md) and proposed as [ADR-202](../adrs/ADR-202-private-content-cross-harness-portability-boundary.md), separating public harness portability from private strategy/memory/metrics projection.
- [x] The `/auto-rollback` router false positive is documented in [Auto-Rollback Router Trigger Forensics](../reports/auto-rollback-router-trigger-forensics-2026-05-06.md), with a narrow negative-context guard and unit coverage added.
- [x] The broader skill-router false-positive cluster (`/systematic-debugging`, `/deep-research`, `/auto-rollback`, `/auto-refine`, `/self-improve`, `/phoenix-trace-ui`) is documented in [Skill Router False-Positive Cluster](../reports/skill-router-false-positive-cluster-2026-05-06.md) and covered by a generic command-mention negative-context guard with unit tests.
- [x] The confidentiality-enforcer gitignored-destination false positive is resolved in [Confidentiality Enforcer Gitignored-Destination Downgrade](../reports/confidentiality-enforcer-gitignored-downgrade-2026-05-06.md): operator absolute paths in gitignored Write/Edit targets downgrade BLOCK to WARN, while protected terms and tracked docs still block.
- [x] Subagent capability mismatch is documented in [Subagent Capability Contract Gap](../reports/subagent-capability-contract-gap-2026-05-06.md) and resolved by [ADR-203](../adrs/ADR-203-subagent-capability-contract-and-launch-preflight.md), `manifests/subagent-capabilities.yaml`, and `scripts/cos subagent preflight`.

## 7. Visible Proof

- [x] Provider compatibility is explicitly inventoried.
- [x] Provider-agnostic outcome metrics exist.
- [x] A canonical demo shows provider and harness switching without system rewrites through [Five-Minute Demo](../manual-tests/five-minute-demo.md) and `scripts/demo-portability-proof.sh`.
- [x] A canonical demo shows real quality gates in action through [Five-Minute Demo](../manual-tests/five-minute-demo.md).
- [x] A canonical demo shows the core becoming usable in minutes through [Five-Minute Demo](../manual-tests/five-minute-demo.md).
- [x] The repo contains a short proof path for “easy to adopt, serious to trust” through [Product Proof Paths](../manual-tests/proof-paths.md).
- [x] The repo contains a short proof path for resilience under ecosystem churn through [Product Proof Paths](../manual-tests/proof-paths.md).

## 8. Immediate Known Gaps

- [x] State retention automatic repair is bounded by ADR-200 through observe/repair-safe/repair-before-block modes, with smoke coverage for auto-pre-agent repair and manual-stash blocking.
- [x] State retention self-bite risk is documented and given a manifest-backed reaper protocol through [Session Diagnosis — State Retention Self-Bite Pattern](../reports/session-self-bite-pattern-2026-05-06.md), [ADR-199](../adrs/ADR-199-state-retention-policy-and-reaper-protocol.md), and `manifests/state-retention.yaml`.
- [x] Fix `README.md` reference to missing `docs/benchmark-results.md`.
- [x] Fix `CONTRIBUTING.md` references from `tests/run-all-tests.sh` to `scripts/run-all-tests.sh`.
- [ ] Redesign and re-enable `.github/workflows/ci.yml`; current repository evidence is `.github/workflows/ci.yml.disabled`, so the product-core CI claim is not complete yet.
- [x] Triage and improve `hooks/self-install.sh` performance against behavior-test expectations.
- [x] Publish a simple “core vs extension” taxonomy document or section.
- [x] Prepare a canonical five-minute product demo path through [Five-Minute Demo](../manual-tests/five-minute-demo.md).
- [ ] Reduce the full Python suite from 195 failures to zero; current evidence is tracked in [Full Suite Validation Report](../reports/full-suite-validation-2026-04-23.md).

## Preserve Branch Governance

- [x] Preserve branch diagnostic report is documented in [Preserve Branch Governance Report — 2026-05-02](../reports/preserve-branch-governance-2026-05-02.md).
- [x] ADR-110 defines preserve branch governance in [ADR-110](../adrs/ADR-110-preserve-branch-governance.md).
- [x] Preserve branch lifecycle and consumer projection are documented in [Preserve Branch Lifecycle](../architecture/preserve-branch-lifecycle.md).
- [x] `scripts/cos-doctor-preserve.sh --json` detects missing manifests, mixed scope, integrated branches, non-ancestor tips, and delete candidates.
- [x] Preserve governance behavior tests cover the required scenarios in `tests/behavior/test_cos_doctor_preserve.py`.
- [ ] Existing local `codex/preserve-*` branches have manifests or are explicitly reconciled/deleted.

## Success Signal

- [x] A new user can understand the product quickly.
- [x] A new user can install it without pain.
- [x] A new user can see real evidence of value quickly.
- [x] A new user can grow into deeper capabilities without needing agent-infrastructure expertise first.

- [x] Headless/clustered runtime direction is documented without overclaiming cluster readiness in [ADR-091](../adrs/ADR-091-headless-clustered-runtime-direction.md) and [Headless and Clustered Runtime Plan](../../.cognitive-os/plans/architecture/headless-clustered-runtime-plan.md).
- [x] Cloud/headless worker tooling research is documented in [Cloud Worker Runtime Tooling Research — 2026-05](../architecture/cloud-worker-runtime-tooling-research-2026-05.md), with lightweight queue and durable-execution options staged behind `cos run-task`.
- [x] Competitive/runtime benchmark direction is documented in [Runtime Comparison Benchmark Plan](../../.cognitive-os/plans/architecture/runtime-comparison-benchmark-plan.md), covering vanilla Claude/Codex, COS-enabled harnesses, and prior-art tools across workstation, VM, container, pod, and worker-cluster surfaces.
- [x] Competitive reassessment against OpenClaw and Hermes Agent is documented in [Competitive Reassessment: OpenClaw and Hermes Agent](competitive-reassessment-openclaw-hermes-2026-04.md), including native self-improvement, skill lifecycle, memory/profile bootstrap, and deployment/onboarding gaps.

- [x] Governed self-improvement execution plan is documented in [Governed Self-Improvement Roadmap](../../.cognitive-os/plans/architecture/governed-self-improvement-roadmap.md), and the first detect/draft/promote slice is covered by unit and behavior tests.
- [x] Primitive self-improvement promotion is now gated by baseline-vs-candidate fitness evidence through [Primitive Fitness Evaluation Contract](../architecture/primitive-fitness-evaluation-contract.md), `lib/primitive_fitness.py`, and `scripts/cos-primitive-fitness`.
- [x] Primitive fitness now reconciles consumer/downstream proposal bundles and ADR-168 dependency readiness as supporting evidence, while preventing supporting-only evidence from promoting a primitive without core runtime metrics.
- [x] Primitive fitness reports now roll up by family through `scripts/cos-primitive-fitness-ledger` and feed ACC as visibility-only capability evidence.
- [x] Memory/Profile Bootstrap now creates a local source-linked, sanitized project profile draft during the first three sessions, with manual and Go CLI generate/inspect/promote/wipe commands, doctor coverage, and Codex SessionStart tests.

- [x] Action-count rate limiting uses token buckets with soft warnings, operator reserve, and diversity penalty (ADR-101).
- [x] Audit/contract lane recovery is documented in [ADR-103](../adrs/ADR-103-audit-contract-lane-recovery.md) and [Audit and Contract Lane Recovery Plan](../../.cognitive-os/plans/archive/audit-contract-lane-recovery-plan.md), with deterministic docs debt fixed before the parallel flip.
- [x] Validation capsules are documented and implemented in [ADR-109](../adrs/ADR-109-validation-capsule-worktree-isolation.md), [Validation Capsule](../architecture/validation-capsule.md), and `scripts/cos-validation-capsule.sh`, separating release validation from the global hook killswitch.
- [ ] Adopt ADR-111 concurrency safety core/consumer boundary and keep primitive tests green (`docs/adrs/ADR-111-core-consumer-concurrency-safety-boundary.md`).
- [ ] Execute the remaining ADR implementation backlog through [ADR Implementation Closure Session — 2026-05-04](../SESSION-ADR-CLOSURE-2026-05-04.md) and [Session Handoff — 2026-05-04](../SESSION-HANDOFF-2026-05-04.md): reconcile all ADRs up to ADR-138 before implementation, then continue current cloud-flow/concurrency/stash/doc-drift closure.

- [x] ADR-119 session filesystem reaper archives stale clean session directories, preserves pending content, and emits aggregate session-volume alarms.
- [x] Boring Reliability Control Plane is documented in [Boring Reliability Control Plane](../architecture/boring-reliability-control-plane.md), with profile, preamble, default-visible, false-positive, WIP safety, recovery drill, runtime reality, and dashboard CLIs covered by unit tests.
- [x] Agentic kernel philosophy is documented in [Agentic Kernel Philosophy](../architecture/agentic-kernel-philosophy.md), establishing small-core, driver, boot-path, and evidence-backed primitive doctrine.
- [x] Expansion hardening is documented in [Expansion Hardening Plan](../architecture/expansion-hardening-plan.md) and [ADR-133](../adrs/ADR-133-expansion-without-monsterization.md), with `scripts/cos-lab-first-gate` preventing unevidenced core/team/blocking/default-on primitive promotion.
- [x] Headless self-improvement proposing is documented in [Headless Self-Improvement Proposer](../architecture/headless-self-improvement-proposer.md), [ADR-134](../adrs/ADR-134-headless-self-improvement-proposer.md), and [Headless Self-Improvement Proposer Plan](../../.cognitive-os/plans/architecture/headless-self-improvement-proposer-plan.md), with `scripts/cos-self-improvement-loop` converting audit findings into propose-only work items and `scripts/cos-self-improvement-discipline-gate` blocking default-surface inflation.
- [ ] Implement the ADR-201 maintainer-agent loop: BLOCKER SQLite-backed performance ledger with signal-quality quarantine, deterministic proposal dedup, full proposal schema, ADR-164 service-mode mutation boundary, outcome-failure protocol, model-cost policy, `PromoteFromTelemetry`, scheduled dry-run maintainer agent, cross-harness/harness-agnostic proposal output, and behavior smoke proving repeated telemetry creates one bounded human-approved proposal. Outcome-failure protocol and scheduled automation remain open; minimum propose-only loop is implemented.
  - [x] SQLite Performance Ledger substrate: `lib/performance_ledger.py`, `scripts/cos-performance-ledger`, `cos performance-ledger compile`, SQLite store, JSONL export, latest report, retention declaration, and tests proving corrupt/suspect rows do not enter eligible rollups.
  - [x] Add corrupt-ratio consumption gate and deterministic proposal id helper: blocked streams cannot feed `PromoteFromTelemetry`, and proposal identity is stable across surface + degradation pattern + day window.
  - [x] Add `lib/promote_from_telemetry.py`, `scripts/cos-promote-from-telemetry`, `scripts/cos-maintainer-agent --once --dry-run --json`, full proposal schema, propose-only ADR-164 boundary, sonnet-first model policy, and smoke tests proving one bounded human-approved proposal.
- [ ] Implement ADR-202 private-content portability: skeleton surface manifest with conservative `local-only` defaults plus `secret-never-touch`, justified elevations, class transition receipts, private-content access audit log, unknown-surface scheduled audit, projection/export guard, service/headless smoke, and provenance/redaction checks.
  - [x] Slice 2a skeleton manifest and audit CLI: `manifests/private-content.yaml`, `scripts/private_content_audit.py`, `scripts/cos-private-content-audit`, `cos private-content audit`, unit tests, and CLI smoke classify known private roots as `local-only` and secret paths as `secret-never-touch`.
  - [x] Slice 2b projection/export guard: `cos private-content check-projection PATH`, secret-never-touch hard block, local-only cloud export block, provenance/redaction policy checks, and private-content access audit metric.
  - [ ] Slice 2c justified elevations, transition receipts, scheduled unknown-surface audit, and service/headless projection smoke.
- [x] Wire ADR-203 subagent preflight into harness-native/Agent launch paths through `hooks/subagent-capability-preflight.sh`, active Claude settings, standard/paranoid profiles, registration allowlist, telemetry, compact block output, and behavior tests.
- [x] Implement ADR-204 reward-signal quality boundary for maintainer consumption so dirty trust scores and corrupt skill-feedback rows cannot drive Performance Ledger or Maintainer proposal decisions. Router/skill lifecycle consumption remains covered by future ADR-207 slices.
  - [x] Add reward-signal contract, validator, audit CLI, route smoke, and tests proving `skill: matias` and default trust score 75 without evidence are quarantined from rollups.
  - [x] Feed ADR-204 quality counts into ADR-201 Performance Ledger so corrupt/suspect rows are excluded from rollups.
  - [x] Block `PromoteFromTelemetry` consumption above corrupt-ratio policy via Performance Ledger `consumption_policy` and `--require-consumable` CLI gate.
- [x] Implement ADR-205 run flight recorder substrate before treating service-mode observability as complete: `lib/trace_joiner.py`, `scripts/cos-run-trace`, `cos observe run`, run-id/event-id normalization, latest run report, JSONL index, state-retention declarations, and tests proving private-content payloads stay ref-only.
- [x] Implement ADR-206 public claim gate and purge/demote unbacked autonomous/MAPE-K/self-improvement claims before public launch.
- [x] Implement ADR-207 skill performance ledger substrate before claiming skill self-improvement; router override events and rewrite proposals remain follow-up slices.
- [x] Adopt ADR-212 cross-stack license audit toolchain: Syft+Grype primary, Trivy guarded secondary, workflow safety gate, install/run wrappers, and tests.
- [x] Fix ADR-213 Agent hook ordering so blocking preflight runs before stash snapshot, preventing hidden WIP after blocked launches.
- [x] Implement ADR-216 Tool Discovery Pre-Use Gate so ad-hoc license/repo tool choices are blocked or warned when COS primitives exist.
- [x] Implement ADR-219 work ownership liveness preflight so preserved branches, stashes, linked worktrees, claims, and process activity are joined before cleanup/closure claims.
- [x] Implement ADR-208 imported-pattern closure audit so producer-only imports cannot be promoted as active loops.
  - [x] Wire the first consumer loop: dependency manifest additions now hit a pre-commit dependency-adoption gate and require staged `/repo-scout`, `/repo-forensics`, or equivalent evidence before adoption.
  - [ ] Add the full imported-pattern closure manifest/audit that proves producer, consumer, scheduler, evaluator, owner, demotion path, and contract tests before promotion claims.
- [x] Implement ADR-209 maintainer experiment contract before executable maintainer changes.
- [ ] Keep ADR-210 fleet confidence as future/cloud-only until ADR-202 sanitized-export and provenance are enforced.
- [x] Implement ADR-211 initial service-mode readiness gate before any standalone/cloud autonomy launch claim: `lib/service_mode_readiness.py`, `scripts/cos-service-readiness-gate`, `cos service readiness`, JSON/compact output, and tests proving missing private-content/trace/ledger gates fail red. ADR-209 executable experiment contract is now green at schema/evaluator level; executable Maintainer changes still require proposal integration and canary slices.
- [x] Self-evolving doctrine proposals are documented in [Self-Evolving Doctrine Proposals](../architecture/self-evolving-doctrine-proposals.md) and [ADR-135](../adrs/ADR-135-self-evolving-doctrine-proposals.md), with `scripts/cos-doctrine-proposer` generating proposed, non-runtime doctrine amendments from control-plane evidence.
- [x] Cross-instance learning runway is documented in [Cross-Instance Learning Runway](../architecture/cross-instance-learning-runway.md) and [ADR-136](../adrs/ADR-136-cross-instance-learning-runway.md), with consumer evidence exchange, deterministic registry locks, propose-only Engram bundles, and Shape-B federation trigger audit.
- [x] Consumer fleet audit is documented in [Consumer Fleet Audit](../architecture/consumer-fleet-audit.md) and exposed through `scripts/cos-consumer-fleet-audit`, joining registry/install metadata, registry-lock drift, claim-signature status, and targeted validation lanes without mutating consumer projects.
- [x] Cross-instance local consumer E2E is documented in [Cross-Instance Consumer E2E Drill — 2026-05-03](../reports/cross-instance-consumer-e2e-2026-05-03.md), proving install, provenance export/import, drills, and that self-owned evidence does not sign external-help claims.

- [x] Expected test skips are classified and enforced through ADR-166, `manifests/test-skip-registry.yaml`, and the pytest summary wrapper so new unclassified skips fail instead of silently growing.

- [x] ADR-218 history sanitization dry-run substrate exists (`cos history sanitize --dry-run --json`); execute rewrite remains operator-gated.

- [x] ADR-217 adoption-truth substrate exists (`cos adoption audit --json`); readiness/downstream consumption and baseline remediation remain pending.

## 9. Orchestration Coverage Substrate (line of work landed 2026-05-06/07)

> Disparada por la pregunta del operador *"¿estamos cubriendo todo lo que cubren los demás en sus versiones más recientes?"*. 79-source prior-art research + 11 reportes paralelos por gap + síntesis ranqueada → 14 ADRs (220–236, ADR-229 tombstone) drafted + Slice A implemented en ~24h. Detalle completo en [SYNTHESIS-2026-05-06.md](../research/orchestration-gaps/SYNTHESIS-2026-05-06.md) y [IMPLEMENTATION-CHECKLIST-2026-05-07.md](../research/orchestration-gaps/IMPLEMENTATION-CHECKLIST-2026-05-07.md).

### 9.1 Evaluation contract

- [x] C1–C4 evaluation contract promoted from chat directives to canonical manifest at [`manifests/orchestration-research-evaluation.yaml`](../../manifests/orchestration-research-evaluation.yaml) — `schema_version: orchestration-research-evaluation/v1`. License allowlist/blocklist, 4 footprint surfaces, T1–T10 with smoke non-negotiable + measure-first T6 caveat, verdict block schema with 6 required fields.
- [x] Substrate-consumer guardrail validator at [`scripts/validate_substrate_consumers.py`](../../scripts/validate_substrate_consumers.py) — 14 checks across 6 dimensions (schema-version invariant, projection robustness, strict-durability required-for, seq type, perf budget liveness, substrate-truth sanity). Result on 2026-05-07: **14/14 PASS**.

### 9.2 Substrate (Tier 1 — load-bearing)

- [x] **ADR-220** Worktree Divergence Audit — `lib/worktree_audit.py` + `cos worktree audit --json [--strict]` + manifest. Accepted, preflight/readiness gate active.
- [x] **ADR-221** Stash Refs by SHA, Not by Position — `lib/stash_sha.py` + marker schema v2 + CI audit tests. Accepted, slice 1 active.
- [x] **ADR-222** Pre-Agent Stash Two-Phase Capture — `agent-launch-confirmed.sh` + plan-only PreToolUse + cleanup. Slices 1–8 implemented (tactical mitigation until ADR-223 fully replaces).
- [x] **ADR-223** Agent Lifecycle Reconstruction (kill auto-pre-agent-stash, worktree-per-write-agent + mutex on `git worktree add`) — `lib/agent_lifecycle.py` + default-on worktree lifecycle + manifest-scoped cleanup/reaper + cross-harness projection + branch-prefix support. Slices A–D implemented.
- [x] **ADR-226** Event-Sourced Session Bus (load-bearing) — `lib/session_bus.py` (extends ADR-205 Flight Recorder) + `lib/event_wrap.py` + `lib/event_projections/{cost_ledger,handoff_chain,retry_classifier,timeline}.py` + per-session JSONL streams + manifest with measured p95_budget_ms. Slices A–E implemented.
- [x] **ADR-227** Shadow-Git Checkpoint Substrate — `lib/shadow_git.py` + `cos rollback` CLI + off-repo snapshots + preview-gated files restore + conversation truncation + atomic files+conversation restore + event-envelope `file_tree_sha` wiring. Slices A–F implemented.
- [x] **ADR-228** Retry Contract + Cost Session Budget (consolidated G8+G10) — `lib/dispatch_gate.py` + `lib/retry_classifier.py` + `lib/session_budget.py` + idempotency mixin + circuit breaker + provider-aware cost predictor + T6 perf baseline + T7 circuit recovery chaos. Runtime closed.
- [x] **ADR-230** Handoff Envelope + Cycle Deduplication — `lib/handoff_envelope.py` + `lib/handoff_dispatcher.py` + permission intersection + ADR-233 inbox transport + explicit receiver execution + external hook runner via `--hook-command` + timeout/failure receipts + SIGKILL/timeout chaos receipts + idempotent skip after failure. Runtime receiver closed.

Pendings remaining (called out per ADR by [`IMPLEMENTATION-CHECKLIST-2026-05-07.md`](../research/orchestration-gaps/IMPLEMENTATION-CHECKLIST-2026-05-07.md)):

- [ ] T6 perf budget hardening across substrate (Linux/Docker baselines pending; macOS+APFS baseline at p95 25 ms locked in manifest; ADR-228 T6 done)
- [ ] T7/T10 chaos and audit invariants partial (event-bus chaos covered; ADR-227 T7/T10 partial; ADR-228 chaos done; some downstream consumers pending)
- [ ] T8 cross-harness end-to-end for some consumers (event bus covered via `tests/red_team/portability/test_event_bus.py`; ADR-230 T8 done; ADR-231 T8 done)

### 9.3 Consumers (Tier 2)

- [x] **ADR-225** Branch-Per-Task Mode — `lib/branch_task_policy.py` + conditional prelaunch enforcement + ADR-235 auto-branching via `--prepare-worktree` default `codex/task/*` prefix. Slices A–C implemented.
- [x] **ADR-231** MCP Server Surface — FastMCP-based 8-tool server + optional OTel spans + stdio + Streamable HTTP registration plans + trust-pin-required URL consumption fingerprints. Slices A–C implemented.
- [x] **ADR-233** Cross-Session Agent-Team File-IPC — `lib/agent_team.py` + `cos team ...` CLI + TaskCreated/TaskCompleted/TeammateIdle hooks + ADR-230 receiver flow + chaos claim race + cross-harness inbox + opt-in NATS publish adapter + A2A HTTP JSON adapter + `transport-send` CLI. Transport adapters closed.

### 9.4 Opt-in adapters (Tier 3)

- [x] **ADR-224** Shadow-State Snapshots Off-Repo — off-repo shadow-git safety net + operator rollback runbook + manual retention/reaper via `cos rollback --prune`. Slices A–C implemented.
- [x] **ADR-232** Sandbox Adapter Tiers (Bubblewrap Linux / Seatbelt macOS, OS-native default) — `lib/sandbox_adapter.py` + dispatch `require_sandbox` preflight + Claude CLI/provider subprocess wrapping + microVM/ConTree adapter contracts + opt-in runner-backed CLI execution. Slices A–E implemented.
- [x] **ADR-234** Approval Policies as Code — `lib/policy_eval.py` + YAML evaluator + CLI + destructive/protected-config policies + two real hook migrations + plan-only Claude/Codex settings projection. External engines deferred. Slices A–C implemented.
- [x] **ADR-235** Detached Agent Daemon — `lib/agent_daemon.py` + queue/state + tmux launcher + sentinels + watchdog + budget gate + TeamTask enqueue + service-plan/install + activation helper + tmux/process-tree kill escalation. Slices A–F implemented.
- [x] **ADR-236** Deferred Tool Loading + ToolSearch — `lib/deferred_tool_loading.py` + manifest-backed planning + ToolSearch index + dispatch insertion/metrics + local `list_changed` state + truthful provider-native payloads with operator-enabled native API switch. Slices A–D implemented.

Pendings remaining (called out per ADR by [`IMPLEMENTATION-CHECKLIST-2026-05-07.md`](../research/orchestration-gaps/IMPLEMENTATION-CHECKLIST-2026-05-07.md)):

- [ ] ADR-232 T7/T8/T10 hardening (chaos + cross-harness + audit invariants extension)
- [ ] ADR-234 T5/T8 hardening (adversarial + cross-harness)
- [ ] ADR-235 T10 audit invariants partial
- [ ] ADR-236 T9 adoption-truth re-run with FastMCP / OTel MCP semconv

### 9.5 Tombstone

- [x] **ADR status taxonomy** — `docs/adrs/STATUS-TAXONOMY.md` separates decision status, implementation status, and index bucket; ADR-044/132/174b/174c/238/253 are canonical fixtures.
- [x] **ADR-229** consolidated into ADR-228 (cost-budget + retry-contract on the same code path).

### 9.6 Conscious non-coverage (do not pursue this cycle)

- [x] Multi-machine cloud orchestration documented as positioning, not a gap.
- [x] CRDT-based merging documented as anti-recommendation (code is non-commutative).
- [x] Hypervisor sandboxes (Firecracker) as primary documented as opt-in tier only (E2BAdapter via ADR-232).
- [x] OPA/Rego policy engine documented as deferred until multi-tenant deployment.
- [x] Mid-session MCP server injection documented as upstream "not planned"; deferred-loading covers ~85%.
- [x] Temporal/Cadence durable workflows documented as heavy-dep violation of C2; `@event_wrap` covers MVP determinism.
- [x] NATS JetStream cross-session bus documented as Tier-3 future, not default.

### 9.7 Ledger / business-doc downstream impacts

- [x] Strategy private log [`04-license-repo-and-corrections-log.md`](../../.cognitive-os/strategy/04-license-repo-and-corrections-log.md) — Anexo with full orchestration-line narrative + 5 new commercial-grade cuñas.
- [x] Strategy research/09 dogfood metrics — §7 added with 8 reproducible orchestration-line metrics.
- [x] Strategy 03-self-bite-pattern — marked CLOSED 2026-05-07 with chain of resolving ADRs.
- [x] Strategy 01-commercial-brief-v2 — patched §2/§5/§7/§9/§12 + new §16 with 5 cuñas + post-landing fold rotation.
- [x] Public docs/business/value-proposition — added 4 new "What It Does" entries + "upstream gaps" table linking each ADR to its issue/limitation.
- [x] Public docs/business/features — Feature Overview 13→19 + new sections §6/§7/§8 (replay, cost+retry, handoff).
- [x] Public docs/business/roadmap — Current State counts refreshed; "What works end-to-end" expanded with 5 new shippables.
- [x] Public docs/business/executive-summary — Problem section expanded with replay-Devin-framing and $47K-incident framing.

- [x] **ADR-279** Orphan Repo-Scan Process Audit — `scripts/cos-orphan-process-audit.py` + `lib/orphan_process_audit.py` detect stale PPID=1 Claude/zsh/grep-style repo scans, stay dry-run by default, require explicit `--kill`, and carry behavior tests.
