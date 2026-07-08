---
type: quality-synthesis
source: docs/09-Quality/security/release-signing.md
provenance: "Documents the current unsigned-tag posture and the planned cosign/Sigstore signing pipeline so consumers and auditors can verify release provenance."
---

## What it is
A hostile-auditor-facing spec for how `luum-agent-os` release tags and artifacts are (and will be) cryptographically attested. Every command is reproducible against a fresh checkout. Covers current state, the target end-state definition of "a signed release," the concrete cosign/GPG implementation plan, consumer verification steps, SBOM attestation linkage, and an explicit threat model.

## Key mechanics
- **Current state (honest disclosure):** all `v0.27.x` tags (`v0.27.0`, `v0.27.1`, `v0.27.1-pre-history-rewrite`) are unsigned annotated tags. `git tag -v v0.27.1` returns `error: no signature found` — documented as a known gap tracked under M1/M2 of the pre-public-readiness checklist, not evidence of tampering.
- **Definition of "signed release"** (once wired): (1) signed annotated git tag, (2) `sbom.json` + `sbom.json.sha256` (already shipped), (3) detached signature for the SBOM (cosign or GPG), (4) a signed `RELEASE-MANIFEST.txt` hashing every release artifact.
- **Signing mechanism priority:** cosign keyless signing via Sigstore (OIDC identity, Rekor transparency log) is primary; GPG-signed git tags are the fallback if cosign tooling is unavailable. SSH-format git signing is called out as the lighter-weight option for a solo maintainer.
- **Implementation plan (§3.2, planned):** install `cosign`/`sigstore-go`/`gnupg` → configure git to sign tags (GPG or SSH path) → cut a signed tag (`git tag -s`) → sign the SBOM with `cosign sign-blob` (produces `.sig`/`.cert`) → generate and sign `RELEASE-MANIFEST.txt` → document the maintainer's OIDC identity in release notes.
- **Consumer verification (§4):** `git tag -v` for the tag signature, `shasum -a 256 -c` against `sbom.json.sha256` (works today), `cosign verify-blob` for the SBOM signature and the release manifest (meaningful only post-§3). Failure modes are enumerated: tampered SBOM, identity mismatch, missing Rekor transparency-log entry.
- **SBOM attestation linkage:** detached signature (`sbom.json.sig`) is sufficient for the language-native distribution; in-toto/DSSE attestation via `cosign attest` is reserved for a future container-image distribution.
- **Threat model:** signing covers source-tree tampering between tag and release page, SBOM swapping post-publication, and "wrong maintainer" identity spoofing. It explicitly does NOT cover upstream registry compromise (mitigated separately by lockfile hash verification) or CI/build-step compromise (tracked as future SLSA-provenance work).

## Relations & where used
- `docs/09-Quality/security/supply-chain.md` — SBOM generation/regeneration procedure this doc's §5 depends on; §4.2 there cross-references this doc's signing plan.
- `docs/09-Quality/security/verify-public-release.md` — the consumer-facing verification walkthrough that exercises §2 (signed-tag check) of this document.
- `docs/09-Quality/legal/pre-public-readiness-checklist.md` — M1/M2 gate items this document's gap is tracked under.
- ADR-218 (git history sanitization / provenance baseline), ADR-238 (supply-chain audit follow-ups).
- `manifests/dependencies.yaml` — third-party CLI inventory (cosign, gnupg) referenced in the setup steps.

## Status / caveats
- The entire §3 implementation plan and every item marked `(planned)` or `aspirational` in the §7 status table is **not implemented** — only tag-signing/verification documentation and the SBOM checksum exist today. This is a forward-looking design doc as much as a status report; treat all cosign/GPG steps as unexecuted until a `v1.0.0`+ tag lands.
- Document is explicitly dated ("Last updated: 2026-05-08") and scoped to `v0.27.x` tags forward — a point-in-time snapshot that will go stale once signing is actually wired.
- Contains placeholder/invalid email addresses (`release@example.invalid`) by design, for copy-paste safety — not a real signing identity.
