---
cluster: observability-eval
date: 2026-05-06
phase: shallow
input_count: 20
pass_count: 13
reject_count: 7
phase2_candidates: 9
---

# Cluster: observability-eval — Shallow Triage (2026-05-06)

Theme: LLM/agent observability, evaluation frameworks, red-teaming, and agent benchmarks (SWE-bench, AgentBench, OSWorld, AndroidWorld, etc.).

Note: input file listed 21 lines but `Arize-ai/phoenix` and `arize-ai/phoenix` are the same repo — 20 unique.

## Triage

### Arize-ai/phoenix
- URL: https://github.com/Arize-ai/phoenix
- License: **Elastic-2.0** (LICENSE file; GitHub reports NOASSERTION)
- Stars: 9,532
- Last commit: 2026-05-06
- Primary language: Python
- Purpose: AI observability and evaluation (tracing, evals, prompt mgmt).
- Verdict: **REJECT**
- Rationale: Elastic-2.0 explicitly excluded by constraints (non-commercial-use limitations on hosted SaaS).

### ClickHouse/ClickHouse
- URL: https://github.com/ClickHouse/ClickHouse
- License: Apache-2.0
- Stars: 47,220
- Last commit: 2026-05-06
- Primary language: C++
- Purpose: Real-time columnar OLAP analytics database.
- Verdict: PASS
- Rationale: Permissive license, active. Out-of-cluster fit (storage, not eval) — useful as trace/metrics backend for agent telemetry.

### GAIR-NLP/AgencyBench
- URL: https://github.com/GAIR-NLP/AgencyBench
- License: MIT
- Stars: 80
- Last commit: 2026-01-23
- Primary language: Python
- Purpose: ACL2026 benchmark for autonomous agents in 1M-token real-world contexts.
- Verdict: PASS
- Rationale: Clean MIT, recent, novel 1M-context agent benchmark relevant to long-horizon agents.

### NVIDIA/garak
- URL: https://github.com/NVIDIA/garak
- License: Apache-2.0
- Stars: 7,728
- Last commit: 2026-05-05
- Primary language: Python
- Purpose: LLM vulnerability scanner / red-teaming probes.
- Verdict: PASS
- Rationale: Permissive, very active, strong fit for security-eval lane (existing redteam-harness skill).

### SWE-bench/SWE-bench
- URL: https://github.com/SWE-bench/SWE-bench
- License: MIT
- Stars: 4,847
- Last commit: 2026-04-01
- Primary language: Python
- Purpose: Benchmark for LLMs resolving real-world GitHub issues.
- Verdict: PASS
- Rationale: Industry-standard SWE eval, MIT, recent.

### SWE-bench/sb-cli
- URL: https://github.com/SWE-bench/sb-cli
- License: MIT
- Stars: 64
- Last commit: 2025-08-14
- Primary language: Python
- Purpose: CLI to run SWE-bench evaluations remotely.
- Verdict: PASS
- Rationale: Companion to SWE-bench, MIT. Stale-ish (8 months) but useful operational primitive.

### THUDM/AgentBench
- URL: https://github.com/THUDM/AgentBench
- License: Apache-2.0
- Stars: 3,389
- Last commit: 2026-02-08
- Primary language: Python
- Purpose: ICLR'24 benchmark evaluating LLMs as agents across 8 environments.
- Verdict: PASS
- Rationale: Apache-2.0, established multi-env agent benchmark.

### Vexp-ai/vexp-swe-bench
- URL: https://github.com/Vexp-ai/vexp-swe-bench
- License: MIT
- Stars: 8
- Last commit: 2026-05-02
- Primary language: Shell
- Purpose: Open benchmark comparing AI coding agents on SWE-bench Verified.
- Verdict: REJECT
- Rationale: Tiny adoption (8 stars), redundant with upstream SWE-bench/sb-cli.

### augmentcode/augment-swebench-agent
- URL: https://github.com/augmentcode/augment-swebench-agent
- License: **MIT** (LICENSE file; GitHub reports NOASSERTION due to third-party notices appendix)
- Stars: 872
- Last commit: 2025-06-09
- Primary language: Python
- Purpose: Reference SWE-bench Verified agent implementation by Augment.
- Verdict: PASS
- Rationale: Clean MIT, well-known reference agent — useful for SWE eval comparison and prompt patterns. Note: 11-month stale.

### benchflow-ai/skillsbench
- URL: https://github.com/benchflow-ai/skillsbench
- License: Apache-2.0
- Stars: 1,112
- Last commit: 2026-05-05
- Primary language: PDDL
- Purpose: Evaluates how well agent skills work and how effective agents are at using them.
- Verdict: PASS
- Rationale: Direct relevance to COS skill ecosystem (skill-quality evaluation). Apache-2.0, active.

### comet-ml/opik
- URL: https://github.com/comet-ml/opik
- License: Apache-2.0
- Stars: 19,216
- Last commit: 2026-05-06
- Primary language: Python
- Purpose: LLM/RAG/agent debug, eval, and monitor with tracing and dashboards.
- Verdict: PASS
- Rationale: Apache-2.0, very active, large adoption — clean alternative to Phoenix/Langfuse for observability lane.

