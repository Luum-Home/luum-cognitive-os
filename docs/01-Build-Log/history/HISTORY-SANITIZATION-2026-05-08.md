# Public History Sanitization Disclosure — 2026-05-08

## Summary

This repository was private and pre-public when the one-time history
sanitization ran on 2026-05-08. The rewrite was performed before public
release to remove operator-local/private data from historical file contents
while preserving the development record.

The canonical runtime report is copied, with local-only rollback paths
redacted, at
[`docs/06-Daily/reports/history-sanitization-20260508T061208Z.json`](../reports/history-sanitization-20260508T061208Z.json).
The frozen policy used to authorize the rewrite remains at
[`docs/01-Build-Log/history/manifest-snapshot-2026-05-07.yaml`](manifest-snapshot-2026-05-07.yaml).

## What was cleaned

The rewrite applied the manifest-backed replacement rules from ADR-218 to
historical blob contents. The public report records these replacements:

- operator personal email text in blobs was replaced with the GitHub noreply
  identity `2144218+MatiasNAmendola@users.noreply.github.com`;
- operator name text in blobs was normalized to `MatiasNAmendola`;
- operator home-directory prefixes were replaced with `<home>`;
- absolute local repository paths were replaced with `<repo>`;
- historical fixture home paths were replaced with
  `/Users/<fixture-user>/Projects/<fixture-project>`;
- private consumer codenames and service names were replaced with neutral
  placeholders such as `<consumer-codename-a>` and `<consumer-service>`.

The rewrite report shows the pre-rewrite head
`2d99d40a3382232f9ab3f32e85cdd89b777670bb`, the post-rewrite head
`db846adb6290456b431bfc191b08543f56a2e8d7`, and the commit count preserved at
2,440 commits before and after the rewrite.

## What was preserved

The sanitization was intentionally scoped. It did not create a clean-root repo
and it did not erase the project's technical or legal history. Per the policy
and disclosure trail, the rewrite preserved:

- commit count and DAG shape;
- commit messages, author dates, and commit dates;
- human commit author and committer metadata;
- ordinary development work, ADRs, tests, documentation, and release notes;
- license-transition evidence for the Apache-2.0 to FSL-1.1-MIT change;
- scanner fixtures and positive controls such as intentionally fake secret-like
  strings used by tests.

## Human authorship was not deleted

The sanitization did **not** remove human authorship. The pre-public risk audit
policy for commit author email metadata is
`preserve-human-author-emails; do-not-auto-rewrite`. This means human commit
author metadata is treated as provenance, not as a secret to delete. The rewrite
focused on sensitive text inside historical file blobs.

## Apache to FSL was not hidden

The license transition from Apache-2.0 to FSL-1.1-MIT is intentionally retained
as public history. The manifest's preserve rules include Apache/FSL license
terms because the transition is legal and product history that readers should be
able to audit. The sanitization did not hide or rewrite that transition.

## Private, pre-public context

This action happened while the repository was private and before public
publication. The purpose was to avoid publishing operator-local paths, private
consumer identifiers, and similar pre-public residue while keeping the real
project history inspectable.

## Verification pointers

- Runtime report:
  [`docs/06-Daily/reports/history-sanitization-20260508T061208Z.json`](../reports/history-sanitization-20260508T061208Z.json)
- Manifest snapshot:
  [`docs/01-Build-Log/history/manifest-snapshot-2026-05-07.yaml`](manifest-snapshot-2026-05-07.yaml)
- Pre-sanitization SHA inventory:
  [`docs/01-Build-Log/history/pre-sanitization-sha-inventory-2026-05-07.txt`](pre-sanitization-sha-inventory-2026-05-07.txt)
- Policy ADR:
  [`docs/02-Decisions/adrs/ADR-218-history-sanitization-toolchain.md`](../adrs/ADR-218-history-sanitization-toolchain.md)
