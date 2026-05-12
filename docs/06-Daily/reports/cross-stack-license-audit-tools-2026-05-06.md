# Cross-Stack License Audit Tools — 2026-05-06

## Decision

Adopt **Syft+Grype as primary** and **Trivy as optional secondary** for
Cognitive OS pre-launch cross-stack license/security audit.

The original shortlist correctly identified Trivy and Syft+Grype as the best
OSS candidates because they are multi-stack, CI-friendly, and Apache-2.0. The
current 2026 supply-chain context changes the ordering: Trivy remains useful,
but not as a blind primary CI action.

## Landscape

| Tool | Stack coverage | License | Approach | Best for |
|---|---|---|---|---|
| Trivy | Python, Go, Node, Rust, Java, C#, containers, IaC | Apache-2.0 | SBOM + license + CVE | Fast local secondary scan |
| Syft + Grype | Multi-stack | Apache-2.0 | SBOM generation + scan | Primary auditable pipeline |
| OSV-Scanner | Multi-stack | Apache-2.0 | OSV vuln DB, license checks | Vulnerability sweep |
| ScanCode Toolkit | File-level multi-stack | Apache-2.0 | Deep license/copyright scan | Forensic legal audit |
| FOSSA | Multi-stack | Commercial | SaaS policy gates | Enterprise compliance |
| Snyk Open Source | Multi-stack | Commercial | SaaS/IDE policy | Existing Snyk teams |
| Dependency-Track | Multi-stack | Apache-2.0 | Self-hosted SBOM platform | Enterprise infra |
| Black Duck / Mend | Multi-stack | Commercial | M&A-grade audit | Legal-heavy diligence |

## Implementation

Implemented artifacts:

- `docs/02-Decisions/adrs/ADR-212-cross-stack-license-audit-toolchain.md`
- `manifests/cross-stack-license-audit.yaml`
- `lib/cross_stack_license_audit.py`
- `scripts/cos-cross-stack-license-audit`
- `scripts/license-audit-syft-grype.sh`
- `scripts/license-audit-trivy.sh`
- `scripts/install-syft-grype.sh`
- `scripts/install-trivy.sh`

## Guardrails

- Known compromised Trivy versions are blocked by policy.
- Unsafe `aquasecurity/trivy-action` / `aquasecurity/setup-trivy` workflow
  usage is blocked unless explicitly pinned to an immutable commit and reviewed.
- Syft+Grype creates a durable SBOM artifact before scanning.
- Scanner wrappers write to `.cognitive-os/reports/license-audit/`, not metrics
  JSONL, because these are evidence artifacts rather than high-volume events.

## Sources checked

- Trivy official docs/GitHub: Apache-2.0 scanner with license scanning support.
- Anchore OSS docs/GitHub: Syft/Grype Apache-2.0 SBOM + scan workflow.
- OSV-Scanner docs: license checks exist, but vulnerability scanning is the main fit.
- ScanCode Toolkit GitHub/docs: Apache-2.0 file-level license/copyright scanner.
- GitHub Security Advisory / Microsoft / StepSecurity reports for March 2026 Trivy compromise.
