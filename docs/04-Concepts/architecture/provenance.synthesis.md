---
type: concept-synthesis
source: docs/04-Concepts/architecture/provenance.md
status: "First-pass audit (H3, pre-public readiness checklist)"
provenance: "Pre-public-release clean-room audit answering whether ADR-218 to ADR-236 code was independently written or copied, written for a hostile patent/copyright counsel reader posture."
---

## What it is
First-pass clean-room provenance audit (dated 2026-05-08) covering ADRs 218-236 and their implementation files, verifying whether COS code was independently written vs. copied from prior-art tools, under self-imposed license constraint C1 (permissive-only, pattern-adoption preferred over code adoption).

## Key mechanics
- Methodology: inventory 20 prior-art tools -> classify ADOPT-CODE / ADOPT-PATTERN / INSPIRED-BY -> smoking-gun code inspection -> license verification (VERIFIED / UNKNOWN / REQUIRES-MANUAL-CHECK).
- C1 constraint: permissive licenses only (MIT/BSD/Apache-2.0/ISC/MPL-2.0/0BSD/Unlicense/Zlib); blocklisted: AGPL, SSPL, BSL, CC-BY-NC, Commons Clause derivatives, Elastic License v2, custom non-free.
- Per-tool table covers 20 sources: Claude Code, OpenCode, Cline, Hermes/Kilo.ai/git-shadow, Codex CLI, LangGraph, Google A2A, LiteLLM, Temporal, fastmcp, Bubblewrap, Seatbelt, tmux, Aider, jujutsu, GitButler, Devin, Replit Agent, plus Cursor/Copilot/OpenHands/Continue.dev/Cody/Goose as convergence-only citations.
- 15 ADRs spot-checked (218, 220, 221, 222, 223, 226, 227, 228, 230, 231, 232, 233, 234, 235, 236); implementation files inspected include `lib/lifecycle_projection.py`, `lib/session_bus.py`, `lib/shadow_git.py` (372 LOC), `lib/session_budget.py`, `lib/handoff_envelope.py`, `lib/sandbox_adapter.py`, `lib/agent_team.py`.
- Results: severity counts LOW=15, MEDIUM=0, HIGH=0; zero smoking guns (no copied variable names, comments, or byte-matching field names).
- MEDIUM-watch item (not a finding): ADR-227 shadow-git (`lib/shadow_git.py`) has high architectural convergence with Cline's pattern — independently written with generic names, not infringement, but most likely to draw hostile-counsel scrutiny.
- fastmcp is the only ADOPT-CODE runtime dependency (Apache-2.0 claimed, imported as a library, not vendored).
- Bubblewrap (LGPL-2.0+) and Apple Seatbelt invoked via subprocess only, no linking — relies on LGPL §5 subprocess-invocation carve-out.
- 14 of 20 tools have UNKNOWN license status pending manual verification (license claims taken from ADR text, not re-fetched from upstream).

## Relations & where used
`CONTRIBUTING.md` (separate AI-authorship policy). ADR-218 through ADR-236. `docs/03-PoCs/research/orchestration-coverage-gap-analysis-2026-05-06.md` (source of constraint C1). `skills/audit-integrity/SKILL.md` (structural integrity, not provenance — used conceptually here).

## Status / caveats
No HIGH-risk items found; public release of the ADR-218→236 batch is not blocked by this audit. Two non-blocking pre-release actions recommended: (1) manual license re-verification for the 9 named UNKNOWN entries (~30 min), (2) optional `NOTICE`/`THIRD-PARTY.md` attribution file (~1h). 5 open questions remain for legal review (pattern-adoption safety, LGPL subprocess carve-out sufficiency, ADR-text-only diligence sufficiency, fastmcp license fallback, Devin patent-vs-copyright risk).
