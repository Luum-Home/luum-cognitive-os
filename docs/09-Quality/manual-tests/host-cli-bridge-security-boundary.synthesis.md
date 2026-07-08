---
type: quality-synthesis
source: docs/09-Quality/manual-tests/host-cli-bridge-security-boundary.md
provenance: "Manual test validating the design-only contract for a future host CLI bridge before any runtime code is allowed to execute host CLIs from Docker or cosd."
---

## What it is
A docs/manifest/contract-only manual test (no provider calls, no credential-store reads) that verifies the not-yet-implemented "host CLI bridge" is still correctly gated as `design-only` — a guardrail preventing premature or accidental runtime execution of host CLIs from containers.

## Key mechanics
- Purpose is explicitly pre-implementation validation: confirms the contract, not runtime behavior.
- Steps walk through `manifests/host-cli-bridge-contract.yaml`, checking: `status: design-only`; allowed transports limited to Unix domain socket or loopback HTTP with a random token; default bind localhost-only with remote bind forbidden by default; a required command allowlist; default commands are non-provider only; provider commands are planned and require human approval; blocked paths explicitly include `~/.codex/auth.json`, `~/.claude`, Keychain, cookies, `.env`, and `secrets`; audit rows require task, command, approval, exit, redaction, and artifact fields.
- Automated checks: `tests/contracts/test_host_cli_bridge_contract.py` and `tests/contracts/test_cos_instance_implementation_phases.py`.
- Expected result: contract tests pass, host provider execution remains unimplemented and gated to a future phase, and the `host-cli-bridge` profile stays `planned`/write-blocked in `manifests/cos-instance-profiles.yaml`.

## Relations & where used
Validates `manifests/host-cli-bridge-contract.yaml` and `manifests/cos-instance-profiles.yaml`. Directly relevant to the credential-boundary claims also exercised in the sibling `headless-docker-service-runtime.md` drill (host CLI bridge is called out there as a "not proven" future capability).

## Status / caveats
Describes a feature in `design-only` status — the test proves the contract stays a contract (unimplemented and gated), not that the bridge works. This is a deliberate pre-implementation guardrail, not an inconsistency.
