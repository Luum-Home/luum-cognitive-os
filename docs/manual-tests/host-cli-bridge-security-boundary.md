# Manual Test — Host CLI Bridge Security Boundary

## Purpose

Validate the design-only contract for the future host CLI bridge before any
runtime code can execute host CLIs from Docker or `cosd`.

## Preconditions

- No provider calls are executed by this manual test.
- No Codex/Claude credential stores are read.
- This test verifies docs/manifest/contracts only.

## Steps

1. Open `manifests/host-cli-bridge-contract.yaml`.
2. Confirm `status: design-only`.
3. Confirm allowed transports are only Unix domain socket or loopback HTTP with
   random token.
4. Confirm default bind is localhost-only and remote bind is forbidden by
   default.
5. Confirm command allowlist is required.
6. Confirm default commands are non-provider only.
7. Confirm provider commands are planned and require human approval.
8. Confirm blocked paths include `~/.codex/auth.json`, `~/.claude`, Keychain,
   cookies, `.env`, and `secrets`.
9. Confirm audit rows require task, command, approval, exit, redaction, and
   artifact fields.
10. Run the automated contract tests.

## Automated checks

```bash
python3 -m pytest tests/contracts/test_host_cli_bridge_contract.py -q
python3 -m pytest tests/contracts/test_cos_instance_implementation_phases.py -q
```

## Expected result

- Contract tests pass.
- Host provider execution remains unimplemented and gated to a future phase.
- `host-cli-bridge` profile remains planned/write-blocked in
  `manifests/cos-instance-profiles.yaml`.
