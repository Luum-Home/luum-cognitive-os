---
name: add-hook
description: 'Use when you need this Cognitive OS skill: Step-by-step guide for adding
  a new hook to the Cognitive OS; do not use when a narrower skill directly matches
  the task.'
routing_intents:
  - "Add a Claude Code lifecycle hook for Cognitive OS tool interception"
  - "Create a new pre-tool or post-tool hook script and register it"
  - "Wire a custom hook into the current harness driver configuration"
  - "Implement a hook that validates tool usage before agent execution"
  - "Scaffold a Cognitive OS hook with metrics and graceful degradation"
version: 0.1.0
audience: os
tags:
- development
- extension
- hooks
platforms:
- claude-code
prerequisites: []
routing_patterns:
- pattern: \badd[- ]?hook\b
  confidence: 0.95
- pattern: /add-hook\b
  confidence: 0.95
- pattern: \bnew\s+hook\b
  confidence: 0.75
summary_line: Step-by-step guide for adding a new hook to the Cognitive OS.
triggers:
- add-hook
- new hook
- hook authoring
- Cognitive OS hook

---
<!-- SCOPE: os-only -->
# Add Hook

> Procedure for creating and registering a new lifecycle hook in the Cognitive OS.

## Scope note

This skill is `os-only` because the procedure modifies Cognitive OS hook
source, harness projection files, efficiency profiles, and COS-specific
portability gates. A generic "author a hook-like extension for any agent
runtime" procedure would be a separate portable primitive.

## Trigger

When you need to add a new hook to intercept tool usage at a specific
lifecycle point and keep its behavior portable across harnesses when possible.

## Inputs

- **Hook name**: kebab-case identifier (e.g., `my-check`)
- **Event type**: `PreToolUse`, `PostToolUse`, `SessionStart`, or `Stop`
- **Matcher**: tool pattern the hook should fire on (e.g., `Agent`, `Edit|Write`, `Bash`)
- **Purpose**: what the hook does and whether it can block execution

## Steps

### 1. Create the hook script

Use `templates/hook-template.sh` as the starting point:

```bash
cp templates/hook-template.sh hooks/{hook-name}.sh
chmod +x hooks/{hook-name}.sh
```

Then fill in the template placeholders. The field contract (ADR-067 Phase 2) requires
for all NEW hooks:

| Field | Requirement |
|---|---|
| Shebang | Line 1 must be `#!/usr/bin/env bash` |
| `# SCOPE:` | One of: `os-only`, `project`, `both` |
| `# PURPOSE:` | One-line description of what the hook does |
| `# EVENT:` | One of: `PreToolUse`, `PostToolUse`, `UserPromptSubmit`, `Stop`, `SessionStart` |
| `set -euo pipefail` | Within first 20 lines |

