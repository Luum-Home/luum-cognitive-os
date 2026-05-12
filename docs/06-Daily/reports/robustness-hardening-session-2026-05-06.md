# Robustness hardening session — 2026-05-06

## Goal

Resolve the remaining root robustness gaps identified during the 2026-05-06
operator review and leave executable evidence for the two active workstreams:
ADR scope creep and mechanical-vs-governance research scoring. Also validate the
local Homebrew install path as far as it can be proven without the external tap.

## Completed hardening

| Area | Result | Evidence |
|---|---|---|
| Validation capsule launch races | Agent launches blocked by an active validation capsule are now enqueued instead of dropped/rescheduled manually. | `hooks/dispatch-gate.sh`, `tests/unit/test_validation_capsule.py` |
| Transient stash residue | Successful auto pre-agent snapshot restores now drop matching `auto-pre-agent-*` stashes; conflicted restores preserve the stash. | `hooks/post-agent-snapshot-restore.sh`, `tests/integration/test_post_agent_snapshot_restore.py` |
| Dormant/live orchestrator mismatch | `OrchestratorSubscriber` is wired into the real orchestrator run path. | `scripts/orchestrator.py`, `tests/integration/test_orchestrator_cli.py` |
| Headless runtime portability | Headless runtime contract now checks systemd and Kubernetes artifacts instead of only macOS launchd shape. | `scripts/cos-headless-runtime-contract`, `tests/contracts/test_headless_runtime_contract.py` |
| ADR scope creep | ADR relationship audit now detects long `extends`/`supersedes`/`replaces` chains and cycles. | `scripts/audit_adrs.py`, `tests/unit/test_adr_relationship_scope.py` |
| Research audit calibration | `ResearchQualityAdvisor` now separates mechanical and governance scoring modes, including auto-detection. | `lib/research_quality_advisor.py`, `tests/unit/test_research_quality_advisor.py` |
| Local Homebrew canary | Opt-in real Homebrew canary now installs from a temporary local tap and checksummed Git HEAD source tarball, then verifies `cos version` and `brew test cognitive-os`. | `scripts/cos-homebrew-local-canary`, `Formula/cognitive-os.rb`, `tests/integration/test_fresh_install_canary.py` |

## Homebrew canary decision and result

Decision: run the local canary because the user explicitly accepted the opt-in
mutation of the real Homebrew prefix.

Command executed:

```bash
COS_RUN_HOMEBREW_CANARY=1 HOMEBREW_NO_AUTO_UPDATE=1 scripts/cos-homebrew-local-canary --apply
```

Observed result:

```json
{"ok": true, "stage": "complete", "tap": "luum-local/cos-canary-35731", "version": " Cognitive OS v0.26.0 ", "kept_installed": false}
```

Cleanup verification after the run:

```text
no luum-local/cos-canary-* tap remains
cognitive-os-installed-exit=1
```

Important boundary: this proves the local formula semantics through a real
Homebrew install. It still does not prove the future external tap command:

```bash
brew install luum-home/tap/cognitive-os
```

That command remains blocked until the real external tap exists and a release is
published into it.

## ADR warning decision

Original audit warning:

```text
ADR-187 -> ADR-173 -> ADR-172 -> ADR-170
```

Final decision before v1.0: resolve, not waive.

ADR-187 was reclassified from an `extends` layer into a proof contract with
`decision_inputs: [ADR-172, ADR-173]`. That preserves the dependency context
without adding another `extends`/`supersedes` lineage link on top of
ADR-173 → ADR-172 → ADR-170. The audit guardrail remains active and still emits
warnings for synthetic long chains; the real ADR graph no longer carries this
scope-creep warning.

## Validation evidence

Focused validation passed on 2026-05-06:

```bash
python3 -m pytest \
  tests/unit/test_adr_relationship_scope.py \
  tests/unit/test_research_quality_advisor.py \
  tests/contracts/test_standalone_distribution_contract.py \
  tests/integration/test_fresh_install_canary.py::TestReleaseCheckPlumbing::test_homebrew_formula_has_install_smoke \
  tests/integration/test_fresh_install_canary.py::TestReleaseCheckPlumbing::test_homebrew_local_canary_script_exists_and_is_opt_in \
  tests/integration/test_fresh_install_canary.py::TestReleaseCheckPlumbing::test_homebrew_local_canary_default_is_non_mutating_json \
  -q
```

Observed result:

```text
18 passed in 0.38s
```

## Remaining work

1. Create/publish the real external Homebrew tap and run
   `brew install luum-home/tap/cognitive-os` against it.
2. Resolve the ADR-187 relationship chain before release, or capture an explicit
   release waiver.
3. Keep the Homebrew local canary opt-in; do not add it to default CI because it
   mutates the host Homebrew prefix.
