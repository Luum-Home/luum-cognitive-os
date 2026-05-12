# Stash Review — License Switch Preservation

**Date**: 2026-05-06  
**Scope**: `stash@{0}` and `stash@{1}` on `claude/priceless-thompson-bbabce`  
**Reason**: Operator concern that progressive ADR work or WIP might be hidden in stashes or lost by cleanup/rollback.

## Summary

Two `auto-pre-agent-*` stashes were present on `main` after the ADR-200+ implementation batch:

- `stash@{0}` — `auto-pre-agent-toolu_01SYoc2d8fhjtesuie3NAZQM`
- `stash@{1}` — `auto-pre-agent-toolu_01PMVAmLX2fyQqHZYTzJ4J6D`

They were inspected and archived. No stash was dropped.

## Preservation artifacts

Ignored local archive:

```text
.cognitive-os/recovery/stash-review-20260506T225050Z/
```

The archive contains:

- `stash-0.patch`
- `stash-1.patch`
- `stash-0.name-status.txt`
- `stash-1.name-status.txt`
- `stash-0.stat.txt`
- `stash-1.stat.txt`
- `patch-sha256.txt`
- `patch.diff`
- `name-status.diff`

## Duplication result

The two stashes are duplicates.

```text
707c5dda28d9bc0e5a6d816b36c7e93c092ba6c9da298a1c8ae31201a76689a6  stash-0.patch
707c5dda28d9bc0e5a6d816b36c7e93c092ba6c9da298a1c8ae31201a76689a6  stash-1.patch
```

Both `name-status.diff` and `patch.diff` are empty.

## Content summary

The stash is not empty/self-generated noise. It is real product/legal WIP:

```text
.goreleaser.yaml
CONTRIBUTING.md
Formula/cognitive-os.rb
LICENSE
NOTICE
README.md
cmd/cos/internal/security/license.go
docs/08-References/business/executive-summary.md
docs/08-References/business/features.md
docs/08-References/business/open-source-design.md
docs/08-References/business/roadmap.md
docs/08-References/business/value-proposition.md
pyproject.toml
```

The patch switches public-facing license posture from Apache-2.0 to `FSL-1.1-MIT`, updates Homebrew metadata, docs/08-References/business positioning, and records that FSL is blocked as a dependency license but allowed as the project's own license.

## Decision

Because the patch is meaningful and the two stashes are identical, the safe action is:

1. preserve one copy in a review branch;
2. keep the original stashes for now;
3. do not merge/apply to `main` until license posture is explicitly approved.

Review branch created:

```text
codex/stash-license-review-20260506
```

Preservation commit on that branch:

```text
ced6dd48 wip: preserve FSL license switch stash
```

## Next decision needed

Before dropping the stashes or merging the branch, decide the product/legal license policy:

- keep Apache-2.0;
- switch to FSL-1.1-MIT before first public release;
- use a different source-available / delayed-open license;
- split licenses between core, plugins, cloud/service components.

Until that decision is made, the stashes should remain available or be archived through the state-retention recovery flow.
