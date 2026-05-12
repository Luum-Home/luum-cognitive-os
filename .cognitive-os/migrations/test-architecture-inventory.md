# Test Architecture Inventory

**Status**: Active migration inventory.  
**Date**: 2026-04-30.  
**Purpose**: classify test-related primitives by exactly one role so Cognitive OS does not accumulate competing test runners, duplicated selection logic, or hidden governance gaps.

## Role definitions

| Role | Definition |
|---|---|
| Selection | Chooses which tests should run and which marker/lane policy applies. |
| Execution | Starts a test command or interactive runner. |
| Reporting | Persists or summarizes test results without deciding scope. |
| Governance | Enforces quality gates, DoD, coverage, or anti-aspirational-test policy. |
| Lifecycle | Stores baselines, historical reports, ratchets, or migration state over time. |

## Inventory

| Role | Primitive | Path | Purpose | Status | Owner / consumer | Action |
|---|---|---|---|---|---|---|
| Selection | Lane registry | .cognitive-os/test-lanes.yaml | Defines test lanes, paths, optional flags, parallel policy, marker exclusions. | Canonical | cos-test + tests/conftest.py | Keep as source of truth. |
| Selection | Pytest auto-marker injection | tests/conftest.py | Injects path-derived lane markers during collection. | Canonical | pytest collection | Keep; boundary-safe matching must stay tested. |
| Selection | Pytest marker registry | pytest.ini | Registers lane markers under strict-markers. | Canonical | pytest | Keep in sync with lane registry. |
| Selection | Lane parser | cmd/cos-test/internal/lanes/lanes.go | Loads and orders lane registry for Go CLI. | Canonical | cmd/cos-test | Keep; no policy duplication elsewhere. |
| Selection | Focused selector | cmd/cos-test/internal/cli/focused.go | Maps changed files or explicit paths to the narrowest useful test set. | Canonical | cmd/cos-test focused | Keep as selection+execution UX. |
| Selection | Cluster selector | cmd/cos-test/internal/cli/cluster.go | Resolves one lane into serial/parallel pytest invocations. | Canonical | cmd/cos-test cluster | Keep; all lane policy flows through registry. |
| Selection | Broad selector | cmd/cos-test/internal/cli/broad.go | Orders the default non-optional lane sweep and optional inclusion. | Canonical | cmd/cos-test broad | Keep; optional lanes explicit. |
| Selection | Run-tests skill selector guidance | skills/run-tests/SKILL.md | Agent-facing decision tree for focused/cluster/broad vs fallback. | Canonical guidance | agents | Keep as user-facing selector guidance. |
| Selection | Lane taxonomy rule | rules/lane-taxonomy.md | Always-active rule for lane classification and escalation ladder. | Canonical governance rule | agents + audits | Keep; must match ADR/inventory. |
| Selection | Makefile no-docker shard shims | Makefile | Compatibility selection for old CI shard commands. | Deprecated shim | Make users/CI | Keep one release cycle; proxy only. |
| Execution | cos-test binary entrypoint | cmd/cos-test/main.go | Runs the Go test CLI. | Canonical | cmd/cos-test | Keep. |
| Execution | cos-test root command | cmd/cos-test/internal/cli/root.go | Defines CLI shell and command registration. | Canonical | cmd/cos-test | Keep. |
| Execution | cos-test legacy run command | cmd/cos-test/internal/cli/run.go | Legacy TUI/CI pytest category runner. | Compatibility | cmd/cos-test run | Keep until focused/cluster/broad fully replace old workflows. |
| Execution | Raw pytest wrapper executor | cmd/cos-test/internal/runner/raw.go | Executes pytest through `pytest-with-summary.sh` when available. | Canonical | `cos-test focused/cluster/broad` | Keep; all ladder commands must preserve persistent summaries. |
| Execution | TUI pytest runner | cmd/cos-test/internal/runner/pytest.go | Direct pytest execution and JSON report parsing for legacy TUI/CI paths. | Compatibility | `cos-test run/dashboard/watch` | Keep secondary until older TUI paths are reconciled with the ladder. |
| Reporting | JSON result parser | cmd/cos-test/internal/runner/results.go | Parses pytest JSON report into typed results for UI paths. | Compatibility | TUI/CI runner | Keep as reporting parser for older UI path. |
| Reporting | UI summary renderer | cmd/cos-test/internal/ui/summary.go | Renders test summaries and coverage matrix. | On-demand | TUI/dashboard | Keep as display layer only. |
| Reporting | cos-test coverage command | cmd/cos-test/internal/cli/coverage.go | Scans tests/source and prints coverage matrix. | On-demand | developers | Keep reporting-only; avoid conflicting with coverage governance thresholds. |
| Governance | Prompt quality hook | hooks/prompt-quality.sh | Checks prompt quality before/after prompt flows. | Canonical governance | hook chain | Keep separate from test execution. |
| Governance | LLM prompt quality hook | hooks/prompt-quality-llm.sh | Runs optional LLM-based prompt quality checks. | Optional governance | prompt quality flow | Keep explicitly cost-bearing. |
| Governance | Resource governance rule | rules/resource-governance.md | Defines budget, agent, and infrastructure resource policy. | Canonical governance | agents/hooks | Keep; test-run resource budgets are follow-up. |
| Execution | cos-test dashboard | cmd/cos-test/internal/cli/dashboard.go | Interactive dashboard execution surface. | On-demand | developer UX | Keep as optional UX, not canonical CI. |
| Execution | cos-test watch | cmd/cos-test/internal/cli/watch.go | File watcher that reruns affected tests. | On-demand | developer UX | Keep; align with lane selector later. |
| Execution | COS startup smoke runner | scripts/cos-smoke.sh | Runs critical-path e2e startup smoke. | On-demand | startup validation | Keep as opt-in, not default broad. |
| Execution | Layer-1 infra shell runner | scripts/test-cognitive-os.sh | Legacy shell infra test runner. | Deprecated shim | legacy shell tests | Deprecate after one release once mapped to lanes. |
| Execution | Three-layer shell pyramid runner | scripts/test-cognitive-os-full.sh | Legacy infra+behavior+quality shell runner. | Deprecated shim | legacy shell tests | Deprecate after one release; quality stays opt-in. |
| Execution | Composite all-test shell runner | scripts/test-all.sh | Legacy pytest+integration+bash composite runner. | Deprecated shim | legacy local flow | Deprecate after one release; replace with cos-test broad. |
| Execution | Release/integrity full sweep | scripts/run-all-tests.sh | Legacy Python+Go+file integrity sweep. | Release-only | release hardening | Keep for release hardening, not daily iteration. |
| Execution | Coverage report script | tests/coverage-report.sh | Runs coverage-oriented test report. | On-demand | coverage validation | Keep until folded into coverage governance. |
| Reporting | Persistent pytest wrapper | scripts/pytest-with-summary.sh | Runs pytest and writes summary, failures, inventory, JUnit, and run history. | Canonical | cos-test transport | Keep as reporting transport only. |
| Reporting | Run inventory generator | scripts/test_run_inventory.py | Builds analyzable inventory for a test run. | Canonical | pytest-with-summary | Keep; reporting-only. |
| Reporting | Test run report store | .cognitive-os/reports/test-runs/ | Ignored local store for persisted test artifacts. | Canonical | pytest-with-summary | Keep ignored and pruned. |
| Reporting | Sprint test summary | scripts/sprint-test-summary.sh | Summarizes test state for sprint/session reporting. | On-demand | session reporting | Keep as lifecycle/reporting consumer. |
| Reporting | Verify metrics | .cognitive-os/metrics/verify-events.jsonl | Append-only verify events. | Canonical metric | verify hooks | Keep. |
| Reporting | Auto-verify metrics | .cognitive-os/metrics/auto-verify.jsonl | Append-only auto-verify events. | Canonical metric | auto-verify | Keep. |
| Reporting | DoD metrics | .cognitive-os/metrics/dod-gate.jsonl | Append-only DoD gate events. | Canonical metric | dod-gate | Keep. |
| Reporting | Coverage metrics | .cognitive-os/metrics/coverage-history.jsonl | Append-only coverage history. | Canonical metric | coverage scripts/hooks | Keep. |
| Reporting | Test quality metrics | .cognitive-os/metrics/test-quality-audit.jsonl | Append-only test quality audit history. | Canonical metric | test quality audit | Keep. |
| Reporting | Test repair ledger | docs/06-Daily/reports/test-suite-repair-ledger-2026-04-24.md | Human-readable historical repair ledger. | Lifecycle report | maintainers | Keep as historical evidence. |
| Governance | Auto verify hook | hooks/auto-verify.sh | Automatically verifies changed files after relevant edits. | Canonical governance | hook chain | Keep; consume canonical selection/reporting. |
| Governance | Global verify hook | hooks/global-verify.sh | Captures and compares verification baselines around global operations. | Canonical governance | hook chain | Keep; needs deterministic changed-file override for tests. |
| Governance | Post-agent verify hook | hooks/post-agent-verify.sh | Validates delegated agent results. | Canonical governance | hook chain | Keep; consume persisted evidence. |
| Governance | Definition-of-Done gate | hooks/dod-gate.sh | Blocks completion when DoD evidence is insufficient. | Canonical governance | hook chain | Keep. |
| Governance | Completion gate | hooks/completion-gate.sh | Checks completion/readiness criteria. | Canonical governance | hook chain | Keep. |
| Governance | Dispatch gate | hooks/dispatch-gate.sh | Gates dispatch decisions and records dispatch metrics. | Canonical governance | hook chain | Keep separate from test execution. |
| Governance | Pre-commit gate | hooks/pre-commit-gate.sh | Runs commit-time checks. | Canonical governance | git/hook chain | Keep; avoid duplicate lane selection. |
| Governance | Test quality checker | scripts/check_test_quality.py | Blocks structural-only new tests. | Canonical governance | pre-commit + CI | Keep. |
| Governance | Quality ratchet checker | scripts/check_test_ratchet.py | Prevents quality regression against a ratchet. | Canonical governance | CI/maintainers | Keep. |
| Governance | Coverage classifier | scripts/cos_classify_coverage.py | Classifies coverage tiers and gaps. | Canonical governance | coverage enforcement | Keep. |
| Governance | Test quality audit | scripts/cos_test_quality_audit.py | Audits test quality and emits quality metrics. | Canonical governance | quality lane | Keep as governance, not runner. |
| Governance | Coverage enforcement skill | skills/coverage-enforcement/SKILL.md | Agent-facing coverage enforcement procedure. | Canonical guidance | agents | Keep; consume coverage artifacts. |
| Governance | DoD check skill | skills/dod-check/SKILL.md | Agent-facing Definition-of-Done verification. | Canonical guidance | agents | Keep. |
| Governance | Test contract repair skill | skills/test-contract-repair/SKILL.md | Guides repair of weak/aspirational tests and contracts. | Canonical guidance | agents | Keep. |
| Lifecycle | Verify baseline runtime | .cognitive-os/runtime/verify-baseline/ | Stores baseline verification state. | Canonical state | global-verify | Keep. |
| Lifecycle | Session test baselines | .cognitive-os/sessions/*/test-baseline.txt | Per-session baseline snapshots. | Canonical state | session lifecycle | Keep pruned/ignored. |
| Lifecycle | Coverage tiers | .cognitive-os/coverage-tiers.json | Defines coverage maturity tiers. | Canonical state | coverage governance | Keep. |
| Lifecycle | Repair ledger report | docs/06-Daily/reports/pre-existing-test-failures-2026-04-21.md | Historical baseline of known failures. | Historical report | maintainers | Keep updated only with evidence. |
| Lifecycle | Full suite validation report | docs/06-Daily/reports/full-suite-validation-2026-04-23.md | Historical full-suite result record. | Historical report | maintainers | Keep. |
| Lifecycle | Test quality audit report | docs/06-Daily/reports/test-quality-audit-2026-04-20.md | Historical quality audit record. | Historical report | maintainers | Keep. |
| Lifecycle | Test runner ergonomics proposal | .cognitive-os/plans/features/test-runner-ergonomics-proposal.md | Historical plan for focused/cluster/broad. | Historical plan | maintainers | Keep as context; current ADR supersedes. |
| Lifecycle | Test runner ergonomics design | .cognitive-os/plans/features/test-runner-ergonomics-design.md | Historical design for runner ladder. | Historical plan | maintainers | Keep as context; current ADR supersedes. |

## Overlap audit

| Overlap / gap | Evidence | Resolution |
|---|---|---|
| Three “smoke/all” execution surfaces compete for mindshare. | `scripts/cos-smoke.sh`, `scripts/test-cognitive-os.sh`, `scripts/test-cognitive-os-full.sh`, `scripts/test-all.sh`, and `scripts/run-all-tests.sh` all historically presented themselves as runners. | `cmd/cos-test` is canonical for focused/cluster/broad. Legacy scripts keep `ROLE`/`CANONICAL` headers and deprecate or become explicit release/startup tools. |
| Selection and execution were coupled in bash scripts. | Legacy scripts choose paths and run tests directly. | New policy: selection belongs in `.cognitive-os/test-lanes.yaml`, `tests/conftest.py`, and `cos-test`; bash wrapper is reporting transport only. |
| Governance primitives can accidentally duplicate runner logic. | `auto-verify`, `dod-gate`, coverage, and quality audit hooks/skills may invoke tests or inspect evidence. | Governance consumes persisted summaries and lane registry; it must not own a parallel test-selection map. |
| Resource governance is not yet part of the test runner architecture. | Budget/resource rules exist (`rules/resource-governance.md`, `skills/resource-governor`) but no test-runner resource lane exists. | Treat as a separate sprint after canonical role registry lands; define time/CPU/Docker/cost budgets for optional lanes. |
| Historical plans still mention old runner shapes. | `.cognitive-os/plans/features/test-runner-ergonomics-*` predate the role registry. | Keep as lifecycle context; ADR-073 becomes current canonical map. |

## Deprecation candidates

| Primitive | Deprecation path | Replacement |
|---|---|---|
| `scripts/test-cognitive-os.sh` | Banner now; redirect/proxy next; remove after one release cycle if no external consumers. | `cos-test cluster --lane hooks` or targeted shell checks. |
| `scripts/test-cognitive-os-full.sh` | Banner now; redirect/proxy next; remove after one release cycle if no external consumers. | `cos-test broad`; explicit quality governance when needed. |
| `scripts/test-all.sh` | Banner now; redirect/proxy next; remove after one release cycle if no external consumers. | `cos-test focused / cluster / broad`. |
| `scripts/run-all-tests.sh` | Do not remove until release flow is audited; demote to release/integrity sweep only. | `cos-test broad` for daily validation; release checklist for hardening. |
| Makefile no-docker shard targets | Keep one release cycle as compatibility shims. | `cos-test cluster --lane <name>` / `cos-test broad`. |
