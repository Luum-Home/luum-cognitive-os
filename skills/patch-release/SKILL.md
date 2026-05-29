<!-- SCOPE: both -->
---
name: patch-release
description: Use when preparing, validating, publishing, or diagnosing a Cognitive OS patch release without running the full laptop lane.
version: 1.0.0
last-updated: 2026-05-27
audience: os-dev
tags: [release, patch, goreleaser, validation]
routing_intents:
- intent: cognitive_os_patch_release
  description: User wants to prepare, validate, diagnose, publish, or automate a Cognitive OS patch release.
  confidence: 0.9
routing_patterns:
- pattern: \bpatch[- ]release\b
  confidence: 0.95
- pattern: \bcos-patch-release\b
  confidence: 0.95
- pattern: \b(release doctor|publish tag|GoReleaser)\b
  confidence: 0.8
summary_line: Repeatable patch release prepare/validate/publish/doctor workflow.
---

# /patch-release

## Purpose

Publish Cognitive OS patch releases through a repeatable primitive instead of ad hoc shell history. This skill is for low-risk patch releases where the proven patch lane is sufficient and the broad laptop lane is known to have unrelated dependency or state drift.

## Invocation

```bash
scripts/cos-patch-release prepare --version X.Y.Z --title "Short Release Title"
scripts/cos-patch-release plan --version X.Y.Z --title "Short Release Title"
scripts/cos-patch-release validate
scripts/cos-patch-release doctor --version X.Y.Z --allow-warnings
scripts/cos-patch-release publish --version X.Y.Z --message "release: vX.Y.Z"
```

Trigger: release, patch release, GoReleaser, bump version, publish tag, release doctor.

## What it does

1. Prepares release metadata by updating `VERSION`, `cmd/cos/VERSION`, `pyproject.toml`, `uv.lock`, and `CHANGELOG.md`.
2. Validates the patch lane: local privacy guard checks, Bun package-manager policy, targeted privacy tests, hook/research contracts, and `cmd/cos` Go tests.
3. Plans the full land-current-branch + prepare + validate + release-branch + tag + watch sequence with `scripts/cos-patch-release plan`.
4. Publishes via a session branch and `scripts/merge-to-main.sh`; it never pushes directly to `main`.
5. Tags the release and watches the `cos-binary-release` GitHub Actions run.
6. Diagnoses common release hazards with `scripts/cos-patch-release doctor`.

## Output

- `patch-release-prepare-ok version=X.Y.Z tag=vX.Y.Z`
- JSON dry-run plan from `scripts/cos-patch-release plan --version X.Y.Z`
- `patch-release-validate-ok`
- `patch-release-publish-ok version=X.Y.Z tag=vX.Y.Z`
- `release-doctor: pass|block version=X.Y.Z tag=vX.Y.Z`

## Edge cases

- Existing local or remote tag: `prepare`, `doctor`, and `publish` report/block before release.
- Dirty `uv.lock` after dependency sync: `prepare` blocks and requires `uv lock` repair.
- Scope portability red: `doctor` reports it as non-blocking for patch release unless another blocking check fails.
- Current branch is `main`: `publish` creates `codex/release-vX.Y.Z` before committing.
- Current branch contains unreleased feature/fix commits: run `scripts/cos-patch-release plan --version X.Y.Z` first. The plan shows the explicit `scripts/merge-to-main.sh --validate 'scripts/cos-patch-release validate' --recommended-lane patch-release --executed-lane patch-release` landing step before `prepare`.

## Success Criteria

- [ ] `scripts/cos-patch-release prepare --version X.Y.Z --dry-run` prints planned files and commands without writing.
- [ ] `scripts/cos-patch-release plan --version X.Y.Z` prints the complete land, prepare, validate, doctor, release-branch, tag, watch, and release-view sequence without writing.
- [ ] `scripts/cos-patch-release validate` passes.
- [ ] `scripts/cos-patch-release publish --version X.Y.Z --dry-run` prints branch, commit, tag, and watch steps.
- [ ] `scripts/cos-patch-release doctor --version X.Y.Z` reports release hazards before publishing.

## Contextual Trigger

Keywords: patch release, release primitive, GoReleaser, release doctor, bump version, publish tag, `cos-binary-release`.
