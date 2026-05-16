---
title: "iFixAi Deep Comparison — luum-agent-os eval/red-team lanes vs iFixAi misalignment diagnostic"
date: 2026-05-11
author: orchestrator
status: draft
source-repo: ".cognitive-os/external-source-cache/iFixAi/ (Apache-2.0, v1.0.0 / 2026-05-04, commit 2e56c4f)"
license_constraint: "Apache-2.0 — adoption allowed (with attribution), but pattern extraction is the preferred posture for evals (upstream-disclosed uncalibrated thresholds, open-core drift risk)."
parent_phase: "Phase 10 — iFixAi deep annex set (extends Phase 8 shallow eval)"
prior_artifacts:
  - docs/03-PoCs/research/repo-scout/deep/ifixai-ai__iFixAi-2026-05-11.md
  - docs/06-Daily/reports/external-tools-radar-ifixai-addendum-2026-05-11.md
classification: "ASSESS / TRIAL-PATTERNS — pattern-only adoption, optional CLI-adapter behind manifest."
---

# iFixAi Deep Comparison — COS eval/red-team lanes vs iFixAi misalignment diagnostic

> Phase 10 of the external-tools-radar. Follows the same shape as the `holaos-comparison-2026-05-10` artifact set: a thin parent and five focused annexes. Code-level evidence on the iFixAi side is mandatory — every claim references a `ifixai/<path>:<line>` from the clone at `.cognitive-os/external-source-cache/iFixAi/`.

---

## 1. Executive summary

iFixAi (`ifixai-ai/iFixAi`, Apache-2.0, 332★, v1.0.0 / 2026-05-04) is an **open-source diagnostic for AI misalignment**. It runs **32 versioned inspections** (`B01`–`B32`) grouped into five pillars — **FABRICATION / MANIPULATION / DECEPTION / UNPREDICTABILITY / OPACITY** — against any LLM exposed through one of 10 provider adapters (`mock`, `openai`, `openrouter`, `anthropic`, `gemini`, `azure`, `bedrock`, `huggingface`, `http`, `langchain` — `ifixai/providers/resolver.py:48`). The harness is fixture-driven (industry knowledge lives in user YAML, not test code — see `ifixai/fixtures/`), cross-judge by default (SUT is forbidden to grade itself unless the operator passes `--eval-mode self` — `ifixai/cli/orchestrator.py:76` and `ifixai/evaluation/manifest.py:103`), and emits a **content-addressed run manifest** (`ifixai/evaluation/manifest.py`, `ifixai/utils/fixture_digest.py`) so any run can be re-verified later by hash.

The original Phase 4 intake brief misclassified it as a "bug-fix agent". It is the **inverse**: a black-box misalignment evaluation harness. Comparisons against `/plan-bug`, `/systematic-debugging`, SDD apply-verify, and `/auto-rollback` are **NOT_COMPARABLE** (already recorded in the prior addendum). The substantive peer family is `red-team`, `redteam-harness`, `security-red-team`, `deepeval-integration`, `promptfoo-integration`, `ragas-integration`, and the aguara policy/standards crosswalk.

**Headline verdict.** iFixAi is the most polished open packaging we have seen of an *alignment-shaped* evaluation taxonomy (vs. the metric-shaped DeepEval / RAG-shaped Ragas / attack-shaped promptfoo families). Five primitives are independently extractable into COS eval lanes today, in **pattern-only** form. Direct code vendoring is legally permitted under Apache-2.0 but **not recommended**: (a) the upstream README self-discloses thresholds are *policy defaults, not empirically calibrated*; (b) there is a deliberate **open-core split** between the OSS repo and a proprietary `iMe` client build referenced in `ifixai/cli/_imecore_prompt.py:13` and `ifixai/reporting/scorecard.py:697`, with the README warning that fixtures, scoring policy, and UI differ in the client build; (c) v1.0.0 is ~1 week old at evaluation time so drift between OSS and proprietary fork should be expected.

---

## 2. License and reuse posture

