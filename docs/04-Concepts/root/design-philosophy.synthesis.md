---
type: concept-synthesis
source: docs/04-Concepts/root/design-philosophy.md
provenance: "Operating-system metaphor broke down (OSes don't learn, heal, evolve, or adapt to their user) — the living-organism analogy fits what COS actually became."
---

## What it is

Framing document mapping every major COS subsystem to a biological analog, used as a design-review lens: "which biological system does this feature strengthen — does it make the organism more fit, or just more complex?"

## Key mechanics

**12 implemented biological systems** (analog → COS component → files):
1. Immune system → Auto-repair + circuit breakers (`hooks/error-pipeline.sh`, `hooks/auto-repair-dispatcher.sh`, `lib/circuit_breaker.py`); 2 strikes = OPEN, 1h cooldown.
2. Long-term memory → Engram; NEVER deletes memories (stores everything, retrieves selectively — unlike context-compression approaches that discard 80-90%). Topic key prefixes = cortical regions (`planning/`, `bugfix/`, `architecture/`).
3. Reflexes → Hooks: 94 scripts exist in `hooks/`, 46 registered in `settings.json`, firing at 8 lifecycle points (SessionStart×3, PreToolUse×9, PostToolUse×24, Stop×5, plus TeammateIdle/TaskCreated/TaskCompleted/UserPromptSubmit×4). Each hook target <500ms.
4. Maturation → Capability levels 1-5 (`lib/capability_levels.py`); L3 disables context-management; L4 disables clarification-gate/assumption-tracking/confidence-gate/model-routing/blast-radius; L5 silences 11 more hooks.
5. Natural selection → Consequence system: score >=85% for 5 consecutive runs = PROMOTE; <60% = WARN→DEGRADE→DISABLE. `lib/consequence_engine.py`, `lib/skill_archive.py`.
6. Pain → Error signals: `error-learning.jsonl`; 3+ same error in 24h triggers warning injection; circuit breaker on repeats.
7. Metabolism → Token economy: `lean` profile ~6,000 tok/session, `standard` ~8,000, `full` ~142,000. Model routing = pick cheapest capable model.
8. Growth → Auto-skill generation: 10+ tool-use tasks trigger draft skill generation; 72 skills exist today, grows organically (`hooks/auto-skill-generator.sh`).
9. Autonomic nervous system → Singularity controller (`lib/singularity.py`), MAPE-K loop, processes events by strict priority: circuit-breaker events → test failures → bugs → KPI degradation → stale docs.
10. Behavioral adaptation → Adaptive bypass (`hooks/adaptive-bypass.sh`): trivial task ~200 tokens vs full orchestration ~3,000 tokens (93% savings); backed by ETH Zurich research showing context overhead reduces performance on simple tasks.
11. Sensory system → Quality-gate hooks (`blast-radius.sh`, `infra-intent-detector.sh`, `secret-detector.sh`, `assumption-tracker.sh`, `clarification-gate.sh`); thresholds score >60=BLOCK, 30-60=WARN, <30=pass.
12. Reproduction → `cos init`/`/cognitive-os-init` spawns adapted instances per project; presets (`lean`, `standard`, `full`, `fintech`, `healthcare`) are phenotypes of the same genome.

**3 designed-but-not-implemented systems**:
- Homeostasis: continuous self-regulation loop (raise capability_level if tokens/session > threshold; lower if error_rate >20%; downgrade models if cost > budget; trigger self-improvement if task_success <70%). Only the continuous automatic loop is missing — monitoring/adjustment mechanisms already exist.
- Symbiosis: overhead/useful token ratio tracking; WARN if ratio >0.3 ("consuming more than contributing"); healthy if <0.1. Implementation path: extend `hooks/session-cleanup.sh`, log to `metrics/symbiosis.jsonl`.
- Ecosystem integration: coexistence with other AI systems (Cursor Cloud Agents, kagent, Skills.sh) via `execution.backends` config — already designed in `docs/04-Concepts/root/execution-backends.md`.

**8 design principles** (biological): store everything/retrieve selectively; respond proportionally; grow through use; mature don't accumulate; be symbiotic not parasitic (RULES-COMPACT.md ~2,890 tok vs full ~17,500 tok); reproduce adapted; fail gracefully (4-tier fault tolerance: connection/LLM-call/context/agent); evolve continuously (max 5 auto-improvements/run, mandatory test gate, improvement blocklist).

**Organism in numbers**: 94 hooks (46 registered), 16 core rules (150+ total), 72 skills, 79 Python modules, 20+ metrics JSONL files, 3 efficiency profiles, 5 capability levels, 4 lifecycle phases, 5 execution backends (designed).

## Relations & where used

`rules/auto-repair.md`, `rules/engram-organization.md`, `rules/capability-levels.md`, `rules/consequence-system.md`, `rules/error-learning.md`, `rules/token-economy.md`, `rules/resource-governance.md`, `rules/auto-skill-generation.md`, `rules/singularity.md`, `rules/adaptive-bypass.md`, `rules/self-improvement-protocol.md`, `docs/03-PoCs/research/minimal-context-principle.md` (ETH Zurich paper), `docs/04-Concepts/root/execution-backends.md`, `docs/04-Concepts/root/distributed-architecture.md`.

## Status / caveats

12 of 15 biological systems are implemented (production/beta/experimental maturity varies — e.g. Singularity is Experimental, Consequence system and Auto-skill-gen are Beta). The remaining 3 (homeostasis, symbiosis awareness, ecosystem integration) are designed with clear implementation paths but not built. Document also raises an open naming question (Cognitive OS vs "Luum" as brand) without resolving it.
