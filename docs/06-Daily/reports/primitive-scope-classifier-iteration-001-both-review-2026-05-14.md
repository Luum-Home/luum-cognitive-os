# Primitive Scope Classifier Iteration 1 — Positive `both` Review

## Input

```bash
.venv/bin/python scripts/primitive_scope_classifier.py --project-dir .
```

## Summary

- Input `suggested_scope=both` rows: 65
- candidate-both-marker-or-proof-gap: 14
- confirmed-both: 48
- missing-header-exact-both-override: 3

## Manual reading

- `confirmed-both`: marker is `both`, positive distribution metadata exists, and a paired portability/falsification proof exists.
- `candidate-both-marker-or-proof-gap`: metadata suggests `both`, but current marker and/or proof does not yet satisfy the contract.
- `missing-header-exact-both-override`: exact override says `both`, but header should be made explicit before relying on it.
- `needs-review`: do not act without deeper inspection.

## Row-level review

| # | Category | Path | Declared | Confidence | Paired proof | Evidence | Action |
|---:|---|---|---|---|---|---|---|
| 1 | confirmed-both | `hooks/agent-control-inbound-guard.sh` | both | medium | `tests/red_team/portability/test_agent-control-inbound-guard.py` | lifecycle → both (distribution=core; state=blocking) | Keep as `both`; no marker change. |
| 2 | confirmed-both | `hooks/claim-validator.sh` | both | medium | `tests/red_team/portability/test_claim-validator.py` | lifecycle → both (distribution=team; state=blocking) | Keep as `both`; no marker change. |
| 3 | confirmed-both | `hooks/concurrent-write-guard.sh` | both | medium | `tests/red_team/portability/test_concurrent-write-guard.py` | lifecycle → both (distribution=core; state=blocking) | Keep as `both`; no marker change. |
| 4 | confirmed-both | `hooks/control-plane-audit-hourly.sh` | both | medium | `tests/red_team/portability/test_control-plane-audit-hourly.py` | lifecycle → both (distribution=core; state=advisory) | Keep as `both`; no marker change. |
| 5 | confirmed-both | `hooks/control-plane-audit.sh` | both | medium | `tests/red_team/portability/test_control-plane-audit.py` | lifecycle → both (distribution=core; state=blocking) | Keep as `both`; no marker change. |
| 6 | confirmed-both | `hooks/cosd-auth-guard.sh` | both | medium | `tests/red_team/portability/test_cosd-auth-guard.py` | lifecycle → both (distribution=core; state=blocking) | Keep as `both`; no marker change. |
| 7 | confirmed-both | `hooks/destructive-git-blocker.sh` | both | medium | `tests/red_team/portability/test_destructive-git-blocker.py` | lifecycle → both (distribution=core; state=blocking) | Keep as `both`; no marker change. |
| 8 | candidate-both-marker-or-proof-gap | `hooks/destructive-rm-blocker.sh` | project | medium | `` | lifecycle → both (distribution=core; state=blocking) | Do not auto-change; add proof or correct stale metadata first. |
| 9 | confirmed-both | `hooks/direct-main-guard.sh` | both | medium | `tests/red_team/portability/test_direct-main-guard.py` | lifecycle → both (distribution=core; state=blocking) | Keep as `both`; no marker change. |
| 10 | confirmed-both | `hooks/edit-lock-pre-tool.sh` | both | medium | `tests/red_team/portability/test_edit-lock-pre-tool.py` | lifecycle → both (distribution=core; state=blocking) | Keep as `both`; no marker change. |
| 11 | confirmed-both | `hooks/orchestrator-claim-gate.sh` | both | medium | `tests/red_team/portability/test_orchestrator-claim-gate.py` | lifecycle → both (distribution=team; state=blocking) | Keep as `both`; no marker change. |
| 12 | confirmed-both | `hooks/orchestrator-skill-invocation-gate.sh` | both | medium | `tests/red_team/portability/test_orchestrator-skill-invocation-gate.py` | lifecycle → both (distribution=team; state=blocking) | Keep as `both`; no marker change. |
| 13 | confirmed-both | `hooks/plan-claim-validator.sh` | both | medium | `tests/red_team/portability/plan-claim-validator.bats` | lifecycle → both (distribution=team; state=blocking) | Keep as `both`; no marker change. |
| 14 | confirmed-both | `hooks/scope-marker-portability-gate.sh` | both | medium | `tests/red_team/portability/scope-marker-portability-gate.bats` | lifecycle → both (distribution=core; state=blocking) | Keep as `both`; no marker change. |
| 15 | confirmed-both | `hooks/secret-detector.sh` | both | medium | `tests/red_team/portability/test_secret-detector.py` | lifecycle → both (distribution=core; state=blocking) | Keep as `both`; no marker change. |
| 16 | confirmed-both | `hooks/skill-router-prompt-suggest.sh` | both | medium | `tests/red_team/portability/test_skill-router-prompt-suggest.py` | lifecycle → both (distribution=core; state=advisory) | Keep as `both`; no marker change. |
| 17 | confirmed-both | `hooks/symlink-mutation-guard.sh` | both | medium | `tests/red_team/portability/test_symlink-mutation-guard.py` | lifecycle → both (distribution=core; state=blocking) | Keep as `both`; no marker change. |
| 18 | confirmed-both | `hooks/untracked-work-preservation-guard.sh` | both | medium | `tests/red_team/portability/test_untracked-work-preservation-guard.py` | lifecycle → both (distribution=team; state=blocking) | Keep as `both`; no marker change. |
| 19 | confirmed-both | `scripts/adr_tombstone.py` | both | medium | `tests/red_team/portability/test_adr_tombstone.py` | lifecycle → both (distribution=team; state=blocking) | Keep as `both`; no marker change. |
| 20 | candidate-both-marker-or-proof-gap | `scripts/apply-efficiency-profile.sh` | os-only | high | `` | protected-install-surface → both (profile-application)<br>lifecycle → both (distribution=core; state=candidate) | Do not auto-change; add proof or correct stale metadata first. |
| 21 | candidate-both-marker-or-proof-gap | `scripts/check_mcp_servers.py` | project | high | `` | consumer-availability → both (shell-ci-candidate)<br>lifecycle → both (distribution=team; state=candidate) | Do not auto-change; add proof or correct stale metadata first. |
| 22 | missing-header-exact-both-override | `scripts/cos` |  | high | `` | scope-override → both (Projected command wrapper for consumer projects.)<br>consumer-availability → both (shell-ci-candidate)<br>lifecycle → both (distribution=team; state=candidate) | Add explicit header and paired proof if it is a distributable primitive. |
| 23 | confirmed-both | `scripts/cos-adapter-compile` | both | medium | `tests/red_team/portability/test_cos-adapter-compile.py` | lifecycle → both (distribution=team; state=candidate) | Keep as `both`; no marker change. |
| 24 | confirmed-both | `scripts/cos-adapters` | both | medium | `tests/red_team/portability/test_cos-adapters.py` | lifecycle → both (distribution=team; state=candidate) | Keep as `both`; no marker change. |
| 25 | candidate-both-marker-or-proof-gap | `scripts/cos-adr-close` | os-only | medium | `` | lifecycle → both (distribution=team; state=candidate) | Do not auto-change; add proof or correct stale metadata first. |
| 26 | confirmed-both | `scripts/cos-adr-tombstone` | both | medium | `tests/red_team/portability/test_cos-adr-tombstone.py` | lifecycle → both (distribution=team; state=blocking) | Keep as `both`; no marker change. |
| 27 | candidate-both-marker-or-proof-gap | `scripts/cos-bootstrap.sh` | os-only | high | `` | protected-install-surface → both (bootstrap)<br>lifecycle → both (distribution=core; state=candidate) | Do not auto-change; add proof or correct stale metadata first. |
| 28 | confirmed-both | `scripts/cos-closure-trust-signal.py` | both | medium | `tests/red_team/portability/test_cos-closure-trust-signal.py` | lifecycle → both (distribution=team; state=candidate) | Keep as `both`; no marker change. |
| 29 | confirmed-both | `scripts/cos-coordination-status.sh` | both | high | `tests/red_team/portability/test_cos-coordination-status.py` | consumer-availability → both (shell-ci-candidate)<br>lifecycle → both (distribution=team; state=candidate) | Keep as `both`; no marker change. |
| 30 | confirmed-both | `scripts/cos-doc-cross-reference-audit.py` | both | medium | `tests/red_team/portability/test_cos-doc-cross-reference-audit.py` | lifecycle → both (distribution=team; state=candidate) | Keep as `both`; no marker change. |
| 31 | candidate-both-marker-or-proof-gap | `scripts/cos-engram-cloud-docker-smoke` | os-only | medium | `` | lifecycle → both (distribution=team; state=candidate) | Do not auto-change; add proof or correct stale metadata first. |
| 32 | missing-header-exact-both-override | `scripts/cos-init.sh` |  | high | `` | scope-override → both (Installer/project bootstrap surface.)<br>protected-install-surface → both (bootstrap)<br>lifecycle → both (distribution=core; state=candidate) | Add explicit header and paired proof if it is a distributable primitive. |
| 33 | confirmed-both | `scripts/cos-observe-primitives` | both | medium | `tests/red_team/portability/test_cos-observe-primitives.py` | lifecycle → both (distribution=team; state=candidate) | Keep as `both`; no marker change. |
| 34 | confirmed-both | `scripts/cos-operational-guide-audit.py` | both | medium | `tests/red_team/portability/test_cos-operational-guide-audit.py` | lifecycle → both (distribution=team; state=candidate) | Keep as `both`; no marker change. |
| 35 | confirmed-both | `scripts/cos-pending-truth-aggregator` | both | medium | `tests/red_team/portability/test_cos-pending-truth-aggregator.py` | lifecycle → both (distribution=team; state=candidate) | Keep as `both`; no marker change. |
| 36 | confirmed-both | `scripts/cos-pending-truth-close` | both | medium | `tests/red_team/portability/test_cos-pending-truth-close.py` | lifecycle → both (distribution=team; state=candidate) | Keep as `both`; no marker change. |
| 37 | confirmed-both | `scripts/cos-pending-truth-verify` | both | medium | `tests/red_team/portability/test_cos-pending-truth-verify.py` | lifecycle → both (distribution=team; state=candidate) | Keep as `both`; no marker change. |
| 38 | confirmed-both | `scripts/cos-portable-ai-overlay` | both | medium | `tests/red_team/portability/test_cos-portable-ai-overlay.py` | lifecycle → both (distribution=team; state=candidate) | Keep as `both`; no marker change. |
| 39 | candidate-both-marker-or-proof-gap | `scripts/cos-pytest-serial-repair` | os-only | medium | `` | lifecycle → both (distribution=team; state=candidate) | Do not auto-change; add proof or correct stale metadata first. |
| 40 | confirmed-both | `scripts/cos-release-check.sh` | both | high | `tests/red_team/portability/test_cos-release-check.py` | consumer-availability → both (shell-ci-candidate)<br>lifecycle → both (distribution=team; state=candidate) | Keep as `both`; no marker change. |
| 41 | confirmed-both | `scripts/cos-remote-branch-triage` | both | medium | `tests/red_team/portability/test_cos-remote-branch-triage.py` | lifecycle → both (distribution=team; state=candidate) | Keep as `both`; no marker change. |
| 42 | confirmed-both | `scripts/cos-service-readiness-gate` | both | medium | `tests/red_team/portability/test_cos-service-readiness-gate.py` | lifecycle → both (distribution=team; state=candidate) | Keep as `both`; no marker change. |
| 43 | confirmed-both | `scripts/cos-session-start-projector` | both | medium | `tests/red_team/portability/test_cos-session-start-projector.py` | lifecycle → both (distribution=team; state=candidate) | Keep as `both`; no marker change. |
| 44 | candidate-both-marker-or-proof-gap | `scripts/cos-skill-description-enrich` | os-only | medium | `` | lifecycle → both (distribution=team; state=candidate) | Do not auto-change; add proof or correct stale metadata first. |
| 45 | confirmed-both | `scripts/cos-smoke.sh` | both | high | `tests/red_team/portability/test_cos-smoke.py` | consumer-availability → both (shell-ci-candidate)<br>lifecycle → both (distribution=team; state=candidate) | Keep as `both`; no marker change. |
| 46 | confirmed-both | `scripts/cos-status.sh` | both | high | `tests/red_team/portability/test_cos-status.py` | consumer-availability → both (shell-ci-candidate)<br>lifecycle → both (distribution=team; state=candidate) | Keep as `both`; no marker change. |
| 47 | confirmed-both | `scripts/cos-usage-report.sh` | both | high | `tests/red_team/portability/test_cos-usage-report.py` | consumer-availability → both (shell-ci-candidate)<br>lifecycle → both (distribution=team; state=candidate) | Keep as `both`; no marker change. |
| 48 | confirmed-both | `scripts/cos-worktree-triage.sh` | both | high | `tests/red_team/portability/test_cos-worktree-triage.py` | consumer-availability → both (shell-ci-candidate)<br>lifecycle → both (distribution=team; state=candidate) | Keep as `both`; no marker change. |
| 49 | confirmed-both | `scripts/cos_init.py` | both | high | `tests/red_team/portability/test_cos_init.py` | protected-install-surface → both (bootstrap)<br>lifecycle → both (distribution=core; state=candidate) | Keep as `both`; no marker change. |
| 50 | candidate-both-marker-or-proof-gap | `scripts/dependency-lane.sh` | project | medium | `` | lifecycle → both (distribution=team; state=candidate) | Do not auto-change; add proof or correct stale metadata first. |
| 51 | candidate-both-marker-or-proof-gap | `scripts/docs_execution_audit.py` | project | high | `` | consumer-availability → both (shell-ci-candidate)<br>lifecycle → both (distribution=team; state=candidate) | Do not auto-change; add proof or correct stale metadata first. |
| 52 | confirmed-both | `scripts/documentation_truth_audit.py` | both | medium | `tests/red_team/portability/test_documentation_truth_audit.py` | lifecycle → both (distribution=team; state=candidate) | Keep as `both`; no marker change. |
| 53 | candidate-both-marker-or-proof-gap | `scripts/generate-project-settings.sh` | os-only | high | `` | protected-install-surface → both (settings-projection)<br>lifecycle → both (distribution=core; state=candidate) | Do not auto-change; add proof or correct stale metadata first. |
| 54 | confirmed-both | `scripts/primitive_harness_coverage.py` | both | medium | `tests/red_team/portability/test_primitive_harness_coverage.py` | lifecycle → both (distribution=core; state=candidate) | Keep as `both`; no marker change. |
| 55 | candidate-both-marker-or-proof-gap | `scripts/project_scaffold.py` | project | high | `` | consumer-availability → both (shell-ci-candidate)<br>lifecycle → both (distribution=team; state=candidate) | Do not auto-change; add proof or correct stale metadata first. |
| 56 | missing-header-exact-both-override | `scripts/project_shell_ci.py` |  | high | `` | scope-override → both (Shell-CI projection surface.) | Add explicit header and paired proof if it is a distributable primitive. |
| 57 | confirmed-both | `scripts/pytest-with-summary.sh` | both | high | `tests/red_team/portability/test_pytest-with-summary.py` | consumer-availability → both (shell-ci-candidate)<br>lifecycle → both (distribution=team; state=candidate) | Keep as `both`; no marker change. |
| 58 | confirmed-both | `scripts/run-all-tests.sh` | both | high | `tests/red_team/portability/test_run-all-tests.py` | consumer-availability → both (shell-ci-candidate)<br>lifecycle → both (distribution=team; state=candidate) | Keep as `both`; no marker change. |
| 59 | confirmed-both | `scripts/run-redteam-scenario.sh` | both | high | `tests/red_team/portability/run-redteam-scenario.bats` | consumer-availability → both (shell-ci-candidate)<br>lifecycle → both (distribution=team; state=candidate) | Keep as `both`; no marker change. |
| 60 | candidate-both-marker-or-proof-gap | `scripts/set-security-profile.sh` | os-only | high | `` | protected-install-surface → both (profile-application)<br>lifecycle → both (distribution=core; state=candidate) | Do not auto-change; add proof or correct stale metadata first. |
| 61 | candidate-both-marker-or-proof-gap | `scripts/setup.sh` | project | high | `` | protected-install-surface → both (bootstrap)<br>lifecycle → both (distribution=core; state=candidate) | Do not auto-change; add proof or correct stale metadata first. |
| 62 | confirmed-both | `scripts/test-all.sh` | both | high | `tests/red_team/portability/test_test-all.py` | consumer-availability → both (shell-ci-candidate)<br>lifecycle → both (distribution=team; state=candidate) | Keep as `both`; no marker change. |
| 63 | confirmed-both | `scripts/test-cognitive-os-full.sh` | both | high | `tests/red_team/portability/test_test-cognitive-os-full.py` | consumer-availability → both (shell-ci-candidate)<br>lifecycle → both (distribution=team; state=candidate) | Keep as `both`; no marker change. |
| 64 | confirmed-both | `skills/agent-control/SKILL.md` | both | medium | `tests/red_team/portability/test_skill_agent_control.py` | lifecycle → both (distribution=core; state=candidate) | Keep as `both`; no marker change. |
| 65 | confirmed-both | `skills/primitive-harness-coverage/SKILL.md` | both | medium | `tests/red_team/portability/test_skill_primitive_harness_coverage.py` | lifecycle → both (distribution=team; state=candidate) | Keep as `both`; no marker change. |

## Decision

No `SCOPE` marker changes are made in this iteration. The bucket is now split into confirmed rows and candidate work items. Next iteration should review `suggested_scope=os-only` by evidence source, starting with consumer-availability maintainer/local-only rows.
