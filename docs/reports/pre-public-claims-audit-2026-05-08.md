# Pre-Public Claims Audit — 2026-05-08

## Scope

Task D audit of public-facing claims in the pre-public surface. I treated these files as the public claim surface because `manifests/public-claim-evidence.yaml` includes them:

- `README.md`
- `docs/business/executive-summary.md`
- `docs/business/kubernetes-for-agents.md`
- `docs/business/value-proposition.md`
- `docs/business/features.md`

Non-goals for this task: history sanitization and license FAQ cleanup. Existing edits in those areas were not touched.

## Commands Run

| Command | Result | Notes |
|---|---|---|
| `python3 scripts/aspirational_audit.py --help` | PASS | Confirmed dry-run / JSON options. |
| `python3 scripts/cos-public-claim-gate --json` | PASS | `status=pass`, `finding_count=0`. |
| `python3 scripts/claim_proof_audit.py --project-dir . --json-out /tmp/cos-claim-proof-task-d.json --md-out /tmp/cos-claim-proof-task-d.md --fail-unmapped` | PASS | Initial proof map: 598 claims, no unmapped failures. |
| `python3 scripts/aspirational_audit.py --dry-run --json --project-root .` | FAIL | Produced JSON, then exited non-zero under default threshold policy: 1025 total, 318 REAL, 183 DORMANT, 38 ASPIRATIONAL, ratio 21.56%. |
| `python3 scripts/cos-claim-signature-audit --json` | FAIL | Operator error: this path is a shell wrapper; reran correctly as `./scripts/cos-claim-signature-audit --json`. |
| `./scripts/cos-claim-signature-audit --json` | PASS | 3 product claims checked; 2 signed, 1 unsigned/info, 0 fail. |
| `./scripts/cos-tier-claim-audit --json` | PASS | 247 ADRs checked; `finding_count=0`. |
| `./scripts/cos-manifest-tier-claim-audit --json` | WARN | 249 findings, 145 warnings; manifest distribution claims still have promotion/demotion evidence gaps. |
| `python3 scripts/aspirational_audit.py --dry-run --json --threshold 0.4 --project-root . > /tmp/cos-aspirational-task-d.json` | PASS | Final dry-run summary: 1026 total, 318 REAL, 184 DORMANT, 38 ASPIRATIONAL, ratio 21.64%. |
| `./scripts/cos-public-claim-gate --json > /tmp/cos-public-claim-gate-task-d.json` | PASS | Final public gate: `status=pass`, `finding_count=0`. |
| `python3 scripts/claim_proof_audit.py --project-dir . --json-out /tmp/cos-claim-proof-task-d-post.json --md-out /tmp/cos-claim-proof-task-d-post.md --fail-unmapped` | PASS | Final proof map: 596 mapped claims, 0 weak-proof, 0 unmapped. |
| `./scripts/cos-claim-signature-audit --json > /tmp/cos-claim-signature-task-d.json` | PASS | Final signature gate: `status=pass`; `self-building` and `maturity-loop` signed; `helps-projects` info-only unsigned. |
| `./scripts/cos-tier-claim-audit --json > /tmp/cos-tier-claim-task-d.json` | PASS | Final ADR tier gate: `status=pass`, `finding_count=0`. |
| `./scripts/cos-manifest-tier-claim-audit --json > /tmp/cos-manifest-tier-claim-task-d.json` | WARN | Final manifest tier gate: `status=warn`, `finding_count=249`, `warning_count=145`. |

## Classification Summary

| Claim family | Classification | Evidence | Action taken |
|---|---|---|---|
| Public autonomous/self-improvement claims in README/business docs | REAL as bounded/demoted wording | `cos-public-claim-gate` final pass with `finding_count=0`; README and feature docs already state self-improvement/self-healing are propose-only and human-gated. | Tightened two public docs to remove residual autonomous/auto-improvement phrasing. |
| Claim-to-proof mapping for public docs and ADR/business docs | REAL | `claim_proof_audit.py --fail-unmapped` final output: 596 claims, all `mapped`. | No broad edits required. |
| Aspirational primitive classification | PARTIAL | Final aspirational dry-run: 1026 total; 318 REAL, 425 ON_DEMAND, 184 DORMANT, 38 ASPIRATIONAL, 61 METADATA; dormant+aspirational ratio 21.64%. | Recorded as a remaining maturity risk, not a public-claim blocker by itself. |
| Signed product claims | PARTIAL | `cos-claim-signature-audit`: 3 claims; 2 signed; `helps-projects` remains unsigned but info-only because no non-maintainer 30+ day adoption report exists. | Kept external adoption/help claim bounded; no unsupported unasterisked proof added. |
| ADR tier claims | REAL | `cos-tier-claim-audit`: 247 ADRs, `finding_count=0`. | No edits. |
| Manifest distribution tier claims | PARTIAL | `cos-manifest-tier-claim-audit`: `status=warn`, 249 findings: 95 maintainer-knowledge-dependent, 76 core/team without strong evidence, 69 candidate-to-lab/advisory, 9 candidate second-demote. | No broad demotions in this task; tracked as a remaining risk. |
| Kubernetes-scale / millions-of-agents positioning | ROADMAP | `docs/business/kubernetes-for-agents.md` marks Phase 2+ items unchecked and says production claims need explicit proof. | Changed current-state bullets from auto-improving/auto-repair to governed proposal/workflow wording. |
| Self-improvement / self-healing | PARTIAL | `docs/business/features.md` labels Self-Improvement Loop and SRE/Self-Healing as DORMANT/propose-only; ADR-201/204/206 gate autonomous mutation. | Changed `value-proposition` wording from “learns from its mistakes” / “autonomous engineering teams” to governed wording. |

## Files Changed

- `docs/reports/pre-public-claims-audit-2026-05-08.md` — this audit report.
- `docs/business/value-proposition.md` — minimal wording demotion: self-improvement is governed proposals; footer says governed engineering teams instead of autonomous engineering teams.
- `docs/business/kubernetes-for-agents.md` — minimal wording demotion: current-state skills/SRE bullets now say governed improvement proposals / governed repair workflow.

## Remaining Risks

1. `cos-manifest-tier-claim-audit` still warns on 145 manifest distribution evidence gaps. This is not fixed here because it would require broad manifest promotion/demotion work outside Task D scope.
2. `cos-claim-signature-audit` leaves `helps-projects` unsigned/info-only until a non-maintainer project has a 30+ day core adoption report with prevented incidents, false-positive ratio, and cognitive-cost feedback.
3. The aspirational audit still reports 38 ASPIRATIONAL and 184 DORMANT primitives. Public docs should continue using REAL/PARTIAL/DORMANT/ROADMAP labels rather than implying all primitives are fully production-real.
4. This session saw unrelated working-tree changes before and during the audit. I did not revert or modify history sanitization, license FAQ, or other out-of-scope files.

## Acceptance Criteria

1. Existing public autonomous/self-improvement claim gate passes: `cos-public-claim-gate status=pass`.
2. Existing claim proof audit has no unmapped claims: `claim_proof_audit.py --fail-unmapped` exits 0 with all rows mapped.
3. Existing aspirational audit primitives classify the repo and are cited with counts.
4. Any public claim fixes are small label/evidence wording changes only.

TRUST_REPORT: SCORE=82 STATUS=HIGH EVIDENCE=5 UNCERTAINTIES=3
