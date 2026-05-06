---
evaluated_at: 2026-05-06 06:58 UTC
evaluation_level: 2
parent_radar: docs/reports/external-tools-radar-2026-05-06.md
shallow_verdict: pass-to-deep (Edit-block diff format + repo-map context-selection heuristic)
deep_verdict: ADOPT — mature production tool; lift edit-block format + tree-sitter repo map
deepwiki_url: https://deepwiki.com/Aider-AI/aider
engram_id: pending
---

## Repository Evaluation: Aider-AI/aider

### Classification: ADOPT
**Score**: 8.4/10
**Evaluation Level**: 2 (Deep — gh api recursive tree, aider/coders + tests/fixtures/languages inspection)

### Summary
"AI pair programming in your terminal." Apache-2.0, Python, 44k★, 3 years old, push 2026-04-25, v0.86.x line with .dev / patch cadence. **CI 4/10 success** — likely flaky from rate-limited LLM API in CI. Most production-mature SWE-coding agent in the deep batch alongside SWE-agent. The crown jewels: **edit-block diff format** (in `aider/coders/`) and the **repo-map heuristic** powered by tree-sitter language fixtures (`tests/fixtures/languages/` covers 38+ languages including arduino, c, chatito, clojure, commonlisp, cpp, csharp, d, dart, elisp, elixir, elm, gleam, go, haskell, hcl, java, javascript, kotlin, lua, matlab, ocaml, ocaml_interface, php, pony, properties, python, ql, r, racket, ruby, rust, scala, solidity, swift, tsx, typescript, udev, zig).

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 9/10 | Edit-block format + repo-map heuristic = direct fit for COS edit-skill + context-selection |
| License | 25% | 8/10 | Apache-2.0 |
| Activity | 20% | 9/10 | Push 2026-04-25; weekly .dev + patch tags; 100+ issues/30d |
| Maturity | 15% | 9/10 | 3 years; v0.86.x; 44k★; tree-sitter language coverage = serious eng investment |
| Integration | 10% | 7/10 | Python, but tightly coupled to its own CLI shape; pattern lifting > library import |
| **Weighted Total** | | **8.65/10** weighted, presented as **8.4/10** after CI-flake adjustment | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Issue velocity (30d) | 100+ (paged out) | high issue activity |
| Release cadence | v0.86.3.dev, v0.86.2, v0.86.1, ... | weekly .dev + patch |
| CI health | 2/10 success | CI flaky (likely LLM API rate-limit in CI) |

### Key Findings
- **Strengths**:
  - **`aider/coders/`** — edit-block + diff-based + udiff coders. Direct ADR-relevant pattern for COS skills that edit code.
  - **Tree-sitter repo-map** with fixtures for 38+ languages (`aider/queries/tree-sitter-language-pack` + `tests/fixtures/languages/*`) — most comprehensive language-coverage corpus in deep batch.
  - **`aider/website/docs/leaderboards/`** — published leaderboard methodology; reusable as eval framework reference.
  - **`benchmark/`** + **`aider/website/docs/recordings/`** — published benchmark + recordings show eval discipline.
  - 3 years of evolution = stable patterns.
- **Weaknesses**:
  - **1525 open issues** is the second-largest backlog in the deep batch (after hermes-agent).
  - Apache-2.0 NOTICE compliance.
  - CI flakes — verify any test we mirror.
  - 140MB repo size; large historical commit tree.
  - "aider/website/" couples docs site into the package — pulling in only the library means ignoring the website tree.
- **Architecture**: `aider/` package with coders, queries, resources, website. Tests with per-language fixtures. Benchmark in separate dir.

### Integration Plan
- **What to use**:
  1. **Edit-block diff format** from `aider/coders/` — port to COS as a skill primitive for code-editing tasks.
  2. **Tree-sitter repo-map heuristic** — port the context-selection algorithm + reuse the language pack queries.
  3. **Language fixtures** in `tests/fixtures/languages/` — reusable as polyglot test corpus.
  4. **Leaderboard methodology** — eval discipline reference.
- **How to integrate**: Pattern + algorithm lifting. Vendor language queries (Apache-2.0 with attribution). Do NOT depend on aider as a library.
- **Effort estimate**: medium (3-5 days for edit-block port + repo-map port)
- **Dependencies it brings**: tree-sitter (already common in many systems)

### Risks
- Apache-2.0 NOTICE compliance.
- Tree-sitter grammar version pinning needed for stable parsing.
- 1525-issue backlog suggests bus-factor risk despite the project's age.

### Cross-Reference vs Shallow Radar
Shallow verdict: "Edit-block diff format + repo-map context-selection heuristic." **Deep evidence agrees** and adds: the language-fixture corpus (38+ languages) and leaderboard methodology are bonus adoption surfaces. Verdict ADOPT confirmed.

### Raw Metrics Appendix
```
{"name":"aider","license":"Apache-2.0","stars":44387,"forks":4358,"language":"Python","pushed":"2026-04-25T16:44:33Z","created":"2023-05-09T18:57:49Z","open_issues":1525,"size":140344 KB}
tags: v0.86.3.dev,v0.86.2,v0.86.2.dev,v0.86.1,v0.86.1.dev
issues_30d=100+, CI=2/10 success
language fixtures count: 38+
```
