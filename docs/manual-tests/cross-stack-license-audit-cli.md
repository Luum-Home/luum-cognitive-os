# Cross-Stack License Audit CLI Manual Test

**Primitive**: `cos license audit`  
**Canonical command**: `scripts/cos license audit --json`  
**ADR**: [ADR-212: Cross-Stack License Audit Toolchain](../adrs/ADR-212-cross-stack-license-audit-toolchain.md)  
**Manifest**: `manifests/cross-stack-license-audit.yaml`  
**Implementation**: `lib/cross_stack_license_audit.py`, `scripts/cos-cross-stack-license-audit`, `scripts/cos`

## Purpose

Run the Cognitive OS cross-stack license/security posture check before release,
dependency adoption, or public claims about commercial/SaaS safety. This command
is the canonical primitive; agents should not replace it with ad-hoc
`pip-licenses`, `go-licenses`, raw `trivy fs`, or one-off scanner chains unless
Tool Discovery explicitly allows a bypass.

## Quick command

```bash
scripts/cos license audit --json
```

Expected behavior:

- exits `0` when scanner posture and workflow policy are acceptable;
- exits `2` when blocked findings exist, such as mutable Trivy workflow actions
  or denied Trivy versions;
- emits JSON with schema `cross-stack-license-audit-report/v1`;
- identifies Syft+Grype as the primary toolchain;
- treats Trivy as guarded secondary local/manual cross-validation.

## Strict release check

```bash
scripts/cos license audit --strict --json
```

Use this in release-readiness or pre-launch checklists when WARN-level posture
should fail the gate.

## What the primitive covers

- Manifest-backed scanner policy.
- Syft+Grype primary scanner posture.
- Trivy secondary scanner policy.
- Blocked Trivy versions.
- Unsafe mutable GitHub workflow actions such as `aquasecurity/trivy-action@vX`.
- JSON output suitable for ADR-201/ADR-211 readiness consumers.

## What it does not replace

- `/repo-scout` or `/repo-forensics` for adopting a new external tool.
- ADR-208 dependency adoption evidence before adding dependencies.
- ScanCode Toolkit forensic legal review when SBOM results are inconclusive.
- Manual legal review for customer/enterprise distribution commitments.

## Automated tests

```bash
python3 -m pytest \
  tests/unit/test_cross_stack_license_audit.py \
  tests/behavior/test_cross_stack_license_audit_cli.py \
  tests/unit/test_tool_discovery_preuse.py \
  tests/behavior/test_tool_discovery_preuse_gate.py \
  -q
```

The tests prove:

1. known-bad Trivy versions are blocked;
2. mutable Trivy workflow actions are blocked;
3. immutable Trivy workflow pins are allowed;
4. the CLI emits the expected JSON schema;
5. Tool Discovery routes ad-hoc license-audit tooling back to this primitive.

## Troubleshooting

If `scripts/cos license audit --json` reports missing scanner binaries, install
through the governed wrappers rather than ad-hoc commands:

```bash
bash scripts/install-syft-grype.sh
bash scripts/install-trivy.sh   # optional secondary scanner only
```

Then re-run:

```bash
scripts/cos license audit --json
```
