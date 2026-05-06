# ADR-198: Release External Readiness Gate

## Status

Accepted — 2026-05-06

## Context

ADR-191 added GoReleaser, checksums, GitHub Actions, and Homebrew tap handoff.
Publishing a real release also needs external state that cannot be fabricated in
a local checkout: a clean git index, a new version tag, GitHub authentication,
a reachable Homebrew tap repository, and a `HOMEBREW_TAP_GITHUB_TOKEN` secret.

The repository already has historical tags and releases, so `v0.1.0` is not a
valid next-release target. The gate must check the requested version rather than
assuming a fixed bootstrap tag.

## Decision

Add `scripts/cos-release-external-readiness` as a non-publishing preflight gate.

The script checks:

- working tree cleanliness and unresolved conflicts;
- local and remote tag collision for the requested version;
- GoReleaser binary availability;
- GitHub CLI authentication;
- main repository reachability;
- Homebrew tap repository reachability;
- presence, but never value, of `HOMEBREW_TAP_GITHUB_TOKEN`;
- `make test-laptop` success through `--run-test-laptop` before a real release.

The script is intentionally read-only. It does not create repositories, tags,
secrets, or releases. Without `--run-test-laptop`, it reports blocked so an
operator cannot confuse external readiness with the required release validation
lane. The GitHub release workflow also runs `make test-laptop` before GoReleaser.

## Consequences

- Operators can distinguish local release readiness from external publication
  readiness before invoking GoReleaser.
- The Homebrew token is never printed.
- Release publication remains a deliberate operator action after the gate is
  green.

## Acceptance Criteria

```text
ACCEPTANCE CRITERIA:
1. The readiness script reports unresolved conflicts as blocked.
2. The readiness script detects an existing local or remote tag for the requested version.
3. Missing Homebrew tap access or missing `HOMEBREW_TAP_GITHUB_TOKEN` blocks publication readiness.
4. The script emits JSON with booleans and reasons without printing secret values.
5. A real release preflight requires `make test-laptop` to pass before tagging/running GoReleaser.
```
