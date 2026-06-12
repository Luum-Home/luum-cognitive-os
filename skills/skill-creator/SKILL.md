---
name: skill-creator
description: Create or update portable AI agent skills from a high-level workflow description. Use when a user asks to create a new SKILL.md, turn repeated instructions into a reusable skill, migrate a Claude custom command or prompt into an Agent Skills-style skill, or adapt a skill for any project stack. Do not use for implementing the workflow itself unless the user asked to create the reusable skill.
metadata:
  version: 1.2.0
  audience: both
  invoke: /skill-creator
  effort: opus
  summary_line: Create or update portable AI agent skills from high-level workflow descriptions.
  platforms:
  - claude-code
  - codex
  - shell
  prerequisites: []
  routing_patterns:
  - pattern: \bskill[- ]?creator\b
    confidence: 0.96
  - pattern: \bcreate\s+(a\s+)?(new\s+)?skill\b
    confidence: 0.9
  - pattern: \bagent\s+skills?\s+spec\b
    confidence: 0.82
  triggers:
  - skill-creator
  - /skill-creator
  - create skill
  - create prompt
  - metaprompt-workflow
  routing_intents:
  - Design a new AI agent skill from user requirements and usage examples.
  - Turn a reusable agent workflow into a portable SKILL.md.
  - Adapt a Claude custom command or prompt into an Agent Skills-style skill.
  - Decide where a skill belongs across COS, project-local, user-local, or packaged surfaces.
  - Update catalogs, lifecycle metadata, tests, and projections when working inside Cognitive OS.
---
<!-- SCOPE: both -->
# Skill Creator

Create or update a reusable AI agent skill from a high-level description. Prefer
portable Agent Skills-style `SKILL.md` instructions that work across project
stacks and harnesses. Keep project-specific conventions in the target project,
not in this skill.

## Inputs

- High-level workflow description or source prompt/command/skill.
- Optional target location, such as a repository skill directory, `.claude/skills/`,
  `$CODEX_HOME/skills`, or a package-backed COS skill path.
- Optional invocation name, arguments, required tools, or known validation cases.

If the requested behavior, target location, or write permissions are unclear and
reasonable assumptions could create files in the wrong surface, ask one concise
clarifying question. Otherwise proceed and record assumptions in the output.

## Workflow

### 1. Classify the request

Choose one outcome before writing files:

- `use-existing`: an existing skill already covers the request.
- `update-existing`: an existing skill should be improved or generalized.
- `create-project-skill`: create a project-local skill for the current repo.
- `create-user-skill`: create a reusable personal/user skill outside the repo.
- `create-cos-primitive`: create or modify a Cognitive OS source primitive.
- `discard`: the source is too specific, unsafe, or better kept as ad-hoc prompt text.

Search existing skill surfaces first. In a repository, inspect likely locations
such as `skills/`, `packages/*/skills/`, `.claude/skills/`, `.cognitive-os/skills/`,
`.codex/skills/`, and project docs that mention skill ownership.

### 2. Pick the target surface

Use the narrowest surface that matches the skill's reuse boundary:

| Target | Use when |
|---|---|
| Project-local skill | The workflow is useful only in one repository or product domain. |
| User-local skill | The workflow is personal and reusable across unrelated repos. |
| Package-backed/shared skill | The workflow is reusable by many projects and needs distribution metadata. |
| Cognitive OS source skill | The workflow changes COS internals, projection, catalogs, lifecycle, or governance. |

Do not assume `.claude/skills/` is the only target. Claude Code supports skills
and custom commands, while other harnesses may project skills through different
surfaces. Prefer `SKILL.md` as the portable source and generate/adapt harness
projection files only when the target repo requires them.

### 3. Extract the reusable behavior

From the source prompt or high-level description, keep:

- The task the skill performs.
- Concrete trigger contexts and non-goals.
- Inputs and outputs.
- Step order that protects correctness.
- Required validation commands or manual checks.
- Tool permissions that are truly required.

Remove or parameterize:

- Hardcoded stack assumptions, package managers, test runners, frameworks, and
  source directories.
- Company or project names that are not part of the reusable behavior.
- Harness-only instructions such as one specific tool name, model name, or slash
  command format unless the target surface explicitly requires them.
- Mandatory web/documentation fetching unless current external documentation is
  needed for the requested skill and a primary source is known.

### 4. Write portable frontmatter

For maximum cross-tool compatibility, use only `name`, `description`, and
optional `metadata` at the top level. Put COS or harness-specific routing fields
under `metadata` when needed.

```yaml
---
name: example-skill
description: Do the reusable workflow. Use when ... Do not use when ...
metadata:
  version: 0.1.0
  audience: both
  triggers:
  - example-skill
  - /example-skill
  routing_intents:
  - User asks to perform the reusable workflow.
---
```

Description is the primary routing surface. Include what the skill does, when to
use it, and when not to use it in that field.

### 5. Write the body

Keep the body concise and operational:

1. Purpose and inputs.
2. Decision workflow.
3. Output format or artifact contract.
4. Validation and reporting.
5. Contextual trigger section if the target repo's skill contracts require it.

Use plain imperative instructions. Avoid stacked emphasis, repeated rules, and
all-caps warnings unless a silent-failure gate needs one explicit hard rule.

When a skill supports multiple stacks, providers, or harnesses, keep only the
selection logic in `SKILL.md`; move detailed variant instructions into direct
reference files only when they are large enough to justify progressive disclosure.

### 6. Add supporting files only when useful

Create extra `scripts/`, `references/`, `assets/`, or `agents/openai.yaml` files
only when they directly improve repeated execution. Do not create README,
installation guide, changelog, or process notes unless the target ecosystem
requires those artifacts.

If adding scripts, run them or a representative sample before claiming the skill
works.

### 7. Register and validate according to the target

For a plain user/project skill:

- Run the available skill validator when present.
- Verify the skill path, frontmatter, and referenced support files.
- Run any tests or manual checks named by the target project.

For Cognitive OS source changes:

- Add or update lifecycle/catalog/registry/projection metadata as required.
- If the skill declares `SCOPE: both`, add portability proof or targeted tests
  that falsify project-specific assumptions.
- Regenerate `.ai` overlay when the primitive is consumer-visible.
- Run targeted repo gates before committing.

### 8. Report

Return:

- Decision: `use-existing`, `update-existing`, `create-project-skill`,
  `create-user-skill`, `create-cos-primitive`, or `discard`.
- Skill path and invocation name.
- Portability scope and any target-specific assumptions.
- Validation performed and remaining gaps.

## Contextual Trigger

- User asks to create, update, migrate, generalize, or package an AI agent skill,
  prompt, slash command, custom command, or reusable agent workflow.
- User provides a `SKILL.md` or prompt file and asks whether to adopt it across
  projects or make it stack-agnostic.
- User asks for `/skill-creator`, `skill-creator`, or `metaprompt-workflow`.
