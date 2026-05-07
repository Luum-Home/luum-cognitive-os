# ADR-212 — Cross-Stack License Audit Toolchain

## Status
Accepted


<!-- SCOPE: OS -->

**Status**: Accepted  
**Date**: 2026-05-06  
**Related**: ADR-006, ADR-145, ADR-208  
**Source**: Q2 tool-adoption review, `.cognitive-os/strategy/research/11-cross-stack-license-audit-tools.md`

---

## Context

Cognitive OS already had skills for investigating external tools before
adoption (`/repo-scout`, `/repo-forensics`, `/scout`, `/pattern-audit`,
`/audit-integrity`, `/harness-audit`) and now has ADR-208 commit-path
enforcement for dependency additions. That still leaves a second gap:
periodic cross-stack scanning of the existing repository for license and
vulnerability drift.

Stack-specific tools (`pip-licenses`, `go-licenses`, `license-checker`) are
insufficient as the canonical pre-launch audit because Cognitive OS is
multi-stack: Python, Go, Node, shell scripts, Homebrew formulae, optional
lanes, generated lockfiles, and vendored/reference material.

## Market review

| Tool | Stack coverage | License | Approach | Best for |
|---|---|---|---|---|
| Trivy (Aqua Security) | Multi-stack: Python, Go, Node, Rust, Java, C#, container, IaC | Apache-2.0 OSS | SBOM + license + CVE | Fast local scans; useful secondary scanner |
| Syft + Grype (Anchore) | Multi-stack | Apache-2.0 OSS | Syft generates SBOM; Grype scans it | Primary CI/CD-style pipeline and auditable SBOM artifact |
| OSV-Scanner (Google) | Multi-stack | Apache-2.0 OSS | OSV vulnerability database; license checks exist but are not the main strength | Vulnerability-focused sweep |
| ScanCode Toolkit (AboutCode/nexB) | File-level multi-stack | Apache-2.0 OSS | Deep source/license/copyright analysis | Forensic legal audits |
| FOSSA | Multi-stack enterprise | Commercial | SaaS dashboard and policy gates | Enterprise compliance |
| Snyk Open Source | Multi-stack | Commercial | SaaS/IDE/license policy | Teams already on Snyk |
| Dependency-Track (OWASP) | Multi-stack | Apache-2.0 OSS | Self-hosted SBOM platform | Organizations with compliance infra |
| Black Duck / Mend | Multi-stack enterprise | Commercial | M&A-grade scanning | Legal-heavy enterprise diligence |

## Current supply-chain caveat

Trivy is still a strong scanner, but in March 2026 its ecosystem had a
reported supply-chain compromise involving malicious Trivy release artifacts
and compromised GitHub Actions tags. Therefore Cognitive OS must not adopt
Trivy as a blind primary CI action by mutable tag.

For this project:

- Syft+Grype is the **primary** pre-launch cross-stack audit path.
- Trivy is an **optional secondary** scanner for local/manual cross-validation.
- Trivy GitHub Actions are blocked unless pinned by reviewed immutable commit
  and explicitly re-approved after incident review.
- Known compromised Trivy artifact versions are blocked by policy.

## Decision

Adopt a manifest-backed cross-stack audit policy with:

1. **Primary scanner**: Syft + Grype.
2. **Secondary scanner**: Trivy, local/manual only, denied for known-bad versions
   and mutable CI action usage.
3. **Forensic escalation**: ScanCode Toolkit when SBOM-level results are
   inconclusive or a release/legal review requires file-level evidence.
4. **Commercial tools**: FOSSA/Snyk/Black Duck/Mend are not required for
   pre-launch; they remain enterprise/customer-driven integrations.

## Enforcement

Add `manifests/cross-stack-license-audit.yaml` and
`scripts/cos-cross-stack-license-audit`.

The audit must:

- verify scanner availability/version posture;
- block known compromised Trivy versions;
- scan GitHub workflows for unsafe `aquasecurity/trivy-action` or
  `aquasecurity/setup-trivy` usage;
- emit JSON suitable for ADR-201/ADR-211 readiness consumption;
- provide wrapper scripts for Syft+Grype and optional Trivy runs.

## Consequences

### Positive

- One multi-stack audit path covers Python, Go, Node, and future stacks.
- SBOM output creates durable evidence for legal/security review.
- Avoids SaaS lock-in and credentials for pre-launch.
- Treats security scanners themselves as supply-chain dependencies.

### Negative / trade-offs

- Syft+Grype requires two binaries instead of Trivy's single binary.
- Local installs still require operator action.
- Trivy remains useful but cannot be represented as a zero-risk default after
  the 2026 incident.

## Acceptance criteria

```bash
python3 -m pytest tests/unit/test_cross_stack_license_audit.py tests/behavior/test_cross_stack_license_audit_cli.py -q
scripts/cos license audit --json
bash -n scripts/install-syft-grype.sh scripts/install-trivy.sh scripts/license-audit-syft-grype.sh scripts/license-audit-trivy.sh
```

The tests must prove unsafe Trivy workflow usage is blocked and known-bad
Trivy versions are classified as blocked.

## Alternatives rejected
- Leave the decision as conversation-only or strategy-only documentation — rejected because ADR-067 requires executable decision records with auditable verification.

## Verification
```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
```
