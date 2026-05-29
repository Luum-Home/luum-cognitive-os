# Changelog

All notable changes to Cognitive OS are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

## [0.29.14] - 2026-05-29 — "Release Gate Audit Fixes"

### Fixed
- Renamed the integration lane coverage checker to `scripts/check_integration_lane_coverage.py` to satisfy the repository snake_case Python script rule.
- Updated the hook functional-audit scorecard to account for `session-quality-close-gate.sh`.

### Validation
- `scripts/cos-test-repair-loop --full-command "make test-laptop" --timeout-seconds 2400 --require-clean-start` exposed the two audit regressions fixed in this release.
- `tests/audit/test_hooks_contracts.py::test_hook_counts_match_scorecard`, `tests/audit/test_python_naming.py::test_scripts_are_snake_case`, and `tests/unit/test_integration_lane_coverage.py` passed.
- `scripts/cos-patch-release validate` passed.

## [0.29.13] - 2026-05-29 — "Root Test Contract Hardening"

### Added
- Added `cos derive check|sync` to centralize generated-artifact verification and projection sync.
- Added formal `cos-test quarantine audit` with an expiring `.cognitive-os/test-quarantine.yaml` manifest.
- Added integration lane coverage, failure classification, and reliability ledger primitives for test drift triage.
- Added `session-quality-close-gate.sh` to block session close when quality/verification metrics contain explicit failing evidence.

### Changed
- Hardened `cos-test broad --json --strict` with semantic lane classes and machine-readable summaries.
- Extended release doctor with `--strict --contract-only` so CI can enforce release contracts without non-idempotent publish checks.
- Split the remaining non-Docker integration surface into an explicit `integration-core` environmental lane.

### Validation
- `scripts/cos-patch-release doctor --version 0.29.13 --strict --contract-only --json` passed.
- `scripts/cos-patch-release validate` passed.
- Targeted Go and Python release/hook/portability tests passed.

## [0.29.12] - 2026-05-29 — "Release Test Contract"

### Added
- Added the `cos-patch-release` primitive for repeatable patch release preparation, validation, publishing, and diagnostics.

### Validation
- `scripts/cos-patch-release validate` is the required patch-release validation lane.

## [0.29.11] - 2026-05-28 — "Root Test Lane Stabilization"

### Fixed
- Routed `research-compliance-guard.sh` through the default Bash hot-path dispatcher while keeping it in the full Claude profile mesh, preventing profile/baseline drift and preserving the one-dispatcher default hot path.
- Hardened `cos-doctor-harness.sh` against poisoned project-root environment variables and made self-host adapter readiness fail when shipped adapters are not `ok`.
- Restored deterministic integration behavior by preventing `cos_watch` imports from leaking `COGNITIVE_OS_PROJECT_DIR` into later subprocess tests.
- Aligned live host-pressure integration assertions with the documented `HostMonitor` thresholds.
- Classified integration skip reasons for optional live services and bootstrap preconditions so broad lanes fail only on unknown skips.

### Validation
- `./cos-test cluster --lane unit --ci` passed: 11435 passed, 73 skipped, unknown_count=0.
- `./cos-test cluster --lane integration --ci` passed: 898 passed, 31 skipped, unknown_count=0.
- Prior broad run passed all other non-resource-blocked lanes; Docker/cost-bearing lanes remained intentionally skipped by resource policy.

## [0.29.10] - 2026-05-28 — "Consumer governance projection fixes"

### Added
- Added the `cos-patch-release` primitive for repeatable patch release preparation, validation, publishing, and diagnostics.

### Validation
- `scripts/cos-patch-release validate` is the required patch-release validation lane.

## [0.29.9] - 2026-05-27 — "Default Research Compliance Guard"

### Added
- Added the `cos-patch-release` primitive for repeatable patch release preparation, validation, publishing, and diagnostics.

### Validation
- `scripts/cos-patch-release validate` is the required patch-release validation lane.

## [0.29.8] - 2026-05-27 — "Go 1.26.3 Toolchain Alignment"

### Added
- Added the `cos-patch-release` primitive for repeatable patch release preparation, validation, publishing, and diagnostics.

### Validation
- `scripts/cos-patch-release validate` is the required patch-release validation lane.

## [0.29.7] - 2026-05-27 — "Patch Release Primitive"

### Added
- Added the `cos-patch-release` primitive for repeatable patch release preparation, validation, publishing, and diagnostics.

### Validation
- `scripts/cos-patch-release validate` is the required patch-release validation lane.

## [0.29.6] - 2026-05-27 — "Locked Release Dependency Sync"

### Fixed
- Updated `uv.lock` for the release version and changed CI dependency setup to use `uv sync --extra testing --locked`, preventing GoReleaser from seeing a dirty `uv.lock` after validation.

### Validation
- Release run `v0.29.5` passed validation and failed only because `uv sync` dirtied `uv.lock` before GoReleaser.

## [0.29.5] - 2026-05-27 — "Patch Release Workflow Stabilization"

### Fixed
- Switched `cos-binary-release` validation to a patch-release smoke lane covering the local privacy guard and `cmd/cos` tests before GoReleaser.
- Fixed the `scope-portability` workflow to run tests from the repo `.venv` created by `uv sync --extra testing`, matching the repository test harness contract.

### Validation
- Release runs `v0.29.3` and `v0.29.4` exposed CI bootstrap and broad-lane dependency/state drift before GoReleaser.
- Local patch-release validation passed before tagging this release.

## [0.29.4] - 2026-05-27 — "Release CI Dependency Bootstrap Fix"

### Fixed
- Fixed the `cos-binary-release` workflow by installing Python test dependencies with `uv sync --extra testing` before running `make test-laptop`.

### Validation
- Release run `v0.29.3` reached the workflow and failed in `Validate release lane` because `python3 -m pytest` was unavailable on the GitHub runner.
- Local targeted privacy guard validation remained green before this patch.

## [0.29.3] - 2026-05-27 — "Local Privacy Guard Patch"

### Added
- Added `scripts/check-local-privacy.sh` as a reusable local privacy guard for staged and full-repo scans.
- Added a gitignored local pattern workflow via `.cognitive-os/private/local-privacy-patterns.txt` and the safe template `templates/local-privacy-patterns.example.txt`.
- Added `rules/local-privacy-hygiene.md` and unit coverage for staged blocking, private pattern configuration, allow markers, pre-commit wiring, and full-repo scans.

### Fixed
- Wired `.githooks/pre-commit` to block local privacy leaks before commits, reducing the chance of committing developer home paths or operator-specific project/user identifiers by accident.

### Validation
- `bash -n scripts/check-local-privacy.sh .githooks/pre-commit` passed.
- `scripts/check-local-privacy.sh --root . --all` returned `privacy-guard-ok`.
- `.venv/bin/python -m pytest tests/unit/test_check_absolute_paths.py tests/unit/test_check_local_privacy.py tests/red_team/portability/test_check-local-privacy.py tests/red_team/portability/test_local-privacy-hygiene.py -q` passed.
- `scripts/cos-scope-both-portability-audit --strict` and `scripts/cos-scope-projection-audit --strict` passed.

## [0.29.2] - 2026-05-22 — "Token Budget Fast Path and Evidence-Grounded Context Savings"

### Added
- Added a micro skill catalog and runtime compact config generation path so session start and prompt preambles can load smaller context surfaces.
- Added an anonymized token-savings Q&A, paired benchmark protocol, and live anonymized paired-run receipt for evidence-grounded operator claims.
- Added a read-only anonymized token-savings audit script with unit and red-team coverage.

### Changed
- Switched the context-budget meter hook to a stdlib fast path that preserves budget enforcement while reducing hot-path Python/YAML overhead.
- Tuned session-start and preamble budget reporting around the micro catalog and runtime compact config projections.

### Validation
- `python3 -m pytest tests/unit/test_catalog_loading.py tests/unit/test_runtime_compact_config.py tests/unit/test_token_savings_audit.py tests/contracts/test_context_budget_hook_wiring.py tests/red_team/portability/test_context_budget_meter_fast.py tests/red_team/portability/test_cos-token-savings-audit.py tests/red_team/portability/test_generate_runtime_compact_config.py -q` passed before release prep.
- `python3 scripts/derived_artifact_gate.py` passed before merging the token-savings evidence to `main`.

## [0.29.1] - 2026-05-20 — "Laptop Lane Stability, Runtime Closure, and Package Patch Release"

### Fixed
- Stabilized `make test-laptop` after full-lane failures by repairing provenance idempotence, MCP unit semantic-routing timeouts, install-skill fixture isolation, primitive readiness artifacts, Wave 5 residual audits, secret hook contracts, and governance-policy portability proof.
- Hardened aspirational audit contracts against xdist/live-worktree contamination by running the contract on an isolated `git archive HEAD` snapshot and extending the contract timeout.
- Fixed runtime dependency closure false positives by treating shell assignment path mentions as non-executable references.
- Repaired package/runtime audit classification for direct embedded Python imports in shell scripts.

### Changed
- Refreshed primitive readiness ledgers and primitive harness coverage artifacts after the latest primitive governance changes.
- Promoted `hooks/_lib/governance-policy.sh` to shared `SCOPE: both` with explicit portability proof.

### Packages
- Released 31 package patch tags for changed extension packages, including `@luum/agent-lifecycle@1.2.1`, `@luum/quality-gates@1.2.1`, `@luum/scope-governance@1.2.1`, `@luum/skill-governance@1.2.1`, and `@luum/verification-audit@1.2.1`.

### Validation
- `scripts/cos-test-repair-loop --full-command "make test-laptop" --timeout-seconds 2400 --require-clean-start` passed on 2026-05-20 with `TEST_REPAIR_LOOP_PASS`.

## [0.29.0] - 2026-05-18 — "Primitive Scope Discipline, Deterministic Quality Gates, and Wave 3 Runtime"

### Fixed
- Stabilized Agent PostToolUse latency validation by demoting superseded legacy verification hooks from active Claude projection and adding cheap no-op paths for completion/review hooks.
- Hardened F1 integration shard execution to allow `COS_TEST_PYTHON` when local shells do not have `uv` or compatible `python3` dependencies.
- Aligned integration tests with current copy-plan snapshot semantics and public-launch privacy placeholder expectations.

### Added

- Added `adversarial-review-gate` and `decision-depth-gate` PostToolUse hooks, converting agent-instruction quality rules to deterministic hook enforcement.
- Added `developer-as-orchestrator.md` and `maintainer-philosophy.md` concept docs.
- Added five product Q&A cards to `manifests/product-question-bank.yaml`: `value_proposition`, `who_is_it_for`, `stack_agnostic`, `codebase_scale`, `onboarding`.
- Reclassified 134 hooks and 45 skills from `SCOPE: both` to `SCOPE: os-only` via content audit; 26 package-layer hooks and 48 skills remain `SCOPE: both` as verified portable primitives.
- Added F1 laptop integration sharding via `scripts/cos-integration-shard-plan`, `make test-laptop-integration-plan`, and `make test-laptop-integration-shard`.
- Added Wave 2 post-M1 opt-in memory retrieval modes: dual-level scoring, Personalized PageRank, memory-class overlay, and hybrid scoring.
- Added opt-in bubblewrap seccomp command construction plus strict profile manifest; default sandbox behavior remains namespace-only.
- Added Wave 3 initial runtime slices: repo-map context selector, optional DSPy structured-skill pilot seam, and vendored agentapi msgfmt golden fixtures with MIT provenance.
- Added the H6 skill-description migration/check script, enforced `description: "Use when…"` across SKILL.md frontmatter, and refreshed the compact skill catalog.
- Added the Engram Wave 2 M1 additive schema migration helper for `valid_from`, `valid_to`, `memory_class`, and `source_episode` while preserving `strategy=current` defaults.
- Added local ToolSearch token-delta metrics, dispatch metric emission, and `cos-deferred-tool-plan --token-delta` to replace the prior measured-vs-claimed gap.
- Added the bubblewrap seccomp threat model and opt-in rollout criteria before implementing any BPF profile.

### Changed

- Language-agnostic semantic routing now uses embeddings against `description`+`summary_line` fields (multilingual-e5-large, ADR-296/298); language dependence audit reports 0 actionable findings.
- Synced the radar implementation tracker after `v0.28.0`: C1-C4 adoption cleanup is now audit-pass, and post-0.28 priorities are explicit for H6, Wave 2 M1, ToolSearch metrics, seccomp, Wave 3, and public launch.

### Goal-Loop Feature Ship

- Added native goal-stop contract: operator sets `--goal` before session; evaluator checks evidence at each agent stop; budget enforcement (`cos goal set/status/clear` CLI). (a07d8071 — core primitives)
- Added Stop hook + harness adapter for goal-loop evaluation gate. (2bb12748)
- Added operator rule and concept page documenting the goal-loop design and operator contract. (d4bbfada)
- Archived SDD change for goal-loop after full apply-verify cycle. (fb24ec50)

### Goal-Loop Hardening (S1/S2)

- Hardened goal-stop to fail-CLOSED on budget or evaluator errors when an active goal is set (S1-1): previously a failed evaluator silently continued execution. (3cb849da)
- Made `evaluate` read-only — evaluator command execution no longer modifies repository state (S1-2). (6b12f4c4)
- Added Codex Stop-hook detection so goal evaluation fires correctly in non-Claude harnesses (S1-3). (625215c8)
- Added deterministic concurrent-writer lock test to close race condition in goal-state persistence (S1-7). (7690da12)
- Bounded dispatch-metrics read to prevent unbounded file growth during long sessions. (031fc38a)
- Preserved cumulative dispatch budgets across evaluator invocations so multi-step goals do not reset token accounting (S2-1). (dfaf8654)
- Hardened evaluator command execution to prevent injection and improve error reporting (S2-2). (92f01925)
- Added regression tests covering S2-1 and S2-2 evaluator hardening scenarios. (bd4ce3a3)

### License Clarification

- Clarified README and docs wording from "Open-Source Core" to "Source-Available Core" to accurately reflect the FSL-1.1-MIT license posture. LICENSE file text is unchanged; FSL-1.1-MIT → MIT (after Change Date) remains authoritative. (09f9ec96)

### English-Only Audit Cleanup and Disclosure

- Removed English-language trigger phrases from `session-report` skill (5099fad0) and `product-answer` skill (25383cb6) as part of the language-dependence audit; multilingual RUNTIME routing (multilingual-e5-large embeddings) is preserved.
- Preserved multilingual capability chain: semantic matcher (743a4701), enrichment pipeline (94ee1272), router (e9fdac50), multilingual corpus (125c0f4b), multilingual fixtures (08bc5f46), and multilingual benchmark (cb8fab35) — routing operates on embeddings, not keyword triggers.
- Disclosure: a CATALOG-COMPACT edit was included in commit 44513883 without explicit operator sign-off; this was documented and retained (not reverted) in 2558d6f3. Operator awareness confirmed post-facto.

## [0.28.0] - 2026-05-10

### Added

