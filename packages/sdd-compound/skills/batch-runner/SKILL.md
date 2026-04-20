<!-- SCOPE: both -->
---
name: batch-runner
version: 1.0.0
description: Execute multiple SDD changes sequentially with timing, reporting, and failure handling
triggers:
  - /batch-run
  - batch pipeline
  - run multiple changes
tags: [sdd, batch, pipeline, automation, ci-cd]
auto-generated: false
audience: project
---

# Batch Runner

Run multiple SDD changes through the pipeline sequentially. Supports all SDD phases (explore, propose, spec, design, tasks, apply, verify, archive), with per-change timing, JSON reports for CI/CD, and resume commands for failures.

## Usage

### From CLI

```bash
# Fast-forward multiple changes through all SDD phases
python lib/batch_runner.py add-auth refactor-payments --fast-forward

# Run a single phase across multiple changes
python lib/batch_runner.py add-auth refactor-payments --phase propose

# Use a YAML batch file
python lib/batch_runner.py --batch batch.yaml --fast-forward

# Dry run to preview execution plan
python lib/batch_runner.py --batch batch.yaml --fast-forward --dry-run

# Continue on failure + JSON report for CI/CD
python lib/batch_runner.py --batch batch.yaml --fast-forward \
  --continue-on-failure --json-report reports/batch-result.json

# Override model and timeout
python lib/batch_runner.py add-auth --fast-forward --model sonnet --timeout 900
```

### Batch YAML Format

Create a `batch.yaml` file:

```yaml
changes:
  - name: add-auth
    phases: [propose, spec, design]   # optional per-change phase override
  - name: refactor-payments           # uses global --phase or --fast-forward
  - name: fix-cache-bug
    phases: [apply, verify]
```

## Options

| Flag | Description |
|------|-------------|
| `--fast-forward` | Run all 8 SDD phases in sequence (explore through archive) |
| `--phase <phase>` | Run a single phase for all changes |
| `--batch <file>` | Read change list from YAML file |
| `--continue-on-failure` | Continue to next change if one fails |
| `--dry-run` | Preview execution plan without running |
| `--json-report <path>` | Write JSON report for CI/CD integration |
| `--project-dir <dir>` | Project directory (default: `.`) |
| `--timeout <seconds>` | Timeout per phase in seconds (default: 600) |
| `--model <model>` | Override Claude model (e.g., `sonnet`, `opus`) |
| `--verbose` | Enable verbose logging |

## Phase Priority

When determining which phases to run for a change:

1. **Per-change phases** (from YAML `phases` field) -- highest priority
2. **`--phase`** flag -- single phase for all changes
3. **`--fast-forward`** flag -- all phases
4. **Default** -- all phases if neither `--phase` nor `--fast-forward` given

## Output

### Console Summary

After execution, a summary table shows:
- Per-change status (OK/FAIL), timing, and failed phase
- Resume commands for failed changes
- Total duration and success/failure counts

### JSON Report

With `--json-report`, produces a structured report:

```json
{
  "summary": {
    "total_changes": 3,
    "succeeded": 2,
    "failed": 1,
    "total_seconds": 1234.56,
    "phases_mode": "fast-forward (all phases)"
  },
  "changes": [...],
  "failed_changes": [
    {
      "name": "fix-cache-bug",
      "failed_phase": "verify",
      "resume_command": "python lib/batch_runner.py fix-cache-bug --phase verify"
    }
  ]
}
```

## Architecture

The batch runner uses `ClaudeExecutor` from `lib/claude_executor.py` to invoke each SDD phase via the `claude` CLI. Each phase runs as a subprocess with configurable timeout.

```
batch_runner.py
  -> ClaudeExecutor.run_phase(phase, change_name)
    -> claude --print --dangerously-skip-permissions "<sdd prompt>"
```

> **Warning**: The `--dangerously-skip-permissions` flag is for development/testing ONLY.
> Using it in production bypasses Claude Code's safety permissions.
> Never use in production without explicit human approval.

## Integration with CI/CD

1. Use `--json-report` to produce machine-readable output
2. Use `--continue-on-failure` to process all changes even if some fail
3. Check exit code: 0 = all succeeded, 1 = at least one failure
4. Parse `failed_changes` array in the JSON report for retry logic

## Dependencies

- Python 3.9+
- `claude` CLI installed and on PATH
- `pyyaml` (only required when using `--batch`)
