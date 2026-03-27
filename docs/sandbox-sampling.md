# Sandbox Sampling

## The Problem

Agents optimize for speed, not correctness at scale. When given a task like "rebrand across the codebase," an agent will:

1. Run `sed -i 's/old/new/g'` on every file
2. Report "done" with confidence
3. Leave behind broken documentation, corrupted configs, and mangled prose

Specific failure modes:

- **sed on Markdown**: `sed 's/acme/globex/g'` turns "built on acme's architecture" into "built on globex's architecture" — grammatically awkward. A contextual agent would rewrite the full sentence as "built on the Globex architecture" instead.
- **sed on YAML**: Replacing a value that happens to be part of an indentation-sensitive structure can break parsing.
- **Partial application**: Agent processes 50 of 600 files, hits context limits, and reports "done" because the first 50 worked.
- **No verification**: Agent never checks if the build still passes or if grep finds zero remaining occurrences.

## The Solution: Classify, Sample, Sandbox, Verify, Scale

Instead of applying changes to all files at once, the sandbox-sampling pattern forces a staged approach:

```
CLASSIFY --> SAMPLE --> SANDBOX --> VERIFY --> DECIDE --> SCALE --> FINAL VERIFY
```

### 1. Classify

Group target files by type. Each type has different transformation rules:

| Type | Transform | Validation |
|------|-----------|------------|
| Code | Mechanical (sed) OK | Build + test |
| Docs | Contextual agent ONLY | LLM coherence check |
| Config | Mechanical OK | Parse validation |
| Templates | Case-by-case | Render test |

### 2. Sample

Select 3-5 representative files per type: smallest, largest, most complex, edge cases. This subset is small enough to verify thoroughly.

### 3. Sandbox

Create a git worktree for isolation. Apply changes ONLY to sampled files. The main codebase remains untouched.

### 4. Verify

Run type-appropriate checks: build for code, parse for config, LLM coherence for docs.

### 5. Decide

If all samples pass, the strategy is validated. If some fail, adjust the approach (e.g., switch docs from sed to contextual agent) and re-test.

### 6. Scale

Apply the validated strategy to all files. Use the same method that passed sampling.

### 7. Final Verify

Full verification on the complete result: build, test, grep for remaining occurrences, parse all configs.

## Decision Matrix

| File Type | <20 files | 20-100 files | >100 files |
|-----------|-----------|--------------|------------|
| Code | Direct apply | Direct OK | Sample first |
| Docs | Contextual agent | Contextual agent | Sample + contextual agent |
| Config | Direct apply | Validate after | Sample + validate |
| Templates | Direct apply | Render test | Sample + render test |

## When Sampling is Mandatory vs Recommended

- **Mandatory** (>100 files): Cannot skip. The risk of silent failures is too high.
- **Recommended** (20-100 files): Should use sampling. Can skip if the change is trivially mechanical (e.g., adding a single import line).
- **Optional** (<20 files): Direct application is fine, but docs still need contextual agents.

## Git Worktree Isolation

The sandbox uses git worktrees for isolation:

```bash
# Create sandbox
git worktree add /tmp/cognitive-os-sandbox-{timestamp} HEAD

# Work in sandbox (changes don't affect main tree)
cd /tmp/cognitive-os-sandbox-{timestamp}
# ... apply and verify changes ...

# Clean up
git worktree remove /tmp/cognitive-os-sandbox-{timestamp} --force
```

Benefits:
- Full git history available for reference
- Changes are completely isolated from the working tree
- Easy cleanup -- just remove the worktree
- Can run builds and tests independently

## Example: Rebranding (Bad vs Good)

### Bad: sed everything

```bash
sed -i 's/old-name/new-name/g' $(grep -rl 'old-name')
# Result: 600 files changed, docs are broken, agent says "done"
```

### Good: sandbox-sample

1. **Classify**: 89 Go, 38 Markdown, 15 YAML, 8 JSON = 150 files
2. **Sample**: 4 Go + 3 MD + 3 YAML + 2 JSON = 12 files
3. **Sandbox**: worktree created, 12 files modified
4. **Verify**: Go builds. MD has broken sentences -- sed failed on docs. YAML parses OK.
5. **Decide**: sed works for code+config. Docs need contextual agent.
6. **Scale**: sed on 112 code+config files, contextual agent on 38 doc files
7. **Final verify**: build passes, 0 grep hits, all configs parse, docs read naturally

The sampling caught the documentation problem on 3 files instead of breaking 38.

## Integration Points

- **Hook**: `epic-task-detector.sh` (PreToolUse on Agent) detects large-scope tasks and suggests `/sandbox-sample`
- **Rule**: `sandbox-sampling.md` enforces the decision matrix
- **Agent Quality**: `agent-quality.md` rules 6-7 reference sandbox sampling
- **Skill**: `/sandbox-sample` walks through the full process

## How to Invoke

```
/sandbox-sample
```

The orchestrator should suggest this when epic-task-detector fires or when a task description implies >20 files.