- Public history-sanitization disclosure package documenting the pre-public rewrite scope, preserved human authorship, preserved Apache-to-FSL license-transition evidence, and sanitized runtime report copy.
- Public-launch transparency package: `TRANSPARENCY.md`, launch-day runbook, and verify-public-release guide.
- External tools radar 2026-05-08 edition with chronological index, bidirectional cross-check axis, five focused cross-check reports, implementation tracker, and reassessment scope controls.
- OpenSage ADK radar addendum and tech-radar ASSESS entry after deep staged analysis; keeps OpenSage pattern-only because dynamic tool creation, sandbox backends, graph-memory retention, and pre-release runtime maturity need COS wrappers first.
- TaskingAI radar addendum and tech-radar HOLD entry after deep repo-scout/repo-forensics pass; keeps TaskingAI pattern-only because upstream activity is stale and CI is red.
- Langflow radar addendum and tech-radar EVALUATE entry after deep staged analysis; keeps Langflow pattern-only because direct runtime adoption would import dynamic code execution, credential/env, storage, telemetry, and MCP blast-radius risks.
- External Tool Intelligence Plane (ADR-254): central adoption doctrine, project overlay model, adoption manifest, inventory/audit/render/research-check CLIs, and tests for COS-vs-project contradictions.
- Feature-to-External-Tool Due Diligence (ADR-255): feature/tool scan, external source fetch, feature-vs-tool benchmark, source-cache guard, and manifest-backed BUILD-vs-ADOPT evidence requirements.
- Capability and feature reality surfaces: feature reality matrix, capability coverage artifacts, and adapter-boundary audits for orchestration and router subsystems.
- Primitive behavioral proof audit to catch overfit tests that only prove file existence or manifest wiring instead of fail-closed behavior.
- Control-plane remediation loop (ADR-248): hook-fast lane, hourly/session-end lane, latest report, metrics, remediation queue, and safe-class auto-fix substrate.
- Release transaction freeze substrate (ADR-246) for high-risk operations such as history rewrites, force-pushes, and public-release preparation.
- Postmortem regression and primitive-coherence audits (ADR-239 through ADR-245) covering branch-shift, recursion boundaries, bypass resolver consistency, release-freeze boundaries, claim verification, and production-source read guards.
- Tiered cleanup primitive (`scripts/cos-cleanup.sh` and session-end cleanup hook) for stale locks, temporary validation capsules, merged branches, orphan worktrees, and daemon cleanup with risk-tier separation.
- Pre-public risk audit and consumer/project residue audit for sensitive blobs, internal trailers, provider-looking identities, disclosure gaps, and license FAQ readiness.
- History sanitization execute slice (ADR-218): git-filter-repo wrapper with recovery mirror, tombstone/report generation, bounded scans, tombstone smoke test, and runbook.
- Supply-chain release artifacts: CycloneDX SBOM, supply-chain audit, digest notes, and sanitized SBOM path/checksum refresh.
- License FAQ and readiness documentation for the Apache 2.0 to FSL-1.1-MIT transition, including badge/readme linkage and legal provenance evidence.
- Orchestration runtime substrate wave: event bus consumer guardrail, dispatch retry/budget/circuit-breaker hardening, handoff receiver hardening, MCP streamable HTTP registration with trust pins, sandbox adapter tiers, policy-as-code projection, detached agent daemon activation, deferred tool loading payload switch, shadow-git restore, shadow-state retention, branch-per-task/worktree lifecycle, and orchestration coverage checklist.
- Test execution efficiency protocol to avoid wasteful full-suite reruns during grouped repair cycles.
- Memory Wave 2 Slice 0: retrieval benchmark manifest, fixtures, runner, baseline report, strategy comparison runner, and five comparable retrieval reports.
- Memory Wave 2 runtime opt-in: M1 temporal validity / supersession-aware reranking and M3 relation support-chain annotations behind `retrieval_strategy="wave2-m1-m3"` or `COS_ENGRAM_RETRIEVAL_STRATEGY=wave2-m1-m3`; `strategy=current` remains default.
- Memory Wave 2 default decision record documenting why M1 stays opt-in until the remaining multi-hop/source-support blocker is closed.
- Primitive observability/portability/contracts wave: portable-AI observable overlay, primitive contract registry phase one, runtime evidence dashboard, observable overlay UX, primitive authoring gate, portability test impact mapping, lifecycle registry release seal, observable release proof, and portable standards due-diligence + authoring-plan documentation.
- Consumer fleet status panel for cross-project audit visibility, plus consumer-leakage cleanup that removes operator/project specifics from core primitive surfaces.
- Pre-launch history audit tooling (SHA inventories, manifest snapshots, pre/post-rewrite remote/upstream verification) so routine audits do not require re-running filter-repo.
- Self-programming primitive patterns documentation and OpenCode primitive projection path notes.
- Tech radar additions: OpenSwarm, EvoSkill, and agno (deep evaluation + radar addendum + index) — extends the prior OpenSage/TaskingAI/Langflow review to the broader consumer-AI surface.
- Portable primitive tool radar entries linking observable-AI manifests and the primitive contract registry to external candidates.

### Changed

- Ratified the adopt-before-build posture: COS should integrate commodity third-party schemas/runtimes behind adapter boundaries while keeping governance semantics first-party.
- Reframed external-tool research as a central COS radar plus lightweight project overlays instead of duplicating deep-research structures inside every consumer project.
- Promoted documentation-before-implementation for radar-derived work: doctrine, design docs, manifests, audit tests, and benchmark receipts must exist before runtime adoption.
- Updated the radar implementation tracker to reflect Wave 1 housekeeping, drift fixes, cleanup tasks, Wave 2 benchmark status, runtime M1/M3 opt-in status, and remaining PPR/schema work.
- Preserved commit author metadata by default in history sanitization; metadata rewrite now requires explicit opt-in flags instead of being implied by content cleanup.
- Made commit provenance trailers opt-in and added guards against invented AI-provider identities or placeholder authors.
- Defaulted agent lifecycle work toward isolated worktrees/task branches and explicit branch-switch blocking instead of silent branch context changes.
- Downgraded or tombstoned stale ADR claims where manifests or docs implied implemented behavior without consuming runtime code.
- Qualified token-reduction claims as upstream figures unless local ToolSearch metrics exist.
- Restored and clarified supply-chain digest notes after SBOM sanitization.
- Hardened context-rot controls so context-budget meters and staleness invariants enforce stricter ceilings under primitive-portability load.
- Aligned the itinerary hook event across the canonical settings driver, the cognitive-os.yaml registry, and the projected `.claude/settings.json` / `.codex/hooks.json`.
- Verified primitive documentation alignment across docs/manifests/scripts so observable-portability claims map to runtime evidence.
- Neutralized package-metadata commit messages during the public-launch history rewrite while preserving the Apache-2.0 to FSL-1.1-MIT transition explanation in `docs/09-Quality/legal/license-faq.md` per ADR-218 transparency posture.

### Fixed

- Closed control-plane audit registry drift and hook classification projection gaps so active/manual/deprecated hook states match registration reality.
- Blocked silent `git switch` / branch checkout context changes from agents unless explicitly bypassed.
- Fixed pre-public audit provider-identity false positives by matching real email-shaped identities instead of Markdown tables such as `active <30d`.
- Fixed cleanup safety so orphan worktrees with uncommitted WIP escalate to manual Tier 3 instead of being removed by Tier 2.
- Fixed release/history rewrite readiness issues: remote restoration, public rewrite identity configuration, X-COS trailer stripping, collision bypass audit, and post-rewrite remotes.
- Fixed privacy/readiness artifacts by avoiding raw operator email/path leakage, moving private tokens to operator-owned files, deriving session directory slugs at runtime, and genericizing consumer/service fixtures.
- Fixed ADR and readiness status drift, including ADR-228 header inconsistency and ADR-238 hook registration follow-up status.
- Fixed test-laptop/unit-lane readiness regressions, suspicious skip classification, hook timing count noise in validation capsules, primitive lifecycle/coverage baseline drift, and snapshot restore tracked-plan baselines.
- Fixed dependency/adoption contradictions by removing direct `litellm`, `langfuse`, `memu`, and `pytest-smell` references that conflicted with current radar posture.
- Fixed package mirrors for agent lifecycle and deferred tool loading after runtime adapter work.
- Cleared remaining laptop audit blockers and unblocked laptop validation gates ahead of the 0.28 soak.
- Aligned the itinerary matcher hook projection so registry, Claude Code settings, and Codex hooks projections agree on event/scope/matcher.
- Made primitive gates clean-tree safe so smoke runs do not false-positive on a pristine working tree.
- Preserved branch upstreams and remotes after history sanitization rewrite (consolidates three patches addressing pre/post-rewrite remote restoration).
- Hardened final pre-launch scanner gates ahead of public release.
- Treated package-metadata edits (license/version/name/author/homepage/repository fields in `package.json` and `pyproject.toml`) as non-dependency changes so the dependency-adoption-gate no longer false-positive-blocks metadata-only commits.

### Security

- Added stronger pre-public gates for secret/PII history, report-publish surfaces, provider-looking identities, and sensitive token configuration.
- Added history rewrite recovery guardrails with mandatory backup mirror, explicit destructive-git gate, and public disclosure artifacts.
- Added production-source read-only chaos guard and release-freeze boundary for destructive operations.
- Added supply-chain SBOM and license/provenance audit artifacts for public readiness.

### Release notes

- `v0.28.0-rc1` validated the primitive observability wave before final promotion. The final release keeps `.ai` as a generated consumer overlay, not the internal source of truth.
- The release-confidence bundle passed with Node available via `fnm`: derived artifacts, portable `.ai` overlay, OpenCode primitive adapter smoke, real-consumer shadow smoke, disposable consumer smoke, ACC brief, dogfood score with no missing signals, and primitive/dashboard contract tests.
- `make test-laptop-integration` previously exhausted the local 900s laptop timeout at 56% without a functional failure; treat the integration lane as requiring a larger timeout or shards before future broad-release attestations.

## [0.27.1] - 2026-05-06

### Fixed

- `fix(validation): register cosd runtime guards` (d958d17f) — registers cosd HTTP/socket runtime guards in the validation gate so the auth + bearer-token primitives surface as audited evidence instead of being silently skipped.
- `fix(audit): close laptop validation gaps` (d4b80a44) — closes residual gaps surfaced by the laptop-lane validation contract introduced ahead of v0.27.0; ensures the laptop release lane (`feat(release): require laptop lane before real release`) catches the cases that slipped through.

## [0.27.0] - 2026-05-06

### Added — ADR-171..187: paperclip rejection, lifecycle activation, and coordination hardening (2026-05-06)

- Rejected the Paperclip/OpenSpace-style auto-apply integration surface and removed the package, hooks, docs, tests, and symlinks tied to the retired Paperclip daemon path. The accepted path keeps generated skills in sandbox until evidence and operator review promote them.
- Activated the skill lifecycle ladder: sandbox skills can now produce propose-only promotion artifacts, advisory/blocking primitives can produce demotion proposals, and doctrine proposals log SkillStore/dogfood/drift/aspirational input signals. Promotion and demotion flows remain non-mutating by contract.
- Adopted SkillStore as the primary skill-evidence ledger for lifecycle decisions. The store now records exact per-execution events in `skill_execution_events`, while JSONL remains a compatibility fallback for older installs and fixtures.
- Added lifecycle CLIs and validation surfaces: `scripts/cos-promotion-proposer`, `scripts/cos-demotion-proposer`, `scripts/migrate_skill_archive_to_store.py`, `hooks/skill-post-execution-analysis.sh`, `hooks/promotion-proposer-weekly.sh`, `tests/contracts/test_promotion_propose_only.py`, `tests/behavior/test_skill_lifecycle_promotion_ladder.py`, and `scripts/run_skill_lifecycle_promotion_smoke.py`.
- Added cross-session coordination primitives: branch ownership locks, event bus, agent message bus, ADR relevance/routing suggesters, context-budget enforcement, and the cosd intent arbiter for ADR number/tombstone arbitration.

### Fixed — lifecycle evidence windows and SkillStore path consistency (2026-05-06)

- Standardised the SkillStore DB path on `.cognitive-os/skill_store.db` across hook, migration, doctrine proposer, promotion proposer, demotion proposer, and tests.
- Fixed demotion evaluation so advisory skills used inside the demotion window are not falsely demoted because promotion-window data was reused.
- Fixed lifecycle proposal evidence to use windowed SkillStore execution events instead of historical aggregate completions when evaluating “N invocations in M days”.
- Hardened `cosd` intent handling so duplicate pending intent IDs are not overwritten and ADR tombstone filenames must preserve the canonical `ADR-NNN-*.md` prefix.

### Added — ADR-176: SkillStore SQLite schema adoption + post-execution analysis trigger (2026-05-05)

ADR-176 adopts OpenSpace's 6-table SQLite schema verbatim (source: HKUDS/OpenSpace @ d1e367d, `skill_engine/store.py` lines 80–166) and introduces a discipline-gated post-execution analysis trigger. Key additions: `lib/skill_store.py` (SkillStore class; 6-table schema: `skill_records`, `skill_lineage_parents`, `execution_analyses`, `skill_judgments`, `skill_tool_deps`, `skill_tags`), `scripts/migrate_skill_archive_to_store.py` (idempotent migration from `skill-archive.jsonl`), and `hooks/skill-post-execution-analysis.sh` (PostToolUse Agent, async). Discipline gate (ADR-133/134) is structurally enforced: the hook's only write path to skill-related files is `docs/06-Daily/reports/skill-analysis-proposals/` — no code path to live `SKILL.md` exists.



### Added — Multi-surface UI architecture (ADR-172)

- `docs/02-Decisions/adrs/ADR-172-multi-surface-ui-architecture.md` — accepted. Declares four UI surfaces: Surface 1 (operator CLI + markdown reports), Surface 2 (Phoenix LLM-trace UI, opt-in), Surface 3 (Engram Cloud), Surface 4 (Obsidian). CLI-as-primary from ADR-170 survives as Surface 1.
- `docs/06-Daily/reports/surface-5-tui-ui-candidates-2026-05-05.md` — audit report of TUI candidates as input to a future ADR-173.

### Changed — ADR-043 deprecated


### Changed — ADR-170 superseded

- `docs/02-Decisions/adrs/ADR-170-operator-cli-as-primary-ui-surface.md` — marked Superseded by ADR-172. CLI-as-primary clause survives as Surface 1 inside ADR-172.


- Removed 6 hook entries from `cognitive-os.yaml` (SessionStart ×2, PostToolUse Agent ×3, Stop ×1)
- Removed 6 registrations from `scripts/_lib/settings-driver-claude-code.sh`
- Removed 6 entries from `hooks/_lib/registration-allowlist.txt`

## [0.26.0] - 2026-05-05 — "Operator-CLI Primary, Phoenix Optional, Honest API Findings"

This release pivots the UI surface story away from a single web dashboard
toward an honest operator-CLI plus markdown-reports model, with Phoenix
declared as an opt-in trace surface. Two days of audits and live verifications
documents that finding instead of papering over it, and reframes the system
around interfaces that actually work today.

### Changed — Operator-CLI as primary UI surface (ADR-170)

- Phoenix declared as a **complementary opt-in surface** for LLM traces only (`bash scripts/dependency-lane.sh install observability && uv run phoenix serve`). It does not model COS lifecycle / doctrine / demotion / audit_class. CLI + markdown remains the governance surface.
- Falsifiable claim added in ADR-170: CLI usability for new operators (under 5-minute orientation), markdown report cadence (at least one per major decision cycle for 60 days), and external-buyer demand (no Shape B trigger from three independent UI-blocker citations within 6 months). Re-evaluation after one year.



