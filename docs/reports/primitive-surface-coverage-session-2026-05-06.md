# Session Report: Primitive Surface Partials and Observe-Only TUI

Date: 2026-05-06

## Goal

Close the next primitive surface coverage cut by making partial harness debt inspectable, resolving codex-adapter-needed and projectable partial buckets, adding an observe-only TUI surface, and regenerating ACC plus primitive surface reports.

## Decisions

- Partial coverage debt is not the same as unclassified debt. It is accepted as visible work only when every gap has a policy, severity, status, and next action.
- The first priority bucket is `must-fix-parity`; no current rows use it in this cut.
- The next priority bucket is `codex-adapter-needed`; the first twenty codex-adapter-needed rows were resolved by either reclassifying no-equivalent Codex Agent events as aligned or documenting optional governance/observer behavior.
- `tui` becomes a real `surface_id=ui` only after `cos tui --snapshot` exists, exits 0, and consumes the same primitive surface reports.
- The TUI can become operable only through whitelisted report-refresh actions, explicit `--confirm`, and append-only action receipts. It must not accept arbitrary shell commands.

## Implemented

- Added prioritized partial report generator:
  - `scripts/primitive_harness_partials.py`
  - `docs/reports/primitive-harness-partials-latest.json`
  - `docs/reports/primitive-harness-partials-latest.md`
- Added operable TUI with safety gates:
  - `scripts/cos-tui`
  - `cos tui --snapshot`
  - `cos tui --operate refresh-coverage --confirm`
  - `cos tui --operate refresh-partials --confirm`
  - `cos tui --operate refresh-all --confirm`
  - `cos tui --operate <action> --dry-run`
- Extended primitive surface coverage:
  - `surface_id=tui`
  - `surface_kind=ui`
  - `observable=true`
  - `operable=true` only for whitelisted report-refresh primitives
  - receipts append to `.cognitive-os/metrics/tui-actions.jsonl`
- Resolved the first thirty-two codex-adapter-needed rows from the previous reports. First batch:
  - `hooks/adaptive-bypass.sh`
  - `hooks/adr-detector.sh`
  - `hooks/agent-bus-monitor.sh`
  - `hooks/agent-checkpoint.sh`
  - `hooks/agent-output-verifier.sh`
  - `hooks/agent-prelaunch.sh`
  - `hooks/agent-quota-advisor.sh`
  - `hooks/agent-qwen-bridge.sh`
  - `hooks/agent-working-dir-inject.sh`
  - `hooks/aguara-scan.sh`
- Resolved the second batch of codex-adapter-needed rows:
  - `hooks/architecture-compliance.sh`
  - `hooks/assumption-tracker.sh`
  - `hooks/auto-checkpoint.sh`
  - `hooks/auto-refine.sh`
  - `hooks/auto-repair-dispatcher.sh`
  - `hooks/auto-rollback-trigger.sh`
  - `hooks/auto-verify.sh`
  - `hooks/background-agent-reminder.sh`
  - `hooks/blast-radius.sh`
  - `hooks/claim-validator.sh`
- Resolved the third codex-adapter-needed batch:
  - `hooks/clarification-gate.sh`
  - `hooks/clarification-interceptor.sh`
  - `hooks/code-review-on-commit.sh`
  - `hooks/completeness-check-llm.sh`
  - `hooks/completion-gate.sh`
  - `hooks/concurrent-write-guard.sh`
  - `hooks/confidence-gate-llm.sh`
  - `hooks/confidence-gate.sh`
  - `hooks/confidentiality-enforcer.sh`
  - `hooks/consequence-evaluator.sh`
  - `hooks/content-policy.sh`
  - `hooks/context-diet.sh`
- Cleared the `projectable-needs-driver` bucket by adding explicit projectable script surface evidence.
- Added ratchets for `unclassified_gaps`, `must-fix-parity`, `partial_count`, `codex-adapter-needed`, and `projectable-needs-driver`.
- Hardened operable TUI with `cos tui --receipts --json` and dashboard-visible TUI receipt metrics.

## Result

- `unclassified_gaps = 0`
- `must-fix-parity = 0`
- `partial_count = 52`
- `codex-adapter-needed = 52`
- `projectable-needs-driver = 0`
- `tui` is operable for whitelisted report refresh actions, reports its action receipts, and remains non-operable for arbitrary primitive execution.
- `tui` is present as a UI surface only because the runtime snapshot contract exists.

## Verification

```bash
python3 scripts/primitive_harness_coverage.py --project-dir .
python3 scripts/primitive_harness_partials.py --project-dir .
bash scripts/cos tui --snapshot
bash scripts/cos tui --operate refresh-all --confirm
bash scripts/cos tui --receipts --json
python3 -m pytest \
  tests/unit/test_primitive_harness_coverage.py \
  tests/contracts/test_primitive_harness_coverage_contract.py \
  tests/contracts/test_primitive_harness_partials_contract.py \
  tests/contracts/test_primitive_harness_partial_ratchets.py \
  tests/contracts/test_projectable_script_surface_evidence.py \
  tests/contracts/test_cos_cli_surface_contract.py \
  tests/contracts/test_cos_tui_operable_surface_contract.py -q
python3 scripts/acc_pipeline.py --project-dir . --fail-new --brief
```

## Next Steps

- Continue resolving the remaining 52 `codex-adapter-needed` rows by adding true adapters where Codex has an equivalent event and adding aligned no-equivalent policies where it does not.
- Consider additional TUI operations only after each action has a whitelist entry, `--confirm`, audit receipts, and explicit tests.
- Keep `must-fix-parity = 0` and `unclassified_gaps = 0` as ratchets.
