# Lifecycle Promotion Ladder — Gap Analysis

**Date**: 2026-05-05
**Status**: research-only; documents an operational gap, proposes ADR-177 as follow-up.
**Trigger**: Adopting OpenSpace's SkillStore schema (ADR-176) raised the question *"are our anti-auto-apply policies coherent? how does the SO actually evolve?"*. Investigation revealed that the lifecycle ladder is doctrinally complete and partially implemented, but the promotion mechanism is dormant.

---

## TL;DR

- COS has a real 5-state lifecycle ladder (sandbox / advisory / blocking / demoted / archived) per ADR-138, with 154 primitives classified.
- Auto-apply IS doctrinally allowed at the sandbox tier (where `auto-skill-generator.sh` writes). Rejecting OpenSpace's auto-apply remains coherent because OpenSpace bypasses the sandbox stage and overwrites production-grade `SKILL.md` directly.
- **The promotion mechanism is dormant.** Verified: 18 auto-generated skills exist; 0 have promoted from sandbox to advisory. `cos-doctrine-proposer` does not log; `self-improvement-loop.jsonl` is recently empty.
- This explains why `dogfood_score.skill_coverage = 24.07/100` — many skills are sandboxed but never enter the routing canon.
- **ADR-176 (SkillStore adoption) is the precondition for fixing this gap.** The 6-table SQLite schema provides exactly the use-frequency, judgment, and lineage data that a promotion mechanism needs.
- **ADR-177 candidate** (not yet drafted): activate the promotion ladder — operator-gated, propose-only, evidence-driven.

---

## The doctrine (what is documented and verified)

| State | Count (registry) | Auto-apply allowed? | Source |
|---|---|---|---|
| `sandbox` | 89 | ✅ Yes (lowest tier — where auto-skill-generator writes) | ADR-138, primitive-lifecycle.yaml |
| `advisory` | 27 | ❌ No — propose-only via discipline gate | ADR-134, ADR-135 |
| `blocking` | 36 | ❌ No — hook-enforced, requires explicit human gate | ADR-133, ADR-134 |
| `demoted` | 2 | ❌ Read-only | ADR-138 |

Documents that establish this doctrine:

- `docs/adrs/ADR-138-flow-contract-schema.md` — ladder formal contract.
- `docs/adrs/ADR-126-*.md`, `ADR-127-*.md`, `ADR-128-*.md` — origin of lifecycle metadata for hooks.
- `docs/adrs/ADR-133-*.md` — auto-skill-generation governance (sandbox-only auto-apply).
- `docs/adrs/ADR-134-*.md` — closed-loop self-improvement (propose-only at promotion).
- `docs/adrs/ADR-135-*.md` — self-evolving doctrine proposer (propose-only).
- `manifests/primitive-lifecycle.yaml` — 154 primitives classified.
- `manifests/agentic-primitive-registry.lock.yaml` — sha256-locked registry, lifecycle metadata per primitive.

---

## The intended evolution flow (per doctrine)

```
auto-skill-generator.sh fires (PostToolUse Agent, complex completions)
   ↓
Creates skill in .cognitive-os/skills/auto-generated/<name>/SKILL.md
   ↓ (lifecycle_state: sandbox, distribution: lab)
Sandbox auto-apply (no gate at this tier — doctrine permits)
   ↓
Skill accumulates evidence: invocations, success rate, agent judgments
   ↓
PROMOTE proposal → cos-doctrine-proposer (ADR-135) → propose-only artifact
   ↓
Operator reviews proposal → approves promotion to advisory tier
   ↓ (lifecycle_state: advisory, distribution still lab or escalated)
More evidence + ADR for the contract → blocking tier (hook-enforced)
   ↓
If drift / no usage / regression → demoted → archived
```

This flow is internally coherent: auto-apply is bounded to the lowest tier; every escalation requires evidence + human approval; rollback path exists at every tier.

---

## What is dormant (the gap)

Verified on 2026-05-05:

| Indicator | Verified value | Implication |
|---|---|---|
| Auto-generated skills on disk | 18 (`.cognitive-os/skills/auto-generated/`) | Generation works |
| Auto-generated skills with `lifecycle_state != sandbox` | **0** | Promotion never happens |
| `.cognitive-os/metrics/doctrine*.jsonl` | **does not exist** | doctrine-proposer not logging |
| `.cognitive-os/metrics/self-improvement-loop.jsonl` | recently empty | self-improvement-loop not active |
| `dogfood_score.skill_coverage` | 24.07 / 100 | Coherent with skills-stuck-at-sandbox state |

**Conclusion**: the system generates skills but does not mature them. The ladder is real in code; the climb is missing.

