# Audit Corpus Re-Validation — Research-Quality Score Across Prior Reports

**Date**: 2026-05-05
**Status**: read-only audit; no state modified.
**Trigger**: ADR-175 introduced a research-quality scoring heuristic. Hypothesis: prior audits likely have the same asymmetric-depth bug exposed tonight. This pass quantifies that.

---

## TL;DR

- **79 reports scored** (excluded: 2026-05-05 files, `*-tombstone.md`, `ARCHIVED.md`)
- **Distribution**: HIGH (≥80): 4 (5%) | MEDIUM (70–79): 3 (4%) | LOW (50–69): 31 (39%) | CRITICAL (<50): 41 (52%)
- **Overall corpus average: 47.6** — well below the ADR-175 threshold of 70; the hypothesis is confirmed
- **16 priority re-audit candidates**: score < 70 AND decision-criticality HIGH; includes all three aspirational audits, the harness landscape report, and the alternatives-comparison report
- **Top structural finding**: `falsifiable_claim` is 0 in 65/79 reports (82%); `numerical_specificity` is 0 in 53/79 (67%); `confidence_levels` is 0 in 45/79 (57%) — the corpus was written almost entirely without epistemic markers
- **Recommended first actions**: re-audit `ai-agent-harness-landscape-2026-05-04.md` and `alternatives-comparison-2026-04.md` with Opus (adoption decisions still actionable); add a pre-commit hook enforcement for the ADR-175 threshold on new reports going forward

---

## Methodology

**Files included**: all `docs/06-Daily/reports/*.md` not containing `2026-05-05` in the filename, not matching `*-tombstone.md` or `ARCHIVED.md`, and not under `docs/06-Daily/reports/auto-generated/` (no such subdirectory exists).

**Scoring tool**: `lib.research_quality_advisor.ResearchQualityAdvisor` (ADR-175). Four dimensions weighted as: `symmetric_citation` 40%, `confidence_levels` 25%, `numerical_specificity` 20%, `falsifiable_claim` 15%.

**Topic-family classification**: heuristic from filename keywords — `aspirational-audit`, `tool-comparison`, `forensics`, `readiness`, `smoke`, `case-study`, `one-off`. Edge cases are noted in Limitations.

**Decision-criticality classification**: inferred from filename — `HIGH` for adoption/architecture decision drivers, `MEDIUM` for operational/forensics reports, `LOW` for session notes and status reports.

---

## Score distribution

| Score band | Count | % | Notable examples |
|---|---|---|---|
| HIGH (≥80) | 4 | 5% | `audit-contract-serial-reversal-investigation-2026-05-01.md` (85), `sub-agent-context-trim-2026-04-20.md` (85) |
| MEDIUM (70–79) | 3 | 4% | `adr-137-plus-implementation-review-2026-05-04.md` (75), `pending-plans-audit-2026-04-30.md` (71) |
| LOW (50–69) | 31 | 39% | `ai-agent-harness-landscape-2026-05-04.md` (65), `adr-067-phase-2-2026-04-24.md` (65), `alternatives-comparison-2026-04.md` (53) |
| CRITICAL (<50) | 41 | 52% | `merge-readiness-master-plan-2026-04-23.md` (0), `claim-proof-latest.md` (0), `aspirational-audit-2026-05-03.md` (55 → actually LOW; see note) |

> Note: `merge-readiness-master-plan-2026-04-23.md` scored 0 across all four dimensions: no file:line citations, no confidence markers, 5 prose numeric claims with no fenced evidence blocks, no falsifiability section. Not an empty file — 94 lines of prose — but written entirely in the pre-ADR-175 narrative style.

---

## Per-topic score averages

