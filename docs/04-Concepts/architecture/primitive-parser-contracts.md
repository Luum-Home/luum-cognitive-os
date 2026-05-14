# Primitive Parser Contracts

Primitive parsing is the layer below `SCOPE` classification. It answers: *what kind of primitive is this, how is it activated, what structure does it declare, and what evidence is missing?* It does **not** answer final distribution scope by itself.

## Normalized contract

Every supported primitive family should parse into one normalized shape:

| Field | Meaning |
|---|---|
| `path` | repository-relative file path |
| `kind` | `skill`, `rule`, `hook`, `script`, `template`, or `unknown` |
| `is_primitive` | whether the path belongs to a known primitive surface |
| `scope_marker` | explicit `SCOPE` marker if present |
| `title` | H1, frontmatter name, or filename fallback |
| `summary` | frontmatter description or first useful prose sentence |
| `audience` | parsed audience metadata, if any |
| `activation.mode` | `always`, `contextual`, `event`, `manual`, `template`, or `unknown` |
| `activation.triggers` | trigger strings, event names, or command hints |
| `frontmatter` | parsed YAML frontmatter when present |
| `sections` | Markdown section headings |
| `structural_findings` | missing or malformed contract signals |
| `semantic_hints` | weak hints such as `os-internal-reference` or `repo-agnostic-language` |

## Family contracts

### Skills

Skills are `SKILL.md` files under `skills/` or `packages/*/skills/*/`. They should include YAML frontmatter with `name`, `version`, `description`, and `triggers`. A missing field is structural debt, not automatic `os-only` scope.

### Rules

Rules are portable Markdown governance files. Cognitive OS expects a top `SCOPE` marker, H1, opening section, and contextual trigger information. YAML frontmatter is optional because AGENTS.md, Cursor rules, Copilot instructions, and Claude/Codex-style rule files do not share one universal metadata grammar.

### Hooks

Hooks are event handlers. Their activation comes from lifecycle events such as `SessionStart`, `PreToolUse`, `PostToolUse`, `Stop`, and `SubagentStop`, plus configured matcher metadata outside the file. They should not be judged by missing `Contextual Trigger` sections.

### Scripts

Scripts are command surfaces. Activation is manual/CLI unless another primitive wraps them. `cos-*` names and Cognitive OS internals are semantic hints, not final classification proof.

### Templates

Templates are composition artifacts. They can be portable even when rendered by OS-specific machinery. Their parser should expose placeholders and path references as hints for later review.



## Relationship with primitive contract registry

`manifests/primitive-contracts.yaml` remains the canonical portable behavior/projection contract registry from ADR-256/ADR-257. It describes runtime intent, triggers, required capabilities, evidence, and per-harness projection fidelity for the subset of primitives that have signed portable contracts.

The parser contract layer is lower-level and broader: it structurally parses every candidate primitive file before ADR-314 scope classification. It must not supersede `primitive-contracts.yaml`. Instead:

1. parser contracts normalize file structure for all primitive families;
2. `primitive-contracts.yaml` supplies behavior/projection facts for contracted primitives;
3. ADR-314 combines parsed structure, lifecycle, consumer availability, scope overrides, protected surfaces, proof paths, and contract evidence to calibrate `SCOPE`.

`manifests/primitive-structure-scopes.yaml` is only a structural escape hatch for comment-hostile templates such as JSON/TOML/YAML render targets. It is not a behavior/projection registry.

## Structure standardizer

Use the standardizer for structure-only normalization. It preserves existing SCOPE markers and does not perform semantic scope adjudication:

```bash
.venv/bin/python scripts/primitive_structure_standardizer.py --project-dir .
.venv/bin/python scripts/primitive_structure_standardizer.py --project-dir . --write
```

Templates whose rendered format cannot safely carry comments use `manifests/primitive-structure-scopes.yaml` as parser metadata.

## Inventory command

Use the parser inventory to inspect structure without changing classification:

```bash
.venv/bin/python scripts/primitive_parse_inventory.py --project-dir .
.venv/bin/python scripts/primitive_parse_inventory.py --project-dir . --paths rules/recommendation-grounding.md skills/code-review/SKILL.md
```

The output is written to `.cognitive-os/reports/primitive-parse-inventory.json` and summarizes kind counts, activation modes, missing scope markers, and structural findings.

## How this feeds scope classification

`lib/primitive_parser.py` provides typed facts to `scripts/primitive_scope_classifier.py`. ADR-314 remains the classification authority:

1. parser extracts marker, kind, activation, and structural debt;
2. classifier combines parsed facts with lifecycle, consumer availability, protected surface, override, and proof evidence;
3. unknown triage groups missing evidence and parser structural findings;
4. manual iterations change one thing at a time.

Do not use parser semantic hints to rewrite markers without a recorded calibration iteration.

## Acceptance criteria

```bash
.venv/bin/python -m pytest tests/unit/test_primitive_parser.py -q
.venv/bin/python scripts/primitive_scope_classifier.py --project-dir . --paths <changed-primitive> --fail-contradictions
```
