---
name: add-skill
description: 'Use when you need this Cognitive OS skill: Step-by-step guide for adding
  a new skill to the Cognitive OS; do not use when a narrower skill directly matches
  the task.'
version: 0.1.0
audience: os
tags:
- development
- extension
- skills
platforms:
- claude-code
prerequisites: []
routing_patterns:
- pattern: \badd[- ]?skill\b
  confidence: 0.95
- pattern: /add-skill\b
  confidence: 0.95
- pattern: \bnew[- ]?skill\b
  confidence: 0.8
summary_line: Step-by-step guide for adding a new skill to the Cognitive OS.
triggers:
- add-skill
- new skill
- skill authoring
- Cognitive OS skill
routing_intents:
- intent: add_skill_request
  description: User asks to step-by-step guide for adding a new skill to the Cognitive
    OS.
  confidence: 0.85
---
<!-- SCOPE: os-only -->
# Add Skill

> Procedure for creating a new skill that agents can invoke in the Cognitive OS.

## Scope note

This skill is `os-only` because the procedure edits Cognitive OS skill source,
catalogs, routing metadata, registry artifacts, and COS-specific projection
gates. A generic "author a SKILL.md capability for any repository" procedure
would be a separate portable primitive.

## Trigger

When you need to add a new reusable procedure, workflow, or domain knowledge as an invokable skill.

## Inputs

- **Skill name**: kebab-case identifier (e.g., `my-skill`)
- **Audience**: `os` (OS development only), `project` (project work), or `both`
- **Invoke command**: the slash command users call (e.g., `/my-skill`)
- **Description**: one-line summary for the CATALOG.md entry
- **Tags**: list of categorization tags

## Steps

### 1. Create the skill directory

```bash
mkdir -p skills/{skill-name}
```

### 2. Create `SKILL.md` with frontmatter

```markdown
---
name: {skill-name}
description: {One-line description — this appears in CATALOG.md}
version: 0.1.0
audience: {os|project|both}
tags: [{tag1}, {tag2}]
summary_line: {One short routing-oriented sentence}
routing_patterns:
  - pattern: '\b{skill-name}\b|/{skill-name}'
    confidence: 0.96
routing_intents:
  - intent: {semantic_intent_name}
    description: User asks to {describe the capability without language-specific keywords}.
    confidence: 0.85
---

# {Skill Display Name}

> One-sentence description of what this skill does.

## Trigger

When the user invokes `/{skill-name}` or when {contextual trigger condition}.

## Steps

1. **Step one**: description
   - Sub-bullet with detail

2. **Step two**: description
   ```bash
   # Example command if applicable
   ```

3. **Step three**: description

## Success Criteria

- [ ] Criterion 1: verifiable outcome
- [ ] Criterion 2: verifiable outcome
```

Structure guidelines:
- Keep under 100 lines for context efficiency (load as Level 2 on demand)
- Use numbered steps for procedures; bullet points for reference info
- Include code blocks only where they clarify conventions
- `audience: os` for OS development skills (adding hooks, rules, skills, MCP servers)
- `audience: project` for project work skills (debugging, SDD phases, etc.)
- `audience: both` for universal skills (formatting, capability snapshot, etc.)
- Author the skill once at the behavioral level. Keep harness-specific triggers,
  driver files, and projection notes separate from the main procedure.

Choose the `<!-- SCOPE: ... -->` marker with the same semantic taxonomy as the
classifier:

| Scope | Use when |
|---|---|
| `os-only` | The skill creates/changes Cognitive OS internals, catalogs, manifests, ADR governance, harness projection files, or source-repo automation. |
| `project` | The skill writes or scaffolds adopter-project artifacts only and is not needed for COS self-construction. |
| `both` | The skill is a repo-agnostic procedure useful in COS and adopter repositories. |

`audience`, distribution tier, or routing exposure are evidence, not automatic
SCOPE. If `audience: both` or `<!-- SCOPE: both -->`, add paired portability
proof and explicit behavior evidence before committing.

### 2b. Add a portability note

Decide whether the skill is:

- `core-agnostic`
- `driver-projected`
- `harness-advantaged`
- `harness-only`

If the skill depends on one harness for triggers, file layout, or workflow
surface, state that explicitly in a short `## Portability` section.

If the skill declares `<!-- SCOPE: both -->` or `audience: both`, scaffold the
paired portability proof using the canonical suggested path:

```bash
scripts/cos-portability-proof-scaffold --artifact skills/{skill-name}/SKILL.md
```

The generated path is `tests/red_team/portability/test_skill_{skill_name}.py`
with hyphens normalized to underscores, matching the audit and scope gate.

After adding the proof, record it in `manifests/primitive-behavior-evidence.yaml`
if the proof path is not the canonical path returned by
`lib.portability_proof_paths.suggested_test_path`.

### 2c. Add language-agnostic routing metadata

Follow ADR-302 for every new skill:

- `routing_patterns` may contain explicit command/identifier aliases only.
- Do not add natural-language keyword regexes in English, Spanish, or any other
  language.
- Put natural-language trigger meaning in `summary_line` and `routing_intents`.
- For multilingual coverage, generate or curate semantic examples with:

