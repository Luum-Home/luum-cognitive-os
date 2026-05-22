# Graphify Phase D Semantic Extraction Plan — 2026-05-22

## Purpose

Phase D covers Markdown/YAML-heavy Cognitive OS surfaces that code-only Graphify
intentionally skipped: `skills/`, `rules/`, and selected architecture/ADR docs.
This phase is not enabled by default because semantic extraction can send document
chunks to the configured model backend and has non-trivial token cost.

## Current Boundary

Graphify remains a context-selection and navigation primitive. It does not become
a verifier, policy oracle, or replacement for tests, ADRs, rules, or source review.
Semantic extraction can improve discovery of governance and procedural gaps, but
its output must be labeled as retrieval support.

## Candidate Slices

| Slice | Reason | Gate |
|---|---|---|
| `skills/` | Skill routing and procedural gap discovery | explicit backend and token-budget approval |
| `rules/` | Governance vocabulary, trigger, and policy gap discovery | explicit backend and token-budget approval |
| `docs/04-Concepts/architecture/` | Architecture retrieval and cross-reference discovery | explicit backend and token-budget approval |
| `docs/02-Decisions/adrs/` | Decision retrieval and supersession checks | explicit backend and token-budget approval |

## Execution Wrapper

Phase D is implemented through `scripts/cos-graphify-phase-d-semantic`. The wrapper checks backend readiness, runs one slice at a time, records receipts, and refuses to execute when the requested backend is unavailable.

Use a temporary output root and a local backend only after the user approves the
backend and budget:

```bash
scripts/cos-graphify-phase-d-semantic --execute --backend ollama --timeout-seconds 600 --progress-seconds 30 --out docs/06-Daily/reports/graphify-phase-d-execution-receipt-YYYY-MM-DD.md
```

The wrapper repeats per slice and does not run one whole-repository semantic extraction. On 2026-05-22 it produced `docs/06-Daily/reports/graphify-phase-d-execution-receipt-2026-05-22.md`; execution was blocked because no local Ollama API or API-key backend was available in the environment.

## Acceptance Criteria

1. The operator approves backend and token budget before `--include-docs` is used.
2. Each semantic slice has its own temporary output and receipt command.
3. Semantic retrieval answers cite documents and distinguish extracted text from
   maintainer inference.
4. No Graphify semantic output is used as verification evidence without source,
   test, or ADR confirmation.
5. Phase D results feed preload or routing updates only after a maintainer reviews
   the generated gaps.
