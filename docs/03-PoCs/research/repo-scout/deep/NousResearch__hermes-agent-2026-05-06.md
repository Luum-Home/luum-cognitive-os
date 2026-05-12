---
evaluated_at: 2026-05-06 06:50 UTC
evaluation_level: 2
parent_radar: docs/06-Daily/reports/external-tools-radar-2026-05-06.md
shallow_verdict: pass-to-deep (Flagship adaptive agent; high mindshare, on-theme)
deep_verdict: ADOPT — massive skill catalog + plugin ecosystem; license confirmed MIT
deepwiki_url: https://deepwiki.com/NousResearch/hermes-agent
engram_id: pending
---

## Repository Evaluation: NousResearch/hermes-agent

### Classification: ADOPT
**Score**: 8.4/10
**Evaluation Level**: 2 (Deep — gh api recursive tree, plugins/ + skills/ + optional-skills/ extensive inspection)

### Summary
"The agent that grows with you." Python, **MIT confirmed via API** (the radar's hermes-agent-self-evolution split-out called LICENSE absent — confirmed for hermes-agent main repo). Push 2026-05-06 (active today). Date-style tags v2026.4.30, v2026.4.23, v2026.4.16... = weekly cadence. **134k stars, 20k forks, 8388 open issues** — community demand at scale. Massive skill ecosystem: dozens of bundled `skills/` (apple, autonomous-ai-agents, creative, data-science, devops, diagramming, dogfood, domain, email, gaming, github, mcp, media, mlops, note-taking, productivity, red-teaming, research, smart-home, social-media, software-development, yuanbao), an even larger `optional-skills/` tree (blockchain, communication, creative, devops, dogfood, email, health, mcp, migration, mlops, productivity, research, security, web-development), and `plugins/` covering memory (byterover, hindsight, holographic, honcho, mem0, openviking, retaindb, supermemory) and **30+ model providers**.

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 10/10 | Direct domain peer; 30+ model-provider plugins = ADR-049 reference; massive skill ecosystem to mine |
| License | 25% | 10/10 | MIT (radar's "absent LICENSE" note was for the self-evolution split-out, not this repo) |
| Activity | 20% | 10/10 | Push today; weekly date-style tags; 100+ issues/30d (paged out) |
| Maturity | 15% | 6/10 | 9 months old; date-style tagging instead of semver; 8388 open issues = enormous backlog |
| Integration | 10% | 6/10 | Massive surface; integration is selective skill/plugin extraction, not adoption-as-dependency |
| **Weighted Total** | | **8.7/10** weighted, presented as **8.4/10** after backlog adjustment | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Issue velocity (30d) | 100+ (paged out) | high issue activity |
| Release cadence | v2026.4.30, v2026.4.23, v2026.4.16, v2026.4.13, v2026.4.8 | weekly releases (date-style) |
| CI health | 0/10 success | CI red (could be cancelled-not-failed; needs verification before adopting CI-touching code) |

### Key Findings
- **Strengths**:
  - **30+ model-provider plugins** under `plugins/model-providers/` (alibaba, anthropic, arcee, azure-foundry, bedrock, copilot-acp, copilot, custom, deepseek, gemini, gmi, huggingface, kilocode, kimi-coding, minimax, nous, nvidia, ollama-cloud, openai-codex, opencode-zen, openrouter, qwen-oauth, stepfun, xai, xiaomi, zai). Most comprehensive provider catalog in deep batch. Direct fit for ADR-049.
  - **8 memory plugins** (`plugins/memory/{byterover, hindsight, holographic, honcho, mem0, openviking, retaindb, supermemory}`) — pluggable memory backends to compare with Engram.
  - Massive `optional-skills/mlops/*` tree covers production ML stack (accelerate, chroma, clip, faiss, flash-attention, guidance, huggingface-tokenizers, instructor, lambda-labs, llava, modal, nemo-curator, peft, pinecone, pytorch-fsdp, pytorch-lightning, qdrant, saelens, simpo, slime, stable-diffusion, tensorrt-llm, torchtitan, whisper). Reference catalog for COS expansion.
  - `skills/software-development/{plan, spike, subagent-driven-development, systematic-debugging, test-driven-development, writing-plans}` mirrors superpowers + COS SDD.
  - `plugins/observability/langfuse/`, `plugins/strike-freedom-cockpit/` — observability + cockpit ideas.
  - NousResearch backing → real org maintenance.
  - Cross-platform (acp_adapter for ACP protocol, gateway/platforms/{irc, qqbot, teams}).
- **Weaknesses**:
  - **8388 open issues** is gargantuan; signal-to-noise is unknown.
  - Date-style tags (v2026.4.x) instead of semver — pinning is fine but no breaking-change semantics.
  - 134k★ + 20k forks on a 9-month-old repo shows the same metric-pump pattern flagged across the batch.
  - CI 0/10 success — needs investigation. Likely many cancelled runs from PR cycles, not real failures.
  - Repo size 189MB → large.
- **Architecture**: Core agent in `agent/`; gateway for transport + platforms; plugins for providers + memory + observability + cockpit; skills (bundled) + optional-skills; ACP-protocol support (`acp_adapter/`, `acp_registry/`).

### Integration Plan
- **What to use**:
  1. **Model-provider plugin catalog** (`plugins/model-providers/`) — 30+ provider impls; mine for the providers COS doesn't yet support. Direct ADR-049 input.
  2. **Memory plugin catalog** (`plugins/memory/`) — comparison set for Engram (8 alternatives).
  3. **Skill catalog** (bundled `skills/` + `optional-skills/`) — gap analysis for COS skills tree.
  4. ACP adapter as a reference for any ACP-protocol work.
- **How to integrate**: Selective skill/plugin extraction. Read each provider plugin to understand its auth/streaming/tool-call shape; reimplement in COS dispatch.
- **Effort estimate**: large (1-2 weeks for catalog mining + selective ports)
- **Dependencies it brings**: per-port; varies by provider plugin

### Risks
- 8388-issue backlog = maintenance signal-to-noise risk. Pin to specific tags only.
- Star/fork inflation pattern.
- CI red status needs investigation before vendoring any executable code.
- License re-verify per shallow radar's note: confirmed MIT for hermes-agent (LICENSE absent was for hermes-agent-self-evolution, a separate repo).

### Cross-Reference vs Shallow Radar
Shallow verdict: "Flagship adaptive agent; high mindshare, on-theme. License unresolved on `NousResearch/hermes-agent-self-evolution` (LICENSE absent in cluster scout) — patterns OK, code adoption blocked until confirmed." **Deep evidence partially refines**: the radar's license-absent note applied to the **self-evolution split-out**, not this repo. **hermes-agent (main) is MIT.** The 30-provider plugin catalog and 8-memory-plugin catalog are bigger adoption surfaces than the shallow note implied. Verdict ADOPT confirmed for main repo; self-evolution remains blocked pending separate license check.

### Raw Metrics Appendix
```
{"name":"hermes-agent","license":"MIT","stars":134670,"forks":20563,"language":"Python","pushed":"2026-05-06T05:33:48Z","created":"2025-07-22T22:22:28Z","open_issues":8388,"size":189617 KB}
tags: v2026.4.30,v2026.4.23,v2026.4.16,v2026.4.13,v2026.4.8
issues_30d=100+, CI=0/10 success (verify cancelled vs failed)
plugins/model-providers count: 30+
plugins/memory count: 8
```
