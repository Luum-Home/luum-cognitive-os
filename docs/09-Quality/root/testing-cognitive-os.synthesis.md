---
type: quality-synthesis
source: docs/09-Quality/root/testing-cognitive-os.md
provenance: "Research findings surveying open-source AI-agent testing frameworks (DeepEval, Promptfoo, SWE-bench, Arize Phoenix, LangSmith, CrewAI, Google ADK, NeMo Guardrails) and recommending a layered testing strategy for the Cognitive OS."
---

## What it is

A research/recommendation doc evaluating external open-source frameworks for testing AI agent systems (skills, rules, hooks, Engram memory, squads, cost tracking) and proposing a 4-layer testing strategy plus a prioritized tooling adoption plan.

## Key mechanics

- Seven testing dimensions identified: skill trigger accuracy, rule compliance, hook protocol correctness, memory persistence, multi-agent coordination, cost tracking accuracy, output quality.
- Framework survey with applicability ratings:
  - **DeepEval** (HIGH) — pytest-style LLM eval; `ToolCorrectnessMetric`, `PlanQualityMetric`, `PlanAdherenceMetric`, `HallucinationMetric`, `FaithfulnessMetric`, `AnswerRelevancyMetric`.
  - **Promptfoo** (HIGH) — declarative YAML test configs, red-teaming with 50+ vulnerability types, CI/CD ready.
  - **SWE-bench** (MEDIUM) — coding-agent benchmark, not SO-specific.
  - **Arize Phoenix** (HIGH) — tracing/path/convergence/session evaluation for multi-agent debugging.
  - **LangSmith** (MEDIUM) — LangChain-coupled; concepts transferable.
  - **CrewAI testing utilities** (MEDIUM) — LLM-as-judge, crew/squad pattern parallels.
  - **Google ADK Evaluation** (LOW-MEDIUM) — newer, less mature for custom architectures.
  - **NeMo Guardrails** (HIGH, already deployed) — input/output filtering, jailbreak detection, PII masking, topical rails.
- Recommended 4-layer strategy: Layer 1 deterministic unit tests (Jest/pytest + JSON schema validation), Layer 2 LLM evaluation (DeepEval + Promptfoo), Layer 3 integration/E2E (Arize Phoenix + custom harness), Layer 4 continuous production monitoring (Langfuse + NeMo Guardrails).
- Adoption priority: must-have = Promptfoo + DeepEval; nice-to-have = Arize Phoenix + SWE-bench; already deployed = Langfuse + NeMo Guardrails.
- 5-phase implementation roadmap: Phase 1 Promptfoo for constitutional gates, Phase 2 DeepEval skill-trigger tests, Phase 3 marked **DONE** (custom Engram persistence harness — `tests/integration/test_engram_persistence.py`, 19 real tests via `real_engram` fixture), Phase 4 hook protocol JSON-schema tests, Phase 5 Arize Phoenix for multi-agent debugging.
- Key limitations flagged: LLM non-determinism requires statistical assertions (pass rate thresholds, not exact match); eval cost; eval speed; model-drift requiring version pinning; and the "evaluation of evaluators" problem (LLM-as-judge has its own failure modes).

## Relations & where used

- Cross-references `constitutional-gates.md` (Gate 1-7) and the SO's Langfuse/NeMo Guardrails deployments.
- Overlaps conceptually with `testing-cognitive-os-suite.md` (which documents the actually-built `.cognitive-os/tests/` Layer 3 promptfoo integration) and `testing.md` (the pytest suite where DeepEval/RAGAS integration tests already exist per `test_eval_frameworks.py`).

## Status / caveats

This is a research/recommendation document, not a status report — most content is framework evaluation and proposed strategy rather than confirmed implementation. Only Phase 3 is explicitly marked DONE within the file; Phases 1, 2, 4, 5 are not marked complete here (cross-check against `testing.md` and `testing-cognitive-os-suite.md`, which show DeepEval/RAGAS and promptfoo integration do exist elsewhere in the repo, suggesting this doc may be stale relative to current implementation state — flagged, not resolved).
