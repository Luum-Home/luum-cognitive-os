# `docs/history/` — Pre-Sanitization Transparency Trail

This directory captures the auditable evidence that surrounds the one-time
git history sanitization scheduled for 2026-05-07 per
[ADR-218](../adrs/ADR-218-history-sanitization-toolchain.md).

**Why this exists**: a history rewrite changes every commit SHA. Without a
public, in-repo trail of (a) what the rewrite was supposed to do and (b)
what the pre-rewrite state looked like, nobody can later verify that the
rewrite was scoped to the declared replacement rules. This directory is
that trail.

## What's here

| File | Purpose | Captured |
|---|---|---|
| [`manifest-snapshot-2026-05-07.yaml`](manifest-snapshot-2026-05-07.yaml) | Frozen copy of `manifests/history-sanitization.yaml` at the moment the rewrite was authorized. Anyone with a pre-rewrite clone can `diff` against the live manifest to verify rules were not silently broadened post-execute. | 2026-05-07 |
| [`pre-sanitization-sha-inventory-2026-05-07.txt`](pre-sanitization-sha-inventory-2026-05-07.txt) | `git log --all --format='%H %ci %s'` — the full SHA + author-date + subject of every commit on every branch immediately before the rewrite. 1,775 entries. Anyone with a pre-rewrite clone can hash-compare against this file to verify the rewrite was strictly scoped. | 2026-05-07 |

After the rewrite executes, these files will be **joined** by:

| File (post-execute) | Purpose |
|---|---|
| `report-{timestamp}.json` | Schema-versioned `history-sanitization-report/v1` from the canonical primitive — replacement counts, blobs rewritten, commits rewritten, preserve-pattern hits. |
| `HISTORY-SANITIZATION-{date}.md` | Operator-facing disclosure: what was rewritten, why, how to verify, links to manifest + report + inventory. |

## How to verify the rewrite was scoped (for any third party)

1. Clone the **pre-rewrite** repository (the operator's pre-rewrite mirror at `~/.cognitive-os/recovery/pre-history-sanitization-{ts}.git` or the tag `v0.27.1-pre-history-rewrite` if pushed before the force-push).
2. Compare `git log --all --format='%H %ci %s'` against `pre-sanitization-sha-inventory-2026-05-07.txt`. They must match.
3. Compare `git show {pre-rewrite-SHA}` against `git show {post-rewrite-equivalent-SHA}` for any commit. The diff should consist exclusively of replacement-rule applications declared in `manifest-snapshot-2026-05-07.yaml`.
4. Verify `git log --all --format='%s'` (subject lines only) is **identical** between pre and post — the rewrite must not modify commit messages, only blob content.
5. Verify `git log --all --format='%ai %ci'` is **identical** between pre and post — the rewrite must not modify author dates or commit dates.

If any of those properties is violated, the rewrite was out-of-scope and
the operator owes a public explanation.

## What the rewrite does NOT change (per `git filter-repo --replace-text`
semantics)

- Commit messages
- Author identity (name + email)
- Committer identity (name + email)
- Author dates
- Commit dates
- Tree topology (file paths, directory structure)
- Number of commits per branch
- DAG topology (parents, merges)
- Tags (they need to be re-pointed manually post-rewrite, but their target
  *equivalence* is preserved by the rewrite — the pre-rewrite v0.27.1
  commit and the post-rewrite v0.27.1-equivalent commit are the same
  commit modulo the replacement rules)

The only thing that changes:
- Blob content matching the manifest's `text_replacements` patterns
- Cascading SHA changes (every commit re-hashes because its tree
  re-hashes because its blobs re-hashed)

## Preserve patterns (per the manifest)

Two pattern sets are explicitly **preserved** — the rewrite must not touch
them:

1. **License-transition evidence** (Apache 2.0 → FSL-1.1-MIT): 102+ hits
   in pre-rewrite history. The license switch at commit
   `598b95bd`-equivalent and successors is honest history; rewriting it
   would erase the legal narrative the operator wants preserved.
2. **Test fixture placeholders** (`[REDACTED]`, `deadbeef`-style positive
   controls): 25+ hits. These are intentional secrets-shaped strings that
   our scanners use as positive controls; rewriting them would break the
   audit suite.

If a future operator-side replacement rule would also match a preserve
pattern, the canonical primitive refuses to execute and asks the operator
to refine. See ADR-218 §"Hard rules" for the full enforcement contract.

## ADR + skill cross-references

- [ADR-218](../adrs/ADR-218-history-sanitization-toolchain.md) — primitive specification, hard rules, alternatives rejected
- [ADR-055b](../adrs/ADR-055b-destructive-git-block.md) — destructive-git operation gate (`COS_ALLOW_DESTRUCTIVE_GIT=1`)
- [`manifests/history-sanitization.yaml`](../../manifests/history-sanitization.yaml) — live (post-rewrite) manifest
- [`scripts/cos history sanitize`](../../scripts/cos-history-sanitization) — the canonical CLI
- [`lib/history_sanitization.py`](../../lib/history_sanitization.py) — implementation
