---
type: concept-synthesis
source: docs/04-Concepts/architecture/graphify-next-step-decision-2026-05-22.md
provenance: "Follow-up to the Graphify controlled trial: which of three next steps (maintainer skill, persistent Codex instructions, semantic docs extraction) should ship next."
---

## What it is
Decision investigation choosing the next Graphify adoption step: implement a maintainer-only `graphify-query` skill next; defer persistent Codex/AGENTS.md instructions; defer semantic documentation extraction pending explicit budget/backend approval.

## Key mechanics
- Upstream `graphify codex install` writes `AGENTS.md` + `.codex/hooks.json`; the Codex hook calls `graphify hook-check`, but Codex Desktop rejects `hookSpecificOutput.additionalContext` so the hook is effectively a no-op — durable effect is just the `AGENTS.md` text, not live enforcement.
- Upstream persistent guidance says run `graphify update .` (writes to `<watch_path>/graphify-out/`), but COS's `scripts/cos-graphify-build` wrapper can write outside the repo — misaligned unless repo standardizes on repo-root `graphify-out/`.
- Query primitive behavior: `graphify path`/`graphify affected`/`graphify explain` gave precise, useful results on `CanonicalEvent`; broad natural-language `graphify query` was unreliable (returned only 3 nodes for "Which modules handle memory and routing?").
- Doc corpus cost estimate for semantic extraction: `docs/04-Concepts/architecture` 189 files (~247K tokens), `docs/02-Decisions/adrs` 344 files (~553K tokens), `rules` (~95K), `skills` (~117K) — combined ~1,012,740 tokens.
- Decision matrix: maintainer skill = High value/Low risk/Low cost/High reversibility → do next; persistent Codex instruction = Medium/Medium/Low/Medium → defer; semantic docs extraction = Potentially high/Medium-high/Medium-high/High-if-external → defer.
- Proposed skill contract: `graphify-query`, `SCOPE: os-only`, triggers on `graphify`/`graph query`/`knowledge graph`/`repo graph`; must check freshness against `git rev-parse HEAD`, never claim correctness proof, never install hooks or run `graphify codex install`.

## Relations & where used
Builds on `graphify-integration-assessment-2026-05-22.md`. Captured in ADR-331 and implemented as `skills/graphify-query/SKILL.md`; portable phase plan at `graphify-portable-optimization-plan-2026-05-22.md`.

## Status / caveats
Final decision executed: maintainer skill implemented next; no persistent Codex instructions added; no semantic docs extraction run.
