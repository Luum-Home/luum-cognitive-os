# @luum/task-management

Task lifecycle hooks — recording, loop detection, scope creep, epic tasks, and blast radius

## Install

```bash
cos install @luum/task-management
```

## Components

- `hooks/task-recorder.sh` (hook) -- Record completed task costs and metadata
- `hooks/tool-loop-detector.sh` (hook) -- Detect repetitive tool call loops
- `hooks/scope-creep-detector.sh` (hook) -- Detect scope creep in agent outputs
- `hooks/epic-task-detector.sh` (hook) -- Detect large-scope tasks that need sampling
- `hooks/blast-radius.sh` (hook) -- Estimate task impact scope before execution

## License

Apache-2.0
