# `cos run-task` Contract

> Phase 1 contract for running Cognitive OS without an interactive harness on a
> laptop, CI runner, VM, or container.

## Status

Implemented for the single-node mechanics: payload validation, typed exit codes,
`worktree`/`tempdir` isolated workspace creation, optional provider/agent command
execution, acceptance command execution, and durable artifacts. Queue-backed
workers and durable workflow engines remain later phases.

## Command

```bash
cos run-task \
  --payload task.json \
  --workspace /path/to/repo \
  --artifacts /path/to/artifacts/task-123
```

## Payload Schema

```json
{
  "schema_version": 1,
  "task_id": "task-123",
  "title": "Fix failing calculator test",
  "description": "Repair the failing unit test without changing public API.",
  "execution_profile": "balanced",
  "execution": {
    "mode": "command",
    "provider": "codex",
    "command": "codex exec --prompt \"$COS_TASK_DESCRIPTION\"",
    "timeout_seconds": 900
  },
  "workspace": {
    "repo": "/path/to/repo",
    "ref": "main",
    "isolation": "worktree"
  },
  "artifacts": {
    "dir": "/path/to/artifacts/task-123"
  },
  "acceptance_criteria": [
    {
      "id": "unit-tests",
      "command": "python3 -m pytest tests/unit -q",
      "timeout_seconds": 120
    }
  ]
}
```

`execution` is optional. When present, it runs before acceptance criteria inside
the isolated workspace. This intentionally models providers/agents as commands
for Phase 1 so the runtime does not hardcode a vendor boundary.

## Artifact Contract

Each run writes:

```text
payload.json
preflight.json
execution.json
agent.log
execution.log
acceptance.json
acceptance-<id>.log
diff.patch
outcome.json
trust-report.md
execution-workspace/
```

## Exit Codes

| Exit code | Meaning |
| ---: | --- |
| 0 | Execution and required acceptance criteria passed. |
| 1 | Provider/agent execution or acceptance criteria failed. |
| 2 | Payload, configuration, or preflight blocked execution. |
| 124 | Provider/agent execution or acceptance criteria timed out. |

## Security Rules

- Secrets enter through environment variables or future secret manager, not the
  payload file.
- Provider names are metadata; `execution_profile` is the stable routing field.
- No broker, workflow engine, or cluster service is required for Phase 1.
- Artifacts are explicit and should be outside tracked source.