- **License**: Apache-2.0 (`LICENSE`, `pyproject.toml:license = "Apache-2.0"`). Under our `[license-policy]` (RULES-COMPACT.md §10) this is ALLOW for both code adoption and pattern extraction.
- **Why pattern-only is preferred for COS eval lanes anyway**:
  - The repo itself states that the default thresholds (`B01=1.00`, `B08=0.95`, `pass=0.85`, mandatory-minimum cap=0.60 — see `ifixai/scoring/mandatory_minimums.py:6-13`) and category weights (FABRICATION 0.20, MANIPULATION 0.35, DECEPTION 0.15, UNPREDICTABILITY 0.15, OPACITY 0.15 — `ifixai/scoring/category_weights.py:4-10`) are **policy defaults, not empirically calibrated baselines** (README L36–L42). Adopting them as code embeds a not-yet-grounded numeric policy into our scoring contract.
  - The proprietary `iMe` client divergence (see Annex D) means future OSS commits may carry messaging or scoring tuned for a sales funnel rather than a neutral baseline; pattern extraction insulates COS from that drift.
  - Apache-2.0 NOTICE / attribution obligations are easier to discharge cleanly when the boundary is "we re-implemented their taxonomy under attribution" than when blended code crosses our lane boundaries.
- **What the addendum already settled**: `pattern-only` is the primary adoption kind. An optional `CLI-adapter` (invoke `ifixai run` from the `red-team` / `security-red-team` lane) is gated on a manifest row in `manifests/external-tools-adoption.yaml` and dedicated low-privilege provider keys.

---

## 3. The peer family — who else lives in this space

| Tool | License | Surface | Where it fits COS |
|---|---|---|---|
| **iFixAi** (this study) | Apache-2.0 | Alignment-shaped taxonomy (32 inspections, 5 pillars), judge-graded, cross-judge default | Misalignment lane — currently empty in COS |
| **DeepEval** (`confident-ai/deepeval`) | Apache-2.0 | 60+ metrics, pytest-style, agent trajectory eval | `skills/deepeval-integration/SKILL.md` — adopted as primary eval framework |
| **promptfoo** (`promptfoo/promptfoo`) | MIT | YAML-driven prompt regression + 50+ red-team plugins | `skills/promptfoo-integration/SKILL.md` — adopted for CI prompt regression + red team |
| **Ragas** (`explodinggradients/ragas`) | Apache-2.0 | 40+ RAG metrics + synthetic test generation | `skills/ragas-integration/SKILL.md` — adopted for RAG/memory eval |
| **COS `red-team` skill** (Promptfoo-driven) | MIT (skill) | Attack-driven prompt injection / jailbreak probes | `skills/red-team/SKILL.md` |
| **COS `security-red-team`** | — | Security-flavored agent probing | `skills/security-red-team/SKILL.md` |
| **COS `redteam-harness`** | — | Wraps the harness side of red-team | `skills/redteam-harness/SKILL.md` |
| **Aguara** | internal | 189-rule policy/standards crosswalk | `[aguara-integration]` per RULES-COMPACT §10 |

**Axis comparison (shape, not quality).**

- **iFixAi** is the only one with an **opinionated, named taxonomy of alignment failure modes** (B01..B32 → 5 pillars). DeepEval/Ragas are metric-shaped; promptfoo is attack-shaped; iFixAi is *behavior-shaped*.
- **iFixAi** is the only one in the peer family with a **cross-judge-by-default contract** in code (`ifixai/cli/orchestrator.py:76`, `JudgeConfig.providers` ensemble validator at `ifixai/judge/config.py:26-44`, and the explicit assertion in `ifixai/evaluation/manifest.py:103` that *"model_under_test must not appear in judge_models"*).
- **iFixAi** ships a **content-addressed run manifest** (per-run, SHA-256 over canonicalised YAML fixture + rubric hashes + test versions — `ifixai/evaluation/manifest.py`, `ifixai/utils/fixture_digest.py`). DeepEval/Ragas/promptfoo do not enforce this; COS has manifest doctrine at the *audit* layer (ADR-247, `manifests/postmortem-regression-audit.yaml`) but not yet at the *eval-run* layer.
- **iFixAi** carries a **regulatory crosswalk** out of the box (OWASP-LLM-Top-10, NIST-AI-RMF, ISO-42001, EU-AI-Act mapping files at `ifixai/mappings/*.yaml`). None of the other peers ships a comparable artifact.

These four are the four primitives most worth extracting (plus a fifth — threshold-policy-as-data — covered in Annex E).

---

## 4. Map of inspections vs COS reality (compact)

The full 32-inspection table with rubric / threshold / file-line refs lives in **Annex A**. The compact, pillar-rolled-up view:

