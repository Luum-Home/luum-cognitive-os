---
name: document-feature
version: 1.1.0
description: 'Generate or update structured feature documentation using 3-layer detection
  (SDD spec, git diff, CLI arg). Extension (v1.1, ADR-054 Phase 2): accepts --project-dir
  to append to docs/05-features/features-backlog.md in an adopter project.'
invocation: /document-feature [feature-name] [--project-dir <path>]
user-invocable: true
last-updated: 2026-03-26
triggers:
- feature documentation
- document feature
- generate docs
- update feature docs
audience: project
summary_line: Generate or update structured feature documentation using 3-layer detection…
routing:
  auto_fallback_to_qwen: true
  fallback_min_pressure: 0.6
  tier: cheap
platforms:
- claude-code
prerequisites: []
---
<!-- SCOPE: both -->
# Document Feature

Generate or incrementally update structured documentation for project features. Uses a 3-layer detection strategy inspired by the AI Workflow document-iso pattern.

## Invocation

```
/document-feature [feature-name] [--project-dir <path>]
```

- With `feature-name`: documents that specific feature (Layer 3)
- Without arguments: auto-detects features via SDD spec or git diff (Layers 1-2)
- With `--project-dir <path>`: **ADR-054 Phase 2 extension** — in addition to (or instead of) the full per-feature doc, append a one-row entry to `<path>/docs/05-features/features-backlog.md` following the 10-category convention. Backward-compat: when the flag is absent, behavior is unchanged.

### `--project-dir` mode (backlog append)

When `--project-dir` is set, invoke:

```
uv run python3 scripts/document_feature_append.py \
  --project-dir <path> \
  --feature "<feature name>" \
  [--status backlog|in-progress|done|blocked] \
  [--priority L|M|H] \
  [--owner "<owner>"]
```

Behavior:
- Creates `docs/05-features/features-backlog.md` if missing, with table header.
- Assigns the next monotonic id `F-NN` based on existing rows.
- Appends one row; does NOT rewrite existing rows.
- Does NOT touch `docs/features/<feature>.md` (the legacy per-feature doc). Both outputs can coexist — backlog is the project-level index, per-feature docs are detail pages.

## Procedure

### 1. Resolve Features to Document (3-Layer Detection)

Resolve which features need documentation using three layers in priority order:

#### Layer 1: SDD Change Name (highest priority)

If a feature name matches an SDD change name (e.g., the user ran `/sdd-new add-biometrics`):

1. Search Engram for the spec: `mem_search(query: "planning/{feature-name}/spec")`
2. If found, retrieve full content via `mem_get_observation(id: {id})`
3. Extract the scope from the spec: affected services, components, endpoints, entities
4. Use this scope to guide documentation depth and coverage

#### Layer 2: Git Diff Detection (fallback)

If no SDD change name is given and no CLI arg provided:

1. Run: `git diff --name-only main...HEAD`
2. Group changed files by feature area:
   - Files under `src/features/{name}/` or `internal/{service}/` or `apps/{name}/`
   - Group by the top-level feature/service directory
3. Deduplicate and sort by number of changes (most-changed first)
4. Present detected features to the user for confirmation before proceeding

#### Layer 3: CLI Argument (manual override)

If a feature name is passed as argument, use it directly. No detection needed.

**If all layers return empty**: report "No features detected for documentation" and exit.

### 2. Scan Feature Codebase

For each feature to document, scan the following sources:

| Source Type | What to Look For |
|-------------|-----------------|
| **Barrel exports** | `index.ts`, `mod.go`, `__init__.py` — public API surface |
| **Components** | React/Vue/Svelte components, UI elements |
| **Hooks/Composables** | Custom React hooks, Vue composables |
| **Services** | Business logic, use cases, application services |
| **API Endpoints** | Controllers, route definitions, handler functions |
| **Entities/Models** | Domain models, database schemas, DTOs |
| **Configuration** | Feature flags, env vars, config files |
| **Tests** | Test files, test utilities, fixtures |

For each source type:
1. Use `Glob` to find matching files within the feature directory
2. Read each file to extract: exported symbols, function signatures, type definitions, route paths
3. Collect structured data for each section of the documentation

### 3. Check for Existing Documentation

Check if `docs/features/{feature-name}.md` already exists:

- **If it does NOT exist**: proceed to Step 4 (Create)
- **If it DOES exist**: proceed to Step 5 (Update)

### 4. Create New Documentation

Generate `docs/features/{feature-name}.md` with this structure:

