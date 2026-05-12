---
adr: 281
title: ADR Implementation Reality Audit
status: accepted
implementation_status: implemented
classification_basis: 'Audit script + control-plane wiring + tests shipped; documents the gap discovered 2026-05-12 and closes it permanently.'
date: 2026-05-12
supersedes: []
superseded_by: null
extends: [ADR-105, ADR-244, ADR-273, ADR-274, ADR-275, ADR-277]
implementation_files:
  - scripts/cos-adr-implementation-audit.py
  - manifests/adr-implementation-runtime-allowlist.yaml
  - tests/red_team/portability/test_cos-adr-implementation-audit.py
tier: maintainer
tags: [adr-contract, implementation-claims, overclaim-prevention, bilateral-verification, postmortem-2026-05-12]
---
# ADR-281: ADR Implementation Reality Audit

## Status

Accepted — Phase 1 shipped 2026-05-12 (audit + allowlist + tests + control-plane wiring).

<!-- SCOPE: OS -->

**Date**: 2026-05-12

## Context

The 2026-05-12 adversarial review on ADR-280 (Product Question-to-Evidence
Primitive) surfaced a fourth class of overclaim that the existing audit
constellation does not catch:

> An ADR can declare `implementation_status: implemented` and list
> `implementation_files: [a, b, c]` while one or more of those paths do
> not exist on disk. Nothing today blocks or warns at write-time.

Empirical evidence from the proper audit run on 2026-05-12:

- **123 ADRs** declare `implementation_status: implemented`.
- **346 implementation_files entries** in total across all of them.
- **1 missing-on-disk entry** flagged (ADR-185 references
  `.cognitive-os/coordination/agent-messages.jsonl`, a runtime artifact
  legitimately gitignored).
- After adding `.cognitive-os/coordination/*` to the runtime allowlist:
  **0 overclaims**.