| Pillar | Inspections | Category weight (default) | What it probes | Current COS surface |
|---|---|---:|---|---|
| **FABRICATION** Accuracy & Calibration | B01–B06 (6) | 0.20 | Tool auth leaks, non-LLM governance, audit-trail coverage, deterministic override, source provenance, explicit uncertainty | None packaged; partially overlaps `red-team` Promptfoo plugins |
| **MANIPULATION** Safety & Containment | B07–B09, B11–B13, B28, B30 (8) | 0.35 | Hallucination, privilege escalation, policy violation, controllability, prompt injection, plan traceability, RAG context integrity, malicious deployer rules | `red-team` (B12-shaped only); RAG-context absent; deployer rules absent |
| **DECEPTION** Hidden Strategy | B10, B14–B18 (6) | 0.15 | Evaluation-awareness drift, covert side tasks, long-horizon drift, silent failure, intra-system response consistency, goal stability | Entirely absent |
| **UNPREDICTABILITY** Stability & Consistency | B19–B23 (5) | 0.15 | Context accuracy, instruction adherence, cross-turn objective, decision reproducibility, policy version trace | Entirely absent |
| **OPACITY** Transparency & Auditability | B24–B27, B29, B31–B32 (7) | 0.15 | Risk scoring, regulatory readiness, rate-limit observability, session integrity, prompt sensitivity, escalation correctness, off-topic detection | Partial: rate limiting policy exists at infra layer; rest absent |

Sources: `ifixai/scoring/category_weights.py:4-10` (weights); `docs/inspection_categories.md` in the clone (canonical pillar map); individual `ifixai/inspections/b<NN>_*/runner.py` SPEC stanzas (per-inspection threshold/weight).

**Key COS gap surfaced**: the DECEPTION pillar is entirely uncovered. None of the existing COS eval skills probe evaluation-awareness drift, covert side tasks, long-horizon goal drift, silent failure, intra-system response consistency, or goal stability.

---

## 5. Annex pointer table

| Annex | Topic | File |
|---|---|---|
| **A** | Taxonomy & inspection surface — all 32 inspections enumerated with file:line, threshold, evidence shape, and the corresponding (or missing) COS surface | [`ifixai-annex-a-taxonomy-2026-05-11.md`](ifixai-annex-a-taxonomy-2026-05-11.md) |
| **B** | Cross-judge & ensemble — the cross-judge-by-default contract, single/ensemble/self/deterministic modes, conservative ensemble tie-break, per-judge attribution | [`ifixai-annex-b-cross-judge-2026-05-11.md`](ifixai-annex-b-cross-judge-2026-05-11.md) |
| **C** | Reproducibility manifest & fixtures — content-addressed manifest format, what is and is not hashed, CI replay, comparison to ADR-247 | [`ifixai-annex-c-manifest-fixtures-2026-05-11.md`](ifixai-annex-c-manifest-fixtures-2026-05-11.md) |
| **D** | Provider abstraction & open-core risk — 10-provider matrix, iMe client divergence, drift risk between OSS and proprietary fork | [`ifixai-annex-d-provider-imeisplit-2026-05-11.md`](ifixai-annex-d-provider-imeisplit-2026-05-11.md) |
| **E** | Extractable primitives — ranked list, integration cost into COS lanes, pattern-only vs vendor decision per primitive | [`ifixai-annex-e-primitives-2026-05-11.md`](ifixai-annex-e-primitives-2026-05-11.md) |

---

## 6. Verdict

- **Adoption posture**: confirm the existing addendum decision — **ASSESS / TRIAL-PATTERNS**, pattern-only as primary, optional CLI-adapter behind manifest.
- **Vendor or clean-room**: **clean-room re-implement** under attribution. Apache-2.0 permits direct code adoption, but the uncalibrated-threshold disclosure + iMe open-core split + 1-week-old v1.0.0 make a code-copy posture fragile. Clean-room owns the calibration and the messaging.
- **Sequencing**:
  1. Phase A (now): extract the 5 patterns into COS docs and SKILL.md stubs (no runtime install required).
  2. Phase B (gate on Phase A landing + a manifest row): wire an optional CLI-adapter behind `red-team` / `security-red-team` that shells out to `ifixai run` against a low-privilege test fixture.
  3. Phase C (only if Phase B value is empirically demonstrated): consider promoting the DECEPTION-pillar inspections into native COS skills, since that pillar is entirely uncovered today.

See Annex E §6 for the ranked primitive list, per-primitive integration cost, and the vendor/clean-room call for each.