```bash
scripts/cos-skill-description-enrich --dry-run --skills {skill-name} --languages en,es,pt,de,fr,it --intents-per-lang 2
scripts/cos-routing-benchmark --quick
scripts/cos-language-dependence-audit --output .cognitive-os/reports/language-dependence-audit.md
```

These examples are embedding corpus data, not hard keyword gates. This applies
both to SO skills and project-local skills in consumer overlays.

### 3. Add to `skills/CATALOG.md`

Find the appropriate section and add a one-line entry:

```markdown
| {skill-name} | {Description matching frontmatter} | `/{invoke-command}` | {audience} |
```

Sections to consider:
- **Universal Skills** — works for any project/context
- **OS Development Skills** — for OS-only work (`audience: os`)
- **Project Skills** — for project-specific work (`audience: project`)

If no section fits, add a new section heading.

### 4. Add to auto-loader (optional)

If the skill maps to a detected technology or should auto-trigger, add it to `rules/RULES-COMPACT.md` in the contextual triggers section with the trigger keywords. Example:

```markdown
[`{skill-name}`]: {description}. Trigger: keyword1, keyword2.
```

### 5. Run `/skill-registry` to update the index

```bash
# Invoke the skill-registry skill to rebuild the registry
# This updates .atl/skill-registry.md and saves to Engram
```

Or if the skill-registry skill is not available, manually verify the CATALOG.md entry is correct.

### 6. Write a test

Create `tests/unit/test-{skill-name}.sh` or add a test case to `tests/unit/test-skills.sh` that verifies the skill file exists with valid frontmatter:

```bash
#!/usr/bin/env bash
# Verify skill structure

SKILL_FILE="skills/{skill-name}/SKILL.md"

if [[ ! -f "$SKILL_FILE" ]]; then
    echo "FAIL: $SKILL_FILE not found"
    exit 1
fi

# Check frontmatter fields
if ! grep -q "^name: {skill-name}" "$SKILL_FILE"; then
    echo "FAIL: missing name in frontmatter"
    exit 1
fi

if ! grep -q "^audience:" "$SKILL_FILE"; then
    echo "FAIL: missing audience in frontmatter"
    exit 1
fi

echo "PASS: {skill-name} skill structure valid"
```

### 6b. Run the scope classifier for this skill

Every new or reclassified skill must pass the evidence-weighted classifier:

```bash
python3 scripts/primitive_scope_classifier.py \
  --project-dir . \
  --paths skills/{skill-name}/SKILL.md \
  --fail-contradictions \
  --fail-low-confidence
```

If it fails, update the evidence instead of hand-waving the SCOPE:

- `manifests/primitive-consumer-availability.yaml` for availability.
- `manifests/primitive-behavior-evidence.yaml` for paired portability proof rows.
- `manifests/primitive-lifecycle.yaml` when the skill becomes durable runtime/governance surface.
- `tests/red_team/portability/test_skill_{skill_name}.py` for `SCOPE: both`.

If the skill is `driver-projected`, also add at least one characterization test
or verification note for the projection behavior.

### 6b. Validate scope projection before commit

For every new skill, run the source-level scope checks. For `audience: both` or
`<!-- SCOPE: both -->`, the paired proof must exist before these pass:

```bash
scripts/cos-scope-both-portability-audit --strict --no-write
scripts/cos-scope-projection-audit --strict --no-write
```

If the skill can be installed into consumer projects, also run the install smoke:

```bash
scripts/cos-scope-projection-audit --run-install-smoke --strict --no-write
scripts/cos-install-projection-audit --json
```

Run `scripts/cos-install-projection-audit --json` whenever the skill changes
generated settings, install profiles, hook routing, or any projected consumer
surface. It catches dangling hook registrations and SCOPE-excluded hook
projection after the actual filtered install runs.

## Operational Skills (command-style frontmatter)

For skills that are invoked as slash commands rather than loaded as context, use this alternative frontmatter format:

```yaml
---
description: What this skill does
command: skill-command-name
---
```

This is used for skills like `daily-health-check` that have a direct invocation pattern.

## Output: Working Skill

- `skills/{skill-name}/SKILL.md` — skill file with frontmatter and steps
- `skills/CATALOG.md` — updated with new entry
- `tests/unit/test-{skill-name}.sh` — structure test (optional but recommended)
- `tests/red_team/portability/test_skill_{skill_name}.py` — paired proof when `SCOPE: both`

## Success Criteria

- [ ] `skills/{skill-name}/SKILL.md` exists with valid YAML frontmatter
- [ ] `grep "{skill-name}" skills/CATALOG.md` returns a matching entry
- [ ] Frontmatter has `name`, `description`, `version`, `audience` fields
- [ ] Steps are numbered, imperative, and verifiable
- [ ] Harness-specific assumptions are either absent or explicitly documented
- [ ] Scope checks pass: `scripts/cos-scope-both-portability-audit --strict --no-write` and `scripts/cos-scope-projection-audit --strict --no-write`
- [ ] Consumer-visible skills pass install projection smoke: `scripts/cos-scope-projection-audit --run-install-smoke --strict --no-write`
- [ ] Generated install/projected settings remain consistent: `scripts/cos-install-projection-audit --json`
- [ ] Skill loads without error: `cat skills/{skill-name}/SKILL.md | head -10`
