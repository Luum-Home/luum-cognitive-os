---

adr: 242
title: git-filter-repo Wrapper Preserves Remote and Refuses Non-Idempotent Re-Runs
status: accepted
implementation_status: partial
date: 2026-05-08
supersedes: []
superseded_by: null
extends: [ADR-094, ADR-117]
implementation_files:
  - scripts/cos-filter-repo-wrap.sh
  - lib/history_sanitization.py
  - tests/behavior/test_filter_repo_wrap.py
tier: maintainer
tags: [history-rewrite, governance, recovery, postmortem-2026-05-08]
---
# ADR-242: git-filter-repo Wrapper Preserves Remote and Refuses Non-Idempotent Re-Runs

## Status

Accepted — Slice A implemented. `scripts/cos-filter-repo-wrap.sh` preserves remotes, refuses idempotent reruns, writes recovery artifacts, and `lib/history_sanitization.py` delegates to it.

## Context

`git filter-repo --execute` strips `origin` as an intentional safety measure
to prevent accidental force-pushes of a rewritten history. Every invocation
during the 2026-05-08 session — sanitize passes, mailmap rewrites, and
text-replacement runs — required the operator to re-add `origin` afterward.
This happened four to five times in a single session.

The more dangerous failure mode was non-idempotency. Two parallel sessions
ran `filter-repo` against overlapping rule sets with mis-configured
environment variables. Each rewrite produced different SHAs because the
input rule files differed in subtle ways, but the wrapper code did not
detect that the same logical operation was being re-applied with drift.
The result was an unpredictable ancestry mutation that required a manual
recovery from a backup mirror.

Observed symptoms on 2026-05-08:

- `origin` URL was lost after every `filter-repo --execute` and re-added by
  hand at least four times.
- Two parallel runs mutated the same `HEAD` with inconsistent SHA outputs,
  with no warning that a prior rewrite had already succeeded.
- No machine-readable artifact recorded pre/post SHAs and the rule-set
  fingerprint, so post-incident reconciliation depended on shell history.
- The operator had to bypass other guards
  (see `hooks/_lib/push-collision-check.sh`) on the next push because the
  rewritten history collided with origin in expected ways.

## Decision

Ship a wrapper, `scripts/cos-filter-repo-wrap.sh`, that all governed
history-rewrite paths must use. The Python entry point in
`lib/history_sanitization.py:execute()` invokes the wrapper instead of
calling `git filter-repo` directly.

Wrapper responsibilities:

1. **Remote preservation.** Before invoking `filter-repo`, snapshot every
   configured remote (URL plus push URL) into a temporary file. After
   `filter-repo` completes, restore each remote. Log any remote that was
   present before but is missing after, and re-add it.
2. **Idempotency guard.** Compute a deterministic SHA-256 of (a) the rules
   file contents passed to `filter-repo`, (b) the canonical environment
   subset that affects rewrite output, and (c) the current `HEAD` SHA. If
   `.cognitive-os/runtime/last-filter-repo.json` records the same triple,
   refuse to re-run unless `--force-re-run` is passed.
3. **Recovery artifact.** Always emit `.cognitive-os/runtime/recovery.json`
   with `pre_head`, `post_head`, `backup_mirror_path`, `rules_hash`, and
   `timestamp`. The backup mirror is created via `git clone --mirror` to a
   timestamped path before any rewrite begins.
4. **Audit trail.** Append an entry to `stash-ops.jsonl` (per ADR-117 naming
   conventions) describing the rewrite, the rule-set hash, and the resulting
   SHA delta.

`lib/history_sanitization.py:execute()` delegates entirely to the wrapper
and surfaces the recovery artifact path to the caller.

## Alternatives rejected

- **Re-add origin after every run via a post-hook** — rejected because it
  fixes only one of the two failure modes. The non-idempotency problem
  remains and is the more destructive of the two.
- **Refuse to ever re-run filter-repo on a repo that has been rewritten** —
  rejected because legitimate re-runs exist: a rule-set bug discovered after
  the first pass, a forgotten path, a follow-up mailmap change. The correct
  guard is "refuse to re-run with the same hash on the same HEAD," not
  "refuse all re-runs."
- **Patch upstream git-filter-repo to preserve remotes** — rejected because
  upstream's behavior is intentional and exists for a different operator
  model. Carrying a patch fork is more risk than a thin wrapper.
- **Document the manual remote-restore step in a runbook** — rejected
  because manual restore was the failing baseline of this session.

## Consequences

### Positive

- `origin` survives every rewrite without operator intervention.
- A second invocation with the same rule-set against the same `HEAD` is a
  no-op with a clear message, instead of a silent re-mutation.
- `recovery.json` and the timestamped backup mirror make rollback a
  documented operation rather than a forensic exercise.
- `stash-ops.jsonl` correlation with rewrites enables auditable history
  hygiene.

### Negative

- Backup mirrors consume disk; they must be reaped on a TTL.
- The idempotency guard introduces a new file under
  `.cognitive-os/runtime/` that must be cleaned on session end.
- A `--force-re-run` flag exists and could be misused; it must be logged.

## Acceptance criteria

1. `scripts/cos-filter-repo-wrap.sh` exists and is the only call site for
   `git filter-repo --execute` within `lib/history_sanitization.py`.
2. Running the wrapper twice with identical inputs against the same `HEAD`
   produces a refusal on the second call (without `--force-re-run`).
3. After any successful run, every previously configured remote is present
   with the original URL.
4. `.cognitive-os/runtime/recovery.json` is written with all required
   fields, and a timestamped mirror exists at the path it cites.
5. `tests/behavior/test_filter_repo_wrap.py` exercises remote preservation,
   idempotency refusal, force-re-run override, and recovery-artifact shape.

## Verification

```bash
python3 -m pytest tests/behavior/test_filter_repo_wrap.py -q
bash scripts/cos-filter-repo-wrap.sh --dry-run --rules /tmp/empty-rules.txt
test -x scripts/cos-filter-repo-wrap.sh
```
