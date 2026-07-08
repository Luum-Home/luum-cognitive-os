---
type: concept-synthesis
source: docs/04-Concepts/architecture/skills-rules-canonicalization-risk-analysis.md
provenance: "Moving skills and rules from a .claude-centered model into a canonical .cognitive-os contract is a behavioral contract change, not a filesystem cleanup — doing it too early breaks rule loading, skill discovery, installer/update flows, diagnostics, docs, and a large body of tests."
---

## What it is
Risk analysis arguing that migrating skills and rules out of `.claude/` into a canonical `.cognitive-os/` contract is a behavioral contract change, not a simple path migration, and would break multiple subsystems if done prematurely.

## Key mechanics
- Static coupling evidence table (reference counts by surface — Tests / Scripts-Hooks-Bin / Go / Docs / Other): `.claude/skills` (1/10/3/72/6); `.claude/rules` (13/12/5/106/6); `.claude/settings.json`+`settings.local.json` (25/30/7/134/5); vs. `.cognitive-os/skills` (5/11/0/57/2) and `.cognitive-os/rules` (3/3/0/22/3) — Claude-facing paths dominate every surface.
- Test distribution referencing `.claude/...` explicitly: 9 unit files, 9 behavior files, 5 integration files, 4 audit files, 2 contract files, 1 hooks test file, 1 e2e file.
- 6 hidden-contract reasons the migration is risky: (1) Claude's recursive rule loading under `.claude/rules/` is itself part of the token-budget design (`docs/04-Concepts/root/rules-loading-architecture.md`, `tests/behavior/test_claude_md_diet.py`, `tests/unit/test_efficiency_stress.py`); (2) skill exposure/truth is already split — `scripts/cos-init.sh` installs to both `.cognitive-os/skills/cos/` (kernel storage) and `.claude/skills/` (the empirically verified discovery surface for the current Claude driver); (3) rules are **not** mirrored the way skills are — more tightly coupled to Claude-facing layout, copied directly into `.claude/rules/cos/` by bootstrap flows; (4) installer/export logic bakes in the contract — `cmd/cos/internal/installer/export.go` resolves skills to `.claude/skills/...` and rules to `.claude/rules/cos/...`; (5) CLI/status tooling (`bin/cognitive-os.sh`) inspects `.claude/skills/`, `.claude/rules/`, `.claude/settings.json` directly; (6) a large body of tests encode the old contract broadly.
- 4-phase recommended migration shape (do **not** start by moving files): Phase 1 define canonical contracts (canonical rules/skill-discovery paths, projection metadata model); Phase 2 teach tooling canonical-first semantics (installer/export, status/diagnostic tooling, update flows, validation/audit); Phase 3 add dual-path compatibility (system works from canonical state while still projecting into Claude); Phase 4 only then demote `.claude/...` to a driver surface.
- 3 things that must exist before a safe migration: a canonical discovery contract (where files live, how the OS enumerates them, what counts as installed, projection metadata), a projection contract per harness (Claude, Codex, future harnesses), and an explicit truth hierarchy (canonical truth / harness projection / compatibility shims) — plus migration-safe contract tests verifying canonical artifacts exist without `.claude/`, Claude projection is generated from canonical artifacts, non-Claude harnesses don't depend on `.claude/`, and portable features fail only when a driver is missing.

## Relations & where used
`docs/04-Concepts/architecture/skills-rules-portability-gap.md`, `bootstrap-portability.md`, `cross-harness-authoring.md`, `cmd/cos/internal/installer/export.go`, `scripts/cos-init.sh`.

## Status / caveats
Conclusion: the `.cognitive-os/`-as-source-of-truth direction is still correct, but a direct path migration today is high-risk — "the migration shape matters more than the destination." No implementation has started per this document; it is a pre-migration risk analysis only.
