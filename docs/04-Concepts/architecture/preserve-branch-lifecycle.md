# Preserve Branch Lifecycle

> Status: draft
> Updated: 2026-05-02
> Related: [ADR-110](../adrs/ADR-110-preserve-branch-governance.md), [Preserve Branch Governance Report](../reports/preserve-branch-governance-2026-05-02.md)

## Purpose

Preserve branches are an airbag for concurrent-agent work. They should prevent loss, not become a hidden second backlog. This document defines the lifecycle for `codex/preserve-*` branches.

## Lifecycle States

| State | Meaning | Allowed next action |
|---|---|---|
| `open` | Work preserved but not evaluated. | inspect, split, restore selectively, mark obsolete. |
| `partially-integrated` | Some files or commits were restored. | continue selective restore or close with evidence. |
| `integrated` | Preserve tip or equivalent changes are in `HEAD`. | delete after verification. |
| `obsolete` | Work is superseded and not needed. | delete after human approval. |
| `delete-approved` | Operator approved deletion. | delete branch. |


## OS Kernel vs Consumer Projection

Preserve governance is defined in the Cognitive OS kernel but must run against any project that consumes the SO. The kernel owns:

- ADR and lifecycle documentation;
- `scripts/cos-doctor-preserve.sh`;
- behavior tests and fixtures;
- manifest schema and branch-state semantics.

Consumer projects receive a projection configured by environment or flags:

```bash
bash scripts/cos-doctor-preserve.sh --project-dir /path/to/app --branch-pattern 'codex/preserve-*' --base-ref main --json
```

Consumer defaults should be conservative: warn on missing manifests, warn on mixed scope, and fail in strict mode when a preserve branch is not integrated or is delete-approved but still present.

## Manifest Path

```text
.cognitive-os/preserve-manifests/<safe-branch-name>.json
```

`<safe-branch-name>` replaces `/` with `__`.

Example:

```json
{
  "branch": "codex/preserve-example-wip-20260502",
  "created_at": "2026-05-02T16:00:00Z",
  "created_by": "codex",
  "source_branch": "main",
  "source_head": "abc1234",
  "reason": "preserve WIP before validation capsule",
  "scope": "validation-capsule",
  "status": "open",
  "files": ["scripts/cos-validation-capsule.sh"],
  "integration_commit": null,
  "delete_after": null
}
```

## Doctor Semantics

`bash scripts/cos-doctor-preserve.sh --json` reports one row per preserve branch:

- `manifest_exists`
- `mixed_scope`
- `categories`
- `tip_is_ancestor_of_head`
- `tip_exists_not_ancestor_of_head`
- `candidate_delete`
- `status`
- `findings`

## Reintegrating Work

Use the safest method that preserves scope:

1. Prefer selective restore for a few known files.
2. Use targeted cherry-pick for a single-scope commit.
3. Avoid merging mixed-scope preserve branches wholesale.

Before declaring work restored, verify:

```bash
git merge-base --is-ancestor <commit> HEAD
# and/or
git cat-file -e HEAD:<required-file>
```

## Deleting Preserve Branches

A branch is a delete candidate when:

- the tip is an ancestor of `HEAD`; or
- manifest status is `integrated`, `obsolete`, or `delete-approved`.

Deletion remains a human action until a later policy explicitly automates it.
