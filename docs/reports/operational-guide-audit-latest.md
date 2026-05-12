# Operational Guide Audit — 2026-05-12T14:41:37Z

> Per ADR-274. Schema: `operational-guide-audit/v1`.
> Audits all `docs/adrs/ADR-*.md` for §Operational Guide section presence
> on maintainer-tier accepted capability ADRs.

## How to read this doc (operational guide for this audit)

This audit answers: **which ADRs are missing operator-readable context?**

Verdict taxonomy:
- `compliant` — has §Operational Guide with ≥3 documented sub-sections
- `partial` — has §Operational Guide but < 3 sub-sections (needs expansion)
- `missing` — subject to contract but no §Operational Guide present (needs backfill)
- `exempt` — explicitly marked `<!-- adr-274-exempt: <reason> -->`
- `not-applicable` — tombstone, superseded, or non-maintainer/non-capability

Priority for backfill (only applies to `missing`/`partial`):
- **P0** — accepted ≤ 30 days ago
- **P1** — maintainer-tier accepted (older)
- **P2** — everything else

Per ADR-274: rules without enforcement are honored ~50% historically;
this audit + `adr-section-validator.sh` extension close the loop.

**Total ADRs scanned**: 285

## By verdict

| Verdict | Count |
|---|---:|
| compliant | 17 |
| exempt | 1 |
| missing | 45 |
| not-applicable | 222 |

## By priority (backfill queue)

| Priority | Count |
|---|---:|
| P0 | 45 |

## Backfill list (P0 + P1)

