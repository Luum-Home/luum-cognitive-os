# ADR Implementation Status Backfill — 2026-05-12

## Scope

This report records the first implementation-status backfill after the ADR status taxonomy split. The pass is intentionally conservative: it updates ADRs that already have YAML frontmatter and leaves prose-only historical ADRs in `Active / Unclassified` until gradual frontmatter migration.

## Result

| Metric | Count |
|---|---:|
| Total ADR files | 283 |
| ADRs with YAML frontmatter | 87 |
| Active ADRs | 245 |
| Active with implementation_status | 74 |
| Active still unclassified because prose-only/no frontmatter | 171 |

## Active Navigation Buckets

| Bucket | Count |
|---|---:|
| Active / Implemented | 49 |
| Active / Partial | 22 |
| Active / Partial / Blocked | 1 |
| Active / Deferred | 1 |
| Active / Planned | 1 |
| Active / Unclassified | 171 |

## Decision Rules Used

- `implemented`: ADR text explicitly says implemented/materialized/shipped, or frontmatter already used `status: implemented` and declared implementation files/tests.
- `partial`: ADR text says partially implemented, first slice implemented, design-only/contract-only scope, or remaining runtime/wiring work is explicitly called out.
- `partial-blocked`: some slice is done and a named external/local blocker remains.
- `deferred`: the ADR intentionally delays implementation or keeps optional work unimplemented.
- `planned`: accepted direction exists, but work is a future trajectory rather than a shipped slice.
- `not-applicable`: terminal/tombstone/superseded/exploration records with no implementation surface.

## Backfilled Active ADRs

