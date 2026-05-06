# Session Report: Primitive Surface Partials and Observe-Only TUI

Date: 2026-05-06

## Goal

Close the next primitive surface coverage cut by making partial harness debt inspectable, resolving the first codex-adapter-needed bucket, adding an observe-only TUI surface, and regenerating ACC plus primitive surface reports.

## Decisions

- Partial coverage debt is not the same as unclassified debt. It is accepted as visible work only when every gap has a policy, severity, status, and next action.
- The first priority bucket is `must-fix-parity`; no current rows use it in this cut.
- The next priority bucket is `codex-adapter-needed`; the first ten rows were resolved by either reclassifying no-equivalent Codex Agent events as aligned or documenting optional governance/observer behavior.
- `tui` becomes a real `surface_id=ui` only after `cos tui --snapshot` exists, exits 0, and consumes the same primitive surface reports.
- The TUI is observe-only in this cut. It does not mutate primitives and does not claim runtime hook execution.

## Implemented

- Added prioritized partial report generator:
  - `scripts/primitive_harness_partials.py`
  - `docs/reports/primitive-harness-partials-latest.json`
  - `docs/reports/primitive-harness-partials-latest.md`
- Added observe-only TUI:
  - `scripts/cos-tui`
  - `cos tui --snapshot`
- Extended primitive surface coverage:
  - `surface_id=tui`
  - `surface_kind=ui`
  - `observable=true`
  - `operable=false`
- Resolved the first ten codex-adapter-needed rows from the previous report:
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

## Result

- `unclassified_gaps = 0`
- `partial_count = 87`
- `codex-adapter-needed = 74`
- `tui` is present as a UI surface only because the runtime snapshot contract exists.

## Verification

```bash
python3 scripts/primitive_harness_coverage.py --project-dir .
python3 scripts/primitive_harness_partials.py --project-dir .
bash scripts/cos tui --snapshot
python3 -m pytest \
  tests/unit/test_primitive_harness_coverage.py \
  tests/contracts/test_primitive_harness_coverage_contract.py \
  tests/contracts/test_primitive_harness_partials_contract.py \
  tests/contracts/test_cos_cli_surface_contract.py -q
python3 scripts/acc_pipeline.py --project-dir . --fail-new --brief
```

## Next Steps

- Continue resolving `codex-adapter-needed` rows by adding true adapters where Codex has an equivalent event and adding aligned no-equivalent policies where it does not.
- Add an operable TUI mode only after commands have safety gates, audit receipts, and explicit tests.
- Keep `must-fix-parity = 0` and `unclassified_gaps = 0` as ratchets.