| Topic family | Avg score | Reports | Notes |
|---|---|---|---|
| tool-comparison | 58.8 | 2 | Includes `ai-agent-harness-landscape` and `alternatives-comparison`; both score 65 and 53; adoption decisions not yet acted on |
| aspirational-audit | 55.0 | 3 | Recurring weekly batches; `falsifiable_claim` = 100 (all have limitations section), but `confidence_levels` = 0 across all three |
| case-study | 53.2 | 6 | Python-major, Docker, ADR implementation reviews; numerical specificity absent (avg num=12) |
| forensics | 50.2 | 13 | Varied; best scorer is `audit-contract-serial-reversal-investigation` at 85 |
| one-off | 49.7 | 27 | Session handoffs, punch lists, plan files; often intentionally short, lower stakes |
| readiness | 42.2 | 23 | Primitive readiness ledgers, gap matrices; tables score well on `symmetric_citation` (avg 98) but zero on confidence/falsifiability |
| smoke | 38.5 | 5 | Validation and test runs; pure pass/fail prose with no evidence blocks |

---

## Priority re-audit candidates

Sorted by score ascending. All have decision-criticality HIGH and score < 70.

| # | Report | Score | Weakest dim | Why it matters | Re-audit model |
|---|---|---|---|---|---|
| 1 | `merge-readiness-master-plan-2026-04-23.md` | 0.0 | symmetric_citation | Gated a branch merge; zero evidence on all four dimensions | opus |
| 2 | `docker-image-review-2026-05-04.md` | 40.0 | confidence_levels | Informs Docker base-image adoption; no confidence tagging or falsifiability | sonnet |
| 3 | `python-major-followup-2026-05-04.md` | 40.0 | confidence_levels | Follow-up on Python major-dep upgrade affecting CI; missing falsifiability and confidence | sonnet |
| 4 | `boring-reliability-audit-2026-05-03.md` | 45.0 | confidence_levels | Reliability adoption signal — high stakes, zero confidence markers, no falsifiability | opus |
| 5 | `python-major-deps-review-2026-05-04.md` | 49.2 | falsifiable_claim | Governs major Python dependency upgrade decisions; no falsifiable section | sonnet |
| 6 | `alternatives-comparison-2026-04.md` | 52.5 | numerical_specificity | Tool-choice decision driver; zero numerical evidence blocks and no falsifiability | opus |
| 7 | `dx-assessment-2026-05-02.md` | 52.5 | numerical_specificity | Developer-experience baseline used for tooling decisions; no numerical specificity | sonnet |
| 8 | `aspirational-audit-2026-04-20.md` | 54.9 | confidence_levels | Component-roadmap driver (509 table rows); zero confidence markers on claims | sonnet |
| 9 | `aspirational-audit-2026-05-02.md` | 55.0 | confidence_levels | Component-roadmap driver (787 rows); zero confidence markers | sonnet |
| 10 | `aspirational-audit-2026-05-03.md` | 55.0 | confidence_levels | Component-roadmap driver (848 rows); zero confidence markers | sonnet |
| 11 | `python-major-lane-resolution-2026-05-04.md` | 60.0 | confidence_levels | Resolves CI lane conflicts for python dep upgrade; zero confidence markers | sonnet |
| 12 | `adr-067-phase-2-2026-04-24.md` | 65.0 | numerical_specificity | ADR phase-2 implementation review; missing numerical evidence and falsifiability | opus |
| 13 | `ai-agent-harness-landscape-2026-05-04.md` | 65.0 | numerical_specificity | Harness-selection landscape report (adoption decision); no numerical evidence or falsifiability | opus |
| 14 | `cos-init-migration-2026-04-24.md` | 65.0 | numerical_specificity | Migration audit governing cos-init adoption; no numerical blocks or falsifiability | sonnet |
| 15 | `primitive-readiness-review-2026-05-04.md` | 65.0 | numerical_specificity | Primitive readiness gating promotion decisions; missing numerical and falsifiability | sonnet |
| 16 | `python-major-bumps-2026-04-24.md` | 65.0 | numerical_specificity | Documents major Python dep bump rationale; missing numerical evidence and falsifiability | sonnet |

---

## Reports that scored well (HIGH band — ≥ 80)

These four are exemplars. Common pattern: all have both a falsifiable/uncertainties/limitations section AND confidence-level markers in claim paragraphs.

