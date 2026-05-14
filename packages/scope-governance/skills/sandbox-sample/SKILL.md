---
name: sandbox-sample
command: /sandbox-sample
description: Classify, sample, sandbox-verify, then scale changes across large file
  sets
trigger: Epic tasks affecting >20 files, or manually via /sandbox-sample
inputs:
- task-description: What changes need to be made
- target-files: List or glob pattern of files to modify
- change-strategy: The transformation to apply (sed pattern, agent rewrite, config
    update)
outputs:
- classification: Files grouped by type with counts
- sample-set: Representative files selected per type
- sandbox-result: PASS | PARTIAL | FAIL per type
- final-result: PASS | FAIL after full-scale application
audience: project
version: 1.0.0
platforms:
- claude-code
prerequisites: []
triggers:
- sandbox-sample
- /sandbox-sample
- Sandbox Sampling
- Classify, sample, sandbox-verify, then scale changes across large file sets
---
<!-- SCOPE: both -->
# Sandbox Sampling

## Purpose

Prevent agents from executing massive changes without validation. Instead of applying changes to hundreds of files at once, the agent SAMPLES a few, validates in a sandbox, then scales.

This is the safety net for epic tasks: rebrands, migrations, bulk refactors, cross-codebase changes.

## When to Run

- **Mandatory**: Tasks affecting >100 files
- **Recommended**: Tasks affecting >20 files
- **Manual**: User invokes `/sandbox-sample`
- **Suggested by**: `epic-task-detector.sh` hook when it detects large-scope prompts

## Process

### Phase 1: CLASSIFY

Group all target files by type. Each type has different validation and transformation rules.

| Type | Extensions | Transform Strategy | Validation |
|------|-----------|-------------------|------------|
| `code` | *.go, *.ts, *.js, *.java, *.py | Mechanical (sed/grep) OK | Build, compile, test |
| `docs` | *.md | Contextual agent ONLY, never sed | LLM reads and checks coherence |
| `config` | *.yaml, *.yml, *.json, *.toml, *.env | Mechanical OK | Parse validation |
| `templates` | *.html, *.tmpl, *.hbs, *.ejs | Careful mechanical or agent | Render test if applicable |

**Action**: Run discovery commands to enumerate ALL target files:
```bash
# Example for a rebrand task
grep -rl 'old-name' --include='*.go' --include='*.ts' --include='*.md' --include='*.yaml' | sort
```

Count files per type and report:
```
CLASSIFICATION REPORT:
  code:      147 files (*.go: 89, *.ts: 42, *.java: 16)
  docs:       38 files (*.md: 38)
  config:     23 files (*.yaml: 15, *.json: 8)
  templates:   2 files (*.html: 2)
  TOTAL:     210 files
```

### Phase 2: SAMPLE

Select 3-5 representative files per type. The sample MUST cover edge cases.

**Selection criteria** (pick one of each when available):
1. **Smallest file** in the type — baseline, simplest case
2. **Largest file** in the type — stress test, most content
3. **Most complex** — deepest nesting, most occurrences of the target
4. **Edge case** — file with the target near quotes, code blocks, URLs, or other tricky contexts
5. **Cross-boundary** — file that references other files or imports (if applicable)

**Report the sample**:
```
SAMPLE SET (12 files from 210 total):
  code (4/147):
    - pkg/tools/http/builder.go (smallest, 45 lines)
    - cmd/main.go (largest, 320 lines)
    - internal/application/auth_usecase.go (complex, 8 occurrences)
    - pkg/sdks/users/client.go (cross-boundary, imports target)
  docs (3/38):
    - README.md (largest, public-facing)
    - docs/api-reference.md (complex, code blocks + prose)
    - CHANGELOG.md (edge case, target in version notes)
  config (3/23):
    - docker-compose.yml (largest, nested structure)
    - .github/workflows/ci.yml (edge case, env vars)
    - package.json (smallest)
  templates (2/2):
    - templates/index.html (all templates sampled — <10 total)
```

**Sample size rules**:
- Minimum: 3 per type (or all if fewer than 3 exist)
- Maximum: 10 per type
- If a type has <10 files total: sample ALL of them (no point sampling)

### Phase 3: SANDBOX

Create an isolated environment to test changes safely.

```bash
# Option A: Git worktree (preferred — full isolation)
SANDBOX_DIR="/tmp/cognitive-os-sandbox-$(date +%s)"
git worktree add "$SANDBOX_DIR" HEAD

# Option B: Copy (fallback if worktree not available)
SANDBOX_DIR="/tmp/cognitive-os-sandbox-$(date +%s)"
mkdir -p "$SANDBOX_DIR"
# Copy only sampled files preserving directory structure
```

Apply changes ONLY to the sampled files in the sandbox.

**Per-type transformation**:

| Type | Method | Detail |
|------|--------|--------|
| `code` | `sed` or `grep`+replace | Mechanical identifier replacement is safe |
| `docs` | **Contextual agent** | Agent reads the full document, understands context, rewrites naturally. NEVER use sed on docs. |
| `config` | `sed` or structured edit | Replace values, then validate parse |
| `templates` | Agent or careful `sed` | Depends on whether target is in markup vs content |

### Phase 4: VERIFY

Run type-appropriate verification on EVERY sampled file in the sandbox.

