---
type: concept-synthesis
source: docs/04-Concepts/architecture/red-team-harness-design.md
status: "DESIGNED — awaiting `sdd-apply`"
---

## What it is
Technical design for the `red-team-harness` SDD change: a standing adversarial test suite that recreates false-done failure surfaces (archive-presence-fallacy, unwired-constant, plan-checkbox-no-evidence, regex-false-positives, partial-completion, silent-stash-loss) and grades COS's verification stack against them.

## Key mechanics
- **Scenario YAML schema** (linchpin): `id`, `name`, `description`, `version`, `min_harness_version`, `scope` (`both`|`os-only`|`project`), `category`, `verbs` (ADR-105), `tags`, `expected_severity`, `replay` (agent_output + expected_extracted_claims, CI-safe default), `live` (opt-in via `COS_REDTEAM_LIVE=1`), `initial_state` (inline files or fixture_dir+overrides, git_init), `expected_fail_mode` (detection_signals, detection_command, detection_exit_code), `grading_rubric` (pass/partial/fail_modes), `cleanup`. Two fully-worked examples ship: `archive-presence-fallacy.yaml` (`both`) and `silent-stash-loss.yaml` (`os-only`, `expected_status: xfail` until ADR-106 P1).
- **Portability Test Contract (KD6 gate)**: tests live in `tests/red_team/portability/`; every test must satisfy 4 invariants — non-SO mini-repo, bilateral assertion, falsification probe (deliberate trap), documented mini-repo naming. Enforced two ways: pre-commit hook `hooks/scope-marker-portability-gate.sh` (blocks commits adding/modifying `SCOPE: both` markers without a paired test) and CI test `tests/contracts/test_redteam_portability_coverage.py` (requires ≥4 test cases and ≥1 case containing `falsification`).
- 5 component contracts specified: `scripts/verify-archived.sh` (`--archive-dir`/`--source-dir`/`--manifest`/`--config-globs`, exit codes 0-4, `--json`); `packages/verification-audit/lib/orchestrator_verify.py` + symlink `lib/orchestrator_verify.py` (extends `lib.ground_truth`, `HIGH_STAKES_VERBS = {archived, wired, tested, verified, claimed}`); `hooks/plan-claim-validator.sh` (`COS_PLAN_GLOB`/`COS_METRICS_DIR`/`COS_PLAN_VALIDATOR_MODE=warn|block`); `scripts/run-redteam-scenario.sh` (exit 0-3); `scripts/redteam-aggregate.py` (versioned `schema_version` JSON + Markdown output).
- Wave sequencing W0-W7, each with inputs/outputs/gate/blast-radius/rollback. Shared-file matrix flags `templates/agent-preamble.md` and `scripts/apply-efficiency-profile.sh` as merge-conflict candidates, resolved via `# === RED-TEAM-HARNESS START/END ===` block fences.
- Reuse decisions locked: EXTEND `lib/ground_truth.py`; PATTERN-DONOR `hooks/claim-validator.sh` and `tests/chaos/test_safety_drill.py`; SCHEMA-DONOR `tests/arena/scenarios/*.yaml`; OUTPUT-SCHEMA-PARALLEL `scripts/adr_implementation_ledger.py` (independent, shares `schema_version`+`generated_at`+`entries[]` shape only).
- Driver-projected hooks via `scripts/apply-efficiency-profile.sh` -> projects into `.claude/settings.json`, `.codex/hooks.json`, and the `cognitive-os.yaml` hook registry; a harness-driver-parity test asserts identical coverage across drivers.
- R10 (false portability declaration — the recursive false-done) is mitigated in 3 layers: pre-commit gate, CI contract test, and a meta-scenario `partial-completion-claim` (W4) that seeds a rubber-stamp portability test and asserts the harness catches it.

## Relations & where used
Inputs: `red-team-harness-proposal.md`, engram observations 16454 (explore) + 16474 (proposal). Cross-refs ADR-105 (claim verification), ADR-106 P1/P2, `cross-harness-authoring.md` §Agent Self-Check (all 9 `both` components must pass its 5-item check). RULES-COMPACT §13 (naming), §14/§15 (lane taxonomy/registry).

## Status / caveats
Status: DESIGNED — awaiting `sdd-apply`. 4 open uncertainties: `add_hook` exact signature in `scripts/apply-efficiency-profile.sh` unconfirmed (pseudocode only); bats availability in CI unconfirmed; `scope-marker-portability-gate.sh` PreToolUse Bash matcher pattern unconfirmed; symlink-target stability risk if `packages/` moves. Estimated 19-27h across 8 waves.
