---
evaluated_at: 2026-05-11 UTC
engram_id: pending
deepwiki_url: null
batch: targeted-user-request
parent_radar: docs/06-Daily/reports/external-tools-radar-INDEX.md
introduced_by_commit: 2e56c4f
last_verified_commit: 2e56c4f
source_url: https://github.com/ifixai-ai/iFixAi
homepage: https://www.ifixai.ai/
---

> **License attribution.** Code excerpts in this document are quoted from `ifixai-ai/iFixAi` v1.0.0 (Apache License 2.0, Copyright 2026 iMe — see https://github.com/ifixai-ai/iFixAi/blob/main/LICENSE). Quoted under Apache-2.0 §4.b (reproduction with attribution). See [`../../ifixai-annex-d-provider-imeisplit-2026-05-11.md`](../../ifixai-annex-d-provider-imeisplit-2026-05-11.md) for license disposition + iMe open-core risk analysis, and [`../../ifixai-annex-f-compliance-cleanroom-2026-05-11.md`](../../ifixai-annex-f-compliance-cleanroom-2026-05-11.md) for the full compliance protocol. No COS code derives from iFixAi source; pattern extraction is recommended over direct vendoring per addendum and cluster-D self-critique Finding 9.

## Repository Evaluation: ifixai-ai/iFixAi

### Classification: ASSESS / TRIAL-PATTERNS
**Score**: 7.6/10 (mechanical).  Runtime call: **ASSESS** (pattern-only adoption candidate; optional `adapter-lab` CLI integration after manifest gate).
**Evaluation Level**: 3 (deep — GitHub API metadata, README, source tree listing, release/CI history, last commit on evaluation day).
**Theme**: AI misalignment diagnostic / multi-provider safety scorecard  •  **Surface role**: provider-agnostic evaluation harness with content-addressed reproducibility manifest.

### Critical scope correction
The intake brief described iFixAi as an "autonomous bug-fix agent". **That is incorrect.** iFixAi is the *opposite* of a code-fixer: it is a black-box AI **misalignment diagnostic** that runs 32 inspections against an LLM/agent under test (SUT) across five risk pillars — *fabrication, manipulation, deception, unpredictability, opacity* — and emits a letter-graded scorecard plus a content-addressed manifest for bit-identical replay. The naming ("Fix Ai") is product framing, not behaviour. Treating iFixAi as a bug-fix peer of `/plan-bug` or the SDD apply-verify loop is a category error; the correct COS peers are `red-team`, `redteam-harness`, `deepeval-integration`, `promptfoo-integration`, `ragas-integration`, and the security/safety eval lane.

### Summary

iFixAi is an Apache-2.0 Python (3.10+) CLI + library that drives any LLM/agent through a fixture-controlled battery of 32 inspections, with **cross-judge** as the default (a second, different provider judges the SUT to avoid self-grading). It supports `openai`, `anthropic`, `gemini`, `azure`, `bedrock`, `huggingface`, `openrouter`, `http` (OpenAI-compatible), `langchain`, and `mock`. Output is a scorecard under `./ifixai-results/` plus a reproducibility manifest. Scoring policy uses thresholds (B01=1.00, B08=0.95, pass=0.85, mandatory-minimum cap=0.60) that the project **explicitly disclaims as policy defaults, not empirically calibrated** — recommending its honest use as a CI drift signal and same-fixture A/B comparator rather than as an absolute safety claim.

**Verdict rationale**: iFixAi is a clean, well-disclaimed, alignment-oriented eval harness that *fills a niche COS does not currently cover end-to-end*: pre-packaged misalignment categories (manipulation, deception, opacity) wired to a multi-provider runner with a reproducibility manifest. COS already has `red-team`, `redteam-harness`, `promptfoo-integration`, `deepeval-integration`, and `ragas-integration`, but none of those ship a five-pillar misalignment taxonomy with policy-disclosed thresholds. The right move is to extract the inspection taxonomy and the content-addressed manifest pattern as references for COS eval lanes, and optionally trial the CLI as a provider-portable diagnostic invoked from `red-team` / `security-red-team`. Do **not** wire it as a default dependency or treat its absolute scores as authoritative — the project itself warns against that.

### Deep-analysis stage ledger

| Stage | Primitive used | What was checked | Finding | COS decision |
|---|---|---|---|---|
| 1. Discovery / positioning | Repo scout + radar index | README, GitHub metadata, topics, homepage | Misalignment diagnostic, **not** bug-fixer; correct peer family is COS eval/red-team lanes | Reframe before scoring |
| 2. Metadata / license | License gate | GitHub API, LICENSE | Apache-2.0, 332★, 50 forks, last push 2026-05-11 (eval day), 2 open issues, v1.0.0 released 2026-05-04 | License clean for pattern extraction and CLI adapter |
| 3. Claims / disclaimers | Evidence review | README "No published baselines yet" disclaimer, scoring.md calibration caveat | Project self-discloses thresholds are policy defaults, not calibrated; positions itself as drift signal and same-fixture comparator | Strong honesty signal; reduces governance risk for trial |
| 4. Source anatomy | Code audit | `ifixai/{cli,core,evaluation,fixtures,harness,inspections,judge,mappings,observability,providers,reporting,rules,schemas,scoring}` | Modular harness: providers adapter, inspection registry, judge layer, scoring engine, schemas, reporting, observability hooks | Architecture is clean and adapter-friendly |
| 5. Provider portability | Adapter audit | README provider matrix + `ifixai/providers/` | OpenAI, Anthropic, Gemini, Azure, Bedrock, HuggingFace, OpenRouter, HTTP (OAI-compat), LangChain, mock | Broad portability — useful for COS llm-dispatch parity testing |
| 6. Reproducibility | Schema audit | `docs/reproducibility.md`, content-addressed manifest claim | Bit-identical replay via content-addressed manifest; same-fixture A/B is the defensible use | Pattern worth extracting for COS eval artifacts |
| 7. Safety / governance | Policy review | Cross-judge default, `--eval-mode self` escape, mandatory-minimum cap, OWASP-LLM/NIST-AI-RMF/ISO-42001/EU-AI-Act topic tags | Strong evaluator-isolation default; standards-mapped taxonomy (mappings/) | Mapping layer aligns with COS aguara/policy posture |
| 8. CI / activity | Release health | GitHub Actions, releases | Last 5 CI runs green; one release (v1.0.0); 2 open issues; merging PRs on eval day | Healthy but young (~2 weeks since v1.0.0) |
| 9. Bidirectional cross-check | COS-vs-external | red-team, redteam-harness, deepeval, promptfoo, ragas, plan-bug, systematic-debugging | Misalignment taxonomy + multi-provider matrix + manifest is novel vs COS eval suite; not comparable to bug-fix loop | Add as ASSESS / pattern-only; explore CLI-adapter |
| 10. Adoption planning | Adapter taxonomy | dependency vs CLI-adapter vs pattern-only | Best initial kind: `pattern-only` for taxonomy + manifest schema; `CLI-adapter` optional for red-team lane | Manifest-gated trial only |

### Scoring Breakdown

| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 7/10 | Useful complement to COS eval/red-team lanes; not in the critical bug-fix or SDD path; gap-filling not core-replacing |
| License | 25% | 10/10 | Apache-2.0, no patent traps observed |
| Activity | 20% | 9/10 | Commits on eval day, CI green, public discussions enabled |
| Maturity | 15% | 5/10 | v1.0.0 from 2026-05-04, only ~2 weeks old; explicit no-baselines disclaimer; single release; small issue queue |
| Integration | 10% | 7/10 | Python 3.10+, optional provider extras, CLI-first, JSON manifest output — friendly to CLI-adapter; not a drop-in library replacement for any COS primitive |
| **Weighted Total** | | **7.6/10** | Mechanical score; runtime adoption gated by manifest + calibration trial |

### Adoption Signals

| Signal | Value | Descriptor |
|--------|-------|------------|
| Stars / forks | 332★ / 50 forks | early traction for a 2-week-old v1.0 |
| Open issues / PRs | 2 open issues; merged PRs #11–#20 in May 2026 | active maintenance |
| Release cadence | 1 release (`v1.0.0` on 2026-05-04) | nascent — too young for trend |
| CI health | last 5 workflow runs green on `main` | healthy current signal |
| License | Apache-2.0 | clean |
| Standards mapping | OWASP-LLM, NIST-AI-RMF, ISO-42001, EU-AI-Act topics + `ifixai/mappings/` | substantive standards alignment posture |
| Author / sponsor | iMe organization; companion homepage <https://www.ifixai.ai/> | commercial-OSS posture (open-core risk to monitor) |

### Architecture summary

```
ifixai/
├── cli/              # Entry: `ifixai run …`, fixture/judge/eval-mode flags
├── core/             # Run orchestration
├── providers/        # SUT + judge adapters (openai, anthropic, gemini,
│                     #   azure, bedrock, huggingface, openrouter, http,
│                     #   langchain, mock)
├── inspections/      # 32 inspection definitions grouped by 5 pillars
├── fixtures/         # Domain-neutral test fixtures + author-your-own
├── judge/            # Judge selection, tie-break order, cross-judge
├── evaluation/       # Run engine
├── scoring/          # Threshold policy (B01, B08, pass, mandatory-min cap)
├── rules/            # Policy rules layer
├── mappings/         # OWASP-LLM / NIST-AI-RMF / ISO-42001 / EU-AI-Act maps
├── schemas/          # JSON schemas for fixtures, results, manifest
├── reporting/        # Scorecard renderer (letter grade)
├── observability/    # Hooks
└── harness/          # Test/harness glue
```

The five-pillar taxonomy (fabrication, manipulation, deception, unpredictability, opacity) and the **default cross-judge** policy (SUT cannot grade itself; tie-break order documented in README) are the two most extractable design ideas. The content-addressed manifest for bit-identical replay is the third.

### Primitive extraction candidates

1. **Five-pillar misalignment taxonomy** — adopt as a vocabulary reference in COS `red-team`, `security-red-team`, and `redteam-harness` skill prompts; do not blindly copy thresholds.
2. **Cross-judge-by-default contract** — encode "SUT must not grade itself unless explicitly opted in" as a rule in COS eval lanes (mirrors the `--eval-mode self` escape hatch).
3. **Content-addressed reproducibility manifest** — pattern for COS eval artifacts; bit-identical replay maps to ADR-247 manifest-driven adapter posture.
4. **Standards mapping layer** (`ifixai/mappings/`) — reference structure for OWASP-LLM / NIST-AI-RMF / ISO-42001 / EU-AI-Act crosswalks; potential reuse in aguara integration.
5. **Threshold-policy disclaimer pattern** — explicitly disclose "policy defaults, not empirically calibrated" in COS eval scorecards as a claim-debt control.
6. **Provider extras matrix** — installation pattern (`pip install -e ".[openai]"`) for keeping core deps lean; mirrors COS llm-dispatch optionality.

### Integration cost estimate

| Adoption kind | Effort | Risk | Notes |
|---|---|---|---|
| pattern-only (taxonomy + manifest + cross-judge contract) | **S** (~0.5 day) | low | Add reference doc in `docs/04-Concepts/patterns/` or `docs/04-Concepts/architecture/`; cite mappings; no runtime change |
| CLI-adapter (invoke `ifixai run` from a COS `red-team` lane) | **M** (~1–2 days) | medium | Pin version, sandbox cwd to a temp dir, require explicit provider keys via env, capture manifest under `docs/06-Daily/reports/`; mark scores as drift-signal |
| Schema port (vendor JSON schemas from `ifixai/schemas/` for COS scorecards) | **M** (~1 day) | low | License-clean (Apache-2.0); attribute upstream |
| Default dependency / library import | **L** | **HIGH — DO NOT** | v1.0.0 is 1 week old; thresholds disclaimed as uncalibrated; would bind COS to an immature scoring policy |

### Risks

1. **Calibration debt (upstream-disclosed)**: README and `docs/scoring.md` admit thresholds are policy defaults with no empirical baselines. Treating absolute letter grades as authoritative would import that debt into COS.
2. **Maturity**: 2 weeks past v1.0.0, single release, 332 stars, small contributor base. Insufficient track record to make a default dependency.
3. **Self-judge collision**: With OpenRouter routing, the SUT and the cross-judge can resolve to the same underlying model; README documents the mitigation (`--judge-provider` pin) but it is the user's responsibility.
4. **Open-core ambiguity**: The README explicitly warns the demo GIF shows a *custom client build* whose fixtures, scoring policy, and UI differ from OSS. Future drift between OSS and proprietary fork is plausible — watch for feature divergence.
5. **Credential surface**: Cross-judge default requires *two* provider keys in env. CLI-adapter integration must isolate credential propagation per COS credential-management rule.
6. **Benchmark contamination**: Fixtures are domain-neutral and small; gaming or overfit is straightforward. Use only as drift signal + same-fixture A/B, never as vendor ranking.
7. **Standards-mapping precision**: OWASP/NIST/ISO/EU-AI-Act labels are governance-sensitive. Adopt the *structure* of the mapping layer, but do not re-export iFixAi's specific mappings as COS claims without independent review.

### Bidirectional cross-check (compact)

| iFixAi capability | COS state | Verdict | Action |
|---|---|---|---|
| 32-inspection misalignment battery | COS has `red-team`, `redteam-harness`, `security-red-team`, `deepeval-integration`, `promptfoo-integration`, `ragas-integration` — none ships a five-pillar misalignment taxonomy with policy-disclosed thresholds | **EXTERNAL_BETTER** (taxonomy) / **NOT_COMPARABLE** (overall scope) | Extract taxonomy as pattern |
| Cross-judge-by-default | COS does not enforce evaluator isolation in eval skills | **EXTERNAL_BETTER** | Add as rule for COS eval lanes |
| Content-addressed reproducibility manifest | COS has ADR-247 manifest doctrine but not per-eval-run content-addressed replay | **EXTERNAL_BETTER** (per-run replay) / **COMPATIBLE** (manifest philosophy) | Pattern extract |
| Multi-provider matrix (10 providers) | COS llm-dispatch covers Qwen/Claude per ADR-049 | **COMPATIBLE / DIFFERENT_AXIS** | No action; complementary surfaces |
| Standards mappings (OWASP/NIST/ISO/EU-AI-Act) | COS aguara handles 189 rules but no public crosswalk artifact | **EXTERNAL_BETTER** (artifact form) | Use as reference for aguara docs |
| vs `/plan-bug`, `/systematic-debugging` | iFixAi does not fix bugs; it diagnoses misalignment | **NOT_COMPARABLE** | No interaction — different surface |
| vs SDD apply-verify retry loop (ADR-228) | iFixAi is a one-shot diagnostic; no retry contract | **NOT_COMPARABLE** | No interaction |
| vs `/auto-rollback` | iFixAi has no rollback responsibility | **NOT_COMPARABLE** | No interaction |

### Recommendation

**ASSESS** the iFixAi project for ~30 days. Extract pattern-only artifacts (taxonomy, cross-judge contract, manifest schema) immediately. Optionally trial a `CLI-adapter` invocation from the `red-team` / `security-red-team` lanes behind ADR-247 manifest gating. Do not add as a default dependency. Re-evaluate after a second release (`v1.1.0+`) and after the project ships empirical baselines for at least one frontier model.

### Acceptance criteria (for any future runtime trial)

```text
ACCEPTANCE CRITERIA:
1. iFixAi remains an ASSESS / pattern-only radar entry until an adoption-manifest row exists in manifests/external-tools-adoption.yaml.
2. Any CLI-adapter trial pins a release tag (>= v1.0.0), runs in an isolated temp workdir, and uses dedicated low-privilege provider keys.
3. The COS wrapper records: SUT provider+model, judge provider+model, fixture hash, manifest hash, pass/fail per pillar, threshold policy version, and rollback command.
4. Absolute letter grades are labeled "drift-signal, not certified score" in any COS report citing iFixAi.
5. No COS skill or rule treats an iFixAi scorecard as authoritative for promotion, release-gating, or security claims without an additional human-reviewed audit.
6. Default COS install remains unchanged; no requirement on ifixai package without a separate ADR.
```

### Decision ledger row

| Tool/framework | Recommendation | Adoption kind | Reason | Next action |
|---|---:|---|---|---|
| ifixai-ai/iFixAi | ASSESS / TRIAL-PATTERNS | pattern-only, optional CLI-adapter | Misalignment taxonomy + cross-judge contract + reproducibility manifest fill a gap COS eval lanes do not cover end-to-end; runtime is too young and self-disclaims uncalibrated thresholds | Add pattern reference; design optional CLI-adapter trial behind manifest |

### Source evidence

- Repository: <https://github.com/ifixai-ai/iFixAi>
- Homepage: <https://www.ifixai.ai/>
- License: Apache-2.0 (verified via GitHub API)
- Last commit at eval time: `2e56c4f` (2026-05-11)
- Latest release: `v1.0.0` (2026-05-04)
- README sections cited: Requirements, Quick Start, Standard and Full run modes, Scoring coverage, Calibration caveat
- COS comparables consulted: `skills/red-team`, `skills/redteam-harness`, `skills/security-red-team`, `skills/deepeval-integration`, `skills/promptfoo-integration`, `skills/ragas-integration`, `skills/plan-bug`, `skills/systematic-debugging`, `skills/auto-rollback`

### Unverified upstream items (flagged)

- Star/fork counts and CI results were read via GitHub API on 2026-05-11; not independently audited.
- The README claims OpenClaw and other in-the-wild adoptions in `docs/methodology.md`; not independently verified.
- arXiv/paper references: none observed in repo root; methodology lives in `docs/methodology.md` only.
- Content-addressed manifest claim: documented in `docs/reproducibility.md`; not reproduced locally in this eval.
