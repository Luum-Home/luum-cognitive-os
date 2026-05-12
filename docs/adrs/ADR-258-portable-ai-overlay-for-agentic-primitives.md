# ADR-258 — Portable `.ai` Overlay for Agentic Primitives

## Status

Accepted — generated overlay implemented; canonical migration intentionally deferred

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

Implemented. Host adapter README files and `adapter.json` manifests are generated
under `.ai/adapters/*/`. They expose declared fidelity and do not claim runtime
enforcement for advisory hosts.

### Phase 3 — enrich all lifecycle primitives with full portable contracts

Implemented as generated portable contract views. Registry-backed rows use
`manifests/primitive-contracts.yaml`; all other lifecycle rows receive
`primitive-lifecycle-derived` portable contract views with explicit warnings that
they must be promoted into the registry before claiming full contract-registry
governance.

### Phase 4 — consumer fleet impact

Implemented by `scripts/portable_ai_consumer_impact.py` and
`docs/reports/portable-ai-consumer-impact-latest.md`. The report is read-only and
keeps canonical migration blocked. `scripts/portable_ai_consumer_smoke.py` also writes the generated overlay into a disposable consumer fixture and verifies adapter manifests, registry-backed portable contracts, lifecycle-derived rows, and no canonical mutation.

Release-hardening adds `scripts/portable_ai_real_consumer_smoke.py`, exposed as
`scripts/cos-portable-ai-real-consumer-smoke`, which selects registered real
consumer projects for this COS checkout, projects the generated `.ai` overlay into
temporary consumer shadows, and snapshots the actual consumer `.ai` tree before
and after. This raises consumer proof from a generic fixture to representative
registered consumers while preserving the invariant that COS release validation
never mutates downstream repositories. Current consumer-fleet status may be
`warn` or `fail` when unrelated external adoption evidence remains unsigned; that
warning must not be hidden or forged.

### Phase 5 — consider canonical migration

Decision: deferred. `.ai/` remains generated and non-canonical. A future ADR is
required before migration because consumer proof and optional VERSA-style
conformance must remain explicit.


## Due-diligence addendum

ADR-258 depends on the following classification from the external due-diligence
report:

| Surface | Role in COS |
|---|---|
| `.ai` / VERSA / dotAIslash | Candidate consumer overlay standard and future conformance target. |
| `AGENTS.md` | Strong cross-tool instruction standard and adapter output. |
| `SKILL.md` / Agent Skills | Strong portable skill standard and COS skill authoring baseline. |
| MCP | Tool/server capability protocol; related but not equivalent to primitive projection. |
| ACP | Editor-agent transport protocol; related but not equivalent to primitive registry. |
| A2A | Agent-to-agent communication protocol; related but not equivalent to IDE adapter projection. |
| COS primitive contracts | Internal canonical registry. |
| `.ai` overlay | Generated consumer export. |

Decision invariant:

```text
COS canonical internal registry != consumer .ai overlay
```

The `.ai` tree is allowed to mirror, package, and project COS primitives. It is
not allowed to invent primitive behavior, erase declared fidelity differences, or
replace `manifests/primitive-contracts.yaml` as source of truth before a later
migration ADR is accepted.


## 2026-05-12 clarification: two `.ai` shapes

A follow-up comparison against a consumer project clarified that Cognitive OS
uses `.ai/` differently from a simple consumer toolkit:

- In the maintainer repo, `.ai/` is a generated, machine-readable overlay for
  contracts, profiles, adapter manifests, and projection fidelity.
- In a consumer repo, `.ai/` may be a human-readable package with README,
  Markdown primitives, context docs, scripts, logs/state, and per-IDE installers.

This does not change the ADR-258 decision. It strengthens the invariant that
COS canonical internal registry != consumer `.ai` overlay. The consumer package
shape is a product UX target; it is not a reason to make maintainer `.ai/`
canonical before Phase 5.

Impact report:

- [Portable `.ai` Overlay vs Consumer `.ai` Model Impact — 2026-05-12](../reports/portable-ai-overlay-consumer-model-impact-2026-05-12.md)

Documentation consequence: future docs must name whether they mean the
maintainer generated overlay or the consumer package view whenever `.ai/` is
discussed.


Projection consequence: the generated overlay is not enough by itself to make
portability effective for a user opening Cursor, Windsurf, Copilot, Aider, or a
similar host. ADR-258 therefore leaves a follow-up compiler problem: native IDE
files should be generated from COS contracts/profiles, or delegated through a
governed `rulesync`-style backend, while preserving declared fidelity. This is a
projection/compiler gap, not evidence that `.ai/` should become canonical.

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
python3 -m pytest tests/unit/test_portable_ai_real_consumer_smoke.py -q
python3 scripts/cos-portable-ai-real-consumer-smoke --check --json
```