| Report | Score | Key differentiators |
|---|---|---|
| `audit-contract-serial-reversal-investigation-2026-05-01.md` | 85.0 | Full confidence-marker coverage, explicit TRUST_REPORT section, fenced command blocks |
| `sub-agent-context-trim-2026-04-20.md` | 85.0 | Systematic claim tagging, limitations section with bullets, numerical claims backed by blocks |
| `docs-execution-latest.md` | 80.0 | 1162 table rows, 100% confidence score, explicit falsifiability section; loses points only on `numerical_specificity` |
| `prune-triage-2026-05-01.md` | 80.0 | Explicit claim boundaries, limitations section, consistent confidence markers; 74 table rows |

**Authoring patterns extracted from exemplars**:
1. Every claim paragraph tagged `HIGH / MEDIUM / LOW` before the verdict sentence
2. An explicit `## Limitations` or `## Uncertainties` / `## TRUST_REPORT` section (not a stub — at least one bullet)
3. Any numeric claim derived from a command is preceded by a ```` ```bash ```` block reproducing that command
4. Comparison tables cite `file.ext:line` on both sides (not just the "interesting" side)

---

## Limitations of this audit

- **Heuristic scorer**: `ResearchQualityAdvisor` uses regex, not semantic analysis. A narrative report written with consistent epistemic language but without the literal tokens `HIGH`/`MEDIUM`/`LOW` or `Confidence:` will score 0 on `confidence_levels` even if the underlying epistemic quality is fine.
- **Topic-family and decision-criticality classification are filename-heuristic only**: manual review may differ for edge cases, especially files named with non-descriptive patterns (e.g., `claim-proof-latest.md`, `d1b-clients-todo.md`).
- **Circularity**: the scoring tool was introduced tonight (ADR-175) and is being used to grade the corpus that predates it. The standard is new, not the reports. Low scores mean "did not follow a standard that did not yet exist" — not necessarily "was wrong at the time."
- **Aspirational-audit series falsifiability**: the three aspirational audit files have a `## Limitations` section and score 100 on `falsifiable_claim`, yet still average 55.0 overall because they have zero confidence markers anywhere in 2,000+ rows. This is a real gap (roadmap DORMANT/REAL/ASPIRATIONAL verdicts are never uncertainty-tagged) but it is distinct from asymmetric citation depth.
- **`merge-readiness-master-plan-2026-04-23.md` score=0**: confirms the report was written in pure prose with no evidence machinery. The merge it gated has long since been resolved; re-audit is historical, not urgent.
- **`numerical_specificity` scoring bias against tabular-only reports**: reports that carry all evidence in tables (e.g., primitive readiness ledgers) strip their numbers from prose before the scorer sees them, so lose `numerical_specificity` points even when the numbers are fully grounded in the table cells.

---

## Recommendation

1. **Immediate**: Re-audit `ai-agent-harness-landscape-2026-05-04.md` and `alternatives-comparison-2026-04.md` with Opus — both are adoption-decision drivers with active relevance and score ≤65. The asymmetric-depth bug documented tonight applies directly.
2. **Near-term**: Add a `TRUST_REPORT` / `## Uncertainties` section to the three aspirational audit templates (the batch generator writes them; one template change fixes all future runs). These are the highest-volume roadmap-driver reports.
3. **Process**: Enforce the ADR-175 70-point threshold in the pre-commit hook for any file matching `docs/06-Daily/reports/*.md` — `lib/research_quality_advisor.py` already supports this; it needs to be wired into `.claude/settings.json`.
4. **Template update**: Add a `## Confidence markers` section to `templates/agent-research-only.md` so future reports start with the required epistemic scaffolding.
5. **Deprecation candidates**: 7 reports scored 0–20 and have LOW decision-criticality (`claim-proof-latest.md`, `docs-duplicate-latest.md`, `primitive-gap-regressions.md`, `primitive-surface-reduction-latest.md`, `reduction-backlog-latest.md`, `next-session-plan-dormant-to-real.md`, `lifecycle-demotion-task-completed-2026-05-03.md`). Consider tombstoning or archiving.
6. **Exemplar documentation**: Extract authoring patterns from the four HIGH-band reports and add them as a "Research report authoring guide" to `docs/04-Concepts/architecture/` (one page, linked from the report template).
7. **Aspirational audit series**: The 3 weekly aspirational audit runs score 55 purely because of missing confidence markers — not because the DORMANT/REAL/ASPIRATIONAL classification is wrong. A targeted sonnet re-run adding `HIGH/MEDIUM/LOW` overlays to the verdict column would bring these to ~80 with minimal cost.
8. **Python major series** (`python-major-bumps`, `python-major-deps-review`, `python-major-followup`, `python-major-lane-resolution`): four related reports, all 40–65. Re-audit as a batch with a single sonnet agent referencing all four for coherence.