---

## Why rejecting OpenSpace's auto-apply remains correct

This gap analysis does NOT reverse the ADR-176 verdict to reject OpenSpace's auto-apply. The two issues are orthogonal:

| Comparison | OpenSpace `_apply_with_retry` | COS auto-skill-generator |
|---|---|---|
| Where does the write land? | Production-grade `SKILL.md` (overwrites existing skill that real agents invoke) | Sandbox tier under `.cognitive-os/skills/auto-generated/` (isolated, not in production routing) |
| Is there a tier above sandbox? | No — production is the only tier | Yes — advisory and blocking exist as separate, gated states |
| Is rollback automatic? | No backup; no rollback path | Git-tracked; sandbox isolation makes revert trivial |
| What happens if the LLM judge is wrong? | Compounds silently into next iteration | Bounded blast radius (sandbox tier only) |

OpenSpace skips the sandbox stage entirely. COS's REJECT applied to OpenSpace's mechanism, not to all auto-apply. **The COS doctrine permits auto-apply at the sandbox tier** — that is what `auto-skill-generator.sh` already does and which we keep.

---

## Reciprocity with ADR-176 (SkillStore adoption)

ADR-176 adopts OpenSpace's 6-table SQLite schema:
- `skill_records` — execution facts (skill_name, agent_session, tool_count, duration, status)
- `execution_analyses` — per-execution analyzer scores
- `skill_judgments` — judge model verdicts
- `skill_lineage_parents` — version graph
- `skill_tool_deps` — tool usage frequency per skill
- `skill_tags` — semantic categorisation

These tables provide exactly the inputs a promotion mechanism would query:

| Promotion signal | Source table |
|---|---|
| "Has this sandbox skill been invoked ≥ N times in T days?" | `skill_records` |
| "Has it succeeded ≥ X% of invocations?" | `skill_records` |
| "Have judges scored it ≥ Y on Z occasions?" | `skill_judgments` + `execution_analyses` |
| "Are its tool dependencies stable (no error spikes)?" | `skill_tool_deps` |
| "Does it form a coherent subgraph with related skills?" | `skill_lineage_parents` |

Without this data, the existing dormant `cos-doctrine-proposer` cannot generate evidence-backed promotion proposals. **Adopting SkillStore is the structural precondition.**

---

## Proposed ADR-177 (not yet drafted)

**Title**: Activate the Lifecycle Promotion Ladder

**Decision sketch** (subject to ADR-176 landing first):

1. **Promotion proposer** (`scripts/cos-promotion-proposer`):
   - Query SkillStore weekly (cron / SessionStart hook).
   - For each sandbox skill with `record_count ≥ 50 AND success_rate ≥ 0.85 AND judge_avg ≥ 0.8`, emit a propose-only artifact at `docs/reports/promotion-proposals/<date>/<skill>.md`.
   - Operator approves → manifest update + ADR fragment.

2. **Doctrine-proposer reactivation** (`scripts/cos-doctrine-proposer`):
   - Add metrics emission to `.cognitive-os/metrics/doctrine-proposals.jsonl`.
   - Connect input from SkillStore + dogfood-score + drift detectors.

3. **Demotion proposer** (companion):
   - Skills at advisory or blocking with `record_count == 0 in 90d` get a demotion proposal.
   - Operator approves → state moves down the ladder.

4. **Falsifiable claim**:
   - 90 days after activation, ≥ 5 sandbox skills should have promoted to advisory based on real evidence. If 0, the mechanism is broken.
   - dogfood_score.skill_coverage should rise from 24 to ≥ 60 within 6 months.

**Effort**: ~6-10h, all gated behind ADR-176 SkillStore landing.

---

## What this report does NOT do

- Does NOT draft ADR-177. ADR-177 depends on ADR-176 (SkillStore) being implemented and validated first.
- Does NOT modify the COS doctrine. The doctrine is correct; the gap is operational.
- Does NOT recommend changing the OpenSpace verdict. OpenSpace's auto-apply remains rejected for the reasons in ADR-176.

## Cross-references

- `docs/adrs/ADR-138-flow-contract-schema.md` — ladder doctrine.
- `docs/adrs/ADR-133-*.md`, `ADR-134-*.md`, `ADR-135-*.md` — propose-only contract.
- `docs/reports/openspace-opus-deep-audit-2026-05-05.md` — the audit that surfaced the SkillStore opportunity.
- `manifests/primitive-lifecycle.yaml` — current classification.
- `dogfood_score` — the metric that signals this gap is real.
- Engram topic_key `lifecycle-promotion-gap/2026-05-05` — saved counterpart for cross-session retrieval.
