---
type: methodology-synthesis
source: docs/05-Methodology/root/blocked-tools.md
provenance: "Records which technically strong external tools were rejected on license grounds and why, so the decision is not re-litigated without cause."
---

## What it is

A registry of open-source tools that are technically excellent but excluded from adoption because their license is incompatible with a commercial closed-source SaaS platform, per Cognitive OS license policy. Each entry documents what the tool does, why it's good, why it's blocked, the chosen alternative, and the condition under which the exclusion should be revisited.

## Key mechanics

- **Blocked by AGPL v3** (7 tools): Daytona (sandbox, alt: E2B/Apache 2.0), Windmill (scheduler, alt: Temporal/MIT), QueryWeaver (Text2SQL, alt: MIT SQLAgent patterns), Auto-Claude (agent loop, alt: internal SDD pipeline), Claude Squad (multi-session, alt: internal session-concurrency + orchestrator-mode), Claudix (VS Code extension, alt: CLI-first scope), pre-commit-hooks/aRustyDev (alt: internal `pre-commit-gate.sh`).
- **Blocked by GPL-3.0** (1 tool): Context Engineering Kit, alt: internal SDD pipeline.
- **Blocked by SSPL** (2 tools): Inngest (alt: Hatchet/MIT), FalkorDB (alt: Apache AGE/Apache 2.0).
- **Blocked by ELv2** (1 tool): Arize Phoenix (alt: Langfuse/MIT).
- Each blocker maps to a specific legal mechanism: AGPL/GPL trigger viral copyleft on network interaction or linking; SSPL and ELv2 explicitly prohibit offering the software as a managed/SaaS service.
- A summary table consolidates all 11 entries by category, stars, license, blocker type, and alternative.
- "License Watch" section notes the 2024-2025 trend of some AGPL projects offering commercial dual licenses, some BSL projects converting to Apache 2.0 post-time-delay, and some ELv2 projects releasing permissive community editions — with a "check quarterly" cadence.

## Relations & where used

- Directly implements `rules/license-policy.md`, which is also summarized in `rules.md` (Rule 3: License Policy) with the same Allowed/Caution/Blocked license tiers (MIT/BSD/Apache=safe, LGPL/MPL=conditional, AGPL/SSPL/BSL/ELv2/Commons Clause/FSL=forbidden).
- Cross-references `docs/03-PoCs/research/license-analysis.md` as the linked license-analysis doc (path in this file uses a relative `../research/license-analysis.md`).
- Each blocked-tool's chosen alternative points to internal Cognitive OS primitives (SDD pipeline, session-concurrency, orchestrator-mode, pre-commit-gate.sh) confirming these were deliberate build-vs-adopt tradeoffs, not oversights.

## Status / caveats

- This is a **dated, point-in-time snapshot**: several entries carry explicit "Evaluated: 2026-03-26" / "Evaluated: 2026-03-28" markers and the doc itself instructs "check quarterly for updates" — license status, star counts, and tool availability may have changed since evaluation.
- The revisit conditions are speculative/forward-looking (e.g., "if Daytona offers a commercial license") and are not verified against any current license change.
