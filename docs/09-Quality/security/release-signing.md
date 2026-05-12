# Release Signing & Verification

This document describes the current and planned posture for signing
`luum-agent-os` (Cognitive OS) release tags and the artifacts that
accompany them. It is written for hostile-auditor consumption: every
command is reproducible against a fresh checkout of the repo.

**Audience:** consumers verifying a release; security reviewers; operators
preparing to cut a public release tag.

**Last updated:** 2026-05-08
**Applies to:** all `v0.27.x` tags and forward.

---

## 1. Current State (Honest Disclosure)

The repository currently publishes **unsigned** annotated tags. As of
this writing:

| Tag                            | Type      | GPG-signed? | SSH-signed? | Sigstore? |
| ------------------------------ | --------- | ----------- | ----------- | --------- |
| `v0.27.0`                      | annotated | NO          | NO          | NO        |
| `v0.27.1`                      | annotated | NO          | NO          | NO        |
| `v0.27.1-pre-history-rewrite`  | annotated | NO          | NO          | NO        |

You can confirm this yourself:

```bash
git fetch --tags
git tag -v v0.27.1
# Output: "error: no signature found"
```

This is a **known gap**, tracked under M1/M2 of
`docs/09-Quality/legal/pre-public-readiness-checklist.md`. The first tag intended
for general public consumption (`v1.0.0` or the first tag flipped to
`public-release: true` in release notes — whichever lands first) MUST be
signed per §3 below; until then, consumers should treat the tags as
"published, but not cryptographically attested."

The project is community-maintained and the maintainer's signing
material has not yet been published. The provenance posture is
therefore:

- Source provenance: git history + force-push audit (see ADR-218 and the
  `history-sanitization-*` tombstone branch).
- Artifact provenance: SBOM (`sbom.json` + sha256, regeneratable per
  `docs/09-Quality/security/supply-chain.md` §1.3).
- Cryptographic attestation: **not yet wired**. See §3.

---

## 2. What "A Signed Release" Means Here

When the project flips to signed releases, every `vX.Y.Z` tag will carry
**all** of the following; consumers can refuse a release that is missing
any one of them.

1. **Signed annotated git tag.** The tag object itself is signed, so
   anyone with the maintainer's public verification material can verify
   the tag without trusting the hosting provider:
   ```bash
   git tag -v vX.Y.Z
   ```
2. **`sbom.json` + `sbom.json.sha256`.** Already shipped today. The SBOM
   is the CycloneDX 1.6 file at the repo root, regeneratable per
   `docs/09-Quality/security/supply-chain.md` §1.3.
3. **Detached signature for the SBOM** so the SBOM cannot be swapped
   without breaking verification (cosign or GPG output).
4. **Release-notes hash manifest.** A `RELEASE-MANIFEST.txt` listing the
   sha256 of every artifact attached to the release page (binaries,
   archives, SBOM, license files), itself signed.

Until §3 is wired, items 3 and 4 do not exist; only items 1 and 2 are
in flight.

---

## 3. Aspirational: Sigstore / cosign Integration Plan

This section describes the intended end-state. Sections marked
`(planned)` are not implemented yet.

### 3.1 Choice of mechanism

Two acceptable options for the project, in priority order:

1. **Sigstore keyless signing via `cosign`** — preferred. No long-term
   signing material to publish or rotate; uses OIDC identity proof tied
   to the maintainer's hosting-provider account, anchored in the public
   Rekor transparency log. Industry standard for OSS releases
   (Kubernetes, Helm, kubectl, distroless, sigstore itself).
2. **GPG-signed git tags** — fallback if cosign tooling is unavailable
   in the maintainer's environment. Requires publishing a long-term
   public verification artifact alongside the first signed release.

The project will adopt cosign as the primary mechanism and continue to
emit signed git tags as a secondary defense for consumers who prefer
identity-based verification.

### 3.2 Concrete steps to implement (planned)

The following are the exact steps the operator runs once to wire signed
releases. They are reproducible: every command works copy-paste against
the current `main`.

#### Step 1 — Install tooling (one time, on the release machine)

macOS:

```bash
brew install cosign sigstore-go gnupg
```

Linux (download cosign from the upstream sigstore release page; checksum
the binary against the upstream SHA file before installing — pin the
expected version in `manifests/dependencies.yaml` so future runs use the
same checksum):

