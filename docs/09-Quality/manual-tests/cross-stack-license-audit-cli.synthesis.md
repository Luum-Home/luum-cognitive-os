---
type: quality-synthesis
source: docs/09-Quality/manual-tests/cross-stack-license-audit-cli.md
provenance: "Manual test for the canonical cos license audit primitive that must be run before release, dependency adoption, or public claims about commercial/SaaS safety."
---

## What it is
A manual test for `cos license audit` (canonical command `scripts/cos license audit --json`), the Cognitive OS cross-stack license/security posture checker. It is the mandated primitive for pre-release, pre-dependency-adoption, and commercial-safety-claim gating — agents should not substitute ad-hoc `pip-licenses`/`go-licenses`/raw `trivy fs` scans unless Tool Discovery explicitly allows a bypass.

## Key mechanics
- `scripts/cos license audit --json`: exits `0` on acceptable posture, `2` when blocked findings exist (e.g. mutable Trivy workflow actions like `aquasecurity/trivy-action@vX`, or denied Trivy versions). Emits JSON with schema `cross-stack-license-audit-report/v1`.
- Toolchain posture: Syft+Grype is the primary scanner; Trivy is a guarded secondary/manual cross-validation tool.
- Strict mode for release gates: `scripts/cos license audit --strict --json` fails on WARN-level posture, not just blocked findings.
- Covers: manifest-backed scanner policy (`manifests/cross-stack-license-audit.yaml`), blocked Trivy versions, unsafe mutable workflow action refs, JSON output consumed by ADR-201/ADR-211 readiness checks.
- Explicitly does NOT replace: `/repo-scout`/`/repo-forensics` for new external tool adoption, ADR-208 dependency-adoption evidence, ScanCode Toolkit forensic legal review, or manual legal review for enterprise distribution.
- Automated test coverage: `tests/unit/test_cross_stack_license_audit.py`, `tests/behavior/test_cross_stack_license_audit_cli.py`, `tests/unit/test_tool_discovery_preuse.py`, `tests/behavior/test_tool_discovery_preuse_gate.py` — proving blocked-version detection, workflow-pin validation, JSON schema conformance, and Tool Discovery routing back to this primitive.
- Troubleshooting: missing scanner binaries should be installed via `bash scripts/install-syft-grype.sh` and optionally `bash scripts/install-trivy.sh`, not ad-hoc installs.

## Relations & where used
Implementation: `lib/cross_stack_license_audit.py`, `scripts/cos-cross-stack-license-audit`, `scripts/cos`. Governed by ADR-212 (Cross-Stack License Audit Toolchain). Ties into the license-policy rule (BLOCK AGPL/SSPL/BSL, ALLOW MIT/BSD/Apache) and supply-chain-defense (digest pinning) from the project's always-active security rules.

## Status / caveats
No inconsistencies noted in source. Straightforward procedural/reference doc; no dated run log.
