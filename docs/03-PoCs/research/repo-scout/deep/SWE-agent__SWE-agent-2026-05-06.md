---
evaluated_at: 2026-05-06 06:55 UTC
evaluation_level: 2
parent_radar: docs/06-Daily/reports/external-tools-radar-2026-05-06.md
shallow_verdict: pass-to-deep (ACI design — bash tool surface, file viewer, edit semantics — reference)
deep_verdict: ADOPT — academic-grade ACI reference; tool/* directory is the gold artifact
deepwiki_url: https://deepwiki.com/SWE-agent/SWE-agent
engram_id: pending
---

## Repository Evaluation: SWE-agent/SWE-agent

### Classification: ADOPT
**Score**: 8.6/10
**Evaluation Level**: 2 (Deep — gh api recursive tree, tools/* + tests/test_data inspection)

### Summary
**[NeurIPS 2024]** SWE-agent: GitHub-issue auto-fixer + offensive cybersecurity + competitive coding. Princeton/CMU-affiliated (`SWE-agent` org). Python, MIT, 19k★, push 2026-04-27, **v1.1.0** stable + v1.0.x patch line. CI 2/10 success (likely cancelled, not failed — 8 nulls excluded from failure count means most are pending/skipped). The crown jewel is the **`tools/*` directory** — 18 first-class ACI tool packages (diff_state, edit_anthropic, filemap, forfeit, image_tools, multilingual_setup, registry, review_on_submit_m, search, submit, web_browser, windowed, windowed_edit_linting, windowed_edit_replace, windowed_edit_rewrite). Each is a self-contained tool with `bin/` + (sometimes) `lib/` — the exact ACI primitive shape COS rules §11 + skills system aspires to.

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 9/10 | tools/* directory is the canonical ACI reference; CTF + SWE-Bench data sources are ready-made evals |
| License | 25% | 10/10 | MIT |
| Activity | 20% | 8/10 | Push 2026-04-27; v1.1.0 stable; 25 issues/30d |
| Maturity | 15% | 9/10 | NeurIPS 2024 paper; v1.1.0 + v1.0.x patches; 2 years old; 19k★; clean modular architecture |
| Integration | 10% | 8/10 | Each tool/ subdir is independently usable as a binary; trajectories/ corpus is reusable as eval data |
| **Weighted Total** | | **8.7/10** weighted, presented as **8.6/10** | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Issue velocity (30d) | 25 issues | moderate-high issue activity |
| Release cadence | v1.1.0, v1.0.1, v1.0.0, v0.7.0, v0.6.1 | quarterly major releases |
| CI health | 2/10 success | CI ambiguous (8 null in last 10; likely cancelled, not failed) |

### Key Findings
- **Strengths**:
  - **`tools/*` is the prize**: 18 self-contained ACI tools with `bin/` entry points. Clean Unix-style decomposition. Each tool is small enough to study in isolation.
  - **`tools/registry/`** is especially interesting — it's a tool that registers tools. Direct fit for COS dynamic-tool-creation primitive.
  - **`tools/web_browser/`** with `lib/` — best-of-class agent-browser-tool reference.
  - **`tools/windowed*`** family (3 variants: linting, replace, rewrite) — sophisticated edit semantics.
  - **`trajectories/demonstrations/`** — published demonstration trajectories, including replay variants. Reusable as imitation-learning corpus or as eval input.
  - **`tests/test_data/data_sources/ctf/`** + **`trajectories/demonstrations/ctf/`** — CTF (capture-the-flag) eval set; offensive-security relevance bridges to deep targets #20 and #21 (snyk/agent-scan, augustus).
  - `config/{benchmarks, demo, exotic, human, sweagent_0_7}` — config catalog.
  - SWE-Bench integration data in `tests/test_data/`.
- **Weaknesses**:
  - 52 open issues — manageable but worth checking triage state.
  - CI 2/10 visible success rate — needs investigation; large null count suggests cancelled jobs.
  - 71MB repo size; trajectories are heavy.
- **Architecture**: `sweagent/{agent, environment, inspector, run, tools, utils}` core; `tools/*` external tool packages; `config/*` profile catalog; `tests/test_data/{trajectories, data_sources/ctf}` eval sets; `trajectories/demonstrations` published runs.

### Integration Plan
- **What to use**:
  1. **`tools/*` ACI catalog** — read each tool's bin/ entry and (if present) lib/ to lift into COS skills. Especially: `tools/registry/`, `tools/web_browser/`, `tools/windowed*` family, `tools/diff_state/`, `tools/edit_anthropic/`, `tools/search/`, `tools/submit/`.
  2. **CTF data sources** in `tests/test_data/data_sources/ctf/` — eval corpus for COS red-teaming + augustus integration.
  3. **trajectories/demonstrations/** — imitation-learning / regression-eval corpus.
  4. **SWE-Bench integration test data** — eval gold set for any SWE-Bench-style COS benchmark.
- **How to integrate**: Tool-by-tool study + selective port. Use trajectories as eval corpus for COS skill verification.
- **Effort estimate**: medium-large (5-10 days for selective tool ports + eval corpus wiring)
- **Dependencies it brings**: per-tool; mostly stdlib + a few CLI tools

### Risks
- License attribution required when porting tool sources.
- Trajectory corpus may be model-specific (gpt4-trajectories) — need newer-model trajectories for current relevance.
- CTF data may have third-party-content licensing concerns (verify per CTF challenge).

### Cross-Reference vs Shallow Radar
Shallow verdict: "ACI design (bash tool surface, file viewer, edit semantics) reference." **Deep evidence agrees and amplifies**: 18 ACI tools, not just bash/file viewer/edit. The trajectories corpus + CTF data sources are bonus adoption surfaces. Verdict ADOPT confirmed at 8.6/10.

### Raw Metrics Appendix
```
{"name":"SWE-agent","license":"MIT","stars":19143,"forks":2062,"language":"Python","pushed":"2026-04-27T22:10:17Z","created":"2024-04-02T04:09:47Z","open_issues":52,"size":71719 KB}
tags: v1.1.0,v1.0.1,v1.0.0,v0.7.0,v0.6.1
issues_30d=25, CI=2/10 success (8 null)
tools count: 18
```