The `hooks/hook-header-validator.sh` PostToolUse hook will warn if these are missing
when you Write/Edit a hooks/*.sh file.

Before choosing `# SCOPE:`, classify the hook semantically:

| Scope | Use when |
|---|---|
| `os-only` | The hook builds/operates Cognitive OS itself, references COS source internals, maintainer manifests, ADR governance, local operator workflows, or source-repo automation. |
| `project` | The hook affects adopter projects only and is not needed for COS self-construction. |
| `both` | The hook is repo-agnostic agent/repository governance useful in COS and adopter repositories. |

Do not use lifecycle event, distribution tier, projection profile, or routing/exposure
labels as the sole SCOPE decision. If unsure, keep the hook out of consumer
projection until the classifier/audit evidence is added.

Key conventions:
- Read stdin JSON via `INPUT=$(cat)` — contains `tool_name`, `tool_input`, and (PostToolUse) `tool_response`
- Add a FAST PATH: `case "$INPUT" in *"TRIGGER"*) ;; *) exit 0 ;; esac` to avoid Python startup overhead
- Exit 0 = pass/advisory, exit 2 = BLOCK (PreToolUse only)
- Always complete in under 200ms for PreToolUse, under 500ms for PostToolUse
- Use `COS_STRICT_<NAME>_VALIDATION=1` env var for opt-in blocking mode (mirrors ADR-067 pattern)
- Prefer canonical env/path/session resolvers over harness-specific variables
- If the hook depends on a harness-specific event shape, isolate that fact in an
  adapter or document it explicitly as a projection constraint

### 2. Make it executable

```bash
chmod +x hooks/{hook-name}.sh
```

### 3. Register through the current harness driver

For the current Claude driver, add under the appropriate trigger key:

```json
{
  "hooks": {
    "{EventType}": [
      {
        "matcher": "{matcher_pattern}",
        "hooks": [
          {
            "type": "command",
            "command": "bash \"$CLAUDE_PROJECT_DIR/hooks/{hook-name}.sh\""
          }
        ]
      }
    ]
  }
}
```

If the trigger key already exists, add a new entry to the array. If a matching `matcher` block already exists, add the command to its `hooks` array.

Do not treat `.claude/settings.local.json` as the universal definition of the
hook. It is only one projection surface.

### 4. Add to efficiency profile (if always-active)

If the hook should run in the `standard` efficiency profile, add it to `packages/efficiency-profiles/profiles/standard.json`. For the `lean` profile, add to `lean.json`. Skip this step if the hook is optional or phase-specific.

Run `bash scripts/apply-efficiency-profile.sh standard` to apply after updating.

### 5. Add a test

Create `tests/unit/test-{hook-name}.sh`:

```bash
#!/usr/bin/env bash
# Tests for hooks/{hook-name}.sh

set -euo pipefail
source "$(dirname "$0")/_lib/test-helpers.sh"

test_pass_case() {
    local input='{"tool_name":"Edit","tool_input":{}}'
    local result
    result=$(echo "$input" | bash hooks/{hook-name}.sh; echo "exit:$?")
    assert_contains "$result" "exit:0" "should pass on normal input"
}

test_pass_case
echo "PASS: {hook-name} tests"
```

Run `bash tests/run-all-tests.sh` to verify.

### 5b. Add paired portability proof for universal hooks

If the hook declares `# SCOPE: both`, scaffold the exact paired proof path before
committing:

```bash
scripts/cos-portability-proof-scaffold --artifact hooks/{hook-name}.sh
```

Keep the generated `test_runs_from_arbitrary_project_root` falsification probe
and specialize it for the hook payload, matcher, and degradation contract.

### 5c. Prove install projection consistency

If the hook can be installed or registered in a generated project harness, run
the install projection audit before commit:

```bash
scripts/cos-install-projection-audit --json
```

This proves generated `.codex/hooks.json` and `.claude/settings.json` do not
reference a hook that the same filtered install failed to copy, and do not
register `SCOPE: os-only` hooks under consumer `project`/`both` installs.

### 5d. Run the scope classifier for this hook

Every new or reclassified hook must pass the evidence-weighted classifier before
commit:

```bash
python3 scripts/primitive_scope_classifier.py \
  --project-dir . \
  --paths hooks/{hook-name}.sh \
  --fail-contradictions \
  --fail-low-confidence
```

If this fails, add the missing evidence instead of weakening the classifier:

- `manifests/primitive-consumer-availability.yaml` for consumer/shared/maintainer availability.
- `manifests/primitive-behavior-evidence.yaml` for paired portability proof rows.
- `tests/red_team/portability/<proof>.py` for `SCOPE: both`.
- lifecycle metadata when the primitive becomes a durable runtime surface.

## Available Trigger Reference

| Trigger | When it fires | Input available | Can block? |
|---------|--------------|-----------------|------------|
| `PreToolUse` | Before a tool runs | `tool_name`, `tool_input` | Yes (exit 2) |
| `PostToolUse` | After a tool runs | `tool_name`, `tool_input`, `tool_response`, `exit_code` | No |
| `SessionStart` | At session start | `session_id` | No |
| `Stop` | At session end | `session_id` | No |

## Matcher Pattern Reference

| Pattern | Matches |
|---------|---------|
| `Agent` | Agent tool only |
| `Bash` | Bash tool only |
| `Edit\|Write` | Edit or Write tools |
| `Edit\|Write\|Bash` | Edit, Write, or Bash tools |
| `.*` | All tools |

## Output: Working Registered Hook

- `hooks/{hook-name}.sh` — executable hook script
- `.claude/settings.local.json` — updated with hook registration
- `tests/unit/test-{hook-name}.sh` — passing test
- `tests/red_team/portability/test_{hook-name}.py` — paired proof when `SCOPE: both`
- Efficiency profile updated (if always-active)

## Success Criteria

- [ ] `bash -n hooks/{hook-name}.sh` exits 0 (syntax valid)
- [ ] Hook is listed in `.claude/settings.local.json` under the correct trigger
- [ ] `bash tests/unit/test-{hook-name}.sh` passes
- [ ] `scripts/cos-portability-proof-scaffold --artifact hooks/{hook-name}.sh` was used for `SCOPE: both` hooks
- [ ] `python3 scripts/primitive_scope_classifier.py --project-dir . --paths hooks/{hook-name}.sh --fail-contradictions --fail-low-confidence` passes
- [ ] `scripts/cos-scope-both-portability-audit --strict --no-write` passes after adding the proof
- [ ] `scripts/cos-scope-projection-audit --run-install-smoke --strict --no-write` passes before commit when the hook can project to projects
- [ ] `scripts/cos-install-projection-audit --json` passes when generated harness hook settings are affected
- [ ] Hook fires correctly: `echo '{"tool_name":"X","tool_input":{}}' | bash hooks/{hook-name}.sh`
- [ ] Any harness-specific assumptions are isolated or explicitly documented
