# ADR-258 — Portable `.ai` Overlay for Agentic Primitives

## Status

Accepted — due-diligence complete, generated overlay implementation started

**Date:** 2026-05-09  
**Owner:** platform-safety  
**Tier:** core  
**Related:** ADR-057, ADR-064, ADR-076, ADR-126, ADR-146, ADR-147, ADR-154, ADR-189, ADR-190, ADR-205, ADR-256, ADR-257

## Context

ADR-256 and ADR-257 introduced a primitive contract registry and the first five
portable primitive contracts. The next question is whether the repository should
port all primitives into a `.ai/` layout similar to the consumer overlay pattern
observed in the practice repository.

A new external due-diligence sweep reviewed 40+ current sources across `.ai` /
VERSA, AGENTS.md, Agent Skills, host-specific rule systems, OpenCode runtime
surfaces, MCP, ACP, A2A, and pre-action authorization systems:

- `docs/reports/portable-ai-primitive-standards-due-diligence-2026-05-09.md`

The key finding is that `.ai` is no longer just a local product-packaging idea:
VERSA / dotAIslash proposes a portable `.ai/` folder with canonical primitives,
profiles, rules, agents, tools, permissions, validation, and conformance tests.
However, AGENTS.md, SKILL.md, and MCP are more mature and broadly adopted than
VERSA itself.

## Decision

Adopt `.ai/` as a **generated portable overlay/export surface**, not as the
immediate internal canonical source of truth.

Internal canonical sources remain:

- `manifests/primitive-contracts.yaml`
- `manifests/primitive-lifecycle.yaml`
- `hooks/`
- `skills/`
- `rules/`
- `scripts/`

The `.ai` overlay will be generated from those sources and will provide a simple,
consumer-facing package:

```text
.ai/
  context.json
  primitives/
    hooks/
    skills/
    rules/
    workflows/
    tools/
  profiles/
    claude.json
    codex.json
    cursor.json
    windsurf.json
    copilot.json
    kiro.json
    opencode.json
  adapters/
    claude-code/
    codex/
    cursor/
    windsurf/
    copilot/
    kiro/
    opencode/
  logs/schema/
  state/
```

Adapters must not invent behavior. They translate contract-declared primitives
into host-specific surfaces and declare fidelity honestly.

## Implementation phases

### Phase 0 — freeze current ADR-256 implementation branch

Do not expand runtime ledger/itinerary/projection code further until the `.ai`
overlay direction is represented in docs and tests.

### Phase 1 — `.ai` overlay generator

Generate `.ai` from current COS manifests with two layers:

- all lifecycle primitives from `manifests/primitive-lifecycle.yaml` as generated reference rows;
- the ADR-257 contract slice enriched with portable trigger, required capabilities, actions, evidence, impact, and declared projection fidelity.

Acceptance:

```text
1. .ai/context.json exists and records schema/version/source manifest.
2. .ai/primitives/* covers every primitive in manifests/primitive-lifecycle.yaml.
3. The five ADR-257 contract ids round-trip with enriched contract metadata.
4. .ai/profiles/* expose declared fidelity, not inferred enforcement.
5. Tests prove .ai rows round-trip to manifests/primitive-contracts.yaml and do not overclaim structural-advisory hosts.
```

Implementation:

- `scripts/portable_ai_overlay.py` generates the overlay.
- `scripts/cos-portable-ai-overlay` is the maintainer wrapper.
- `tests/contracts/test_portable_ai_overlay.py` keeps the generated tree current.

### Phase 2 — adapter projection proof

Generate host adapter readmes/manifests for Claude, Codex, Cursor, Windsurf,
Copilot, Kiro, and OpenCode. Do not claim runtime enforcement for advisory hosts.

### Phase 3 — enrich all lifecycle primitives with full portable contracts

The initial generator already exports all lifecycle primitives as generated `.ai`
reference rows. Phase 3 upgrades those rows from lifecycle-only metadata into
full portable primitive contracts in batches, with risk classes and consumer
impact reports.

### Phase 4 — consumer fleet impact

Run consumer fleet audit and report which projects would receive `.ai` overlay
files, instruction files, hooks, or adapter docs.

### Phase 5 — consider canonical migration

Only after generator, conformance, adapters, and consumer proof are stable should
COS revisit whether `.ai/` becomes canonical rather than generated.

## Consequences

### Positive

- Aligns COS with an emerging `.ai` portable overlay spec without breaking current
  runtime hooks and tests.
- Keeps AGENTS.md, SKILL.md, MCP, and host-specific adapters as first-class
  surfaces rather than replacing them with a weaker abstraction.
- Gives consumer projects the mental packaging clarity seen in the practice repo.
- Preserves ADR-256 runtime evidence work; `.ai` becomes another projection layer.

### Negative

- Adds another generated surface that needs drift tests.
- Delays mass-porting all primitives until the overlay generator is proven.
- Duplicates metadata until a later canonical migration decision.

## Alternatives rejected

| Alternative | Rejection rationale |
|---|---|
| Move all primitive source files into `.ai/` immediately | Too disruptive; executable hooks/scripts and existing projections depend on current paths. |
| Ignore `.ai` because it is not as mature as AGENTS.md | Rejected because VERSA and the practice repo show a useful portable packaging pattern. |
| Treat `.ai` as purely documentation | Rejected; it must be generated, linted, tested, and joined to adapter fidelity. |
| Replace AGENTS.md/SKILL.md/MCP with `.ai` | Rejected; those are stronger standards and should be adapter outputs or embedded surfaces. |

## Verification plan

```bash
python3 -m pytest tests/contracts/test_portable_ai_overlay.py -q
python3 -m pytest tests/contracts/test_primitive_contract_registry.py -q
python3 -m pytest tests/contracts/test_primitive_projection_fidelity.py -q
```
