# Sandbox Sampling Rule

## Purpose

Prevents agents from blindly applying changes to large file sets. Forces a classify-sample-verify-scale workflow that catches errors early on a small subset before scaling to the full scope.

## When Sampling Applies

| Scope | Requirement |
|-------|-------------|
| <20 files | Optional (direct application OK) |
| 20-100 files | SHOULD use sampling |
| >100 files | MUST use sampling (mandatory, cannot skip) |

## Decision Matrix by File Type

| File Type | <20 files | 20-100 files | >100 files |
|-----------|-----------|--------------|------------|
| Code (*.go, *.ts, *.java, *.py) | Direct apply | Direct OK | Sample first |
| Docs (*.md) | Contextual agent | Contextual agent | Sample + contextual agent |
| Config (*.yaml, *.json, *.toml, *.env) | Direct apply | Validate after | Sample + validate |
| Templates (*.html, *.tmpl) | Direct apply | Render test | Sample + render test |

## Immutable Rules

### 1. Documentation changes MUST use contextual agents

NEVER use sed, grep replacement, or any mechanical text substitution on Markdown or documentation files. Documentation is prose -- it requires an agent that reads the full context of each sentence and rewrites naturally.

**Why**: Mechanical replacement breaks prose. For example, `sed 's/acme/globex/g'` on "the acme platform provides..." works fine. But "built on acme's architecture" becomes "built on globex's architecture" which is grammatically awkward. A contextual agent would rewrite the entire sentence as "built on the Globex architecture" — natural and correct.

**Bad**: `sed -i 's/old/new/g' README.md`
**Good**: Agent reads README.md, understands each paragraph, rewrites with the new name in natural prose.

### 2. Code changes CAN use mechanical tools

Renaming identifiers, imports, package names, and string literals in code files is deterministic and safe with sed/grep after sample validation confirms the pattern works.

### 3. Config changes MUST be validated after apply

Mechanical replacement in YAML/JSON/TOML is acceptable, but every changed file MUST be parsed after modification to confirm the file is still valid.

### 4. Sampling cannot be skipped for >100 files

No matter how "simple" the change appears, if it touches >100 files, the agent MUST:
1. Classify files by type
2. Sample 3-5 per type
3. Apply to samples in a sandbox
4. Verify samples pass
5. Only then scale to all files

### 5. The orchestrator should suggest /sandbox-sample

When the orchestrator detects an epic task (via `epic-task-detector.sh` hook or manual assessment), it should suggest running `/sandbox-sample` before launching agents.

## How to Invoke

```
/sandbox-sample
```

The skill walks through: CLASSIFY -> SAMPLE -> SANDBOX -> VERIFY -> DECIDE -> SCALE -> FINAL VERIFY.

See `skills/sandbox-sample/SKILL.md` for the full process.

## Integration with Existing Rules

- **Agent Quality** (`agent-quality.md`): Sandbox sampling is an additional quality gate. It complements acceptance criteria and exhaustive prompts by adding empirical validation.
- **Acceptance Criteria** (`acceptance-criteria.md`): The FINAL VERIFY phase generates acceptance criteria results (grep counts, build status, parse checks).
- **Completeness Check** (`completeness-check.sh`): The epic-task-detector hook complements completeness-check by specifically catching large-scope tasks.
- **Definition of Done** (`definition-of-done.md`): For large/critical tasks, sampling verification is part of the DoD.

## Contextual Trigger

This rule is loaded when:
- Tasks mention >20 files or large scope keywords
- `epic-task-detector.sh` fires an advisory
- User invokes `/sandbox-sample`
- Orchestrator detects a rebrand, migration, or bulk refactor task
