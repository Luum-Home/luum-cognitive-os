---
adr: 315
title: Primitive Parser Contracts Before Scope Classification
status: accepted
implementation_status: implemented
date: '2026-05-14'
extends:
  - ADR-126
  - ADR-127
  - ADR-174
  - ADR-256
  - ADR-314
supersedes: []
superseded_by: null
implementation_files:
  - lib/primitive_parser.py
  - tests/unit/test_primitive_parser.py
  - docs/04-Concepts/architecture/primitive-parser-contracts.md
  - docs/06-Daily/reports/primitive-structure-standardization-2026-05-14.md
  - scripts/primitive_scope_classifier.py
  - scripts/primitive_parse_inventory.py
  - manifests/primitive-structure-scopes.yaml
  - scripts/primitive_structure_standardizer.py
  - scripts/primitive_scope_unknown_triage.py
tier: maintainer
tags:
  - primitive-governance
  - parser-contracts
  - scope
  - portability
classification_basis: accepted to prevent SCOPE taxonomy decisions from being inferred directly from raw grep/content heuristics; each primitive family must first be parsed into a normalized contract that separates structure, activation, scope declarations, metadata, and semantic hints.
verification:
  level: medium
  commands:
    - .venv/bin/python -m pytest tests/unit/test_primitive_parser.py tests/unit/test_primitive_scope_classifier.py tests/unit/test_primitive_scope_unknown_triage.py -q
    - .venv/bin/python -m py_compile lib/primitive_parser.py scripts/primitive_parse_inventory.py scripts/primitive_scope_classifier.py scripts/primitive_scope_unknown_triage.py
  proves:
    - skill, rule, hook, script, template, and package skill files parse into one normalized contract
    - parser keeps YAML frontmatter optional for rules but mandatory-findable for skills
    - classifier consumes parsed scope markers instead of reimplementing header parsing
---

# ADR-315 — Primitive Parser Contracts Before Scope Classification

## Status

Accepted and implemented — 2026-05-14.

<!-- SCOPE: os-only -->

## Context

ADR-314 fixed the immediate scope-taxonomy failure by adding an evidence-weighted classifier and a manual calibration loop. That still leaves a lower-level risk: the classifier currently has to infer primitive facts from raw files.

That is fragile because each primitive family has a different authoring grammar:

- skills use `SKILL.md` with YAML frontmatter plus Markdown body;
- rules are portable Markdown governance files with a `SCOPE` marker, H1, sections, and usually a `Contextual Trigger` section; YAML frontmatter may exist for routing but is not a universal cross-IDE requirement;
- hooks are executable event handlers whose activation comes from OS/harness lifecycle events, not from prose triggers;
- scripts are command surfaces, often manually invoked or wrapped by hooks/skills;
- templates are prompt/config composition artifacts, not runtime handlers by themselves;
- package skills under `packages/*/skills/*/SKILL.md` are consumer-facing skill artifacts and must not be skipped.

Without a parser layer, scope classification can regress into the same pattern that caused the reverted commits: reading content directly, over-weighting OS-specific strings, and confusing missing structure with an `os-only` decision.

## Decision

Introduce a canonical primitive parser layer before classification.

The parser must produce a normalized `PrimitiveContract` for every supported primitive kind:

```json
{
  "path": "rules/example.md",
  "kind": "rule",
  "is_primitive": true,
  "scope_marker": "both",
  "title": "Example Rule",
  "summary": "first useful sentence or description",
  "audience": "both",
  "activation": {
    "mode": "contextual",
    "triggers": ["review", "evidence"]
  },
  "frontmatter": {},
  "sections": ["Purpose", "Rule", "Contextual Trigger"],
  "structural_findings": [],
  "semantic_hints": ["repo-agnostic"]
}
```

The parser is **descriptive**, not authoritative. It may report semantic hints and structural findings, but it must not decide final `SCOPE`. Final classification remains owned by ADR-314 evidence and manual calibration.


## Relationship to `manifests/primitive-contracts.yaml`

ADR-315 does not replace ADR-256/ADR-257. `manifests/primitive-contracts.yaml` remains the canonical portable behavior/projection contract registry for primitives with signed runtime or projection semantics. The parser layer is a broader structural normalization layer for all candidate primitive files.

Future classifier iterations should treat primitive-contract entries as positive behavior/projection evidence where their `source` matches a parsed primitive path. The structure-only manifest `manifests/primitive-structure-scopes.yaml` exists only for file formats where inline `SCOPE` comments would corrupt generated artifacts.

