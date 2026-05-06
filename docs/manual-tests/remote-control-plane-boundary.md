# Manual Test — Remote Control Plane Boundary

## Purpose

Validate the first research/contract slice for remote Cognitive OS operation:
chat/web/API ingress is separate from provider execution, and no credential

## Preconditions

- Worktree is on the intended branch.
- No provider API keys or chat bot tokens are required.
- Network research artifacts have already been generated.

## Steps

1. Open `manifests/remote-control-plane-alternatives.yaml`.
2. Confirm every project has `remote_ingress`, `provider_strategy`,
   `credential_strategy`, `license_posture`, and `source_urls`.
   `reference-only`, with `provider_strategy: delegates-to-cos`.
4. Confirm `openclaw`, `agent-zero`, and `opencode-current` are present.
5. Confirm `pinchy` is `license_posture: blocked`.
6. Open `docs/reports/remote-control-plane-alternatives-2026-05-05.md`.
7. Confirm Telegram/chat/webhook surfaces are described as untrusted ingress,
   not direct execution.
8. Confirm the report includes the phrase `No credential scraping` and rejects
   reading vendor token stores.
9. Open `docs/adrs/ADR-161-remote-control-plane-and-provider-adapter-boundary.md`.
10. Confirm the Decision section separates `remote ingress` from
    `provider/executor adapters`.
11. Run the automated checks below.

## Automated checks

```bash
python3 -m pytest tests/contracts/test_remote_control_plane_alternatives.py -q
python3 -m pytest tests/audit/test_adr_contracts.py tests/audit/test_adr_locations.py -q
python3 scripts/acc_pipeline.py --project-dir . --brief
```

## Expected result

- Contract tests pass.
- ADR audit/location tests pass.
- ACC brief completes without loading `docs/acc/latest.json` into context.
- No secrets or credential values are present in the manifest, report, or ADR.

## Evidence captured on 2026-05-05

```text
tests/contracts/test_remote_control_plane_alternatives.py: 3 passed
tests/audit/test_adr_contracts.py + tests/audit/test_adr_locations.py: 454 passed
scripts/acc_pipeline.py --project-dir . --brief: gate.status=pass, finding_count=0
```
