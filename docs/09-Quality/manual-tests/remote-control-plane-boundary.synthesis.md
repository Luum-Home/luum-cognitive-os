---
type: quality-synthesis
source: docs/09-Quality/manual-tests/remote-control-plane-boundary.md
provenance: "Validates the first research/contract slice for remote Cognitive OS operation, confirming chat/web/API ingress stays separate from provider execution and no secret material is accessed."
---

## What it is
A manual test that checks `manifests/remote-control-plane-alternatives.yaml`, its supporting research report, and ADR-161 all agree that remote ingress (chat/web/API) is architecturally separated from provider/executor adapters, with no access to stored secrets.

## Key mechanics
- Open `manifests/remote-control-plane-alternatives.yaml` and confirm every project entry has `remote_ingress`, `provider_strategy`, `credential_strategy`, `license_posture`, and `source_urls`.
- Confirm `openclaw`, `agent-zero`, and `opencode-current` are present as reference-only projects with `provider_strategy: delegates-to-cos`.
- Confirm `pinchy` is marked `license_posture: blocked`.
- Open the dated research report `docs/06-Daily/reports/remote-control-plane-alternatives-2026-05-05.md` and confirm chat/notification surfaces are described as an unverified inbound layer (not direct execution) and the report states that vendor secret stores are never read.
- Open `ADR-161-remote-control-plane-and-provider-adapter-boundary.md` and confirm its Decision section separates "remote ingress" from "provider/executor adapters."
- Automated checks: `tests/contracts/test_remote_control_plane_alternatives.py`, `tests/audit/test_adr_contracts.py` + `test_adr_locations.py`, and `scripts/acc_pipeline.py --project-dir . --brief`.
- Evidence captured on 2026-05-05: remote-control-plane contract 3 passed; ADR audit/location 454 passed; ACC brief `gate.status=pass, finding_count=0`.

## Relations & where used
Ties directly to ADR-161 and `manifests/remote-control-plane-alternatives.yaml`; part of the same research-first family as `task-lifecycle-worktree-pr-flow.md` (ADR-162) covering future remote/`cosd` control-plane work.

## Status / caveats
Dated evidence block (captured 2026-05-05) is embedded as a point-in-time snapshot; re-running the automated checks is required to confirm current state. The source file has a numbering gap in its steps list (step 3 text is missing between steps 2 and 4) — flagged as a source inconsistency, not fixed here.
