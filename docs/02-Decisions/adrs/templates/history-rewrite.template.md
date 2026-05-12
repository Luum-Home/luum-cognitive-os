---
adr: NNN
title: <Short description of the history rewrite>
status: proposed
date: YYYY-MM-DD
supersedes: []
superseded_by: null
extends: [ADR-218, ADR-242, ADR-243, ADR-246, ADR-269]
implementation_files:
  - manifests/history-rewrite-ledger.yaml
tier: maintainer
tags: [history-rewrite, governance]
related_adrs:
  - ADR-218 (history sanitization toolchain)
  - ADR-242 (filter-repo wrapper preserves remote)
  - ADR-243 (post-rewrite push-collision exception)
  - ADR-246 (release transaction freeze)
  - ADR-269 (mandatory ADR reference for history rewrites)
---

# ADR-NNN — <Title>

## Status

Proposed YYYY-MM-DD. Promote to **Accepted** before running the rewrite —
ADR-269 requires `--adr-ref` to name an Accepted ADR.

## Context

<!--
Why is this history rewrite needed? Examples:
- Sensitive content leaked into a historical commit (secret, PII).
- License-incompatible upstream content needs removal before public release.
- External-pattern attribution surface reduction (cf. ADR-268).
- IP discovery defensive cleanup.

Cite postmortems, audits, or upstream issues. Do not name the content
verbatim — that defeats the purpose of the rewrite. Use references
(category, blob hashes, commit ranges).
-->

## Decision

<!--
What concretely will change in history?

- Scope: blob-content | commit-messages-only | metadata | all
- Tool: git-filter-repo via cos-history-sanitization --execute
- Manifest: manifests/history-sanitization.yaml rules touched
- Operator opt-in env: COS_HISTORY_SANITIZE_COMMIT_MESSAGES=1 / METADATA=1 (as needed)
- Backup: .cognitive-os/recovery/pre-history-sanitization-<ts>.bundle (auto)
- Ledger: manifests/history-rewrite-ledger.yaml entry (auto-appended)
-->

## Rationale

<!--
Why this approach over alternatives?

- Why a full filter-repo rewrite vs. a single commit revert.
- Why blob-content scope vs. metadata.
- Why now vs. parking until next release boundary.

Explicitly note interaction with ADR-246 release freeze if the rewrite
will happen during an active release transaction.
-->

## Consequences

### Positive

- <Auditor-visible benefit 1>
- <Auditor-visible benefit 2>

### Negative

- All commit SHAs after `<base-sha>` will change. Tags reattached on
  post-rewrite equivalents.
- Force-push to origin required (ADR-243 push-collision exception applies).
- Any open branches / forks need rebase or fresh clone.

### Risks not mitigated

- <Listing of residual risks>

## Implementation plan

1. Update `manifests/history-sanitization.yaml` if rule changes are needed.
2. Run dry-run: `python3 scripts/cos-history-sanitization --dry-run --json > /tmp/dry-run.json`
3. Review dry-run: zero `block`-severity findings, expected hit counts.
4. Promote this ADR to **Accepted** in the same commit set as the rewrite.
5. Execute: `python3 scripts/cos-history-sanitization --execute --adr-ref ADR-NNN --reason "..."`
6. Verify ledger entry appended at `manifests/history-rewrite-ledger.yaml`.
7. Re-tag versions, write disclosure doc, force-push (separate operator steps).

## Alternatives considered

- <Alternative 1 and why rejected>
- <Alternative 2 and why rejected>

## Open questions (UNSURE)

- <Question 1>

## References

- ADR-218 — History sanitization toolchain
- ADR-242 — git-filter-repo wrapper preserves remote
- ADR-243 — Post-rewrite push-collision exception
- ADR-246 — Release transaction freeze for destructive ops
- ADR-269 — Mandatory ADR reference for history rewrites