```bash
COSIGN_VERSION=v2.4.1
# Pull from the upstream sigstore release page documented at the
# sigstore project homepage; verify the checksum against the SHA file
# published next to the binary before trusting.
sudo apt-get install -y gnupg
```

#### Step 2 — Configure git to sign tags by default

GPG path:

```bash
gpg --quick-generate-key "Luum Cognitive OS Release <release@example.invalid>" rsa4096 sign 2y
gpg --armor --export release@example.invalid > docs/09-Quality/security/release-signing-id.asc
SIGNID=$(gpg --list-secret-keys --keyid-format=long release@example.invalid | awk '/sec/ {split($2,a,"/"); print a[2]; exit}')
git config --local user.signingkey "$SIGNID"
git config --local tag.gpgSign true
```

SSH path (lighter-weight, recommended for solo maintainer; requires
git 2.34+):

```bash
git config --local gpg.format ssh
git config --local user.signingkey "$HOME/.ssh/release_sign.pub"
git config --local tag.gpgSign true
echo "release@example.invalid $(cat $HOME/.ssh/release_sign.pub)" \
  > .git/allowed_signers
git config --local gpg.ssh.allowedSignersFile .git/allowed_signers
```

#### Step 3 — Cut a signed tag

```bash
VERSION=v1.0.0
git tag -s "$VERSION" -m "Release $VERSION"
git tag -v "$VERSION"   # confirms the signature locally before publishing
# Publish the tag with the operator's normal tag-publish step.
```

#### Step 4 — Sign the SBOM with cosign (keyless)

```bash
COSIGN_EXPERIMENTAL=1 cosign sign-blob \
  --yes \
  --output-signature sbom.json.sig \
  --output-certificate sbom.json.cert \
  sbom.json
```

`sbom.json.sig` and `sbom.json.cert` are uploaded to the release page
alongside `sbom.json` and `sbom.json.sha256`. The certificate is
anchored in Rekor automatically.

#### Step 5 — Generate the release manifest

```bash
{
  echo "# Release manifest for $VERSION"
  echo "# Generated $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  for f in sbom.json sbom.json.sig sbom.json.cert LICENSE NOTICE; do
    [ -f "$f" ] && shasum -a 256 "$f"
  done
} > RELEASE-MANIFEST.txt

cosign sign-blob --yes \
  --output-signature RELEASE-MANIFEST.txt.sig \
  --output-certificate RELEASE-MANIFEST.txt.cert \
  RELEASE-MANIFEST.txt
```

Upload `RELEASE-MANIFEST.txt`, `.sig`, and `.cert` to the release page.

#### Step 6 — Document the maintainer identity

Add to the release notes:

> Releases are signed by the maintainer's documented hosting-provider
> identity. cosign verification anchors against this identity via
> Sigstore Fulcio; consumers do not need to trust any long-term key.

The exact identity URL is recorded in the release notes for each tag,
so it can be rotated without invalidating older releases.

---

## 4. Consumer Verification (When Signed Releases Land)

Consumers verify a release end-to-end with three commands. The first
two work today against unsigned tags but will fail-closed; the third
becomes meaningful once §3 is wired.

```bash
# Anchor variables (replace with the values from the release notes)
VERSION=v1.0.0
REPO_DIR=luum-cognitive-os
EXPECTED_IDENTITY_REGEX='.*'           # set per release-notes guidance
EXPECTED_OIDC_ISSUER='.*'              # set per release-notes guidance
```

### 4.1 Verify the signed git tag

```bash
git -C "$REPO_DIR" tag -v "$VERSION"
# Expect: "Good signature ..." (GPG)
#    or:  "Good 'git' signature for ... using ssh key SHA256:..." (SSH)
```

If `git tag -v` reports `error: no signature found`, the tag is unsigned.
Until §3 is implemented this is the **expected** result; do not treat
it as evidence of tampering on a `v0.27.x` tag, only as the documented
gap.

### 4.2 Verify the SBOM checksum

```bash
shasum -a 256 -c <(echo "$(cat sbom.json.sha256)  sbom.json")
```

This already works today.

### 4.3 Verify the SBOM signature (post-§3)

```bash
COSIGN_EXPERIMENTAL=1 cosign verify-blob \
  --signature sbom.json.sig \
  --certificate sbom.json.cert \
  --certificate-identity-regexp "$EXPECTED_IDENTITY_REGEX" \
  --certificate-oidc-issuer-regexp "$EXPECTED_OIDC_ISSUER" \
  sbom.json
# Expect: "Verified OK"
```