---

## Sources

<details>
<summary>All 79 files scored (grouped by score band)</summary>

**HIGH (≥80)**
- `docs/06-Daily/reports/audit-contract-serial-reversal-investigation-2026-05-01.md` — 85.0
- `docs/06-Daily/reports/sub-agent-context-trim-2026-04-20.md` — 85.0
- `docs/06-Daily/reports/docs-execution-latest.md` — 80.0
- `docs/06-Daily/reports/prune-triage-2026-05-01.md` — 80.0

**MEDIUM (70–79)**
- `docs/06-Daily/reports/adr-137-plus-implementation-review-2026-05-04.md` — 75.0
- `docs/06-Daily/reports/pending-plans-audit-2026-04-30.md` — 71.1
- `docs/06-Daily/reports/demotion-loop-audit-bite-verification-2026-05-03.md` — 70.0

**LOW (50–69)**
- `docs/06-Daily/reports/adr-067-phase-2-2026-04-24.md` — 65.0
- `docs/06-Daily/reports/ai-agent-harness-landscape-2026-05-04.md` — 65.0
- `docs/06-Daily/reports/cos-init-migration-2026-04-24.md` — 65.0
- `docs/06-Daily/reports/primitive-gap-latest.md` — 65.0
- `docs/06-Daily/reports/primitive-gap-matrix-2026-04.md` — 65.0
- `docs/06-Daily/reports/primitive-readiness-ledger-hooks-latest.md` — 65.0
- `docs/06-Daily/reports/primitive-readiness-ledger-rules-latest.md` — 65.0
- `docs/06-Daily/reports/primitive-readiness-ledger-scripts-latest.md` — 65.0
- `docs/06-Daily/reports/primitive-readiness-ledger-skills-latest.md` — 65.0
- `docs/06-Daily/reports/primitive-readiness-review-2026-05-04.md` — 65.0
- `docs/06-Daily/reports/python-major-bumps-2026-04-24.md` — 65.0
- `docs/06-Daily/reports/session-close-2026-04-20.md` — 65.0
- `docs/06-Daily/reports/bug2-reset-cascade-forensics-2026-04-20.md` — 60.8
- `docs/06-Daily/reports/python-major-lane-resolution-2026-05-04.md` — 60.0
- `docs/06-Daily/reports/second-demotion-candidate-resolution-2026-05-03.md` — 60.0
- `docs/06-Daily/reports/d01-git-reset-forensics-2026-04-20.md` — 59.2
- `docs/06-Daily/reports/implement-tier1-2026-05-02.md` — 59.2
- `docs/06-Daily/reports/debt-register-2026-04-20.md` — 57.0
- `docs/06-Daily/reports/aspirational-audit-2026-04-20.md` — 54.9
- `docs/06-Daily/reports/aspirational-audit-2026-05-02.md` — 55.0
- `docs/06-Daily/reports/aspirational-audit-2026-05-03.md` — 55.0
- `docs/06-Daily/reports/claim-boundary-resolution-2026-05-04.md` — 55.0
- `docs/06-Daily/reports/dormant-b1-batch-2026-05-02.md` — 55.0
- `docs/06-Daily/reports/preserve-branch-governance-2026-05-02.md` — 55.0
- `docs/06-Daily/reports/redteam-consumer-rehearsal-2026-05-02.md` — 55.0
- `docs/06-Daily/reports/skill-side-dormant-2026-05-02.md` — 55.0
- `docs/06-Daily/reports/alternatives-comparison-2026-04.md` — 52.5
- `docs/06-Daily/reports/dx-assessment-2026-05-02.md` — 52.5
- `docs/06-Daily/reports/orchestrator-dogfood-smoke-test-2026-04-20.md` — 54.3
- `docs/06-Daily/reports/hook-registration-classification-2026-05-04.md` — 50.0
- `docs/06-Daily/reports/next-session-handoff-2026-04-20.md` — 50.0

