---
adr: 191
title: COS Binary Release Pipeline
status: accepted
implementation_status: implemented
date: '2026-05-06'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: accepted record with explicit partial/phase scope
partial_remaining: null
remaining_in_scope: false
partial_remaining_basis: external tap was created and verified for v0.29.1
---

# ADR-191: COS Binary Release Pipeline

## Status

Accepted — 2026-05-06

## Context

The Go `cos` CLI builds locally and exposes the operator command surface, but
standalone distribution was still only partially represented by a Homebrew
formula stub and an older shell release helper. A standalone install path needs a
repeatable binary release pipeline, checksums, and a Homebrew tap cask handoff instead
of relying on a repository checkout.

## Decision

Adopt GoReleaser as the canonical `cos` binary release pipeline.

The release contract is:

- Git tags matching `v*.*.*` trigger `.github/workflows/cos-binary-release.yml`.
- The workflow runs `go test ./cmd/cos/...` before publishing.
- `.goreleaser.yaml` builds Linux and macOS binaries for `amd64` and `arm64`.
- Release archives include the `cos` binary plus the portable OS assets needed by
  installers and headless workers.
- Checksums are emitted as `checksums.txt`.
- Homebrew tap publication is delegated to `Luum-Home/homebrew-tap` as a GoReleaser cask, matching current GoReleaser packaging guidance.
- The in-repo `Formula/cognitive-os.rb` remains a `--HEAD` developer formula so
  it has no fake checksum.

## Consequences

- The repository now has real release plumbing instead of a SHA placeholder.
- Stable Homebrew tap installation depends on the external tap repository and
  `HOMEBREW_TAP_GITHUB_TOKEN` release secret. As of v0.29.1,
  `Luum-Home/homebrew-tap` exists and contains `Casks/cognitive-os.rb`.
- Local smoke tests install GoReleaser only through `scripts/install-goreleaser.sh`,
  which uses Homebrew on macOS and `go install github.com/goreleaser/goreleaser/v2@latest` as fallback.
- The existing `scripts/create-release.sh` is retained as a release-notes helper,
  not the canonical binary publishing path.

## Acceptance Criteria

```text
ACCEPTANCE CRITERIA:
1. `.goreleaser.yaml` exists and builds `./cmd/cos` for darwin/linux amd64/arm64.
2. `.github/workflows/cos-binary-release.yml` validates `go test ./cmd/cos/...` before release.
3. `Formula/cognitive-os.rb` contains no checksum placeholder and installs a local HEAD build.
4. `scripts/install-goreleaser.sh --check` validates the GoReleaser config when the binary is available.
5. `scripts/install-goreleaser.sh --check --snapshot-smoke` runs a no-publish snapshot release smoke.
6. `cd cmd/cos && go test ./...` passes.
```

## 2026-05-22 update — v0.29.1 external tap proof

The external tap handoff is no longer theoretical:

- Tap repository: `https://github.com/Luum-Home/homebrew-tap`
- Published cask: `Casks/cognitive-os.rb`
- Verified command: `brew info --cask Luum-Home/homebrew-tap/cognitive-os`
- Observed version: `0.29.1`
- Install command:

```bash
brew install --cask Luum-Home/homebrew-tap/cognitive-os
```

The in-repo `Formula/cognitive-os.rb` remains a developer `HEAD` formula by
design; the stable user-facing binary path is the external cask tap.

## Alternatives rejected

- Keep the placeholder Homebrew formula as the release path; rejected because it cannot produce verified checksums, archives, or a reproducible GitHub release.

## Verification

```bash
cd cmd/cos && go test ./...
bash scripts/install-goreleaser.sh --check
bash scripts/install-goreleaser.sh --check --snapshot-smoke
```
