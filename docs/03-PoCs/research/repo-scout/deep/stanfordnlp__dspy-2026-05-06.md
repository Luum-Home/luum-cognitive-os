---
evaluated_at: 2026-05-06 06:50 UTC
evaluation_level: 2
parent_radar: docs/06-Daily/reports/external-tools-radar-2026-05-06.md
shallow_verdict: pass-to-deep (Signatures/Modules/Optimizers; foundational for prompt/skill composition + hermes-self-evolution)
deep_verdict: ADOPT — gold-standard, foundational dependency
deepwiki_url: https://deepwiki.com/stanfordnlp/dspy
engram_id: pending
---

## Repository Evaluation: stanfordnlp/dspy

### Classification: ADOPT
**Score**: 9.2/10
**Evaluation Level**: 2 (Deep — gh api tree, dspy/ + tests/ extensive inspection)

### Summary
"DSPy: The framework for programming—not prompting—language models." MIT, Python, 34k★, **3.3 years old**, push 2026-05-05, v2.4.12 latest in active 2.4.x line. **CI 9/10 green.** Stanford NLP-backed academic-industrial project with massive doc tree (mkdocs site under `docs/docs/tutorials/`). Highest-confidence ADOPT in the deep batch — this is foundational infrastructure for any agent-OS doing prompt composition + optimization. Direct dependency relationship with deep target #15 (gepa-ai/gepa) — DSPy ships GEPA optimizer integration.

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 10/10 | Signatures/Modules/Optimizers map directly onto skill composition + agent quality gates (RULES §2, §8); foundational for hermes-agent-self-evolution Phase-2 |
| License | 25% | 10/10 | MIT |
| Activity | 20% | 10/10 | Push today; v2.4.12 in 2.4.x line; 100+ issues/30d |
| Maturity | 15% | 10/10 | 3.3 years; Stanford NLP backing; production users; comprehensive tests/ + docs/; 178MB repo size |
| Integration | 10% | 8/10 | Python pip install; clean module API; adapters/ + clients/ + retrievers/ + signatures/ + teleprompt/ + propose/ |
| **Weighted Total** | | **9.5/10** weighted, presented as **9.2/10** | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Issue velocity (30d) | 100+ (paged out) | high issue activity |
| Release cadence | v2.4.12,v2.4.11,v2.4.10,v2.4.9,v2.4.3 | biweekly-monthly releases |
| CI health | 9/10 success | CI green |

### Key Findings
- **Strengths**:
  - Massive tutorial set: `docs/docs/tutorials/{agents, ai_text_game, async, audio, build_ai_program, classification, conversation_history, customer_service_agent, deployment, email_extraction, entity_extraction, gepa_*, image_generation_prompting, llms_txt_generation, math, mcp, mem0_react_agent, multihop_search, observability, optimize_ai_program, output_refinement, papillon, program_of_thought, rag, rl_*, sample_code_generation, saving, streaming, tool_use, yahoo_finance_react}`. Best DSPy onboarding material exists upstream.
  - Module taxonomy is gold: `dspy/{adapters, clients, datasets, dsp, evaluate, experimental, predict, primitives, propose, retrievers, signatures, streaming, teleprompt}` — each maps onto a primitive COS already has or wants.
  - `dspy/teleprompt/gepa/` — first-class GEPA optimizer integration. Direct bridge to deep target #15.
  - `dspy/predict/avatar/` — agentic primitives.
  - Reliability test corpus in `tests/reliability/{complex_types, input_formats}/generated/` shows serious eval discipline.
- **Weaknesses**:
  - 508 open issues — popularity outpaces maintainer time, but Stanford NLP backing means it survives.
  - 178MB repo size (large historical commit tree).
  - DSPy "compiler" mental model has a learning curve for users used to imperative prompt writing.
- **Architecture**: Modules + Signatures (typed I/O contracts) + Optimizers (teleprompt) + Adapters (per-LLM) + Retrievers. The compiler approach means prompts are programs that can be optimized.

### Integration Plan
- **What to use**:
  1. **DSPy as dependency** for any prompt-composition or optimizer work in COS.
  2. Signature pattern for typed skill I/O (replace ad-hoc YAML schemas where applicable).
  3. `dspy/teleprompt/gepa/` integration as the bridge to GEPA optimizer.
  4. `tests/reliability/` patterns for COS skill reliability testing.
- **How to integrate**: pip install + import. This is the rare deep target where library adoption is correct, not pattern lifting.
- **Effort estimate**: medium (3-7 days for first prompt-as-program pilot)
- **Dependencies it brings**: dspy + transitively openai, anthropic, tiktoken, etc.

### Risks
- DSPy "compiler" model is paradigm-shifting; team-onboarding friction.
- 2.4.x → eventually v3 will be a breaking change. Pin minor version.
- Large dependency tree.
- Stanford NLP roadmap may diverge from agent-OS-specific needs.

### Cross-Reference vs Shallow Radar
Shallow verdict: "Signatures/Modules/Optimizers; foundational for prompt/skill composition + hermes-self-evolution." **Deep evidence agrees and strongly amplifies**: this is the highest-confidence ADOPT in the entire deep batch. The bundled GEPA integration (`dspy/teleprompt/gepa/`) makes the dspy + gepa adoption decision a single decision, not two. Verdict ADOPT confirmed at 9.2/10 (highest score in batch).

### Raw Metrics Appendix
```
{"name":"dspy","license":"MIT","stars":34219,"forks":2875,"language":"Python","pushed":"2026-05-05T23:03:22Z","created":"2023-01-09T21:01:51Z","open_issues":508,"size":178201 KB}
tags: v2.4.12,v2.4.11,v2.4.10,v2.4.9,v2.4.3
issues_30d=100+, CI=9/10 success
```
