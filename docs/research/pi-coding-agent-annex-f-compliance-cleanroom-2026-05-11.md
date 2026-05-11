---
title: "Pi coding-agent Annex F — Compliance & Clean-Room Protocol"
date: 2026-05-11
annex: F
parent: null  # backfill — predates annex doctrine
scope: research-only
license_classification: "UNVERIFIED — MIT claimed inline, upstream not identifiable; treat as unverified until legal confirms"
reviewed-by-legal: "no — BLOCKED pending upstream identification"
---

# Annex F — Compliance & Clean-Room Protocol for Pi coding-agent

## 1. License posture

**Claimed license**: MIT (stated inline in `lib/file_mutation_queue.py` docstring).

**Upstream identification**: Two web searches against GitHub (queries: "pi coding agent
file-mutation-queue", "pi-coding-agent OR 'pi coding agent' file-mutation-queue") returned
**zero matching repositories**. The project name "Pi coding-agent" is ambiguous and could
refer to multiple unrelated projects. A third code-search attempt was blocked by GitHub's
authentication wall for unauthenticated code search.

**Verdict**: Upstream **not identifiable** with confidence in 2 fetch attempts (budget limit).
The MIT claim cannot be verified against an upstream LICENSE file. No copyright holder
name, repo URL, or commit hash is recorded in the ported file.

**Action required before legal sign-off**: The author of the original port must supply:
1. The canonical upstream repository URL (e.g. `https://github.com/<org>/pi-coding-agent`).
2. The exact copyright line from the upstream LICENSE file.
3. The commit hash or release tag from which `file-mutation-queue.ts` was ported.

Until those are supplied this compliance record remains **BLOCKED**.

## 2. What this corpus contains

One file ported into COS runtime:

| File | Lines | Note |
|------|-------|------|
| `lib/file_mutation_queue.py` | lines 1–20+ | Full port with Python/threading adaptation |

The comment at line 8 reads verbatim:
> `Ported from: Pi coding-agent file-mutation-queue.ts (MIT license)`
> `Adapted to Python using threading.Lock per resolved path.`

No upstream URL, no copyright line, no commit hash is recorded in the source file.

## 3. Per-file disposition

| File | Origin claim | License claim | Upstream verified | Disposition |
|------|-------------|---------------|-------------------|-------------|
| `lib/file_mutation_queue.py` | Pi coding-agent `file-mutation-queue.ts` | MIT (inline only) | NO — upstream not found | HOLD — cannot distribute until upstream confirmed |

## 4. NOTICE preservation requirements

**For the NOTICE-file creator agent** — once upstream is confirmed, add the following
entry to `NOTICE` (fill bracketed fields when upstream is identified):

```
Pi coding-agent — file-mutation-queue
  Source file: lib/file_mutation_queue.py
  Ported from: [upstream repo URL]/file-mutation-queue.ts
  Commit: [upstream commit hash]
  License: MIT
  Copyright: [upstream copyright holder and year]
  Modifications: Adapted from TypeScript to Python; threading.Lock replaces
                 JavaScript promise-queue; symlink-aware path resolution added.
```

**Do not add this NOTICE entry until upstream URL and copyright line are confirmed.**

## 5. Why this is backfill

This file was ported before ADR-259 (supply-chain attribution gate) and ADR-267
(Annex F mandatory before vendoring). The port predates the doctrine that requires
upstream URL + commit hash to be recorded at time of port. This annex is retroactively
created to surface the gap and block distribution until the gap is closed.

## 6. Pending tasks for legal review

1. **Upstream identification** (P0): Author of original port must supply repo URL,
   copyright holder, and commit hash. Without this, the MIT claim is unsubstantiated.
2. **Copyright line capture** (P0): Once URL is known, fetch `LICENSE` file and extract
   verbatim copyright line for NOTICE entry.
3. **Alternative: clean-room rewrite** (P1 fallback): If upstream cannot be identified
   within 30 days, recommend replacing `lib/file_mutation_queue.py` with a clean-room
   implementation (the algorithm — per-file mutex serialization — is not copyrightable;
   only the specific expression is). Remove all "Pi coding-agent" references.
4. **Source-file header update** (P2): Once upstream is confirmed, update the docstring
   in `lib/file_mutation_queue.py` to include the upstream URL and commit hash per
   ADR-267 §2.3.

## 7. reviewed-by-legal status

```
reviewed-by-legal: BLOCKED — upstream unverifiable
Reason: No matching repository found for "Pi coding-agent" on GitHub.
        MIT claim is inline-only with no verifiable upstream URL or copyright holder.
        File must not be redistributed in a release artifact until this is resolved.
Next action: Port author must surface upstream URL within 30 days or trigger clean-room rewrite.
```
