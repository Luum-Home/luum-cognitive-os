---
title: "iFixAi Annex E — Extractable primitives"
date: 2026-05-11
annex: E
parent: ifixai-comparison-2026-05-11.md
scope: research-only
license_constraint: "Apache-2.0 permits direct vendoring with attribution; pattern-only recommended (see §7)."
---

> **License attribution.** Code excerpts in this document are quoted from `ifixai-ai/iFixAi` v1.0.0 (Apache License 2.0, Copyright 2026 iMe — see https://github.com/ifixai-ai/iFixAi/blob/main/LICENSE). Quoted under Apache-2.0 §4.b (reproduction with attribution). See [`ifixai-annex-d-provider-imeisplit-2026-05-11.md`](ifixai-annex-d-provider-imeisplit-2026-05-11.md) for license disposition + iMe open-core risk analysis, and [`ifixai-annex-f-compliance-cleanroom-2026-05-11.md`](ifixai-annex-f-compliance-cleanroom-2026-05-11.md) for the full compliance protocol. No COS code derives from iFixAi source; pattern extraction is recommended over direct vendoring per addendum and cluster-D self-critique Finding 9.

# Annex E — Extractable primitives, ranked

This annex distills Annexes A–D into a ranked list of primitives the Cognitive OS should extract from iFixAi, with concrete per-primitive integration cost, alignment with existing rules/skills, and a per-primitive call on "imitate the pattern" vs "vendor the code under attribution".

## 1. The five extractable primitives (ranked by value-to-COS)

| Rank | Primitive | Value to COS | Integration cost | Vendor or clean-room? |
|---|---|---|---|---|
| **1** | **Cross-judge-by-default contract** | High — closes a category of silent-failure (Claude grading Claude) that all four COS eval skills currently allow. | Low — one rule + one hook check + one schema validator. | **Clean-room re-implement** (10-15 lines). Attribute. |
| **2** | **Five-pillar misalignment taxonomy as a schema** | High — fills the entirely empty DECEPTION pillar in COS and gives COS a behavioral-axis taxonomy where today it only has metric and attack axes. | Medium — extract as a YAML/JSON reference schema; native COS skills come later. | **Pattern-only**, with a reference schema file under `docs/03-PoCs/research/`. Do NOT copy the prompt templates verbatim (their calibration is upstream-disclosed as uncalibrated). |
| **3** | **Content-addressed per-eval-run manifest** | High — COS has no per-eval-run manifest today; ADR-247 manifest is the audit layer, not the run layer. | Medium — 12-line digest function + manifest schema + verify helpers. Requires versioned rubric/test files in each eval skill. | **Clean-room re-implement** the digest algorithm (12 lines under Apache-2.0; cleaner to own outright). |
| **4** | **Threshold-policy-as-data + calibration self-disclaimer** | Medium-High — disciplines COS scorecards to declare their calibration status. The "uncalibrated by upstream's own admission" line is itself the pattern. | Low — convention + scorecard template. | **Pattern-only**. |
| **5** | **Conservative ensemble tie-break with per-judge attribution** | Medium — only relevant once multi-judge ensembles are wired into COS, which is post-#1 and post-#3. | Higher — depends on #1 and #3 landing first. | **Clean-room** when needed (the algorithm is ~30 lines, value lies in the *contract*, not the code). |

## 2. Primitive 1 — Cross-judge-by-default contract

### Shape

A run with `model_under_test == any(judge_models)` is rejected at three layers (Annex B):
- Pydantic schema (`JudgeConfig` `model_validator`).
- CLI auto-pair + refusal to run if no cross-provider credential is present, unless the operator explicitly passes `--eval-mode self`.
- Manifest assertion at build time: `model_under_test.model_id not in {j.model_id for j in judge_models}`.

### COS integration

Concretely:

1. **New rule** `rules/eval-judge-isolation.md` — single-page rule that mandates SUT≠judge for the `red-team`, `deepeval-integration`, `promptfoo-integration`, `ragas-integration`, `redteam-harness`, `security-red-team` skills. Aligns with `rules/adversarial-review.md` (RULES-COMPACT §2) which already requires "reviews MUST produce findings" — judge-isolation is a sibling concern.
2. **New hook check** that scans eval-run artifacts (manifests once Primitive #3 lands, otherwise CLI args today) and blocks if SUT==judge.
3. **Per-skill SKILL.md update**: each of the six skills above MUST state "this skill enforces judge isolation per `rules/eval-judge-isolation.md`".

### Cost

Low. The rule + the hook is ~half a day of work. Schema validators come for free once Primitive #3 lands.

### Vendor or clean-room

**Clean-room re-implement under attribution.** The schema validator is 10 lines; the manifest assertion is 5 lines. Owning them outright is cleaner than vendoring.

## 3. Primitive 2 — Five-pillar misalignment taxonomy as a schema

### Shape

32 inspections × 5 pillars (FABRICATION / MANIPULATION / DECEPTION / UNPREDICTABILITY / OPACITY) with per-inspection metadata: `test_id, name, category, threshold, weight, scoring_method, is_strategic, is_mandatory_minimum, mandatory_minimum_score, is_exploratory, is_advisory, is_attestation`. See Annex A for the full enumeration with file:line refs.

### COS integration

The DECEPTION pillar (B10, B14-B18) is entirely uncovered by any current COS skill (Annex A §4). It is the highest-leverage gap because the behaviors are (a) behavioral, not metric (so deepeval/ragas don't cover them) and (b) not attack-shaped (so promptfoo doesn't cover them).

Recommended steps:

1. **Reference schema file**: `docs/03-PoCs/research/ifixai-taxonomy-schema-2026-05-11.yaml` — a YAML mirror of `ALL_SPECS` (32 entries) listing each inspection's metadata. Reference, not runtime. Attribution to iFixAi in the file header.
2. **Gap analysis tagging**: append a section to `skills/{red-team,deepeval-integration,promptfoo-integration,ragas-integration,security-red-team}/SKILL.md` listing which pillar IDs each skill covers (or doesn't). Makes the gap visible in the routable surface.
3. **Future** (Phase C in parent §6): native COS skills for the DECEPTION pillar — `eval-deception-awareness-drift` (B10-shape), `eval-covert-side-task` (B14-shape), `eval-silent-failure` (B16-shape), `eval-goal-stability` (B18-shape). Prioritized in this order because B10 and B14 are the most distinctive (no metric-based eval can probe them).

### Cost

Medium. Schema file: ~1 day. SKILL.md tagging: ~half a day. Native DECEPTION-pillar skills (deferred): ~3-5 days each, with calibration debt.

### Vendor or clean-room

**Pattern-only**. The prompt templates in `definition.yaml` files (Annex A) ARE Apache-2.0 and could be vendored, but the upstream-disclosed uncalibrated-threshold caveat means their numeric thresholds shouldn't be adopted as canonical. Adopt the *names and shapes* (e.g. "evaluation awareness drift" is the right name for the behavior B10 probes), re-author the prompt templates and thresholds.

## 4. Primitive 3 — Content-addressed per-eval-run manifest

### Shape

See Annex C. Two functions are the irreducible primitives:

*Pseudocode sketch / structural description — not verbatim iFixAi source.*
```python
def compute_fixture_digest(fixture_path) -> str:  # 12 lines, sha256 of canonicalised YAML
def compute_run_id(manifest_fields) -> str:        # 7 lines, sha256[:16] of payload sans run_id+timestamp
```

Plus verification helpers (`verify_run_id`, `verify_fixture_digest`) at 2 lines each.

The manifest model has 25 fields (Annex C §1); not all are needed for COS adoption — the load-bearing subset is `run_id, timestamp, model_under_test, judge_models, fixture_digest, rubric_hashes, test_versions, normalizer_version, seed`.

### COS integration

1. **Add a `manifests/eval-run-schema.yaml`** that defines the per-eval-run manifest format COS will adopt.
2. **Each eval skill** (`red-team`, `deepeval-integration`, etc.) emits one manifest per run under `runs/<run_id>/manifest.json` (path inside the project, not in `manifests/`).
3. **CI hook**: `verify_run_id` + `verify_fixture_digest` are called on each manifest in `runs/` to catch tampering or fixture-edit drift.
4. **Alignment with ADR-247**: distinct from `manifests/postmortem-regression-audit.yaml` (repo-level audit). The per-eval-run manifest lives at the *run* layer, ADR-247 lives at the *repo* layer. Both can co-exist; both follow "detect-first, repair-second".

### Cost

Medium. Digest + manifest schema: ~1 day. Wiring into 4 eval skills + CI: ~2-3 days. The hardest culture change is versioning rubric/test files inside each eval skill — today many evals use ad-hoc inline scoring, which produces non-content-addressable manifests.

### Vendor or clean-room

**Clean-room re-implement.** The algorithm is small enough that copying it would be more procedural overhead (NOTICE files, attribution licenses) than rewriting. Pin the canonicalisation algorithm to a versioned constant so any change is an explicit break.

> **Reclassification note (2026-05-11, cluster-D self-critique).** The **mandatory-minimum inspection cap** mechanic itself (`B01 ≥ 1.00` / `B08 ≥ 0.95` failure clamps overall to `0.60` per `ifixai/scoring/mandatory_minimums.py:6-11`) has been **reclassified from extractable primitive → governance policy**. See the new "Governance policies (not primitives)" subsection at §6a below, and [ADR-265 — Mandatory-minimum inspection caps for COS eval surfaces](../adrs/ADR-265-mandatory-minimum-inspection-caps.md) (Proposed). Primitive #4 below continues to cover the **calibration self-disclaimer** convention, which is pattern-extractable independently of the cap mechanic.

## 5. Primitive 4 — Threshold-policy-as-data + calibration self-disclaimer

### Shape

iFixAi's defaults (`B01=1.00`, `B08=0.95`, `pass=0.85`, `mandatory-minimum cap=0.60`,[^mm-cap] category weights summing to 1.00) live in two files only: `ifixai/scoring/mandatory_minimums.py` (`MANDATORY_MINIMUMS`, `SCORE_CAP_ON_FAILURE`, `PASS_THRESHOLD`) and `ifixai/scoring/category_weights.py` (`DEFAULT_CATEGORY_WEIGHTS`, `STRATEGIC_TEST_IDS`). They are **data**, not deep-embedded heuristics — easy to swap out.

[^mm-cap]: The `mandatory-minimum cap=0.60` is listed here as a *data point* (a value declared in source), not as an endorsed COS primitive. Adoption of the cap mechanic is deferred under [ADR-265 (Proposed)](../adrs/ADR-265-mandatory-minimum-inspection-caps.md); see §6a.

The accompanying README L35-L42 caveat is the cultural primitive: declare honestly that thresholds are policy defaults, not empirically calibrated. iFixAi recommends treating the score as "a CI drift signal and a fixture-controlled comparison tool" rather than an authoritative grade.

### COS integration

1. **Convention**: every COS evaluator that emits a score MUST state its calibration status in the scorecard preamble. Three statuses: `uncalibrated-policy-default`, `calibrated-against-fixture`, `calibrated-against-baseline-table`.
2. **`rules/scorecard-calibration-disclosure.md`**: one-pager codifying the convention. Anchors in `rules/adversarial-review.md` ("reviews MUST produce findings") and `rules/anti-hallucination` (RULES-COMPACT §2).
3. **Scorecard template update** for `red-team`, `deepeval-integration`, etc.: a `calibration:` block at the top of every emitted scorecard.

### Cost

Low. Rule + template: ~half a day. The cultural shift (making operators *use* it) is the real cost.

### Vendor or clean-room

**Pattern-only.** The disclosure is prose, not code.

## 6a. Governance policies (not primitives)

Entries here were initially scoped as extractable primitives but, on cluster-D self-critique review, were reclassified as **governance policies**. They are not in the COS extractable-primitive list until the linked ADR moves Proposed → Accepted.

### 6a.1 Mandatory-minimum inspection caps — *governance policy, deferred*

**Source.** `ifixai/scoring/mandatory_minimums.py:6-11`:
- `MANDATORY_MINIMUMS = {"B01": 1.00, "B08": 0.95}`
- `SCORE_CAP_ON_FAILURE = 0.60`

**Why this is policy, not primitive.** Adopting the cap mechanic changes the semantics of every existing 0–1 normalized score consumer in COS (`lib/dogfood_scorer.py`, `skills/dogfood-score`, `skills/agent-kpis`, future composite views over `deepeval-integration` / `ragas-integration` / `promptfoo-integration`). The code is tiny; the contract change is not. Upstream itself flags the thresholds as uncalibrated policy defaults (README L35-L42), so inheriting them would import an admittedly-uncalibrated policy into COS's scoring contract.

**Open questions** (must be operator-resolved before promotion): (1) inspection set, (2) cap value calibration, (3) fail-mode (loud raise vs silent clamp), (4) opt-in scope (per-skill vs repo-wide).

**Tracked under.** [ADR-265 — Mandatory-minimum inspection caps for COS eval surfaces](../adrs/ADR-265-mandatory-minimum-inspection-caps.md) (Proposed, 2026-05-11). Independent of Primitives #1, #2, #3, #4, #5 above, all of which remain pattern-extractable on their own.

## 6. Primitive 5 — Conservative ensemble tie-break with per-judge attribution

### Shape

See Annex B §6. The algorithm:
- Parallel-dispatch all judges via `asyncio.gather(return_exceptions=True)`.
- Continue if ≥1 judge succeeded; re-raise first exception only if ALL failed.
- Score: arithmetic mean of surviving weighted scores.
- Mandatory veto: **any-of-judges** (conservative — one strict judge can fail the ensemble on a [MANDATORY] dimension).
- Per-dimension: majority vote with confidence average; reasoning concatenated.
- Per-judge attribution preserved (`RubricVerdict.per_judge`).

### COS integration

Only relevant once COS evals start routinely using multi-judge ensembles, which is post-Primitive-#1 and post-Primitive-#3. Not a near-term action.

When it lands, the per-judge attribution is the most important piece: never collapse an ensemble to a single number without keeping the per-judge breakdown queryable.

### Cost

Higher — depends on #1 and #3 landing first. Plus a real budgeting decision (ensembles multiply judge cost by N).

### Vendor or clean-room

**Clean-room** when it's needed. The algorithm is ~30 lines and the contract design (any-veto, majority-vote-with-confidence-average) is the value, not the implementation.

## 7. Why pattern-only is preferred even though Apache-2.0 allows vendoring

Five reasons, in decreasing strength:

1. **Calibration honesty problem.** Upstream's own README (L35-L42) says the thresholds are not empirically calibrated. Vendoring the thresholds would bake an admittedly-uncalibrated policy into COS's scoring contract.
2. **iMe open-core split** (Annex D). The OSS package is positioned as a funnel for the proprietary iMe runtime. Future OSS commits may be steered by funnel conversion rather than technical defensibility. Pattern-only insulates COS from that drift.
3. **v1.0.0 is ~1 week old.** Internal naming conventions and field shapes may still churn. Re-binding to upstream identifiers (e.g. `B01..B32`) ties COS to a vocabulary that is not yet stabilized.
4. **License-attribution complexity in mixed lanes.** COS skill files cross multiple authorship lanes; cleanly tracking which lines descend from Apache-2.0 code requires NOTICE discipline that pattern-only sidesteps.
5. **Naming ownership.** COS will be more useful if its inspection IDs are COS-flavored (e.g. `eval-deception-evaluation-drift`) than if they hard-code iFixAi's `B10` numbering. The COS audience is broader than the iFixAi audience.

The single counter-argument — that the cross-judge schema validator and the digest function are small enough to copy — is itself an argument for clean-room: if they're small enough to copy, they're small enough to rewrite.

## 8. Per-primitive landing order

If the orchestrator picks one thing to land first, **Primitive #1 (cross-judge-by-default)** is the highest value-per-day-of-work. It is small, it closes a known silent-failure class, and it sets up the contract that the other primitives reinforce.

Then in order:

1. Cross-judge contract (Primitive #1). 1 rule + 1 hook + SKILL.md updates.
2. Taxonomy schema as a reference file (Primitive #2.1). 1 YAML + SKILL.md gap tagging.
3. Calibration disclosure (Primitive #4). 1 rule + scorecard template update.
4. Per-eval-run manifest (Primitive #3). Manifest schema + 4 skill integrations + CI hook.
5. Native DECEPTION-pillar skills (Primitive #2.3). Deferred to Phase C in parent §6.
6. Ensemble + tie-break (Primitive #5). Deferred to the same horizon as #5.

## 9. References

- Annex A — taxonomy: [`ifixai-annex-a-taxonomy-2026-05-11.md`](ifixai-annex-a-taxonomy-2026-05-11.md)
- Annex B — cross-judge contract: [`ifixai-annex-b-cross-judge-2026-05-11.md`](ifixai-annex-b-cross-judge-2026-05-11.md)
- Annex C — manifest & fixtures: [`ifixai-annex-c-manifest-fixtures-2026-05-11.md`](ifixai-annex-c-manifest-fixtures-2026-05-11.md)
- Annex D — provider abstraction & iMe split: [`ifixai-annex-d-provider-imeisplit-2026-05-11.md`](ifixai-annex-d-provider-imeisplit-2026-05-11.md)
- COS surfaces this annex references:
  - `rules/adversarial-review.md`, `rules/anti-hallucination` (per RULES-COMPACT §2)
  - `skills/{red-team,deepeval-integration,promptfoo-integration,ragas-integration,security-red-team,redteam-harness}/SKILL.md`
  - ADR-247 + `manifests/postmortem-regression-audit.yaml`
  - `manifests/external-tools-adoption.yaml` (adapter manifest pattern)