Failure modes and what they mean:

- `error: failed to verify signature` → SBOM tampered with after signing,
  or wrong `.sig` / cert pair.
- `certificate identity` mismatch → file signed by someone other than
  the documented maintainer identity. Refuse the artifact.
- `transparency log entry not found` → signature was produced offline
  without Rekor inclusion. Refuse for production use.

### 4.4 Verify the release manifest

```bash
cosign verify-blob \
  --signature RELEASE-MANIFEST.txt.sig \
  --certificate RELEASE-MANIFEST.txt.cert \
  --certificate-identity-regexp "$EXPECTED_IDENTITY_REGEX" \
  --certificate-oidc-issuer-regexp "$EXPECTED_OIDC_ISSUER" \
  RELEASE-MANIFEST.txt

# Then re-check every artifact listed inside it:
grep -v '^#' RELEASE-MANIFEST.txt | awk '{print $1"  "$2}' | shasum -a 256 -c -
```

---

## 5. SBOM Attestation Linkage

The SBOM is attestable two ways once §3 lands:

1. **Detached signature** (above): `sbom.json.sig` covers exactly the
   bytes of `sbom.json` shipped with the release.
2. **In-toto attestation** (cosign `attest` subcommand): wraps the SBOM
   in a DSSE envelope so consumers can pull SBOM + signature in one
   blob:

   ```bash
   cosign attest --predicate sbom.json --type cyclonedx <artifact-ref>
   ```

   This is most useful when the project ships a container image. For
   the language-native (Python wheel / `go install` / npm) distribution
   the detached-signature flow in §4.3 is sufficient and simpler.

The release page MUST link the SBOM signature next to the SBOM itself.
The `docs/09-Quality/security/supply-chain.md` §5 procedure already requires
`sbom.json` + `sbom.json.sha256` on every release; once signed releases
are wired, that section gains `sbom.json.sig` + `sbom.json.cert` to the
required-file list.

---

## 6. Threat Model Notes

What signing does cover:

- Tampering with the source tree between the tag pointer and the
  release page (mitigated by signed tag + signed manifest).
- Swapping `sbom.json` after publication (mitigated by detached
  signature anchored in Rekor).
- "Wrong maintainer" attacks via stolen hosting-provider session
  (Sigstore certificate identity check rejects keyless signatures from
  any unexpected identity).

What signing does NOT cover (out of scope for this document):

- Compromise of the upstream package registry (PyPI, npm, Go module
  proxy). Mitigated separately by `uv.lock` / `package-lock.json` /
  `go.sum` hash verification — see `docs/09-Quality/security/supply-chain.md` §4.
- Build-step compromise (a malicious CI runner producing a "correctly
  signed" but malicious artifact). Mitigated by SLSA-style provenance,
  tracked as future work in supply-chain §4.2.
- Reproducibility of the binary artifacts themselves. Tracked in
  supply-chain §4.2 as aspirational.

---

## 7. Status Summary

| Item                                          | Status         | Evidence                                         |
| --------------------------------------------- | -------------- | ------------------------------------------------ |
| Tag-signing process documented                | done           | this document, §3                                |
| Verification commands documented              | done           | §4                                               |
| `v0.27.x` tags signed                         | aspirational   | `git tag -v v0.27.1` returns "no signature"      |
| Maintainer signing identity published         | aspirational   | not yet published; setup step in §3.2            |
| SBOM detached signature on releases           | aspirational   | §3.2 step 4                                      |
| Release manifest                              | aspirational   | §3.2 step 5                                      |
| Sigstore keyless signing wired                | aspirational   | tooling installation step in §3.2 step 1         |
| SBOM checksum present                         | done           | `sbom.json` + supply-chain §1.2 sha256           |

---

## 8. Cross-References

- `docs/09-Quality/security/supply-chain.md` — SBOM, license audit, dependency pinning
- `docs/09-Quality/legal/pre-public-readiness-checklist.md` — M1 (supply chain), M2 (signed releases / onboarding)
- ADR-218 — git history sanitization (provenance baseline)
- ADR-238 — supply-chain audit follow-ups (UNKNOWN SPDX enrichment)
- `manifests/dependencies.yaml` — third-party CLI tool inventory
