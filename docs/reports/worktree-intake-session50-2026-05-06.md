# Worktree Intake — session/50c35ce9-remove-paperclip-multi-surface — 2026-05-06

**Active branch reviewed from**: `session/41961ce2-paperclip-rejection-multi-surface` at `338c1067`.

**Sibling worktree reviewed read-only**: `<workspace-parent>/luum-agent-os-session50-paperclip-purge` at branch `session/50c35ce9-remove-paperclip-multi-surface` (`2aba0fe9` plus uncommitted WIP).

## Verdict

Do **not** merge or cherry-pick the sibling worktree as a batch. Its WIP is a stale purge branch that overlaps with work already landed on the active branch and, in several files, would remove newer ADR-174/182/183/185/186 governance wiring.

Safe outcome: keep the active branch as source of truth; keep the sibling worktree quarantined/read-only until the operator decides whether to delete it after this report is reviewed.

## Counts

- Status entries reviewed: **206**.
- Entries byte-identical to active branch: **124**.
- Entries not byte-identical: **82**.
- Rejected-surface paths: **29**.
- ADR tombstone paths: **11**.
- Generated/report paths: **34**.

## Decision counts

| Decision | Count |
|---|---:|
| `NO_ACTION_ALREADY_IN_CURRENT` | 124 |
| `NO_ACTION_PURGE_ALREADY_LANDED` | 29 |
| `NO_IMPORT_STALE_OR_NON_CRITICAL_DRIFT` | 34 |
| `REJECT_COLLIDES_WITH_ACTIVE_ADR_NUMBERS` | 5 |
| `REJECT_MALFORMED_OR_STALE_CONFIG_DRIFT` | 2 |
| `REJECT_OLDER_ROUTER_BEHAVIOR` | 1 |
| `REJECT_OLDER_TOMBSTONE_TOOL` | 3 |
| `REJECT_OR_ALREADY_SUPERSEDED_BY_ADR174_V2` | 1 |
| `REJECT_STALE_PROJECTION` | 7 |

## Stash review

Six local stashes exist on the active branch. They are auto-pre-agent snapshots with overlapping file sets. They primarily contain older paperclip archive/delete attempts plus older routing/config edits. They are **not** safe to apply wholesale; at most they are archaeology if a specific file must be recovered.

| Stash | Files | File-list digest | First paths |
|---|---:|---|---|
| `stash@{0}` | 47 | `453724efda38` | `M	CHANGELOG.md, M	README.md, M	VERSION, M	cognitive-os.yaml, M	docker-compose.cognitive-os.yml, M	docs/INDEX.md, M	docs/adrs/ADR-043-paperclip-local-daemon.md, M	docs/adrs/ADR-044-context-payload-slimming.md` |
| `stash@{1}` | 47 | `453724efda38` | `M	CHANGELOG.md, M	README.md, M	VERSION, M	cognitive-os.yaml, M	docker-compose.cognitive-os.yml, M	docs/INDEX.md, M	docs/adrs/ADR-043-paperclip-local-daemon.md, M	docs/adrs/ADR-044-context-payload-slimming.md` |
| `stash@{2}` | 47 | `453724efda38` | `M	CHANGELOG.md, M	README.md, M	VERSION, M	cognitive-os.yaml, M	docker-compose.cognitive-os.yml, M	docs/INDEX.md, M	docs/adrs/ADR-043-paperclip-local-daemon.md, M	docs/adrs/ADR-044-context-payload-slimming.md` |
| `stash@{3}` | 42 | `c27610b7448d` | `M	CHANGELOG.md, M	README.md, M	VERSION, M	cognitive-os.yaml, M	docker-compose.cognitive-os.yml, M	docs/INDEX.md, M	docs/adrs/ADR-043-paperclip-local-daemon.md, M	docs/adrs/ADR-044-context-payload-slimming.md` |
| `stash@{4}` | 42 | `c27610b7448d` | `M	CHANGELOG.md, M	README.md, M	VERSION, M	cognitive-os.yaml, M	docker-compose.cognitive-os.yml, M	docs/INDEX.md, M	docs/adrs/ADR-043-paperclip-local-daemon.md, M	docs/adrs/ADR-044-context-payload-slimming.md` |
| `stash@{5}` | 40 | `5f489c0a4c75` | `M	CHANGELOG.md, M	README.md, M	VERSION, M	cognitive-os.yaml, M	docker-compose.cognitive-os.yml, M	docs/INDEX.md, M	docs/adrs/ADR-043-paperclip-local-daemon.md, M	docs/adrs/ADR-044-context-payload-slimming.md` |

