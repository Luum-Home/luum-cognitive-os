<!-- SCOPE: both -->
---
name: patch-release
description: Use when preparing, validating, publishing, or diagnosing a Cognitive OS patch release without running the full laptop lane.
version: 1.0.0
last-updated: 2026-05-27
audience: os-dev
tags: [release, patch, goreleaser, validation]
summary_line: Repeatable patch release prepare/validate/publish/doctor workflow.
---

# /patch-release

## Purpose

Publish Cognitive OS patch releases through a repeatable primitive instead of ad hoc shell history. This skill is for low-risk patch releases where the proven patch lane is sufficient and the broad laptop lane is known to have unrelated dependency or state drift.

## Invocation

```bash
scripts/cos-patch-release prepare --version X.Y.Z --title "Short Release Title"
scripts/cos-patch-release validate
scripts/cos-patch-release doctor --version X.Y.Z --allow-warnings
scripts/cos-patch-release publish --version X.Y.Z --message "release: vX.Y.Z"
```

Trigger: release, patch release, GoReleaser, bump version, publish tag, release doctor.

## What it does

1. Prepares release metadata by updating `VERSION`, `cmd/cos/VERSION`, `pyproject.toml`, `uv.lock`, and `CHANGELOG.md`.
2. Validates the patch lane that proved `v0.29.6`: local privacy guard checks, targeted privacy tests, and `cmd/cos` Go tests.
3. Publishes via a session branch and `scripts/merge-to-main.sh`; it never pushes directly to `main`.
4. Tags the release and watches the `cos-binary-release` GitHub Actions run.
5. Diagnoses common release hazards with `scripts/cos-patch-release doctor`.

## Output

- `patch-release-prepare-ok version=X.Y.Z tag=vX.Y.Z`
- `patch-release-validate-ok`
- `patch-release-publish-ok version=X.Y.Z tag=vX.Y.Z`
- `release-doctor: pass|block version=X.Y.Z tag=vX.Y.Z`

## Edge cases

- Existing local or remote tag: `prepare`, `doctor`, and `publish` report/block before release.
- Dirty `uv.lock` after dependency sync: `prepare` blocks and requires `uv lock` repair.
- Scope portability red: `doctor` reports it as non-blocking for patch release unless another blocking check fails.
- Current branch is `main`: `publish` creates `codex/release-vX.Y.Z` before committing.

## Success Criteria

- [ ] `scripts/cos-patch-release prepare --version X.Y.Z --dry-run` prints planned files and commands without writing.
- [ ] `scripts/cos-patch-release validate` passes.
- [ ] `scripts/cos-patch-release publish --version X.Y.Z --dry-run` prints branch, commit, tag, and watch steps.
- [ ] `scripts/cos-patch-release doctor --version X.Y.Z` reports release hazards before publishing.

## Contextual Trigger

Keywords: patch release, release primitive, GoReleaser, release doctor, bump version, publish tag, `cos-binary-release`.
