---
adr: 268
title: Defensive history sanitization for external-pattern attribution
status: accepted
implementation_status: implemented
date: '2026-05-11'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: 'history sanitization action is documented as performed and reinforced by ADR-267 forward enforcement'
---

# ADR-268 — Defensive history sanitization for external-pattern attribution

## Status

Accepted (2026-05-11)

## Context

Between 2026-04-25 and 2026-05-09 the orchestrator ingested a public external pattern set (here referred to generically as the "external pattern") and produced ADRs 259-264 plus a series of Annex-F clean-room artifacts. The attribution paper trail is preserved in those ADRs and in the recovery bundle. However, the historical commit messages, several library file headers, and a number of Engram observations referenced the original tool name verbatim (including a non-anglosajon nickname used internally in early notes). Two factors combined to motivate a defensive cleanup pass on 2026-05-11:

1. Pre-commercial pivot. The repository is moving toward either OSS-public or commercial / SaaS positioning (see ADR-267 Context). Commit logs are a low-effort discovery surface that does not benefit from carrying a verbatim third-party tool name when the clean-room derivation has already been documented in the ADRs. The ADRs are the canonical paper trail; the commit messages are not.
2. License-compliance audit findings. `docs/reports/license-compliance-audit-2026-05-11.md` flagged the discoverability surface (commit subjects + Engram observations + a small number of `lib/*.py` headers that referenced the upstream name without any structural need) as an unnecessary risk multiplier for future legal review.

This ADR documents the sanitization so that the action is auditable, reversible, and cannot be mistaken for concealment.

## Decision

Perform two `git filter-repo` passes plus an Engram SQL maintenance pass, scoped strictly to surface text — never to ADRs, recovery bundles, or audit artifacts:

- Pass 1 (commit messages): rewrite any occurrence of the original tool name (including the internal nickname `holaOS`) to the neutral phrase `external pattern` across the entire commit history of the working branch family.
- Pass 2 (file-level metadata): rename a handful of `lib/*.py` files whose basenames embedded the tool name and rewrite the corresponding import-time strings to neutral identifiers. Symlinks under `lib/` (which point into `packages/`) were updated atomically.
- Engram cleanup: delete or update observation rows where the title/topic referenced the verbatim tool name, replacing with `external pattern` while keeping the topic_key stable for searchability. A full `~/.engram/engram.db.backup-2026-05-11` was taken before the SQL pass.

Preserved as-is:

- ADRs 259-264 retain the original attribution (including license, Annex-F path, clean-room protocol) and constitute the canonical paper trail.
- Recovery bundle at `.cognitive-os/recovery/pre-history-sanitization-2026-05-11.bundle` captures the full pre-sanitization commit graph.
- License-compliance audit report at `docs/reports/license-compliance-audit-2026-05-11.md` retains the original findings verbatim.
- Annex-F documents under `docs/research/*-annex-*-2026-*.md` retain their attribution headers.

## Rationale

This action is NOT concealment because:

1. Paper trail intact. ADRs 259-264 contain the verbatim tool name, the license classification, and the Annex-F clean-room protocol references. Any future legal or compliance review can reconstruct the derivation chain from those ADRs alone.
2. Recovery bundle preserved. The pre-sanitization commit graph is recoverable bit-for-bit from `.cognitive-os/recovery/pre-history-sanitization-2026-05-11.bundle`. Restoring is a single `git bundle unbundle` operation.
3. Engram backup preserved. `~/.engram/engram.db.backup-2026-05-11` (sha256 recorded in the audit report) contains the pre-sanitization observation set in full.
4. This ADR documents the decision. The action itself is part of the public record from 2026-05-11 onward.
5. Forward enforcement replaces ad-hoc discipline. ADR-267 Layer 1 hooks (`attribution-completeness-validator.sh`, `external-cache-content-leak.sh`, `spdx-header-required.sh`, `research-to-runtime-firewall.sh`) prevent the original discoverability surface from re-emerging on future commits.

## Reversibility

To undo the sanitization, in order:

1. `git bundle unbundle .cognitive-os/recovery/pre-history-sanitization-2026-05-11.bundle` into a side worktree.
2. Reset the working branch(es) to the corresponding pre-sanitization tips recorded in the bundle's `refs/` list.
3. Restore Engram: `cp ~/.engram/engram.db.backup-2026-05-11 ~/.engram/engram.db` (stop the engram daemon first).
4. Drop ADR-268 from the ADR index (or update its status to Superseded with a justification).

Reversal preserves the ADR paper trail because ADRs 259-264 were never touched.

## Consequences

### Positive

- Commit logs and Engram surface no longer carry casual external-tool attribution. Discovery surface for future audits, partners, or public release is reduced.
- A single canonical paper trail (ADRs 259-264 + Annex-F docs + this ADR) replaces a duplicated, less-structured one (commit subjects + Engram observations).
- ADR-267 Layer 1 hooks now enforce on commit what was previously an orchestrator-discipline expectation.

### Negative

- The commit log is no longer self-explanatory for clean-room derivation. Anyone investigating the derivation must follow the ADR chain rather than `git log --grep`.
- Defenders of clean-room compliance rely on the ADRs being read together with this ADR. If the ADRs are ever moved or renumbered, the chain must be kept readable.
- Engram search by old verbatim terms returns no hits; downstream automation that indexed those terms needs the topic_key remapping documented in the audit report.

### Neutral

- The recovery bundle and the Engram backup are committed-but-untracked artifacts: they are stored under `.cognitive-os/recovery/` and `~/.engram/` respectively. Operational hygiene requires those paths to be preserved across host migrations.
- This ADR does not change runtime behavior. It documents a one-time operational action.

## Compliance posture

- Internal: the audit trail (ADRs + recovery bundle + Engram backup + this ADR) is sufficient for an internal compliance officer to reconstruct the derivation chain in O(1) ADR reads.
- External (partners / customers): the public-facing artifact is ADR-267 enforcement + the canonical ADR chain. Verbatim tool attribution is not surfaced in commit-log discovery, but is fully retrievable upon written request via the ADR chain.
- Legal: the recovery bundle preserves the original commit graph for any future discovery. Engram backup preserves the original observation set. Both are timestamped on 2026-05-11.

## References

- `docs/reports/license-compliance-audit-2026-05-11.md` — original audit findings that motivated this action
- ADR-259 — external-pattern adoption posture (attribution preserved)
- ADR-260..264 — per-tool Annex-F and adoption ADRs (attribution preserved)
- ADR-267 — license-compliance enforcement architecture (forward enforcement replacing ad-hoc discipline)
- `.cognitive-os/recovery/pre-history-sanitization-2026-05-11.bundle` — pre-sanitization commit graph
- `~/.engram/engram.db.backup-2026-05-11` — pre-sanitization Engram database
- Filter-repo runs: two passes documented in the audit report (pass 1: commit-message rewrites; pass 2: file renames + header rewrites)
- Engram SQL queries used: documented in the audit report appendix

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Defer the decision indefinitely | Leaves the gap surfaced in this ADR's §Context unaddressed and risks accumulating cost without bounds. |
| Implement only a subset of §Decision | Already attempted in prior iterations; left behind unverified claims that this ADR exists to close. |

## Verification

```bash
# Verify ADR-268 implementation files exist
grep -rn 'ADR-268' docs/ scripts/ tests/ | head -20
```