| ADR | Decision | Implementation | Evidence summary |
|---|---|---|---|
| [044](../adrs/ADR-044-context-payload-slimming.md) | `accepted` | `partial-blocked` | **Authors**: Agent C (startup-optimization initiative, stream 3/4) |
| [052](../adrs/ADR-052-provider-benchmark-harness.md) | `implemented` | `implemented` | **Implemented for the no-cost offline harness scope.** The repository now ships a |
| [053](../adrs/ADR-053-dispatch-auto-optimizer.md) | `implemented` | `implemented` | **Implemented for reviewed proposal generation.** The repository now ships a |
| [105](../adrs/ADR-105-claim-verification-contract.md) | `implemented` | `partial` | **Author**: Maintainer |
| [116](../adrs/ADR-116-multi-session-coordination-primitives.md) | `accepted` | `partial` | **Author**: Maintainer (operator) + Software Architect (analysis) |
| [119](../adrs/ADR-119-session-filesystem-reaper.md) | `implemented` | `implemented` | Accepted — 2026-05-02. Related: ADR-102, ADR-106, ADR-111, ADR-116, ADR-117. |
| [121](../adrs/ADR-121-foundation-hardening-program.md) | `accepted` | `partial` | Accepted — 2026-05-02 |
| [123](../adrs/ADR-123-operational-stability-friction-reduction.md) | `implemented` | `implemented` | Implemented — 2026-05-08 status sync |
| [129](../adrs/ADR-129-safe-worktree-removal.md) | `accepted` | `implemented` | Accepted. Implemented in commit `d5ecda43` with the shared |
| [130](../adrs/ADR-130-suspend-claude-api-workflows.md) | `accepted` | `implemented` | Accepted. |
| [131](../adrs/ADR-131-local-ci-migration.md) | `accepted` | `implemented` | Accepted. Implemented in the same PR that lands this ADR. Companion |
| [137](../adrs/ADR-137-operational-trajectory-governance-layer-to-embedded-runtime.md) | `accepted` | `planned` | **Accepted** for the trajectory itself. The directional commitment (B → A, defined below) is firm. |
| [138](../adrs/ADR-138-flow-contract-schema.md) | `accepted` | `implemented` | **Accepted and materialized for first lab registration.** The companion |
| [139](../adrs/ADR-139-account-agnostic-multi-provider-runtime.md) | `implemented` | `implemented` | **Accepted — Implemented** as the credential and billing posture for all COS runtime surfaces — local maintainer, cloud worker, and ephemeral sandbox. |
| [140](../adrs/ADR-140-cross-os-containerized-deployment.md) | `accepted` | `implemented` | **Accepted — Implemented** as the containerised deployment shape for COS cloud |
| [141](../adrs/ADR-141-engram-cloud-cross-instance-replication.md) | `implemented` | `implemented` | **Accepted — Implemented** as the replication strategy for Engram observations across COS instances. Local SQLite remains authoritative. Cloud is replication-on |
| [142](../adrs/ADR-142-compliance-audit-air-gapped-surface.md) | `implemented` | `implemented` | **Accepted — Implemented** as the compliance posture and audit-trail bridge for all COS cloud worker surfaces. |
| [143](../adrs/ADR-143-closure-discipline-gate.md) | `accepted` | `implemented` | **Accepted.** Closure discipline is now a first-class blocking maintainer gate. |
| [144](../adrs/ADR-144-hook-enforced-rule-projection-contract.md) | `accepted` | `implemented` | Accepted. Hook-enforced rule exclusions are now a projection contract, not a prose convention. |
| [148](../adrs/ADR-148-adr-authoring-primitive.md) | `accepted` | `implemented` | **Accepted** — 2026-05-04 |
| [149](../adrs/ADR-149-primitive-duplication-audit.md) | `accepted` | `implemented` | **Accepted** — 2026-05-04 |
| [150](../adrs/ADR-150-acc-projection-profiles-and-harness-registry.md) | `accepted` | `implemented` | **Accepted** — 2026-05-04 |
| [151](../adrs/ADR-151-consumer-availability-classification.md) | `implemented` | `implemented` | **Implemented for manifest/classification scope** — 2026-05-04. The consumer availability manifest, ACC adapter, and contract tests named below exist; future sc |
| [152](../adrs/ADR-152-shell-ci-projection-and-local-surface-defaults.md) | `implemented` | `implemented` | **Implemented for shell/CI projection and local-surface defaults** — 2026-05-04. The projection manifest, projector, ACC integration, and artifact-status extrac |
| [153](../adrs/ADR-153-acc-fail-new-and-harness-proof-boundary.md) | `accepted` | `implemented` | **Accepted** — 2026-05-04 |
| [154](../adrs/ADR-154-multi-ide-structural-harness-projection.md) | `implemented` | `implemented` | **Implemented for structural projection scope** — 2026-05-04. OpenCode, VS Code Copilot, and Cursor project-local projections are generated and tested; this doe |
| [155](../adrs/ADR-155-shell-ci-formal-harness.md) | `accepted` | `implemented` | **Accepted** — 2026-05-04 |
| [156](../adrs/ADR-156-qwen-code-structural-harness-projection.md) | `implemented` | `implemented` | **Implemented for structural projection scope** — 2026-05-04. Qwen Code project-local settings/context projection is generated and tested; account-backed Qwen r |
| [157](../adrs/ADR-157-kimi-code-cli-structural-harness-projection.md) | `implemented` | `implemented` | **Implemented for structural CLI projection scope** — 2026-05-04. Kimi Code project-local CLI context/config projection is generated and tested; authenticated C |
| [158](../adrs/ADR-158-ai-agent-harness-landscape-and-proof-backlog.md) | `accepted` | `implemented` | **Accepted** — 2026-05-04 |
| [159](../adrs/ADR-159-agents-md-native-structural-harness-batch.md) | `accepted` | `implemented` | **Accepted** — 2026-05-05 |
| [160](../adrs/ADR-160-rules-mcp-structural-harness-batch-and-kiro-adapter-design.md) | `implemented` | `implemented` | **Implemented for structural projection and Kiro design scope** — 2026-05-05. The seven rules/MCP harness projections and Kiro adapter design artifacts exist an |
| [161](../adrs/ADR-161-remote-control-plane-and-provider-adapter-boundary.md) | `implemented` | `implemented` | **Implemented for boundary/inventory scope** — 2026-05-05. The remote ingress versus provider/executor adapter boundary, alternatives manifest, report, manual t |
| [162](../adrs/ADR-162-task-lifecycle-interruption-question-worktree-pr-protocol.md) | `implemented` | `partial` | **Implemented for contract scope** — 2026-05-05. The task lifecycle schema, contract tests, and manual proof checklist exist; full queue/worker/PR runtime enfor |
| [163](../adrs/ADR-163-cos-instance-installer.md) | `accepted` | `partial` | **Accepted** — 2026-05-05 |
| [164](../adrs/ADR-164-host-cli-bridge-security-boundary.md) | `implemented` | `partial` | **Implemented for the design-only security contract scope** — 2026-05-05. |
| [165](../adrs/ADR-165-proof-drill-and-smoke-opt-in-primitives.md) | `implemented` | `implemented` | **Implemented for the proof-drill registry and smoke opt-in primitive scope** — 2026-05-05. The ADR closes the governed registry, agent procedure, manual proof  |
| [166](../adrs/ADR-166-expected-skip-registry-and-opt-in-test-lanes.md) | `implemented` | `implemented` | **Implemented for the first enforcement slice** — 2026-05-05. |
| [167](../adrs/ADR-167-proof-drill-selector-and-acc-evidence-adapter.md) | `implemented` | `implemented` | **Implemented for the proof-drill selector, evidence recorder, ACC adapter, instance-profile projection, and runtime-flag registry scope** — 2026-05-05. Live pr |
| [168](../adrs/ADR-168-cross-device-dependency-installation.md) | `implemented` | `partial` | **Implemented for the manifest-driven dry-run installer and credential-safe |
| [169](../adrs/ADR-169-dashboard-formal-demotion.md) | `accepted` | `implemented` | Accepted. |
| [171](../adrs/ADR-171-reject-paperclip-integration.md) | `accepted` | `implemented` | Accepted. Supersedes ADR-043. |
| [172](../adrs/ADR-172-multi-surface-ui-architecture.md) | `accepted` | `partial` | Accepted. Supersedes ADR-170. |
| [173](../adrs/ADR-173-surface-5-research-gate.md) | `accepted` | `deferred` | **Accepted** — 2026-05-06. |
| [174](../adrs/ADR-174-auto-derived-primitive-routing.md) | `accepted` | `implemented` | As of 2026-05-05, `lib/skill_router.py` contains a hand-maintained |
| [174b](../adrs/ADR-174b-prevention-followup.md) | `accepted` | `implemented` | Accepted. This ADR owns Part A (auto-generation includes `routing_patterns:`) and the implemented propose-only soak evaluator. The actual advisory-to-blocking p |
| [175](../adrs/ADR-175-research-quality-enforcement.md) | `accepted` | `implemented` | **Accepted** — 2026-05-05 |
| [176](../adrs/ADR-176-skillstore-and-analysis-trigger.md) | `accepted` | `implemented` | Accepted. |
| [177](../adrs/ADR-177-activate-skill-lifecycle-promotion-ladder.md) | `accepted` | `implemented` | Accepted. |
| [179](../adrs/ADR-179-rules-auto-derive-routing.md) | `accepted` | `partial` | **Accepted** — 2026-05-05 |
| [180](../adrs/ADR-180-lifecycle-promotion-activation.md) | `accepted` | `implemented` | Accepted. |
| [181](../adrs/ADR-181-adr-relevance-suggester.md) | `accepted` | `implemented` | Accepted — 2026-05-05 |
| [182](../adrs/ADR-182-branch-ownership-lock.md) | `accepted` | `implemented` | **Accepted.** Implemented as the ADR-182 branch-lock hook, library, CLI wrappers, and contract tests. Filed in response to the cross-session collision incident |
| [183](../adrs/ADR-183-cross-session-event-log.md) | `accepted` | `implemented` | **Accepted.** Implemented as an extension of the existing `lib/session_bus.py` plus emit/context hooks. Companion to ADR-182. ADR-182 prevents *conflicts*; ADR- |
| [184](../adrs/ADR-184-manager-of-managers-daemon.md) | `accepted` | `implemented` | **Accepted.** First implementation landed as a local file-queue daemon for ADR identity arbitration. Long-horizon refinement of ADR-163 (cos-instance-installer) |
| [185](../adrs/ADR-185-cross-agent-audit-findings.md) | `accepted` | `implemented` | **Accepted.** Implemented as the directed message bus, inbox/context hooks, CLI, and tests. Fourth architectural layer companion to ADR-182 (branch |
| [186](../adrs/ADR-186-context-budget-enforcement.md) | `accepted` | `implemented` | **Accepted.** Implemented as `lib/context_budget.py`, a shared hook accountant, a UserPromptSubmit meter, and hook-level budget checks. Filed in response to tod |
| [188](../adrs/ADR-188-mandatory-skill-invocation-at-high-confidence.md) | `accepted` | `implemented` | **Accepted (2026-05-06).** Implementation landed on session branch |
| [239](../adrs/ADR-239-isolated-worktree-default-for-write-agents.md) | `accepted` | `implemented` | Accepted. This ADR records the corrective decision after the 2026-05-08 |
| [241](../adrs/ADR-241-consolidated-cos-bypass-allowlist.md) | `accepted` | `partial` | Accepted — Slice A implemented. Shared resolver, cheatsheet, target hook integration, and behavior tests are active; broad ecosystem bypass consolidation remain |
| [242](../adrs/ADR-242-git-filter-repo-wrapper-preserves-remote.md) | `accepted` | `partial` | Accepted — Slice A implemented. `scripts/cos-filter-repo-wrap.sh` preserves remotes, refuses idempotent reruns, writes recovery artifacts, and `lib/history_sani |
| [243](../adrs/ADR-243-post-rewrite-push-collision-exception.md) | `accepted` | `partial` | Accepted — Slice A implemented. History sanitization writes `.cognitive-os/runtime/last-rewrite.json`; push-collision detection consumes it to allow matching po |
| [244](../adrs/ADR-244-trust-report-claim-validator-must-enforce.md) | `accepted` | `partial` | Accepted — Slice A implemented. `scripts/claim_enforcer.py` enforces structured `verification:` evidence for high-stakes claims, `hooks/claim-validator.sh` bloc |
| [245](../adrs/ADR-245-chaos-tests-readonly-production-source.md) | `accepted` | `partial` | Accepted — Slice A implemented. `tests/chaos/conftest.py` installs `chaos_readonly_workspace`, restores source mutations under `lib/`, `scripts/`, and `hooks/`, |
| [246](../adrs/ADR-246-release-transaction-freeze.md) | `accepted` | `partial` | Accepted — Slice A implemented. `scripts/cos-release-freeze` now provides `--prepare`, `--begin`, `--status`, and `--end`; receipts are written under `.cognitiv |
| [247](../adrs/ADR-247-manifest-driven-postmortem-regression-audits.md) | `accepted` | `partial` | Accepted. This ADR documents the policy correction made after ADR-242 through |
| [248](../adrs/ADR-248-control-plane-audit-loop.md) | `accepted` | `partial` | Accepted — Slice A implemented. |
| [249](../adrs/ADR-249-primitive-behavioral-proof-anti-overfit-tests.md) | `accepted` | `partial` | Accepted — Slice A implemented. |
| [250](../adrs/ADR-250-skill-router-retrieval-adapter-boundary.md) | `accepted` | `partial` | Accepted — Slice A implemented. |
| [251](../adrs/ADR-251-agent-orchestration-adapter-boundary.md) | `accepted` | `partial` | Accepted — Slice A implemented. |
| [252](../adrs/ADR-252-capability-coverage-matrix-and-feature-reality-ledger.md) | `accepted` | `partial` | Accepted — Slice A implemented. |
| [269](../adrs/ADR-269-mandatory-adr-reference-for-history-rewrites.md) | `accepted` | `implemented` | Accepted (2026-05-11). Implementation lands in companion commit set. |
| [270](../adrs/ADR-270-legal-compliance-workflow-automation.md) | `accepted` | `implemented` | Accepted (2026-05-11). Implementation lands in companion commit. |
| [273](../adrs/ADR-273-pending-truth-ledger-and-bilateral-verification.md) | `accepted` | `partial` | Accepted — Slice A implemented (schema + aggregator); Slices B (verifier) and C (hooks) tracked. |

## Remaining Work

- 171 Active ADRs remain unclassified because they are prose-only historical records. Migrating them should happen in reviewable batches of 25-40 ADRs with frontmatter creation and evidence snippets.
- The audit now fails frontmatter ADRs that omit `implementation_status`; it intentionally keeps prose-only ADRs as warnings to avoid blind mass edits.
