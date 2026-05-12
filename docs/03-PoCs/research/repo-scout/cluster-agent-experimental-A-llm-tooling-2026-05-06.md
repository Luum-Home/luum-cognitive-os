---
cluster: agent-experimental-A-llm-tooling
date: 2026-05-06
phase: shallow
total_repos: 8
phase_2_candidates: 3
monitor: 3
rejected: 2
license_blocked: 2
---

# Cluster: agent-experimental-A-llm-tooling — Shallow Scout

Theme: LLM tooling + dspy + simonw/llm + gptme + open-interpreter + raw model releases (MiniMax-M2).

## Repos

### stanfordnlp/dspy
- URL: https://github.com/stanfordnlp/dspy
- License: MIT
- Stars: 34,216
- Last commit: 2026-05-05
- Primary language: Python
- Purpose: Framework for programming (not prompting) language models — declarative modules, signatures, optimizers.
- Verdict: **Phase 2 candidate**
- Rationale: High-leverage primitive surface (Signatures, Modules, Optimizers, Predict/CoT/ReAct). MIT-clean. Active. Directly relevant to skill/prompt composition + agent quality gates (RULES §2, §8). Worth deep reverse-engineer for primitive harvest.

### simonw/llm
- URL: https://github.com/simonw/llm
- License: Apache-2.0
- Stars: 11,789
- Last commit: 2026-05-06
- Primary language: Python
- Purpose: CLI + Python library for accessing LLMs from many providers via a plugin architecture.
- Verdict: **Phase 2 candidate**
- Rationale: Apache-2.0 clean. Plugin architecture + provider abstraction is directly applicable to `lib/dispatch.py` LLM routing (RULES §4, ADR-049). Mature, broad provider coverage. Reverse-engineer for plugin pattern + key/credential model.

### gptme/gptme
- URL: https://github.com/gptme/gptme
- License: MIT
- Stars: 4,291
- Last commit: 2026-05-05
- Primary language: Python
- Purpose: Terminal-resident agent with local tools (shell, code, browse, files), persistent.
- Verdict: **Phase 2 candidate**
- Rationale: MIT-clean. Persistent terminal-agent loop overlaps with COS persistent-agent skill — patterns for tool-loop, conversation memory, local sandboxing worth harvesting. Active.

### TheR1D/shell_gpt
- URL: https://github.com/TheR1D/shell_gpt
- License: MIT
- Stars: 12,045
- Last commit: 2026-05-06
- Primary language: Python
- Purpose: Shell-focused command-line productivity tool powered by LLMs.
- Verdict: **Monitor**
- Rationale: MIT-clean and active, but primitive surface heavily overlaps simonw/llm (CLI + provider calls). Lower novelty for our needs. Watch for unique shell-integration patterns; defer deep dive.

### sigoden/aichat
- URL: https://github.com/sigoden/aichat
- License: Apache-2.0
- Stars: 9,944
- Last commit: 2026-02-23
- Primary language: Rust
- Purpose: All-in-one LLM CLI — REPL, shell assistant, RAG, agents/tools across many providers.
- Verdict: **Monitor**
- Rationale: Apache-2.0 clean and feature-rich, but Rust adds porting/translation cost vs Python alternatives. Slower commit cadence. Monitor for RAG + agent-tool patterns; not Phase 2 priority.

### MiniMax-AI/MiniMax-M2
- URL: https://github.com/MiniMax-AI/MiniMax-M2
- License: MIT (LICENSE file; GitHub API reports NOASSERTION)
- Stars: 2,590
- Last commit: 2025-11-13
- Primary language: (model weights repo, no primary code language)
- Purpose: Raw model release — MiniMax-M2 weights/configs targeting coding + agentic workflows.
- Verdict: **Monitor (raw weights, not primitive)**
- Rationale: Per cluster rules, raw model releases are monitor-only. No tooling/primitive surface to extract; track for routing eligibility in `lib/dispatch.py` if benchmarks justify.

### openinterpreter/open-interpreter
- URL: https://github.com/openinterpreter/open-interpreter
- License: AGPL-3.0
- Stars: 63,398
- Last commit: 2026-05-04
- Primary language: Python
- Purpose: Natural-language interface for computers — execute code locally via LLM.
- Verdict: **Rejected (license)**
- Rationale: AGPL-3.0 is on the BLOCK list (RULES §10 license-policy). Cannot adopt code or copy patterns directly — clean-room only if a primitive becomes critical, which is not the case given gptme covers similar ground under MIT.

### Pythagora-io/gpt-pilot
- URL: https://github.com/Pythagora-io/gpt-pilot
- License: FSL-1.1-MIT (Functional Source License)
- Stars: 33,770
- Last commit: 2026-04-17
- Primary language: Python
- Purpose: Multi-agent system that builds production apps from spec ("first real AI developer").
- Verdict: **Rejected (license)**
- Rationale: FSL is on the BLOCK list (non-commercial / competitive-use restriction; converts to MIT only after 2 years). Cannot adopt. Patterns may be re-derived from MIT/Apache alternatives if needed.

## Phase 2 candidates

1. **stanfordnlp/dspy** — primitive-harvest target: Signatures, Modules, Optimizers; map to skill composition + prompt quality gates.
2. **simonw/llm** — primitive-harvest target: plugin/provider architecture; map to `lib/dispatch.py` and provider abstraction.
3. **gptme/gptme** — primitive-harvest target: terminal-agent tool-loop, conversation persistence; map to COS persistent-agent + conversation-memory skills.
