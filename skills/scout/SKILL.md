<!-- SCOPE: both -->
---
name: scout
command: /scout
description: Quick pre-implementation codebase reconnaissance with 3 depth levels
trigger: Before medium+ implementation tasks, or when user invokes /scout
inputs:
  - target: File path, directory, service name, or task description to scout
  - depth (optional): quick, standard, or deep (auto-determined from task complexity if omitted)
outputs:
  - scout_report: Structured terrain map with file counts, dependencies, constraints
  - risk_signals: Unexpected complexity or missing coverage
  - recommended_approach: Brief guidance based on terrain
version: 1.0.0
last-updated: 2026-03-28
audience: project
---

# Scout -- Pre-Implementation Codebase Reconnaissance

## Purpose

Map the relevant codebase terrain BEFORE implementing changes. The scout uses a disposable context window to explore, then returns a compressed, structured report. All value must be in the report -- the scout context is garbage collected after.

## When to Scout

Determined by task complexity (see `rules/scout-pattern.md`):

| Complexity | Scout Required? | Default Depth |
|------------|----------------|---------------|
| Trivial | No | -- |
| Small | No (optional) | Quick |
| Medium | Yes | Quick |
| Large | Yes | Standard |
| Critical | Yes | Deep |

## Depth Levels

### Quick (~2,000 tokens budget)

Examine:
- File structure: `ls`, `tree -L 2` on target directories
- Entry points: `head -30` on target files (exports, public API, struct definitions)
- Direct dependencies: `grep -l` for imports of target files

Commands to use:
```bash
tree -L 2 {target_dir}
head -30 {target_files}
grep -rl "import.*{target}" {scope} --include="*.go" --include="*.ts" | wc -l
```

### Standard (~5,000 tokens budget)

Everything in Quick, plus:
- Direct importers: Which files import/depend on the target
- Test coverage existence: Do test files exist for the target
- Config references: YAML/JSON files referencing the target

Commands to use:
```bash
# Importers
grep -rl "{package_or_module}" {scope} --include="*.go" --include="*.ts"

# Test files
find {scope} -name "*_test.go" -o -name "*.spec.ts" -o -name "*.test.ts" | grep -i "{target_name}"

# Config refs
grep -rl "{target_name}" {scope} --include="*.yaml" --include="*.yml" --include="*.json"
```

### Deep (~10,000 tokens budget)

Everything in Standard, plus:
- Transitive dependencies: Second-level importers (who imports the importers)
- Security surfaces: Auth, crypto, token, permission references in target area
- Database/migration implications: Schema, migration, SQL references
- Docker/infrastructure: Which services build from the target area

Commands to use:
```bash
# Transitive deps (second level)
for f in $(grep -rl "{target}" {scope}); do grep -l "$f" {scope}; done | sort -u

# Security surfaces
grep -rn "auth\|jwt\|token\|permission\|encrypt\|secret" {target_dir}

# DB implications
grep -rn "migration\|schema\|ALTER\|CREATE TABLE" {target_dir}
find . -name "*.sql" -path "*migration*"
```

## Process

### Step 1: Receive Target

Accept a file path, directory, service name, or task description. Resolve to concrete paths.

### Step 2: Determine Depth

If depth not specified, infer from task complexity:
- Count files in scope with `find | wc -l`
- Check for cross-service keywords
- Default to Quick if uncertain

### Step 3: Run Discovery Commands

Execute the commands for the determined depth level. Use counts (`wc -l`) over full listings when possible. Read only file headers (`head -30`), never full files.

### Step 4: Synthesize Report

Produce the structured Scout Report (format below). Every claim must reference a concrete file or count.

### Step 5: Persist (Optional)

If findings are non-trivial (>5 files in scope, constraints discovered, risk signals found):
```
mem_save(
  title: "Scout: {task summary}",
  type: "discovery",
  scope: "project",
  topic_key: "scout/{task-slug}",
  content: "{scout report}"
)
```

## Scout Report Format

```
SCOUT REPORT: {task summary}
Depth: {quick|standard|deep}
Token budget: {used}/{allocated}

TERRAIN MAP:
  Target files: {N files in scope}
  Direct importers: {N files depend on targets} (standard/deep only)
  Test files: {N test files cover targets} (standard/deep only)
  Config files: {N config files reference targets} (standard/deep only)
  Services affected: {list}

KEY FINDINGS:
  1. {Finding with file reference}
  2. {Finding with file reference}
  3. {Finding with file reference}

CONSTRAINTS DISCOVERED:
  - {Constraint that affects implementation approach}

RISK SIGNALS:
  - {Any unexpected complexity, missing tests, circular deps}

RECOMMENDED APPROACH:
  {1-2 sentences on how to proceed based on terrain}
```

## Rules

- NEVER read full files. Headers only (`head -20` to `head -30`).
- Use `grep` and `find` for discovery, not `Read` tool on entire files.
- Use `wc -l` for counts, not manual enumeration.
- Stay within token budget. Report partial results if budget is exhausted, flagging unchecked dimensions.
- The scout context is disposable. ALL value must be in the report.
- Do not make implementation decisions. Report data, not opinions (except brief recommended approach).
- If the target does not exist yet (new feature), scout the surrounding area where it will be added.

## Integration

- **Output feeds**: `sdd-explore`, `exhaustive-prompt`, `impact-analysis`, implementation agents
- **Triggered by**: Orchestrator (auto for medium+ tasks), user (`/scout`), `sdd-explore` (as input)
- **Engram key**: `scout/{task-slug}`
- **Model routing**: sonnet (lightweight reconnaissance does not need opus)