| Priority | ADR | Verdict | Age (days) | Path |
|---|---|---|---:|---|
| P0 | `ADR-177-activate-skill-lifecycle-promotion-ladder` | missing | 6 | `docs/adrs/ADR-177-activate-skill-lifecycle-promotion-ladder.md` |
| P0 | `ADR-188-mandatory-skill-invocation-at-high-confidence` | missing | 6 | `docs/adrs/ADR-188-mandatory-skill-invocation-at-high-confidence.md` |
| P0 | `ADR-159-agents-md-native-structural-harness-batch` | missing | 7 | `docs/adrs/ADR-159-agents-md-native-structural-harness-batch.md` |
| P0 | `ADR-160-rules-mcp-structural-harness-batch-and-kiro-adapter-design` | missing | 7 | `docs/adrs/ADR-160-rules-mcp-structural-harness-batch-and-kiro-adapter-design.md` |
| P0 | `ADR-161-remote-control-plane-and-provider-adapter-boundary` | missing | 7 | `docs/adrs/ADR-161-remote-control-plane-and-provider-adapter-boundary.md` |
| P0 | `ADR-162-task-lifecycle-interruption-question-worktree-pr-protocol` | missing | 7 | `docs/adrs/ADR-162-task-lifecycle-interruption-question-worktree-pr-protocol.md` |
| P0 | `ADR-163-cos-instance-installer` | missing | 7 | `docs/adrs/ADR-163-cos-instance-installer.md` |
| P0 | `ADR-164-host-cli-bridge-security-boundary` | missing | 7 | `docs/adrs/ADR-164-host-cli-bridge-security-boundary.md` |
| P0 | `ADR-165-proof-drill-and-smoke-opt-in-primitives` | missing | 7 | `docs/adrs/ADR-165-proof-drill-and-smoke-opt-in-primitives.md` |
| P0 | `ADR-166-expected-skip-registry-and-opt-in-test-lanes` | missing | 7 | `docs/adrs/ADR-166-expected-skip-registry-and-opt-in-test-lanes.md` |
| P0 | `ADR-167-proof-drill-selector-and-acc-evidence-adapter` | missing | 7 | `docs/adrs/ADR-167-proof-drill-selector-and-acc-evidence-adapter.md` |
| P0 | `ADR-168-cross-device-dependency-installation` | missing | 7 | `docs/adrs/ADR-168-cross-device-dependency-installation.md` |
| P0 | `ADR-169-dashboard-formal-demotion` | missing | 7 | `docs/adrs/ADR-169-dashboard-formal-demotion.md` |
| P0 | `ADR-171-reject-paperclip-integration` | missing | 7 | `docs/adrs/ADR-171-reject-paperclip-integration.md` |
| P0 | `ADR-172-multi-surface-ui-architecture` | missing | 7 | `docs/adrs/ADR-172-multi-surface-ui-architecture.md` |
| P0 | `ADR-175-research-quality-enforcement` | missing | 7 | `docs/adrs/ADR-175-research-quality-enforcement.md` |
| P0 | `ADR-176-skillstore-and-analysis-trigger` | missing | 7 | `docs/adrs/ADR-176-skillstore-and-analysis-trigger.md` |
| P0 | `ADR-179-rules-auto-derive-routing` | missing | 7 | `docs/adrs/ADR-179-rules-auto-derive-routing.md` |
| P0 | `ADR-180-lifecycle-promotion-activation` | missing | 7 | `docs/adrs/ADR-180-lifecycle-promotion-activation.md` |
| P0 | `ADR-181-adr-relevance-suggester` | missing | 7 | `docs/adrs/ADR-181-adr-relevance-suggester.md` |
| P0 | `ADR-182-branch-ownership-lock` | missing | 7 | `docs/adrs/ADR-182-branch-ownership-lock.md` |
| P0 | `ADR-183-cross-session-event-log` | missing | 7 | `docs/adrs/ADR-183-cross-session-event-log.md` |
| P0 | `ADR-184-manager-of-managers-daemon` | missing | 7 | `docs/adrs/ADR-184-manager-of-managers-daemon.md` |
| P0 | `ADR-185-cross-agent-audit-findings` | missing | 7 | `docs/adrs/ADR-185-cross-agent-audit-findings.md` |
| P0 | `ADR-186-context-budget-enforcement` | missing | 7 | `docs/adrs/ADR-186-context-budget-enforcement.md` |
| P0 | `ADR-139-account-agnostic-multi-provider-runtime` | missing | 8 | `docs/adrs/ADR-139-account-agnostic-multi-provider-runtime.md` |
| P0 | `ADR-141-engram-cloud-cross-instance-replication` | missing | 8 | `docs/adrs/ADR-141-engram-cloud-cross-instance-replication.md` |
| P0 | `ADR-142-compliance-audit-air-gapped-surface` | missing | 8 | `docs/adrs/ADR-142-compliance-audit-air-gapped-surface.md` |
| P0 | `ADR-143-closure-discipline-gate` | missing | 8 | `docs/adrs/ADR-143-closure-discipline-gate.md` |
| P0 | `ADR-144-hook-enforced-rule-projection-contract` | missing | 8 | `docs/adrs/ADR-144-hook-enforced-rule-projection-contract.md` |
| P0 | `ADR-148-adr-authoring-primitive` | missing | 8 | `docs/adrs/ADR-148-adr-authoring-primitive.md` |
| P0 | `ADR-149-primitive-duplication-audit` | missing | 8 | `docs/adrs/ADR-149-primitive-duplication-audit.md` |
| P0 | `ADR-150-acc-projection-profiles-and-harness-registry` | missing | 8 | `docs/adrs/ADR-150-acc-projection-profiles-and-harness-registry.md` |
| P0 | `ADR-151-consumer-availability-classification` | missing | 8 | `docs/adrs/ADR-151-consumer-availability-classification.md` |
| P0 | `ADR-152-shell-ci-projection-and-local-surface-defaults` | missing | 8 | `docs/adrs/ADR-152-shell-ci-projection-and-local-surface-defaults.md` |
| P0 | `ADR-153-acc-fail-new-and-harness-proof-boundary` | missing | 8 | `docs/adrs/ADR-153-acc-fail-new-and-harness-proof-boundary.md` |
| P0 | `ADR-154-multi-ide-structural-harness-projection` | missing | 8 | `docs/adrs/ADR-154-multi-ide-structural-harness-projection.md` |
| P0 | `ADR-155-shell-ci-formal-harness` | missing | 8 | `docs/adrs/ADR-155-shell-ci-formal-harness.md` |
| P0 | `ADR-156-qwen-code-structural-harness-projection` | missing | 8 | `docs/adrs/ADR-156-qwen-code-structural-harness-projection.md` |
| P0 | `ADR-157-kimi-code-cli-structural-harness-projection` | missing | 8 | `docs/adrs/ADR-157-kimi-code-cli-structural-harness-projection.md` |
| P0 | `ADR-158-ai-agent-harness-landscape-and-proof-backlog` | missing | 8 | `docs/adrs/ADR-158-ai-agent-harness-landscape-and-proof-backlog.md` |
| P0 | `ADR-130-suspend-claude-api-workflows` | missing | 9 | `docs/adrs/ADR-130-suspend-claude-api-workflows.md` |
| P0 | `ADR-131-local-ci-migration` | missing | 9 | `docs/adrs/ADR-131-local-ci-migration.md` |
| P0 | `ADR-138-flow-contract-schema` | missing | 9 | `docs/adrs/ADR-138-flow-contract-schema.md` |
| P0 | `ADR-044-context-payload-slimming` | missing | 22 | `docs/adrs/ADR-044-context-payload-slimming.md` |
