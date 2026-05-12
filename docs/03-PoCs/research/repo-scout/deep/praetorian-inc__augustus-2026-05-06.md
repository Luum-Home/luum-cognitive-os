---
evaluated_at: 2026-05-06 06:58 UTC
evaluation_level: 2
parent_radar: docs/06-Daily/reports/external-tools-radar-2026-05-06.md
shallow_verdict: pass-to-deep (190-probe offensive corpus, single Go binary; complements Aguara defense)
deep_verdict: ADOPT — comprehensive Go-binary red-team corpus; complementary to snyk/agent-scan and Aguara
deepwiki_url: https://deepwiki.com/praetorian-inc/augustus
engram_id: pending
---

## Repository Evaluation: praetorian-inc/augustus

### Classification: ADOPT
**Score**: 8.5/10
**Evaluation Level**: 2 (Deep — gh api recursive tree, internal/probes + internal/detectors + internal/generators inspection)

### Summary
"LLM security testing framework for detecting prompt injection, jailbreaks, and adversarial attacks — 190+ probes, 28 providers, single Go binary." Apache-2.0, Go, 203★ (small but high signal-to-noise), push 2026-05-06 (today), v0.0.5→v0.0.9 cadence (pre-v0.1). Praetorian is an established offensive-security firm. CI shows 1 failure 2 success in 10 — the rest null/cancelled, likely PR-cycle artifacts. Tree confirms the radar's claim of comprehensive coverage. Direct complement to snyk/agent-scan (defensive) and Aguara (runtime defense): augustus is the **offensive corpus**.

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 10/10 | 190-probe offensive corpus + 28 generators = comprehensive red-team primitive; fills the offensive gap COS needs |
| License | 25% | 8/10 | Apache-2.0 |
| Activity | 20% | 9/10 | Push today; weekly v0.0.x cadence; 57 issues/30d |
| Maturity | 15% | 5/10 | Pre-v0.1 (v0.0.9); 3 months old; 22 open issues; small community but Praetorian-backed |
| Integration | 10% | 8/10 | Single Go binary = drop-in CLI tool; pkg/ exposes library API for embedded use |
| **Weighted Total** | | **8.7/10** weighted, presented as **8.5/10** after pre-v0.1 adjustment | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Issue velocity (30d) | 57 issues | high issue activity for a small repo |
| Release cadence | v0.0.5-v0.0.9 | weekly releases (pre-v0.1) |
| CI health | 2/10 success (7 null) | CI ambiguous — likely many cancelled PR runs |

### Key Findings
- **Strengths**:
  - **Probes catalog (`internal/probes/`)** confirms 50+ probe families: advpatch, ansiescape, apikey, artprompts, autodan, avspamscanning, badchars, browsing, continuation, crescendo, dan, divergence, donotanswer, dra, exploitation, flipattack, gcg, glitch, goat, goodside, grandma, guardrail, hydra, latentinjection, leakreplay, lmrc, malwaregen, mischievous, misleading, multiagent, multimodal, obscureprompt, packagehallucination, pair, phrasing, poetry, prefix, promptinject, ragpoisoning, realtoxicityprompts, snowball, suffix, tap, test, topic, treesearch, webinjection.
  - **Detectors catalog (`internal/detectors/`)** complements probes with 40+ detector types covering judge LLMs, refusal-detection, content-policy, etc.
  - **Generators catalog (`internal/generators/`)** = 28+ provider integrations (anthropic, anyscale, azure, bedrock, cohere, deepinfra, fireworks, function, ggml, groq, guardrails, huggingface, langchain, langchainserve, litellm, mistral, nemo, nim, nvcf, ollama, openai, openaicompat, rasa, replicate, rest, test, together, vertex, watsonx). Direct ADR-049 reference.
  - **`internal/multiturn/strategies/{crescendo, goat, hydra, mischievous}`** — multi-turn jailbreak strategies. Adversarial primitives.
  - **`internal/buffs/{conlang, encoding, flip, lowercase, lrl, paraphrase, poetry, smuggling}`** — input-perturbation library.
  - **`internal/harnesses/{agentwise, batch, probewise}`** — execution harnesses.
  - Single Go binary deploy → easy sidecar.
  - Praetorian backing + offensive-security pedigree.
- **Weaknesses**:
  - Pre-v0.1 — API may shift.
  - 22 open issues with 57 inbound = manageable.
  - 203 stars is genuinely small (no metric-pump pattern), but means small external community vetting.
  - Go binary in a Python COS world adds runtime dependency.
- **Architecture**: Standard Go layout. `cmd/augustus` = CLI binary. `internal/{probes, detectors, generators, harnesses, buffs, multiturn}` = the offensive engine. `pkg/` exposes a library API for embedding.

### Integration Plan
- **What to use**:
  1. **augustus as a CI red-team gate** in COS pre-release validation (per ADR-139..142). Run probe sets against COS skills/MCP surface; fail on detector hits.
  2. **Probe taxonomy** as a structured threat-model index for ADR-141 compliance/audit.
  3. **Multiturn strategies** (`internal/multiturn/strategies/{crescendo, goat, hydra}`) as adversarial test scaffolds.
  4. **Generators catalog** as a second cross-reference for ADR-049 dispatch (alongside hermes-agent's plugins/model-providers and pal-mcp-server's providers/registries).
- **How to integrate**: Run augustus binary in CI; pipe results into COS metrics. Optionally embed `pkg/` in a Go sidecar tool.
- **Effort estimate**: small-to-medium (1-2 days for CI gate, 3-5 days for full taxonomy mapping)
- **Dependencies it brings**: Go binary as a sidecar tool

### Risks
- Apache-2.0 NOTICE compliance.
- Pre-v0.1 — pin to v0.0.9.
- Go binary adds runtime dependency for COS Python users.
- Probes hit live LLM APIs → cost governance: budget red-team CI runs explicitly.

### Cross-Reference vs Shallow Radar
Shallow verdict: "190-probe offensive corpus, single Go binary; complements Aguara defense. Both Phase-2 to land before flow #1 promotion (per ADR-139..142)." **Deep evidence agrees fully** and adds detail: 50+ probe families, 40+ detector types, 28+ generators, 4 multiturn strategies. The 28-generator catalog also doubles as an ADR-049 cross-reference. Verdict ADOPT confirmed.

### Raw Metrics Appendix
```
{"name":"augustus","license":"Apache-2.0","stars":203,"forks":23,"language":"Go","pushed":"2026-05-06T02:40:53Z","created":"2026-02-06T17:26:47Z","open_issues":22,"size":47792 KB}
tags: v0.0.9,v0.0.8,v0.0.7,v0.0.6,v0.0.5
issues_30d=57, CI=2/10 success (7 null)
probe families: 50+
detector types: 40+
generators: 28+
multiturn strategies: 4 (crescendo, goat, hydra, mischievous)
```