### Changed — Mapping #5 deferred (cos packages → skills marketplace)


### Changed — Dashboard formally demoted (ADR-169)

- `dashboard/` formally archived. `dashboard/ARCHIVED.md` is the new entry point and points at ADR-169. Files preserved on disk (not deleted) so the demotion is reversible if the falsifiable claim in the ADR fires.

### Added — Docker worker accessibility

- `docs/05-Methodology/runbooks/run-cos-in-docker.md` — operator runbook for the ADR-140 worker container. Quick Start (90 seconds), bootstrap subcommand reference, BYOK env vars per ADR-139, full stack with engram-cloud profile per ADR-141, audit-trail compliance evidence per ADR-142, troubleshooting, related-docs cross-reference. Closes the maintainer-cache discoverability gap surfaced when the runbook was missing despite the underlying infrastructure being complete.
- `scripts/cos-cloud-worker-bootstrap.sh` — added `up-full` subcommand that activates the engram-cloud Compose profile (postgres + pgvector + engram cloud server). `down` now stops both default and engram-cloud profiles so callers do not need to know which subset was started. Usage banner now lists every subcommand with one-line descriptions and points at the runbook.
- `README.md` — new "Headless / cloud-worker container" section in the Quick Start area, linking to the runbook. Differentiates the Docker worker (headless / CI / evaluation) from the daily-IDE-governance install path.
- `docs/00-MOCs/entrypoints/INDEX.md` — added entry for the runbook under Operational Documents.
- `docs/00-MOCs/entrypoints/getting-started.md` — new "Headless deployment via Docker" section before "Next Steps", with a decision matrix (which path for which scenario).

## [0.25.0] - 2026-05-05 — "Embedded-Runtime Trajectory and Enterprise-Readiness"

This release commits the operational direction for Cognitive OS to shift from
*"governance layer over coding agents"* toward *"embedded runtime for agent
flows"* (ADR-137), and lands the enterprise-readiness surface (BYOK
credentials, cross-OS containers, engram-cloud replication, air-gapped audit
trail) that makes the trajectory consumable outside the maintainer's machine.

158 commits since v0.24.0, 13+ new ADRs (137–149, 168), 15+ new architecture
documents, 10+ new lib modules. The doctrine deepens with the *"Two maturity
stages"* extension to `cognitive-prosthesis.md` — a primitive earns
default-visible status only when both *does it work?* and *how would I know
mechanically when it stops working?* are answered.

### Added — Closure Discipline Gate (ADR-143)

- `docs/02-Decisions/adrs/ADR-143-closure-discipline-gate.md` — accepted blocking maintainer gate for closing validator drift after fast agent batches.
- `scripts/cos-closure-discipline-audit` / `scripts/cos_closure_discipline_audit.py` — quick structural audit for stale suspended-workflow references, hardcoded runtime hook counts, validation capsule minimal-repo fallback, primitive lifecycle findings, and local-CI self-wiring.
- `docs/09-Quality/manual-tests/closure-discipline.md` and `tests/unit/test_closure_discipline_audit.py` — manual and automatic proof paths for closure discipline.

### Fixed — Validation closure drift from May 3 batch

- Updated workflow tests to understand ADR-130 `.yml.disabled` preservation.
- Replaced hardcoded runtime hook count assertion with report-derived runtime-hook reality parity.
- Made `cos-validation-capsule.sh` usable in minimal repos without silently falling back to `rm -rf`.
- Updated work-inventory tests to opt out of ephemeral-path filtering when testing direct parser behavior.
- Corrected blocking primitive lifecycle metadata for self-improvement discipline and registry-lock gates.

### Documentation

- `docs/04-Concepts/architecture/cognitive-prosthesis.md` — new section *Two maturity stages: works-when-it-works, and knows-when-it-doesn't* enumerates the nine concrete mechanisms that materialise the transition (demotion-with-evidence, governance-maturity labels, silent-failure allowlist, aspirational audit, false-positive ledger, propose-only proposers per ADR-134/135, anti-self-validation, ADR-136 runway with observable triggers, falsifiable claims as release artefact). Adds the operable test for whether a capability belongs in the default profile: not only *does it work?* but *how would I know mechanically when it stops working?*.
- `docs/04-Concepts/architecture/dx-cloud-flow-bootstrap-plan.md` — new strategic plan for COS as runtime-of-prosthesis for cloud agent flows (vuln-fix, bug-fix, features, docs, primitive expansion) under human audit. Names the trajectory B → A (governance layer over agents → embedded runtime), the priority shifts that follow, and the bootstrap path: vulnerability remediation in `e2b` sandbox as flow #1 with explicit budget caps (zero new default-visible primitives, zero rules added to RULES-COMPACT, no Shape B activation). Includes 6 falsifiable conditions, 5 explicit non-goals, and a 3-step ordered next-action list.
- `docs/02-Decisions/adrs/ADR-137-operational-trajectory-governance-layer-to-embedded-runtime.md` — accepted trajectory ADR. Commits direction `Framing B → Framing A` orthogonal to ADR-132's Shape A/B axis (near-term target: `(Shape A, Framing A)`). Introduces the **framing-exercise statement** required in flow skill metadata; flows without it cannot be promoted out of `lab`. Makes ADR-064 implementation completion flow-gated rather than roadmap-gated.
- `docs/02-Decisions/adrs/ADR-138-flow-contract-schema.md` — accepted schema ADR. Commits the required shape for `manifests/flow-contract-schema.yaml` (twelve top-level fields including `flow_id`, `lifecycle_state`, `input_source.determinism`, `success_condition.verifier`, `sandboxed_write_paths`, `blocked_actions`, hardcoded `human_approval_required: true`, `evidence_shape` with anti-self-validation independence flags, `framing_exercise_statement`, `non_goals`, `falsifiable_when`). Schema stays in `exemplary` status until the second flow registers against it unchanged; extensions land as ADR-138a or new ADR. Updated to add eight new fields from ADR-139/141/142 (`credential_source`, `billing_identity`, `provider_capabilities`, `engram_project_scope`, `air_gapped_compatible`, `tenant_id`, `audit_class`).
- `docs/02-Decisions/adrs/ADR-139-account-agnostic-multi-provider-runtime.md` — accepted ADR. Establishes caller-supplied credentials as the default for all COS surfaces, bans credential propagation from maintainer shell to cloud workers, defines three billing postures (`byok-maintainer`, `byok-project`, `proxied`), extends Rules §10 to provider SDK licenses, mandates generic env var names (`LLM_PRIMARY_API_KEY`), and requires `billing_identity` in every LLM audit row.
- `docs/02-Decisions/adrs/ADR-140-cross-os-containerized-deployment.md` — accepted ADR. Defines a Docker Compose worker stack (`docker/cos-worker/docker-compose.yml`) for Linux/macOS/Windows+WSL2 cloud worker surfaces; satisfies `bootstrap-portability.md` for container deployments; no shell profile assumption; optional services remain optional via Compose profiles.
- `docs/02-Decisions/adrs/ADR-141-engram-cloud-cross-instance-replication.md` — accepted ADR. Wires upstream `engram cloud` (April 2026) as a live-sync complement to the existing git-jsonl path. Three coexisting modes: `local-only`, `git-jsonl` (not deprecated), `engram-cloud`. Local SQLite authoritative; cloud replication-only. Project-scoped bearer tokens; `ENGRAM_CLOUD_ALLOWED_PROJECTS` tenant isolation; conflict surfacing reuses the propose-only contract. Introduces `scripts/cos-engram-cloud-enroll` bootstrap wrapper. Audit bridge to `agent-audit-trail.jsonl`.
- `docs/02-Decisions/adrs/ADR-142-compliance-audit-air-gapped-surface.md` — accepted ADR. Formalises `.cognitive-os/runtime/agent-audit-trail.jsonl` as the canonical compliance evidence surface. Defines `audit_class` enumeration (seven classes covering SOC 2 / ISO 27001 / GDPR relevance), `tenant_id` per-flow isolation, air-gap deployment surface (local JSONL + git-jsonl), and GDPR erasure procedure. Classifies existing governance hooks as `access_control` evidence.
- `docs/04-Concepts/architecture/dx-cloud-flow-bootstrap-plan.md` — updated: ADR-139..142 added as prerequisites before promoting flow #1 beyond `lab`; status updated to `ready-for-first-flow-lab`; companion docs list extended.

### Added — Operational Tooling and Discipline (ADRs 144–149, 168)

- ADR-144 — **Hook-Enforced Rule Projection Contract.** The mapping from
  rules to hooks is now contract-enforced; rule projections that do not
  reach a registered hook fail audit.
- ADR-145 — **Dependency Lane Split.** Heavy optional dependencies move out
  of `dev` into explicit lanes under `requirements/dependency-lanes/` so
  upstream pins on one lane (e.g. `cognee`/`kuzu`) cannot block core
  dependency hygiene. `pyproject.toml` `dev` extra now resolves to
  `[web,direct_providers,testing,enforcement]`.
- ADR-146 — **Primitive Readiness Ledger.** Each primitive carries an
  explicit readiness record consumed by the boring-reliability dashboard
  and by tier-claim auditing.
- ADR-147 — **Agent Capability Coverage Pipeline.** ACC pipeline measures
  what agents can/cannot achieve under the current primitive surface and
  surfaces gaps as a first-class metric. Wired into the statusline segment
  through `cos-coverage`.
- ADR-148 — **ADR Authoring Primitive.** ADR creation itself becomes a
  primitive with required schema, frontmatter, and admission contract;
  prevents drift in the most load-bearing decision artifact.
- ADR-149 — **Primitive Duplication Audit.** Audits the registry for
  semantic duplicates (different names, same effective surface) so the
  default-visible budget is not inflated by accidental re-implementations.
- ADR-168 — **Cross-Device Dependency Installation Contract.** Standardised
  install metadata so a primitive can declare its dependency requirements
  in a way that survives installation across machines and OSes; companion
  to ADR-140 (Docker Compose) and ADR-141 (engram cloud).

### Added — Self-Improvement Loop Extensions

- `lib/consumer_improvement_proposals.py` — consumer projects can now feed
  their own observations back through the propose-only contract.
- `lib/governed_self_improvement.py` — the self-improvement loop is now
  audited end-to-end as a closed governed flow, not as an isolated
  primitive.
- `lib/key_learning_capture.py`, `lib/dispatch_optimizer.py`,
  `lib/friction_telemetry.py`, `lib/adaptive_profile.py` — supporting
  primitives that feed the learning loop with structured signals.
- `lib/engram_obsidian_exporter.py` + `scripts/cos-engram-export-obsidian` —
  manual Engram export to an Obsidian vault for human review and
  cross-tool reading. Stop-hook variant included.

### Added — Architecture Documentation

- `docs/04-Concepts/architecture/dx-cloud-flow-bootstrap-plan.md` — strategic plan for
  COS as runtime-of-prosthesis for cloud agent flows under human audit.
- `docs/04-Concepts/architecture/agent-capability-coverage-pipeline.md` — ACC pipeline
  reference.
- `docs/04-Concepts/architecture/bootstrap-portability.md` — cross-OS portability
  contract for installation and runtime.
- `docs/04-Concepts/architecture/concurrency-safety-core-consumer-contract.md` —
  contract surface between core and consumer projects under concurrent
  use.
- `docs/04-Concepts/architecture/consumer-project-primitive-accessibility.md` —
  accessibility guarantees for consumers.
- `docs/04-Concepts/architecture/cos-instance-installer.md` /
  `cos-service-runtime-boundary.md` — installer and service-runtime
  boundaries.
- `docs/04-Concepts/architecture/engram-command-contract.md` — Engram CLI contract.
- `docs/04-Concepts/architecture/expected-skip-registry-and-opt-in-test-lanes.md` —
  classified skip registry; unit-lane skip policy is now explicit.
- `docs/04-Concepts/architecture/gdpr-erasure-procedure.md` — GDPR erasure procedure
  companion to ADR-142.
- `docs/04-Concepts/architecture/adr-closure-policy.md` — closure policy for ADRs that
  reach `accepted` and need their evidence linked.
- `docs/04-Concepts/architecture/functional-audit/scorecard-hooks.md` — hook
  functional-audit scorecard.

### Changed

- `pyproject.toml` version bumped from `0.24.0` to `0.25.0`. The
  dependency-lane split (ADR-145) collapses the previously bundled `llm`,
  `observability`, `guardrails`, `jupyter`, `crawling`, `memory`,
  `semantic` extras out of the default `dev` extra; opt in per lane via
  `requirements/dependency-lanes/*`.
- `rich>=15` replaces the previous `rich>=14` pin; the upstream
  cognee/kuzu blocker that held `rich` at 14 lives in the `memory` lane
  now and no longer constrains core.

### Internal

- `manifests/hook-quality.yaml` — regenerated via `scripts/hook_quality_audit.py --sync` to register two auto-detected behavior tests for `task-completed` and `validation-lock-cleanup` hooks (drift surfaced by `derived-artifact-gate` during merge-to-main validation).
- `manifests/expected-skip-registry.yaml` and supporting audit — unit-lane
  skip policy classified explicitly; expected skips no longer hide as
  silent test passes.

### Falsifiable claims added (per release artefact discipline)

- **Embedded-runtime trajectory**: a flow without a
  `framing_exercise_statement` per ADR-137 cannot leave `lab`. If a flow
  reaches `core`/`team` without one, the trajectory is broken.
- **Closure discipline**: validator drift after a fast batch must be closed
  by `cos-closure-discipline-audit` before the batch can be claimed
  complete. If a drift entry remains open after a release tag, the
  discipline is broken.
- **ADR authoring primitive**: ADRs lacking the schema required by ADR-148
  cannot be admitted. If ADRs land without it, the primitive is
  decorative.
- **Primitive duplication audit**: the registry should not contain
  semantic duplicates after the audit runs. If `cos-primitive-duplication-audit`
  reports duplicates and they persist past the next release, the audit
  is decorative.

## [0.24.0] - 2026-05-03 — "Closed-Loop Self-Improvement and Shape B Runway"

This release lands the closed-loop self-improvement framework that the v0.23.0
case study identified as the natural follow-up. Three new ADRs (134–136) plus
one provenance-hardening commit add **four architectural ceilings** stacked on
top of the v0.23.0 boring-reliability doctrine. Each ceiling blocks a distinct
runaway class while preserving human review as a structural invariant.

The release also lands a Shape-B runway: infrastructure required for future
multi-maintainer / federated operation, built but not operated, with
trigger conditions converted from prose into observable counters.

### Added — Closed-Loop Self-Improvement (ADR-134, ADR-135)

- `scripts/cos-self-improvement-loop` (ADR-134) — converts control-plane audit
  findings into bounded operational proposals. `propose-only` mode hardcoded,
  `human_approval_required: true`, sandboxed write paths per proposal,
  blocked actions list (`auto_merge`, `auto_promote_core_or_team`,
  `invent_roi_evidence`, `delete_without_reversible_path`).
- `scripts/cos-self-improvement-discipline-gate` — wired into `cos-ci-local.sh`,
  enforces the proposer's own discipline contract.
- `scripts/cos-doctrine-proposer` (ADR-135) — generates proposed doctrine
  amendments as markdown under `docs/03-PoCs/proposals/`. `runtime_effect: none`
  hardcoded; the system proposes new rules but never applies them.