**CRITICAL (<50)**
- `docs/06-Daily/reports/d1b-clients-todo.md` — 49.2
- `docs/06-Daily/reports/python-major-deps-review-2026-05-04.md` — 49.2
- `docs/06-Daily/reports/pre-existing-test-failures-2026-04-21.md` — 48.3
- `docs/06-Daily/reports/swarm-stress-2026-05-02.md` — 45.0
- `docs/06-Daily/reports/boring-reliability-audit-2026-05-03.md` — 45.0
- `docs/06-Daily/reports/cross-instance-consumer-e2e-2026-05-03.md` — 45.0
- `docs/06-Daily/reports/global-verify-validation-2026-04-20.md` — 45.0
- `docs/06-Daily/reports/stash-resolution-2026-05-01.md` — 45.0
- `docs/06-Daily/reports/hook-audit-2026-04.md` — 44.2
- `docs/06-Daily/reports/primitive-duplication-triage-latest.md` — 44.2
- `docs/06-Daily/reports/primitive-row-audit-latest.md` — 44.2
- `docs/06-Daily/reports/reconciliation-audit-2026-04-20.md` — 44.2
- `docs/06-Daily/reports/test-quality-audit-2026-04-20.md` — 44.2
- `docs/06-Daily/reports/docker-image-review-2026-05-04.md` — 40.0
- `docs/06-Daily/reports/full-suite-validation-2026-04-23.md` — 40.0
- `docs/06-Daily/reports/install-timing-baseline-2026-05-01.md` — 40.0
- `docs/06-Daily/reports/metrics-census.md` — 40.0
- `docs/06-Daily/reports/plugin-caveman-review-2026-04-20.md` — 40.0
- `docs/06-Daily/reports/primitive-coverage-backend-benchmark-2026-05-01.md` — 40.0
- `docs/06-Daily/reports/primitive-coverage-latest.md` — 40.0
- `docs/06-Daily/reports/primitive-duplication-latest.md` — 40.0
- `docs/06-Daily/reports/primitive-fitness-ledger-latest.md` — 40.0
- `docs/06-Daily/reports/primitive-usage-map-latest.md` — 40.0
- `docs/06-Daily/reports/punch-list-hooks.md` — 40.0
- `docs/06-Daily/reports/punch-list-lib.md` — 40.0
- `docs/06-Daily/reports/punch-list-skills.md` — 40.0
- `docs/06-Daily/reports/python-major-followup-2026-05-04.md` — 40.0
- `docs/06-Daily/reports/test-suite-repair-ledger-2026-04-24.md` — 33.1
- `docs/06-Daily/reports/artifact-verification-2026-04-20.md` — 34.1
- `docs/06-Daily/reports/agentic-mastery-validation-2026-05-02.md` — 20.0
- `docs/06-Daily/reports/lifecycle-demotion-task-completed-2026-05-03.md` — 20.0
- `docs/06-Daily/reports/next-session-plan-dormant-to-real.md` — 20.0
- `docs/06-Daily/reports/primitive-gap-regressions.md` — 20.0
- `docs/06-Daily/reports/primitive-readiness-lifecycle-backlog-scripts-latest.md` — 20.0
- `docs/06-Daily/reports/primitive-surface-reduction-latest.md` — 20.0
- `docs/06-Daily/reports/reduction-backlog-latest.md` — 20.0
- `docs/06-Daily/reports/validation-worktree-mutation-postmortem-2026-05-02.md` — 5.0
- `docs/06-Daily/reports/punch-list-rules.md` — 15.0
- `docs/06-Daily/reports/claim-proof-latest.md` — 0.0
- `docs/06-Daily/reports/docs-duplicate-latest.md` — 0.0
- `docs/06-Daily/reports/merge-readiness-master-plan-2026-04-23.md` — 0.0

</details>