## Contract by primitive family

### Skill

A skill parser must recognize `skills/*/SKILL.md` and `packages/*/skills/*/SKILL.md`.

Required structural signals:

- YAML frontmatter exists;
- frontmatter includes `name`, `version`, `description`, and `triggers`;
- Markdown body has an H1 title or a frontmatter name;
- contextual trigger information exists in frontmatter or a `Contextual Trigger` section;
- optional `audience` may seed the parsed audience but does not override `SCOPE` evidence.

### Rule

A rule parser must treat Markdown as the portable source of truth.

Required minimum contract for Cognitive OS governance:

- `<!-- SCOPE: os-only|project|both -->` marker near the top;
- H1 title;
- an opening section such as `Purpose`, `Rule`, `Principle`, or `Mandate`;
- a `Contextual Trigger` section unless the rule is explicitly listed as always-active in the compact rule index.

YAML frontmatter in rules is optional routing metadata. It may be parsed when present, but lack of YAML is not a rule-structure failure by itself.

### Hook

A hook parser must identify executable hook files and derive activation from hook event names and filename/metadata, not from a contextual trigger section. Hooks are usually OS/harness event handlers. Their parsed contract should expose:

- declared `SCOPE` marker if present;
- event activation hints such as `SessionStart`, `PreToolUse`, `PostToolUse`, `Stop`, or `SubagentStop`;
- whether the file is a symlink/package-projected surface;
- script language and shell-syntax-relevant metadata.

### Script

A script parser must identify command-like primitives under `scripts/` and expose:

- declared `SCOPE` marker if present;
- CLI/manual activation;
- language/extension;
- whether the script appears to be a `cos-*` maintainer command;
- structural findings for missing scope markers on primitive-like scripts.

### Template

A template parser must identify prompt/config artifacts under `templates/` and expose:

- declared `SCOPE` marker if present;
- template/manual activation;
- title or filename summary;
- consumer/project path references as semantic hints only.

## Non-goals

- Do not make YAML frontmatter mandatory for rules.
- Do not let parser hints rewrite scope markers.
- Do not treat OS path mentions as demotion proof.
- Do not replace ADR-314's evidence model; feed it cleaner facts.

## Implementation plan

1. Add `lib/primitive_parser.py` with dataclasses and kind-specific parsing functions.
2. Add `scripts/primitive_parse_inventory.py` for structural inventories without scope rewrites.
3. Add `scripts/primitive_structure_standardizer.py` for idempotent structure-only normalization.
4. Update `scripts/primitive_scope_classifier.py` to consume `parse_primitive_file(...).scope_marker` instead of its own header parser.
5. Keep classifier output stable; do not perform mass marker edits.
6. Add unit tests for all primitive families and for the important rule distinction: YAML optional, contextual trigger meaningful.
7. Update unknown triage to use parsed structural findings rather than duplicating section/frontmatter checks.

## Consequences

### Positive

- Scope classification starts from a typed primitive contract instead of loose grep.
- The system can explain *why* a primitive is structurally incomplete without pretending the scope is known.
- Cross-IDE portability is clearer: author once in a canonical format, then project to Claude, Codex, Cursor, Copilot, OpenCode, or future harnesses.
- Package skills remain first-class parser targets.

### Negative / trade-offs

- Parser maintenance becomes another governed surface.
- Some legacy primitives will show structural debt even when their scope marker is currently correct.
- Semantic hints remain heuristic and need manual calibration before they influence any gate.

## Verification

```bash
.venv/bin/python -m pytest tests/unit/test_primitive_parser.py tests/unit/test_primitive_scope_classifier.py tests/unit/test_primitive_scope_unknown_triage.py -q
```

## Acceptance criteria

```bash
.venv/bin/python -m pytest tests/unit/test_primitive_parser.py tests/unit/test_primitive_scope_classifier.py tests/unit/test_primitive_scope_unknown_triage.py -q
.venv/bin/python -m py_compile lib/primitive_parser.py scripts/primitive_parse_inventory.py scripts/primitive_scope_classifier.py scripts/primitive_scope_unknown_triage.py
```

## Alternatives rejected

- Leave the decision implicit in conversation history: rejected because ADR-gated governance needs a durable, reviewable record with explicit trade-offs.
- Treat this as an unversioned implementation note: rejected because the behavior affects operator-facing contracts and must survive refactors.
