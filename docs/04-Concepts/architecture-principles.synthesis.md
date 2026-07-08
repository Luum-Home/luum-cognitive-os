---
type: concept-synthesis
source: docs/04-Concepts/architecture-principles.md
---

## What it is
5-layer Clean-Architecture-inspired dependency model (Rules -> Skills -> Hooks -> Libs -> Externals) governing how Cognitive OS primitives relate; dependencies point only inward toward Rules.

## Key mechanics
- Layers: 1 Rules (`rules/*.md`, no deps, 16 core symlinked to `.claude/rules/cos/`, 150+ total), 2 Skills (`skills/*/SKILL.md`, 72, reference rules by name), 3 Hooks (`hooks/*.sh`, 94 scripts/46 registered in settings.json, source `hooks/_lib/common.sh`), 4 Libs (`lib/*.py`, 22 modules, stdlib-preferred), 5 Externals (Docker Compose, 18 services, 4 profiles).
- Dependency Rule: inward only; prohibited: Rule->Hook/Lib, Skill->Lib, Hook->Rule(write), Lib->Rule(read). Permitted: Skill->Rule (by name), Hook->Rule/Config (read), Hook->shared lib (source), Lib->Config/External.
- Antipatterns with fixes: rule-as-documentation (>60 lines -> split to docs/), hook-with-business-logic (>100 lines -> move to lib/), skill-calling-code (executable code as implementation, not example), lib-reading-rules (parses rules/*.md -> should read cognitive-os.yaml), config-as-code (conditional logic in yaml -> belongs in hook).
- Cross-cutting: cognitive-os.yaml (single source of truth, never modified by hooks/libs), Engram (rules define schema, skills tell agents what to save, hooks enforce when, libs provide API), Metrics (.cognitive-os/metrics/*.jsonl, hooks write/skills+libs read).
- ADR-1..5: Rules=Markdown, Hooks=Bash (<100ms startup), Libs=Python 3.9+, CLI=Go (cos-test TUI), Externals=Docker Compose.
- Progressive loading: Rules ~1,500 base tokens + ~500/triggered rule; Skills ~2,000 base + 1-3K/active skill (max 5 active); Hooks/Libs/Externals consume 0 context tokens.
- System Knowledge Graph: `cos map` CLI (`cos map <primitive>`, `--affected <file>`, `--full`, `--orphans`, `--hotspots`, `--json`); relation types ENFORCES/REFERENCES/WRITES_TO/READS_FROM/SOURCES/IMPORTS/REGISTERED/CATALOGED/COMPACTED/SYMLINKED; risk tiers LOW(0-2)/MEDIUM(3-5)/HIGH(6-10)/CRITICAL(10+ or 3+ layers); rule of thumb: run `cos map` before modifying a primitive with >5 dependents. Implementation: `lib/system_graph.py`, `cmd/cos/internal/cli/map.go`, `tests/unit/test_system_graph.py`.

## Relations & where used
References `rules/trust-score.md`, `hooks/trust-score-validator.sh`, `lib/claude_executor.py`, `skills/sdd-verify/SKILL.md`, `rules/blast-radius.md`, `lib/impact_analysis.py`, `rules/closed-loop-prompts.md` (cited antipattern example), `tests/behavior/test_architecture_principles.py`.

## Status / caveats
No explicit status field in source; presented as the current governing pattern. Migration guide provided for fixing layer violations (4-step: identify antipattern, extract to correct layer, update tests, verify via `tests/behavior/test_architecture_principles.py`).