## Notable findings

1. The sibling worktree has **206** status entries, not 156 in this snapshot.
2. The active branch already contains the intentional rejected-surface purge for runtime, tests, packages, scripts, and hook files. No sibling import is needed for those paths.
3. `ADR-171-tombstone.md` through `ADR-175-tombstone.md` in the sibling worktree are rejected because the active branch owns those numbers with real ADRs.
4. The sibling `scripts/adr_tombstone.py` is older and less safe: it allows replacing active ADRs by default. The active branch version refuses active ADR replacement unless explicitly forced.
5. The sibling hook projections and settings are stale: importing them would remove cross-session peer context, message inbox, branch lock, event emit, routing validators, and context-budget wiring.
6. `tests/contracts/test_no_rejected_surface_references.py` exposed a real gap during intake: it scanned historical docs/ADRs/postmortems as if they were active runtime surfaces. The contract was tightened to scan active operational paths only.

## File-level matrix

| Status | Path | Category | Decision | Rationale |
|---|---|---|---|---|
| ` M` | `.claude/settings.json` | `hook-projection` | `REJECT_STALE_PROJECTION` | The session50 version removes or omits newer ADR-182/183/185/186 hook wiring; keep active branch projection. |
| ` M` | `.codex/hooks.json` | `hook-projection` | `REJECT_STALE_PROJECTION` | The session50 version removes or omits newer ADR-182/183/185/186 hook wiring; keep active branch projection. |
| ` M` | `.cognitive-os/plans/architecture/core-vs-extensions-migration-plan.md` | `plan` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `.cognitive-os/plans/architecture/cos-instance-installer-implementation-plan.md` | `plan` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `.cognitive-os/plans/features/component-scope-classification.md` | `plan` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `.cognitive-os/plans/features/docker-to-pip-migration.md` | `plan` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `.cognitive-os/plans/features/docs-to-skills-audit.md` | `plan` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `.cognitive-os/plans/features/skill-atomicity-audit.md` | `plan` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `.cognitive-os/plans/features/so-existential-validation-2026-04-24.md` | `plan` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `CHANGELOG.md` | `other` | `NO_IMPORT_STALE_OR_NON_CRITICAL_DRIFT` | Reviewed as part of session50 intake; no evidence it improves the active branch over current commits. |
| ` M` | `Makefile` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `cognitive-os.yaml` | `other` | `REJECT_MALFORMED_OR_STALE_CONFIG_DRIFT` | Diff shows stale/malformed fragments and omitted newer governance hooks; keep active branch config. |
| ` M` | `dashboard/ARCHIVED.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docker-compose.cognitive-os.yml` | `other` | `REJECT_MALFORMED_OR_STALE_CONFIG_DRIFT` | Diff shows stale/malformed fragments and omitted newer governance hooks; keep active branch config. |
| ` M` | `docs/INDEX.md` | `other` | `NO_IMPORT_STALE_OR_NON_CRITICAL_DRIFT` | Reviewed as part of session50 intake; no evidence it improves the active branch over current commits. |
| ` M` | `docs/SESSION-ADR-CLOSURE-2026-05-04.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/SESSION-HANDOFF-2026-05-05-headless-service-runtime.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/acc/latest.json` | `generated-or-report` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/adrs/ADR-009-package-architecture.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/adrs/ADR-018-docker-to-pip-migration.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/adrs/ADR-027.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/adrs/ADR-042-valkey-local-daemon.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` D` | `docs/adrs/ADR-043-paperclip-local-daemon.md` | `rejected-surface` | `NO_ACTION_PURGE_ALREADY_LANDED` | The active branch already removed active runtime/test/package files for the rejected surface. |
| ` M` | `docs/adrs/ADR-045-postgres-local-daemon.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/adrs/ADR-091-headless-clustered-runtime-direction.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/adrs/ADR-092-harness-skills-sync-path.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/adrs/ADR-093-simplify-profiles.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/adrs/ADR-161-remote-control-plane-and-provider-adapter-boundary.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/adrs/ADR-162-task-lifecycle-interruption-question-worktree-pr-protocol.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/adrs/ADR-169-dashboard-formal-demotion.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/adrs/ADR-170-operator-cli-as-primary-ui-surface.md` | `other` | `NO_IMPORT_STALE_OR_NON_CRITICAL_DRIFT` | Reviewed as part of session50 intake; no evidence it improves the active branch over current commits. |
| ` M` | `docs/architecture.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/architecture/FROZEN-BACKLOG.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/architecture/POST-MORTEM-2026-04.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/architecture/core-vs-extensions-audit-2026-04-20.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/architecture/core-vs-extensions.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/architecture/functional-audit/scorecard-hooks.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/architecture/functional-audit/scorecard-packages-squads-agents.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/architecture/functional-audit/scorecard-skills.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/architecture/harness-adoption-gap/diagnosis.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/architecture/harness-adoption-gap/scripts-audit-D-profile-uninstall.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/architecture/host-cli-bridge-security-boundary.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/architecture/infrastructure-service-catalog.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/architecture/plans-reconciliation-2026-04-21.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/architecture/service-control-plane-implementation-plan.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/architecture/tooling-stack-rationalization.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/archive/plans/docs-hook-rule-candidates.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/archive/plans/docs-rescan-results.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/competitive-analysis.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/component-audit.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/component-sources.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/dashboard-architecture.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/faq.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/getting-started.md` | `other` | `NO_IMPORT_STALE_OR_NON_CRITICAL_DRIFT` | Reviewed as part of session50 intake; no evidence it improves the active branch over current commits. |
| ` M` | `docs/hook-security-profiles.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/manual-tests/local-connected-systems-validation.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/manual-tests/remote-control-plane-boundary.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/manual-tests/task-lifecycle-worktree-pr-flow.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/multi-model-factory.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/onboarding-wizard-design.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` D` | `docs/paperclip-integration.md` | `rejected-surface` | `NO_ACTION_PURGE_ALREADY_LANDED` | The active branch already removed active runtime/test/package files for the rejected surface. |
| ` M` | `docs/plug-and-play.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/release/v1.0-release-criteria.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/reports/artifact-verification-2026-04-20.md` | `generated-or-report` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/reports/aspirational-audit-2026-04-20.md` | `generated-or-report` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/reports/aspirational-audit-2026-05-02.md` | `generated-or-report` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/reports/aspirational-audit-2026-05-03.md` | `generated-or-report` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/reports/aspirational-audit-2026-05-05.md` | `generated-or-report` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/reports/claim-proof-latest.json` | `generated-or-report` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/reports/d1b-clients-todo.md` | `generated-or-report` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/reports/debt-register-2026-04-20.md` | `generated-or-report` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/reports/docker-image-review-2026-05-04.md` | `generated-or-report` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/reports/docs-execution-latest.json` | `generated-or-report` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/reports/docs-execution-latest.md` | `generated-or-report` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/reports/hook-audit-2026-04.md` | `generated-or-report` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/reports/metrics-census.md` | `generated-or-report` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/reports/next-session-handoff-2026-04-20.md` | `generated-or-report` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` D` | `docs/reports/paperclip-integration-audit-2026-05-05.md` | `rejected-surface,generated-or-report` | `NO_ACTION_PURGE_ALREADY_LANDED` | The active branch already removed active runtime/test/package files for the rejected surface. |
| ` D` | `docs/reports/paperclip-live-smoke-2026-05-05.md` | `rejected-surface,generated-or-report` | `NO_ACTION_PURGE_ALREADY_LANDED` | The active branch already removed active runtime/test/package files for the rejected surface. |
| ` M` | `docs/reports/pre-existing-test-failures-2026-04-21.md` | `generated-or-report` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/reports/primitive-coverage-latest.json` | `generated-or-report` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/reports/primitive-coverage-latest.md` | `generated-or-report` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/reports/primitive-duplication-triage-latest.md` | `generated-or-report` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/reports/primitive-readiness-ledger-hooks-latest.json` | `generated-or-report` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/reports/primitive-readiness-ledger-hooks-latest.md` | `generated-or-report` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/reports/primitive-readiness-ledger-rules-latest.json` | `generated-or-report` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/reports/primitive-readiness-ledger-scripts-latest.json` | `generated-or-report` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/reports/primitive-readiness-ledger-scripts-latest.md` | `generated-or-report` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/reports/primitive-readiness-ledger-skills-latest.json` | `generated-or-report` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/reports/primitive-row-audit-latest.json` | `generated-or-report` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/reports/prune-triage-2026-05-01.md` | `generated-or-report` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/reports/punch-list-hooks.md` | `generated-or-report` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/reports/reconciliation-audit-2026-04-20.md` | `generated-or-report` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/reports/remote-control-plane-alternatives-2026-05-05.md` | `generated-or-report` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/reports/test-suite-repair-ledger-2026-04-24.md` | `generated-or-report` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/reports/validation-worktree-mutation-postmortem-2026-05-02.md` | `generated-or-report` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/roadmap.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/self-usage-audit.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/setup/dependencies.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/testing.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/tool-stack.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `docs/ui-platforms-evaluation.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `env.example` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` D` | `hooks/_lib/paperclip-notify.sh` | `rejected-surface` | `NO_ACTION_PURGE_ALREADY_LANDED` | The active branch already removed active runtime/test/package files for the rejected surface. |
| ` M` | `hooks/_lib/registration-allowlist.txt` | `other` | `NO_IMPORT_STALE_OR_NON_CRITICAL_DRIFT` | Reviewed as part of session50 intake; no evidence it improves the active branch over current commits. |
| ` M` | `hooks/cognitive-os-health.sh` | `other` | `NO_IMPORT_STALE_OR_NON_CRITICAL_DRIFT` | Reviewed as part of session50 intake; no evidence it improves the active branch over current commits. |
| ` M` | `hooks/infra-health.sh` | `other` | `NO_IMPORT_STALE_OR_NON_CRITICAL_DRIFT` | Reviewed as part of session50 intake; no evidence it improves the active branch over current commits. |
| ` D` | `hooks/paperclip-agent-status.sh` | `rejected-surface` | `NO_ACTION_PURGE_ALREADY_LANDED` | The active branch already removed active runtime/test/package files for the rejected surface. |
| ` D` | `hooks/paperclip-cost-stream.sh` | `rejected-surface` | `NO_ACTION_PURGE_ALREADY_LANDED` | The active branch already removed active runtime/test/package files for the rejected surface. |
| ` D` | `hooks/paperclip-sdd-sync.sh` | `rejected-surface` | `NO_ACTION_PURGE_ALREADY_LANDED` | The active branch already removed active runtime/test/package files for the rejected surface. |
| ` D` | `hooks/paperclip-squad-sync.sh` | `rejected-surface` | `NO_ACTION_PURGE_ALREADY_LANDED` | The active branch already removed active runtime/test/package files for the rejected surface. |
| ` D` | `hooks/paperclip-sync.sh` | `rejected-surface` | `NO_ACTION_PURGE_ALREADY_LANDED` | The active branch already removed active runtime/test/package files for the rejected surface. |
| ` D` | `hooks/paperclip-task-sync.sh` | `rejected-surface` | `NO_ACTION_PURGE_ALREADY_LANDED` | The active branch already removed active runtime/test/package files for the rejected surface. |
| ` D` | `infra/paperclip/init-config.sh` | `rejected-surface` | `NO_ACTION_PURGE_ALREADY_LANDED` | The active branch already removed active runtime/test/package files for the rejected surface. |
| ` D` | `lib/paperclip_client.py` | `rejected-surface` | `NO_ACTION_PURGE_ALREADY_LANDED` | The active branch already removed active runtime/test/package files for the rejected surface. |
| ` M` | `lib/singularity.py` | `other` | `NO_IMPORT_STALE_OR_NON_CRITICAL_DRIFT` | Reviewed as part of session50 intake; no evidence it improves the active branch over current commits. |
| ` M` | `lib/skill_router.py` | `other` | `REJECT_OLDER_ROUTER_BEHAVIOR` | Session50 removes disk-skill validation added for ADR-174 coverage; keep active branch. |
| ` M` | `lib/smart_infra.py` | `other` | `NO_IMPORT_STALE_OR_NON_CRITICAL_DRIFT` | Reviewed as part of session50 intake; no evidence it improves the active branch over current commits. |
| ` M` | `manifests/adr-closure-metadata.yaml` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `manifests/cos-instance-implementation-phases.yaml` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `manifests/cos-instance-profiles.yaml` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `manifests/hook-registration-classification.yaml` | `other` | `NO_IMPORT_STALE_OR_NON_CRITICAL_DRIFT` | Reviewed as part of session50 intake; no evidence it improves the active branch over current commits. |
| ` M` | `manifests/optional-hook-aliases.json` | `other` | `NO_IMPORT_STALE_OR_NON_CRITICAL_DRIFT` | Reviewed as part of session50 intake; no evidence it improves the active branch over current commits. |
| ` M` | `manifests/reduction-demotions.json` | `other` | `NO_IMPORT_STALE_OR_NON_CRITICAL_DRIFT` | Reviewed as part of session50 intake; no evidence it improves the active branch over current commits. |
| ` M` | `manifests/remote-control-plane-alternatives.yaml` | `other` | `NO_IMPORT_STALE_OR_NON_CRITICAL_DRIFT` | Reviewed as part of session50 intake; no evidence it improves the active branch over current commits. |
| ` M` | `manifests/runtime-hardcoding-allowlist.yaml` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `manifests/silent-failure-allowlist.yaml` | `other` | `NO_IMPORT_STALE_OR_NON_CRITICAL_DRIFT` | Reviewed as part of session50 intake; no evidence it improves the active branch over current commits. |
| ` M` | `manifests/task-lifecycle-schema.yaml` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `packages/cos-index/index/packages.yaml` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` D` | `packages/ecosystem-tools/lib/paperclip_client.py` | `rejected-surface` | `NO_ACTION_PURGE_ALREADY_LANDED` | The active branch already removed active runtime/test/package files for the rejected surface. |
| ` M` | `packages/ecosystem-tools/skills/automaker-bridge/SKILL.md` | `other` | `NO_IMPORT_STALE_OR_NON_CRITICAL_DRIFT` | Reviewed as part of session50 intake; no evidence it improves the active branch over current commits. |
| ` D` | `packages/paperclip-integration/README.md` | `rejected-surface` | `NO_ACTION_PURGE_ALREADY_LANDED` | The active branch already removed active runtime/test/package files for the rejected surface. |
| ` D` | `packages/paperclip-integration/cos-package.yaml` | `rejected-surface` | `NO_ACTION_PURGE_ALREADY_LANDED` | The active branch already removed active runtime/test/package files for the rejected surface. |
| ` D` | `packages/paperclip-integration/hooks/_lib` | `rejected-surface` | `NO_ACTION_PURGE_ALREADY_LANDED` | The active branch already removed active runtime/test/package files for the rejected surface. |
| ` D` | `packages/paperclip-integration/hooks/paperclip-agent-status.sh` | `rejected-surface` | `NO_ACTION_PURGE_ALREADY_LANDED` | The active branch already removed active runtime/test/package files for the rejected surface. |
| ` D` | `packages/paperclip-integration/hooks/paperclip-cost-stream.sh` | `rejected-surface` | `NO_ACTION_PURGE_ALREADY_LANDED` | The active branch already removed active runtime/test/package files for the rejected surface. |
| ` D` | `packages/paperclip-integration/hooks/paperclip-sdd-sync.sh` | `rejected-surface` | `NO_ACTION_PURGE_ALREADY_LANDED` | The active branch already removed active runtime/test/package files for the rejected surface. |
| ` D` | `packages/paperclip-integration/hooks/paperclip-squad-sync.sh` | `rejected-surface` | `NO_ACTION_PURGE_ALREADY_LANDED` | The active branch already removed active runtime/test/package files for the rejected surface. |
| ` D` | `packages/paperclip-integration/hooks/paperclip-sync.sh` | `rejected-surface` | `NO_ACTION_PURGE_ALREADY_LANDED` | The active branch already removed active runtime/test/package files for the rejected surface. |
| ` D` | `packages/paperclip-integration/hooks/paperclip-task-sync.sh` | `rejected-surface` | `NO_ACTION_PURGE_ALREADY_LANDED` | The active branch already removed active runtime/test/package files for the rejected surface. |
| ` D` | `packages/paperclip-integration/skills/paperclip-dashboard/SKILL.md` | `rejected-surface` | `NO_ACTION_PURGE_ALREADY_LANDED` | The active branch already removed active runtime/test/package files for the rejected surface. |
| ` M` | `packages/quality-gates/hooks/claim-validator.sh` | `other` | `NO_IMPORT_STALE_OR_NON_CRITICAL_DRIFT` | Reviewed as part of session50 intake; no evidence it improves the active branch over current commits. |
| ` M` | `packages/quality-gates/hooks/completion-gate.sh` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `packages/quality-gates/hooks/confidence-gate.sh` | `other` | `NO_IMPORT_STALE_OR_NON_CRITICAL_DRIFT` | Reviewed as part of session50 intake; no evidence it improves the active branch over current commits. |
| ` M` | `rules/infra-health.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `rules/resource-governance.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `scripts/_lib/settings-driver-claude-code.sh` | `hook-projection` | `REJECT_STALE_PROJECTION` | The session50 version removes or omits newer ADR-182/183/185/186 hook wiring; keep active branch projection. |
| ` M` | `scripts/apply-efficiency-profile.sh` | `hook-projection` | `REJECT_STALE_PROJECTION` | The session50 version removes or omits newer ADR-182/183/185/186 hook wiring; keep active branch projection. |
| ` M` | `scripts/ci-setup.sh` | `other` | `NO_IMPORT_STALE_OR_NON_CRITICAL_DRIFT` | Reviewed as part of session50 intake; no evidence it improves the active branch over current commits. |
| ` M` | `scripts/cos-bootstrap.sh` | `other` | `NO_IMPORT_STALE_OR_NON_CRITICAL_DRIFT` | Reviewed as part of session50 intake; no evidence it improves the active branch over current commits. |
| ` M` | `scripts/cos-core-skills-check.sh` | `other` | `NO_IMPORT_STALE_OR_NON_CRITICAL_DRIFT` | Reviewed as part of session50 intake; no evidence it improves the active branch over current commits. |
| ` D` | `scripts/cos-paperclip-local.sh` | `rejected-surface` | `NO_ACTION_PURGE_ALREADY_LANDED` | The active branch already removed active runtime/test/package files for the rejected surface. |
| ` M` | `scripts/cos_classify_coverage.py` | `other` | `NO_IMPORT_STALE_OR_NON_CRITICAL_DRIFT` | Reviewed as part of session50 intake; no evidence it improves the active branch over current commits. |
| ` M` | `scripts/cos_init.py` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `scripts/doctor.sh` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `scripts/setup.sh` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `skills/CATALOG-COMPACT.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `skills/CATALOG.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `skills/REGISTRY.lock` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `skills/cognitive-os-status/SKILL.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` D` | `skills/paperclip-dashboard` | `rejected-surface` | `NO_ACTION_PURGE_ALREADY_LANDED` | The active branch already removed active runtime/test/package files for the rejected surface. |
| ` M` | `skills/resource-governor/SKILL.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `skills/reverse-engineer/SKILL.md` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `templates/security-profiles/minimal.json` | `hook-projection` | `REJECT_STALE_PROJECTION` | The session50 version removes or omits newer ADR-182/183/185/186 hook wiring; keep active branch projection. |
| ` M` | `templates/security-profiles/paranoid.json` | `hook-projection` | `REJECT_STALE_PROJECTION` | The session50 version removes or omits newer ADR-182/183/185/186 hook wiring; keep active branch projection. |
| ` M` | `templates/security-profiles/standard.json` | `hook-projection` | `REJECT_STALE_PROJECTION` | The session50 version removes or omits newer ADR-182/183/185/186 hook wiring; keep active branch projection. |
| ` M` | `tests/audit/test_hooks_contracts.py` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `tests/behavior/test_core_skills_check.py` | `other` | `NO_IMPORT_STALE_OR_NON_CRITICAL_DRIFT` | Reviewed as part of session50 intake; no evidence it improves the active branch over current commits. |
| ` M` | `tests/behavior/test_hooks_batch2.py` | `other` | `NO_IMPORT_STALE_OR_NON_CRITICAL_DRIFT` | Reviewed as part of session50 intake; no evidence it improves the active branch over current commits. |
| ` D` | `tests/behavior/test_paperclip_integration_complete.py` | `rejected-surface` | `NO_ACTION_PURGE_ALREADY_LANDED` | The active branch already removed active runtime/test/package files for the rejected surface. |
| ` M` | `tests/behavior/test_safety_mesh.py` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `tests/contracts/EXCLUDED_HOOKS.txt` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `tests/contracts/test_remote_control_plane_alternatives.py` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` M` | `tests/contracts/test_service_sunset_policy.py` | `other` | `NO_IMPORT_STALE_OR_NON_CRITICAL_DRIFT` | Reviewed as part of session50 intake; no evidence it improves the active branch over current commits. |
| ` M` | `tests/integration/conftest.py` | `other` | `NO_IMPORT_STALE_OR_NON_CRITICAL_DRIFT` | Reviewed as part of session50 intake; no evidence it improves the active branch over current commits. |
| ` M` | `tests/integration/test_databases.py` | `other` | `NO_IMPORT_STALE_OR_NON_CRITICAL_DRIFT` | Reviewed as part of session50 intake; no evidence it improves the active branch over current commits. |
| ` M` | `tests/integration/test_e2e_flows.py` | `other` | `NO_IMPORT_STALE_OR_NON_CRITICAL_DRIFT` | Reviewed as part of session50 intake; no evidence it improves the active branch over current commits. |
| ` M` | `tests/integration/test_fresh_install_canary.py` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` D` | `tests/integration/test_paperclip_local_daemon.py` | `rejected-surface` | `NO_ACTION_PURGE_ALREADY_LANDED` | The active branch already removed active runtime/test/package files for the rejected surface. |
| ` M` | `tests/integration/test_platform_services.py` | `other` | `NO_IMPORT_STALE_OR_NON_CRITICAL_DRIFT` | Reviewed as part of session50 intake; no evidence it improves the active branch over current commits. |
| ` M` | `tests/integration/test_service_health.py` | `other` | `NO_IMPORT_STALE_OR_NON_CRITICAL_DRIFT` | Reviewed as part of session50 intake; no evidence it improves the active branch over current commits. |
| ` M` | `tests/unit/test_deps_update_docker_audit.py` | `other` | `NO_IMPORT_STALE_OR_NON_CRITICAL_DRIFT` | Reviewed as part of session50 intake; no evidence it improves the active branch over current commits. |
| ` M` | `tests/unit/test_efficiency_stress.py` | `other` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| ` D` | `tests/unit/test_paperclip_client.py` | `rejected-surface` | `NO_ACTION_PURGE_ALREADY_LANDED` | The active branch already removed active runtime/test/package files for the rejected surface. |
| ` M` | `tests/unit/test_reverse_engineer.py` | `other` | `NO_IMPORT_STALE_OR_NON_CRITICAL_DRIFT` | Reviewed as part of session50 intake; no evidence it improves the active branch over current commits. |
| ` M` | `tests/unit/test_skill_router.py` | `other` | `NO_IMPORT_STALE_OR_NON_CRITICAL_DRIFT` | Reviewed as part of session50 intake; no evidence it improves the active branch over current commits. |
| ` M` | `tests/unit/test_smart_infra.py` | `other` | `NO_IMPORT_STALE_OR_NON_CRITICAL_DRIFT` | Reviewed as part of session50 intake; no evidence it improves the active branch over current commits. |
| `??` | `docs/adrs/ADR-003-tombstone.md` | `adr-tombstone` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| `??` | `docs/adrs/ADR-004-tombstone.md` | `adr-tombstone` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| `??` | `docs/adrs/ADR-005-tombstone.md` | `adr-tombstone` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| `??` | `docs/adrs/ADR-043-tombstone.md` | `adr-tombstone` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| `??` | `docs/adrs/ADR-046-tombstone.md` | `adr-tombstone` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| `??` | `docs/adrs/ADR-085-tombstone.md` | `adr-tombstone` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| `??` | `docs/adrs/ADR-171-tombstone.md` | `adr-tombstone` | `REJECT_COLLIDES_WITH_ACTIVE_ADR_NUMBERS` | The active branch owns these ADR numbers with real decisions; tombstones would reintroduce the collision pattern. |
| `??` | `docs/adrs/ADR-172-tombstone.md` | `adr-tombstone` | `REJECT_COLLIDES_WITH_ACTIVE_ADR_NUMBERS` | The active branch owns these ADR numbers with real decisions; tombstones would reintroduce the collision pattern. |
| `??` | `docs/adrs/ADR-173-tombstone.md` | `adr-tombstone` | `REJECT_COLLIDES_WITH_ACTIVE_ADR_NUMBERS` | The active branch owns these ADR numbers with real decisions; tombstones would reintroduce the collision pattern. |
| `??` | `docs/adrs/ADR-174-tombstone.md` | `adr-tombstone` | `REJECT_COLLIDES_WITH_ACTIVE_ADR_NUMBERS` | The active branch owns these ADR numbers with real decisions; tombstones would reintroduce the collision pattern. |
| `??` | `docs/adrs/ADR-175-tombstone.md` | `adr-tombstone` | `REJECT_COLLIDES_WITH_ACTIVE_ADR_NUMBERS` | The active branch owns these ADR numbers with real decisions; tombstones would reintroduce the collision pattern. |
| `??` | `manifests/skill-routing-coverage.yaml` | `skill-routing` | `REJECT_OR_ALREADY_SUPERSEDED_BY_ADR174_V2` | The active branch has the newer routing coverage/schema contract; session50 is older or identical. |
| `??` | `scripts/adr_tombstone.py` | `adr-tombstone-tool` | `REJECT_OLDER_TOMBSTONE_TOOL` | The active branch has the safer tombstone tool that refuses active ADR replacement by default. |
| `??` | `scripts/cos-adr-tombstone` | `adr-tombstone-tool` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| `??` | `skills/adr-tombstone/` | `adr-tombstone-tool` | `REJECT_OLDER_TOMBSTONE_TOOL` | The active branch has the safer tombstone tool that refuses active ADR replacement by default. |
| `??` | `tests/contracts/test_adr_numbering_integrity.py` | `adr-tombstone-tool` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| `??` | `tests/contracts/test_no_rejected_surface_references.py` | `other` | `NO_IMPORT_STALE_OR_NON_CRITICAL_DRIFT` | Reviewed as part of session50 intake; no evidence it improves the active branch over current commits. |
| `??` | `tests/contracts/test_skill_router_profile_contracts.py` | `skill-routing` | `NO_ACTION_ALREADY_IN_CURRENT` | The session50 worktree content matches the active branch content. |
| `??` | `tests/unit/test_adr_tombstone.py` | `adr-tombstone-tool` | `REJECT_OLDER_TOMBSTONE_TOOL` | The active branch has the safer tombstone tool that refuses active ADR replacement by default. |

## Closure actions — 2026-05-06

After the file-level matrix above was reviewed, the stale sibling worktree was closed surgically instead of imported.

Actions performed:

1. Created a **local, non-versioned** archival snapshot under `.cognitive-os/archives/worktree-intake/session50-2026-05-06/` containing:
   - `README.txt` with branch/head metadata;
   - `status-porcelain.txt` and `status-short-branch.txt`;
   - `uncommitted.diff` with binary-safe WIP diff;
   - `untracked-files.tgz` for untracked files;
   - `SHA256SUMS` for integrity.
2. Removed the stale worktree with `git worktree remove --force <workspace-parent>/luum-agent-os-session50-paperclip-purge`.
3. Deleted the stale local branch with `git branch -D session/50c35ce9-remove-paperclip-multi-surface`.
4. Re-ran `git worktree list --porcelain`; only the active worktree remained.

Rationale: the report reviewed every status entry and found no file that should be imported wholesale. Keeping the stale worktree alive would preserve a second semantic source of truth for ADR/Paperclip disposition and make future agent intake more error-prone.

Recovery path: if a specific historical hunk is needed, inspect the local archive snapshot and manually port only that hunk onto a fresh branch with current tests.
