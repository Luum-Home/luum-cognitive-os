---
type: concept-synthesis
source: docs/04-Concepts/architecture/functional-audit/scorecard-skills.md
provenance: "Reachable is not the same as functional: 124 skill directories exist under skills/, but which are actually harness-discoverable and reference-clean?"
---

## What it is

Capa-3 audit of every skill directory under `skills/`, classifying each as functional, stub (malformed frontmatter), code-dead (references missing files), or doc-drift (missing from catalog).

## Key mechanics

- Totals: 124 skill directories. 113 functional (91.1%), 6 stub (4.8%), 5 code-dead (4.0%), 0 doc-drift.
- Stub root cause (identical for all 6): YAML frontmatter placed **after** the H1 heading instead of file-start, invisible to strict parsers. Affected: `agent-stress-test`, `auto-rollback`, `capability-snapshot`, `cognitive-os-status`, `impact-analysis`, `red-team`. Fix is mechanical: move frontmatter to lines 1-N.
- Code-dead: `arena` (references missing `run-arena.sh`); `auto-generated` (empty directory, no SKILL.md); `auto-refine` (its trigger hook `hooks/auto-refine.sh` was archived at `hooks/_archived/auto-refine.sh.bak` — later resolved by rebuilding it, see `ux2-hook-hygiene.md`); `coverage-enforcement` (references missing `coverage-gate.sh`); `scaffold-project` (references 4 missing paths — nuance: these are the skill's expected *output* paths in a target project, not inputs, so the classifier's code-dead flag is a known false-positive pattern here).
- Classification priority order: code-dead > stub (missing `name:` key or TODO/aspirational/WIP markers) > doc-drift (well-formed but absent from `CATALOG.md`/`CATALOG-COMPACT.md`) > functional.
- Sample verification (`random.seed(42)`, n=5) confirmed all 5 sampled functional skills have substantive content (>50 lines) and every referenced path resolves.

## Relations & where used

`tests/audit/test_skills_contracts.py` (the authoritative classifier and test), `skills/CATALOG.md`, `skills/CATALOG-COMPACT.md`; sibling `scorecard-hooks.md`.

## Status / caveats

Read-only audit. Next actions (not done in this pass): reimplement/remove `hooks/auto-refine.sh`, mechanical frontmatter fix for the 6 stub skills, decide fate of `arena`/`coverage-enforcement`/`auto-generated`, add a generator-verifier for `scaffold-project`'s output-vs-input distinction.