### confident-ai/deepeval
- URL: https://github.com/confident-ai/deepeval
- License: Apache-2.0
- Stars: 15,168
- Last commit: 2026-05-05
- Primary language: Python
- Purpose: LLM evaluation framework (G-Eval, RAG metrics, red-team, hallucination).
- Verdict: PASS
- Rationale: Apache-2.0, deepeval-integration skill already exists — strong fit. Active.

### cxcscmu/General-AgentBench
- URL: https://github.com/cxcscmu/General-AgentBench
- License: MIT
- Stars: 18
- Last commit: 2026-04-14
- Primary language: Python
- Purpose: Benchmark for test-time scaling of general LLM agents.
- Verdict: REJECT
- Rationale: Very low adoption (18 stars), niche; AgentBench/AgencyBench cover similar ground better.

### explodinggradients/ragas
- URL: https://github.com/explodinggradients/ragas (redirects to vibrantlabsai/ragas)
- License: Apache-2.0
- Stars: 13,777
- Last commit: 2026-02-24
- Primary language: Python
- Purpose: RAG evaluation framework (faithfulness, context precision, answer relevancy).
- Verdict: PASS
- Rationale: Apache-2.0, ragas-integration skill exists. Note: org rename to vibrantlabsai — verify continuity in Phase 2.

### google-research/android_world
- URL: https://github.com/google-research/android_world
- License: Apache-2.0
- Stars: 753
- Last commit: 2026-04-09
- Primary language: Python
- Purpose: Environment + benchmark for autonomous mobile agents on Android.
- Verdict: REJECT
- Rationale: Out of COS scope (mobile UI agents); no near-term integration path.

### langchain-ai/agentevals
- URL: https://github.com/langchain-ai/agentevals
- License: MIT
- Stars: 573
- Last commit: 2026-04-21
- Primary language: Python
- Purpose: Pre-built evaluators for agent trajectories (tool-use, planning).
- Verdict: PASS
- Rationale: MIT, lightweight, directly relevant to agent-trajectory verify/improve loop.

### langfuse/langfuse
- URL: https://github.com/langfuse/langfuse
- License: **Mixed — MIT core + proprietary EE** (NOASSERTION, LICENSE explicitly mixed)
- Stars: 26,619
- Last commit: 2026-05-05
- Primary language: TypeScript
- Purpose: LLM observability platform (tracing, metrics, evals, prompt mgmt).
- Verdict: REJECT
- Rationale: Mixed-license per constraints (clean-license preference). Use Opik or Phoenix-replacement instead.

### openai/procgen
- URL: https://github.com/openai/procgen
- License: MIT
- Stars: 1,155
- Last commit: 2026-03-27
- Primary language: C++
- Purpose: Procedurally-generated Gym RL game environments.
- Verdict: REJECT
- Rationale: RL-only; out of LLM/agent eval scope for COS.

### promptfoo/promptfoo
- URL: https://github.com/promptfoo/promptfoo
- License: MIT
- Stars: 20,884
- Last commit: 2026-05-06
- Primary language: TypeScript
- Purpose: Prompt/agent/RAG testing, red-teaming, vuln scanning, multi-model compare.
- Verdict: PASS
- Rationale: MIT, very active, promptfoo-integration skill exists. Top-tier eval tool.

### xlang-ai/OSWorld
- URL: https://github.com/xlang-ai/OSWorld
- License: Apache-2.0
- Stars: 2,822
- Last commit: 2026-05-01
- Primary language: Python
- Purpose: NeurIPS'24 benchmark for multimodal agents in real OS/desktop environments.
- Verdict: REJECT
- Rationale: Multimodal desktop GUI agents — out of current COS scope (terminal/code agents focus).

## Phase 2 Candidates

Recommend deep-dive (reverse-engineer / repo-forensics) on:

1. **comet-ml/opik** — primary candidate to fill observability gap left by Phoenix/Langfuse rejection.
2. **NVIDIA/garak** — security-eval integration via redteam-harness; Apache-2.0 patterns adoptable.
3. **confident-ai/deepeval** — extend existing deepeval-integration skill.
4. **explodinggradients/ragas** — verify org migration (vibrantlabsai); update ragas-integration skill.
5. **promptfoo/promptfoo** — already integrated; assess upstream changes for skill refresh.
6. **SWE-bench/SWE-bench** + **augmentcode/augment-swebench-agent** — pair eval harness for COS coding-agent benchmarking.
7. **benchflow-ai/skillsbench** — direct relevance to COS skill-quality KPI; novel angle.
8. **langchain-ai/agentevals** — lightweight trajectory eval; complements verify/improve loop.
9. **THUDM/AgentBench** — broad multi-env agent benchmark; lower priority but established.

Counts: 20 unique input (21 listed, 1 case-duplicate) = 13 PASS + 7 REJECT (sum verified).
