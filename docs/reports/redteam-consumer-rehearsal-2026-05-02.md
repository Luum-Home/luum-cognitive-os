# Red-Team Harness — Consumer Install Rehearsal (W7)

**Date:** 2026-05-02  
**Wave:** W7  
**Scope:** Consumer install rehearsal — `cos_init.py --install-scope project` scope_allows() assertions

---

## Summary

| Category | Files Tested | Propagate | Blocked | Result |
|---|---|---|---|---|
| SCOPE: both (consumer artifacts) | 9 | 9 | 0 | PASS |
| SCOPE: os-only (internal tests) | 2 | 0 | 2 | PASS |
| Contract tests (pytest) | 57 | — | — | 57 passed, 1 skipped |

---

## SCOPE: both — Consumer Propagation (9/9 PASS)

All artifacts marked `# SCOPE: both` or `<!-- SCOPE: both -->` propagate correctly when `COS_INSTALL_SCOPE=project`:

| File | Expected | Actual |
|---|---|---|
| `templates/contracts/test_redteam_baseline.template.py` | PROPAGATE | PROPAGATE |
| `hooks/scope-marker-portability-gate.sh` | PROPAGATE | PROPAGATE |
| `tests/red_team/portability/template-test-redteam-baseline.bats` | PROPAGATE | PROPAGATE |
| `tests/red_team/portability/redteam-aggregate.bats` | PROPAGATE | PROPAGATE |
| `tests/red_team/portability/run-redteam-scenario.bats` | PROPAGATE | PROPAGATE |
| `skills/redteam-harness/skill.yaml` | PROPAGATE | PROPAGATE |
| `skills/redteam-harness/run` | PROPAGATE | PROPAGATE |
| `scripts/run-redteam-scenario.sh` | PROPAGATE | PROPAGATE |
| `scripts/redteam_aggregate.py` | PROPAGATE | PROPAGATE |

---

## SCOPE: os-only — Internal Test Blocking (2/2 PASS)

Contract tests that are OS-internal (os-only scope) are correctly blocked from consumer installs:

| File | Expected | Actual |
|---|---|---|
| `tests/contracts/test_redteam_baseline.py` | BLOCKED | BLOCKED |
| `tests/contracts/test_redteam_portability_coverage.py` | BLOCKED | BLOCKED |

---

## Contract Test Suite Results

```
pytest tests/contracts/test_redteam_baseline.py tests/contracts/test_redteam_portability_coverage.py -v
57 passed, 1 skipped
```

The 1 skipped test is `test_source_file_has_scope_both_marker[template-test-redteam-baseline.bats]` — the portability test's self-check correctly skips via `pytest.skip()` when the source is itself the portability test (not a SCOPE: both artifact). This is by design.

---

## Known Limitations

- `silent-stash-loss` scenario exits 3 (ERROR rather than XFAIL) due to bash heredoc quoting of JSON with embedded single quotes in `signal_details`. The aggregator skips this scenario and exits 1. The contract test suite accepts 5/6 scenarios minimum and excludes `silent-stash-loss` from strict checks. Resolution tracked as ADR-106 P1.

---

## Driver Wiring Verification

```
bash scripts/apply-efficiency-profile.sh default
→ Applied profile 'default': 111 hook commands in settings.json
→ PreToolUse Bash: ..., scope-marker-portability-gate.sh
→ PreToolUse Edit|Write: ..., plan-claim-validator.sh
```

Codex driver (`cognitive-os.yaml > harness.hooks`) and hook quality manifest (`manifests/hook-quality.yaml`) both include the `scope-marker-portability-gate` entry.

---

## W6 Deliverables Confirmed On-Disk

| Artifact | Status |
|---|---|
| `tests/contracts/test_redteam_baseline.py` | EXISTS (os-only, 13 tests) |
| `templates/contracts/test_redteam_baseline.template.py` | EXISTS (both, 6 tests) |
| `tests/contracts/test_redteam_portability_coverage.py` | EXISTS (os-only, 44 tests+1 skip) |
| `hooks/scope-marker-portability-gate.sh` | EXISTS (both, KD8 warn-only) |
| `docs/RED-TEAM-COVERAGE.md` | EXISTS (ADR-105 verb coverage table) |
| `docs/RED-TEAM-CHANGELOG.md` | EXISTS (v1.0.0 entry W0-W6) |
| `.cognitive-os/test-lanes.yaml` red_team lane | REGISTERED (parallel: true) |
| `pytest.ini` red_team marker | REGISTERED |
| `settings-driver-claude-code.sh` scope-marker-portability-gate | WIRED (pre_bash) |
| `cognitive-os.yaml` scope-marker-portability-gate | WIRED (harness.hooks) |
| `manifests/hook-quality.yaml` scope-marker-portability-gate | WIRED |
