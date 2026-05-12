---
title: "Sprut Agent Kit Annex F — Compliance & Clean-Room Protocol"
date: 2026-05-11
annex: F
parent: null  # backfill — predates annex doctrine
scope: research-only
license_classification: "MIT — claimed in upstream README (AlekseiUL/sprut-agent-kit); LICENSE file returned 404; copyright holder unverified; treat as provisionally safe pending legal confirmation"
reviewed-by-legal: "BLOCKED — upstream ambiguous, copyright holder unverified, attribution absent from source file"
---

# Annex F — Compliance & Clean-Room Protocol for Sprut Agent Kit

## 1. License posture

**Claimed license in COS source**: None — `packages/verification-audit/lib/research_scoring.py`
contains only the phrase "Adapted from the Sprut Agent Kit last30days scoring pattern."
No license, no upstream URL, no commit hash, no copyright line are recorded.

**Upstream search results** (3 web fetches consumed):

1. GitHub search for "sprut agent kit" → found 3 repositories:
   - `AlekseiUL/sprut-agent-kit` (61 stars, Python, "Ready-to-use AI agent with soul,
     memory, and 23 skills for ClaudeClaw")
   - `sananrasool/sprut-agent-kit` (0 stars — likely fork)
   - `sundukov1max-lang/sprut-agent-kit` (0 stars — likely fork)

2. Fetch of `AlekseiUL/sprut-agent-kit` main page → README states license: **MIT**.
   The description mentions "last30days" as a skill name ("Research trends from the last
   30 days"), which is consistent with the "last30days scoring pattern" reference in the
   COS source file.

3. Fetch of `AlekseiUL/sprut-agent-kit/blob/main/LICENSE` → **HTTP 404**. The LICENSE
   file either does not exist at that path or is not publicly accessible. The MIT claim
   from the README cannot be verified against a LICENSE file. Copyright holder name and
   year are unknown.

**Verdict**: Upstream is provisionally identified as `AlekseiUL/sprut-agent-kit`
(MIT claimed in README) but this is **not confirmed** due to:
- No LICENSE file found at standard path.
- No copyright holder or year recorded anywhere in COS or upstream README.
- The COS source file contains zero attribution (no URL, no commit, no license, no
  copyright) — this is the worst-case attribution profile.
- "Sprut Agent Kit" is a generic name; `AlekseiUL` may not be the original author.

## 2. What this corpus contains

One file adapted from upstream:

| File | Lines | Note |
|------|-------|------|
| `packages/verification-audit/lib/research_scoring.py` | lines 1–9 (header) + full file | Adaptation of "last30days scoring pattern"; pure Python, no external deps |

The comment at lines 5–6 reads verbatim:
> `Adapted from the Sprut Agent Kit last30days scoring pattern.`

No upstream URL, no commit hash, no copyright line, no license identifier are present.
This file has the **worst-case attribution** profile: a bare name reference with no
verifiable provenance.

## 3. Per-file disposition

| File | Origin claim | License claim | Upstream verified | Disposition |
|------|-------------|---------------|-------------------|-------------|
| `packages/verification-audit/lib/research_scoring.py` | "Sprut Agent Kit last30days scoring pattern" | None stated | PARTIAL — MIT in README, LICENSE file 404 | HOLD — cannot distribute; attribution absent; copyright holder unknown |

## 4. NOTICE preservation requirements

**For the NOTICE-file creator agent** — a NOTICE entry CANNOT be authored until the
following information is supplied:

```
Sprut Agent Kit — last30days scoring pattern
  Source file: packages/verification-audit/lib/research_scoring.py
  Ported from: [upstream repo URL — MISSING]
  Commit: [upstream commit hash — MISSING]
  License: [MIT if confirmed — UNVERIFIED]
  Copyright: [copyright holder and year — UNKNOWN]
  Modifications: Adapted scoring logic to Python; integrated with COS research pipeline.
```

**Do not add this NOTICE entry until all bracketed fields are resolved.**

If the clean-room rewrite path (§6 option B) is chosen, this NOTICE entry is omitted
entirely and the "Sprut Agent Kit" reference is removed from the source file.

## 5. Why this is backfill

This file was adapted before ADR-259 (supply-chain attribution gate) and ADR-267
(Annex F mandatory before vendoring). The adaptation predates the doctrine requiring
upstream URL + commit hash + license + copyright at time of port. Unlike the OpenHarness
port (which had complete inline attribution) and the Pi port (which at least named a
license), this adaptation has zero attribution beyond a bare project name. This is the
highest-risk compliance gap in the three backfill items.

## 6. Pending tasks for legal review

**Two remediation paths — operator must choose one within 30 days:**

### Option A — Surface and verify upstream (preferred if MIT is confirmed)
1. **Identify commit** (P0): Author of original adaptation must supply the exact upstream
   repo URL and commit/release from which the "last30days scoring pattern" was adapted.
   Candidate: `https://github.com/AlekseiUL/sprut-agent-kit`.
2. **Verify LICENSE file** (P0): Fetch the LICENSE file from the identified commit.
   If MIT is confirmed, extract verbatim copyright line and proceed to attribution.
3. **Update source file header** (P0): Add upstream URL, commit hash, license identifier,
   and copyright line to `research_scoring.py` per ADR-267 §2.3.
4. **Author NOTICE entry** (P1): Once §4 fields are filled, add the NOTICE entry.
5. **Re-evaluate this Annex F** (P1): Upgrade `reviewed-by-legal` from BLOCKED to `no`
   once attribution is complete.

### Option B — Clean-room rewrite (fallback if upstream unverifiable after 30 days)
1. **Remove all "Sprut" references** from `research_scoring.py` docstring.
2. **Rewrite scoring logic** from first principles (engagement-weighted scoring with
   recency decay is not a copyrightable algorithm; only the specific expression is).
3. **Author a new internal design note** citing the general technique (no upstream
   required for clean-room).
4. **Close this Annex F** as "resolved via clean-room rewrite" with a note in §7.

**If upstream IS found and license is NOT MIT (e.g. AGPL, SSPL, BSL, ELv2)**:
Trigger immediate license-policy violation response per `rules/license-policy.md`:
- Mark this Annex F `reviewed-by-legal: BLOCKED — license violation found`.
- Quarantine `research_scoring.py` from release artifacts immediately.
- Mandatory clean-room rewrite (Option B above).

## 7. reviewed-by-legal status

```
reviewed-by-legal: BLOCKED — upstream ambiguous, copyright holder unverified
Reason: Source file contains zero attribution beyond a bare project name.
        Upstream provisionally identified as AlekseiUL/sprut-agent-kit (MIT in README)
        but LICENSE file returned 404 and copyright holder is unknown.
        File must not appear in a release artifact until Option A or Option B (§6) is
        completed.
Risk level: HIGH — this is the highest-risk of the three backfill items.
Next action: Port author must surface upstream URL + commit within 30 days.
             If not surfaced: trigger Option B (clean-room rewrite).
Deadline: 2026-06-10
```
