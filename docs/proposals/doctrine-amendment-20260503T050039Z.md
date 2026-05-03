---
status: proposed
kind: doctrine-amendment-proposal
generated_at: 2026-05-03T05:00:39+00:00
runtime_effect: none
---

# Doctrine Amendment Proposal

This file is generated evidence for human review. It does not change runtime behavior.

## Review direct-main bypasses as emergency debt

- **Proposal ID**: `direct-main-bypass-review-cadence`
- **Trigger**: direct-main bypass audit has recorded bypass events
- **Evidence**: `{"direct_main_bypass_count": 9}`

### Proposed rule

Direct-main bypasses remain allowed for maintainer recovery, but each bypass must carry a reason and the aggregate should be reviewed before release or after repeated use.

### Non-goals

- ban emergency bypasses
- normalize direct pushes as the standard landing path

### Required follow-up

- Keep `.cognitive-os/metrics/direct-main-bypass.jsonl` append-only.
- Escalate if bypass frequency increases without a matching policy update.

## Prefer semantic matching over substring matching in gates

- **Proposal ID**: `semantic-match-before-string-match`
- **Trigger**: false-positive ledger has scoped events
- **Evidence**: `{"false_positive_events": 24, "top_hooks": [{"count": 24, "hook": "git-op-blocks"}]}`

### Proposed rule

Any blocking gate that inspects commands, claims, or filenames should parse scoped fields first. Substring matching is fallback only and must be covered by false-positive regression tests.

### Non-goals

- remove conservative safety gates
- silence historical false positives without classification

### Required follow-up

- Add regression tests for every false-positive class before tightening gates.
- Keep the false-positive ledger scoped to explicit event fields.

## Warnings need expiry, owner, or explicit deferral

- **Proposal ID**: `warnings-need-expiry-or-owner`
- **Trigger**: demotion loop has two demotions but no ROI-signed demotion
- **Evidence**: `{"demotion_count": 2, "findings": [{"id": "roi-signed-demotion-missing", "message": "No demotion records governance ROI as the primary signing signal; ROI dashboard remains an instrument, not a decision knife.", "severity": "warn"}], "roi_signed_demotion_count": 0}`

### Proposed rule

A governance warning must have an owner, expiry, or explicit deferral state. Permanent warnings are not invariants; they are ambient noise.

### Non-goals

- fabricate ROI evidence
- extend warning budgets silently

### Required follow-up

- Let the existing demotion-loop deadline bite if no ROI-signed demotion appears.
- Treat deadline extension without evidence as doctrine regression.

## Maintainer-cache allowlists are not transferable doctrine

- **Proposal ID**: `maintainer-cache-is-not-transferable-doctrine`
- **Trigger**: silent-failure audit reports Shape-B transferability debt
- **Evidence**: `{"file_count": 201, "occurrence_count": 1580, "warn_count": 65}`

### Proposed rule

Allowlist entries based on maintainer cache are valid only for Shape A. Shape B adoption requires owner/review evidence or reclassification.

### Non-goals

- pretend maintainer tier is externally onboardable today
- delete allowlisted occurrences without review

### Required follow-up

- Keep ADR-132 as the Shape-B trigger boundary.
- Reclassify entries only when evidence is externalizable.

## Self-improvement remains propose-only until promotion evidence exists

- **Proposal ID**: `self-improvement-is-propose-only`
- **Trigger**: self-improvement loop generated proposals
- **Evidence**: `{"policy": {"auto_merge": false, "auto_promote_core_or_team": false, "dashboard_required": false, "human_approval_required": true}, "proposal_count": 7}`

### Proposed rule

Self-improvement may generate proposals and validation plans, but it may not auto-merge, auto-promote core/team, or write live runtime surfaces directly.

### Non-goals

- claim autonomous self-building without promotion evidence
- use proposal volume as a reason to expand default-visible surface

### Required follow-up

- Keep `cos-self-improvement-discipline-gate` in quick CI.
- Require harvester-signed sandbox→advisory evidence before signing the self-building claim.