#### Code verification
```bash
# Go
cd "$SANDBOX_DIR" && go build ./...
cd "$SANDBOX_DIR" && go vet ./...
cd "$SANDBOX_DIR" && go test ./... -count=1

# TypeScript
cd "$SANDBOX_DIR" && npx tsc --noEmit

# Java
cd "$SANDBOX_DIR" && ./gradlew compileJava
```

#### Documentation verification
For EACH modified doc file, an agent reads the full document and checks:
- Does every sentence make sense in context?
- Are there broken references or dangling mentions of the old name?
- Is the prose natural (not mechanically replaced)?
- Are code examples still correct?

#### Config verification
```bash
# YAML
python3 -c "import yaml; yaml.safe_load(open('$FILE'))"

# JSON
python3 -c "import json; json.load(open('$FILE'))"

# TOML
python3 -c "import tomllib; tomllib.load(open('$FILE', 'rb'))"

# .env — check for syntax
grep -nE '^[^#=]+$' "$FILE"  # Lines that aren't comments or key=value
```

#### Template verification
- If a render pipeline exists, render the template and check output
- Otherwise, validate HTML/markup syntax

### Phase 5: DECIDE

Based on verification results, choose the next action:

| Result | Action |
|--------|--------|
| ALL samples PASS | "Strategy validated. Scaling to all {N} files." Proceed to Phase 6. |
| Code fails | Check compilation errors. Fix the sed pattern. Re-test sample. |
| Docs fail | Switch to contextual-rewrite agent if sed was attempted. Re-test. |
| Config fails | Parse errors — fix the replacement pattern. Re-test. |
| Multiple types fail | Reassess strategy. May need per-type strategies. |
| >2 retries on same type | HALT. Report to orchestrator: "Strategy cannot be validated for {type}. Manual review needed." |

### Phase 6: SCALE

Apply the validated strategy to ALL files (not just the sample).

- For code: Apply the same sed/mechanical transformation to all code files
- For docs: Launch contextual agents for each doc file (batch if >20)
- For config: Apply mechanical transformation + validate each file after
- For templates: Apply per template with validation

**Progress tracking**:
```
SCALING PROGRESS:
  code:      147/147 files processed ✓
  docs:       38/38  files processed ✓
  config:     23/23  files processed ✓
  templates:   2/2   files processed ✓
  TOTAL:     210/210 files complete
```

### Phase 7: FINAL VERIFY

Run full verification on the complete result set — not just samples.

```bash
# Full build
go build ./... && go test ./...
npx tsc --noEmit

# Full grep check (nothing left unreplaced)
grep -rl 'old-name' --include='*.go' --include='*.ts' --include='*.md' | wc -l
# Expected: 0

# Config parse check on all configs
find . -name '*.yaml' -exec python3 -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))" {} \;
```

Report final results:
```
FINAL VERIFICATION:
  Build:     PASS (go build, tsc --noEmit)
  Tests:     PASS (go test, jest)
  Grep:      PASS (0 remaining occurrences)
  Configs:   PASS (23/23 parse OK)
  TOTAL:     PASS — All 210 files verified
```

### Cleanup

```bash
# Remove sandbox worktree
git worktree remove "$SANDBOX_DIR" --force
```

## Key Rules

1. **Documentation changes MUST use contextual agents** — NEVER apply sed/grep to *.md files. Prose requires understanding, not pattern matching.
2. **Code identifier changes CAN use sed** — renaming variables, imports, package names is mechanical and safe after sample validation.
3. **Config value changes CAN use sed** — but MUST validate parsing after every change.
4. **Sample size**: minimum 3, maximum 10 per type. If <10 files in a type, sample ALL.
5. **If >100 files**: sampling is MANDATORY. Cannot skip directly to full application.
6. **If sample fails twice**: HALT and report. Do not keep retrying with the same strategy.
7. **Always clean up**: Remove sandbox worktree/directory after completion.

## Acceptance Criteria

When this skill completes, verify:

1. `CLASSIFICATION REPORT` was generated with accurate file counts per type
2. `SAMPLE SET` includes 3-5 files per type with rationale for each selection
3. Sandbox was created and changes applied only to sampled files
4. Per-type verification ran and results were reported
5. Decision was made based on verification results (not skipped)
6. If scaling: ALL files were processed (count matches classification)
7. Final verification passed with zero remaining issues
8. Sandbox was cleaned up

## Example: Rebranding "old-name" to "new-name"

**Bad approach** (what agents do without sampling):
```bash
# Agent runs this on 600 files, breaks documentation prose,
# corrupts YAML indentation, and reports "done"
sed -i 's/old-name/new-name/g' $(grep -rl 'old-name')
```

**Good approach** (with sandbox-sample):
1. CLASSIFY: 89 Go files, 38 Markdown, 15 YAML, 8 JSON
2. SAMPLE: 4 Go + 3 MD + 3 YAML + 2 JSON = 12 files
3. SANDBOX: worktree created, changes applied to 12 files
4. VERIFY: Go builds OK, but MD has broken sentences ("the new-na platform" instead of "the new-name platform" because "old-name" appeared mid-sentence). YAML parses OK.
5. DECIDE: Code+Config strategy validated. Docs need contextual agent.
6. SCALE: sed for code+config (112 files), contextual agent for docs (38 files)
7. FINAL VERIFY: build passes, 0 grep hits, all configs parse, docs read naturally
