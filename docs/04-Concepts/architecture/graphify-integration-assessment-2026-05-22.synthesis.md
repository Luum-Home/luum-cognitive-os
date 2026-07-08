---
type: concept-synthesis
source: docs/04-Concepts/architecture/graphify-integration-assessment-2026-05-22.md
status: "TRIAL-CONTROLLED"
provenance: "A prior May 2026 repo-scout monitor rejected safishamsi/graphify over anomalous star-count signal-integrity concerns; this reassessment used a local clone + probe to reconsider."
---

## What it is
Decision to adopt `safishamsi/graphify` (PyPI `graphifyy`, MIT, CLI `graphify`) as an optional, maintainer-only graph-indexing/query-optimization tool for COS — not a core runtime dependency, not a mandatory hook, not a whole-repo scan.

## Key mechanics
- Pipeline: `detect() -> extract() -> build_graph() -> cluster() -> analyze() -> report() -> export()`; uses Tree-sitter + NetworkX.
- Local clone `/tmp/graphify-investigation` (HEAD `6efd06c`), upstream test slice: `218 passed in 32.20s`.
- Probe on `lib/`: `graphify extract --backend ollama --exclude '*.md' ...` → `7956 nodes, 12984 edges, 511 communities`; benchmark showed `101.0x` fewer tokens per query (~5,252 avg query tokens vs ~530,400 naive).
- Gotchas: whole-repo scan unsafe (reference/ ~77k files, dashboard/ ~15k, etc. — must scope via `.graphifyignore`); `--no-cluster` output incompatible with `graphify benchmark`; semantic (docs/PDF/image) extraction costs LLM tokens; `graphify codex install` mutates `AGENTS.md`/`.codex/hooks.json` — do not run blindly; do not enable Graphify git hooks initially.
- Adoption plan phases: (1) curated `.graphifyignore`, (2) maintainer wrapper `scripts/cos-graphify-build`, (3) trial query workflow (`graphify query`, `affected`, `benchmark`), (4) optional docs semantic-extraction lane (opt-in), (5) optional Codex instruction later.
- Implemented: `.graphifyignore`, `.gitignore` for `graphify-out/`, `scripts/cos-graphify-build` wrapper, manual proof doc `docs/09-Quality/manual-tests/graphify-controlled-trial.md`, receipt at `docs/06-Daily/reports/graphify-controlled-trial-receipt-2026-05-22.md`.

## Relations & where used
Complements Engram (durable memory) and repo-map skills (curated orientation); does not replace tests/ACC. Follow-ups: ADR-331, `skills/graphify-query/SKILL.md`, `scripts/cos-graphify-build`.

## Status / caveats
TRUST_REPORT: SCORE=84 STATUS=HIGH. Uncertainties: semantic doc extraction not run (cost); Codex install/hook install intentionally not executed. Do not vendor Graphify; install via `uvx --from graphifyy graphify` or local venv only.
