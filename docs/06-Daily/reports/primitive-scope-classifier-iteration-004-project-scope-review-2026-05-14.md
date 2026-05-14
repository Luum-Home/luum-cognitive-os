# Primitive Scope Classifier Iteration 4 — `project` Scope Model Review

## Input

```bash
.venv/bin/python scripts/primitive_scope_classifier.py --project-dir .
```

## Classifier adjustment in this iteration

Manual review showed that the classifier had no positive model for `project`: 64 primitives declared `project`, but 0 were suggested as `project`. The classifier now preserves `declared_scope=project` as low-confidence `suggested_scope=project` when no stronger distribution evidence exists. This is explicitly `declared-project-pending-proof`, not proof that the row is truly project-only.

## Summary after adjustment

- Declared `project` rows: 64
- Suggested `project` rows: 35
- project-marker-conflicting-metadata: 7
- project-marker-conflicts-with-both-evidence: 6
- project-marker-conflicts-with-os-only-evidence: 16
- project-pending-positive-proof: 35

## Row-level review

| # | Category | Path | Suggested | Confidence | Evidence | Action |
|---:|---|---|---|---|---|---|
| 1 | project-pending-positive-proof | `hooks/aguara-scan.sh` | project | low | declared-project-pending-proof → project (explicit SCOPE marker without distribution metadata) | Keep visible as `project` candidate; add positive project-only evidence. |
| 2 | project-pending-positive-proof | `hooks/ai-provider-identity-guard.sh` | project | low | declared-project-pending-proof → project (explicit SCOPE marker without distribution metadata) | Keep visible as `project` candidate; add positive project-only evidence. |
| 3 | project-pending-positive-proof | `hooks/architecture-compliance.sh` | project | low | declared-project-pending-proof → project (explicit SCOPE marker without distribution metadata) | Keep visible as `project` candidate; add positive project-only evidence. |
| 4 | project-pending-positive-proof | `hooks/code-review-on-commit.sh` | project | low | declared-project-pending-proof → project (explicit SCOPE marker without distribution metadata) | Keep visible as `project` candidate; add positive project-only evidence. |
| 5 | project-marker-conflicts-with-os-only-evidence | `hooks/confidentiality-enforcer.sh` | os-only | medium | lifecycle → os-only (distribution=lab; state=blocking) | Do not auto-change; inspect whether marker or metadata is stale. |
| 6 | project-marker-conflicts-with-os-only-evidence | `hooks/content-policy.sh` | os-only | medium | lifecycle → os-only (distribution=lab; state=blocking) | Do not auto-change; inspect whether marker or metadata is stale. |
| 7 | project-marker-conflicts-with-both-evidence | `hooks/destructive-rm-blocker.sh` | both | medium | lifecycle → both (distribution=core; state=blocking) | Do not auto-change; inspect whether marker or metadata is stale. |
| 8 | project-marker-conflicts-with-os-only-evidence | `hooks/doc-sync-detector.sh` | os-only | medium | lifecycle → os-only (distribution=lab; state=sandbox) | Do not auto-change; inspect whether marker or metadata is stale. |
| 9 | project-pending-positive-proof | `hooks/dry-run-preview.sh` | project | low | declared-project-pending-proof → project (explicit SCOPE marker without distribution metadata) | Keep visible as `project` candidate; add positive project-only evidence. |
| 10 | project-pending-positive-proof | `hooks/ecosystem-check.sh` | project | low | declared-project-pending-proof → project (explicit SCOPE marker without distribution metadata) | Keep visible as `project` candidate; add positive project-only evidence. |
| 11 | project-marker-conflicts-with-os-only-evidence | `hooks/git-commit-scope-guard.sh` | os-only | medium | lifecycle → os-only (distribution=maintainer; state=blocking) | Do not auto-change; inspect whether marker or metadata is stale. |
| 12 | project-pending-positive-proof | `hooks/global-verify.sh` | project | low | declared-project-pending-proof → project (explicit SCOPE marker without distribution metadata) | Keep visible as `project` candidate; add positive project-only evidence. |
| 13 | project-pending-positive-proof | `hooks/guardrails-validator.sh` | project | low | declared-project-pending-proof → project (explicit SCOPE marker without distribution metadata) | Keep visible as `project` candidate; add positive project-only evidence. |
| 14 | project-pending-positive-proof | `hooks/infra-intent-detector.sh` | project | low | declared-project-pending-proof → project (explicit SCOPE marker without distribution metadata) | Keep visible as `project` candidate; add positive project-only evidence. |
| 15 | project-pending-positive-proof | `hooks/jupyter-sandbox.sh` | project | low | declared-project-pending-proof → project (explicit SCOPE marker without distribution metadata) | Keep visible as `project` candidate; add positive project-only evidence. |
| 16 | project-marker-conflicts-with-os-only-evidence | `hooks/mcp-scan.sh` | os-only | medium | lifecycle → os-only (distribution=lab; state=sandbox) | Do not auto-change; inspect whether marker or metadata is stale. |
| 17 | project-pending-positive-proof | `hooks/parry-scan.sh` | project | low | declared-project-pending-proof → project (explicit SCOPE marker without distribution metadata) | Keep visible as `project` candidate; add positive project-only evidence. |
| 18 | project-pending-positive-proof | `hooks/pre-cleanup-snapshot.sh` | project | low | declared-project-pending-proof → project (explicit SCOPE marker without distribution metadata) | Keep visible as `project` candidate; add positive project-only evidence. |
| 19 | project-pending-positive-proof | `hooks/pre-commit-gate.sh` | project | low | declared-project-pending-proof → project (explicit SCOPE marker without distribution metadata) | Keep visible as `project` candidate; add positive project-only evidence. |
| 20 | project-marker-conflicts-with-os-only-evidence | `hooks/predev-completeness-check.sh` | os-only | medium | lifecycle → os-only (distribution=lab; state=blocking) | Do not auto-change; inspect whether marker or metadata is stale. |
| 21 | project-marker-conflicts-with-os-only-evidence | `hooks/private-mode-gate.sh` | os-only | medium | lifecycle → os-only (distribution=lab; state=sandbox) | Do not auto-change; inspect whether marker or metadata is stale. |
| 22 | project-marker-conflicts-with-os-only-evidence | `hooks/private-mode-metrics-gate.sh` | os-only | medium | lifecycle → os-only (distribution=lab; state=sandbox) | Do not auto-change; inspect whether marker or metadata is stale. |
| 23 | project-marker-conflicts-with-os-only-evidence | `hooks/rate-limit-drain.sh` | os-only | medium | lifecycle → os-only (distribution=lab; state=sandbox) | Do not auto-change; inspect whether marker or metadata is stale. |
| 24 | project-marker-conflicts-with-os-only-evidence | `hooks/rate-limit-precheck.sh` | os-only | medium | lifecycle → os-only (distribution=maintainer; state=advisory) | Do not auto-change; inspect whether marker or metadata is stale. |
| 25 | project-marker-conflicts-with-os-only-evidence | `hooks/rate-limiter.sh` | os-only | medium | lifecycle → os-only (distribution=lab; state=blocking) | Do not auto-change; inspect whether marker or metadata is stale. |
| 26 | project-marker-conflicts-with-os-only-evidence | `hooks/reinvention-check.sh` | os-only | medium | lifecycle → os-only (distribution=lab; state=sandbox) | Do not auto-change; inspect whether marker or metadata is stale. |
| 27 | project-marker-conflicts-with-os-only-evidence | `hooks/release-guard.sh` | os-only | medium | lifecycle → os-only (distribution=maintainer; state=blocking) | Do not auto-change; inspect whether marker or metadata is stale. |
| 28 | project-pending-positive-proof | `hooks/semgrep-scan.sh` | project | low | declared-project-pending-proof → project (explicit SCOPE marker without distribution metadata) | Keep visible as `project` candidate; add positive project-only evidence. |
| 29 | project-pending-positive-proof | `hooks/valkey-ensure.sh` | project | low | declared-project-pending-proof → project (explicit SCOPE marker without distribution metadata) | Keep visible as `project` candidate; add positive project-only evidence. |
| 30 | project-pending-positive-proof | `hooks/worktree-submodule-fix.sh` | project | low | declared-project-pending-proof → project (explicit SCOPE marker without distribution metadata) | Keep visible as `project` candidate; add positive project-only evidence. |
| 31 | project-marker-conflicts-with-both-evidence | `scripts/check_mcp_servers.py` | both | high | consumer-availability → both (shell-ci-candidate)<br>lifecycle → both (distribution=team; state=candidate) | Do not auto-change; inspect whether marker or metadata is stale. |
| 32 | project-pending-positive-proof | `scripts/cos-cloud-worker-bootstrap.sh` | project | low | declared-project-pending-proof → project (explicit SCOPE marker without distribution metadata) | Keep visible as `project` candidate; add positive project-only evidence. |
| 33 | project-pending-positive-proof | `scripts/cos-postgres-local.sh` | project | low | declared-project-pending-proof → project (explicit SCOPE marker without distribution metadata) | Keep visible as `project` candidate; add positive project-only evidence. |
| 34 | project-pending-positive-proof | `scripts/cos-valkey-local.sh` | project | low | declared-project-pending-proof → project (explicit SCOPE marker without distribution metadata) | Keep visible as `project` candidate; add positive project-only evidence. |
| 35 | project-pending-positive-proof | `scripts/credibility-audit.sh` | project | low | declared-project-pending-proof → project (explicit SCOPE marker without distribution metadata) | Keep visible as `project` candidate; add positive project-only evidence. |
| 36 | project-marker-conflicts-with-both-evidence | `scripts/dependency-lane.sh` | both | medium | lifecycle → both (distribution=team; state=candidate) | Do not auto-change; inspect whether marker or metadata is stale. |
| 37 | project-marker-conflicts-with-os-only-evidence | `scripts/deps-update.sh` | os-only | medium | lifecycle → os-only (distribution=maintainer; state=candidate) | Do not auto-change; inspect whether marker or metadata is stale. |
| 38 | project-marker-conflicts-with-both-evidence | `scripts/docs_execution_audit.py` | both | high | consumer-availability → both (shell-ci-candidate)<br>lifecycle → both (distribution=team; state=candidate) | Do not auto-change; inspect whether marker or metadata is stale. |
| 39 | project-pending-positive-proof | `scripts/doctor.sh` | project | low | declared-project-pending-proof → project (explicit SCOPE marker without distribution metadata) | Keep visible as `project` candidate; add positive project-only evidence. |
| 40 | project-marker-conflicting-metadata | `scripts/document_feature_append.py` | unknown | low | consumer-availability → os-only (maintainer-only)<br>lifecycle → both (distribution=team; state=candidate) | Resolve metadata conflict before marker changes. |
| 41 | project-marker-conflicting-metadata | `scripts/domain_model.py` | unknown | low | consumer-availability → os-only (maintainer-only)<br>lifecycle → both (distribution=team; state=candidate) | Resolve metadata conflict before marker changes. |
| 42 | project-pending-positive-proof | `scripts/install-aguara.sh` | project | low | declared-project-pending-proof → project (explicit SCOPE marker without distribution metadata) | Keep visible as `project` candidate; add positive project-only evidence. |
| 43 | project-pending-positive-proof | `scripts/install-credibility-tools.sh` | project | low | declared-project-pending-proof → project (explicit SCOPE marker without distribution metadata) | Keep visible as `project` candidate; add positive project-only evidence. |
| 44 | project-marker-conflicts-with-os-only-evidence | `scripts/install-garak.sh` | os-only | medium | lifecycle → os-only (distribution=maintainer; state=candidate) | Do not auto-change; inspect whether marker or metadata is stale. |
| 45 | project-pending-positive-proof | `scripts/install-git-filter-repo.sh` | project | low | declared-project-pending-proof → project (explicit SCOPE marker without distribution metadata) | Keep visible as `project` candidate; add positive project-only evidence. |
| 46 | project-pending-positive-proof | `scripts/install-mcp-scan.sh` | project | low | declared-project-pending-proof → project (explicit SCOPE marker without distribution metadata) | Keep visible as `project` candidate; add positive project-only evidence. |
| 47 | project-marker-conflicts-with-os-only-evidence | `scripts/install-promptfoo.sh` | os-only | medium | lifecycle → os-only (distribution=maintainer; state=candidate) | Do not auto-change; inspect whether marker or metadata is stale. |
| 48 | project-pending-positive-proof | `scripts/install-syft-grype.sh` | project | low | declared-project-pending-proof → project (explicit SCOPE marker without distribution metadata) | Keep visible as `project` candidate; add positive project-only evidence. |
| 49 | project-pending-positive-proof | `scripts/install-tob-skills.sh` | project | low | declared-project-pending-proof → project (explicit SCOPE marker without distribution metadata) | Keep visible as `project` candidate; add positive project-only evidence. |
| 50 | project-pending-positive-proof | `scripts/install-trivy.sh` | project | low | declared-project-pending-proof → project (explicit SCOPE marker without distribution metadata) | Keep visible as `project` candidate; add positive project-only evidence. |
| 51 | project-pending-positive-proof | `scripts/license-audit-syft-grype.sh` | project | low | declared-project-pending-proof → project (explicit SCOPE marker without distribution metadata) | Keep visible as `project` candidate; add positive project-only evidence. |
| 52 | project-pending-positive-proof | `scripts/license-audit-trivy.sh` | project | low | declared-project-pending-proof → project (explicit SCOPE marker without distribution metadata) | Keep visible as `project` candidate; add positive project-only evidence. |
| 53 | project-marker-conflicting-metadata | `scripts/llm_status.py` | unknown | low | consumer-availability → os-only (maintainer-only)<br>lifecycle → both (distribution=team; state=candidate) | Resolve metadata conflict before marker changes. |
| 54 | project-marker-conflicting-metadata | `scripts/ops_runbook.py` | unknown | low | consumer-availability → os-only (maintainer-only)<br>lifecycle → both (distribution=team; state=candidate) | Resolve metadata conflict before marker changes. |
| 55 | project-marker-conflicts-with-both-evidence | `scripts/project_scaffold.py` | both | high | consumer-availability → both (shell-ci-candidate)<br>lifecycle → both (distribution=team; state=candidate) | Do not auto-change; inspect whether marker or metadata is stale. |
| 56 | project-marker-conflicting-metadata | `scripts/radar_merge.py` | unknown | low | consumer-availability → os-only (maintainer-only)<br>lifecycle → both (distribution=team; state=candidate) | Resolve metadata conflict before marker changes. |
| 57 | project-marker-conflicting-metadata | `scripts/risk_register.py` | unknown | low | consumer-availability → os-only (maintainer-only)<br>lifecycle → both (distribution=team; state=candidate) | Resolve metadata conflict before marker changes. |
| 58 | project-pending-positive-proof | `scripts/setup-git-hooks.sh` | project | low | declared-project-pending-proof → project (explicit SCOPE marker without distribution metadata) | Keep visible as `project` candidate; add positive project-only evidence. |
| 59 | project-marker-conflicts-with-both-evidence | `scripts/setup.sh` | both | high | protected-install-surface → both (bootstrap)<br>lifecycle → both (distribution=core; state=candidate) | Do not auto-change; inspect whether marker or metadata is stale. |
| 60 | project-marker-conflicting-metadata | `scripts/sprint-test-summary.sh` | unknown | low | consumer-availability → os-only (maintainer-only)<br>lifecycle → both (distribution=team; state=candidate) | Resolve metadata conflict before marker changes. |
| 61 | project-pending-positive-proof | `skills/project-scaffold/SKILL.md` | project | low | declared-project-pending-proof → project (explicit SCOPE marker without distribution metadata) | Keep visible as `project` candidate; add positive project-only evidence. |
| 62 | project-pending-positive-proof | `templates/fintech-gates.md` | project | low | declared-project-pending-proof → project (explicit SCOPE marker without distribution metadata) | Keep visible as `project` candidate; add positive project-only evidence. |
| 63 | project-pending-positive-proof | `templates/go-service-context.md` | project | low | declared-project-pending-proof → project (explicit SCOPE marker without distribution metadata) | Keep visible as `project` candidate; add positive project-only evidence. |
| 64 | project-pending-positive-proof | `templates/project-gotchas.md` | project | low | declared-project-pending-proof → project (explicit SCOPE marker without distribution metadata) | Keep visible as `project` candidate; add positive project-only evidence. |

## Decision

`project` remains an explicit first-class bucket. Rows with only a project marker are now kept visible as low-confidence project candidates rather than collapsing to unknown or os-only. No marker changes were made.