```markdown
---
feature: {feature-name}
created: {YYYY-MM-DD}
last-updated: {YYYY-MM-DD}
status: active
source: auto-generated
---

# {Feature Name}

## Overview

{1-2 paragraph description of what the feature does, its purpose, and how it fits
into the larger system. Derived from code analysis, SDD spec if available, or
README/comments in the feature directory.}

## Architecture

{Describe the feature's internal architecture: layers involved, key design
decisions, data flow. Include a simple text diagram if the feature spans
multiple services or has complex data flow.}

### Key Components

| Component | Path | Responsibility |
|-----------|------|---------------|
| {ComponentName} | {relative/path} | {what it does} |

### Dependencies

- **Internal**: {other features or services this depends on}
- **External**: {third-party libraries, APIs, services}

## API

### Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| {GET/POST/...} | {/api/...} | {what it does} | {required/optional/none} |

### Request/Response Examples

{For each significant endpoint, provide a brief request/response example
using the types found in the codebase. Do NOT fabricate data — use type
definitions from DTOs/models.}

## Components

{List UI components if applicable, with their props/inputs and purpose.
Skip this section entirely for backend-only features.}

| Component | Props/Inputs | Description |
|-----------|-------------|-------------|
| {Name} | {key props} | {what it renders} |

## Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| {ENV_VAR or config key} | {type} | {default} | {what it controls} |

## Testing

### Test Coverage

| Test Type | File | Status |
|-----------|------|--------|
| Unit | {path} | {exists/missing} |
| Integration | {path} | {exists/missing} |
| E2E | {path} | {exists/missing} |

### Running Tests

```bash
{exact command to run this feature's tests}
```

## Changelog

| Date | Change | Author |
|------|--------|--------|
| {YYYY-MM-DD} | Initial documentation generated | agent |

<!-- MANUAL NOTES START -->
<!-- Add manual notes, decisions, or context below this line. -->
<!-- These notes are preserved during automatic updates. -->
<!-- MANUAL NOTES END -->
```

### Section Rules

- **Skip empty sections**: If a feature has no UI components, omit the Components section entirely. If no API endpoints, omit the API section. Do not leave empty tables.
- **Use real code references**: Every entry in a table must reference an actual file path or symbol found during scanning. Never fabricate paths or names.
- **Keep Overview concise**: Max 2 paragraphs. Link to SDD spec in Engram if available.

### 5. Update Existing Documentation

When `docs/features/{feature-name}.md` already exists:

#### 5a. Diff Current State vs Documented

1. Read the existing doc
2. Compare scanned codebase state against each documented section:
   - New endpoints not in the API table
   - Removed endpoints still listed
   - New components not documented
   - Changed configuration variables
   - New or removed test files

#### 5b. Preserve Manual Notes

1. Extract content between `<!-- MANUAL NOTES START -->` and `<!-- MANUAL NOTES END -->` markers
2. Store it in memory
3. After updating all auto-generated sections, re-insert the manual notes block unchanged

#### 5c. Preserve Existing Changelog

1. Read the existing Changelog table entries
2. Do NOT remove or modify existing entries
3. Append a new entry for this update:
   ```
   | {YYYY-MM-DD} | {brief description of what changed} | agent |
   ```

#### 5d. Update Sections Incrementally

For each section:
- **Add** new items (endpoints, components, config vars, tests)
- **Remove** items that no longer exist in the codebase (mark as removed in changelog)
- **Update** items whose signatures or paths changed
- **Never delete** manual prose within sections — only update structured tables and generated descriptions

#### 5e. Update Frontmatter

Update `last-updated` to today's date. Keep all other frontmatter fields.

### 6. Clear Stale Doc Entries

After successfully generating/updating documentation:

1. Read `.cognitive-os/metrics/stale-docs.jsonl`
2. Remove entries where `stale_docs` includes the doc file just updated
3. Write back the filtered entries (or truncate if all cleared)

This integrates with the doc-sync system so the session-end warning reflects reality.

### 7. Report

Output a summary:

```
## Document Feature Report

| Feature | Action | Doc Path | Sections Updated |
|---------|--------|----------|-----------------|
| {name} | Created/Updated | docs/features/{name}.md | {list} |

Detection layer used: {1: SDD spec / 2: git diff / 3: CLI arg}
Stale doc entries cleared: {N}
```

## Edge Cases

- **Feature directory does not exist**: Report error, skip that feature, continue with others
- **No source files found**: Generate a minimal doc with Overview only, note "No source files detected" in the overview
- **Multiple features detected**: Document each one sequentially, report all results
- **Doc file is read-only or in a submodule**: Warn and skip
- **SDD spec found but outdated**: Use spec for context but scan codebase for current truth — codebase always wins over spec for factual content
- **Existing doc has no MANUAL NOTES markers**: Add the markers at the end during update, preserving all existing content above them

## Integration

- **doc-sync rule** (`rules/doc-sync.md`): Clears stale-docs entries after documenting
- **doc-sync skill** (`skills/doc-sync/`): Complementary — doc-sync updates existing docs based on code changes; document-feature creates comprehensive feature docs
- **SDD pipeline**: Uses spec artifacts from `planning/{change}/spec` for scope detection
- **Engram**: Saves documentation decisions to `docs/{feature-name}/documentation` topic key

## Acceptance Criteria

1. `test -f docs/features/{feature-name}.md` — doc file exists after run
2. Doc contains at least Overview and Architecture sections with non-empty content
3. All file paths referenced in the doc exist in the codebase: `grep -oP '(?<=\| )[^ |]+\.(ts|go|py|java)' docs/features/{name}.md | xargs -I{} test -f {}`
4. Manual notes block preserved if doc was updated (diff old vs new manual notes section)
5. Changelog has a new entry dated today if doc was updated
6. `.cognitive-os/metrics/stale-docs.jsonl` has no entries referencing the updated doc
