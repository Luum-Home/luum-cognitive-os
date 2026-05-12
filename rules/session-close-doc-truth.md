<!-- SCOPE: both -->
<!-- TIER: 1 -->
# Session-Close Documentation-Truth Discipline (ADR-277 + ADR-275)

> **Status**: active, 2026-05-12.
> **Trigger**: at every session-close (`/session-wrapup`) AND at every
> `cos-adr-close` invocation AND when an agent discovers any documentation
> contradiction during work.

## The rule (one sentence)

**Every documentation contradiction discovered during a session MUST
terminate in ONE of two outcomes before the session closes:**

1. **Pointwise fix + automated claim** — fix the prose AND add (or extend)
   a claim in `manifests/documentation-truth-claims.yaml` so the same
   class of contradiction cannot silently return.
2. **Explicit debt entry** — add the contradiction to the pending/remaining
   ledger (`docs/reports/pending-truth-latest.json` via a `follow-up` or
   `audit-finding` item) with `next_action` describing the fix path.

**A discovered contradiction cannot remain as a human comment, slack
message, or session-summary bullet alone.** That regresses to the
pre-ADR-273 anti-pattern.

## What counts as a "documentation contradiction"

Any of:
- Stale phrase describing a now-implemented feature as missing/pending
  (e.g., "no atomic close primitive exists" — when ADR-275 shipped one)
- Outdated harness/coverage claim (e.g., "Claude/Codex-only" — when
  structural projection already handles 4 harnesses)
- Generated truth block out of sync with its source report
- ADR `implementation_status: implemented` with no implementation_files
  pointing to actual code
- "Future work" / "known gap" / "falta documentar" phrases referring to
  something that already exists in `scripts/`, `hooks/`, or `manifests/`

## Classification flowchart (mandatory before closing the contradiction)

```
Discovered contradiction
        │
        ▼
Is the implementation already shipped?
        │
   ┌────┴────┐
   YES        NO
   │          │
   ▼          ▼
Doc is stale.       Real debt.
                     │
1. Fix the prose.    ▼
2. ADD a claim to    Add a `follow-up` or `audit-finding`
   manifests/         item to docs/reports/pending-truth-
   documentation-     latest.json with concrete next_action.
   truth-claims.yaml
   - required_phrases
   - forbidden_phrases
   - source_reports
3. Re-run
   documentation_truth_audit.py
   --update-generated
4. Verify pass.
```

## What gets added to documentation-truth (the criterion)

ONLY these classes go in `manifests/documentation-truth-claims.yaml`:

- Coverage claims (how many X exist now)
- Harness-support claims (which harnesses are projected)
- "Implemented vs gap" claims (this exists; this is pending)
- Authority/write-effects/security claims
- Claims about generated reports (their freshness, content)
- ADR `implementation_status` claims (implemented/partial)
- Lists derived from manifests or ledgers (must round-trip)

Everything else (free prose explaining concepts, opinions, prose
descriptions of behavior) stays out — `documentation-truth` is for
**volatile facts**, not for all docs.

## Session-close checklist (operational integration)

The `/session-wrapup` skill (`skills/session-wrapup/SKILL.md`) Step 2b
runs this check. Manually:

```bash
# 1. Run documentation-truth audit
python3 scripts/documentation_truth_audit.py --project-dir . --update-generated --fail-on-block

# 2. If audit reports a NEW contradiction (not pre-existing), classify:
#    - shipped already? → add claim entry to manifests/documentation-truth-claims.yaml
#    - real debt?       → add ledger item via cos-pending-truth-aggregator inputs

# 3. Re-run audit to confirm pass
python3 scripts/documentation_truth_audit.py --project-dir . --fail-on-block
```

## ADR closure integration

When invoking `scripts/cos-adr-close`, if the ADR has prose that
describes volatile coverage or harness facts:

1. Check if a `documentation-truth` claim covers that prose.
2. If not, ADD one in the same commit as the ADR closure.
3. The ADR closure commit MUST include the claim entry when applicable
   (or explicitly note "no volatile claims" in the commit message).

## ACC refresh integration

The ACC adapter `documentation_truth` already wires audit findings into
capability classification (ADR-031). At session close, the wrapup
explicitly checks this adapter's output and notes any stale
capability classification as a follow-up.

## Why this rule exists

Without it, contradictions are caught reactively (in adversarial review,
in cold-reader audits). With it, contradictions are caught at the moment
they appear and never accumulate. This is the **same** discipline that
ADR-273/274/275 imposed on tasks and decisions — applied to prose.

The rule is enforced by:
- `scripts/documentation_truth_audit.py --fail-on-block` (CI gate)
- `skills/session-wrapup/SKILL.md` Step 2b (per-session)
- ADR-277 (canonical contract)
- The control-plane `documentation_truth` audit (hourly)
