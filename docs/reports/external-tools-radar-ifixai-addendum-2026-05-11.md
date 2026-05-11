---
report_type: external-tools-radar-targeted-addendum
scope: ifixai-ai/iFixAi
source_index: docs/reports/external-tools-radar-INDEX.md
generated_at: 2026-05-11
status: documentation-before-implementation
related_adrs: [ADR-065, ADR-247, ADR-254]
source_artifacts:
  - docs/research/repo-scout/deep/ifixai-ai__iFixAi-2026-05-11.md
related_docs:
  - docs/architecture/external-tool-adoption-doctrine.md
  - docs/architecture/external-tool-adapter-taxonomy.md
  - docs/reports/external-tools-radar-evoskill-addendum-2026-05-09.md
  - docs/reports/external-tools-radar-full-reassessment-2026-05-08.md
---

> **License attribution.** Code excerpts in this document are quoted from `ifixai-ai/iFixAi` v1.0.0 (Apache License 2.0, Copyright 2026 iMe — see https://github.com/ifixai-ai/iFixAi/blob/main/LICENSE). Quoted under Apache-2.0 §4.b (reproduction with attribution). See [`../research/ifixai-annex-d-provider-imeisplit-2026-05-11.md`](../research/ifixai-annex-d-provider-imeisplit-2026-05-11.md) for license disposition + iMe open-core risk analysis, and [`../research/ifixai-annex-f-compliance-cleanroom-2026-05-11.md`](../research/ifixai-annex-f-compliance-cleanroom-2026-05-11.md) for the full compliance protocol. No COS code derives from iFixAi source; pattern extraction is recommended over direct vendoring per addendum and cluster-D self-critique Finding 9.

# External Tools Radar Addendum — iFixAi 2026-05-11

## Why this addendum exists

The user added `ifixai-ai/iFixAi` to the deep-analysis queue under the (incorrect)
working description "autonomous bug-fix agent". The deep evaluation confirmed iFixAi
is actually an **AI misalignment diagnostic / evaluation harness** — the inverse
of a code-fixer. This addendum records the corrected radar decision so future
iterations do not re-mis-classify the tool against bug-fix peers.

## Scope correction (read this first)

iFixAi is not comparable to `/plan-bug`, `/systematic-debugging`, the SDD
apply-verify retry loop (ADR-228), or `/auto-rollback`. It is comparable to
COS eval / red-team lanes: `red-team`, `redteam-harness`, `security-red-team`,
`deepeval-integration`, `promptfoo-integration`, `ragas-integration`,
and the aguara policy/standards crosswalk.

The original intake brief asked for bidirectional verdicts against the bug-fix
family; those verdicts are recorded as **NO_COMPARABLE** for completeness, and
the substantive verdicts are recorded against the eval/red-team family.

## Executive verdict

| Field | Decision |
|---|---|
| Radar status | **ASSESS / TRIAL-PATTERNS** |
| Recommendation | Extract taxonomy, cross-judge contract, and reproducibility manifest patterns now; optional `CLI-adapter` trial gated by manifest |
| Adoption kind | `pattern-only`, optional `CLI-adapter` |
| License | Apache-2.0 |
| Default-install posture | **Do not install by default** |
| Primary value | Five-pillar misalignment taxonomy (fabrication/manipulation/deception/unpredictability/opacity), provider-agnostic harness, content-addressed replay manifest, OWASP-LLM/NIST-AI-RMF/ISO-42001/EU-AI-Act mapping layer |
| Primary risk | Maturity (v1.0.0 is ~1 week old at eval); upstream-disclosed uncalibrated thresholds; open-core drift between OSS and the iMe client build |

## Current metadata snapshot

| Repository | License | Stars | Forks | Last push | Latest release | Open issues | CI | Radar call |
|---|---:|---:|---:|---|---|---:|---|---|
| [`ifixai-ai/iFixAi`](https://github.com/ifixai-ai/iFixAi) | Apache-2.0 | 332 | 50 | 2026-05-11 | `v1.0.0` (2026-05-04) | 2 | green (last 5 runs) | **ASSESS / TRIAL-PATTERNS** |

Verified on 2026-05-11 via GitHub API + README at commit `2e56c4f`. Counts are
not adoption proof.

## Full-stage pipeline result

| Stage | Result |
|---|---|
| Discovery | Relevant to COS eval/red-team gap; missing from prior radar corpus |
| Scope correction | Reframed from "bug-fix agent" to "misalignment diagnostic"; peer family changed |
| License gate | Apache-2.0, clean for pattern extraction and CLI-adapter trial |
| Source audit | Modular harness: providers / inspections / judge / fixtures / scoring / mappings / schemas / reporting |
| Evidence review | README self-discloses "no published baselines yet" and threshold policy is uncalibrated — strong honesty signal |
| Bidirectional cross-check | Better than COS at packaged misalignment taxonomy; not comparable to bug-fix family |
| Adoption decision | ASSESS as pattern-only; optional CLI-adapter behind ADR-247 manifest |
| Acceptance criteria | See below |

## Bidirectional implementation cross-check

### Against bug-fix family (per intake brief — recorded for traceability)

| Comparable | Verdict | Note |
|---|---|---|
| `/plan-bug` skill | **NO_COMPARABLE** | iFixAi does not analyze defects in user code |
| `/systematic-debugging` skill | **NO_COMPARABLE** | iFixAi is a black-box LLM diagnostic, not a debugger |
| SDD apply-verify retry loop (ADR-228) | **NO_COMPARABLE** | No code-edit retry contract; one-shot diagnostic |
| `/auto-rollback` | **NO_COMPARABLE** | No rollback responsibility |

### Against the actual peer family (eval / red-team / governance)

| iFixAi capability | COS state | Verdict | Action |
|---|---|---|---|
| Five-pillar misalignment taxonomy (32 inspections) | `red-team`, `redteam-harness`, `security-red-team` cover attack red-teaming; no shipped misalignment taxonomy with policy-disclosed thresholds | **MEJOR_EXTERNO** | Extract taxonomy as a COS pattern reference |
| Cross-judge by default (SUT cannot self-grade) | COS eval skills do not enforce evaluator isolation | **MEJOR_EXTERNO** | Encode as rule for COS eval lanes |
| Provider-portable harness (10 providers) | COS llm-dispatch covers Qwen/Claude per ADR-049 | **COMPATIBLE / DIFFERENT_AXIS** | No action — different surface |
| Content-addressed reproducibility manifest | COS has ADR-247 manifest doctrine; no per-eval-run content-addressed replay | **MEJOR_EXTERNO** (per-run) / **COMPATIBLE** (philosophy) | Pattern extract |
| Standards crosswalk (OWASP/NIST/ISO/EU-AI-Act) mapping layer | Aguara handles 189 rules; no public artifact-form crosswalk | **MEJOR_EXTERNO** (artifact form) | Use as reference structure for aguara docs |
| Threshold-policy self-disclaimer | COS scorecards do not standardize "calibration caveat" | **MEJOR_EXTERNO** (disclosure pattern) | Adopt as claim-debt control |
| vs `promptfoo-integration` | Promptfoo is a generic eval runner; iFixAi is opinionated on alignment | **IGUAL / DIFFERENT_AXIS** | Keep both; iFixAi for alignment lane, promptfoo for generic evals |
| vs `deepeval-integration` | DeepEval is metric-rich; iFixAi is taxonomy-rich | **IGUAL / DIFFERENT_AXIS** | Complementary |
| vs `ragas-integration` | Ragas is RAG-specific; iFixAi is alignment-specific | **IGUAL / DIFFERENT_AXIS** | Complementary |
| vs `red-team` / `redteam-harness` | COS red-team is attack-driven; iFixAi is inspection-driven | **COMPATIBLE** | iFixAi could be invoked from `red-team` lane via CLI-adapter |

## Adoption kind (per `external-tool-adapter-taxonomy.md`)

- **Initial**: `pattern-only` — taxonomy, cross-judge contract, manifest schema, threshold disclaimer pattern, standards-mapping structure.
- **Optional**: `CLI-adapter` — invoke `ifixai run` from the `red-team` / `security-red-team` lane behind ADR-247 manifest gating.
- **Not allowed without separate ADR**: `dependency`, `library import`, default install.

## What to extract

1. **Misalignment taxonomy** — fabrication / manipulation / deception / unpredictability / opacity, as a vocabulary reference in COS eval/red-team lane prompts and reports.
2. **Cross-judge-by-default rule** — "SUT must not grade itself unless explicitly opted in"; mirror the `--eval-mode self` escape and tiebreak order.
3. **Content-addressed reproducibility manifest** — pattern for COS eval artifacts under `docs/reports/`.
4. **Standards-crosswalk structure** — `ifixai/mappings/` as a reference shape (do not re-export specific mappings without independent review).
5. **Calibration caveat boilerplate** — standardize "drift-signal, not certified score" labelling in COS scorecards.
6. **Provider-extras installation pattern** — keeps core deps lean; aligns with COS llm-dispatch optionality.

## What not to extract

- No default `ifixai` dependency in COS bootstrap, requirements, hooks, packages, or install scripts.
- No re-export of iFixAi's specific OWASP/NIST/ISO/EU-AI-Act mappings as COS claims without independent review.
- No treatment of iFixAi letter grades as authoritative for COS release-gating, security claims, or vendor ranking.
- No assumption that the OSS build behaves like the iMe client build shown in the README demo GIF.

## Recommendation

ASSESS for ~30 days. Land pattern-only artifacts now. Design (but do not yet
execute) a `CLI-adapter` trial that invokes `ifixai run` from a COS red-team
lane behind an ADR-247 manifest row. Re-evaluate after a second release and
after upstream ships at least one empirically-calibrated baseline.

## Acceptance criteria

```text
ACCEPTANCE CRITERIA:
1. iFixAi remains an ASSESS / pattern-only radar entry until an adoption-manifest row exists in manifests/external-tools-adoption.yaml.
2. Any CLI-adapter trial pins a release tag (>= v1.0.0), runs in an isolated temp workdir, and uses dedicated low-privilege provider keys (no reuse of COS production keys).
3. The COS wrapper records: SUT provider+model, judge provider+model, fixture hash, manifest hash, pass/fail per pillar, threshold policy version, cost, and rollback command, written under docs/reports/.
4. Absolute letter grades carry a "drift-signal, not certified score" label in any COS report citing iFixAi.
5. No COS skill, rule, or hook treats an iFixAi scorecard as authoritative for promotion, release-gating, or external security claims without an additional human-reviewed audit.
6. Default COS install remains unchanged; no requirement on the ifixai package without a separate ADR.
7. Cross-judge isolation is enforced: SUT provider != judge provider in CI lanes; --eval-mode self only allowed in mock/drift lanes.
```

## Rollback path

1. **pattern-only rollback**: delete the pattern reference doc and any citations in `docs/architecture/` or `docs/patterns/ecosystem-tools.md`. No runtime impact.
2. **CLI-adapter rollback** (if ever trialled): remove the `red-team` lane invocation, drop the manifest row in `manifests/external-tools-adoption.yaml`, purge cached scorecards under `docs/reports/ifixai-runs/`. Adapter is self-contained — no schema or rule depends on it.
3. **Tombstone trigger**: upstream archives the repo, license changes, or open-core fork diverges past the documented OSS scope.

## Decision ledger row

| Tool/framework | Recommendation | Adoption kind | Reason | Next action |
|---|---:|---|---|---|
| ifixai-ai/iFixAi | ASSESS / TRIAL-PATTERNS | pattern-only, optional CLI-adapter | Misalignment taxonomy + cross-judge default + reproducibility manifest fill a COS eval-lane gap; runtime is 1 week past v1.0.0 with self-disclaimed uncalibrated thresholds | Land pattern-only references; design CLI-adapter behind ADR-247 manifest |

## Source evidence

- Deep evaluation: `docs/research/repo-scout/deep/ifixai-ai__iFixAi-2026-05-11.md`
- GitHub repository: <https://github.com/ifixai-ai/iFixAi>
- Homepage: <https://www.ifixai.ai/>
- COS comparables: `skills/red-team`, `skills/redteam-harness`, `skills/security-red-team`, `skills/deepeval-integration`, `skills/promptfoo-integration`, `skills/ragas-integration`
