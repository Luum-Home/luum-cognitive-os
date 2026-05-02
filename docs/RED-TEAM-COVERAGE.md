# Red-Team Coverage Map

> Verb → scenario mapping. Required by design §4 W6 gate (ADR-105 §3).
> Every ADR-105 high-stakes verb must have ≥1 scenario.

## ADR-105 Verb Coverage

| ADR-105 Verb | Scenario ID | Wave | Scope | Status |
|---|---|---|---|---|
| `archived` | `archive-presence-fallacy` | W3 | both | active |
| `wired` | `unwired-constant` | W3 | both | active |
| `verified` | `plan-checkbox-no-evidence` | W3 | both | active |
| `verified` | `partial-completion-claim` | W4 | both | active |
| `tested` | `regex-false-positives` | W4 | both | active |
| `completed` | `silent-stash-loss` | W4 | os-only | xfail (ADR-106 P1) |

### Coverage Summary

| Verb | Count | Gap? |
|---|---|---|
| `archived` | 1 | No |
| `wired` | 1 | No |
| `tested` | 1 | No |
| `verified` | 2 | No |
| `completed` | 1 (xfail) | No (xfail until ADR-106 P1) |

All 5 ADR-105 high-stakes verbs have coverage. The `completed` verb scenario is
marked `xfail` until ADR-106 Priority 1 ships (stash-leak alarm).

## Scenario Index

| Scenario ID | File | Scope | Category | Verbs |
|---|---|---|---|---|
| `archive-presence-fallacy` | `tests/red_team/scenarios/archive-presence-fallacy.yaml` | both | archive-fallacy | archived |
| `unwired-constant` | `tests/red_team/scenarios/unwired-constant.yaml` | both | unwired-constant | wired |
| `plan-checkbox-no-evidence` | `tests/red_team/scenarios/plan-checkbox-no-evidence.yaml` | both | false-done | verified |
| `partial-completion-claim` | `tests/red_team/scenarios/partial-completion-claim.yaml` | both | partial-completion | verified |
| `regex-false-positives` | `tests/red_team/scenarios/regex-false-positives.yaml` | both | regex-fp | tested |
| `silent-stash-loss` | `tests/red_team/scenarios/silent-stash-loss.yaml` | os-only | silent-loss | completed |

## KD6 Gate Status

| Artifact | Scope | Portability Test | Falsification |
|---|---|---|---|
| `scripts/verify-archived.sh` | both | `tests/red_team/portability/verify-archived.bats` | Yes |
| `scripts/run-redteam-scenario.sh` | both | `tests/red_team/portability/run-redteam-scenario.bats` | Yes |
| `scripts/redteam_aggregate.py` | both | `tests/red_team/portability/redteam-aggregate.bats` | Yes |
| `hooks/plan-claim-validator.sh` | both | `tests/red_team/portability/plan-claim-validator.bats` | Yes |
| `skills/redteam-harness/SKILL.md` | both | `tests/red_team/portability/skill-redteam-harness.bats` | Yes |
| `tests/red_team/scenarios/archive-presence-fallacy.yaml` | both | `tests/red_team/portability/scenario-archive-presence-fallacy.bats` | Yes |
| `tests/red_team/scenarios/unwired-constant.yaml` | both | `tests/red_team/portability/scenario-unwired-constant.bats` | Yes |
| `tests/red_team/scenarios/plan-checkbox-no-evidence.yaml` | both | `tests/red_team/portability/scenario-plan-checkbox-no-evidence.bats` | Yes |
| `tests/red_team/scenarios/regex-false-positives.yaml` | both | `tests/red_team/portability/scenario-regex-false-positives.bats` | Yes |
| `tests/red_team/scenarios/partial-completion-claim.yaml` | both | `tests/red_team/portability/scenario-partial-completion-claim.bats` | Yes |

Layer 2 enforcement (CI): `tests/contracts/test_redteam_portability_coverage.py`
Layer 1 enforcement (pre-commit): `hooks/scope-marker-portability-gate.sh`

## Anti-Rubber-Stamp Guards

1. **Falsification case mandatory** (Layer 2): every portability test must contain
   the keyword `falsification`. Enforced by `test_redteam_portability_coverage.py`.

2. **Meta-scenario** (`partial-completion-claim`, W4): the harness itself detects
   rubber-stamp portability tests. A fake portability test that always passes is
   graded as fail, causing baseline regression.

3. **Pre-commit gate** (`scope-marker-portability-gate.sh`, KD8 warn-only):
   staged `SCOPE: both` files without portability tests emit a warning.
   Promote to block via `COS_SCOPE_GATE_MODE=block`.