Note on the discovery process: an initial one-shot manual scan
reported "6 overclaims" — itself an overclaim caused by a buggy regex
that did not strip inline `# comment` text from `implementation_files`
entries (e.g. `- lib/foo.py    # description` parsed as the literal
path `lib/foo.py    # description`). The properly-implemented audit
(this ADR's script) strips comments and applies the allowlist; it found
the real magnitude. This is itself a demonstration of why the audit
must be deterministic code rather than ad-hoc shell — a one-shot
manual scan was wrong about its own count.

The discovery was triggered by ADR-280 (Product Question-to-Evidence
Primitive) initially declaring `implementation_status: implemented`
with 7 `implementation_files`, of which 2 (`tests/unit/test_product_answer.py`
+ `tests/behavior/test_product_answer_cli.py`) did not exist at the
moment of the audit (the parallel session created them shortly after).
That single real overclaim motivated the systematic audit, which then
revealed the audit was needed for future regression prevention even
though current real-overclaim count is 0.

### Why existing audits do not catch this

| Audit (ADR) | What it checks | Misses this overclaim? |
|---|---|---|
| `adr-section-validator` (ADR-067) | Required sections present | YES — purely structural |
| `cos-operational-guide-audit` (ADR-274) | §Operational Guide presence + ≥3 sub-sections | YES — section presence, not claim reality |
| `cos-pending-truth-aggregator` (ADR-273) | Open task items | YES — operates on plan checkboxes + ADR slices, not implementation_files |
| `cos-closure-trust-signal` (ADR-275 §10 P3) | Closure-trail vs verified-done | YES — task closures, not ADR claims |
| `documentation_truth_audit` (ADR-277) | Required/forbidden phrases per declared claim | NO — would catch IF a claim were declared for this. None is. |
| `cos-primitive-authority-audit` (ADR-276) | Write-effects boundary | YES — orthogonal concern |
| `cos-adr-partial-audit` (parallel session) | Lifecycle metadata on partials | YES — looks at partials, not implementeds |
| `cos-doc-cross-reference-audit` (ADR-275) | Primitive token presence across surfaces | YES — not a disk-existence check |

The class of "claim is documented + claim is internally consistent +
claim is contradicted by disk" was uncovered.

## Decision

Add a permanent audit that cross-validates ADR implementation claims
against on-disk reality.

### 1. Contract

An ADR with `implementation_status: implemented` MUST satisfy:

- Every entry in `implementation_files:` either (a) exists on disk, or
  (b) is explicitly listed in
  `manifests/adr-implementation-runtime-allowlist.yaml` with rationale.

If the implementation is partial or only some files exist, the ADR
MUST use `implementation_status: partial` (with `partial_remaining` per
ADR-275 §10 / STATUS-TAXONOMY).

Setting `implementation_status: implemented` while listing missing
files is an **overclaim** — the same anti-pattern that ADR-105 prohibits
for plan checkboxes.

### 2. Audit (Phase 1, this ADR)

`scripts/cos-adr-implementation-audit.py`:

- Scans `docs/adrs/ADR-*.md`
- For each with `implementation_status: implemented`:
  - Parses `implementation_files:`
  - Cross-checks each path against repository disk + the runtime
    allowlist
- Emits findings in the ADR-248 control-plane runner shape:
  - severity: `warn` per missing file (operator must triage)
  - code: `adr-implementation-file-missing`
  - stable_id: `adr-281/missing/<ADR-NNN>/<rel-path>`

Schema: `adr-implementation-audit/v1`.

### 3. Runtime allowlist

`manifests/adr-implementation-runtime-allowlist.yaml` declares paths
that legitimately do not exist in the repository (runtime artifacts,
gitignored generated files). Required fields per entry:
`pattern`, `rationale`, `owner`.

Default seed:
- `.cognitive-os/metrics/*.jsonl` — runtime metrics streams
- `.cognitive-os/audit/*.jsonl` — runtime audit trails (e.g. closure-trail)
- `.cognitive-os/state/*.json` — runtime state
- `.cognitive-os/runtime/*` — runtime caches and locks

### 4. Wiring

- Registered in `manifests/control-plane-audits.yaml` under
  `adr-implementation-coverage` in `hourly` + `pre-public` lanes.
- documentation-truth claim added to forbid stale phrases like "ADR
  status checking is purely structural" (future-proofing).
- doc-cross-reference contract added so the primitive cannot ship
  without surfacing in operations MOC + this ADR.

### 5. Backfill

The first audit run with proper comment-stripping + the seeded
allowlist produces **0 overclaims**. Backfill is therefore not needed
at audit-creation time. Future overclaims would be tracked via the
same control-plane remediation queue:

a. **Create the missing files** (real implementation), or
b. **Change `implementation_status: implemented` → `partial`** with
   `partial_remaining` documenting the gap (per STATUS-TAXONOMY), or
c. **Add the path to the allowlist** if it is a legitimate runtime
   artifact (with rationale + owner).

### 6. Why this is now mandatory

This is the **fourth iteration** of the same anti-pattern:

| Iteration | Anti-pattern | Closing ADR |
|---|---|---|
| 1 (2026-05-12 AM) | "operational model lives only in chat" | ADR-273 §Operational Guide retrofit |
| 2 (mid-day) | "single-instance §OG fix doesn't generalize" | ADR-274 §OG contract + audit |
| 3 (afternoon) | "audit visible but not projected; closure asymmetric" | ADR-275 projector + close primitive |
| **4 (2026-05-12 PM)** | **"ADR claims implemented + files missing on disk"** | **ADR-281 (this ADR)** |

Each iteration follows the pattern from ADR-275 §10: state proliferates
faster than verification discipline. The fix is always the same shape:
explicit contract + audit script + control-plane wiring + backfill.

## Operational Guide

### What changes for the operator

| Surface | Before ADR-281 | After ADR-281 |
|---|---|---|
| Writing a new ADR with `implementation_status: implemented` | Author claim accepted; no verification | Audit flags any missing `implementation_files`; resolved before merge or downgraded to partial |
| Reading an ADR cold | Trust the frontmatter claim | Cross-check via control-plane `adr-implementation-coverage` audit |
| Runtime artifacts in implementation_files | Audited as missing | Explicit allowlist with rationale |
| Backfill list of overclaims | Invisible | Visible via remediation queue |

### Daily operational pattern

1. Author drafts ADR, lists `implementation_files`.
2. If status is `implemented`, all listed files MUST exist OR be in the
   allowlist.
3. Audit runs hourly via `cos-control-plane-audit --lane hourly`:
   ```bash
   python3 scripts/cos-adr-implementation-audit.py --strict
   ```
4. New findings appear in the remediation queue with stable_id
   `adr-281/missing/<ADR-NNN>/<rel-path>`.
5. Operator resolves each finding by either creating the file or
   downgrading the ADR status.

### Reading guide for cold readers

1. Run the audit to see current state:
   ```bash
   python3 scripts/cos-adr-implementation-audit.py | jq .summary
   ```
2. Read `manifests/adr-implementation-runtime-allowlist.yaml` for
   legitimate exemptions.
3. Read this ADR §Decision for the contract.
4. The 4-pattern table in §Context explains how this is the same
   anti-pattern that motivated ADR-273/274/275.

## Consequences

- **Overclaim is no longer invisible**: the system flags `implemented`
  ADRs whose implementation is partial-or-aspirational.
- **Allowlist is the safety valve**: runtime/gitignored files have a
  declared place; the bias is "list as allowlist OR fix the claim".
- **Backfill is small** (4 ADRs at audit time of writing) — closes
  cleanly in one sweep.
- **Future ADRs cannot regress** silently — control-plane hourly lane
  catches new overclaims within 1 hour.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Manual review on PRs | History shows manual review missed this for 6 days across 4 ADRs; audit-as-code is required. |
| Block at write-time (PreToolUse Edit on ADR-*.md) | False-positive cost: ADR may be drafted before files exist (legitimate "design then build" flow). Hourly audit catches it within ≤1h with operator-friendly remediation. |
| Strip `implementation_files` from the contract | Loses the cross-reference value entirely; the field is useful, just unverified. |
| Trust the author + LLM audit | The §OG backfill experiment proved LLM agents render docs from §Decision/§Context, not from disk reality. Deterministic disk-check is required. |

## Verification

```bash
# Audit (Phase 1)
python3 scripts/cos-adr-implementation-audit.py
# Expected: JSON with summary + findings array

# Strict mode (CI gate)
python3 scripts/cos-adr-implementation-audit.py --strict
# Exit 2 if any overclaim is present

# Portability proof
python3 -m pytest tests/red_team/portability/test_cos-adr-implementation-audit.py -q

# Control-plane integration
python3 scripts/cos-control-plane-audit --lane hourly | grep adr-implementation-coverage
```

## Follow-ups

- **Phase 2**: extend to other lifecycle states — e.g. `partial` ADRs
  whose `partial_remaining` lists files that DO exist (under-claim).
- **Phase 3**: cross-validate `implementation_files` against
  `manifests/primitive-lifecycle.yaml` so primitives registered there
  must also appear in at least one ADR's `implementation_files`.

## Related

- ADR-105 — Bilateral claim verification (this ADR is the ADR-frontmatter
  analogue of plan-checkbox bilateral verification)
- ADR-244 — Trust-report enforcement (overclaim is a LOW trust signal)
- ADR-273 — Pending truth ledger (same proliferation root cause)
- ADR-274 — §Operational Guide contract (same shape: contract + audit
  + backfill)
- ADR-275 — Closure & projection primitives (this audit feeds the
  same remediation queue)
- ADR-277 — Documentation truth control (a doc-truth claim could be
  added later to forbid stale phrases about ADR audits)
- 2026-05-12 adversarial review thread iteration #4 — surfaced this
  anti-pattern after iterations 1–3 closed §OG drift / projector gap /
  closure asymmetry.
