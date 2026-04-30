# Merge Readiness: Master Plan Onboarding Proof

> Final merge-readiness snapshot for `codex/master-plan-onboarding-proof`.

## Branch State

Current branch:

- `codex/master-plan-onboarding-proof`

Observed comparison after fetching remotes on 2026-04-23:

- `codex/master-plan-onboarding-proof` is 11 commits ahead of `origin/main`.
- `codex/master-plan-onboarding-proof` is 0 commits behind `origin/main`.
- The worktree was clean before final validation.

## Master Plan Status

The executable master plan checklist is complete:

- `docs/business/master-plan-checklist.md` has no unchecked items.
- `.cognitive-os/plans/architecture/skills-rules-canonicalization-workplan.md` has no unchecked deliverables.

Completed product guarantees now have artifacts and tests:

- Product promise and positioning are documented.
- Kernel contract exists in docs, manifest, and contract tests.
- Product zones classify the repository into `core`, `compatibility`, `extensions`, and `experimental`.
- Runtime hardcoding guardrails prevent new central-runtime promotion of non-core subsystems without an allowlist.
- Compatibility layer and provider inventory distinguish implemented adapters from documented targets.
- Bootstrap and settings-driver flows are harness-aware for Claude and Codex.
- Capability-centric routing is enforced in dispatch, gateway selection, skill routing, and metrics.
- Skills and rules now use `.cognitive-os/skills/cos` and `.cognitive-os/rules/cos` as canonical artifact contracts, while `.claude/...` remains a Claude Code driver projection.
- Product proof paths exist for onboarding, portability, provider/kernel checks, quality gates, and five-minute demo flow.

## Automated Validation

The following validation passed locally on this branch:

- Exact declared Python CI lane:
  - `python3 -m pytest tests/contracts/test_kernel_contract.py tests/contracts/test_product_zones.py tests/contracts/test_killswitch.py tests/unit/test_execution_profile.py tests/unit/test_compatibility_layer.py tests/unit/test_outcome_metrics.py tests/unit/test_model_router.py tests/unit/test_config_loader.py tests/unit/test_cross_platform_discipline.py tests/behavior/test_self_install.py -q`
  - Result: `1302 passed, 21 skipped, 16 xfailed`
- Expanded merge lane covering runtime, bootstrap, contracts, installers, status, and proof-path tests:
  - `342 passed`
- Go provider/kernel and installer/CLI/wizard lanes:
  - `go test ./internal/provider/... ./internal/validator/... ./pkg/hook/... -count=1`
  - `(cd cmd/cos && go test ./internal/installer/... ./internal/cli/... ./internal/wizard/... -count=1)`
- Shell syntax:
  - `bash -n hooks/*.sh scripts/*.sh bin/cognitive-os.sh install.sh`
- Product-facing documentation link integrity:
  - `README.md`
  - `CONTRIBUTING.md`
  - `docs/README.md`
- YAML configuration parsing:
  - all `*.yaml` and `*.yml`
- Docker Compose config:
  - `docker compose -f docker-compose.cognitive-os.yml config --quiet`
- Security CI check:
  - `hooks/secret-detector.sh`
  - `.gitignore` coverage for `.env`, `.env.local`, `*.pem`, and `*.key`

## Manual Proofs

The following manual/executable proof paths passed locally:

- First-run onboarding proof:
  - `bash scripts/demo-first-run-onboarding.sh --harness=codex`
  - Result: install, status, and total first-run budgets passed.
- Cross-harness portability proof:
  - `bash scripts/demo-portability-proof.sh`
  - Result: Codex and Claude projections produced matching canonical core fingerprints while keeping driver settings separate.

## Non-CI Suite Note

`python3 -m pytest tests/ -q` was attempted as an exploratory full-repository run on local Python 3.14. It is not the declared CI lane and began surfacing broad failures from non-merge lanes while also mutating `.claude/settings.json`. The run was stopped to prevent further worktree contamination, the generated settings diff was reverted, and the declared CI plus expanded merge lanes were run cleanly afterward.

This should be treated as a follow-up test-suite hygiene issue, not as a hidden pass. The merge signal for this branch is the declared CI lane, expanded product merge lane, Go lanes, documentation/config checks, security checks, and manual proof paths above.

## Merge Recommendation

This branch is ready to merge into `main` after a clean merge dry-run.

Before deleting branches:

1. Confirm `main` contains commit `bb5e962` or a later merge commit containing it.
2. Push `main`.
3. Delete the local branch `codex/master-plan-onboarding-proof`.
4. Delete the remote branch `origin/codex/master-plan-onboarding-proof`.

## Risk Notes

- Do not delete `.claude/...` projection paths. They are no longer the source-of-truth, but Claude Code still needs them as a driver surface.
- Continue treating full-suite pytest failures outside the declared CI lane as test-suite hygiene debt that should be triaged intentionally.
- New runtime additions must continue to pass product-zone and runtime-hardcoding contracts.