- `lib/self_improvement_loop.py`, `lib/doctrine_proposer.py` — the core
  libraries. Each proposal includes `non_goals` (anti-patterns to avoid) so
  the proposer cannot accidentally propose its own over-correction.
- First doctrine-proposer run produced five concrete amendments derived from
  live audit data. One amendment ("prefer semantic matching over substring
  matching in gates") is structurally identical to a finding from the
  external SR review that triggered the v0.23.0 cycle, re-derived
  independently from the system's own `cos-false-positive-ledger`.

### Added — Shape B Runway (ADR-136)

- `manifests/agentic-primitive-registry.lock.yaml` — SHA-pinned manifest of
  every primitive (1,588 lines). Cross-machine instances can verify identical
  primitive sets deterministically.
- `manifests/skills/REGISTRY.lock` — version-pinned skill set.
- `manifests/federation-triggers.yaml` — converts ADR-132's prose trigger
  conditions for Shape B into observable counters. Six metrics
  (`active_maintainers`, `active_machines`, `concurrent_remote_writers`,
  `external_consumer_reports_30d`, `repeated_cross_machine_lock_conflicts`,
  `unsupervised_remote_agents`); each with current observed value and
  Shape-B trigger threshold. Audit fires when any observed value crosses
  its threshold.
- `scripts/cos-export-consumer-evidence` / `cos-import-consumer-evidence` —
  cross-instance evidence exchange. Imports are propose-only.
- `scripts/cos-engram-bundle` / `cos-engram-import-propose` — portable
  Engram bundle. Imports propose new observations; never auto-merge.
- `scripts/cos-federation-trigger-audit` — periodic audit of the
  observed-vs-trigger gap.
- `scripts/cos-cross-instance-drill` — manual rehearsal of the runway
  primitives end-to-end. A runway that is never rehearsed rusts; this drill
  exercises the full export → bundle → import-propose → registry-lock
  verification path without activating Shape B.

### Added — Anti-Self-Validation (commit `d4535df0`)

- `manifests/external-adoption-evidence.yaml` — schema for admissible
  external-help claims. Required: `independence.maintainer_owned: false`,
  `same_machine: false`, `same_repo: false`, `self_reported: false`, plus a
  `provenance.producer` block (type, identity, optional signature,
  timestamp). Evidence violating any `independence` flag is rejected as
  drill output, not as adoption signal.
- `scripts/cos_claim_signature_audit.py` extended — claims must carry signed
  provenance to count.
- First drill report (`docs/06-Daily/reports/cross-instance-consumer-e2e-2026-05-03.md`)
  applies the schema to its own output and explicitly disqualifies itself
  from signing the `helps-projects` claim. Doctrine applied recursively to
  its first verification artefact.

### Added — Case Study Sections

The external-review-cycle case study gained four new structural sections,
each documenting a property of the cycle distinct from the operational
narrative:

- *Self-evolving doctrine: when the audit subsystem proposes rules about itself*
- *Convergence: when internal proposals reproduce external review findings*
- *Runway-not-rocket: building Shape B's infrastructure without operating Shape B*
- The *Runway-not-rocket* section now also documents the fourth ceiling
  (anti-self-validation through required provenance) and the falsifiable
  claim it adds for external adopters.

The case study now has **seven meta-property sections** for external
adopters to use as a frame when evaluating governance systems.

### Changed

- `pyproject.toml` version bumped from `0.23.0` to `0.24.0`.
- The architectural posture documented as "three ceilings" (in the v0.23.0
  case study) is now four, with the fourth landing inline in the
  *Runway-not-rocket* section to keep all anti-runaway refusals in one
  table.

### Documentation

- ADR-134 — Headless Self-Improvement Proposer
- ADR-135 — Self-Evolving Doctrine Proposals
- ADR-136 — Cross-Instance Learning Runway
- `docs/04-Concepts/architecture/cross-instance-learning-runway.md`
- `docs/04-Concepts/architecture/headless-self-improvement-proposer.md`
- `docs/04-Concepts/architecture/self-evolving-doctrine-proposals.md`
- `docs/06-Daily/reports/cross-instance-consumer-e2e-2026-05-03.md` — first drill
  report, intentionally self-disqualified per the new
  anti-self-validation rule.

### Falsifiable claims added (for external adopters)

- **Self-improvement loop**: subsequent runs against new audit data should
  produce new proposals when the data shifts. If the proposal set is static
  after months of audit evolution, the loop is broken.
- **Doctrine proposer**: the healthy zone is *partial convergence* with an
  independent external review. Zero convergence = loop too narrow; full
  convergence = loop hallucinating.
- **Shape B runway**: dormant runway with continuous trigger observability is
  healthy. Active runway with zero observed triggers = discipline broken.
  Triggers fired with no runway primitive activation = runway decorative.
- **Anti-self-validation**: `manifests/external-adoption-evidence.yaml` must
  not accumulate entries with `maintainer_owned: true` that sign product
  claims.

## [0.23.0] - 2026-05-03 — "Boring Reliability and the Audited Default Surface"

This release completes a single-session external-review absorption cycle (DX
assessment → ADRs → enforcement → demotions → doctrine update). The dominant
direction is **subtraction and maturity**, not addition: lifecycle states earn
their default-visible position through evidence; demotion is a first-class
operation; CI moves from GitHub-hosted to local pre-push gates.

### Added — Boring Reliability Control Plane

- `scripts/cos-boring-reliability` aggregator dashboard plus 9 sub-tools:
  `cos-adoption-profile`, `cos-preamble-budget`, `cos-default-visible-reducer`,
  `cos-false-positive-ledger`, `cos-wip-safety-score`, `cos-recovery-drill`,
  `cos-runtime-hook-reality`, `cos-silent-failure-audit`, `cos-dispatch-smoke`.
  Operator-readable signals replace prose-only reasoning about system health.
- `manifests/governance-maturity.yaml` — explicit `advisory` / `observe` /
  `blocking` labels for `trust-score-validator`, `blast-radius`, `review-spawner`.
  Product docs can no longer claim a check is blocking without evidence.
- `manifests/silent-failure-allowlist.yaml` — every `|| true` / `|| :` /
  `2>/dev/null` occurrence in hooks is now classified with a rationale and
  `max_occurrences`. Growth without classification fails the audit.
- `docs/04-Concepts/architecture/boring-reliability-control-plane.md` — operating doctrine
  for default-visible primitives: real / measurable / reversible / honest /
  evidence-backed.
- `docs/04-Concepts/architecture/cognitive-prosthesis.md` — rationale companion explaining
  why the system has the shape it has.

### Added — Adoption Profiles and Lifecycle Discipline

- Adoption tiers `core` / `team` / `maintainer` / `lab` (ADR-124) with
  `cos-active-primitive-index` enforcing default-visible thresholds
  (`VISIBLE_WARN_THRESHOLD=12`, `VISIBLE_FAIL_THRESHOLD=25`) wired into local CI.
- Eight lifecycle states (ADR-126: `candidate` → `sandbox` → `advisory` →
  `blocking` → `default-on` → `demoted` → `archived` → `deleted`) with
  required `demotion_evidence` and `sunset_criteria` on demoted entries.
- `scripts/cos-tier-claim-audit` + `tests/audit/test_adr_tier_claims.py` —
  ADRs claiming `tier: core`/`team` must include machine-readable evidence
  blocks linking to control-plane output (ADR-133).
- `scripts/lab_first_promotion_gate.py` — every new primitive starts in
  `lab`/`sandbox`; promotion requires evidence (ADR-133).
- First two demotions executed with evidence: `hooks/task-completed.sh`
  and `hooks/context-watchdog.sh` projection.

### Added — Local CI Migration (replaces GitHub Actions)

- `scripts/cos-ci-local.sh` — tiered runner (`quick` / `full` / `deep`)
  consolidating the seven ubuntu-equivalent workflows. Pre-push default
  targets ~30s wall-clock (ADR-131).
- `git-hooks/pre-push` + `scripts/install-git-hooks.sh` — tracked git hook
  activated via `core.hooksPath`. Bypass with `--no-verify` or
  `COS_PRE_PUSH_SKIP=1`.
- Three weekly `launchd` schedules via `scripts/install-launchd-jobs.sh`
  replacing the cron-style workflows: config-audit (Mon 09:00),
  public-metrics (Mon 12:00), primitive-gap (Mon 12:30).
- `scripts/cos-pr-review.sh` — manual `prep` / `post` CLI replacing the three
  Claude API workflows. Zero per-PR API cost.

### Added — Data Layer Integrity (ADR-128)

- Engram wrapper-level upsert: `lib/engram_client.save_observation()` searches
  for `(project, topic_key)` matches before save; routes exact matches to HTTP
  update instead of appending duplicates.
- Engram rank-derived score fallback in `lib/engram_lifecycle`: when the
  binary returns no numeric `score`, the differential signal no longer
  collapses to `1.0`.
- Engram daemon-down visibility: `engram-daemon-down.jsonl` metric is written
  when reinforcement cannot reach the daemon. Failures are no longer silent.
- SDD topic-key namespace canonicalised to `planning/{change}/...`. Legacy
  `sdd/*` keys remain read-fallbacks (ADR-128 §6).
- `tests/audit/test_version_consistency.py` — `pyproject.toml` version must
  match the latest released `CHANGELOG.md` heading.
- `tests/audit/test_sdd_topic_keys.py` — canonical SDD namespace audit.

### Added — Safety Hardening

- `hooks/_lib/safe-worktree-remove.sh` (ADR-129) — replaces the
  `--force || rm -rf` antipattern across four callsites with a helper that
  captures git stderr, logs to `.cognitive-os/metrics/worktree-removals.jsonl`,
  and never falls back to `rm -rf` unless `COS_WORKTREE_REMOVE_ALLOW_RM_RF=1`.
- Semantic-scope refactor of `destructive-git-blocker.sh`,
  `direct-main-guard.sh`, and `orchestrator-claim-gate.sh` — substring-match
  false positives reduced by parsing actual command shape.
- `direct-main-guard.sh` now requires `COS_DIRECT_MAIN_BYPASS_REASON` for
  bypasses and appends each event to `.cognitive-os/metrics/direct-main-bypass.jsonl`.
- `cos_false_positive_ledger.py` — match scope tightened from full-event
  text to `event_type` / `bypass_kind` fields, eliminating filename-string
  false positives.

### Added — Strategic Decisions

- ADR-132 — Solo-Swarm vs Multi-Maintainer Fork (`exploration`). Names the
  trigger conditions for re-shaping the system from single-maintainer
  (Shape A) to multi-maintainer (Shape B). Recommends staying in Shape A
  until trigger fires.
- ADR-133 — Expansion Without Monsterization. Lab-first admission contract
  with required evidence blocks for `core` / `team` tiers.

### Changed

- All eleven GitHub Actions workflows renamed to `.disabled` (ADR-130). The
  `.disabled` extension takes them out of GHA auto-discovery while preserving
  YAML in the repo as documentation. Restoration is per-file rename.
- `pyproject.toml` version bumped from `0.22.0` to `0.23.0`.
- `core` adoption profile preamble files now include `AGENTS.md` so the
  preamble-budget tool reflects the full context tax.
- Architecture readiness fails when projected hooks are not represented in
  the lifecycle manifest — readiness can no longer report green while
  undercounting runtime surface.
- Boring-reliability dashboard distinguishes `warn` from `fail` exit codes
  cleanly: `warn` does not escalate to non-zero, `fail` does.

### Fixed

- Engram upsert no longer creates duplicate observations on repeated save
  with the same `topic_key` (ADR-128 §1).
- `cos_false_positive_ledger` no longer inflates counts by matching filenames
  in event payloads (`adaptive-bypass.jsonl` was firing on every so-vitals
  heartbeat tick).
- Multiple substring-match gates no longer false-positive on legitimate
  commit messages, push commands, and command bodies.
- `pyproject.toml` and `CHANGELOG.md` versions are now CI-enforced to match.

### Documentation

- ADR-124 distribution boundaries / ADR-125 governance-tools value boundary /
  ADR-126 lifecycle governor / ADR-127 active primitive index / ADR-128 data
  layer integrity / ADR-129 safe worktree removal / ADR-130 GHA suspend /
  ADR-131 local-CI migration / ADR-132 solo-swarm fork / ADR-133 expansion
  without monsterization.
- ADR namespace consolidated under `docs/02-Decisions/adrs/` (ADR-087); legacy paths
  remain as documentation references.
- `docs/08-References/case-studies/external-review-cycle-2026-05-02.md` — worked example
  of one external-review absorption cycle. Sections cover the cycle, what
  made it possible, bilateral pressure, protected landing, self-triggered
  absorption, cadence asymmetry between reviewer and maintainer, what the
  cycle does not prove, and a replication template.
- `docs/04-Concepts/architecture/direct-main-policy.md` — operational policy for direct
  pushes to `main`.
- `docs/06-Daily/reports/dx-assessment-2026-05-02.md` — the SR-level DX assessment
  that triggered the absorption cycle.
- `docs/06-Daily/reports/boring-reliability-audit-2026-05-03.md` — end-to-end audit
  baseline of the 10 control-plane tools.

### Removed

- Three Claude-API GitHub Actions workflows (`claude-interactive`,
  `claude-issue-triage`, `claude-pr-review`) suspended by rename to
  `.disabled` — no per-PR API cost.
- macOS-matrix workflow (`cross-platform`) suspended — was the largest
  remaining cost driver after the Claude-API workflows.
- Seven additional ubuntu workflows suspended in favour of local-CI
  replacement (ADR-131).

## [0.22.0] - 2026-04-30

- **Test runner ergonomics** (ADR-072): Lane taxonomy with `.cognitive-os/test-lanes.yaml` as source of truth. New `cos-test focused/cluster/broad` escalation ladder. Auto-marker injection in conftest. Audit and contracts lanes now parallel (~40% wall-time reduction observed). Makefile `test-*` targets deprecated; redirect to cos-test (1 release cycle). Originally proposed as ADR-069; renumbered after the slot was claimed by `research-first-protocol`.

## [0.21.0] - 2026-04-28 — "Portable Runtime, Memory Lifecycle, and Developer Confidence"

### Added

- Codex-first host tooling verification with a doctor that checks active harness, settings driver JSON, declared dependencies, Engram CLI, Engram MCP startup, and Codex config wiring.
- Cached SessionStart host-doctor execution so Codex and Claude installs can surface toolchain drift automatically without paying the full diagnostic cost on every session.
- Memory lifecycle portability checks and documentation covering SessionStart, UserPromptSubmit, Stop, Engram daemon launch, session resume, session changelog, and crystallization flows.
- Harness driver parity audit docs/tests to compare canonical Cognitive OS agentic primitives against Claude/Codex driver projections.
- Developer-confidence product positioning: Cognitive OS improves trust in AI-assisted development through memory, guardrails, recovery, portable checks, and lightweight defaults.
- Session summary reminder Stage A/B hooks: first remind/block for missing `mem_session_summary`, then provide a heuristic Engram auto-save fallback on repeated Stop attempts.

### Changed

- Preserved the installed harness and settings driver in `.cognitive-os/install-meta.json` so pull/push auto-update flows do not fall back to Claude when Codex markers are also present.
- Enforced native Codex projection paths so Codex installs no longer treat `.claude/` as the runtime center of gravity.
- Canonicalized memory hook environment resolution around `COGNITIVE_OS_*`, `CODEX_*`, and `CLAUDE_*` variables instead of Claude-only project/session assumptions.
- Dropped an excluded Engram driver projection from rules and clarified automatic memory semantics: shell hooks can persist local lifecycle evidence and reminders, while `mem_session_summary` remains an agent MCP tool call.

### Fixed

- Repaired post-SIGALRM test contract drift and replaced SIGALRM-based timeout fixtures with `pytest-timeout`-compatible behavior.
- Hardened hook latency tests to avoid flaky wall-clock/observability false signals.
- Stabilized the broad repair lane by removing stale observability assumptions and aligning hook latency targets.
- Isolated integration fixtures with `monkeypatch` and `tmp_path` to avoid cross-test state leakage.

### Documentation

- Added Codex host tooling verification runbook and memory lifecycle quick map.
- Added ADR-064 implementation plan covering remaining harness-agnostic surfaces, P0 sequence, and verification suite design.
- Documented developer-confidence positioning as a product artifact.
- Recorded release/handoff context for the v0.20.0-to-v0.21.0 stabilization cycle.


## [0.20.0] - 2026-04-27 — "ADR-071: Engram Lifecycle Evolution (Phases 1–3)"

### Added — confidence + Ebbinghaus decay (Phase 1, commit `d48dcb8`)

- `lib/engram_lifecycle.py` — wrapper layer with `save`/`search`/`reinforce`, `decay_retention(t,tau)`, `reinforce_confidence(c,beta=0.15)`, `adjusted_score(base,conf,ret,alpha=0.3)`. Six decay classes (architecture=365d, decision=180d, pattern=180d, discovery=90d, bugfix=60d, manual=90d). Lifecycle metadata stored as a `<engram-lifecycle>{...}</engram-lifecycle>` trailer in observation `content` so engram passes it through unchanged.
- `tests/unit/test_engram_lifecycle.py` — 22+ unit tests (trailer round-trip, decay math, reinforcement asymptote, ranking bounds, search re-ranking, decay-class mapping, malformed-trailer fallback).
- `hooks/engram-reinforce-on-access.sh` — async PostToolUse hook for `mem_search`/`mem_get_observation`. Registered in both `apply-efficiency-profile.sh` and `set-security-profile.sh`.

### Added — HTTP correction + safety policy (Wave 3a, commit `f2cd0aa`)

- `lib/engram_http_client.py` — REST wrapper for the engram daemon at port 7437. `is_available`, `get_observation`, `search_observations`, `get_recent`, `update_observation`, `create_observation`. `urllib` fallback when `requests` is absent. **Empty-PATCH raises `ValueError`** as a destructive-op preflight.
- `lib/engram_lifecycle.py` `reinforce()` rewritten to use HTTP `PATCH /observations/{id}` — true in-place update, no duplicate observations. The Phase 1 caveat ("engram CLI lacks `get`/`update`") was wrong; HTTP API exposes both. Corrected with addendum in ADR-071.
- `rules/engram-api-safety.md` — ratified after observation #13283 was accidentally overwritten during API discovery. Production daemon mutation only via typed clients; ad-hoc `curl PATCH/POST/DELETE` must target a sandboxed daemon (`ENGRAM_DATA_DIR=$tmp ENGRAM_PORT=7438 engram serve`).

### Added — crystallization (Phase 2, commit `f2cd0aa`)

- `lib/engram_crystallizer.py` — deterministic synthesis (no LLM in v1) when a `topic_key` crosses thresholds (`revision_count ≥ 5` in 30 days OR `≥ 10` total). Saves digest as `type=pattern`, `topic_key=<original>/crystallized`, with `crystallized:true` + `superseded_obs_ids: [...]` in trailer. Idempotent via topic-key check.
- `hooks/engram-crystallize-on-session-end.sh` — async Stop hook calling `crystallize_all()`. Latency budget ≤500ms with short-circuit on empty candidates.
- `tests/unit/test_engram_crystallizer.py` — coverage for thresholds, candidate detection, idempotence, synthesize_content determinism, force=True replacement.

### Added — graph traversal (Phase 3, commit `f2cd0aa`)

- `lib/engram_graph_walker.py` — BFS over the `memory_relations` SQLite table opened **read-only** (`sqlite3.connect(f"file:{path}?mode=ro", uri=True)`). Excludes `judgment_status='rejected'`. Default `max_depth=2`, `graph_boost=0.3`, `alpha_graph=0.2`.
- `EngramLifecycle.search(graph_walk=True)` triggers traversal and merges neighbors into the ranked result set.
- `tests/unit/test_engram_graph_walker.py` — BFS correctness, depth limit, deduplication, rejected-relation skip, score merging.

### Added — end-to-end test harness

- `tests/e2e/test_engram_lifecycle_e2e.py` — 14 e2e tests against a **real sandboxed engram daemon** spawned on a free port with `ENGRAM_DATA_DIR=tempdir`. Marked `@pytest.mark.e2e`. Skipped automatically when the `engram` binary is absent. Total test count: **135 pass** (121 unit + 14 e2e).

### Documentation

- `docs/02-Decisions/adrs/ADR-071-engram-lifecycle-evolution.md` — full decision (schema, formulas, decay classes, ranking weight alpha=0.3, asymptotic confidence beta=0.15) + two addendums (HTTP discovery + Phase 2/3 shipped) + **Honest Limitations** section listing 12 caveats: heuristic synthesis, supersedes-not-written, local-only reinforcement, schema coupling, save-count proxy, dormant hooks, unvalidated thresholds, structural-only cloud-sync compat, etc.
- `docs/03-PoCs/research/llm-wiki-v2-engram-evolution-2026-04-27.md` — analysis of the LLM Wiki v2 gist (rohitg00/agentmemory) + 14 sources + post-implementation status footer.
- `.cognitive-os/plans/features/engram-lifecycle-evolution.md` — phased plan, marked SHIPPED for Phases 1–3, Phase 4 (Obsidian export) deferred.

### Notes

- Engram cloud branch (`feat/integrate-engram-cloud`) was inspected and confirmed **behind main by 10 commits** — cloud is already merged. The lifecycle trailer survives sync because it lives in `content`, but cross-device reinforcement aggregation is **not** implemented.
- The hook `engram-reinforce-on-access.sh` requires `engram serve` (port 7437) to be running. If down, `reinforce()` returns `False` silently and the failure is observable in `.cognitive-os/metrics/lifecycle-reinforcement.jsonl`.
- This is the implementation referenced in [LLM Wiki v2](https://gist.github.com/rohitg00/2067ab416f7bbe447c1977edaaa681e2). Phases 1–3 cover lifecycle (confidence + decay), crystallization, and graph traversal — i.e. everything the gist identifies as the load-bearing additions to a flat-page Karpathy wiki.

## [0.19.0] - 2026-04-27 — "ADR-068 Phase 1: Adaptive Pytest"

### Added — ADR-068 Phase 1: adaptive pytest worker selection

- `scripts/detect_runner_capacity.py` — cross-platform helper implementing the 6-row heuristic table (cores≤2→serial, load>70%→2, mem<2GB→4, battery<30% off-AC→serial, CI=true→auto, default→auto). Emits scalar token to stdout (`auto`/`0`/integer); `--json` flag exposes full diagnostics dict.
- `scripts/pytest-with-summary.sh` now invokes the detector when no `-n`/`--numprocesses` flag is present, preventing the 21-min serial regression that triggered the ADR. Explicit `-n` and `COS_PYTEST_WORKERS` env var both short-circuit detection per the override precedence chain.
- `tests/unit/test_detect_runner_capacity.py` — 9 unit tests covering each heuristic row, override precedence, and JSON diagnostics. psutil-missing path is exercised via mocked import failure; production path degrades to `auto` with a stderr warning.
- ADR-068 status: **Proposed → Accepted**.

## [0.18.0] - 2026-04-27 — "cos-init Python + Defense-in-Depth Complete"

### Added — cos-init.sh fully migrated to Python (strangler-fig complete)

- `scripts/cos_init.py` — full Python implementation of cos-init flow (Python 3.11+, stdlib + pyyaml)
- `scripts/cos-init.sh` collapsed from **711 → 5 lines** (exec shim for backward compat with `bash scripts/cos-init.sh`)
- 6 functions migrated through strangler-fig phases (2.1 → 2.final):
  - Phase 2.1 (`8a4778c`): `detect_harness()`
  - Phase 2.2 (`39dd40c`): `scope_allows()` + `skill_scope_allows()`
  - Phase 2.3 (`7fde5f9`): `install_rule()` + `install_hook()` + `install_skill_dir()`
  - Phase 2.final (`31f0002`): all 12 procedural sections (stack detection, mode components, dir structure, rules/hooks/skills install, templates, cognitive-os.yaml write, efficiency profile filtering, settings.json merge, install-meta, registry registration, gitignore update, summary)
- 47 unit tests + 29 parity tests + 72 integration tests pass post-migration
- Per ADR-066 polyglot policy: bash kebab-case shim retained, Python snake_case implementation owns the logic

### Added — ADR-067 Phase 2 defense-in-depth (rules + hooks + ADRs)

Extends the template + hook + audit pattern from `skills/*/SKILL.md` (Phase 1) to 3 more artifact types:

- `templates/rule-template.md`, `templates/hook-template.sh`, `templates/adr-template.md` — canonical skeletons with `<REQUIRED>` placeholders
- `hooks/rule-frontmatter-validator.sh` — PostToolUse Edit/Write hook for `rules/*.md`. Validates SCOPE, H1, opening section, conditional `## Contextual Trigger`. Advisory by default; BLOCK opt-in via `COS_STRICT_RULE_VALIDATION=1`.
- `hooks/hook-header-validator.sh` — for `hooks/*.sh`. Validates shebang, SCOPE, PURPOSE, EVENT, `set -euo pipefail`. Grandfathers existing 154 hooks (only enforces for new). `COS_STRICT_HOOK_VALIDATION=1`.
- `hooks/adr-section-validator.sh` — for `docs/02-Decisions/adrs/ADR-*.md`. Validates required sections (Status, Context, Decision, Consequences, Alternatives rejected, Verification with ≥1 fenced code block). Cutoff at ADR-067 — pre-067 ADRs grandfathered. `COS_STRICT_ADR_VALIDATION=1`.
- All 3 hooks: fast-path filter (skip Python startup if input doesn't match path pattern), bash 3.x compatible
- Hook registration in: `apply-efficiency-profile.sh` + `set-security-profile.sh` + 3 hook-architecture-v2 profile JSONs
- Audit tests extended: `test_rules_enforcement.py` (+4 tests), `test_hooks_contracts.py` (+1 contract), new `test_adr_contracts.py` (+5 tests)
- `/add-rule` and `/add-hook` skills updated to reference their templates
- ADR-068 self-bootstrap fix: its own `## Verification` section now has a code block (caught by the new audit test)

### Added — deps-update v2 (MCP-aware)

Lessons from the 2026-04-27 engram MCP outage codified into tooling:

- `scripts/deps-update.sh` — engram section rewritten brew-first (instead of `go install`):
  - `brew update` + `brew install/upgrade` preferred (Operon-safe path)
  - `which -a engram` multi-path conflict detection with symlink fix suggestions
  - Backup-before-replace (timestamped `.bak`)
  - `⚠️  Restart Claude Code` reminder when binary changed
- `scripts/check_mcp_servers.py` — diagnostic script: reads MCP configs, resolves binaries via `which -a`, checks process via `pgrep`, reports version. `--json` mode for machine readers.
- `tests/unit/test_check_mcp_servers.py` — 8 tests covering standalone config, mcpServers format, plugin-bundled config, multi-path detection, missing-process WARN, missing-binary ERROR, JSON output validity.
- `docs/05-Methodology/root/tooling-update-protocol.md` (new, 147 lines) — protocol for updating any Claude Code-integrated tool. Covers 3-paths trap, MCP restart requirement, brew vs go install vs manual, verification post-update, rollback. Living example: engram 2026-04-27 case study.
- `skills/deps-update/SKILL.md` — adds 4 new sections: brew-first flow, multi-path resolution trap, MCP server lifecycle, backup/rollback.

### Changed — Breaking (pre-1.0)

- **`scripts/cos-init.sh` is now a shim** — all logic lives in `scripts/cos_init.py`. Functionally backward compatible (CI / `install.sh` / docs all invoke `bash scripts/cos-init.sh`), but `--internal-call` dispatcher is the only Python-direct entry point now.

### Fixed

- **engram MCP server outage** (manual fix, no commit): `~/go/bin/engram v1.13.1` was SIGKILL'd by macOS Operon Sandbox when spawned from Claude Code. Resolution: `brew install gentleman-programming/tap/engram` → v1.14.5 + symlinks unified across `~/.local/bin/engram` + `~/go/bin/engram` → both point to brew canonical install. Engram MCP now operational, `mem_save`/`mem_search` available across sessions. Documented in engram observation `tooling/engram-mcp-fix` (#13280).

### Added — Tests

- `tests/unit/test_cos_init_py.py` — 47 unit tests across 6 functions
- `tests/behavior/test_cos_init_parity_2_1.py` + `_2_2.py` + `_2_3.py` — 29 parity tests (Python output == bash output, byte-for-byte)
- `tests/audit/test_adr_contracts.py` (new) — 5 tests including monotonic-warn for ADR numbering gaps
- `tests/unit/test_check_mcp_servers.py` — 8 tests

### Verified

- 76 unit + parity tests pass (2.59s)
- 72 integration tests pass (3m 26s) including `test_fresh_install_canary` full + idempotent upgrade
- 1813 audit tests pass, 0 failures (post-Phase-2 add)
- Live install test: 3 scratch directories (node --default, python --full, go --harness=codex) all produce correct output

### Operator decisions accepted (from research-first triage)

- **9 cos-init migration decisions**: pyyaml, defer generate-project-settings, inline detect_harness, keep bash shim, subprocess.run, tomllib+tomli fallback, both unit+parity tests, strangler-fig, drop bash 3.x constraint
- **9 ADR-067 Phase 2 decision points + 5 open questions**: WARN advisory default, ADR-067 cutoff (no pre-067 backfill), grandfather 154 existing hooks, flat templates/, extend existing audit tests where possible, CI-gated, integrate with /add-rule + /add-hook skills, conditional Contextual Trigger enforcement, ≥1 fenced code block in ADR Verification, monotonic ADR numbering WARN not BLOCK

### Known issues (deferred)

- **125 unanswered operator decisions** still surfaced by `/decision-triage` (mostly historical ADR open questions; today's research reports' decisions all answered).
- **`rich 14→15`**: blocked by cognee[memory] pin `rich<13.7.0` — pending cognee upstream upgrade.
- **`wrapt 1→2`**: deferred until OpenTelemetry transitives validate 2.x.
- **hermes-agent `default_backend()` cleanup**: 3 files, ~30 min, before cryptography 49.0.0.
- Phase 2 of `/add-rule` and `/add-hook` skill updates: templates referenced; full automation deferred.

## [0.17.0] - 2026-04-25 — "Defense-in-Depth + Research-First"

### Added — ADR-065 Tech Radar Curation Pipeline

- `docs/02-Decisions/adrs/ADR-065-radar-update-curation-pipeline.md` — design for `/radar-update` skill
- `skills/radar-update/SKILL.md` + `scripts/radar_merge.py` — Phase 1: skill + merge engine + dry-run
- `tests/unit/test_radar_merge.py` — 28 tests covering dedup, human-field preservation, classification routing, classification shift, fuzzy match, artifact parser, CHANGELOG updater, diff generation

### Added — ADR-066 Polyglot Language Boundaries

- `docs/02-Decisions/adrs/ADR-066-polyglot-language-boundaries.md` — bash/Python/Go role matrix + naming conventions + migration triggers
- `rules/python-naming.md` + `tests/audit/test_python_naming.py` — Python `snake_case` enforcement
- `rules/bash-naming.md` + `tests/audit/test_bash_naming.py` — bash kebab-case enforcement
- `.github/workflows/go-quality.yml` — `gofmt -l` + `go vet` CI gates for 3 Go modules

### Added — ADR-067 SKILL.md Defense-in-Depth (Phase 1)

- `docs/02-Decisions/adrs/ADR-067-frontmatter-defense-in-depth.md` — 3-layer defense pattern (template + hook + audit)
- `templates/skill-template.md` — canonical SKILL.md skeleton with explicit `<REQUIRED>` placeholders
- `hooks/skill-frontmatter-validator.sh` — PostToolUse Edit/Write hook (advisory by default, blocks on `COS_STRICT_SKILL_VALIDATION=1`); fast-path skips Python startup when input doesn't contain `SKILL.md` (17ms vs 70ms)
- `tests/audit/test_skill_descriptions_nonempty.py` — 3 audit tests using fixed `_fm()` parser
- Hook registered in 5 places (apply-efficiency-profile + set-security-profile + 3 hook-architecture-v2 profile JSONs)

### Added — ADR-068 Adaptive Test Runner Capacity

- `docs/02-Decisions/adrs/ADR-068-adaptive-test-runner-capacity.md` — cross-platform heuristic for choosing `-n auto|N|0` based on CPU/memory/load/battery/CI

### Added — ADR-069 Research-First Protocol

- `docs/02-Decisions/adrs/ADR-069-research-first-protocol.md` — 3-phase cycle (research → operator triage → implementation) for high-risk changes (4-dimensional risk scoring)
- `templates/agent-research-only.md` — boilerplate for research-only agent prompts
- `rules/research-first-protocol.md` + `tests/audit/test_research_reports_format.py` — operational policy + audit gate
- 3 research reports landed using the protocol:
  - `docs/06-Daily/reports/cos-init-migration-2026-04-24.md` — feasibility analysis (9 decision points)
  - `docs/06-Daily/reports/adr-067-phase-2-2026-04-24.md` — defense-in-depth Phase 2 scope (15 decisions)
  - `docs/06-Daily/reports/python-major-bumps-2026-04-24.md` — wrapt/rich/cryptography probe

### Added — Skills

- `/repo-scout` (renamed from `/eval-repo`, v2.0): scout external git repos for tech radar with bulk mode (`--batch <file>`), per-repo markdown artifacts, adoption signals (issue velocity, release cadence, CI health). Old `/eval-repo` kept as deprecated alias stub.
- `/radar-update` (Phase 1): merge `/repo-scout` evaluations into `docs/04-Concepts/patterns/ecosystem-tools.md` + `docs/05-Methodology/root/blocked-tools.md` with dry-run by default
- `/decision-triage`: aggregate unanswered operator decisions across research reports + ADRs into a single ranked view. Score-based urgency heuristic (initial 0/125 critical → 33/125 critical after improved scoring).
- `/deps-update`: automated audit + upgrade across Python deps, engram binary, Claude Code plugins, Docker images. Modes: `--audit` (default), `--apply`, `--apply --major`, `--dry-run`.

### Added — Auditing

- `tests/audit/test_python_naming.py`, `tests/audit/test_bash_naming.py` — naming convention enforcement
- `tests/audit/test_skill_descriptions_nonempty.py` — frontmatter contract enforcement
- `tests/audit/test_research_reports_format.py` — research report structure validation
- `tests/audit/test_packages_hooks_lib_symlinks.py` — packages/*/hooks/_lib symlink integrity
- `docs/04-Concepts/architecture/parser-coverage-audit-2026-04-24.md` — audit of 12 sibling parsers for `_fm()`-class gaps

### Changed — Breaking (pre-1.0)

- **35 Python scripts renamed** from kebab-case to snake_case (`scripts/*-*.py` → `scripts/*_*.py`). 143 caller files updated atomically. Backward compat: zero (no aliases). See `rules/python-naming.md` for migration table.
- **`/eval-repo` → `/repo-scout`** (skill rename). Old name kept as deprecated alias.
- **`cognee` removed from `[dev]` extra** — moved to `[memory]` extra. Reason: `kuzu` (cognee transitive) fails to build with `make clean` errors, blocking normal `uv sync --extra dev`. Opt-in explicitly with `uv sync --extra memory`.

### Fixed

- **`lib/session_hygiene._fm()` parser**: regex required `^---` at absolute file start, but every SKILL.md begins with `<!-- SCOPE: ... -->\n---`. 18 skills appeared as "No description" in CATALOG.md. Fix: `re.MULTILINE` flag + multi-line block scalar handling. Result: 0 "No description" entries.
- **2 sibling parsers had same bug**: `lib/pattern_detector._parse_frontmatter_keys` + `lib/smart_access.get_skill_frontmatter`. Same fix applied.
- **`packages/quality-gates/hooks/_lib` symlink missing** — caused `completion-gate.sh` crash. Fix: created symlink + audit test. Bonus: 17 OTHER `packages/*/hooks/` directories had the same latent bug — all fixed in one pass.
- **35 hyphenated Python script names** caused pytest importlib hacks + Python 3.14 dataclass resolution failures. Fix: snake_case rename + enforcement rule.
- **17 `gofmt` debt files** — cleared with `gofmt -w` (precondition for go-quality.yml CI to be green).
- **5 perf flakes under `-n auto`** — `@pytest.mark.xdist_group("perf")` to serialize within xdist (not `@pytest.mark.flaky`).
- **Project registry pollution** (post-v0.16.0): 3 stale "target" duplicates from pytest fixtures removed. Registry: 10 → 7 real entries.
- **Hook bookkeeping after `skill-frontmatter-validator.sh` add**: scorecard 154→155, baselines regenerated, orphan-hooks contract restored.
- **Rule bookkeeping after `bash-naming.md` add**: classified in CORE_RULES, stale file refs in pedagogical examples removed.

### Documentation

- `docs/04-Concepts/architecture/cos-update-vs-cos-cli-responsibility-analysis.md` — bash orchestrator vs Go package manager scope clarity (commit `583dc5c`)
- `rules/research-first-protocol.md` — when to use research-first vs background agents (4-dim scoring)

### Performance

- `hooks/contextual-rule-loader.sh` — already shipped in 0.16.0 (17x speedup); no regressions in 0.17.0
- `hooks/skill-frontmatter-validator.sh` fast-path — 70ms → 17ms per non-skill invocation
- `scripts/decision_triage.py` urgency heuristic — score-based (was returning 0 critical for 125 real decisions)

### Verified

- Python 7148/7154 unit tests pass (6 perf flakes confirmed under `-n auto`, all pass `-p no:xdist`)
- Shard-B 3967/3988 pass (21 pre-existing flakes from install-test resource contention, all pass `-p no:xdist`)
- 162 provider tests pass post-refactor

### Known issues (deferred)

- **Research report dual-location**: `.cognitive-os/reports/research/` (gitignored) vs `docs/06-Daily/reports/` — 3 reports exist in both, causing duplicates in `/decision-triage` output. Will be unified in next session.
- **rich 14→15 upgrade blocked**: `cognee[memory]` pins `rich<13.7.0`, breaking `[dev]+[memory]` combo. Reverted to `rich>=14`. Pending: cognee upstream upgrade.
- **wrapt 1→2** + **cryptography deprecated `default_backend()` in hermes-agent**: deferred per `docs/06-Daily/reports/python-major-bumps-2026-04-24.md`.
- **125 unanswered operator decisions** surfaced by `/decision-triage` (33 critical from today's research reports).

## [0.16.0] - 2026-04-24 — "Multi-Provider + Harness-Agnostic"

### Added — ADR-062 Multi-Provider Agent Loop

- `packages/llm-providers/` — 7 provider wrappers (qwen, openrouter, gemini, ollama, openai, deepseek, claude_sdk) behind uniform `REGISTRY` interface. Symlinked at `lib/providers`.
- `lib/openai_compatible_agent_loop.py` — generalized loop (renamed from `qwen_agent_loop.py`, which remains as a 65-line backward-compat shim).
- `lib/dispatch.py` — N-provider cascade with `ADVANCE_ON_ANY_FAILURE` vs `ADVANCE_ON_RATE_LIMIT_ONLY` policies; reads `llm_providers:` config block from `cognitive-os.yaml`.
- `scripts/smoke-multi-provider-fallback.sh` — per-provider smoke test with SIGALRM timeout (Unix-only).
- `/llm-status` skill v2.0.0 — provider inventory (tier, configured Y/N, advance policy, model_map); env key names detected (never values).
- Default cascade: `qwen,openrouter,gemini,ollama,claude` (zero direct Anthropic API key path). `openai`, `deepseek`, `claude_sdk` are opt-in.

### Added — ADR-063 Agent() Replication Strategy

- `docs/02-Decisions/adrs/ADR-063-agent-tool-replication-strategy.md` — reject full Agent() clone; adopt Python `claude-agent-sdk` (MIT) as triple-gated opt-in provider.
- `pyproject.toml` — `claude-sdk = ["claude-agent-sdk>=0.1"]` optional dep.

### Added — ADR-064 Harness-Agnostic Cognitive OS

- `docs/02-Decisions/adrs/ADR-064-harness-agnostic-cognitive-os.md` — architectural decision for Codex/Cursor/bare-CLI support. Names 4 integration surfaces (event capture, hook registration, skill invocation, sub-agent spawning). 10-15 session roadmap.

### Added — ADR-058 Phoenix Observability

- Langfuse purged. Phoenix OTel replaces it as the observability backend.
- `/phoenix-trace-ui` skill.

### Added — ADR-060 Local-Only Policy

- `docs/02-Decisions/adrs/ADR-060-local-only-optional-services.md` — pip-first, Docker-fallback, never-cloud-default.
- Opik removed. MemU wired with self-contained `memu-pg` backend.
- Profile-gated services: `cognee`, `nemo-guardrails`, `jupyter` behind `--profile memory|guardrails|jupyter`.
- `scripts/cos-bootstrap.sh` `--profile full` now correctly activates all three profiles (was silent no-op).

### Added — ADR-061 Focus Narrative + External Evidence

- `README.md` rewritten governance-first (leads with "governance layer for coding agents").
- `docs/08-References/root/vs-alternatives.md` — comparison with Hermes, Agent Zero, OpenClaw.
- `docs/08-References/migration-from/{vanilla-claude-code,hermes}.md` — recipe-style migration docs.
- `scripts/demo-governance.sh` — 5-minute governance value demo.
- `.github/workflows/weekly-public-metrics.yml` — Monday cron, updates badges (dogfood-score, REAL%, hook-wiring).

### Added — Measurement & Observability

- `/dogfood-score` — composite SO self-build maturity score (7 dimensions).
- `/component-reality-check` — drill-down into REAL/DORMANT/ASPIRATIONAL/METADATA classification for agentic primitives.
- `aspirational-audit.py` — new `ON_DEMAND` classification label.
- `scripts/so-vs-vanilla-benchmark.py` — A/B test harness with `COS_DISABLE_ALL_GOVERNANCE=1` master kill-switch.

### Added — Dependency Maintenance

- `scripts/deps-update.sh` — automated audit + upgrade (Python/engram binary/plugins/Docker). Modes: `--audit` (default), `--apply`, `--apply --major`, `--dry-run`. Handles GOBIN-versioned-path trap.
- `/deps-update` skill (os-only, haiku).
- `/validate-release` paso 6: advisory deps audit call (non-blocking).

### Added — Project Scaffold

- 10 pilot skill unit tests (+7.12 skill_coverage): `audit-integrity`, `bump-version`, `compat-test`, `doc-sync`, `dod-check`, `evaluate-plan`, `exhaustive-prompt`, `invariant-check`, `session-backlog`, `validate-config`.

### Changed — Breaking (pre-1.0)

- **Langfuse removed** — replaced by Phoenix OTel (ADR-058).
- **Opik removed** — replaced by MemU self-contained backend (ADR-060).
- `lib/qwen_agent_loop.py` → `lib/openai_compatible_agent_loop.py` (shim preserves backward compat but file is now deprecated).
- `lib/providers/` is a symlink into `packages/llm-providers/lib/` (new package).

### Changed — Dependencies

- `uv sync --upgrade`: pydantic 2.12.5 → 2.13.3, openai 2.30.0 → 2.32.0, click 8.1.8 → 8.3.3, certifi 2026.2.25 → 2026.4.22 (CA bundle), +transitives. Skipped major bumps: wrapt 1→2, rich 14→15, cryptography 46→47 (queued for dedicated review).
- engram binary: `dev` build → `v1.13.1` (via `go install`). `~/.local/bin/engram v1.10.2` remains as MCP server path (macOS Operon sandbox blocks the go-installed binary — documented in code).

### Fixed

- **Hook chain 17x speedup**: `contextual-rule-loader.sh` 2200ms → 130ms. Root cause: O(n×m) subprocess forks iterating rules × patterns. Fix: in-process regex indent detection.
- **`completion-gate.sh` crash**: `packages/quality-gates/hooks/_lib` symlink to root `hooks/_lib` was missing. Fix: created symlink. Follow-up: audit other `packages/*/hooks/` for same bug.
- **Project registry pollution**: 241 stale pytest fixture entries in `~/.cognitive-os/installations.json` (251 → 10 real projects). Root cause: `tests/integration/test_install_scope.py` didn't set `COS_REGISTRY_FILE`. Fix: env var in tests + `PYTEST_CURRENT_TEST` guard in `cos_registry_register` as belt-and-suspenders.
- **engram roundtrip test**: failed after upgrade to v1.13.1. Root cause: macOS Operon sandbox SIGKILL'd `~/go/bin/engram` spawned from Claude Code. Fix: `_resolve_engram_bin()` prefers `~/.local/bin/engram` (has Gatekeeper allow-list) over `~/go/bin/engram`.
- `cos-bootstrap.sh --profile full` — was silent no-op for nemo/jupyter/cognee. Now passes the three profile flags.
- 15 unit perf test failures root-caused (not marked flaky). Result: 7155 pass / 0 fail.
- Empty-stdin fast-exit budget: 200ms → 500ms (documented with rationale).
- `observability-trace.sh` orphan symlink (post-ADR-058 cleanup).
- `test_profiled_services` post-Opik removal (ADR-060).
- `test_rules_enforcement`: registered 6 previously hook-enforced-BROKEN rules (audit-trail, auto-rollback, confidence-gate, confidentiality-protection, agent-identity, pre-dev-readiness-gate, reinvention-prevention).

### Documentation

- `docs/02-Decisions/adrs/ADR-059-existential-validation.md` — 3-phase plan (prune humo / install-timing / core-extensions split).
- `docs/04-Concepts/patterns/cross-harness-authoring.md` — self-check protocol for SO-path changes.
- Package migration plan — 10 integrations mapped to future `cos` packages.
- Plugin marketplace design — `cos install` with 6-gate security audit pipeline.
- `install.sh` dual-mode installer (local source auto-detection + `--from` flag).
- Tech radar update — 26 Claude Code ecosystem tools analyzed (7 ADOPT, 19 WATCH, 5 BLOCK).
- Multi-tool architecture — adapter layer for OpenCode, Aider, Cursor support (foundation for ADR-064).
- 7 ecosystem integrations documented (agnix, claude-code-action, parry, Trail of Bits, recall, Usage Monitor, hcom).
- 19 WATCH repos deep-analyzed — 22 extractable patterns prioritized (P0-P3).

## [0.15.0] - 2026-04-21 — "ADR-047 Phase A + Decision Depth Gate"

> Note: VERSION file was stale at 0.9.0 when this release was cut, but
> tags v0.10.0 through v0.14.2 already existed remotely (patch releases
> not documented in this CHANGELOG). Bumped to 0.15.0 as next available.
> This is the first documented release since 0.12.0; intervening patches
> exist as tags only.

### Added — ADR-047 Session Lifecycle Management (Phase A shipped)

- `scripts/so-session-watchdog.py` — Phase A log-only daemon. Classifies sessions (HEALTHY / IDLE_OVER_TTL / ORPHANED / RESUMED_RECENTLY), writes `session-watchdog.jsonl`. NEVER kills.
- `lib/session_watchdog_lib.py` — layered Phase B liveness predicate: `should_kill() = parent_dead OR (ttl_exceeded AND heartbeat_stale AND metric_writes_stale AND cpu_idle_sustained)`. 4 checks, each tested independently.
- `hooks/session-heartbeat.sh` — PRIMARY liveness signal. Fires on `UserPromptSubmit` + `PreToolUse` wildcard. Atomic epoch write to `.cognitive-os/sessions/{id}/heartbeat`. Distinct from `state-heartbeat.sh` (crash recovery) and `agent_bus_metrics` (sub-agent watchdog).
- `hooks/session-watchdog-launcher.sh` — SessionStart singleton launcher (mirrors reaper-daemon-launcher pattern). mkdir-lock + pidfile guard with cmdline verification. Respects `COS_SESSION_WATCHDOG_DISABLE=1` opt-out.
- 39 new unit tests + 12 E2E smoke tests (zero daemon leaks verified).

### Added — Decision Depth Gate

- `rules/decision-depth-gate.md` — Q1-Q4 coherence analysis mandatory before closing "two values inconsistent" findings. Caught a real threshold bug (Phase A 1.0% vs Phase B 5.0% CPU — Phase A was under-predicting Phase B kills).
- `skills/invariant-check/` — scans ADR+lib pairs, emits pytest assertions for proposed invariants. On ADR-047 produces 7 invariants.
- `hooks/surface-fix-detector.sh` — PostToolUse advisory. Detects ~100% additive diffs with clarify/note trigger words.
- Cross-phase invariant test: Phase A threshold ≥ Phase B threshold (enforced in CI).

### Added — cos-config-audit validator

- `scripts/cos-config-audit.sh` — reports each cognitive-os.yaml section as IMPL / PARTIAL / ASPIR by checking agentic primitive wiring. Data-driven CONTRACTS list.
- `# STATUS:` annotations on 9 cognitive-os.yaml sections (indent-aware parser).
- `--strict` flag — exits 1 on DRIFT (annotation vs runtime mismatch).
- `meta.settings_freshness` contract — detects `apply-efficiency-profile.sh` changes without settings regen.
- CI workflow `.github/workflows/cos-config-audit.yml` — weekly cron + PR-triggered + drift comment.
- Current snapshot: **8 IMPL / 0 PARTIAL / 2 ASPIR** (ttft_watchdog + engram_mcp intentionally Phase B scope).

### Added — Startup Protocol

- `rules/startup-protocol.md` + `hooks/session-startup-protocol.sh` — 5-step checklist (mem_search → plans↔ADRs → work-queue → validator → execute). Fires on SessionStart, 55ms, advisory only.

### Added — Cross-platform CI discipline

- `hooks/_lib/portable.sh` — BSD/GNU abstraction with Python3 fallback (date arithmetic, sed in-place, stat mtime, readlink, timeout, sha256).
- 17 hooks + scripts migrated off direct BSD-only invocations.
- `.github/workflows/cross-platform.yml` + `Dockerfile.ci-linux` — Linux CI smoke job prevents regressions.
- `scripts/shellcheck-baseline.txt` captures known-acceptable violations.

### Added — Startup baseline + ADR-044 Phase 2

- `scripts/startup-benchmark.sh` + SLO 10 (≤50k tokens core payload) and SLO 11 (TTFT p95 <5s) in `rules/so-slo.md`.
- ADR-044 Phase 2: 85 skills gained `summary_line` frontmatter (-270 tokens / -8% in `CATALOG-COMPACT.md`).
- 4 slash commands (`/engram-help`, `/sdd-help`, `/skills-search`, `/rules-expand`) for lazy-load on demand.

### Added — `cos-update` auto-regen + runtime daemons visibility

- `cos-update.sh` auto-regenerates `.claude/settings.json` when `apply-efficiency-profile.sh` changes (SHA-tracked at `.cognitive-os/state/apply-efficiency-profile.sha`). Mirrors `uv sync` pattern.
- `hooks/cognitive-os-health.sh` + `scripts/cos-status.sh` gain Daemons section (watchdog, reaper) with PID/uptime/cmdline-match verification.
- `hooks/context-watchdog.sh` REGISTERED (was an existing gap: rule said "NOT registered" — now fires on PostToolUse wildcard with 50/70/85% thresholds).

### Fixed

- 4 files with unresolved merge conflict markers: `hooks/self-install.sh`, `hooks/_lib/dispatch_gate_check.py`, `lib/agent_health_monitor.py`, `lib/dispatch_helper.py`. Resolved favoring "Stashed changes" side.
- `tests/unit/test_nemo_integration.py::test_skill_has_frontmatter` — tolerates leading `<!-- SCOPE: -->` comment (scope-governance convention).
- `tests/unit/test_repomix_integration.py::test_config_in_yaml` — tolerates documented section removal.
- Reconciliation: 20 plans in `.cognitive-os/plans/features/` mapped against ADRs. 11 SUPERSEDED / 4 LIVE / 3 STALE. Summary at `docs/04-Concepts/architecture/plans-reconciliation-2026-04-21.md`.
- ADR-038 + ADR-039 published to canonical `docs/02-Decisions/adrs/` (publication gap closed).
- ADR-003 duplicate deleted (wrong path). ADR-027a 4 PENDING items resolved. ADR-028a 6 PENDING items resolved (6 done, 2 deferred, 1 partial).
- work-queue.json rotated (44 completed entries to Engram, 3 stale parked removed).

### Metrics this release

- **22 commits** over one session.
- 6177 / 6209 tests pass (99.5%). 32 remaining failures are pre-existing (tracked in `docs/06-Daily/reports/pre-existing-test-failures-2026-04-21.md`).
- Engram observations added: 15+ under `adr-047/*`, `cos-config-audit/*`, `plans-reconciliation/*`, `decision-depth-gate/*`.

---

## [0.12.0] - 2026-04-20 — "SO Reliability Framework"

### Added — ADR-028 (full 6-pillar reliability framework)

- **D1.A Observability foundation**: `lib/metric_event.py` (canonical JSONL event schema with ENOSPC-safe `append_event` returning bool), `docs/06-Daily/reports/metrics-census.md` (F-1..F-8 surfaced), rotation by size (>1 MiB) + age (>7 d) in `hooks/metrics-rotation.sh`, archive path aligned.
- **D1.B Process registry + reaper**: `lib/process_registry.py` + `ProcessRegistry` facade (register/deregister/cleanup_expired/detect_orphans), `scripts/so-reaper.sh`, `hooks/session-end-reap.sh`. 8 real call sites via `hooks/_lib/register-bg.sh`. Safe-kill contract: only registered PIDs can be terminated.
- **D1.C Agent liveness (via agent_bus adapter, ADR-028b)**: `lib/agent_bus_metrics.py` bridges `cos:agent:*:heartbeat` events to MetricEvent JSONL. No parallel heartbeat system — builds on existing `lib/agent_bus.py`. Proven end-to-end with orchestrator smoke test (commit `ae84bb8`).
- **D1.D Unified dashboard**: `scripts/so-vitals.sh` (human + `--json` modes) aggregates agents, registered processes, orphan suspects, JSONL sizes, Valkey reachability. Consumed by chaos and contract tests.
- **D2 Contract test suite**: `tests/contracts/test_orphan_hooks.py` (130 hooks → 0 orphans), `test_fd_invariant.py`, `test_ram_ceiling.py`, `test_p95_hook_latency.py`. 4 real contracts, all behavioral.
- **D3 Systematic audit**: `docs/06-Daily/reports/hook-audit-2026-04.md` — 130 hooks scanned, 18 findings (2 BLOCKER, 9 CONCERN, 7 SUGGESTION) with anti-pattern taxonomy.
- **D4 Systematic fix**: 2/2 BLOCKERs + 9/9 CONCERNs resolved. `test-baseline-diff.sh` deleted (WS11 Bug-1 pattern). `mlflow-sync` + 5 other hooks wrapped in `timeout 30`. `rate-limit-protection.sh` reduced to deprecation shim of `token-budget-monitor.sh`.
- **D5 SLOs + runbook + killswitch**: `rules/so-slo.md` (9 SLOs + error budget), `docs/05-Methodology/runbooks/so-incident-runbook.md`, `scripts/so-emergency-stop.sh`, `hooks/_lib/killswitch_check.sh` sourced by 124 of 129 hooks.
- **D6 Chaos suite**: `tests/chaos/` 5 scenarios (MCP kill, hook timeout, disk-full ENOSPC, FD exhaustion, git-reset cascade detector). All behavioral, 1 found a real gap and flipped to pass after D4 fix.

### Added — ADR-027 (SO slimming)

- **Phase 1**: `hooks/global-verify.sh` (PreToolUse/PostToolUse Agent, targeted test resolver + baseline/after diff), `lib/targeted_test_resolver.py` + `TargetedTestResolver` facade.
- **Phase 2**: `lib/ref_key_loader.py` — on-demand `[\`key\`]` → `rules/<key>.md` expansion with miss logging. Enables contextual rule inclusion.

### Added — ADR-029 (anti-reinvention gate)

- `hooks/reinvention-check.sh` wired at PreToolUse Agent. Grep-based similarity check against existing modules before sub-agent writes new file. Advisory in Phase A; hard-block at ≥0.7 similarity planned for Phase B.

### Added — Infrastructure

- `hooks/valkey-ensure.sh` auto-starts Valkey via OrbStack when `ORCHESTRATOR_MODE=executor`.
- `scripts/orchestrator.py` — dogfood entry point that uses `ClaudeExecutor` + `agent_bus_metrics` instead of the native Agent tool. Self-hosting loop proven (see `docs/06-Daily/reports/orchestrator-dogfood-smoke-test-2026-04-20.md`).
- 5 MetricEvent writer migrations (cost-events, consequence, skill-archive, telemetry, learning, singularity). 100% of cost-events rows migrated via `scripts/backfill-cost-events.py`.

### Changed

- `rules/RULES-COMPACT.md`: added `[\`so-slo\`]` ref-key on Infra line so ADR-028 SLO catalogue is loadable via the ref-key loader.
- `templates/agent-preamble.md`: 100 → 34 lines (trim). ~60% reduction in sub-agent context overhead (see `docs/06-Daily/reports/sub-agent-context-trim-2026-04-20.md`).
- `hooks/blast-radius.sh`: CRITICAL now requires `(INFRA AND SECURITY) OR file_score > 100` (was: `INFRA OR SECURITY OR file_score > 50`). Message compressed to one line.
- `hooks/inject-phase-context.sh`: gotchas dedup per session (first agent gets full text, subsequent get pointer).
- `hooks/_lib/task_panel_adapter.py`: skip tasks already in native Task panel (no more duplicate blocks).
- `lib/rate_limit_protection.py` → renamed to `lib/token_budget_monitor.py` (name collision with rate-limiter killed).

### Removed

- `lib/task_dag.py`, `lib/pipeline_executor.py`, `lib/workload_scheduler.py` — 65KB of dead code (`workflow-engine`), zero production callers.
- `hooks/test-baseline-diff.sh` — WS11 Bug-1 pattern (unbounded pytest at Stop).
- `lib/rate_limit_protection.py` + `hooks/rate-limit-protection.sh` reduced to deprecation shims.
- `valkey>=5.0` from `pyproject.toml` (redundant; `redis>=5.0.0` speaks the Valkey wire protocol).

### Fixed

- **F-4 SESSION_ID propagation**: `hooks/session-init.sh` now explicitly `export`s `COGNITIVE_OS_SESSION_ID` so 7 previously-invisible JSONL files (error-learning, repair-outcomes, remediation-registry, repair-queue, repair-dispatch, session-audit, singularity-events) can be written.
- **Singularity path**: `lib/singularity.py` `_SINGULARITY_LOG` was pointing to a dead `metrics/` directory; now writes to `.cognitive-os/metrics/`.
- **Hook registration sweep (debt register P1)**: `audit-id-enricher`, `auto-rollback-trigger`, `confidence-gate`, `confidentiality-enforcer`, `predev-completeness-check` registered (were on disk but never fired).
- **`metric_event.append_event` ENOSPC**: now returns `False` instead of raising, preventing cascading failures under disk pressure. `tests/chaos/test_disk_full_metrics.py` flipped from xfail to pass.
- **`scripts/so-vitals.sh` `cwd` bug**: `sys.path.insert(0, ".")` replaced with `"$PROJECT_DIR"` so the script works when invoked from outside the repo root.

### Documentation

- 4 new ADRs: `ADR-027a`, `ADR-028a`, `ADR-028b`, `ADR-029`.
- 9 audit / report documents under `docs/06-Daily/reports/` (metrics census, hook audit, debt register, artifact verification, reconciliation audit, smoke test, context trim, D1B TODO, validation).

### Dependencies

- `pyproject.toml` version bumped from `0.8.4` (stale — had not tracked releases since April 10) to `0.12.0` (aligned with tag).

## [Unreleased — superseded by 0.12.0] — UX1 + UX8 installer overhaul (ADR-002)

### Changed

- **BREAKING CHANGE (ADR-002)**: collapsed the 3-tier install profile system
  (`--lean` / `--standard` / `--full`) to 2 tiers:
  - `default` (no flag): 10 curated core skills + ~29 standard hooks + 14 core
    rules (~8000 tokens/session). Installed out of the box with no flag — the
    vanilla DX matches `git`, `gh`, and `claude`.
  - `--full`: every skill, hook, and rule (~142000 tokens/session). For mature
    projects and COS contributors.
- Legacy flags (`--lean`, `--standard`, `--minimal`) are now silently remapped
  to `default` with a stderr migration note — existing deployments continue to
  work without manual intervention.
- `install.sh`: new flag surface (`--full`, `--profile=NAME`, `--from`,
  `--force`, `--help`) with explicit ENV override (`COS_PROFILE`). Auto-detection
  removed; default is always `default`. Post-install summary now reports the
  number of skills exposed under `.claude/skills/` and warns on zero.
- `scripts/cos-init.sh`: accepts `--default` and `--full`; legacy flags
  silently map to `--default`. Skill install no longer gated behind non-minimal
  (both tiers ship skills). `DEFAULT_SKILLS` lists the 10 curated entries.
- `scripts/apply-efficiency-profile.sh`: 2-tier profile builder. The default
  tier now explicitly registers `auto-verify.sh`, `auto-refine.sh`,
  `dod-gate.sh`, `session-sanity.sh`, and `confidentiality-enforcer.sh`
  (PostToolUse Edit|Write) — the last fixes a regression where the enforcer
  had been dropped from the generated settings.
- `scripts/auto-update-projects.sh`: normalizes legacy registry `mode` values
  (`lean`, `standard`, `minimal`) to `default` before re-running `cos-init.sh`,
  so projects upgrade automatically on the next cascade.
- `scripts/generate-project-settings.sh`: `--default` is the canonical flag;
  legacy flags silently alias. `DEFAULT_HOOKS` now contains
  `confidentiality-enforcer.sh` and `session-sanity.sh`.
- `cognitive-os.yaml`: `efficiency.profile: default` and the `profiles:` map
  now defines only `default` and `full`.
- `docs/05-Methodology/usage/cos-status.md`: references updated to the 2-tier model.

### Migration

Users who previously ran `install.sh --lean` or `install.sh --standard` should
drop the flag. The new `default` tier is a strict superset of the old `lean`
tier and the same hook set as the old `standard` tier plus 10 curated skills.
See `docs/04-Concepts/architecture/harness-adoption-gap/ADR-002-simplify-profiles.md`.

## [0.9.0] - 2026-04-16 — "Self-Awareness"

Major stabilization release following the growth crisis post-mortem. OS can now
detect its own degradation patterns. See docs/04-Concepts/architecture/POST-MORTEM-2026-04.md.

### Added

**Self-awareness mechanisms (the 5 wounds prevented):**
- feat: cos-dispatch Go binary — vendor-agnostic hook dispatcher (Phases 1-4 complete)
  - 11 Go packages, all tests passing on Go 1.25.6
  - Validators + transformers + predicates + provider adapters for 5 AI coding agents
  - SQLite pattern tracker with 3 detector types (RepeatedFailure, PerfRegression, ErrorCluster)
  - 6 high-value bash hooks ported to Go (rate-limiter, rate-limit-protection, secret-detector, content-policy, completeness-checker, prompt-quality)
- feat: lib/pattern_detector.py — detects dead metadata, broken chains, phantom entries, structural tests
- feat: lib/adr_detector.py + hooks/adr-detector.sh — auto-generates ADR drafts on architectural git commits (8 weighted signals)
- feat: hooks/_lib/file_checker.sh — symlink-aware file existence checks (prevents false "missing" reports)
- feat: /audit-integrity skill — standardized audit with symlink resolution
- feat: /detect-patterns skill — on-demand pattern detection

**Agent amnesia prevention:**
- feat: templates/agent-mandatory-rules.md — rules injected into every sub-agent via SubagentStart hook
- feat: Updated hooks/subagent-context-injector.sh to load mandatory rules automatically

**Task panel bridge (ADR-024):**
- feat: hooks/_lib/task_bridge.py — correlates COS task_id with Claude Code tool_use_id
- feat: hooks/task-bridge-notify.sh — PostToolUse hook emitting hookSpecificOutput with COS orchestration state
- feat: Enhanced hooks/agent-prelaunch.sh to capture tool_use_id

**Cross-device memory:**
- feat: scripts/engram-sync.sh — project-scoped export/import of engram observations to git
- feat: Activated packages/engram-sync hooks (Stop + SessionStart)
- feat: First export: 544 observations at .engram/exports/luum-cognitive-os.jsonl

**Claude Code feature integration (ADR-021 adapter pattern):**
- feat: hooks/_lib/recap_adapter.py + hooks/recap-sync.sh — integrates session-wrapup with Claude Code /recap
- feat: hooks/task-panel-sync.sh + _lib/task_panel_adapter.py — exposes active-tasks to native UI
- feat: Registered TeammateIdle/TaskCreated/TaskCompleted events in settings.json
- feat: 3 prompt-type hooks (prompt-quality-llm, completeness-check-llm, confidence-gate-llm) — Haiku-evaluated advisories (ADR-022)
- feat: .claude/plugins/cos-monitors/plugin.json — native monitors manifest for background daemons
- feat: Skills sweep — 21 skills annotated with paths/disable-model-invocation/effort frontmatter

**Mutation via updatedInput (ADR-023):**
- feat: hooks/secret-detector.sh — redacts AWS/GitHub/Slack/Stripe/OpenAI secrets via updatedInput instead of blocking
- feat: hooks/blast-radius.sh — emits warnings via additionalContext, still allows execution
- feat: hooks/inject-phase-context.sh + context-diet.sh — migrated to native hookSpecificOutput.additionalContext

**CI gate for test quality:**
- feat: .github/workflows/test-quality.yml — mutation testing (cosmic-ray) + structural test detector on PRs
- feat: scripts/check-test-quality.py — AST-based classifier (CI/pre-commit/manual modes)
- feat: .cosmic-ray.toml — mutation testing config
- feat: Pre-commit Gate 3f blocks structural-only tests

**2-tier skill loading:**
- feat: skills/CATALOG-COMPACT.md — ~60% token reduction at session start (~2965 vs 7243)
- feat: scripts/generate-compact-catalog.py — regenerates from SKILL.md files
- feat: /catalog-full skill for on-demand full catalog

**Onboarding tooling:**
- feat: scripts/setup.sh — one-command dependency install (--minimal/--standard/--full)
- feat: scripts/doctor.sh — 12 health check categories
- feat: .go-version + goenv integration (Go 1.25.6)
- feat: docs/05-Methodology/setup/dependencies.md — comprehensive manifest by package manager

**ADRs (7 new, 16 retroactive = 22 total):**
- ADR-006 through ADR-020: retroactive coverage of March 21 - April 13 history
- ADR-021: Vendor-agnostic state with provider adapters
- ADR-022: Prompt-type hooks adoption (Haiku-evaluated)
- ADR-023: updatedInput pattern (mutate vs block)
- ADR-024: Task Panel Bridge (tool_use_id correlation)

**Institutional memory (4 living documents):**
- .cognitive-os/plans/roadmaps/stabilization-roadmap.md — status tracker
- docs/04-Concepts/architecture/FROZEN-BACKLOG.md — 30+ deferred plans
- docs/04-Concepts/architecture/LESSONS-LEARNED.md — 5 wounds + red flags
- docs/04-Concepts/architecture/POST-MORTEM-2026-04.md — full retrospective

**Testing:**
- 23 behavioral tests for 3 hook perf fixes (rate-limit-protection, dispatch-gate, completion-gate)
- 10 tests for Task Panel Bridge
- 18 tests for prompt-type hooks
- 22 tests for pattern detector
- 54 tests for auto-ADR detector
- docs/09-Quality/testing/README.md — comprehensive testing guide

### Fixed

**Performance (3 critical hooks):**
- perf: rate-limit-protection.sh — O(n) Python per-line → single call (30-90s → 50-100ms)
- perf: dispatch-gate.sh — 9 Python cold starts → 1 consolidated call (2.1s → 300-400ms)
- perf: completion-gate.sh — EXIT trap guarded behind Agent check (42s/session saved from non-Agent calls)
- perf: session-init.sh — 3 Python cold starts → 1 helper script

**Test infrastructure:**
- fix: 8 failing singularity tests — extracted _singularity_suggestion to _lib/ for isolated testing (20x faster)
- fix: test_app_services.py collection error (DockerContainer type annotation)

**Stale references cleanup:**
- fix: Removed 8 dead config flags + 18 dead config sections from cognitive-os.yaml
- fix: project.name corrected from my-project to luum-cognitive-os
- fix: Bifrost disabled in config to match docker-compose (ADR-011 superseded by ADR-018)
- fix: Removed 179 dead SCOPE/scope tags from 84 hooks + 95 libs (no code reads them)

### Removed

- 67 structural-only test files (false coverage) — tests/smoke/ deleted entirely
- 2,317 lines of structural tests pruned from 33 mixed behavior files
- 3 phantom skill entries from CATALOG.md (skills with no SKILL.md)
- 3 phantom entries from lib/skill_router.py routing table

### Changed

- Audience filtering now implemented in lib/skill_router.py (was metadata-only for 18 days)
- .claude/settings.json: 10 new hooks registered across events
- scripts/apply-efficiency-profile.sh + set-security-profile.sh: updated for all new hooks

### Notes

- Stabilization reached 98% per stabilization-roadmap.md
- 4 agentic primitives identified for reclassification to packages/ (deferred to v1.0 — see FROZEN-BACKLOG)
- 50+ commits in the 2-session stabilization effort

## [0.7.0] - 2026-04-09

### Added
- feat: Task DAG runner — declarative dependency graph for multi-agent workflows (lib/task_dag.py, 27 tests)
- feat: Agent health monitor — file-based dead/stuck agent detection without Valkey (lib/agent_health_monitor.py, 34 tests)
- feat: Queue drain on completion — blocked agents auto-enqueue and launch when slots free (lib/queue_drainer.py, 18 tests)
- feat: CronCreate scheduled drain — periodic 5-min fallback for stuck queues (lib/scheduled_drain.py, 15 tests)
- feat: Auto-repair with worktree isolation — fixes applied in isolated git worktree, verify, merge or discard (20 tests)
- feat: Auto-rewrite on skill failure — 3+ failures triggers /optimize-skill suggestion (9 tests)
- feat: Escalation detection wired — agents emit ESCALATION: markers, completion-gate detects (20 tests)
- feat: PromptBuilder — integrates context_diet + prompt_cache for token-efficient agent prompts (36 tests)
- feat: Dynamic model routing — DEGRADE/PROMOTE feed into model selection, budget-aware downgrade (16 tests)
- feat: E2E self-repair smoke test — 5 scenarios proving full feedback loop works (29 tests)
- feat: Closed-loop consequence tests — DEGRADE/PROMOTE/DISABLE validated end-to-end (22 tests)
- feat: cos-bootstrap.sh — one-command project setup (env, Docker, Langfuse, rules sync) (16 tests)
- feat: cos-update.sh — idempotent update for existing installations
- feat: scripts/test-all.sh — unified test runner with pytest-xdist parallel execution
- feat: Claude HUD — real-time statusline showing context %, costs, agents (ADOPT, MIT)
- feat: Langfuse v3 integration — traces + scores via OTEL API, auto-provisioned API keys
- feat: scripts/setup-langfuse.sh — fully automated Langfuse key provisioning (no manual steps)
- docs: self-repair-guide.md — user guide explaining what developers will experience
- docs: getting-started.md — updated with bootstrap, test runner, self-repair sections

### Fixed
- fix: agent preamble injection — sub-agents now emit TRUST_REPORT (was missing, cascade root cause)
- fix: cost tracking $0.00 — tool_response parsed as string, model-aware pricing (was always zero)
- fix: detect_success false positive — "0 failed" in Trust Report matched FAIL pattern
- fix: SeaweedFS healthcheck — localhost→127.0.0.1 (IPv6 resolution bug in Alpine)
- fix: integration test timeout — 30s→300s for testcontainers (was killing Docker fixtures)
- fix: hardcoded project path in test_e2e_flows.py — now uses Path(__file__).parents[2]
- fix: record_completion.py Langfuse API updated to v3 (OTEL-based spans + generations)
- fix: consequence-history.jsonl cleaned — 83% test data removed (600→102 real entries)

### Wired (hooks connected to settings.json)
- error-learning.sh (PostToolUse/Bash) — captures test/lint/build failures
- consequence-evaluator.sh (PostToolUse/Agent) — PROMOTE/DEGRADE/DISABLE decisions
- pre-compaction-flush.sh (PreCompact) — saves state before context reset
- resource-check.sh (PreToolUse/Agent) — budget enforcement blocks over-spend
- confidence-gate.sh (PostToolUse/Agent) — blocks low-confidence results in production

### Changed
- requirements.txt: langfuse>=3.0, pytest-xdist>=3.5 added
- rules/RULES-COMPACT.md: added skill-rewrite and task-dag references
- templates/agent-preamble.md: full escalation protocol with 5 signal types

## [0.8.4] - 2026-04-10

### Added
- feat: security-tools-landscape.md — implementation status tracking for P1/P2 security tools
- feat: tero-testing and mantis-security packages with cos-package.yaml manifests
- feat: workflow YAML files (feature-pipeline.yaml, bugfix-pipeline.yaml) in .cognitive-os/workflows/
- fix: pre-commit hook Gate 3e made advisory (warn, not block) on malformed workflow YAML
- fix: pre-commit hook gate labels standardized (Gate 3a–3e) for consistent detection
- fix: docs/00-MOCs/entrypoints/INDEX.md version updated to v0.8.4

## [0.1.0] - 2026-03-27

### Added
- SDD Pipeline: 12-phase structured development (explore -> archive)
- Safety Mesh: 13-layer defense system (clarification gate, blast radius, scope proportionality, etc.)
- Anti-Hallucination: ground truth checker, cross-verifier, claim validator
- Agent Security: least privilege permissions, audit trail, time-scoped access
- Performance Monitor: p50/p95/p99 latency, overhead tracking, bottleneck detection
- Token Economy: cost dashboard, decomposition rule, 5 token principles
- Cost Predictor: historical predictions based on real API response data
- Planning Poker: multi-agent task estimation with consensus algorithm
- System Knowledge Graph: 232 agentic primitives, 430 edges, `cos map` command
- Agent Bus: Valkey pub/sub with heartbeat, progress tracking, file lock registry
- Estimation Calibration: predict -> actual -> adjust loop with per-agent factors
- Singularity Controller: MAPE-K autonomous loop (7 monitors, 9 event types)
- Issue-to-PR Pipeline: GitHub issue -> SDD -> PR (automated)
- Webhook Trigger: FastAPI server for GitHub event-driven automation
- Batch Runner: sequential multi-change SDD execution
- Primitive Linter: overlap detection, size warnings, registration checks
- Research Protocol: systematic investigation methodology (DISCOVER -> ANALYZE -> COMPARE -> SYNTHESIZE)
- 80+ skills including: contract-drift, deep-research, audit-website, confidence-check, self-review, persistent-agent, security-audit, pentest-self
- 60+ rules covering: quality, security, performance, cost, architecture
- 60+ hooks for lifecycle automation
- 30+ Python lib modules
- 2 Go CLI tools: cos (package manager v0.1) and cos-test (TUI test runner)
- 2200+ automated tests (pytest + Go tests)
- Testcontainers for 17 Docker services
- Coexistence with existing .claude/ configurations (cos/ namespace)
- Self-hosting (dogfooding): the OS builds itself using its own tools

### Architecture
- 5-Layer Clean Architecture for Agent OS (Rules -> Skills -> Hooks -> Libs -> Externals)
- Dependency rule: dependencies only point inward
- UX Principles: invisible safety, AI as driver, progressive disclosure

### Infrastructure
- Docker Compose with 18 services (Langfuse, Opik, Cognee, Valkey, LiteLLM, etc.)
- Multi-model routing (Anthropic, OpenAI, Google, DeepSeek, local)
- Engram persistent memory with organized topic keys
